"""Worker-identity records for the Issue #13 memory adapter.

Plaintext enrollment tokens, private keys, nonces, and rate-limit buckets are
not fields on these records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Literal

ENROLLMENT_TTL = timedelta(hours=24)
CHALLENGE_TTL = timedelta(seconds=120)
REQUEST_QUOTA = 30
QUOTA_WINDOW = timedelta(minutes=15)
IP_FALLBACK = "missing-peer"
FAMILY_DEVICES = "devices"
FAMILY_CHALLENGES = "challenges"

AuditResult = Literal[
    "ok",
    "enrollment_pending",
    "account_ineligible",
    "not_found",
    "invalid_body",
    "unavailable",
    "rejected",
    "capability_rejected",
    "signature_invalid",
    "device_revoked",
    "rate_limited",
]
ObjectClass = Literal["enrollment", "device", "hello", "statistics"]
HealthState = Literal["ready", "busy", "draining", "error"]


class DeviceStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True, repr=False)
class Enrollment:
    enrollment_id: str
    account_id: str
    verifier: bytes
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None

    def __repr__(self) -> str:
        used = self.used_at is not None
        return (
            f"Enrollment(enrollment_id={self.enrollment_id!r}, "
            f"account_id={self.account_id!r}, used={used})"
        )


@dataclass(frozen=True, slots=True, repr=False)
class Device:
    device_id: str
    account_id: str
    public_key: bytes
    status: DeviceStatus
    created_at: datetime
    revoked_at: datetime | None

    def __repr__(self) -> str:
        return (
            f"Device(device_id={self.device_id!r}, account_id={self.account_id!r}, "
            f"status={self.status.value!r})"
        )


@dataclass(frozen=True, slots=True, repr=False)
class Challenge:
    challenge_id: str
    device_id: str
    nonce: bytes | None
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None

    def __repr__(self) -> str:
        return (
            f"Challenge(challenge_id={self.challenge_id!r}, "
            f"device_id={self.device_id!r}, used={self.used_at is not None})"
        )


@dataclass(frozen=True, slots=True)
class Admission:
    device_id: str
    expires_at: datetime
    consumed_at: datetime | None


@dataclass(frozen=True, slots=True)
class AllowlistEntry:
    provider: str
    model_id: str
    revision: str
    sha256: str

    def key(self) -> tuple[str, str, str, str]:
        return (self.provider, self.model_id, self.revision, self.sha256)

    def body(self) -> dict[str, str]:
        return {
            "provider": self.provider,
            "model_id": self.model_id,
            "revision": self.revision,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class Statistic:
    online_duration_seconds: int = 0
    processed_audio_ms: int = 0
    segments_accepted: int = 0
    segments_rejected: int = 0
    rtf: str | None = None
    health_state: HealthState | None = None
    health_observed_at: datetime | None = None
    stats_initialized: bool = False


@dataclass(frozen=True, slots=True)
class AuditRecord:
    time: datetime
    action: str
    result: AuditResult
    object_class: ObjectClass
    account_id: str | None = None
    device_id: str | None = None
