import {
  VIEWER_PROTOCOL,
  PROTOCOL_MINOR,
  canonicalJson,
  strictJsonParse,
  validateModel,
  type ViewerCursorV1,
  type ViewerReadyV1,
  type TimelineEventV1,
} from "@livecho/protocol/browser";
import {
  PresentationEngine,
  DELAY_MIN_MS,
  type DisplayRow,
  type SchedulerClock,
  type TextMutation,
} from "./scheduler";
import { ViewerReceiveDomain, isBlockingStatus, type AcceptedStatus, type SessionStatus } from "./domain";
import { CONNECTION_LABELS, type ConnectionState } from "./labels";

export { CONNECTION_LABELS };
export type { ConnectionState };

const RETRY_DELAYS_MS = [250, 1_000, 2_000, 4_000, 8_000] as const;
const CLIENT_VERSION = "0.1.0";

const encoder = new TextEncoder();

export interface SessionNotices {
  /** Resync gap; stays until dismissed or the view is left. */
  gap: boolean;
  overflow: boolean;
  undisplayed: boolean;
}

export interface SessionMetrics {
  receivedEvents: number;
  duplicates: number;
  rejectedFrames: number;
  resyncs: number;
  appliedMutations: number;
  renderLagMaxMs: number;
  queuePeak: number;
  queueBytesPeak: number;
}

export interface SessionSnapshot {
  connection: ConnectionState;
  sessionStatus: SessionStatus | null;
  statusReason: string | null;
  delayMs: number;
  partial: DisplayRow | null;
  finals: readonly DisplayRow[];
  notices: SessionNotices;
  retryOffered: boolean;
  metrics: SessionMetrics;
}

/** Minimal WebSocket surface; injectable for tests and Node harnesses. */
export interface WebSocketLike {
  send(data: string): void;
  close(code?: number, reason?: string): void;
  addEventListener(type: string, listener: (event: { data?: unknown }) => void): void;
  readyState: number;
}

export interface SessionEnvironment {
  isOnline(): boolean;
  onOnline(listener: () => void): () => void;
  onOffline(listener: () => void): () => void;
  onVisible(listener: () => void): () => void;
}

export interface SessionDeps {
  url: string;
  roomId: string;
  clock: SchedulerClock;
  environment: SessionEnvironment;
  webSocketFactory?: (url: string, protocols: string[]) => WebSocketLike;
  /** Timer functions are injectable so unit tests can avoid real waits. */
  setTimeoutFn?: (handler: () => void, milliseconds: number) => unknown;
  clearTimeoutFn?: (handle: unknown) => void;
}

/**
 * Single-room caption session controller.
 *
 * Owns the viewer WebSocket, the bounded retry ladder, cursor resume, the
 * fresh-resync procedure, and the visibility precedence rules from the
 * accepted Issue #11 spec. Nothing here persists timeline data: cursors,
 * notices, and rows live in session memory only. Delay adjustments and
 * reconnects never rewrite source time, seq, epoch, revision, or text.
 */
export class CaptionSession {
  readonly engine: PresentationEngine;
  private readonly domain = new ViewerReceiveDomain();
  private readonly notices: SessionNotices = { gap: false, overflow: false, undisplayed: false };
  private state: ConnectionState = "connecting";
  private retryAttempt = 0;
  private retryOfferedValue = false;
  private retryTimer: unknown = null;
  private drainTimer: unknown = null;
  private drainTimerFireAt = 0;
  private socket: WebSocketLike | null = null;
  private sentCursor: ViewerCursorV1 | null = null;
  private closed = false;
  private terminal = false;
  private incompatible = false;
  private snapshotCache: SessionSnapshot | null = null;
  private readonly listeners = new Set<() => void>();
  private readonly metricsValue: SessionMetrics = {
    receivedEvents: 0,
    duplicates: 0,
    rejectedFrames: 0,
    resyncs: 0,
    appliedMutations: 0,
    renderLagMaxMs: 0,
    queuePeak: 0,
    queueBytesPeak: 0,
  };
  private readonly webSocketFactory: (url: string, protocols: string[]) => WebSocketLike;
  private readonly timeout: (handler: () => void, milliseconds: number) => unknown;
  private readonly cancelTimeout: (handle: unknown) => void;
  private readonly environment: SessionEnvironment;
  private readonly url: string;
  private readonly roomIdValue: string;
  private readonly clock: SchedulerClock;
  private readonly detachEnvironment: () => void;

