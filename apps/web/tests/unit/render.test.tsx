import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { RoomPanel } from "../../src/ui/App";
import type { CaptionSession, SessionSnapshot } from "../../src/protocol/session";
import type { ConnectionState } from "../../src/protocol/labels";

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
});

function snapshot(overrides: Partial<SessionSnapshot> = {}): SessionSnapshot {
  return {
    connection: "connected",
    sessionStatus: "live",
    statusReason: null,
    delayMs: 0,
    partial: null,
    finals: [],
    notices: { gap: false, overflow: false, undisplayed: false },
    retryOffered: false,
    metrics: {
      receivedEvents: 0,
      duplicates: 0,
      rejectedFrames: 0,
      resyncs: 0,
      appliedMutations: 0,
      renderLagMaxMs: 0,
      queuePeak: 0,
      queueBytesPeak: 0,
    },
    ...overrides,
  };
}

function row(seq: bigint, eventId: string, text: string) {
  return { seq, eventId, segmentId: `segment-${seq}`, text, byteSize: text.length };
}

function stubSession(current: SessionSnapshot): {
  session: CaptionSession;
  calls: { setDelay: number[] };
} {
  const calls = { setDelay: [] as number[] };
  const listeners = new Set<() => void>();
  const session = {
    engine: {},
    getSnapshot: () => current,
    subscribe: (listener: () => void) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    setDelay: (ms: number) => {
      calls.setDelay.push(ms);
      return true;
    },
    dismissGap: () => undefined,
    dismissOverflow: () => undefined,
    dismissUndisplayed: () => undefined,
    retry: () => undefined,
    dispose: () => undefined,
  } as unknown as CaptionSession;
  return { session, calls };
}

const container = document.createElement("div");
let root: Root | null = null;

function render(element: React.JSX.Element): void {
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => {
    root!.render(element);
  });
}

afterEach(() => {
  act(() => {
    root?.unmount();
  });
  container.remove();
});

describe("room view rendering", () => {
  it("renders subtitles as plain text, never markup", () => {
    const hostile =
      '<img src=x onerror="alert(1)"><script>window.pwned=1</script>&<b>bold</b>';
    const { session } = stubSession(
      snapshot({
        partial: row(4n, "event-4", hostile),
        finals: [row(3n, "event-3", hostile)],
      }),
    );
    render(<RoomPanel session={session} snapshot={session.getSnapshot()} roomId="livecho.fixture.room" />);
    expect(container.querySelectorAll("img, script, b")).toHaveLength(0);
    const partialRow = container.querySelector('[data-testid="partial-row"]')!;
    expect(partialRow.textContent).toContain(hostile);
    expect((window as { pwned?: number }).pwned).toBeUndefined();
  });

  it("preserves Unicode and line breaks and labels provisional text", () => {
    const text = "第一行\nsecond line\u00a0with nbsp";
    const { session } = stubSession(snapshot({ partial: row(1n, "event-1", text) }));
    render(<RoomPanel session={session} snapshot={session.getSnapshot()} roomId="livecho.fixture.room" />);
    const partialRow = container.querySelector('[data-testid="partial-row"]')!;
    expect(partialRow.textContent).toContain("Provisional");
    expect(partialRow.textContent).toContain(text);
  });

  it("shows at most four final rows and the partial availability truth", () => {
    const { session } = stubSession(
      snapshot({
        finals: [1n, 2n, 3n, 4n].map((seq) => row(seq, `event-${seq}`, `row ${seq}`)),
        partial: row(5n, "event-5", "current"),
      }),
    );
    render(<RoomPanel session={session} snapshot={session.getSnapshot()} roomId="livecho.fixture.room" />);
    expect(container.querySelectorAll(".final")).toHaveLength(4);
    expect(container.querySelector('[data-testid="partial-availability"]')!.textContent).toContain(
      "real-worker partial output remains unconfirmed",
    );
  });

  it("renders dismissible notices and the retry offer", () => {
    const { session } = stubSession(
      snapshot({
        connection: "reconnecting" as ConnectionState,
        notices: { gap: true, overflow: true, undisplayed: true },
        retryOffered: true,
        sessionStatus: null,
      }),
    );
    render(<RoomPanel session={session} snapshot={session.getSnapshot()} roomId="livecho.fixture.room" />);
    expect(container.querySelector('[data-testid="gap-notice"]')!.textContent).toContain(
      "Subtitle gap; continuing from the current position",
    );
    expect(container.querySelector('[data-testid="overflow-notice"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="undisplayed-notice"]')).not.toBeNull();
    const dismissButtons = container.querySelectorAll("button");
    expect(dismissButtons.length).toBeGreaterThanOrEqual(4);
  });

  it("offers a keyboard-operable delay control bound to the session", () => {
    const { session, calls } = stubSession(snapshot({ delayMs: 300 }));
    render(<RoomPanel session={session} snapshot={session.getSnapshot()} roomId="livecho.fixture.room" />);
    const input = container.querySelector("#display-delay") as HTMLInputElement;
    expect(input).not.toBeNull();
    expect(input.type).toBe("range");
    expect(input.min).toBe("0");
    expect(input.max).toBe("5000");
    expect(input.step).toBe("100");
    expect(input.value).toBe("300");
    const output = container.querySelector('[data-testid="delay-value"]')!;
    expect(output.textContent).toBe("300 ms");
    input.focus();
    const nativeSetter = Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    )!.set!;
    act(() => {
      nativeSetter.call(input, "400");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    expect(calls.setDelay.at(-1)).toBe(400);
  });

  it("shows the offline notice when the browser is offline", () => {
    const { session } = stubSession(
      snapshot({ connection: "offline" as ConnectionState, sessionStatus: null }),
    );
    render(<RoomPanel session={session} snapshot={session.getSnapshot()} roomId="livecho.fixture.room" />);
    expect(container.querySelector('[data-testid="offline-notice"]')!.textContent).toBe(
      "Offline; subtitles unavailable",
    );
  });

  it("never writes transcript data to browser storage", () => {
    const { session } = stubSession(
      snapshot({ finals: [row(1n, "event-1", "storage probe")] }),
    );
    render(<RoomPanel session={session} snapshot={session.getSnapshot()} roomId="livecho.fixture.room" />);
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    expect(container.querySelector('[data-testid="final-list"]')!.textContent).toContain(
      "storage probe",
    );
  });
});
