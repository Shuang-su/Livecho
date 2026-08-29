import { Buffer } from "node:buffer";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import {
  Ajv2020,
  type AnySchema,
  type ErrorObject,
  type ValidateFunction,
} from "ajv/dist/2020.js";
import canonicalize from "canonicalize";

export const WORKER_PROTOCOL = "livecho.worker.v1" as const;
export const VIEWER_PROTOCOL = "livecho.viewer.v1" as const;
export const PROTOCOL_MINOR = 0 as const;
export const MAX_CONTROL_BYTES = 65_536;

export type StableCode =
  | "accepted"
  | "malformed_json"
  | "duplicate_key"
  | "unknown_field"
  | "schema_invalid"
  | "control_frame_too_large"
  | "unknown_major"
  | "unsupported_minor"
  | "worker_version_too_old"
  | "capability_required"
  | "manifest_not_allowed"
  | "lease_unknown"
  | "lease_expired"
  | "lease_closed"
  | "binding_mismatch"
  | "epoch_stale"
  | "epoch_unknown"
  | "seq_duplicate"
  | "seq_conflict"
  | "seq_gap"
  | "revision_duplicate"
  | "cancel_duplicate"
  | "revision_conflict"
  | "revision_stale"
  | "revision_gap"
  | "revision_immutable"
  | "revision_capacity_exceeded"
  | "cancel_conflict"
  | "object_final"
  | "resync_required"
  | "binary_header_invalid"
  | "binary_frame_too_large"
  | "audio_pts_invalid"
  | "audio_budget_exceeded";

export interface GoldenCaseV1 {
  case_id: string;
  model: string;
  expect: "accepted" | "rejected";
  code: StableCode;
  wire?: Record<string, unknown>;
  raw_text?: string;
  binary_header?: Record<string, unknown>;
}

const PUBLIC_MODELS = [
  "AudioFormatV1",
  "HeartbeatV1",
  "LeaseCancelV1",
  "LeaseV1",
  "ModelManifestRefV1",
  "ProtocolAckV1",
  "ProtocolErrorV1",
  "SessionStatusTimelinePayloadV1",
  "TimelineEventV1",
  "TranscriptSegmentV1",
  "TranscriptTimelinePayloadV1",
  "ViewerCursorV1",
  "ViewerReadyV1",
  "ViewerSubscribeV1",
  "WorkerHelloV1",
  "WorkerResumeV1",
  "WorkerStatsV1",
  "WorkerWelcomeV1",
] as const;

const WORKER_MODELS = new Set([
  "HeartbeatV1",
  "LeaseCancelV1",
  "LeaseV1",
  "WorkerHelloV1",
  "WorkerStatsV1",
  "WorkerWelcomeV1",
  "TranscriptSegmentV1",
]);
const VIEWER_MODELS = new Set([
  "TimelineEventV1",
  "ViewerReadyV1",
  "ViewerSubscribeV1",
]);
const SHARED_ENVELOPE_MODELS = new Set(["ProtocolAckV1", "ProtocolErrorV1"]);
const publicModelSet = new Set<string>(PUBLIC_MODELS);
const ajv = new Ajv2020({
  allErrors: true,
  formats: {
    "date-time": validateCanonicalTimestamp,
    "uint64-decimal": validateUint64Decimal,
    uuid: validateUuidV4,
  },
  strict: true,
  validateFormats: true,
});
const validators = new Map<string, ValidateFunction>();

for (const model of PUBLIC_MODELS) {
  const path = new URL(`../schema/${model}.schema.json`, import.meta.url);
  const schema = JSON.parse(readFileSync(path, "utf8")) as AnySchema;
  validators.set(model, ajv.compile(schema));
}

class DuplicateKeyError extends Error {}

function validateCanonicalTimestamp(value: string): boolean {
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$/u.test(value)) {
    return false;
  }
  if (value.startsWith("0000-")) return false;
  const parsed = new Date(value);
  return !Number.isNaN(parsed.valueOf()) && parsed.toISOString() === value;
}

function validateUint64Decimal(value: string): boolean {
  if (!/^(?:0|[1-9][0-9]{0,19})$/u.test(value)) return false;
  try {
    return BigInt(value) <= 18_446_744_073_709_551_615n;
  } catch {
    return false;
  }
}

function validateUuidV4(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/u.test(
    value,
  );
}