  constructor(deps: SessionDeps) {
    this.url = deps.url;
    this.roomIdValue = deps.roomId;
    this.clock = deps.clock;
    this.environment = deps.environment;
    this.engine = new PresentationEngine(deps.clock);
    this.webSocketFactory =
      deps.webSocketFactory ?? ((url, protocols) => new WebSocket(url, protocols) as unknown as WebSocketLike);
    this.timeout = deps.setTimeoutFn ?? ((handler, ms) => setTimeout(handler, ms));
    this.cancelTimeout = deps.clearTimeoutFn ?? ((handle) => clearTimeout(handle as number));
    this.detachEnvironment = this.wireEnvironment();
    this.connect();
  }

  private wireEnvironment(): () => void {
    const offOnline = this.environment.onOnline(() => {
      if (this.closed || this.terminal || this.incompatible) return;
      // Coming online may begin one bounded retry cycle.
      this.retryAttempt = 0;
      if (this.socket === null && this.retryTimer === null) this.scheduleRetry();
    });
    const offOffline = this.environment.onOffline(() => {
      // Offline suspends timers and hides text immediately.
      this.cancelRetryTimer();
      this.closeSocket();
      this.clearTextAfterDisconnect();
      this.setState("offline");
    });
    const offVisible = this.environment.onVisible(() => {
      // Foreground restoration drains only the bounded queue; overflow is
      // already visible as a gap rather than a burst of stale subtitles.
      this.engine.drain();
      this.notify();
    });
    return () => {
      offOnline();
      offOffline();
      offVisible();
    };
  }

  get roomId(): string {
    return this.roomIdValue;
  }

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  getSnapshot(): SessionSnapshot {
    if (this.snapshotCache === null) this.snapshotCache = this.buildSnapshot();
    return this.snapshotCache;
  }

  private buildSnapshot(): SessionSnapshot {
    this.metricsValue.queuePeak = this.engine.pendingPeak;
    this.metricsValue.queueBytesPeak = this.engine.pendingBytesPeak;
    this.metricsValue.appliedMutations = this.engine.appliedMutations;
    this.metricsValue.renderLagMaxMs = this.engine.renderLagMaxMs;
    return {
      connection: this.state,
      sessionStatus: this.domain.status,
      statusReason: this.domain.statusReason,
      delayMs: this.engine.delayMs,
      partial: this.engine.partial,
      finals: this.engine.finalRows,
      notices: {
        gap: this.notices.gap,
        overflow: this.engine.notices.overflow,
        undisplayed: this.notices.undisplayed,
      },
      retryOffered: this.retryOfferedValue,
      metrics: { ...this.metricsValue },
    };
  }

  private notify(): void {
    this.snapshotCache = null;
    for (const listener of this.listeners) listener();
    this.scheduleDrain();
  }

  /**
   * Ensure one timer fires at the earliest pending due time so a delayed
   * mutation becomes visible even when no further events arrive. Delay
   * changes reschedule; emptying the queue cancels.
   */
  private scheduleDrain(): void {
    if (this.closed) {
      this.cancelDrainTimer();
      return;
    }
    const due = this.engine.earliestPendingDue();
    if (due === null) {
      this.cancelDrainTimer();
      return;
    }
    if (this.drainTimer !== null && this.drainTimerFireAt <= due) return;
    this.cancelDrainTimer();
    const wait = Math.max(0, due - this.clock.now());
    this.drainTimerFireAt = due;
    this.drainTimer = this.timeout(() => {
      this.drainTimer = null;
      this.engine.drain();
      this.snapshotCache = null;
      for (const listener of this.listeners) listener();
      this.scheduleDrain();
    }, wait);
  }

