"""Pure, I/O-free wire builders and parsers for the worker gateway (Issue #14)."""

from __future__ import annotations

from typing import Any

from livecho_protocol.errors import ProtocolValidationError, StableCode
from livecho_protocol.models import (
    HeartbeatV1,
    HeartbeatV1Minor1,
    LeaseCancelV1,
    LeaseCancelV1Minor1,
    LeaseV1,
    LeaseV1Minor1,
    ModelManifestRefV1,
    ProtocolAckV1,
    ProtocolAckV1Minor1,
    ProtocolErrorV1,
    ProtocolErrorV1Minor1,
    TranscriptSegmentV1,
    TranscriptSegmentV1Minor1,
    WorkerStatsV1,
    WorkerStatsV1Minor1,
    WorkerWelcomeV1,
    WorkerWelcomeV1Minor1,
)
from livecho_protocol.parser import strict_json_loads, validate_object
from pydantic import ValidationError

type WorkerOutput = HeartbeatV1 | WorkerStatsV1 | TranscriptSegmentV1

_OUTPUT_MODELS: dict[int, dict[str, type[WorkerOutput]]] = {
    0: {
        "worker.heartbeat": HeartbeatV1,
        "worker.stats": WorkerStatsV1,
        "worker.transcript": TranscriptSegmentV1,
    },
    1: {
        "worker.heartbeat": HeartbeatV1Minor1,
        "worker.stats": WorkerStatsV1Minor1,
        "worker.transcript": TranscriptSegmentV1Minor1,
    },
}

CAPABILITIES_MINOR0 = ["asr.transcribe", "protocol.binary-pcm"]
CAPABILITIES_MINOR1 = ["asr.transcribe", "protocol.binary-pcm", "protocol.epoch-rotation"]
SYNTHETIC_AUDIO_FORMAT: dict[str, Any] = {
    "encoding": "pcm_s16le",
    "sample_rate_hz": 16000,
    "channels": 1,
}
CURRENT_EPOCH = "1"
CURRENT_REVISION = "1"


def _code_value(code: StableCode | str) -> str:
    return code.value if isinstance(code, StableCode) else str(code)


def parse_output(text: str, minor: int) -> tuple[WorkerOutput, dict[str, Any]]:
    raw = strict_json_loads(text)
    kind = raw.get("type")
    models = _OUTPUT_MODELS.get(minor)
    model = models.get(kind) if models is not None and isinstance(kind, str) else None
    if model is None:
        raise ProtocolValidationError(StableCode.SCHEMA_INVALID)
    return validate_object(raw, model), raw


def welcome(
    fields: dict[str, Any],
    *,
    minor: int,
    connection_id: str,
    resumed: bool,
    manifests: list[ModelManifestRefV1],
) -> WorkerWelcomeV1:
    model = WorkerWelcomeV1Minor1 if minor == 1 else WorkerWelcomeV1
    return model.model_validate(
        {
            **fields,
            "connection_id": connection_id,
            "selected_minor": minor,
            "minimum_worker_version": "0.1.0",
            "resume_succeeded": resumed,
            "accepted_capabilities": CAPABILITIES_MINOR1 if minor == 1 else CAPABILITIES_MINOR0,
            "accepted_manifests": [m.model_dump(mode="json") for m in manifests],
        }
    )


def lease(
    fields: dict[str, Any],
    *,
    minor: int,
    lease_id: str,
    session_id: str,
    room_id: str,
    issued_at: str,
    expires_at: str,
    manifest: ModelManifestRefV1,
) -> LeaseV1:
    model = LeaseV1Minor1 if minor == 1 else LeaseV1
    start = "1" if minor == 1 else "0"
    return model.model_validate(
        {
            **fields,
            "lease_id": lease_id,
            "session_id": session_id,
            "room_id": room_id,
            "epoch": CURRENT_EPOCH,
            "revision": CURRENT_REVISION,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "input_start_seq": start,
            "output_start_seq": start,
            "model_manifest": manifest.model_dump(mode="json"),
            "audio_format": dict(SYNTHETIC_AUDIO_FORMAT),
            "audio_origin": "synthetic",
        }
    )


def error(fields: dict[str, Any], *, minor: int, code: str) -> ProtocolErrorV1:
    model = ProtocolErrorV1Minor1 if minor == 1 else ProtocolErrorV1
    retryable_codes = {"resync_required", "epoch_rotated"} if minor == 1 else {"resync_required"}

    def build(value: str) -> ProtocolErrorV1:
        return model.model_validate(
            {**fields, "code": value, "message": value, "retryable": value in retryable_codes}
        )

    value = _code_value(code)
    try:
        return build(value)
    except ValidationError:
        return build(StableCode.SCHEMA_INVALID.value)


def ack(
    fields: dict[str, Any], *, minor: int, message: WorkerOutput, outcome: StableCode
) -> ProtocolAckV1:
    model = ProtocolAckV1Minor1 if minor == 1 else ProtocolAckV1
    value = _code_value(outcome)
    revision = getattr(message, "revision", None)
    data: dict[str, Any] = {
        **fields,
        "outcome": value,
        "acknowledged_message_id": message.message_id,
        "seq": message.seq,
    }
    if value in ("accepted", "revision_duplicate") and revision is not None:
        data["revision"] = revision
    return model.model_validate(data)


def cancel(
    fields: dict[str, Any], *, minor: int, active_lease: LeaseV1, revision: int, reason: str
) -> LeaseCancelV1:
    model = LeaseCancelV1Minor1 if minor == 1 else LeaseCancelV1
    return model.model_validate(
        {
            **fields,
            "lease_id": active_lease.lease_id,
            "session_id": active_lease.session_id,
            "epoch": active_lease.epoch,
            "expected_revision": str(revision),
            "reason": reason,
        }
    )
