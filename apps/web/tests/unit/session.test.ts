import { describe, expect, it } from "vitest";
import { strictJsonParse } from "@livecho/protocol/browser";
import {
  CaptionSession,
  type SessionDeps,
  type WebSocketLike,
} from "../../src/protocol/session";
import {
  protocolErrorFrame,
  readyFrame,
  stamp,
  statusEvent,
  testUuid,
  transcriptEvent,
  TestClock,
} from "./helpers";

class FakeSocket implements WebSocketLike {
  readonly sent: string[] = [];
  readyState = 1;
  closed = false;
  private readonly listeners = new Map<string, Array<(event: { data?: unknown }) => void>>();

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    if (this.closed) return;
    this.closed = true;
    this.emit("close", {});
  }

  addEventListener(type: string, listener: (event: { data?: unknown }) => void): void {
    const existing = this.listeners.get(type) ?? [];
    existing.push(listener);
    this.listeners.set(type, existing);
  }

  emit(type: "open" | "close", event: { data?: unknown } = {}): void {
    for (const listener of [...(this.listeners.get(type) ?? [])]) listener(event);
  }

  emitMessage(data: unknown): void {
    for (const listener of [...(this.listeners.get("message") ?? [])]) listener({ data });
  }
}

class ManualTimers {
  private sequence = 0;
  private readonly entries: Array<{ id: number; due: number; handler: () => void }> = [];
  private now = 0;

  timeout(handler: () => void, milliseconds: number): number {
    this.sequence += 1;
    this.entries.push({ id: this.sequence, due: this.now + milliseconds, handler });
    return this.sequence;
  }

  cancel(handle: unknown): void {
    const index = this.entries.findIndex((entry) => entry.id === handle);
    if (index >= 0) this.entries.splice(index, 1);
  }

  pending(): number {
    return this.entries.length;
  }

  advance(milliseconds: number): void {
    this.now += milliseconds;
    for (const entry of [...this.entries].sort((a, b) => a.due - b.due)) {
      if (entry.due <= this.now) {
        this.cancel(entry.id);
        entry.handler();
      }
    }
  }
}

const ALWAYS_ONLINE = {
  isOnline: () => true,
  onOnline: () => () => undefined,
  onOffline: () => () => undefined,
  onVisible: () => () => undefined,
};

interface Harness {
  session: CaptionSession;
  sockets: FakeSocket[];
  timers: ManualTimers;
  clock: TestClock;
}

function startSession(supportedMinors?: SessionDeps["supportedMinors"]): Harness {
  const sockets: FakeSocket[] = [];
  const timers = new ManualTimers();
  const clock = new TestClock();
  const deps: SessionDeps = {
    url: "ws://test.invalid/api/viewer/ws",
    roomId: "livecho.fixture.room",
    ...(supportedMinors && { supportedMinors }),
    clock,
    environment: ALWAYS_ONLINE,
    webSocketFactory: () => {
      const socket = new FakeSocket();
      sockets.push(socket);
      return socket;
    },
    setTimeoutFn: (handler, ms) => timers.timeout(handler, ms),
    clearTimeoutFn: (handle) => timers.cancel(handle),
  };
  const session = new CaptionSession(deps);
  return { session, sockets, timers, clock };
}

function openMinor1(harness: Harness): FakeSocket {
  const socket = harness.sockets[0]!;
  socket.emit("open");
  expect(strictJsonParse(socket.sent[0]!).value?.supported_minors).toEqual([0, 1]);
  socket.emitMessage(JSON.stringify({
    ...readyFrame({ nextSeq: 1n }),
    protocol_minor: 1,
    selected_minor: 1,
  }));
  expect(harness.session.getSnapshot().connection).toBe("connected");
  return socket;
}

function resyncFrame(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    protocol: "livecho.viewer.v1",
    protocol_minor: 1,
    message_id: crypto.randomUUID(),
    sent_at: stamp(),
    type: "viewer.resync",
    session_id: readyFrame({ nextSeq: 1n }).session_id,
    room_id: "livecho.fixture.room",
    epoch: "2",
    next_seq: "1",
    media_continue_ms: 20,
    reason: "epoch_rotated",
    gap: true,
    ...overrides,
  };
}

