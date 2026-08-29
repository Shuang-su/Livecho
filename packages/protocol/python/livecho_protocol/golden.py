"""Authoritative synthetic golden corpus and Python decision runner."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from .compatibility import manifest_key, negotiate_viewer, negotiate_worker
from .errors import SUCCESS_CODES, ProtocolValidationError, StableCode
from .models import (
    MODEL_BY_NAME,
    LeaseCancelV1,
    LeaseV1,
    StrictModel,
    ViewerSubscribeV1,
    WorkerHelloV1,
    WorkerResumeV1,
)
from .parser import canonical_digest, parse_control, strict_json_loads, validate_object
from .scalars import UINT64_MAX
from .state import (
    ActiveLease,
    CancellationRegistry,
    JsonSequenceWindow,
    LiveWorkerCursor,
    decide_worker_resume,
)

MESSAGE_ID = "00000000-0000-4000-8000-000000000001"
MESSAGE_ID_2 = "00000000-0000-4000-8000-000000000002"
WORKER_ID = "00000000-0000-4000-8000-000000000010"
CONNECTION_ID = "00000000-0000-4000-8000-000000000011"
LEASE_ID = "00000000-0000-4000-8000-000000000020"
SESSION_ID = "00000000-0000-4000-8000-000000000030"
SEGMENT_ID = "00000000-0000-4000-8000-000000000040"
STATS_ID = "00000000-0000-4000-8000-000000000050"
EVENT_ID = "00000000-0000-4000-8000-000000000060"
TIMESTAMP = "2026-01-01T00:00:00.000Z"
MANIFEST = {
    "provider": "synthetic",
    "model_id": "fixture-asr",
    "revision": "1",
    "sha256": "a" * 64,
}


class GoldenCaseV1(StrictModel):
    case_id: str = Field(pattern=r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
    model: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z][A-Za-z0-9]+$")
    expect: Literal["accepted", "rejected"]
    code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    wire: dict[str, Any] | None = None
    raw_text: str | None = None
    binary_header: dict[str, Any] | None = None

    @model_validator(mode="after")
    def exactly_one_input(self) -> GoldenCaseV1:
        if sum(value is not None for value in (self.wire, self.raw_text, self.binary_header)) != 1:
            raise ValueError("golden case requires exactly one input")
        return self


def _worker_envelope(message_type: str, message_id: str = MESSAGE_ID) -> dict[str, Any]:
    return {
        "protocol": "livecho.worker.v1",
        "protocol_minor": 0,
        "message_id": message_id,
        "type": message_type,
        "sent_at": TIMESTAMP,
    }


def _viewer_envelope(message_type: str, message_id: str = MESSAGE_ID) -> dict[str, Any]:
    return {
        "protocol": "livecho.viewer.v1",
        "protocol_minor": 0,
        "message_id": message_id,
        "type": message_type,
        "sent_at": TIMESTAMP,
    }


def _public_values() -> dict[str, dict[str, Any]]:
    resume = {
        "connection_id": CONNECTION_ID,
        "lease_id": LEASE_ID,
        "session_id": SESSION_ID,
        "epoch": "1",
        "next_input_seq": "0",
        "next_output_seq": "0",
    }
    cursor = {"session_id": SESSION_ID, "epoch": "1", "next_seq": "0"}
    hello = {
        **_worker_envelope("worker.hello"),
        "worker_id": WORKER_ID,
        "worker_version": "0.1.0",
        "supported_minors": [0],
        "capabilities": ["asr.transcribe", "protocol.binary-pcm"],
        "model_manifests": [deepcopy(MANIFEST)],
        "resume": None,
    }
    welcome = {
        **_worker_envelope("worker.welcome"),
        "connection_id": CONNECTION_ID,
        "selected_minor": 0,
        "minimum_worker_version": "0.1.0",
        "resume_succeeded": False,
        "accepted_capabilities": ["asr.transcribe", "protocol.binary-pcm"],
        "accepted_manifests": [deepcopy(MANIFEST)],
    }
    lease = {
        **_worker_envelope("worker.lease"),
        "lease_id": LEASE_ID,
        "session_id": SESSION_ID,
        "room_id": "synthetic-room",
        "epoch": "1",
        "revision": "1",
        "issued_at": TIMESTAMP,
        "expires_at": "2026-01-01T00:02:00.000Z",
        "input_start_seq": "0",
        "output_start_seq": "0",
        "model_manifest": deepcopy(MANIFEST),
        "audio_format": {"encoding": "pcm_s16le", "sample_rate_hz": 16000, "channels": 1},
        "audio_origin": "synthetic",
    }
    cancel = {
        **_worker_envelope("worker.lease_cancel"),
        "lease_id": LEASE_ID,
        "session_id": SESSION_ID,
        "epoch": "1",
        "expected_revision": "1",
        "reason": "operator_stop",
    }
    heartbeat = {
        **_worker_envelope("worker.heartbeat"),
        "lease_id": LEASE_ID,
        "session_id": SESSION_ID,
        "epoch": "1",
        "seq": "0",
        "state": "ready",
        "last_input_seq": None,
        "last_output_seq": None,
        "audio_buffer_bytes": 0,
        "observed_at": TIMESTAMP,
    }
    stats = {
        **_worker_envelope("worker.stats"),
        "lease_id": LEASE_ID,
        "session_id": SESSION_ID,
        "stats_id": STATS_ID,
        "epoch": "1",
        "seq": "0",
        "revision": "1",
        "processed_audio_ms": "0",
        "segments_accepted": "0",
        "segments_rejected": "0",
        "realtime_factor": 1.0,
        "window_started_at": TIMESTAMP,
        "window_ended_at": "2026-01-01T00:00:01.000Z",
    }
    transcript_payload = {
        "segment_id": SEGMENT_ID,
        "start_ms": 0,
        "end_ms": 1000,
        "text": "synthetic caption",
        "language": "en",
        "confidence": 0.9,
        "is_final": False,
    }
    transcript = {
        **_worker_envelope("worker.transcript"),
        "lease_id": LEASE_ID,
        "session_id": SESSION_ID,
        "epoch": "1",
        "seq": "0",
        "revision": "1",
        **deepcopy(transcript_payload),
    }
    timeline = {
        **_viewer_envelope("viewer.timeline_event"),
        "event_id": EVENT_ID,
        "session_id": SESSION_ID,
        "room_id": "synthetic-room",
        "epoch": "1",
        "seq": "0",
        "revision": "1",
        "occurred_at": TIMESTAMP,
        "payload": deepcopy(transcript_payload),
    }
    status_payload = {"status": "live", "reason_code": None}
    subscribe = {
        **_viewer_envelope("viewer.subscribe"),
        "client_version": "0.1.0",
        "supported_minors": [0],
        "room_id": "synthetic-room",
        "cursor": None,
    }
    ready = {
        **_viewer_envelope("viewer.ready"),
        "selected_minor": 0,
        "minimum_client_version": "0.1.0",
        "session_id": SESSION_ID,
        "epoch": "1",
        "next_seq": "0",
        "cursor_resumed": False,
    }
    ack = {
        **_worker_envelope("protocol.ack"),
        "outcome": "accepted",
        "acknowledged_message_id": MESSAGE_ID_2,
        "seq": "0",
        "revision": None,
        "expected_revision": None,
    }
    error = {
        **_worker_envelope("protocol.error"),
        "code": "schema_invalid",
        "message": "Invalid synthetic message",
        "retryable": False,
        "expected": None,
        "received": None,
    }
    return {
        "AudioFormatV1": deepcopy(lease["audio_format"]),
        "HeartbeatV1": heartbeat,
        "LeaseCancelV1": cancel,
        "LeaseV1": lease,
        "ModelManifestRefV1": deepcopy(MANIFEST),
        "ProtocolAckV1": ack,
        "ProtocolErrorV1": error,
        "SessionStatusTimelinePayloadV1": status_payload,
        "TimelineEventV1": timeline,
        "TranscriptSegmentV1": transcript,
        "TranscriptTimelinePayloadV1": transcript_payload,
        "ViewerCursorV1": cursor,
        "ViewerReadyV1": ready,
        "ViewerSubscribeV1": subscribe,
        "WorkerHelloV1": hello,
        "WorkerResumeV1": resume,
        "WorkerStatsV1": stats,
        "WorkerWelcomeV1": welcome,
    }


def _case(
    case_id: str,
    model: str,
    expect: Literal["accepted", "rejected"],
    code: StableCode,
    *,
    wire: dict[str, Any] | None = None,
    raw_text: str | None = None,
    binary_header: dict[str, Any] | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "case_id": case_id,
        "model": model,
        "expect": expect,
        "code": code.value,
    }
    if wire is not None:
        value["wire"] = wire
    elif raw_text is not None:
        value["raw_text"] = raw_text
    elif binary_header is not None:
        value["binary_header"] = binary_header
    return value


def accepted_cases() -> list[dict[str, Any]]:
    values = _public_values()
    cases = [
        _case(f"model.{name.lower()}", name, "accepted", StableCode.ACCEPTED, wire=value)
        for name, value in sorted(values.items())
    ]
    cases.extend(
        [
            _case(
                "ack.seq_duplicate",
                "ProtocolAckV1",
                "accepted",
                StableCode.ACCEPTED,
                wire=_changed(
                    values["ProtocolAckV1"],
                    outcome="seq_duplicate",
                ),
            ),
            _case(
                "ack.revision_duplicate_sequenced",
                "ProtocolAckV1",
                "accepted",
                StableCode.ACCEPTED,
                wire=_changed(
                    values["ProtocolAckV1"],
                    outcome="revision_duplicate",
                    revision="1",
                ),
            ),
            _case(
                "ack.revision_duplicate_lease",
                "ProtocolAckV1",
                "accepted",
                StableCode.ACCEPTED,
                wire=_changed(
                    values["ProtocolAckV1"],
                    outcome="revision_duplicate",
                    seq=None,
                    revision="1",
                ),
            ),
            _case(
                "ack.cancel_duplicate",
                "ProtocolAckV1",
                "accepted",
                StableCode.ACCEPTED,
                wire=_changed(
                    values["ProtocolAckV1"],
                    outcome="cancel_duplicate",
                    seq=None,
                    expected_revision="1",
                ),
            ),
            _case(
                "schema.timestamp_year_one",
                "TranscriptSegmentV1",
                "accepted",
                StableCode.ACCEPTED,
                wire=_changed(
                    values["TranscriptSegmentV1"],
                    sent_at="0001-01-01T00:00:00.000Z",
                ),
            ),
            _case(
                "sequence.duplicate",
                "JsonSequenceDecisionV1",
                "accepted",
                StableCode.SEQ_DUPLICATE,
                wire={
                    "start_seq": 0,
                    "accepted_count": 1,
                    "candidate_seq": 0,
                    "candidate_message_id": MESSAGE_ID,
                    "candidate_value_index": 0,
                },
            ),
            _case(
                "revision.duplicate",
                "RevisionDecisionV1",
                "accepted",
                StableCode.REVISION_DUPLICATE,
                wire={
                    "existing": True,
                    "fill_count": 0,
                    "current_revision": 1,
                    "current_projection": "a",
                    "current_immutable": "a",
                    "current_final": False,
                    "candidate_revision": 1,
                    "candidate_projection": "a",
                    "candidate_immutable": "a",
                    "candidate_final": False,
                },
            ),
            _final_revision_case(
                "final.duplicate",
                "accepted",
                StableCode.REVISION_DUPLICATE,
                2,
                "final",
            ),
            _case(
                "pcm_sequence.duplicate",
                "PcmSequenceDecisionV1",
                "accepted",
                StableCode.SEQ_DUPLICATE,
                wire={"start_seq": 0, "accepted_count": 257, "candidate_seq": 1},
            ),
            _case(
                "cancel.initial",
                "CancellationDecisionV1",
                "accepted",
                StableCode.ACCEPTED,
                wire={"initial": "active", "candidate": "new"},
            ),
            _case(
                "cancel.duplicate",
                "CancellationDecisionV1",
                "accepted",
                StableCode.CANCEL_DUPLICATE,
                wire={"initial": "cancelled", "candidate": "duplicate"},
            ),
            _case(
                "epoch.non_resumed_replacement_clears_state",
                "LeaseReplacementDecisionV1",
                "accepted",
                StableCode.ACCEPTED,
                wire={
                    "current_epoch": "1",
                    "replacement_epoch": "2",
                    "resumed": False,
                    "superseded_active_after": False,
                    "retained_pcm_bytes": 0,
                    "retained_output_revisions": 0,
                },
            ),
            _binary_case("binary.end_of_segment", StableCode.ACCEPTED, flags=1),
            _case(
                "canonical.equal",
                "CanonicalDecisionV1",
                "accepted",
                StableCode.ACCEPTED,
                wire={
                    "left": {"a": "synthetic", "b": 1.0},
                    "right": {"b": 1, "a": "synthetic"},
                    "expect_equal": True,
                },
            ),
            _canonical_raw_case(
                "canonical.key_order",
                '{"b":1,"a":"synthetic"}',
                '{"a":"synthetic","b":1}',
                True,
            ),
            _canonical_raw_case(
                "canonical.escaping",
                '{"a":"synthetic"}',
                '{"a":"\\u0073ynthetic"}',
                True,
            ),
            _canonical_raw_case(
                "canonical.number_spelling",
                '{"a":1.0}',
                '{"a":1e0}',
                True,
            ),
            _canonical_raw_case(
                "canonical.missing_null",
                '{"a":"synthetic"}',
                '{"a":"synthetic","b":null}',
                False,
            ),
            _canonical_raw_case(
                "canonical.changed_value",
                '{"a":1}',
                '{"a":2}',
                False,
            ),
        ]
    )
    return sorted(cases, key=lambda item: item["case_id"])


def _changed(value: dict[str, Any], **updates: Any) -> dict[str, Any]:
    result = deepcopy(value)
    result.update(updates)
    return result


def rejected_cases() -> list[dict[str, Any]]:
    values = _public_values()
    hello = values["WorkerHelloV1"]
    ack = values["ProtocolAckV1"]
    error = values["ProtocolErrorV1"]
    heartbeat = values["HeartbeatV1"]
    timeline = values["TimelineEventV1"]
    partial_timeline = deepcopy(timeline)
    partial_payload = partial_timeline["payload"]
    if not isinstance(partial_payload, dict):
        raise TypeError("timeline payload fixture must be an object")
    del partial_payload["segment_id"]
    transcript = values["TranscriptSegmentV1"]
    non_nfc = deepcopy(transcript)
    non_nfc["text"] = "e\u0301"
    malformed = '{"protocol":'
    duplicate = '{"protocol":"livecho.worker.v1","protocol":"livecho.worker.v1"}'
    large = "{" + " " * 65_536 + "}"
    return sorted(
        [
            _case(
                "parser.malformed",
                "WorkerHelloV1",
                "rejected",
                StableCode.MALFORMED_JSON,
                raw_text=malformed,
            ),
            _case(
                "parser.duplicate_key",
                "WorkerHelloV1",
                "rejected",
                StableCode.DUPLICATE_KEY,
                raw_text=duplicate,
            ),
            _case(
                "parser.malformed_duplicate",
                "WorkerHelloV1",
                "rejected",
                StableCode.MALFORMED_JSON,
                raw_text='{"a":1,"a":2,}',
            ),
            _case(
                "parser.malformed_nested_duplicate",
                "WorkerHelloV1",
                "rejected",
                StableCode.MALFORMED_JSON,
                raw_text='{"a":{"x":1,"x":2},"b":}',
            ),
            _case(
                "parser.too_large",
                "WorkerHelloV1",
                "rejected",
                StableCode.CONTROL_FRAME_TOO_LARGE,
                raw_text=large,
            ),
            _case(
                "schema.unknown_field",
                "WorkerHelloV1",
                "rejected",
                StableCode.UNKNOWN_FIELD,
                wire=_changed(hello, command="forbidden"),
            ),
            _case(
                "schema.invalid",
                "TranscriptSegmentV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                wire=_changed(transcript, end_ms=0),
            ),
            _case(
                "schema.integral_fraction_integer",
                "HeartbeatV1",
                "accepted",
                StableCode.ACCEPTED,
                raw_text=json.dumps(
                    _changed(heartbeat, audio_buffer_bytes=0.0),
                    separators=(",", ":"),
                ),
            ),
            _case(
                "schema.nonintegral_fraction_integer",
                "HeartbeatV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                raw_text=json.dumps(
                    _changed(heartbeat, audio_buffer_bytes=0.5),
                    separators=(",", ":"),
                ),
            ),
            _case(
                "schema.string_integer",
                "HeartbeatV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                raw_text=json.dumps(
                    _changed(heartbeat, audio_buffer_bytes="0"),
                    separators=(",", ":"),
                ),
            ),
            _case(
                "schema.boolean_protocol_minor",
                "LeaseV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                raw_text=json.dumps(
                    _changed(values["LeaseV1"], protocol_minor=False),
                    separators=(",", ":"),
                ),
            ),
            _case(
                "schema.boolean_selected_minor",
                "WorkerWelcomeV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                raw_text=json.dumps(
                    _changed(values["WorkerWelcomeV1"], selected_minor=False),
                    separators=(",", ":"),
                ),
            ),
            _case(
                "schema.boolean_channels",
                "AudioFormatV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                raw_text=json.dumps(
                    _changed(values["AudioFormatV1"], channels=True),
                    separators=(",", ":"),
                ),
            ),
            _case(
                "schema.boolean_sample_rate",
                "AudioFormatV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                raw_text=json.dumps(
                    _changed(values["AudioFormatV1"], sample_rate_hz=True),
                    separators=(",", ":"),
                ),
            ),
            _case(
                "schema.timeline_payload_value",
                "TimelineEventV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                wire=_changed(timeline, payload=_changed(timeline["payload"], text="")),
            ),
            _case(
                "schema.timeline_partial_payload",
                "TimelineEventV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                wire=partial_timeline,
            ),
            _case(
                "schema.timestamp_invalid",
                "TranscriptSegmentV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                wire=_changed(transcript, sent_at="2026-02-31T00:00:00.000Z"),
            ),
            _case(
                "schema.timestamp_year_zero",
                "TranscriptSegmentV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                wire=_changed(transcript, sent_at="0000-01-01T00:00:00.000Z"),
            ),
            _case(
                "ack.seq_position_required",
                "ProtocolAckV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                wire=_changed(
                    ack,
                    outcome="seq_duplicate",
                    seq=None,
                    revision="1",
                ),
            ),
            _case(
                "ack.seq_rejects_cas",
                "ProtocolAckV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                wire=_changed(
                    ack,
                    outcome="seq_duplicate",
                    expected_revision="1",
                ),
            ),
            _case(
                "ack.accepted_seq_rejects_cas",
                "ProtocolAckV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                wire=_changed(ack, expected_revision="1"),
            ),
            _case(
                "ack.accepted_revision_rejects_cas",
                "ProtocolAckV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                wire=_changed(
                    ack,
                    seq=None,
                    revision="1",
                    expected_revision="1",
                ),
            ),
            _case(
                "ack.revision_position_required",
                "ProtocolAckV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                wire=_changed(
                    ack,
                    outcome="revision_duplicate",
                    revision=None,
                ),
            ),
            _case(
                "ack.cancel_position_required",
                "ProtocolAckV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                wire=_changed(
                    ack,
                    outcome="cancel_duplicate",
                ),
            ),
            _case(
                "schema.uint64_overflow",
                "TranscriptSegmentV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                wire=_changed(transcript, seq="18446744073709551616"),
            ),
            _case(
                "version.major",
                "WorkerHelloV1",
                "rejected",
                StableCode.UNKNOWN_MAJOR,
                wire=_changed(hello, protocol="livecho.worker.v2"),
            ),
            _case(
                "version.nested_protocol_field",
                "AudioFormatV1",
                "rejected",
                StableCode.UNKNOWN_FIELD,
                wire=_changed(values["AudioFormatV1"], protocol="livecho.worker.v1"),
            ),
            _case(
                "version.protocol_missing",
                "WorkerHelloV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                wire={key: value for key, value in hello.items() if key != "protocol"},
            ),
            _case(
                "version.protocol_type",
                "WorkerHelloV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                wire=_changed(hello, protocol=1),
            ),
            _case(
                "version.minor_missing",
                "WorkerHelloV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                wire={key: value for key, value in hello.items() if key != "protocol_minor"},
            ),
            _case(
                "version.shared_ack_major",
                "ProtocolAckV1",
                "rejected",
                StableCode.UNKNOWN_MAJOR,
                wire=_changed(ack, protocol="livecho.worker.v2"),
            ),
            _case(
                "version.shared_error_major",
                "ProtocolErrorV1",
                "rejected",
                StableCode.UNKNOWN_MAJOR,
                wire=_changed(error, protocol="livecho.viewer.v2"),
            ),
            _case(
                "version.minor",
                "WorkerHelloV1",
                "rejected",
                StableCode.UNSUPPORTED_MINOR,
                wire=_changed(hello, protocol_minor=1),
            ),
            _case(
                "version.integral_fraction_minor",
                "WorkerHelloV1",
                "rejected",
                StableCode.UNSUPPORTED_MINOR,
                raw_text=json.dumps(
                    _changed(hello, protocol_minor=1.0),
                    separators=(",", ":"),
                ),
            ),
            _case(
                "version.integral_fraction_minor_with_unknown_major",
                "WorkerHelloV1",
                "rejected",
                StableCode.UNKNOWN_MAJOR,
                raw_text=json.dumps(
                    _changed(hello, protocol="livecho.worker.v2", protocol_minor=0.0),
                    separators=(",", ":"),
                ),
            ),
            _case(
                "version.worker_supported_minor_missing",
                "WorkerHelloV1",
                "rejected",
                StableCode.UNSUPPORTED_MINOR,
                wire=_changed(hello, supported_minors=[1]),
            ),
            _case(
                "version.viewer_supported_minor_missing",
                "ViewerSubscribeV1",
                "rejected",
                StableCode.UNSUPPORTED_MINOR,
                wire=_changed(values["ViewerSubscribeV1"], supported_minors=[1]),
            ),
            _case(
                "version.worker_old",
                "WorkerHelloV1",
                "rejected",
                StableCode.WORKER_VERSION_TOO_OLD,
                wire=_changed(hello, worker_version="0.1.0-rc.1"),
            ),
            _case(
                "capability.required",
                "WorkerHelloV1",
                "rejected",
                StableCode.CAPABILITY_REQUIRED,
                wire=_changed(hello, capabilities=["asr.transcribe"]),
            ),
            _case(
                "capability.missing_field",
                "WorkerHelloV1",
                "rejected",
                StableCode.CAPABILITY_REQUIRED,
                wire={key: value for key, value in hello.items() if key != "capabilities"},
            ),
            _case(
                "manifest.not_allowed",
                "WorkerHelloV1",
                "rejected",
                StableCode.MANIFEST_NOT_ALLOWED,
                wire=_changed(hello, model_manifests=[{**MANIFEST, "sha256": "b" * 64}]),
            ),
            _case(
                "manifest.reference_mismatch",
                "WorkerHelloV1",
                "rejected",
                StableCode.MANIFEST_NOT_ALLOWED,
                wire=_changed(
                    hello,
                    model_manifests=[{**MANIFEST, "provider": "other-synthetic"}],
                ),
            ),
            _case(
                "manifest.lease_not_allowed",
                "LeaseV1",
                "rejected",
                StableCode.MANIFEST_NOT_ALLOWED,
                wire=_changed(
                    values["LeaseV1"],
                    model_manifest={**MANIFEST, "sha256": "b" * 64},
                ),
            ),
            _semantic_case(
                "lease.unknown",
                "CancellationDecisionV1",
                StableCode.LEASE_UNKNOWN,
                {"initial": "missing", "candidate": "new"},
            ),
            _semantic_case(
                "lease.closed",
                "CancellationDecisionV1",
                StableCode.LEASE_CLOSED,
                {"initial": "closed", "candidate": "new"},
            ),
            _semantic_case(
                "lease.expired",
                "ResumeDecisionV1",
                StableCode.LEASE_EXPIRED,
                {"live": True, "expired": True, "binding": "same", "epoch": 1, "sequence": "same"},
            ),
            _semantic_case(
                "binding.mismatch",
                "CancellationDecisionV1",
                StableCode.BINDING_MISMATCH,
                {"initial": "active", "candidate": "binding_mismatch"},
            ),
            _semantic_case(
                "epoch.stale",
                "EpochDecisionV1",
                StableCode.EPOCH_STALE,
                {"current": 2, "received": 1},
            ),
            _semantic_case(
                "epoch.unknown",
                "EpochDecisionV1",
                StableCode.EPOCH_UNKNOWN,
                {"current": 1, "received": 2},
            ),
            _semantic_case(
                "epoch.uint64_unknown",
                "EpochDecisionV1",
                StableCode.EPOCH_UNKNOWN,
                {"current": "9007199254740992", "received": "9007199254740993"},
            ),
            _semantic_case(
                "epoch.stale_runtime_creation",
                "LeaseReplacementDecisionV1",
                StableCode.EPOCH_STALE,
                {
                    "current_epoch": "2",
                    "replacement_epoch": "1",
                    "resumed": False,
                    "superseded_active_after": True,
                    "retained_pcm_bytes": 2,
                    "retained_output_revisions": 1,
                },
            ),
            _semantic_case(
                "epoch.equal_runtime_creation",
                "LeaseReplacementDecisionV1",
                StableCode.RESYNC_REQUIRED,
                {
                    "current_epoch": "2",
                    "replacement_epoch": "2",
                    "resumed": False,
                    "superseded_active_after": True,
                    "retained_pcm_bytes": 2,
                    "retained_output_revisions": 1,
                },
            ),
            _semantic_case(
                "lease.invalid_replacement_revision",
                "LeaseReplacementDecisionV1",
                StableCode.REVISION_GAP,
                {
                    "current_epoch": "1",
                    "replacement_epoch": "2",
                    "replacement_revision": "2",
                    "resumed": False,
                    "superseded_active_after": True,
                    "retained_pcm_bytes": 2,
                    "retained_output_revisions": 1,
                },
            ),
            _semantic_case(
                "sequence.exhausted",
                "JsonSequenceDecisionV1",
                StableCode.RESYNC_REQUIRED,
                {
                    "start_seq": str(UINT64_MAX),
                    "accepted_count": 0,
                    "candidate_seq": str(UINT64_MAX),
                    "candidate_message_id": MESSAGE_ID,
                    "candidate_value_index": 0,
                },
            ),
            _semantic_case(
                "sequence.conflict",
                "JsonSequenceDecisionV1",
                StableCode.SEQ_CONFLICT,
                {
                    "start_seq": 0,
                    "accepted_count": 1,
                    "candidate_seq": 0,
                    "candidate_message_id": MESSAGE_ID_2,
                    "candidate_value_index": 1,
                },
            ),
            _semantic_case(
                "sequence.gap",
                "JsonSequenceDecisionV1",
                StableCode.SEQ_GAP,
                {
                    "start_seq": 0,
                    "accepted_count": 1,
                    "candidate_seq": 2,
                    "candidate_message_id": MESSAGE_ID,
                    "candidate_value_index": 2,
                },
            ),
            _semantic_case(
                "sequence.uint64_gap",
                "JsonSequenceDecisionV1",
                StableCode.SEQ_GAP,
                {
                    "start_seq": "9007199254740992",
                    "accepted_count": 0,
                    "candidate_seq": "9007199254740993",
                    "candidate_message_id": MESSAGE_ID,
                    "candidate_value_index": 0,
                },
            ),
            _semantic_case(
                "sequence.resync",
                "JsonSequenceDecisionV1",
                StableCode.RESYNC_REQUIRED,
                {
                    "start_seq": 0,
                    "accepted_count": 257,
                    "candidate_seq": 0,
                    "candidate_message_id": MESSAGE_ID,
                    "candidate_value_index": 0,
                },
            ),
            _revision_case(
                "revision.conflict", StableCode.REVISION_CONFLICT, 1, "changed", "a", False
            ),
            _revision_case("revision.stale", StableCode.REVISION_STALE, 0, "a", "a", False),
            _revision_case("revision.gap", StableCode.REVISION_GAP, 3, "changed", "a", False),
            _revision_case(
                "revision.immutable", StableCode.REVISION_IMMUTABLE, 2, "changed", "changed", False
            ),
            _semantic_case(
                "revision.capacity",
                "RevisionDecisionV1",
                StableCode.REVISION_CAPACITY_EXCEEDED,
                {
                    "existing": False,
                    "fill_count": 4096,
                    "current_revision": 1,
                    "current_projection": "a",
                    "current_immutable": "a",
                    "current_final": False,
                    "candidate_revision": 1,
                    "candidate_projection": "new",
                    "candidate_immutable": "new",
                    "candidate_final": False,
                },
            ),
            _semantic_case(
                "revision.capacity_precedes_gap",
                "RevisionDecisionV1",
                StableCode.REVISION_CAPACITY_EXCEEDED,
                {
                    "existing": False,
                    "fill_count": 4096,
                    "current_revision": 1,
                    "current_projection": "a",
                    "current_immutable": "a",
                    "current_final": False,
                    "candidate_revision": 2,
                    "candidate_projection": "new",
                    "candidate_immutable": "new",
                    "candidate_final": False,
                },
            ),
            _case(
                "revision.uint64_next",
                "RevisionDecisionV1",
                "accepted",
                StableCode.ACCEPTED,
                wire={
                    "existing": True,
                    "fill_count": 0,
                    "current_revision": "9007199254740992",
                    "current_projection": "a",
                    "current_immutable": "a",
                    "current_final": False,
                    "candidate_revision": "9007199254740993",
                    "candidate_projection": "changed",
                    "candidate_immutable": "a",
                    "candidate_final": False,
                },
            ),
            _semantic_case(
                "cancel.conflict",
                "CancellationDecisionV1",
                StableCode.CANCEL_CONFLICT,
                {"initial": "cancelled", "candidate": "conflict"},
            ),
            _semantic_case(
                "cancel.cas_stale",
                "CancellationDecisionV1",
                StableCode.REVISION_STALE,
                {"initial": "active", "candidate": "cas_stale"},
            ),
            _semantic_case(
                "cancel.cas_gap",
                "CancellationDecisionV1",
                StableCode.REVISION_GAP,
                {"initial": "active", "candidate": "cas_gap"},
            ),
            _revision_case("object.final", StableCode.OBJECT_FINAL, 1, "changed", "a", True),
            _final_revision_case(
                "final.stale",
                "rejected",
                StableCode.REVISION_STALE,
                1,
                "old",
            ),
            _final_revision_case(
                "final.higher",
                "rejected",
                StableCode.OBJECT_FINAL,
                3,
                "changed",
            ),
            _semantic_case(
                "pcm_sequence.resync",
                "PcmSequenceDecisionV1",
                StableCode.RESYNC_REQUIRED,
                {"start_seq": 0, "accepted_count": 257, "candidate_seq": 0},
            ),
            _semantic_case(
                "pcm_sequence.uint64_gap",
                "PcmSequenceDecisionV1",
                StableCode.SEQ_GAP,
                {
                    "start_seq": "9007199254740992",
                    "accepted_count": 0,
                    "candidate_seq": "9007199254740993",
                },
            ),
            _semantic_case(
                "pcm_sequence.exhausted",
                "PcmSequenceDecisionV1",
                StableCode.RESYNC_REQUIRED,
                {
                    "start_seq": str(UINT64_MAX),
                    "accepted_count": 0,
                    "candidate_seq": str(UINT64_MAX),
                },
            ),
            _binary_case("binary.header", StableCode.BINARY_HEADER_INVALID, flags=2),
            _binary_case("binary.epoch_zero", StableCode.BINARY_HEADER_INVALID, epoch="0"),
            _binary_case(
                "binary.epoch_overflow",
                StableCode.BINARY_HEADER_INVALID,
                epoch=str(UINT64_MAX + 1),
            ),
            _binary_case(
                "binary.seq_overflow",
                StableCode.BINARY_HEADER_INVALID,
                seq=str(UINT64_MAX + 1),
            ),
            _binary_case(
                "binary.pts_overflow",
                StableCode.BINARY_HEADER_INVALID,
                pts_ms=str(UINT64_MAX + 1),
            ),
            _binary_case(
                "binary.frame_large", StableCode.BINARY_FRAME_TOO_LARGE, total_length=32_057
            ),
            _binary_case("audio.pts", StableCode.AUDIO_PTS_INVALID, previous_pts=2, pts_ms=1),
            _binary_case("audio.budget", StableCode.AUDIO_BUDGET_EXCEEDED, buffered_bytes=959_999),
            _binary_case(
                "audio.session_budget",
                StableCode.AUDIO_BUDGET_EXCEEDED,
                session_buffered_bytes=959_999,
            ),
            _binary_case(
                "binary.uint64_seq_gap",
                StableCode.SEQ_GAP,
                seq="9007199254740993",
                input_start_seq="9007199254740992",
                next_expected_seq="9007199254740992",
            ),
            _binary_case(
                "binary.sequence_exhausted",
                StableCode.RESYNC_REQUIRED,
                seq=str(UINT64_MAX),
                input_start_seq=str(UINT64_MAX),
                next_expected_seq=str(UINT64_MAX),
            ),
            _binary_case(
                "binary.seq_duplicate_precedes_pts_budget",
                StableCode.SEQ_DUPLICATE,
                seq=0,
                next_expected_seq=1,
                previous_pts=2,
                pts_ms=1,
                buffered_bytes=959_999,
            ),
            _case(
                "canonical.changed",
                "CanonicalDecisionV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                wire={"left": {"a": 1}, "right": {"a": 2}, "expect_equal": True},
            ),
            _case(
                "canonical.non_nfc",
                "TranscriptSegmentV1",
                "rejected",
                StableCode.SCHEMA_INVALID,
                raw_text=json.dumps(non_nfc, ensure_ascii=False, separators=(",", ":")),
            ),
        ],
        key=lambda item: item["case_id"],
    )


def _semantic_case(
    case_id: str, model: str, code: StableCode, wire: dict[str, Any]
) -> dict[str, Any]:
    return _case(case_id, model, "rejected", code, wire=wire)


def _canonical_raw_case(
    case_id: str, left_raw: str, right_raw: str, expect_equal: bool
) -> dict[str, Any]:
    return _case(
        case_id,
        "CanonicalRawDecisionV1",
        "accepted",
        StableCode.ACCEPTED,
        wire={"left_raw": left_raw, "right_raw": right_raw, "expect_equal": expect_equal},
    )


def _revision_case(
    case_id: str,
    code: StableCode,
    revision: int,
    projection: str,
    immutable: str,
    current_final: bool,
) -> dict[str, Any]:
    return _semantic_case(
        case_id,
        "RevisionDecisionV1",
        code,
        {
            "existing": True,
            "fill_count": 0,
            "current_revision": 1,
            "current_projection": "a",
            "current_immutable": "a",
            "current_final": current_final,
            "candidate_revision": revision,
            "candidate_projection": projection,
            "candidate_immutable": immutable,
            "candidate_final": current_final,
        },
    )


def _final_revision_case(
    case_id: str,
    expect: Literal["accepted", "rejected"],
    code: StableCode,
    candidate_revision: int,
    candidate_projection: str,
) -> dict[str, Any]:
    return _case(
        case_id,
        "RevisionDecisionV1",
        expect,
        code,
        wire={
            "existing": True,
            "fill_count": 0,
            "current_revision": 2,
            "current_projection": "final",
            "current_immutable": "a",
            "current_final": True,
            "candidate_revision": candidate_revision,
            "candidate_projection": candidate_projection,
            "candidate_immutable": "a",
            "candidate_final": True,
        },
    )


def _binary_case(case_id: str, code: StableCode, **updates: Any) -> dict[str, Any]:
    metadata = {
        "magic": "LPCM",
        "major": 1,
        "minor": 0,
        "flags": 0,
        "header_length": 56,
        "lease_id": LEASE_ID,
        "expected_lease_id": LEASE_ID,
        "epoch": 1,
        "expected_epoch": 1,
        "seq": 0,
        "input_start_seq": 0,
        "next_expected_seq": 0,
        "pts_ms": 0,
        "previous_pts": None,
        "sample_count": 1,
        "payload_length": 2,
        "total_length": 58,
        "buffered_bytes": 0,
        "session_buffered_bytes": 0,
        "process_buffered_bytes": 0,
    }
    metadata.update(updates)
    expect: Literal["accepted", "rejected"] = "accepted" if code in SUCCESS_CODES else "rejected"
    return _case(case_id, "PcmHeaderV1", expect, code, binary_header=metadata)


def all_cases() -> list[dict[str, Any]]:
    cases = [*accepted_cases(), *rejected_cases()]
    ids = [case["case_id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("golden case IDs must be unique")
    for case in cases:
        GoldenCaseV1.model_validate(case)
    return sorted(cases, key=lambda item: item["case_id"])


def _evaluate_public(case: GoldenCaseV1) -> StableCode:
    model = MODEL_BY_NAME[case.model]
    try:
        if case.raw_text is not None:
            parsed, _ = parse_control(case.raw_text, model)
        elif case.wire is not None:
            parsed = validate_object(case.wire, model)
        else:
            return StableCode.SCHEMA_INVALID
    except ProtocolValidationError as error:
        return error.code
    if isinstance(parsed, WorkerHelloV1):
        allowed = frozenset(
            {
                manifest_key(
                    WorkerHelloV1.model_validate(_public_values()["WorkerHelloV1"]).model_manifests[
                        0
                    ]
                )
            }
        )
        return negotiate_worker(parsed, allowed).decision.code
    if isinstance(parsed, ViewerSubscribeV1):
        return negotiate_viewer(parsed).decision.code
    if isinstance(parsed, LeaseV1):
        allowed_manifest = manifest_key(
            LeaseV1.model_validate(_public_values()["LeaseV1"]).model_manifest
        )
        return (
            StableCode.ACCEPTED
            if manifest_key(parsed.model_manifest) == allowed_manifest
            else StableCode.MANIFEST_NOT_ALLOWED
        )
    return StableCode.ACCEPTED


def _evaluate_sequence(wire: dict[str, Any]) -> StableCode:
    start = int(wire["start_seq"])
    accepted_count = int(wire["accepted_count"])
    if start + accepted_count > UINT64_MAX:
        return StableCode.RESYNC_REQUIRED
    window = JsonSequenceWindow(start)
    for index in range(accepted_count):
        digest = canonical_digest({"index": index})
        window.commit(index + start, MESSAGE_ID, digest)
    return window.preview(
        int(wire["candidate_seq"]),
        str(wire["candidate_message_id"]),
        canonical_digest({"index": int(wire["candidate_value_index"])}),
    ).code


def _evaluate_revision(wire: dict[str, Any]) -> StableCode:
    candidate = int(wire["candidate_revision"])
    if not bool(wire["existing"]):
        if int(wire["fill_count"]) >= 4096:
            return StableCode.REVISION_CAPACITY_EXCEEDED
        return StableCode.ACCEPTED if candidate == 1 else StableCode.REVISION_GAP
    current = int(wire["current_revision"])
    if candidate < current:
        return StableCode.REVISION_STALE
    if candidate == current and wire["candidate_projection"] == wire["current_projection"]:
        return StableCode.REVISION_DUPLICATE
    if bool(wire["current_final"]):
        return StableCode.OBJECT_FINAL
    if candidate == current:
        return StableCode.REVISION_CONFLICT
    if candidate > current + 1:
        return StableCode.REVISION_GAP
    if wire["candidate_immutable"] != wire["current_immutable"]:
        return StableCode.REVISION_IMMUTABLE
    return StableCode.ACCEPTED


def _cancel_raw(message_id: str, reason: str, **updates: Any) -> dict[str, Any]:
    raw = {
        **_worker_envelope("worker.lease_cancel", message_id),
        "lease_id": LEASE_ID,
        "session_id": SESSION_ID,
        "epoch": "1",
        "expected_revision": "1",
        "reason": reason,
    }
    raw.update(updates)
    return raw


def _evaluate_cancellation(wire: dict[str, Any]) -> StableCode:
    registry = CancellationRegistry()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    initial = wire["initial"]
    candidate = wire["candidate"]
    if initial == "closed":
        return StableCode.LEASE_CLOSED
    current_revision = 2 if candidate == "cas_stale" else 1
    if initial != "missing":
        registry.add_active(ActiveLease(LEASE_ID, SESSION_ID, 1, current_revision))
    initial_raw = _cancel_raw(MESSAGE_ID, "operator_stop")
    initial_message = LeaseCancelV1.model_validate(initial_raw)
    if initial == "cancelled":
        registry.cancel(initial_message, initial_raw, now)
    if candidate == "duplicate":
        raw = initial_raw
    elif candidate == "conflict":
        raw = _cancel_raw(MESSAGE_ID, "session_end")
    elif candidate == "binding_mismatch":
        raw = _cancel_raw(MESSAGE_ID_2, "operator_stop", session_id=WORKER_ID)
    elif candidate == "cas_stale":
        raw = _cancel_raw(MESSAGE_ID_2, "operator_stop", expected_revision="1")
    elif candidate == "cas_gap":
        raw = _cancel_raw(MESSAGE_ID_2, "operator_stop", expected_revision="2")
    else:
        raw = _cancel_raw(MESSAGE_ID_2, "operator_stop")
    message = LeaseCancelV1.model_validate(raw)
    return registry.cancel(message, raw, now).code


def _evaluate_resume(wire: dict[str, Any]) -> StableCode:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    requested = _public_values()["WorkerResumeV1"]
    live = None
    if wire["live"]:
        live = LiveWorkerCursor(
            CONNECTION_ID,
            LEASE_ID,
            SESSION_ID,
            1,
            0,
            0,
            "2025-12-31T23:59:59.000Z" if wire["expired"] else "2026-01-01T00:01:00.000Z",
        )
    return decide_worker_resume(WorkerResumeV1.model_validate(requested), live, now).code


def _evaluate_binary(metadata: dict[str, Any]) -> StableCode:
    if int(metadata["total_length"]) > 32_056:
        return StableCode.BINARY_FRAME_TOO_LARGE
    if (
        metadata["magic"] != "LPCM"
        or metadata["major"] != 1
        or metadata["minor"] != 0
        or int(metadata["flags"]) & ~1
        or metadata["header_length"] != 56
        or not 1 <= int(metadata["epoch"]) <= UINT64_MAX
        or not 0 <= int(metadata["seq"]) <= UINT64_MAX
        or not 0 <= int(metadata["pts_ms"]) <= UINT64_MAX
        or int(metadata["total_length"]) != 56 + int(metadata["payload_length"])
        or not 1 <= int(metadata["sample_count"]) <= 16_000
        or int(metadata["payload_length"]) != int(metadata["sample_count"]) * 2
    ):
        return StableCode.BINARY_HEADER_INVALID
    if metadata["lease_id"] != metadata["expected_lease_id"]:
        return StableCode.BINDING_MISMATCH
    if int(metadata["epoch"]) < int(metadata["expected_epoch"]):
        return StableCode.EPOCH_STALE
    if int(metadata["epoch"]) > int(metadata["expected_epoch"]):
        return StableCode.EPOCH_UNKNOWN
    sequence = int(metadata["seq"])
    next_expected = int(metadata["next_expected_seq"])
    oldest_replayable = max(int(metadata["input_start_seq"]), next_expected - 256)
    if sequence < oldest_replayable:
        return StableCode.RESYNC_REQUIRED
    if sequence < next_expected:
        return StableCode.SEQ_DUPLICATE
    if sequence > next_expected:
        return StableCode.SEQ_GAP
    if sequence == UINT64_MAX:
        return StableCode.RESYNC_REQUIRED
    previous = metadata["previous_pts"]
    if previous is not None and int(metadata["pts_ms"]) < int(previous):
        return StableCode.AUDIO_PTS_INVALID
    if (
        int(metadata["buffered_bytes"]) + int(metadata["payload_length"]) > 960_000
        or int(metadata["session_buffered_bytes"]) + int(metadata["payload_length"]) > 960_000
        or int(metadata["process_buffered_bytes"]) + int(metadata["payload_length"]) > 16_777_216
    ):
        return StableCode.AUDIO_BUDGET_EXCEEDED
    return StableCode.ACCEPTED


def evaluate_case(value: dict[str, Any]) -> StableCode:
    case = GoldenCaseV1.model_validate(value)
    if case.model in MODEL_BY_NAME:
        return _evaluate_public(case)
    if case.wire is not None:
        if case.model == "JsonSequenceDecisionV1":
            return _evaluate_sequence(case.wire)
        if case.model == "PcmSequenceDecisionV1":
            start = int(case.wire["start_seq"])
            next_expected = start + int(case.wire["accepted_count"])
            if next_expected > UINT64_MAX:
                return StableCode.RESYNC_REQUIRED
            candidate = int(case.wire["candidate_seq"])
            if candidate < max(start, next_expected - 256):
                return StableCode.RESYNC_REQUIRED
            if candidate < next_expected:
                return StableCode.SEQ_DUPLICATE
            if candidate > next_expected:
                return StableCode.SEQ_GAP
            return StableCode.RESYNC_REQUIRED if candidate == UINT64_MAX else StableCode.ACCEPTED
        if case.model == "EpochDecisionV1":
            current = int(case.wire["current"])
            received = int(case.wire["received"])
            if received < current:
                return StableCode.EPOCH_STALE
            if received > current:
                return StableCode.EPOCH_UNKNOWN
            return StableCode.ACCEPTED
        if case.model == "LeaseReplacementDecisionV1":
            current_epoch = int(case.wire["current_epoch"])
            replacement_epoch = int(case.wire["replacement_epoch"])
            if replacement_epoch < current_epoch:
                return StableCode.EPOCH_STALE
            if replacement_epoch == current_epoch:
                return StableCode.RESYNC_REQUIRED
            if int(case.wire.get("replacement_revision", 1)) != 1:
                return StableCode.REVISION_GAP
            is_replacement = not bool(case.wire["resumed"]) and replacement_epoch > current_epoch
            cleared = (
                not bool(case.wire["superseded_active_after"])
                and int(case.wire["retained_pcm_bytes"]) == 0
                and int(case.wire["retained_output_revisions"]) == 0
            )
            return StableCode.ACCEPTED if is_replacement and cleared else StableCode.SCHEMA_INVALID
        if case.model == "RevisionDecisionV1":
            return _evaluate_revision(case.wire)
        if case.model == "CancellationDecisionV1":
            return _evaluate_cancellation(case.wire)
        if case.model == "ResumeDecisionV1":
            return _evaluate_resume(case.wire)
        if case.model == "CanonicalDecisionV1":
            equal = canonical_digest(case.wire["left"]) == canonical_digest(case.wire["right"])
            return (
                StableCode.ACCEPTED
                if equal == bool(case.wire["expect_equal"])
                else StableCode.SCHEMA_INVALID
            )
        if case.model == "CanonicalRawDecisionV1":
            left = strict_json_loads(str(case.wire["left_raw"]))
            right = strict_json_loads(str(case.wire["right_raw"]))
            equal = canonical_digest(left) == canonical_digest(right)
            return (
                StableCode.ACCEPTED
                if equal == bool(case.wire["expect_equal"])
                else StableCode.SCHEMA_INVALID
            )
    if case.binary_header is not None and case.model == "PcmHeaderV1":
        return _evaluate_binary(case.binary_header)
    return StableCode.SCHEMA_INVALID
