"""Stable, payload-free protocol decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class StableCode(StrEnum):
    """Stable outcomes shared by Python, TypeScript, and the wire contract."""

    ACCEPTED = "accepted"
    MALFORMED_JSON = "malformed_json"
    DUPLICATE_KEY = "duplicate_key"
    UNKNOWN_FIELD = "unknown_field"
    SCHEMA_INVALID = "schema_invalid"
    CONTROL_FRAME_TOO_LARGE = "control_frame_too_large"
    UNKNOWN_MAJOR = "unknown_major"
    UNSUPPORTED_MINOR = "unsupported_minor"
    WORKER_VERSION_TOO_OLD = "worker_version_too_old"
    CAPABILITY_REQUIRED = "capability_required"
    MANIFEST_NOT_ALLOWED = "manifest_not_allowed"
    LEASE_UNKNOWN = "lease_unknown"
    LEASE_EXPIRED = "lease_expired"
    LEASE_CLOSED = "lease_closed"
    BINDING_MISMATCH = "binding_mismatch"
    EPOCH_STALE = "epoch_stale"
    EPOCH_UNKNOWN = "epoch_unknown"
    SEQ_DUPLICATE = "seq_duplicate"
    SEQ_CONFLICT = "seq_conflict"
    SEQ_GAP = "seq_gap"
    REVISION_DUPLICATE = "revision_duplicate"
    CANCEL_DUPLICATE = "cancel_duplicate"
    REVISION_CONFLICT = "revision_conflict"
    REVISION_STALE = "revision_stale"
    REVISION_GAP = "revision_gap"
    REVISION_IMMUTABLE = "revision_immutable"
    REVISION_CAPACITY_EXCEEDED = "revision_capacity_exceeded"
    CANCEL_CONFLICT = "cancel_conflict"
    OBJECT_FINAL = "object_final"
    RESYNC_REQUIRED = "resync_required"
    BINARY_HEADER_INVALID = "binary_header_invalid"
    BINARY_FRAME_TOO_LARGE = "binary_frame_too_large"
    AUDIO_PTS_INVALID = "audio_pts_invalid"
    AUDIO_BUDGET_EXCEEDED = "audio_budget_exceeded"


SUCCESS_CODES = frozenset(
    {
        StableCode.ACCEPTED,
        StableCode.SEQ_DUPLICATE,
        StableCode.REVISION_DUPLICATE,
        StableCode.CANCEL_DUPLICATE,
    }
)


@dataclass(frozen=True, slots=True)
class Decision:
    """One deterministic protocol result without diagnostics or input reflection."""

    code: StableCode

    @property
    def accepted(self) -> bool:
        return self.code in SUCCESS_CODES


class ProtocolValidationError(ValueError):
    """Internal exception carrying only a stable public code."""

    def __init__(self, code: StableCode) -> None:
        super().__init__(code.value)
        self.code = code
