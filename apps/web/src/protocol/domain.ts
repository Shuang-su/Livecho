import {
  canonicalJson,
  sha256Hex,
  validateModel,
  type StableCode,
  type TimelineEventV1,
  type TimelineEventV1Minor1,
  type ViewerCursorV1,
  type ViewerReadyV1,
  type ViewerReadyV1Minor1,
  type ViewerResyncV1,
} from "@livecho/protocol/browser";

export type SessionStatus = "starting" | "live" | "stopping" | "stopped" | "failed";

/** Server-selected viewer protocol minor. */
export type ViewerMinor = 0 | 1;
export type AnyViewerReady = ViewerReadyV1 | ViewerReadyV1Minor1;
export type AnyTimelineEvent = TimelineEventV1 | TimelineEventV1Minor1;

export interface AcceptedTranscript {
  kind: "transcript";
  seq: bigint;
  eventId: string;
  segmentId: string;
  text: string;
  isFinal: boolean;
  startMs: number;
  endMs: number;
  language: string | null;
}

export interface AcceptedStatus {
  kind: "status";
  seq: bigint;
  eventId: string;
  status: SessionStatus;
  reasonCode: string | null;
}

export type AcceptedEvent = AcceptedTranscript | AcceptedStatus;

export type DomainOutcome =
  | { outcome: "accepted"; event: AcceptedEvent }
  | { outcome: "duplicate" }
  | { outcome: "rejected"; code: StableCode; resync: boolean };

export interface ReadyAssessment {
  outcome: "fresh" | "resumed" | "invalid";
  /** True when presentation state and the session delay must reset. */
  resetsPresentation: boolean;
}

export type ResyncOutcome =
  | { outcome: "applied" }
  /** A live same-epoch notice: no counter or state change. */
  | { outcome: "duplicate" }
  | { outcome: "rejected"; code: StableCode };

export interface ResyncContext {
  roomId: string;
  /** True until the current connection has accepted a ready or resync. */
  awaitingFirstResponse: boolean;
  /** Cursor sent in this connection's subscribe, if any. */
  sentCursor: ViewerCursorV1 | null;
}

type RevisionDecision =
  | { kind: "accepted"; event: AcceptedEvent }
  | { kind: "outcome"; outcome: DomainOutcome };

interface RevisionState {
  currentRevision: bigint;
  contentDigest: string;
  immutableDigest: string;
  final: boolean;
}

interface Binding {
  sessionId: string;
  epoch: bigint;
  minor: ViewerMinor;
}

const SEQUENCE_WINDOW = 256;
const REVISION_IDENTITY_CAPACITY = 4096;

/** Statuses and reason codes that block all further transcript presentation. */
const TERMINAL_STATUSES: ReadonlySet<SessionStatus> = new Set([
  "stopping",
  "stopped",
  "failed",
]);
const BLOCKING_REASONS: ReadonlySet<string> = new Set([
  "ingest_disabled",
  "policy_disable",
  "session_deleted",
]);

export function isBlockingStatus(status: SessionStatus, reasonCode: string | null): boolean {
  return (
    TERMINAL_STATUSES.has(status) || (reasonCode !== null && BLOCKING_REASONS.has(reasonCode))
  );
}

function contentDigest(event: AnyTimelineEvent): string {
  const { message_id: _messageId, sent_at: _sentAt, seq: _seq, ...projection } = event;
  return sha256Hex(canonicalJson(projection));
}

function immutableDigest(event: AnyTimelineEvent): string {
  const payload = event.payload as unknown as Record<string, unknown>;
  const isTranscript = "segment_id" in payload;
  const projection: Record<string, unknown> = {
    type: event.type,
    session_id: event.session_id,
    room_id: event.room_id,
    event_id: event.event_id,
    epoch: event.epoch,
    occurred_at: event.occurred_at,
    payload: isTranscript ? "transcript" : "session-status",
  };
  if (isTranscript) {
    projection.segment_id = payload.segment_id;
    projection.start_ms = payload.start_ms;
    projection.end_ms = payload.end_ms;
  }
  return sha256Hex(canonicalJson(projection));
}

/**
 * Client-side receive state for one `(session_id, epoch)` viewer binding.
 *
 * Implements the v1 sequence/revision acceptance rules exactly: integer-safe
 * uint64 identities, the 256-record sequence window, the 4,096-identity
 * revision capacity, duplicate no-ops, immutable projections, and terminal
 * status blocking. Pure: no timers, storage, or transport.
 */
export class ViewerReceiveDomain {
  private binding: Binding | null = null;
  private nextSeq = 0n;
  private readonly window = new Map<bigint, { messageId: string; digest: string }>();
  private readonly revisions = new Map<string, RevisionState>();
  private statusValue: SessionStatus | null = null;
  private statusReasonValue: string | null = null;
  private blockedValue = false;

  get sessionId(): string | null {
    return this.binding?.sessionId ?? null;
  }

  get nextExpectedSeq(): bigint {
    return this.nextSeq;
  }

  get status(): SessionStatus | null {
    return this.statusValue;
  }

  get statusReason(): string | null {
    return this.statusReasonValue;
  }