function scanJson(text: string): void {
  let index = 0;
  const whitespace = /\s/u;

  const skipWhitespace = (): void => {
    while (index < text.length && whitespace.test(text[index] ?? "")) index += 1;
  };
  const parseStringToken = (): string => {
    const start = index;
    if (text[index] !== '"') throw new SyntaxError("expected string");
    index += 1;
    while (index < text.length) {
      const character = text[index];
      if (character === '"') {
        index += 1;
        return JSON.parse(text.slice(start, index)) as string;
      }
      if (character === "\\") index += 2;
      else index += 1;
    }
    throw new SyntaxError("unterminated string");
  };
  const parseValue = (): void => {
    skipWhitespace();
    const character = text[index];
    if (character === "{") {
      index += 1;
      const keys = new Set<string>();
      skipWhitespace();
      if (text[index] === "}") {
        index += 1;
        return;
      }
      while (true) {
        skipWhitespace();
        const key = parseStringToken();
        if (keys.has(key)) throw new DuplicateKeyError();
        keys.add(key);
        skipWhitespace();
        if (text[index] !== ":") throw new SyntaxError("expected colon");
        index += 1;
        parseValue();
        skipWhitespace();
        if (text[index] === "}") {
          index += 1;
          return;
        }
        if (text[index] !== ",") throw new SyntaxError("expected comma");
        index += 1;
      }
    }
    if (character === "[") {
      index += 1;
      skipWhitespace();
      if (text[index] === "]") {
        index += 1;
        return;
      }
      while (true) {
        parseValue();
        skipWhitespace();
        if (text[index] === "]") {
          index += 1;
          return;
        }
        if (text[index] !== ",") throw new SyntaxError("expected comma");
        index += 1;
      }
    }
    if (character === '"') {
      parseStringToken();
      return;
    }
    const rest = text.slice(index);
    const token = /^(?:true|false|null|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)/u.exec(
      rest,
    )?.[0];
    if (!token) throw new SyntaxError("invalid value");
    index += token.length;
  };

  parseValue();
  skipWhitespace();
  if (index !== text.length) throw new SyntaxError("trailing input");
}

export function strictJsonParse(raw: string):
  | { code: "accepted"; value: Record<string, unknown> }
  | { code: StableCode; value?: never } {
  if (Buffer.byteLength(raw, "utf8") > MAX_CONTROL_BYTES) {
    return { code: "control_frame_too_large" };
  }
  try {
    scanJson(raw);
    const value: unknown = JSON.parse(raw);
    if (value === null || Array.isArray(value) || typeof value !== "object") {
      return { code: "schema_invalid" };
    }
    return { code: "accepted", value: value as Record<string, unknown> };
  } catch (error) {
    return { code: error instanceof DuplicateKeyError ? "duplicate_key" : "malformed_json" };
  }
}

export function canonicalJson(value: unknown): string {
  const result = canonicalize(value);
  if (result === undefined) throw new TypeError("value is not RFC 8785 canonicalizable");
  return result;
}

function digest(value: unknown): string {
  return createHash("sha256").update(canonicalJson(value), "utf8").digest("hex");
}

function classifySchemaErrors(errors: ErrorObject[] | null | undefined): StableCode {
  if (errors?.some((error) => error.keyword === "additionalProperties")) return "unknown_field";
  if (
    errors?.some(
      (error) =>
        error.instancePath.startsWith("/capabilities") ||
        (error.keyword === "required" && error.params.missingProperty === "capabilities"),
    )
  ) {
    return "capability_required";
  }
  return "schema_invalid";
}

function precheckVersion(model: string, value: Record<string, unknown>): StableCode | undefined {
  const allowed = WORKER_MODELS.has(model)
    ? [WORKER_PROTOCOL]
    : VIEWER_MODELS.has(model)
      ? [VIEWER_PROTOCOL]
      : SHARED_ENVELOPE_MODELS.has(model)
        ? [WORKER_PROTOCOL, VIEWER_PROTOCOL]
        : undefined;
  if (allowed !== undefined && !allowed.includes(value.protocol as typeof WORKER_PROTOCOL)) {
    return "unknown_major";
  }
  if ("protocol" in value && value.protocol_minor !== PROTOCOL_MINOR) return "unsupported_minor";
  return undefined;
}