describe("minor-1 caption recovery", () => {
  it("clears delayed old captions and ignores old-epoch data on the same socket", () => {
    const { session, sockets, clock, timers } = startSession([0, 1]);
    const socket = sockets[0]!;
    socket.emit("open");
    socket.emitMessage(JSON.stringify(transcriptEvent({ protocolMinor: 1 })));
    expect(session.getSnapshot().partial).toBeNull();
    socket.emitMessage(JSON.stringify({
      ...readyFrame({ nextSeq: 1n }),
      protocol_minor: 1,
      selected_minor: 1,
    }));
    socket.emitMessage(JSON.stringify(transcriptEvent({ protocolMinor: 1, text: "old partial" })));
    expect(session.getSnapshot().partial?.text).toBe("old partial");
    session.setDelay(5_000);
    socket.emitMessage(JSON.stringify(transcriptEvent({ protocolMinor: 1, seq: 2n, isFinal: true })));
    expect(timers.pending()).toBe(1);
    socket.emitMessage(JSON.stringify(resyncFrame()));
    expect(session.getSnapshot()).toMatchObject({
      connection: "connected",
      delayMs: 0,
      partial: null,
      finals: [],
      notices: { gap: true },
    });
    expect(timers.pending()).toBe(0);
    socket.emitMessage(JSON.stringify(transcriptEvent({ protocolMinor: 1, seq: 3n, isFinal: true })));
    socket.emitMessage(JSON.stringify({
      ...transcriptEvent({ protocolMinor: 1, text: "new final", isFinal: true }),
      epoch: "2",
    }));
    socket.emitMessage(JSON.stringify(resyncFrame()));
    clock.advance(5_000);
    timers.advance(5_000);
    expect(session.getSnapshot().finals.map((row) => row.text)).toEqual(["new final"]);
    expect(sockets).toHaveLength(1);
  });

  it("accepts an expired-cursor notice as the first response on a resumed socket", () => {
    const harness = startSession([0, 1]);
    const first = openMinor1(harness);
    first.emitMessage(JSON.stringify(transcriptEvent({ protocolMinor: 1 })));
    first.emit("close");
    harness.timers.advance(250);
    const second = harness.sockets[1]!;
    second.emit("open");
    expect(strictJsonParse(second.sent[0]!).value?.cursor).toMatchObject({ epoch: "1", next_seq: "2" });
    second.emitMessage(JSON.stringify(resyncFrame({ epoch: "1", next_seq: "8", reason: "cursor_expired" })));
    expect(harness.session.getSnapshot()).toMatchObject({
      connection: "connected",
      partial: null,
      notices: { gap: true },
    });
    second.emitMessage(JSON.stringify(transcriptEvent({ protocolMinor: 1, seq: 8n, isFinal: true })));
    expect(harness.session.getSnapshot().finals).toHaveLength(1);
  });

  it("rejects unrelated notices and keeps terminal visibility blocked", () => {
    const harness = startSession([0, 1]);
    const socket = openMinor1(harness);
    for (const fields of [{ room_id: "other-room" }, { session_id: testUuid(91) }]) {
      socket.emitMessage(JSON.stringify(resyncFrame(fields)));
    }
    expect(harness.session.getSnapshot().notices.gap).toBe(false);
    socket.emitMessage(JSON.stringify({ ...statusEvent({ status: "failed" }), protocol_minor: 1 }));
    socket.emitMessage(JSON.stringify(resyncFrame()));
    expect(harness.session.getSnapshot()).toMatchObject({
      sessionStatus: "failed",
      notices: { gap: false },
      finals: [],
    });
  });
});

function handshake(harness: Harness, nextSeq = 1n, withCursor: boolean[] = []): void {
  const { session, sockets, timers } = harness;
  const socket = sockets[sockets.length - 1]!;
  socket.emit("open");
  const subscribe = strictJsonParse(socket.sent[0] ?? "{}");
  expect(subscribe.code).toBe("accepted");
  const frame = subscribe.value;
  if (frame === undefined) throw new Error("missing subscribe frame");
  expect(frame.type).toBe("viewer.subscribe");
  expect(frame.room_id).toBe("livecho.fixture.room");
  const hasCursor = withCursor.shift() ?? false;
  expect((frame.cursor ?? null) !== null).toBe(hasCursor);
  socket.emitMessage(JSON.stringify(readyFrame({ nextSeq, cursorResumed: hasCursor })));
  expect(session.getSnapshot().connection).toBe("connected");
}

