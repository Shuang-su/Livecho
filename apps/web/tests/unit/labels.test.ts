import { describe, expect, it } from "vitest";
import { reasonLabel, STATUS_LABELS, CONNECTION_LABELS } from "../../src/protocol/labels";
import { isBlockingStatus } from "../../src/protocol/domain";
import { resolveRequestedRoom } from "../../src/config";

describe("safe status labels", () => {
  it("maps the accepted public reason codes only", () => {
    expect(reasonLabel("no_compatible_worker")).toBe("No compatible worker");
    expect(reasonLabel("ingest_disabled")).toBe("Ingest disabled");
    expect(reasonLabel("policy_disable")).toBe("Disabled by policy");
    expect(reasonLabel("session_deleted")).toBe("Session deleted");
    expect(reasonLabel("worker_failed")).toBe("Worker failure");
    expect(reasonLabel("source_failed")).toBe("Source failure");
    expect(reasonLabel("protocol_failed")).toBe("Protocol failure");
    expect(reasonLabel(null)).toBeNull();
  });

  it("renders a generic label for unknown safe reasons and never server text", () => {
    expect(reasonLabel("something_new")).toBe("Status changed");
    expect(reasonLabel("worker crashed on host gpu-07")).toBe("Status changed");
  });

  it("labels all connection and session states", () => {
    expect(CONNECTION_LABELS.incompatible).toBe("Incompatible");
    expect(STATUS_LABELS.starting).toContain("Waiting");
    expect(STATUS_LABELS.live).toBe("Live");
  });

  it("blocks presentation exactly for terminal statuses and disable reasons", () => {
    expect(isBlockingStatus("stopping", null)).toBe(true);
    expect(isBlockingStatus("stopped", null)).toBe(true);
    expect(isBlockingStatus("failed", null)).toBe(true);
    expect(isBlockingStatus("starting", "ingest_disabled")).toBe(true);
    expect(isBlockingStatus("live", "no_compatible_worker")).toBe(false);
    expect(isBlockingStatus("live", null)).toBe(false);
  });
});

describe("room route selection", () => {
  it("accepts the configured room or no route parameter", () => {
    expect(resolveRequestedRoom("/", "livecho.fixture.room")).toEqual({
      ok: true,
      roomId: "livecho.fixture.room",
    });
    expect(resolveRequestedRoom("/r/livecho.fixture.room", "livecho.fixture.room")).toEqual({
      ok: true,
      roomId: "livecho.fixture.room",
    });
  });

  it("refuses other rooms, URLs, and invalid identifiers", () => {
    expect(resolveRequestedRoom("/r/other.room", "livecho.fixture.room").ok).toBe(false);
    expect(resolveRequestedRoom("/r/livecho.fixture.room/extra", "livecho.fixture.room").ok).toBe(false);
    expect(
      resolveRequestedRoom("/r/https%3A%2F%2Fexample.invalid%2Fwatch", "livecho.fixture.room").ok,
    ).toBe(false);
    expect(resolveRequestedRoom("/r/Room", "livecho.fixture.room").ok).toBe(false);
  });
});
