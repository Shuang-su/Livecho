"""Authoritative Pydantic source for protocol v1 JSON control messages."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .scalars import (
    LanguageTag,
    ManifestText,
    NFCString,
    PositiveUint64Decimal,
    ReasonCode,
    RoomId,
    SemVerString,
    Sha256Hex,
    TimestampString,
    Uint64Decimal,
    UUID4String,
    decimal_places,
    parse_timestamp,
)

WORKER_PROTOCOL = "livecho.worker.v1"
VIEWER_PROTOCOL = "livecho.viewer.v1"
PROTOCOL_MINOR = 0
MINIMUM_WORKER_VERSION = "0.1.0"
MINIMUM_VIEWER_VERSION = "0.1.0"

Minor = Annotated[int, Field(strict=True, ge=0, le=255)]
BoundedCount = Annotated[int, Field(strict=True, ge=0, le=2_147_483_647)]
AudioBufferBytes = Annotated[int, Field(strict=True, ge=0, le=960_000)]
Milliseconds = Annotated[int, Field(strict=True, ge=0, le=2_147_483_647)]
Confidence = Annotated[float, Field(strict=True, ge=0, le=1)]
RealtimeFactor = Annotated[float, Field(strict=True, ge=0, le=100)]
RejectCode = Literal[
    "malformed_json",
    "duplicate_key",
    "unknown_field",
    "schema_invalid",
    "control_frame_too_large",
    "unknown_major",
    "unsupported_minor",
    "worker_version_too_old",
    "capability_required",
    "manifest_not_allowed",
    "lease_unknown",
    "lease_expired",
    "lease_closed",
    "binding_mismatch",
    "epoch_stale",
    "epoch_unknown",
    "seq_conflict",
    "seq_gap",
    "revision_conflict",
    "revision_stale",
    "revision_gap",
    "revision_immutable",
    "revision_capacity_exceeded",
    "cancel_conflict",
    "object_final",
    "resync_required",
    "binary_header_invalid",
    "binary_frame_too_large",
    "audio_pts_invalid",
    "audio_budget_exceeded",
]


class StrictModel(BaseModel):
    """Fail-closed base shared by every nested and envelope model."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, validate_default=True)


class ModelManifestRefV1(StrictModel):
    provider: ManifestText
    model_id: ManifestText
    revision: ManifestText
    sha256: Sha256Hex


class AudioFormatV1(StrictModel):
    encoding: Literal["pcm_s16le"]
    sample_rate_hz: Literal[16000]
    channels: Literal[1]


class WorkerResumeV1(StrictModel):
    connection_id: UUID4String
    lease_id: UUID4String
    session_id: UUID4String
    epoch: PositiveUint64Decimal
    next_input_seq: Uint64Decimal
    next_output_seq: Uint64Decimal


class ViewerCursorV1(StrictModel):
    session_id: UUID4String
    epoch: PositiveUint64Decimal
    next_seq: Uint64Decimal


class WorkerEnvelopeV1(StrictModel):
    protocol: Literal["livecho.worker.v1"]
    protocol_minor: Literal[0]
    message_id: UUID4String
    type: str
    sent_at: TimestampString


class ViewerEnvelopeV1(StrictModel):
    protocol: Literal["livecho.viewer.v1"]
    protocol_minor: Literal[0]
    message_id: UUID4String
    type: str
    sent_at: TimestampString


class EitherEnvelopeV1(StrictModel):
    protocol: Literal["livecho.worker.v1", "livecho.viewer.v1"]
    protocol_minor: Literal[0]
    message_id: UUID4String
    type: str
    sent_at: TimestampString


class WorkerHelloV1(WorkerEnvelopeV1):
    type: Literal["worker.hello"]
    worker_id: UUID4String
    worker_version: SemVerString
    supported_minors: Annotated[
        list[Minor], Field(min_length=1, max_length=16, json_schema_extra={"uniqueItems": True})
    ]
    capabilities: Annotated[
        list[Literal["asr.transcribe", "protocol.binary-pcm"]],
        Field(min_length=1, max_length=16, json_schema_extra={"uniqueItems": True}),
    ]
    model_manifests: Annotated[
        list[ModelManifestRefV1], Field(max_length=16, json_schema_extra={"uniqueItems": True})
    ]
    resume: WorkerResumeV1 | None = None

    @model_validator(mode="after")
    def unique_values(self) -> WorkerHelloV1:
        if len(set(self.supported_minors)) != len(self.supported_minors):
            raise ValueError("supported_minors must be unique")
        if len(set(self.capabilities)) != len(self.capabilities):
            raise ValueError("capabilities must be unique")
        manifests = {
            (item.provider, item.model_id, item.revision, item.sha256)
            for item in self.model_manifests
        }
        if len(manifests) != len(self.model_manifests):
            raise ValueError("model_manifests must be unique")
        return self