describe("caption session controller", () => {
  it("connects, presents a fixture timeline, and clears text on disconnect", () => {
    const harness = startSession();
    const { session, sockets, clock } = harness;
    handshake(harness);
    const socket = sockets[0]!;

    socket.emitMessage(JSON.stringify(statusEvent({ seq: 1n, status: "live" })));
    socket.emitMessage(
      JSON.stringify(transcriptEvent({ seq: 2n, eventId: testUuid(11), segmentId: testUuid(12), text: "provisional words" })),
    );
    socket.emitMessage(
      JSON.stringify(transcriptEvent({ seq: 3n, revision: 2n, eventId: testUuid(11), segmentId: testUuid(12), text: "final words", isFinal: true })),
    );
    let snapshot = session.getSnapshot();
    expect(snapshot.sessionStatus).toBe("live");
    expect(snapshot.partial).toBeNull();
    expect(snapshot.finals.map((row) => row.text)).toEqual(["final words"]);

    // Accept but delay a mutation, then disconnect: text hides immediately
    // and the pending loss is reported even though the cursor can resume.
    expect(session.setDelay(5_000)).toBe(true);
    socket.emitMessage(JSON.stringify(transcriptEvent({ seq: 4n, text: "never shown", isFinal: true })));
    socket.emit("close");
    snapshot = session.getSnapshot();
    expect(snapshot.finals).toHaveLength(0);
    expect(snapshot.notices.undisplayed).toBe(true);
    expect(snapshot.connection).toBe("reconnecting");

    harness.timers.advance(250);
    handshake(harness, 5n, [true]);
    snapshot = session.getSnapshot();
    expect(snapshot.notices.undisplayed).toBe(true);
    expect(snapshot.delayMs).toBe(5_000);
    expect(session.dismissUndisplayed()).toBeUndefined();
    expect(session.getSnapshot().notices.undisplayed).toBe(false);
    // The delayed final was dropped; the resumed stream continues from 5.
    sockets[sockets.length - 1]!.emitMessage(
      JSON.stringify(transcriptEvent({ seq: 5n, text: "resumed words", isFinal: true })),
    );
    // The scheduled drain timer fires at the delayed due time.
    clock.advance(6_000);
    harness.timers.advance(5_000);
    expect(session.getSnapshot().finals.map((row) => row.text)).toEqual(["resumed words"]);
  });

  it("resyncs fresh with a visible gap on a sequence gap", () => {
    const harness = startSession();
    const { session, sockets } = harness;
    handshake(harness);
    const socket = sockets[0]!;
    socket.emitMessage(JSON.stringify(statusEvent({ seq: 1n, status: "live" })));
    socket.emit("close");
    harness.timers.advance(250);
    const resumed = sockets[sockets.length - 1]!;
    resumed.emit("open");
    const resubscribe = strictJsonParse(resumed.sent[0] ?? "{}").value;
    if (resubscribe === undefined) throw new Error("missing resubscribe frame");
    expect(resubscribe.cursor).toBeDefined();
    resumed.emitMessage(JSON.stringify(transcriptEvent({ seq: 5n, isFinal: true })));
    const snapshot = session.getSnapshot();
    expect(snapshot.notices.gap).toBe(true);
    expect(snapshot.connection).toBe("reconnecting");
    expect(snapshot.delayMs).toBe(0);
    harness.timers.advance(250);
    handshake(harness);
    expect(session.getSnapshot().notices.gap).toBe(true);
    session.dismissGap();
    expect(session.getSnapshot().notices.gap).toBe(false);
  });

  it("treats a cursor-refused resync as an explicit gap and resubscribes without a cursor", () => {
    const harness = startSession();
    const { session, sockets } = harness;
    handshake(harness);
    const socket = sockets[0]!;
    socket.emitMessage(JSON.stringify(statusEvent({ seq: 1n, status: "live" })));
    socket.emit("close");
    harness.timers.advance(250);
    const resumed = sockets[sockets.length - 1]!;
    resumed.emit("open");
    const cursorFrame = strictJsonParse(resumed.sent[0] ?? "{}").value;
    if (cursorFrame === undefined) throw new Error("missing resubscribe frame");
    expect(cursorFrame.cursor).toBeDefined();
    resumed.emitMessage(JSON.stringify(protocolErrorFrame("resync_required")));
    const snapshot = session.getSnapshot();
    expect(snapshot.notices.gap).toBe(true);
    expect(snapshot.connection).toBe("reconnecting");
    harness.timers.advance(250);
    handshake(harness, 1n, [false]);
    expect(session.getSnapshot().notices.gap).toBe(true);
  });

  it("retries fresh admission refusal through the bounded ladder without a gap claim", () => {
    const harness = startSession();
    const { session, sockets } = harness;
    const socket = sockets[0]!;
    socket.emit("open");
    socket.emitMessage(JSON.stringify(protocolErrorFrame("resync_required")));
    expect(session.getSnapshot().notices.gap).toBe(false);
    expect(session.getSnapshot().connection).toBe("reconnecting");
    for (const delay of [250, 1_000, 2_000, 4_000, 8_000]) {
      harness.timers.advance(delay);
      const next = sockets[sockets.length - 1]!;
      next.emit("open");
      next.emitMessage(JSON.stringify(protocolErrorFrame("resync_required")));
    }
    const snapshot = session.getSnapshot();
    expect(snapshot.retryOffered).toBe(true);
    expect(snapshot.connection).toBe("reconnecting");
    session.retry();
    expect(session.getSnapshot().retryOffered).toBe(false);
    harness.timers.advance(250);
    handshake(harness);
  });

  it("stops retrying after exhaustion and offers an explicit Retry control", () => {
    const harness = startSession();
    const { session, sockets, timers } = harness;
    expect(session.getSnapshot().connection).toBe("connecting");
    for (const [index, delay] of [250, 1_000, 2_000, 4_000, 8_000].entries()) {
      sockets[sockets.length - 1]!.emit("close");
      timers.advance(delay);
      expect(sockets.length).toBe(index + 2);
    }
    sockets[sockets.length - 1]!.emit("close");
    const snapshot = session.getSnapshot();
    expect(snapshot.retryOffered).toBe(true);
    expect(timers.pending()).toBe(0);
  });

  it("rejects binary and invalid frames without display effects", () => {
    const harness = startSession();
    const { session, sockets } = harness;
    handshake(harness);
    const socket = sockets[0]!;
    const before = session.getSnapshot();
    socket.emitMessage(new ArrayBuffer(8));
    socket.emitMessage("not-json");
    socket.emitMessage('{"type":"unknown.thing"}');
    const event = transcriptEvent({ seq: 1n });
    event.extra = 1;
    socket.emitMessage(JSON.stringify(event));
    const after = session.getSnapshot();
    expect(after.metrics.rejectedFrames).toBe(4);
    expect(after.finals).toHaveLength(before.finals.length);
    expect(after.metrics.receivedEvents).toBe(0);
  });

  it("closes and reconnects with the cursor when the presentation queue overflows", () => {
    const harness = startSession();
    const { session, sockets, clock, timers } = harness;
    handshake(harness);
    const socket = sockets[0]!;
    expect(session.setDelay(5_000)).toBe(true);
    socket.emitMessage(JSON.stringify(statusEvent({ seq: 1n, status: "live" })));
    for (let index = 2n; index <= 130n; index += 1n) {
      socket.emitMessage(
        JSON.stringify(transcriptEvent({ seq: index, segmentId: testUuid(Number(index)), eventId: testUuid(500 + Number(index)), isFinal: true })),
      );
    }
    const snapshot = session.getSnapshot();
    expect(snapshot.notices.overflow).toBe(true);
    expect(snapshot.metrics.queuePeak).toBeLessThanOrEqual(128);
    expect(snapshot.connection).toBe("reconnecting");
    timers.advance(250);
    const resumed = sockets[sockets.length - 1]!;
    resumed.emit("open");
    const resubscribe = strictJsonParse(resumed.sent[0] ?? "{}").value;
    if (resubscribe === undefined) throw new Error("missing resubscribe frame");
    expect(resubscribe.cursor).toBeDefined();
    expect((resubscribe.cursor as Record<string, string>).next_seq).toBe("131");
    clock.advance(1);
    resumed.emitMessage(
      JSON.stringify(readyFrame({ nextSeq: 131n, cursorResumed: true })),
    );
    const after = session.getSnapshot();
    expect(after.connection).toBe("connected");
    expect(after.notices.overflow).toBe(true);
    session.dismissOverflow();
    expect(session.getSnapshot().notices.overflow).toBe(false);
  });

  it("hides text ahead of delay timers on stop, disable, delete, and failure", () => {
    for (const status of ["stopped", "failed"] as const) {
      for (const reason of [null, "ingest_disabled", "policy_disable", "session_deleted", "protocol_failed"]) {
        const harness = startSession();
        const { session, sockets, clock } = harness;
        handshake(harness);
        const socket = sockets[0]!;
        socket.emitMessage(JSON.stringify(statusEvent({ seq: 1n, status: "live" })));
        expect(session.setDelay(5_000)).toBe(true);
        socket.emitMessage(
          JSON.stringify(transcriptEvent({ seq: 2n, text: "hidden by the stop", isFinal: true })),
        );
        socket.emitMessage(JSON.stringify(statusEvent({ seq: 3n, status, reasonCode: reason })));
        const snapshot = session.getSnapshot();
        expect(snapshot.sessionStatus).toBe(status);
        expect(snapshot.finals).toHaveLength(0);
        expect(snapshot.partial).toBeNull();
        clock.advance(10_000);
        expect(session.getSnapshot().finals).toHaveLength(0);
        session.dispose();
      }
    }
  });

  it("marks incompatible protocol without retrying", () => {
    const harness = startSession();
    const { session, sockets, timers } = harness;
    const socket = sockets[0]!;
    socket.emit("open");
    socket.emitMessage(JSON.stringify(protocolErrorFrame("unsupported_minor", { retryable: false })));
    const snapshot = session.getSnapshot();
    expect(snapshot.connection).toBe("incompatible");
    expect(timers.pending()).toBe(0);
    session.retry();
    expect(session.getSnapshot().connection).toBe("incompatible");
  });

  it("suspends timers and clears text when the browser goes offline", () => {
    const online: boolean[] = [true];
    const offlineListeners: Array<() => void> = [];
    const clock = new TestClock();
    const sockets: FakeSocket[] = [];
    const timers = new ManualTimers();
    const deps: SessionDeps = {
      url: "ws://test.invalid/api/viewer/ws",
      roomId: "livecho.fixture.room",
      clock,
      environment: {
        isOnline: () => online[0] === true,
        onOnline: () => () => undefined,
        onOffline: (listener) => {
          offlineListeners.push(listener);
          return () => undefined;
        },
        onVisible: () => () => undefined,
      },
      webSocketFactory: () => {
        const socket = new FakeSocket();
        sockets.push(socket);
        return socket;
      },
      setTimeoutFn: (handler, ms) => timers.timeout(handler, ms),
      clearTimeoutFn: (handle) => timers.cancel(handle),
    };
    const session = new CaptionSession(deps);
    sockets[0]!.emit("open");
    sockets[0]!.emitMessage(JSON.stringify(readyFrame({ nextSeq: 1n })));
    sockets[0]!.emitMessage(
      JSON.stringify(transcriptEvent({ seq: 1n, text: "before offline", isFinal: true })),
    );
    expect(session.getSnapshot().finals).toHaveLength(1);
    online[0] = false;
    for (const listener of offlineListeners) listener();
    const snapshot = session.getSnapshot();
    expect(snapshot.connection).toBe("offline");
    expect(snapshot.finals).toHaveLength(0);
    expect(timers.pending()).toBe(0);
    session.dispose();
  });

  it("rejects out-of-range delay selections through the session", () => {
    const harness = startSession();
    const { session } = harness;
    expect(session.setDelay(100)).toBe(true);
    expect(session.setDelay(5_100)).toBe(false);
    expect(session.setDelay(55)).toBe(false);
    expect(session.getSnapshot().delayMs).toBe(100);
    session.dispose();
  });
});