function hasAtMostSixDecimalPlaces(value: unknown): boolean {
  if (typeof value !== "number" || !Number.isFinite(value)) return false;
  const rendered = value.toString().toLowerCase();
  if (rendered.includes("e-")) return Number(rendered.split("e-")[1]) <= 6;
  return (rendered.split(".")[1]?.length ?? 0) <= 6;
}

function isNfcScalarText(value: unknown): boolean {
  if (typeof value !== "string" || value.normalize("NFC") !== value) return false;
  for (const character of value) {
    const point = character.codePointAt(0);
    if (point !== undefined && point >= 0xd800 && point <= 0xdfff) return false;
  }
  return true;
}

function semanticModelCode(model: string, value: Record<string, unknown>): StableCode {
  if (model === "LeaseV1") {
    const issued = Date.parse(String(value.issued_at));
    const expires = Date.parse(String(value.expires_at));
    if (expires <= issued || expires - issued > 120_000) return "schema_invalid";
  }
  if (model === "WorkerStatsV1") {
    if (Date.parse(String(value.window_ended_at)) < Date.parse(String(value.window_started_at))) {
      return "schema_invalid";
    }
    if (!hasAtMostSixDecimalPlaces(value.realtime_factor)) return "schema_invalid";
  }
  if (model === "TranscriptSegmentV1" || model === "TranscriptTimelinePayloadV1") {
    const start = Number(value.start_ms);
    const end = Number(value.end_ms);
    if (start >= end || end - start > 30_000) return "schema_invalid";
    if (
      value.confidence !== null &&
      value.confidence !== undefined &&
      !hasAtMostSixDecimalPlaces(value.confidence)
    ) {
      return "schema_invalid";
    }
    if (!isNfcScalarText(value.text)) return "schema_invalid";
  }
  if (model === "TimelineEventV1") {
    const payload = value.payload as Record<string, unknown>;
    if ("segment_id" in payload) {
      const result = semanticModelCode("TranscriptTimelinePayloadV1", payload);
      if (result !== "accepted") return result;
    }
  }
  if (model === "ProtocolErrorV1" && !isNfcScalarText(value.message)) return "schema_invalid";
  if (model === "ProtocolAckV1") {
    const outcome = value.outcome;
    const hasSeq = value.seq != null;
    const hasRevision = value.revision != null;
    const hasExpectedRevision = value.expected_revision != null;
    if (outcome === "accepted" && !hasSeq && !hasRevision && !hasExpectedRevision) {
      return "schema_invalid";
    }
    if (outcome === "seq_duplicate" && (!hasSeq || hasRevision || hasExpectedRevision)) {
      return "schema_invalid";
    }
    if (outcome === "revision_duplicate" && (!hasRevision || hasExpectedRevision)) {
      return "schema_invalid";
    }
    if (outcome === "cancel_duplicate" && (!hasExpectedRevision || hasSeq || hasRevision)) {
      return "schema_invalid";
    }
  }
  return "accepted";
}

interface ParsedSemver {
  core: [number, number, number];
  prerelease?: string[];
}

function parseSemver(value: string): ParsedSemver {
  const match = /^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z.-]+))?$/u.exec(
    value,
  );
  if (!match?.[1] || !match[2] || !match[3]) throw new TypeError("invalid SemVer");
  return {
    core: [Number(match[1]), Number(match[2]), Number(match[3])],
    ...(match[4] === undefined ? {} : { prerelease: match[4].split(".") }),
  };
}

function semverAtLeast(value: string, minimum: string): boolean {
  const left = parseSemver(value);
  const right = parseSemver(minimum);
  for (let index = 0; index < 3; index += 1) {
    const difference = (left.core[index] ?? 0) - (right.core[index] ?? 0);
    if (difference !== 0) return difference > 0;
  }
  if (left.prerelease === undefined) return true;
  if (right.prerelease === undefined) return false;
  const length = Math.max(left.prerelease.length, right.prerelease.length);
  for (let index = 0; index < length; index += 1) {
    const a = left.prerelease[index];
    const b = right.prerelease[index];
    if (a === undefined) return false;
    if (b === undefined) return true;
    if (a === b) continue;
    const aNumeric = /^[0-9]+$/u.test(a);
    const bNumeric = /^[0-9]+$/u.test(b);
    if (aNumeric && bNumeric) return Number(a) > Number(b);
    if (aNumeric !== bNumeric) return !aNumeric;
    return a > b;
  }
  return true;
}