class WorkerWelcomeV1(WorkerEnvelopeV1):
    type: Literal["worker.welcome"]
    connection_id: UUID4String
    selected_minor: Literal[0]
    minimum_worker_version: Literal["0.1.0"]
    resume_succeeded: bool
    accepted_capabilities: Annotated[
        list[Literal["asr.transcribe", "protocol.binary-pcm"]],
        Field(min_length=2, max_length=2, json_schema_extra={"uniqueItems": True}),
    ]
    accepted_manifests: Annotated[
        list[ModelManifestRefV1], Field(max_length=16, json_schema_extra={"uniqueItems": True})
    ]

    @model_validator(mode="after")
    def exact_acceptance_sets(self) -> WorkerWelcomeV1:
        if set(self.accepted_capabilities) != {"asr.transcribe", "protocol.binary-pcm"}:
            raise ValueError("accepted_capabilities must contain both required values")
        manifests = {
            (item.provider, item.model_id, item.revision, item.sha256)
            for item in self.accepted_manifests
        }
        if len(manifests) != len(self.accepted_manifests):
            raise ValueError("accepted_manifests must be unique")
        return self


class LeaseV1(WorkerEnvelopeV1):
    type: Literal["worker.lease"]
    lease_id: UUID4String
    session_id: UUID4String
    room_id: RoomId
    epoch: PositiveUint64Decimal
    revision: PositiveUint64Decimal
    issued_at: TimestampString
    expires_at: TimestampString
    input_start_seq: Uint64Decimal
    output_start_seq: Uint64Decimal
    model_manifest: ModelManifestRefV1
    audio_format: AudioFormatV1
    audio_origin: Literal["synthetic"]

    @model_validator(mode="after")
    def valid_lifetime(self) -> LeaseV1:
        lifetime = parse_timestamp(self.expires_at) - parse_timestamp(self.issued_at)
        if lifetime.total_seconds() <= 0 or lifetime.total_seconds() > 120:
            raise ValueError("lease lifetime must be in (0, 120] seconds")
        return self


class LeaseCancelV1(WorkerEnvelopeV1):
    type: Literal["worker.lease_cancel"]
    lease_id: UUID4String
    session_id: UUID4String
    epoch: PositiveUint64Decimal
    expected_revision: PositiveUint64Decimal
    reason: Literal[
        "operator_stop",
        "lease_expired",
        "worker_replaced",
        "policy_disable",
        "protocol_violation",
        "session_end",
    ]


class HeartbeatV1(WorkerEnvelopeV1):
    type: Literal["worker.heartbeat"]
    lease_id: UUID4String
    session_id: UUID4String
    epoch: PositiveUint64Decimal
    seq: Uint64Decimal
    state: Literal["ready", "busy", "draining", "error"]
    last_input_seq: Uint64Decimal | None = None
    last_output_seq: Uint64Decimal | None = None
    audio_buffer_bytes: AudioBufferBytes
    observed_at: TimestampString


class WorkerStatsV1(WorkerEnvelopeV1):
    type: Literal["worker.stats"]
    lease_id: UUID4String
    session_id: UUID4String
    stats_id: UUID4String
    epoch: PositiveUint64Decimal
    seq: Uint64Decimal
    revision: PositiveUint64Decimal
    processed_audio_ms: Uint64Decimal
    segments_accepted: Uint64Decimal
    segments_rejected: Uint64Decimal
    realtime_factor: RealtimeFactor
    window_started_at: TimestampString
    window_ended_at: TimestampString

    @model_validator(mode="after")
    def valid_window(self) -> WorkerStatsV1:
        if parse_timestamp(self.window_ended_at) < parse_timestamp(self.window_started_at):
            raise ValueError("stats window end precedes its start")
        if decimal_places(self.realtime_factor) > 6:
            raise ValueError("realtime_factor has more than six decimal places")
        return self


class TranscriptSegmentV1(WorkerEnvelopeV1):
    type: Literal["worker.transcript"]
    lease_id: UUID4String
    session_id: UUID4String
    segment_id: UUID4String
    epoch: PositiveUint64Decimal
    seq: Uint64Decimal
    revision: PositiveUint64Decimal
    start_ms: Milliseconds
    end_ms: Milliseconds
    text: Annotated[NFCString, Field(min_length=1, max_length=4096)]
    language: LanguageTag | None = None
    confidence: Confidence | None = None
    is_final: bool

    @model_validator(mode="after")
    def valid_segment(self) -> TranscriptSegmentV1:
        if self.start_ms >= self.end_ms or self.end_ms - self.start_ms > 30_000:
            raise ValueError("segment time range is invalid")
        if self.confidence is not None and decimal_places(self.confidence) > 6:
            raise ValueError("confidence has more than six decimal places")
        return self


