import { describe, expect, it } from "vitest";
import { canonicalJson, strictJsonParse } from "@livecho/protocol/browser";
import { ViewerReceiveDomain, isBlockingStatus } from "../../src/protocol/domain";
import { assertSchemaValid, readyFrame, statusEvent, testUuid, transcriptEvent } from "./helpers";

function freshDomain(atSeq = 1n): ViewerReceiveDomain {
  const domain = new ViewerReceiveDomain();
  const ready = domain.acceptReady(readyFrame({ nextSeq: atSeq }) as never, null);
  expect(ready.outcome).toBe("fresh");
  return domain;
}

describe("viewer receive domain", () => {
  it("accepts a fresh ready and exposes an exact cursor", () => {
    const domain = new ViewerReceiveDomain();
    const assessment = domain.acceptReady(readyFrame({ nextSeq: 42n }) as never, null);
    expect(assessment).toEqual({ outcome: "fresh", resetsPresentation: true });
    expect(domain.cursor()).toEqual({
      session_id: "3f9d0f6e-6f4a-4d8b-9fbd-4f0c0d7c1e21",
      epoch: "1",
      next_seq: "42",
    });
  });

  it("rejects a fresh ready that claims cursor resume", () => {
    const domain = new ViewerReceiveDomain();
    const assessment = domain.acceptReady(
      readyFrame({ nextSeq: 1n, cursorResumed: true }) as never,
      null,
    );
    expect(assessment.outcome).toBe("invalid");
  });

  it("accepts a resume only for the same session, epoch, and next sequence", () => {
    const domain = freshDomain();
    domain.acceptEvent(statusEvent({ seq: 1n, status: "live" }) as never);
    domain.acceptEvent(transcriptEvent({ seq: 2n, isFinal: true }) as never);
    const cursor = domain.cursor()!;
    expect(cursor.next_seq).toBe("3");

    expect(domain.acceptReady(readyFrame({ nextSeq: 3n, cursorResumed: true }) as never, cursor).outcome).toBe("resumed");
    expect(
      domain.acceptReady(
        readyFrame({ nextSeq: 3n, cursorResumed: true, sessionId: "11111111-2222-4333-8444-555555555555" }) as never,
        cursor,
      ).outcome,
    ).toBe("invalid");
    expect(
      domain.acceptReady(readyFrame({ nextSeq: 3n, cursorResumed: true, epoch: "2" }) as never, cursor).outcome,
    ).toBe("invalid");
    expect(domain.acceptReady(readyFrame({ nextSeq: 4n, cursorResumed: true }) as never, cursor).outcome).toBe(
      "invalid",
    );
    expect(domain.acceptReady(readyFrame({ nextSeq: 3n, cursorResumed: false }) as never, cursor).outcome).toBe(
      "invalid",
    );
  });

  it("accepts exact-next events and advances with bigint identities", () => {
    const domain = freshDomain(9_007_199_254_740_993n);
    const event = transcriptEvent({ seq: 9_007_199_254_740_993n, isFinal: false });
    assertSchemaValid("TimelineEventV1", event);
    const outcome = domain.acceptEvent(event as never);
    expect(outcome).toMatchObject({ outcome: "accepted" });
    expect(domain.nextExpectedSeq).toBe(9_007_199_254_740_994n);
  });

  it("treats an in-window replay of the identical frame as a duplicate", () => {
    const domain = freshDomain();
    const event = transcriptEvent({ seq: 1n, isFinal: true });
    expect(domain.acceptEvent(event as never).outcome).toBe("accepted");
    expect(domain.acceptEvent(event as never).outcome).toBe("duplicate");
  });

  it("treats changed content at an in-window position as a conflict without display", () => {
    const domain = freshDomain();
    const event = transcriptEvent({ seq: 1n, isFinal: true, text: "first" });
    expect(domain.acceptEvent(event as never).outcome).toBe("accepted");
    const outcome = domain.acceptEvent(
      transcriptEvent({ seq: 1n, isFinal: true, text: "changed" }) as never,
    );
    expect(outcome).toEqual({ outcome: "rejected", code: "seq_conflict", resync: false });
  });

  it("rejects a sequence gap without advancing the cursor", () => {
    const domain = freshDomain();
    const outcome = domain.acceptEvent(transcriptEvent({ seq: 3n }) as never);
    expect(outcome).toEqual({ outcome: "rejected", code: "seq_gap", resync: true });
    expect(domain.nextExpectedSeq).toBe(1n);
  });

  it("rejects a replay below the 256-record window with resync", () => {
    const domain = freshDomain();
    const frames: Array<ReturnType<typeof transcriptEvent>> = [];
    for (let index = 0n; index < 257n; index += 1n) {
      const frame = transcriptEvent({
        seq: index + 1n,
        isFinal: true,
        segmentId: testUuid(Number(index)),
      });
      frames.push(frame);
      const outcome = domain.acceptEvent(frame as never);
      expect(outcome.outcome).toBe("accepted");
    }
    expect(domain.nextExpectedSeq).toBe(258n);
    // Window now retains sequences 2..257; replaying 1 is below the window.
    const outcome = domain.acceptEvent(transcriptEvent({ seq: 1n, isFinal: true }) as never);
    expect(outcome).toEqual({ outcome: "rejected", code: "resync_required", resync: true });
    // An exact replay of 2 is still an in-window duplicate.
    const inWindow = domain.acceptEvent(frames[1]! as never);
    expect(inWindow.outcome).toBe("duplicate");
  });

  it("applies revision precedence exactly", () => {
    const domain = freshDomain();
    const eventId = "0f0b5c9a-9c8f-4f9e-b7a3-6c0d6a5b4e10";
    const segmentId = "1e2d3c4b-5a69-4788-96a5-7b6c5d4e3f20";
    const occurredAt = "2026-11-14T00:00:01.000Z";
    expect(
      domain.acceptEvent(
        transcriptEvent({ seq: 1n, revision: 1n, eventId, segmentId, occurredAt, isFinal: false, text: "one" }) as never,
      ).outcome,
    ).toBe("accepted");
    // Revision replay at the next sequence with the same content is a no-op.
    expect(
      domain.acceptEvent(
        transcriptEvent({ seq: 2n, revision: 1n, eventId, segmentId, occurredAt, isFinal: false, text: "one" }) as never,
      ).outcome,
    ).toBe("duplicate");
    // A jump of more than one is a gap.
    expect(
      domain.acceptEvent(
        transcriptEvent({ seq: 3n, revision: 3n, eventId, segmentId, occurredAt, isFinal: false, text: "three" }) as never,
      ),
    ).toEqual({ outcome: "rejected", code: "revision_gap", resync: false });
    // Immutable bounds cannot move.
    expect(
      domain.acceptEvent(
        transcriptEvent({ seq: 3n, revision: 2n, eventId, segmentId, occurredAt: "2026-11-14T09:00:01.000Z", isFinal: false, text: "moved" }) as never,
      ),
    ).toEqual({ outcome: "rejected", code: "revision_immutable", resync: false });
    // The exact next revision with stable bounds is accepted.
    expect(
      domain.acceptEvent(
        transcriptEvent({ seq: 3n, revision: 2n, eventId, segmentId, occurredAt, isFinal: true, text: "final text" }) as never,
      ).outcome,
    ).toBe("accepted");
    // The object is final: any further revision is object_final.
    expect(
      domain.acceptEvent(
        transcriptEvent({ seq: 4n, revision: 3n, eventId, segmentId, occurredAt, isFinal: true, text: "no" }) as never,
      ),
    ).toEqual({ outcome: "rejected", code: "object_final", resync: false });
    // A lower revision is stale.
    expect(
      domain.acceptEvent(
        transcriptEvent({ seq: 4n, revision: 1n, eventId, segmentId, occurredAt, isFinal: true, text: "stale" }) as never,
      ),
    ).toEqual({ outcome: "rejected", code: "revision_stale", resync: false });
  });

  it("rejects a previously unseen identity that does not start at revision 1", () => {
    const domain = freshDomain();
    const outcome = domain.acceptEvent(transcriptEvent({ seq: 1n, revision: 2n }) as never);
    expect(outcome).toEqual({ outcome: "rejected", code: "revision_gap", resync: false });
  });

  it("keeps existing identities valid at the 4,096 capacity and rejects identity 4,097", () => {
    const domain = freshDomain();
    for (let index = 0n; index < 4_096n; index += 1n) {
      const outcome = domain.acceptEvent(
        transcriptEvent({ seq: index + 1n, revision: 1n, isFinal: true, eventId: testUuid(2000 + Number(index)), segmentId: testUuid(3000 + Number(index)) }) as never,
      );
      expect(outcome.outcome).toBe("accepted");
    }
    // An existing identity still accepts a valid duplicate at capacity.
    expect(
      domain.acceptEvent(
        transcriptEvent({ seq: 4_097n, revision: 1n, isFinal: true, eventId: testUuid(2000), segmentId: testUuid(3000), text: "Fixture transcript text" }) as never,
      ).outcome,
    ).toBe("duplicate");
    // Only the new 4,097th identity triggers capacity rejection and resync.
    expect(
      domain.acceptEvent(transcriptEvent({ seq: 4_098n, revision: 1n, eventId: testUuid(2000 + 4096), segmentId: testUuid(3000 + 4096) }) as never),
    ).toEqual({ outcome: "rejected", code: "revision_capacity_exceeded", resync: true });
    expect(domain.nextExpectedSeq).toBe(4_098n);
  });

  it("requires the binding session and epoch and never changes epoch from an event", () => {
    const domain = freshDomain();
    expect(
      domain.acceptEvent(
        transcriptEvent({ seq: 1n, eventId: testUuid(700), segmentId: testUuid(701), occurredAt: "2026-11-14T00:00:01.000Z", isFinal: true, text: "same id" }) as never,
      ).outcome,
    ).toBe("accepted");
    // Same event id at a higher epoch: not authority to change epoch.
    const higher = transcriptEvent({ seq: 2n, eventId: testUuid(700), segmentId: testUuid(701), isFinal: true, text: "same id" });
    higher.epoch = "2";
    assertSchemaValid("TimelineEventV1", higher);
    expect(domain.acceptEvent(higher as never)).toEqual({
      outcome: "rejected",
      code: "epoch_unknown",
      resync: true,
    });
    // A lower epoch is stale: bind to epoch 2 first, then receive epoch 1.
    const second = new ViewerReceiveDomain();
    expect(second.acceptReady(readyFrame({ nextSeq: 1n, epoch: "2" }) as never, null).outcome).toBe("fresh");
    const lower = transcriptEvent({ seq: 1n, eventId: testUuid(702), segmentId: testUuid(703), isFinal: true });
    lower.epoch = "1";
    assertSchemaValid("TimelineEventV1", lower);
    expect(second.acceptEvent(lower as never)).toEqual({
      outcome: "rejected",
      code: "epoch_stale",
      resync: true,
    });
    const foreign = transcriptEvent({ seq: 2n, isFinal: true });
    foreign.session_id = "11111111-2222-4333-8444-555555555555";
    assertSchemaValid("TimelineEventV1", foreign);
    expect(domain.acceptEvent(foreign as never)).toEqual({
      outcome: "rejected",
      code: "binding_mismatch",
      resync: true,
    });
  });

  it("records terminal statuses and blocking reasons", () => {
    const domain = freshDomain();
    expect(isBlockingStatus("live", null)).toBe(false);
    expect(isBlockingStatus("stopping", null)).toBe(true);
    expect(isBlockingStatus("stopped", "ingest_disabled")).toBe(true);
    expect(isBlockingStatus("live", "no_compatible_worker")).toBe(false);

    domain.acceptEvent(statusEvent({ seq: 1n, status: "live" }) as never);
    expect(domain.blocked).toBe(false);
    domain.acceptEvent(statusEvent({ seq: 2n, status: "stopped", reasonCode: "policy_disable" }) as never);
    expect(domain.blocked).toBe(true);
    expect(domain.status).toBe("stopped");
    expect(domain.statusReason).toBe("policy_disable");
  });

  it("rejects schema-invalid and unknown-field events before display", () => {
    const domain = freshDomain();
    const invalid = transcriptEvent({ seq: 1n, extraField: true });
    expect(domain.acceptEvent(invalid as never)).toEqual({
      outcome: "rejected",
      code: "unknown_field",
      resync: false,
    });
    // Non-canonical JSON text is rejected by the strict parser shared entry.
    const parsed = strictJsonParse('{"a":1,"a":2}');
    expect(parsed.code).toBe("duplicate_key");
    expect(canonicalJson({ b: 2, a: 1 })).toBe('{"a":1,"b":2}');
  });
});