  private cancelDrainTimer(): void {
    if (this.drainTimer !== null) {
      this.cancelTimeout(this.drainTimer);
      this.drainTimer = null;
    }
  }

  private setState(state: ConnectionState): void {
    if (this.state === state) return;
    this.state = state;
    this.notify();
  }

  /** Session-only display delay; rejects values outside the accepted range. */
  setDelay(ms: number): boolean {
    const changed = this.engine.setDelay(ms);
    if (changed) this.notify();
    return changed;
  }

  dismissGap(): void {
    this.notices.gap = false;
    this.notify();
  }

  dismissUndisplayed(): void {
    this.notices.undisplayed = false;
    this.notify();
  }

  dismissOverflow(): void {
    this.engine.dismissOverflow();
    this.notify();
  }

  /** Explicit Retry control; never starts a room or enables ingest. */
  retry(): void {
    if (this.closed || this.terminal || this.incompatible) return;
    this.retryAttempt = 0;
    this.retryOfferedValue = false;
    this.cancelRetryTimer();
    this.setState("reconnecting");
    this.connect();
    this.notify();
  }

  dispose(): void {
    if (this.closed) return;
    this.closed = true;
    this.cancelRetryTimer();
    this.cancelDrainTimer();
    this.closeSocket();
    this.detachEnvironment();
    const { droppedUndisplayed } = this.engine.clearTextAndQueue();
    if (droppedUndisplayed) this.notices.undisplayed = true;
    this.notify();
  }

  private connect(): void {
    this.closeSocket();
    this.sentCursor = this.domain.cursor();
    const socket = this.webSocketFactory(this.url, [VIEWER_PROTOCOL]);
    this.socket = socket;
    socket.addEventListener("open", (event) => {
      if (this.socket !== socket) return;
      this.onOpen();
    });
    socket.addEventListener("message", (event) => {
      if (this.socket !== socket) return;
      this.onMessage(event.data);
    });
    socket.addEventListener("close", (event) => {
      if (this.socket !== socket) return;
      this.socket = null;
      this.onClose();
    });
    socket.addEventListener("error", () => {
      // The runtime always follows an error with a close event.
    });
  }

  private onOpen(): void {
    const cursor = this.sentCursor;
    const subscribe: Record<string, unknown> = {
      protocol: VIEWER_PROTOCOL,
      protocol_minor: PROTOCOL_MINOR,
      message_id: crypto.randomUUID(),
      sent_at: new Date().toISOString(),
      type: "viewer.subscribe",
      client_version: CLIENT_VERSION,
      supported_minors: [PROTOCOL_MINOR],
      room_id: this.roomIdValue,
    };
    if (cursor !== null) subscribe.cursor = cursor;
    if (validateModel("ViewerSubscribeV1", subscribe) !== "accepted" || !this.sendFrame(subscribe)) {
      this.metricsValue.rejectedFrames += 1;
      this.beginReconnectCycle(false);
    }
  }

  private sendFrame(frame: Record<string, unknown>): boolean {
    const socket = this.socket;
    if (socket === null) return false;
    try {
      socket.send(canonicalJson(frame));
      return true;
    } catch {
      return false;
    }
  }