  get blocked(): boolean {
    return this.blockedValue;
  }

  /** Cursor for a same-binding resume, or null before the first ready. */
  cursor(): ViewerCursorV1 | null {
    if (this.binding === null) return null;
    return {
      session_id: this.binding.sessionId,
      epoch: this.binding.epoch.toString(),
      next_seq: this.nextSeq.toString(),
    };
  }

  /**
   * Apply a validated ViewerReadyV1 and decide whether protocol state starts
   * fresh or resumes the same binding.
   */
  acceptReady(ready: AnyViewerReady, sentCursor: ViewerCursorV1 | null): ReadyAssessment {
    const readyModel = ready.protocol_minor === 1 ? "ViewerReadyV1Minor1" : "ViewerReadyV1";
    if (
      validateModel(readyModel, ready as unknown as Record<string, unknown>) !== "accepted" ||
      ready.selected_minor !== ready.protocol_minor
    ) {
      return { outcome: "invalid", resetsPresentation: true };
    }
    const minor: ViewerMinor = ready.selected_minor;
    // A binding never downgrades, and a resumed binding keeps its exact minor.
    if (this.binding !== null && minor < this.binding.minor) {
      return { outcome: "invalid", resetsPresentation: true };
    }
    if (sentCursor === null) {
      if (ready.cursor_resumed) return { outcome: "invalid", resetsPresentation: true };
      this.binding = { sessionId: ready.session_id, epoch: BigInt(ready.epoch), minor };
      this.nextSeq = BigInt(ready.next_seq);
      this.window.clear();
      this.revisions.clear();
      this.statusValue = null;
      this.statusReasonValue = null;
      this.blockedValue = false;
      return { outcome: "fresh", resetsPresentation: true };
    }
    if (
      !ready.cursor_resumed ||
      ready.session_id !== sentCursor.session_id ||
      ready.epoch !== sentCursor.epoch ||
      ready.next_seq !== sentCursor.next_seq ||
      (this.binding !== null && minor !== this.binding.minor)
    ) {
      return { outcome: "invalid", resetsPresentation: true };
    }
    // The retained same-binding protocol state stays authoritative for the
    // resumed connection; display text was already cleared on disconnect.
    return { outcome: "resumed", resetsPresentation: false };
  }

  /**
   * Apply a minor-1 viewer.resync notice. Accepted only for an established
   * minor-1 binding of the same room and session, never after a terminal
   * status, with a current or higher epoch. While awaiting the first response
   * of a reconnect it needs the cursor that was sent; on a live connection a
   * same-epoch notice is a duplicate and never rewinds counters.
   */
  acceptResync(resync: ViewerResyncV1, context: ResyncContext): ResyncOutcome {
    const schemaCode = validateModel("ViewerResyncV1", resync as unknown as Record<string, unknown>);
    if (schemaCode !== "accepted") return { outcome: "rejected", code: schemaCode };
    const binding = this.binding;
    if (
      this.blockedValue ||
      binding === null ||
      binding.minor !== 1 ||
      resync.room_id !== context.roomId ||
      resync.session_id !== binding.sessionId
    ) {
      return { outcome: "rejected", code: "binding_mismatch" };
    }
    const epoch = BigInt(resync.epoch);
    if (epoch < binding.epoch) return { outcome: "rejected", code: "epoch_stale" };
    if (context.awaitingFirstResponse) {
      const sent = context.sentCursor;
      if (
        sent === null ||
        sent.session_id !== binding.sessionId ||
        sent.epoch !== binding.epoch.toString() ||
        sent.next_seq !== this.nextSeq.toString()
      ) {
        return { outcome: "rejected", code: "binding_mismatch" };
      }
    } else if (epoch === binding.epoch) {
      return { outcome: "duplicate" };
    }
    this.binding = { sessionId: binding.sessionId, epoch, minor: 1 };
    this.nextSeq = BigInt(resync.next_seq);
    this.window.clear();
    this.revisions.clear();
    this.statusValue = null;
    this.statusReasonValue = null;
    return { outcome: "applied" };
  }

  /** Drop every binding, window, revision, and status record. */
  clearAll(): void {
    this.binding = null;
    this.nextSeq = 0n;
    this.window.clear();
    this.revisions.clear();
    this.statusValue = null;
    this.statusReasonValue = null;
    this.blockedValue = false;
  }

