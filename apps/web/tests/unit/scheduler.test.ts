import { describe, expect, it } from "vitest";
import {
  DELAY_MAX_MS,
  DELAY_STEP_MS,
  FINAL_ROW_LIMIT,
  MAX_DISPLAY_TEXT_BYTES,
  MAX_PENDING_BYTES,
  MAX_PENDING_MUTATIONS,
  PresentationEngine,
  isValidDelay,
  type TextMutation,
} from "../../src/protocol/scheduler";
import { TestClock } from "./helpers";

function mutation(overrides: Partial<TextMutation> = {}): TextMutation {
  return {
    seq: overrides.seq ?? 1n,
    eventId: overrides.eventId ?? "e-1",
    segmentId: overrides.segmentId ?? "s-1",
    text: overrides.text ?? "fixture",
    isFinal: overrides.isFinal ?? false,
    receivedAt: overrides.receivedAt ?? 1_000,
    byteSize: overrides.byteSize ?? 128,
  };
}

function byteSizeOf(text: string): number {
  return new TextEncoder().encode(
    JSON.stringify({ payload: { text, segment_id: "s", is_final: true } }),
  ).length;
}

describe("presentation scheduler", () => {
  it("validates the session delay range and step", () => {
    expect(isValidDelay(0)).toBe(true);
    expect(isValidDelay(DELAY_MAX_MS)).toBe(true);
    expect(isValidDelay(DELAY_MAX_MS + DELAY_STEP_MS)).toBe(false);
    expect(isValidDelay(-DELAY_STEP_MS)).toBe(false);
    expect(isValidDelay(50)).toBe(false);
    expect(isValidDelay(123.5)).toBe(false);
  });

  it("displays accepted text after the selected delay without rewriting it", () => {
    const clock = new TestClock();
    const engine = new PresentationEngine(clock);
    expect(engine.enqueueText(mutation({ text: "hello", isFinal: true }))).toEqual({ ok: true });
    expect(engine.finalRows).toHaveLength(1);
    expect(engine.finalRows[0]!.text).toBe("hello");
    expect(engine.finalRows[0]!.seq).toBe(1n);

    engine.setDelay(2_000);
    expect(engine.enqueueText(mutation({ seq: 2n, eventId: "e-2", segmentId: "s-2", text: "later", isFinal: true }))).toEqual({ ok: true });
    expect(engine.finalRows.map((row) => row.text)).toEqual(["hello"]);
    clock.advance(2_000);
    engine.drain();
    expect(engine.finalRows.map((row) => row.text)).toEqual(["hello", "later"]);
  });

  it("replaces the provisional row in place and never shows a partial after its final", () => {
    const engine = new PresentationEngine(new TestClock());
    engine.enqueueText(mutation({ seq: 1n, eventId: "e", segmentId: "s", text: "par one" }));
    expect(engine.partial?.text).toBe("par one");
    engine.enqueueText(mutation({ seq: 2n, eventId: "e", segmentId: "s", text: "par two" }));
    expect(engine.partial?.text).toBe("par two");
    expect(engine.partial?.seq).toBe(2n);
    engine.enqueueText(mutation({ seq: 3n, eventId: "e", segmentId: "s", text: "final", isFinal: true }));
    expect(engine.partial).toBeNull();
    expect(engine.finalRows.map((row) => row.text)).toEqual(["final"]);
    // A later partial for the same finalized segment never reappears.
    engine.enqueueText(mutation({ seq: 4n, eventId: "e", segmentId: "s", text: "ghost" }));
    expect(engine.partial).toBeNull();
  });

  it("coalesces pending partial revisions for the same row", () => {
    const engine = new PresentationEngine(new TestClock());
    engine.setDelay(5_000);
    engine.enqueueText(mutation({ seq: 1n, eventId: "e", segmentId: "s", text: "first", receivedAt: 1_000 }));
    engine.enqueueText(mutation({ seq: 2n, eventId: "e", segmentId: "s", text: "second", receivedAt: 1_100 }));
    // Lowering the delay makes the retained latest revision due in order.
    const clock = new TestClock();
    engine.setDelay(0);
    clock.advance(200);
    engine.drain(clock.now());
    expect(engine.partial?.text).toBe("second");
  });

  it("retains at most four recent final rows, evicting the oldest first", () => {
    const engine = new PresentationEngine(new TestClock());
    for (let index = 1n; index <= 6n; index += 1n) {
      engine.enqueueText(
        mutation({ seq: index, eventId: `e-${index}`, segmentId: `s-${index}`, text: `row ${index}`, isFinal: true }),
      );
    }
    expect(engine.finalRows.map((row) => row.text)).toEqual(["row 3", "row 4", "row 5", "row 6"]);
    expect(FINAL_ROW_LIMIT).toBe(4);
  });

  it("triggers overflow at either queue limit and clears text", () => {
    const engine = new PresentationEngine(new TestClock());
    engine.setDelay(5_000);
    for (let index = 1n; index <= MAX_PENDING_MUTATIONS; index += 1n) {
      expect(
        engine.enqueueText(mutation({ seq: index, eventId: `e-${index}`, segmentId: `s-${index}`, receivedAt: 1_000 })),
      ).toEqual({ ok: true });
    }
    expect(engine.pendingPeak).toBe(MAX_PENDING_MUTATIONS);
    const overflow = engine.enqueueText(
      mutation({ seq: 129n, eventId: "e-129", segmentId: "s-129", receivedAt: 1_000 }),
    );
    expect(overflow).toEqual({ ok: false, overflow: true });
    expect(engine.finalRows).toHaveLength(0);
    expect(engine.partial).toBeNull();
    expect(engine.notices.overflow).toBe(true);
    // Admission stops after overflow until a new handshake resumes it.
    expect(engine.enqueueText(mutation({ seq: 129n, eventId: "e-129b", segmentId: "s-129b" }))).toEqual({ ok: true });
    expect(engine.partial).toBeNull();
    engine.resumeAdmission();
    engine.setDelay(0);
    engine.enqueueText(mutation({ seq: 129n, eventId: "e-129c", segmentId: "s-129c" }));
    expect(engine.partial?.text).toBe("fixture");
  });

  it("counts queue bytes before enqueue", () => {
    const engine = new PresentationEngine(new TestClock());
    engine.setDelay(5_000);
    const big = MAX_PENDING_BYTES - 1_000;
    expect(engine.enqueueText(mutation({ seq: 1n, eventId: "e-1", segmentId: "s-1", byteSize: big, receivedAt: 1_000 }))).toEqual({ ok: true });
    expect(engine.enqueueText(mutation({ seq: 2n, eventId: "e-2", segmentId: "s-2", byteSize: 2_000, receivedAt: 1_000 }))).toEqual({
      ok: false,
      overflow: true,
    });
  });

  it("clears the view with a local overflow gap when a whole row cannot fit", () => {
    const engine = new PresentationEngine(new TestClock());
    engine.enqueueText(
      mutation({ seq: 1n, eventId: "e-1", segmentId: "s-1", text: "keep", isFinal: true }),
    );
    expect(engine.finalRows).toHaveLength(1);
    const huge = "x".repeat(MAX_DISPLAY_TEXT_BYTES + 1);
    engine.enqueueText(mutation({ seq: 2n, eventId: "e-2", segmentId: "s-2", text: huge, isFinal: true }));
    expect(engine.finalRows).toHaveLength(0);
    expect(engine.partial).toBeNull();
    expect(engine.notices.overflow).toBe(true);
  });

  it("keeps display text within the byte budget, evicting oldest finals first", () => {
    const engine = new PresentationEngine(new TestClock());
    const unit = 30_000;
    for (let index = 1n; index <= 6n; index += 1n) {
      engine.enqueueText(
        mutation({
          seq: index,
          eventId: `e-${index}`,
          segmentId: `s-${index}`,
          text: "y".repeat(unit),
          isFinal: true,
        }),
      );
    }
    // Four rows of 30,000 bytes stay; a fifth would exceed 131,072.
    const total = engine.finalRows.reduce((sum, row) => sum + row.byteSize, 0);
    expect(total).toBeLessThanOrEqual(MAX_DISPLAY_TEXT_BYTES);
    expect(engine.finalRows.map((row) => row.seq)).toEqual([3n, 4n, 5n, 6n]);
  });

  it("blocks all presentation on terminal status and clears immediately", () => {
    const engine = new PresentationEngine(new TestClock());
    engine.setDelay(5_000);
    engine.enqueueText(mutation({ seq: 1n, eventId: "e-1", segmentId: "s-1", receivedAt: 1_000 }));
    const { droppedUndisplayed } = engine.blockAndClearText();
    expect(droppedUndisplayed).toBe(true);
    expect(engine.blocked).toBe(true);
    // Delayed mutations can never reappear after the block.
    engine.resumeAdmission();
    engine.enqueueText(mutation({ seq: 2n, eventId: "e-2", segmentId: "s-2" }));
    expect(engine.partial).toBeNull();
    expect(engine.setDelay(0)).toBe(true);
    engine.drain();
    expect(engine.partial).toBeNull();
  });

  it("never hides a displayed final when the delay increases", () => {
    const engine = new PresentationEngine(new TestClock());
    engine.enqueueText(mutation({ seq: 1n, eventId: "e-1", segmentId: "s-1", text: "shown", isFinal: true }));
    expect(engine.finalRows).toHaveLength(1);
    expect(engine.setDelay(DELAY_MAX_MS)).toBe(true);
    expect(engine.finalRows).toHaveLength(1);
  });

  it("reports when accepted-but-undisplayed text was cleared", () => {
    const engine = new PresentationEngine(new TestClock());
    expect(engine.clearTextAndQueue().droppedUndisplayed).toBe(false);
    engine.setDelay(5_000);
    engine.enqueueText(mutation({ seq: 1n, eventId: "e-1", segmentId: "s-1", receivedAt: 1_000 }));
    expect(engine.clearTextAndQueue().droppedUndisplayed).toBe(true);
  });

  it("measures receive-to-render lag on the injected monotonic clock", () => {
    const clock = new TestClock();
    const engine = new PresentationEngine(clock);
    engine.setDelay(100);
    engine.enqueueText(mutation({ seq: 1n, eventId: "e-1", segmentId: "s-1", text: "lag", isFinal: true, receivedAt: 1_000, byteSize: byteSizeOf("lag") }));
    clock.advance(400);
    engine.drain();
    expect(engine.appliedMutations).toBe(1);
    expect(engine.renderLagMaxMs).toBe(300);
  });
});