function publicDecision(model: string, value: Record<string, unknown>): StableCode {
  const version = precheckVersion(model, value);
  if (version !== undefined) return version;
  if (
    model === "TimelineEventV1" &&
    value.payload !== null &&
    typeof value.payload === "object" &&
    !Array.isArray(value.payload)
  ) {
    const payload = value.payload as Record<string, unknown>;
    const payloadModel = "segment_id" in payload
      ? "TranscriptTimelinePayloadV1"
      : "status" in payload
        ? "SessionStatusTimelinePayloadV1"
        : undefined;
    const payloadValidator = payloadModel === undefined ? undefined : validators.get(payloadModel);
    if (payloadValidator !== undefined && !payloadValidator(payload)) {
      return classifySchemaErrors(payloadValidator.errors);
    }
  }
  const validator = validators.get(model);
  if (validator === undefined || !validator(value)) return classifySchemaErrors(validator?.errors);
  const semantic = semanticModelCode(model, value);
  if (semantic !== "accepted") return semantic;
  if (model === "WorkerHelloV1") {
    if (!semverAtLeast(String(value.worker_version), "0.1.0")) return "worker_version_too_old";
    const capabilities = value.capabilities as string[];
    if (
      capabilities.length !== 2 ||
      !capabilities.includes("asr.transcribe") ||
      !capabilities.includes("protocol.binary-pcm")
    ) {
      return "capability_required";
    }
    const manifests = value.model_manifests as Array<Record<string, unknown>>;
    if (
      manifests.length === 0 ||
      manifests.some(
        (item) =>
          item.provider !== "synthetic" ||
          item.model_id !== "fixture-asr" ||
          item.revision !== "1" ||
          item.sha256 !== "a".repeat(64),
      )
    ) {
      return "manifest_not_allowed";
    }
  }
  if (model === "ViewerSubscribeV1") {
    if (!semverAtLeast(String(value.client_version), "0.1.0")) return "worker_version_too_old";
  }
  return "accepted";
}

function sequenceDecision(value: Record<string, unknown>): StableCode {
  const start = Number(value.start_seq);
  const count = Number(value.accepted_count);
  const records = new Map<number, { messageId: string; digest: string }>();
  for (let index = 0; index < count; index += 1) {
    records.set(start + index, {
      messageId: "00000000-0000-4000-8000-000000000001",
      digest: digest({ index }),
    });
    if (records.size > 256) records.delete(Math.min(...records.keys()));
  }
  const nextExpected = start + count;
  const candidate = Number(value.candidate_seq);
  if (candidate < nextExpected) {
    const record = records.get(candidate);
    if (record === undefined) return "resync_required";
    return record.messageId === value.candidate_message_id &&
      record.digest === digest({ index: Number(value.candidate_value_index) })
      ? "seq_duplicate"
      : "seq_conflict";
  }
  return candidate > nextExpected ? "seq_gap" : "accepted";
}

function revisionDecision(value: Record<string, unknown>): StableCode {
  const capacity = Number(value.fill_count);
  const existing = Boolean(value.existing);
  if (!existing && capacity >= 4096) return "revision_capacity_exceeded";
  if (!existing) return Number(value.candidate_revision) === 1 ? "accepted" : "revision_gap";
  const current = Number(value.current_revision);
  const candidate = Number(value.candidate_revision);
  if (candidate < current) return "revision_stale";
  if (candidate === current && value.candidate_projection === value.current_projection) {
    return "revision_duplicate";
  }
  if (Boolean(value.current_final)) return "object_final";
  if (candidate === current) return "revision_conflict";
  if (candidate > current + 1) return "revision_gap";
  if (value.candidate_immutable !== value.current_immutable) return "revision_immutable";
  return "accepted";
}

function cancellationDecision(value: Record<string, unknown>): StableCode {
  if (value.initial === "missing") return "lease_unknown";
  if (value.initial === "closed") return "lease_closed";
  if (value.initial === "cancelled") {
    return value.candidate === "duplicate" ? "cancel_duplicate" : "cancel_conflict";
  }
  if (value.candidate === "binding_mismatch") return "binding_mismatch";
  if (value.candidate === "cas_stale") return "revision_stale";
  if (value.candidate === "cas_gap") return "revision_gap";
  return "accepted";
}