  /**
   * Run the full v1 sequence and revision decision for one validated inbound
   * timeline event, never using Number arithmetic for epoch/seq/revision.
   */
  acceptEvent(event: AnyTimelineEvent): DomainOutcome {
    const eventModel = event.protocol_minor === 1 ? "TimelineEventV1Minor1" : "TimelineEventV1";
    const schemaCode = validateModel(eventModel, event as unknown as Record<string, unknown>);
    if (schemaCode !== "accepted") {
      return { outcome: "rejected", code: schemaCode, resync: false };
    }
    const binding = this.binding;
    if (
      binding === null ||
      event.session_id !== binding.sessionId ||
      event.protocol_minor !== binding.minor
    ) {
      return { outcome: "rejected", code: "binding_mismatch", resync: true };
    }
    const epoch = BigInt(event.epoch);
    if (epoch !== binding.epoch) {
      // A higher epoch is not authority to change epoch and a lower epoch is
      // stale; only a new valid handshake can resolve either. A late event of
      // a closed minor-1 epoch is dropped without a fresh resync.
      return {
        outcome: "rejected",
        code: epoch < binding.epoch ? "epoch_stale" : "epoch_unknown",
        resync: epoch > binding.epoch || binding.minor === 0,
      };
    }

    const seq = BigInt(event.seq);
    const digest = contentDigest(event);
    if (seq < this.nextSeq) {
      const record = this.window.get(seq);
      if (record === undefined) {
        return { outcome: "rejected", code: "resync_required", resync: true };
      }
      if (record.messageId !== event.message_id || record.digest !== digest) {
        return { outcome: "rejected", code: "seq_conflict", resync: false };
      }
      return { outcome: "duplicate" };
    }
    if (seq > this.nextSeq) {
      return { outcome: "rejected", code: "seq_gap", resync: true };
    }

    const decision = this.acceptRevision(event, digest);
    if (decision.kind === "outcome") {
      if (decision.outcome.outcome === "duplicate") {
        // An exact canonical retransmission of the current revision consumes
        // the sequence with no object side effect (v1 revision_duplicate).
        this.nextSeq = seq + 1n;
        this.window.set(seq, { messageId: event.message_id, digest });
        if (this.window.size > SEQUENCE_WINDOW) {
          const oldest = this.window.keys().next();
          if (!oldest.done) this.window.delete(oldest.value);
        }
        return { outcome: "duplicate" };
      }
      return decision.outcome;
    }

    this.nextSeq = seq + 1n;
    this.window.set(seq, { messageId: event.message_id, digest });
    if (this.window.size > SEQUENCE_WINDOW) {
      const oldest = this.window.keys().next();
      if (!oldest.done) this.window.delete(oldest.value);
    }
    return { outcome: "accepted", event: decision.event };
  }

  private acceptRevision(event: AnyTimelineEvent, digest: string): RevisionDecision {
    const revision = BigInt(event.revision);
    const existing = this.revisions.get(event.event_id);
    if (existing === undefined) {
      if (this.revisions.size >= REVISION_IDENTITY_CAPACITY) {
        return {
          kind: "outcome",
          outcome: {
            outcome: "rejected",
            code: "revision_capacity_exceeded",
            resync: true,
          },
        };
      }
      if (revision !== 1n) {
        return {
          kind: "outcome",
          outcome: { outcome: "rejected", code: "revision_gap", resync: false },
        };
      }
    } else if (revision < existing.currentRevision) {
      return {
        kind: "outcome",
        outcome: { outcome: "rejected", code: "revision_stale", resync: false },
      };
    } else if (revision === existing.currentRevision) {
      if (digest === existing.contentDigest) {
        return { kind: "outcome", outcome: { outcome: "duplicate" } };
      }
      return {
        kind: "outcome",
        outcome: {
          outcome: "rejected",
          code: existing.final ? "object_final" : "revision_conflict",
          resync: false,
        },
      };
    } else if (existing.final) {
      return { kind: "outcome", outcome: { outcome: "rejected", code: "object_final", resync: false } };
    } else if (revision > existing.currentRevision + 1n) {
      return {
        kind: "outcome",
        outcome: { outcome: "rejected", code: "revision_gap", resync: false },
      };
    } else if (immutableDigest(event) !== existing.immutableDigest) {
      return {
        kind: "outcome",
        outcome: { outcome: "rejected", code: "revision_immutable", resync: false },
      };
    }

    const payload = event.payload as unknown as Record<string, unknown>;
    const transcriptPayload = "segment_id" in payload ? payload : null;
    this.revisions.set(event.event_id, {
      currentRevision: revision,
      contentDigest: digest,
      immutableDigest: immutableDigest(event),
      final: transcriptPayload !== null && transcriptPayload.is_final === true,
    });

    if (transcriptPayload === null) {
      const status = payload.status as SessionStatus;
      const reasonCode =
        payload.reason_code === undefined || payload.reason_code === null
          ? null
          : String(payload.reason_code);
      if (isBlockingStatus(status, reasonCode)) this.blockedValue = true;
      this.statusValue = status;
      this.statusReasonValue = reasonCode;
      return {
        kind: "accepted",
        event: {
          kind: "status",
          seq: BigInt(event.seq),
          eventId: event.event_id,
          status,
          reasonCode,
        },
      };
    }
    return {
      kind: "accepted",
      event: {
        kind: "transcript",
        seq: BigInt(event.seq),
        eventId: event.event_id,
        segmentId: String(transcriptPayload.segment_id),
        text: String(transcriptPayload.text),
        isFinal: transcriptPayload.is_final === true,
        startMs: Number(transcriptPayload.start_ms),
        endMs: Number(transcriptPayload.end_ms),
        language:
          transcriptPayload.language === undefined || transcriptPayload.language === null
            ? null
            : String(transcriptPayload.language),
      },
    };
  }
}
