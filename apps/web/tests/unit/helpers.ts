import { validateModel } from "@livecho/protocol/browser";

const randomUUID = (): string => crypto.randomUUID();

export function stamp(offsetMs = 0): string {
  return new Date(Date.parse("2026-11-14T00:00:00.000Z") + offsetMs).toISOString();
}

/** Deterministic schema-valid UUIDv4 for event/segment identities in tests. */
export function testUuid(seed: number): string {
  const hex = seed.toString(16).padStart(12, "0").slice(0, 12);
  return `00000000-0000-4000-8000-${hex}`;
}

export interface TranscriptOverrides {
  seq?: bigint;
  revision?: bigint;
  eventId?: string;
  segmentId?: string;
  text?: string;
  isFinal?: boolean;
  occurredAt?: string;
  startMs?: number;
  endMs?: number;
  messageId?: string;
  sentAt?: string;
  protocolMinor?: number;
  extraField?: boolean;
}

/** Build one schema-valid transcript TimelineEventV1 for domain tests. */
export function transcriptEvent(overrides: TranscriptOverrides = {}): Record<string, unknown> {
  const eventId = overrides.eventId ?? randomUUID();
  const startMs = overrides.startMs ?? 0;
  const endMs = overrides.endMs ?? startMs + 2_000;
  const frame: Record<string, unknown> = {
    protocol: "livecho.viewer.v1",
    protocol_minor: overrides.protocolMinor ?? 0,
    message_id: overrides.messageId ?? randomUUID(),
    sent_at: overrides.sentAt ?? stamp(),
    type: "viewer.timeline_event",
    event_id: eventId,
    session_id: "3f9d0f6e-6f4a-4d8b-9fbd-4f0c0d7c1e21",
    room_id: "livecho.fixture.room",
    epoch: "1",
    seq: (overrides.seq ?? 1n).toString(),
    revision: (overrides.revision ?? 1n).toString(),
    occurred_at: overrides.occurredAt ?? stamp(),
    payload: {
      segment_id: overrides.segmentId ?? randomUUID(),
      start_ms: startMs,
      end_ms: endMs,
      text: overrides.text ?? "Fixture transcript text",
      is_final: overrides.isFinal ?? false,
    },
  };
  if (overrides.extraField) frame.extra = "forbidden";
  return frame;
}

export interface StatusOverrides {
  seq?: bigint;
  revision?: bigint;
  eventId?: string;
  status?: "starting" | "live" | "stopping" | "stopped" | "failed";
  reasonCode?: string | null;
  occurredAt?: string;
  messageId?: string;
  sentAt?: string;
}

/** Build one schema-valid session-status TimelineEventV1 for domain tests. */
export function statusEvent(overrides: StatusOverrides = {}): Record<string, unknown> {
  const payload: Record<string, unknown> = { status: overrides.status ?? "live" };
  if (overrides.reasonCode !== undefined && overrides.reasonCode !== null) {
    payload.reason_code = overrides.reasonCode;
  }
  return {
    protocol: "livecho.viewer.v1",
    protocol_minor: 0,
    message_id: overrides.messageId ?? randomUUID(),
    sent_at: overrides.sentAt ?? stamp(),
    type: "viewer.timeline_event",
    event_id: overrides.eventId ?? randomUUID(),
    session_id: "3f9d0f6e-6f4a-4d8b-9fbd-4f0c0d7c1e21",
    room_id: "livecho.fixture.room",
    epoch: "1",
    seq: (overrides.seq ?? 1n).toString(),
    revision: (overrides.revision ?? 1n).toString(),
    occurred_at: overrides.occurredAt ?? stamp(),
    payload,
  };
}

export function readyFrame(options: {
  nextSeq: bigint;
  cursorResumed?: boolean;
  sessionId?: string;
  epoch?: string;
}): Record<string, unknown> {
  return {
    protocol: "livecho.viewer.v1",
    protocol_minor: 0,
    message_id: randomUUID(),
    sent_at: stamp(),
    type: "viewer.ready",
    cursor_resumed: options.cursorResumed ?? false,
    session_id: options.sessionId ?? "3f9d0f6e-6f4a-4d8b-9fbd-4f0c0d7c1e21",
    epoch: options.epoch ?? "1",
    next_seq: options.nextSeq.toString(),
    minimum_client_version: "0.1.0",
    selected_minor: 0,
  };
}

export function assertSchemaValid(model: string, frame: Record<string, unknown>): void {
  if (validateModel(model, frame) !== "accepted") {
    throw new Error(`test frame is not schema valid: ${model}`);
  }
}

export function protocolErrorFrame(
  code: string,
  options: { retryable?: boolean; message?: string } = {},
): Record<string, unknown> {
  return {
    protocol: "livecho.viewer.v1",
    protocol_minor: 0,
    message_id: randomUUID(),
    sent_at: stamp(),
    type: "protocol.error",
    code,
    message: options.message ?? "Fixture protocol error",
    retryable: options.retryable ?? true,
  };
}

/** Injects a controllable clock; ticks are advanced by the test. */
export class TestClock {
  private current = 1_000;

  now(): number {
    return this.current;
  }

  advance(milliseconds: number): void {
    this.current += milliseconds;
  }
}