  private onMessage(data: unknown): void {
    if (typeof data !== "string") {
      // Binary input is rejected before it can affect display.
      this.metricsValue.rejectedFrames += 1;
      this.notify();
      return;
    }
    const parsed = strictJsonParse(data);
    if (parsed.code !== "accepted") {
      this.metricsValue.rejectedFrames += 1;
      this.notify();
      return;
    }
    const value = parsed.value;
    if (value === undefined) {
      this.metricsValue.rejectedFrames += 1;
      this.notify();
      return;
    }
    if (typeof value.type !== "string") {
      this.metricsValue.rejectedFrames += 1;
      this.notify();
      return;
    }
    switch (value.type) {
      case "viewer.ready":
        this.handleReady(value);
        return;
      case "viewer.timeline_event":
        this.handleTimelineEvent(value);
        return;
      case "protocol.error":
        this.handleProtocolError(value);
        return;
      case "protocol.ack":
        if (validateModel("ProtocolAckV1", value) !== "accepted") {
          this.metricsValue.rejectedFrames += 1;
          this.notify();
        }
        return;
      default:
        this.metricsValue.rejectedFrames += 1;
        this.notify();
    }
  }

  private handleReady(value: Record<string, unknown>): void {
    if (validateModel("ViewerReadyV1", value) !== "accepted") {
      this.metricsValue.rejectedFrames += 1;
      this.beginReconnectCycle(true);
      return;
    }
    const ready = value as unknown as ViewerReadyV1;
    const assessment = this.domain.acceptReady(ready, this.sentCursor);
    if (assessment.outcome === "invalid") {
      this.metricsValue.rejectedFrames += 1;
      this.beginReconnectCycle(true);
      return;
    }
    if (assessment.outcome === "fresh") {
      // Room/session/epoch change erases the delay and all display state, and
      // a new binding ends any previous terminal visibility block.
      this.terminal = false;
      this.engine.reset();
      this.engine.setDelay(DELAY_MIN_MS);
    }
    this.engine.resumeAdmission();
    this.retryAttempt = 0;
    this.retryOfferedValue = false;
    this.cancelRetryTimer();
    this.setState("connected");
    this.notify();
  }

  private handleTimelineEvent(value: Record<string, unknown>): void {
    const schemaCode = validateModel("TimelineEventV1", value);
    if (schemaCode !== "accepted") {
      this.metricsValue.rejectedFrames += 1;
      this.notify();
      return;
    }
    const event = value as unknown as TimelineEventV1;
    const outcome = this.domain.acceptEvent(event);
    if (outcome.outcome === "duplicate") {
      this.metricsValue.duplicates += 1;
      this.notify();
      return;
    }
    if (outcome.outcome === "rejected") {
      this.metricsValue.rejectedFrames += 1;
      this.notify();
      if (outcome.resync) this.beginFreshResync();
      return;
    }
    this.metricsValue.receivedEvents += 1;
    if (outcome.event.kind === "status") {
      this.applyStatus(outcome.event);
      return;
    }
    const mutation: TextMutation = {
      seq: outcome.event.seq,
      eventId: outcome.event.eventId,
      segmentId: outcome.event.segmentId,
      text: outcome.event.text,
      isFinal: outcome.event.isFinal,
      receivedAt: this.clock.now(),
      byteSize: encoder.encode(canonicalJson(value)).length,
    };
    const result = this.engine.enqueueText(mutation);
    if (!result.ok) {
      // Either presentation queue limit: the engine stopped admission and
      // cleared text; close the connection and reconnect through the normal
      // current-cursor procedure with the visible overflow gap.
      this.metricsValue.resyncs += 1;
      this.retryAttempt = 0;
      this.closeSocket();
      this.setState("reconnecting");
      this.scheduleRetry();
      this.notify();
      return;
    }
    this.notify();
  }

  private applyStatus(status: AcceptedStatus): void {
    if (isBlockingStatus(status.status, status.reasonCode)) {
      // Stop/disable/delete/failure processing takes immediate priority over
      // delayed display and cancels reconnection timers.
      this.terminal = true;
      this.cancelRetryTimer();
      const { droppedUndisplayed } = this.engine.blockAndClearText();
      if (droppedUndisplayed) this.notices.undisplayed = true;
    }
    this.notify();
  }