function binaryDecision(value: Record<string, unknown>): StableCode {
  if (Number(value.total_length) > 32_056) return "binary_frame_too_large";
  if (
    value.magic !== "LPCM" ||
    value.major !== 1 ||
    value.minor !== 0 ||
    (Number(value.flags) & ~1) !== 0 ||
    value.header_length !== 56 ||
    Number(value.total_length) !== 56 + Number(value.payload_length) ||
    Number(value.sample_count) < 1 ||
    Number(value.sample_count) > 16_000 ||
    Number(value.payload_length) !== Number(value.sample_count) * 2
  ) {
    return "binary_header_invalid";
  }
  if (value.lease_id !== value.expected_lease_id) return "binding_mismatch";
  if (Number(value.epoch) < Number(value.expected_epoch)) return "epoch_stale";
  if (Number(value.epoch) > Number(value.expected_epoch)) return "epoch_unknown";
  const sequence = Number(value.seq);
  const nextExpected = Number(value.next_expected_seq);
  const oldestReplayable = Math.max(Number(value.input_start_seq), nextExpected - 256);
  if (sequence < oldestReplayable) return "resync_required";
  if (sequence < nextExpected) return "seq_duplicate";
  if (sequence > nextExpected) return "seq_gap";
  if (value.previous_pts !== null && Number(value.pts_ms) < Number(value.previous_pts)) {
    return "audio_pts_invalid";
  }
  if (
    Number(value.buffered_bytes) + Number(value.payload_length) > 960_000 ||
    Number(value.process_buffered_bytes) + Number(value.payload_length) > 16_777_216
  ) {
    return "audio_budget_exceeded";
  }
  return "accepted";
}

export function evaluateGoldenCase(testCase: GoldenCaseV1): StableCode {
  if (publicModelSet.has(testCase.model)) {
    let value = testCase.wire;
    if (testCase.raw_text !== undefined) {
      const parsed = strictJsonParse(testCase.raw_text);
      if (parsed.code !== "accepted") return parsed.code;
      value = parsed.value;
    }
    return value === undefined ? "schema_invalid" : publicDecision(testCase.model, value);
  }
  const value = testCase.wire;
  if (testCase.model === "JsonSequenceDecisionV1" && value !== undefined) {
    return sequenceDecision(value);
  }
  if (testCase.model === "PcmSequenceDecisionV1" && value !== undefined) {
    const start = Number(value.start_seq);
    const nextExpected = start + Number(value.accepted_count);
    const candidate = Number(value.candidate_seq);
    if (candidate < Math.max(start, nextExpected - 256)) return "resync_required";
    if (candidate < nextExpected) return "seq_duplicate";
    if (candidate > nextExpected) return "seq_gap";
    return "accepted";
  }
  if (testCase.model === "EpochDecisionV1" && value !== undefined) {
    const current = Number(value.current);
    const received = Number(value.received);
    return received < current ? "epoch_stale" : received > current ? "epoch_unknown" : "accepted";
  }
  if (testCase.model === "RevisionDecisionV1" && value !== undefined) {
    return revisionDecision(value);
  }
  if (testCase.model === "CancellationDecisionV1" && value !== undefined) {
    return cancellationDecision(value);
  }
  if (testCase.model === "ResumeDecisionV1" && value !== undefined) {
    return Boolean(value.expired)
      ? "lease_expired"
      : Boolean(value.live)
        ? "accepted"
        : "resync_required";
  }
  if (testCase.model === "CanonicalDecisionV1" && value !== undefined) {
    const equal = digest(value.left) === digest(value.right);
    return equal === Boolean(value.expect_equal) ? "accepted" : "schema_invalid";
  }
  if (testCase.model === "CanonicalRawDecisionV1" && value !== undefined) {
    const left = strictJsonParse(String(value.left_raw));
    const right = strictJsonParse(String(value.right_raw));
    if (left.code !== "accepted") return left.code;
    if (right.code !== "accepted") return right.code;
    const equal = digest(left.value) === digest(right.value);
    return equal === Boolean(value.expect_equal) ? "accepted" : "schema_invalid";
  }
  if (testCase.model === "PcmHeaderV1" && testCase.binary_header !== undefined) {
    return binaryDecision(testCase.binary_header);
  }
  return "schema_invalid";
}

export function isAcceptedCode(code: StableCode): boolean {
  return ["accepted", "seq_duplicate", "revision_duplicate", "cancel_duplicate"].includes(code);
}