class TranscriptTimelinePayloadV1(StrictModel):
    segment_id: UUID4String
    start_ms: Milliseconds
    end_ms: Milliseconds
    text: Annotated[NFCString, Field(min_length=1, max_length=4096)]
    language: LanguageTag | None = None
    confidence: Confidence | None = None
    is_final: bool

    @model_validator(mode="after")
    def valid_payload(self) -> TranscriptTimelinePayloadV1:
        if self.start_ms >= self.end_ms or self.end_ms - self.start_ms > 30_000:
            raise ValueError("timeline segment time range is invalid")
        if self.confidence is not None and decimal_places(self.confidence) > 6:
            raise ValueError("confidence has more than six decimal places")
        return self


class SessionStatusTimelinePayloadV1(StrictModel):
    status: Literal["starting", "live", "stopping", "stopped", "failed"]
    reason_code: ReasonCode | None = None


class TimelineEventV1(ViewerEnvelopeV1):
    type: Literal["viewer.timeline_event"]
    event_id: UUID4String
    session_id: UUID4String
    room_id: RoomId
    epoch: PositiveUint64Decimal
    seq: Uint64Decimal
    revision: PositiveUint64Decimal
    occurred_at: TimestampString
    payload: TranscriptTimelinePayloadV1 | SessionStatusTimelinePayloadV1


class ViewerSubscribeV1(ViewerEnvelopeV1):
    type: Literal["viewer.subscribe"]
    client_version: SemVerString
    supported_minors: Annotated[
        list[Minor], Field(min_length=1, max_length=16, json_schema_extra={"uniqueItems": True})
    ]
    room_id: RoomId
    cursor: ViewerCursorV1 | None = None

    @model_validator(mode="after")
    def unique_minors(self) -> ViewerSubscribeV1:
        if len(set(self.supported_minors)) != len(self.supported_minors):
            raise ValueError("supported_minors must be unique")
        return self


class ViewerReadyV1(ViewerEnvelopeV1):
    type: Literal["viewer.ready"]
    selected_minor: Literal[0]
    minimum_client_version: Literal["0.1.0"]
    session_id: UUID4String
    epoch: PositiveUint64Decimal
    next_seq: Uint64Decimal
    cursor_resumed: bool


class ProtocolAckV1(EitherEnvelopeV1):
    type: Literal["protocol.ack"]
    outcome: Literal["accepted", "seq_duplicate", "revision_duplicate", "cancel_duplicate"]
    acknowledged_message_id: UUID4String
    seq: Uint64Decimal | None = None
    revision: PositiveUint64Decimal | None = None
    expected_revision: PositiveUint64Decimal | None = None

    @model_validator(mode="after")
    def applicable_position(self) -> ProtocolAckV1:
        if self.seq is None and self.revision is None and self.expected_revision is None:
            raise ValueError("ack requires a sequence, revision, or CAS value")
        return self


class ProtocolErrorV1(EitherEnvelopeV1):
    type: Literal["protocol.error"]
    code: RejectCode
    message: Annotated[NFCString, Field(min_length=1, max_length=160)]
    retryable: bool
    expected: Uint64Decimal | None = None
    received: Uint64Decimal | None = None

    @model_validator(mode="after")
    def rejection_only(self) -> ProtocolErrorV1:
        return self


type ProtocolMessageV1 = (
    WorkerHelloV1
    | WorkerWelcomeV1
    | LeaseV1
    | LeaseCancelV1
    | HeartbeatV1
    | WorkerStatsV1
    | TranscriptSegmentV1
    | TimelineEventV1
    | ViewerSubscribeV1
    | ViewerReadyV1
    | ProtocolAckV1
    | ProtocolErrorV1
)

PUBLIC_MODELS: tuple[type[StrictModel], ...] = (
    AudioFormatV1,
    HeartbeatV1,
    LeaseCancelV1,
    LeaseV1,
    ModelManifestRefV1,
    ProtocolAckV1,
    ProtocolErrorV1,
    SessionStatusTimelinePayloadV1,
    TimelineEventV1,
    TranscriptSegmentV1,
    TranscriptTimelinePayloadV1,
    ViewerCursorV1,
    ViewerReadyV1,
    ViewerSubscribeV1,
    WorkerHelloV1,
    WorkerResumeV1,
    WorkerStatsV1,
    WorkerWelcomeV1,
)
MODEL_BY_NAME: dict[str, type[StrictModel]] = {model.__name__: model for model in PUBLIC_MODELS}