  private handleProtocolError(value: Record<string, unknown>): void {
    if (validateModel("ProtocolErrorV1", value) !== "accepted") {
      this.metricsValue.rejectedFrames += 1;
      this.beginFreshResync();
      return;
    }
    const code = String(value.code);
    if (
      code === "unsupported_minor" ||
      code === "unknown_major" ||
      code === "worker_version_too_old"
    ) {
      this.incompatible = true;
      this.cancelRetryTimer();
      this.closeSocket();
      this.clearTextAfterDisconnect();
      this.setState("incompatible");
      this.notify();
      return;
    }
    if (code === "resync_required") {
      if (this.sentCursor !== null) {
        // The server cannot resume our cursor: explicit gap, fresh handshake.
        this.beginFreshResync();
        return;
      }
      // Fresh admission refused (for example a fixture partial is open);
      // retry through the bounded reconnect policy without a gap claim.
      this.metricsValue.resyncs += 1;
      this.closeSocket();
      this.clearTextAfterDisconnect();
      this.setState("reconnecting");
      this.scheduleRetry();
      this.notify();
      return;
    }
    // Any other server protocol error is a discontinuity: fresh resync with a
    // visible gap.
    this.beginFreshResync();
  }

  /**
   * A handshake failed or a fresh handshake is needed. Retries through the
   * bounded ladder; optionally claims a visible gap.
   */
  private beginReconnectCycle(showGap: boolean): void {
    this.closeSocket();
    this.clearTextAfterDisconnect();
    if (showGap) this.notices.gap = true;
    this.setState("reconnecting");
    this.scheduleRetry();
    this.notify();
  }

  /**
   * Fresh-resync procedure: clear protocol and display state, erase the
   * delay, show the visible gap, and obtain a new no-cursor handshake through
   * the bounded retry ladder.
   */
  private beginFreshResync(): void {
    if (this.closed) return;
    this.metricsValue.resyncs += 1;
    // A deliberate fresh resync starts a new bounded retry cycle.
    this.retryAttempt = 0;
    this.cancelRetryTimer();
    this.closeSocket();
    this.domain.clearAll();
    const { droppedUndisplayed } = this.engine.clearTextAndQueue();
    if (droppedUndisplayed) this.notices.undisplayed = true;
    this.engine.reset();
    this.engine.setDelay(DELAY_MIN_MS);
    this.notices.gap = true;
    this.setState("reconnecting");
    this.scheduleRetry();
    this.notify();
  }

  private clearTextAfterDisconnect(): void {
    const { droppedUndisplayed } = this.engine.clearTextAndQueue();
    if (droppedUndisplayed) this.notices.undisplayed = true;
    this.notify();
  }

  private onClose(): void {
    if (this.closed || this.terminal || this.incompatible) {
      this.clearTextAfterDisconnect();
      if (this.terminal) this.setState("offline");
      return;
    }
    // A closed connection immediately hides text; only the memory cursor and
    // protocol metadata survive for a possible same-binding resume.
    this.clearTextAfterDisconnect();
    if (this.retryTimer !== null) return;
    this.setState(this.environment.isOnline() ? "reconnecting" : "offline");
    this.scheduleRetry();
  }

  private scheduleRetry(): void {
    if (this.retryTimer !== null) return;
    if (!this.environment.isOnline()) {
      this.setState("offline");
      return;
    }
    if (this.retryAttempt >= RETRY_DELAYS_MS.length) {
      this.retryOfferedValue = true;
      this.notify();
      return;
    }
    const delay = RETRY_DELAYS_MS[this.retryAttempt]!;
    this.retryAttempt += 1;
    this.setState("reconnecting");
    this.retryTimer = this.timeout(() => {
      this.retryTimer = null;
      this.connect();
    }, delay);
    this.notify();
  }

  private cancelRetryTimer(): void {
    if (this.retryTimer !== null) {
      this.cancelTimeout(this.retryTimer);
      this.retryTimer = null;
    }
  }

  private closeSocket(): void {
    const socket = this.socket;
    this.socket = null;
    if (socket !== null && socket.readyState <= 1) socket.close(1000);
  }
}
