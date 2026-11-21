"""Process-local enrollment, device, challenge, and statistics store."""

from __future__ import annotations

import hmac
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from threading import Lock

from .crypto import challenge_message, verify_signature
from .records import (
    QUOTA_WINDOW,
    REQUEST_QUOTA,
    Admission,
    AllowlistEntry,
    AuditRecord,
    Challenge,
    Device,
    DeviceStatus,
    Enrollment,
    HealthState,
    Statistic,
)

AccountActive = Callable[[str], bool]
Negotiation = tuple[str, bool, int | None]
Negotiate = Callable[[frozenset[tuple[str, str, str, str]]], Negotiation]


class IssueKind(StrEnum):
    CREATED = "created"
    PENDING = "pending"
    UNAVAILABLE = "unavailable"


class RedeemKind(StrEnum):
    CREATED = "created"
    UNKNOWN = "unknown"
    REJECTED = "rejected"
    INELIGIBLE = "ineligible"
    UNAVAILABLE = "unavailable"


class ChallengeKind(StrEnum):
    ISSUED = "issued"
    UNKNOWN = "unknown"
    REVOKED = "revoked"
    QUOTA = "quota"
    UNAVAILABLE = "unavailable"


class VerifyKind(StrEnum):
    OK = "ok"
    SIGNATURE_INVALID = "signature_invalid"
    DEVICE_REVOKED = "device_revoked"
    REJECTED = "rejected"


class RevokeKind(StrEnum):
    REVOKED = "revoked"
    ALREADY = "already"
    UNKNOWN = "unknown"


class UpdateKind(StrEnum):
    OK = "ok"
    STALE = "stale"
    REJECTED = "rejected"
    DEVICE_REVOKED = "device_revoked"


class MemoryWorkerIdentityStore:
    """One process-local worker-identity adapter. It has no backup."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._enrollments: dict[str, Enrollment] = {}
        self._devices: dict[str, Device] = {}
        self._stats: dict[str, Statistic] = {}
        self._challenges: dict[str, Challenge] = {}
        self._admissions: dict[str, Admission] = {}
        self._allowlist: dict[tuple[str, str, str, str], AllowlistEntry] = {}
        self._audits: list[AuditRecord] = []
        self._ip_hits: dict[tuple[str, str], list[datetime]] = {}
        self._challenge_times: dict[str, list[datetime]] = {}

    def try_issue(
        self,
        enrollment: Enrollment,
    ) -> IssueKind:
        """Insert one token unless this account already has a live unused token."""
        with self._lock:
            if enrollment.enrollment_id in self._enrollments:
                return IssueKind.UNAVAILABLE
            if self._pending(enrollment.account_id, enrollment.created_at):
                return IssueKind.PENDING
            self._enrollments[enrollment.enrollment_id] = enrollment
            return IssueKind.CREATED

    def redeem(
        self,
        *,
        verifier: bytes,
        now: datetime,
        account_active: AccountActive,
        device_id: str,
        public_key: bytes,
    ) -> tuple[RedeemKind, str | None, Device | None]:
        """Consume a matching live token and, when the account is eligible, store a device."""
        with self._lock:
            row = self._match_enrollment(verifier)
            if row is None:
                return RedeemKind.UNKNOWN, None, None
            if row.used_at is not None or now >= row.expires_at:
                return RedeemKind.REJECTED, row.account_id, None
            if device_id in self._devices:
                return RedeemKind.UNAVAILABLE, row.account_id, None
            self._enrollments[row.enrollment_id] = Enrollment(
                enrollment_id=row.enrollment_id,
                account_id=row.account_id,
                verifier=row.verifier,
                created_at=row.created_at,
                expires_at=row.expires_at,
                used_at=now,
            )
            if not account_active(row.account_id):
                return RedeemKind.INELIGIBLE, row.account_id, None
            device = Device(
                device_id=device_id,
                account_id=row.account_id,
                public_key=public_key,
                status=DeviceStatus.ACTIVE,
                created_at=now,
                revoked_at=None,
            )
            self._devices[device_id] = device
            self._stats[device_id] = Statistic()
            return RedeemKind.CREATED, row.account_id, device

    def consume_ip(self, family: str, ip: str, now: datetime) -> bool:
        """Count one request. Return False when the rolling window is already over quota."""
        with self._lock:
            self._evict_idle_buckets(now)
            key = (family, ip)
            hits = [item for item in self._ip_hits.get(key, []) if now - item < QUOTA_WINDOW]
            hits.append(now)
            self._ip_hits[key] = hits
            return len(hits) <= REQUEST_QUOTA

    def issue_challenge(
        self,
        *,
        device_id: str,
        now: datetime,
        account_active: AccountActive,
        challenge_id: str,
        nonce: bytes,
        expires_at: datetime,
    ) -> tuple[ChallengeKind, Challenge | None]:
        """Store one challenge, retiring older unused challenges for that device."""
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                return ChallengeKind.UNKNOWN, None
            if device.status is not DeviceStatus.ACTIVE or not account_active(device.account_id):
                return ChallengeKind.REVOKED, None
            if not self._quota_open(device_id, now):
                return ChallengeKind.QUOTA, None
            if challenge_id in self._challenges:
                return ChallengeKind.UNAVAILABLE, None
            self._retire_challenges(device_id, now)
            challenge = Challenge(
                challenge_id=challenge_id,
                device_id=device_id,
                nonce=nonce,
                created_at=now,
                expires_at=expires_at,
                used_at=None,
            )
            self._challenges[challenge_id] = challenge
            times = self._challenge_times.get(device_id, [])
            times.append(now)
            self._challenge_times[device_id] = times
            return ChallengeKind.ISSUED, challenge

    def verify(
        self,
        *,
        challenge_id: str,
        device_id: str,
        signature: bytes,
        now: datetime,
        account_active: AccountActive,
    ) -> tuple[VerifyKind, str | None, str | None]:
        """Check one signature. A failed check of a live challenge consumes it."""
        with self._lock:
            challenge = self._challenges.get(challenge_id)
            if challenge is None:
                return VerifyKind.REJECTED, None, None
            device = self._devices.get(challenge.device_id)
            if device is None:
                return VerifyKind.REJECTED, None, None
            unused = challenge.used_at is None and challenge.nonce is not None
            live = unused and now < challenge.expires_at
            if device.status is not DeviceStatus.ACTIVE or not account_active(device.account_id):
                if unused:
                    self._consume_challenge(challenge, now)
                return VerifyKind.DEVICE_REVOKED, device.account_id, device.device_id
            if not live or device_id != challenge.device_id:
                if unused:
                    self._consume_challenge(challenge, now)
                return VerifyKind.SIGNATURE_INVALID, device.account_id, device.device_id
            nonce = challenge.nonce
            if nonce is None:
                return VerifyKind.SIGNATURE_INVALID, device.account_id, device.device_id
            message = challenge_message(device_id, challenge_id, nonce)
            ok = verify_signature(device.public_key, signature, message)
            self._consume_challenge(challenge, now)
            if not ok:
                return VerifyKind.SIGNATURE_INVALID, device.account_id, device.device_id
            self._admissions[device.device_id] = Admission(
                device_id=device.device_id,
                expires_at=challenge.expires_at,
                consumed_at=None,
            )
            return VerifyKind.OK, device.account_id, device.device_id

    def decide_hello(
        self,
        *,
        device_id: str,
        worker_id: str,
        now: datetime,
        account_active: AccountActive,
        negotiate: Negotiate,
    ) -> tuple[str, str, int | None, str | None]:
        """Apply Hello precedence. Return audit result, protocol code, minor, account id."""
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                return "rejected", "rejected", None, None
            active = device.status is DeviceStatus.ACTIVE and account_active(device.account_id)
            if not active:
                self._consume_live_admission(device_id, now)
                return "device_revoked", "device_revoked", None, device.account_id
            if worker_id != device_id or not self._admission_live(device_id, now):
                self._consume_live_admission(device_id, now)
                return "signature_invalid", "signature_invalid", None, device.account_id
            code, accepted, minor = negotiate(self._allowlist_keys())
            self._consume_live_admission(device_id, now)
            if not accepted:
                if code in {"manifest_not_allowed", "capability_required"}:
                    return "capability_rejected", code, None, device.account_id
                return "rejected", code, None, device.account_id
            return "ok", code, minor, device.account_id

    def revoke(self, device_id: str, now: datetime) -> tuple[RevokeKind, Device | None]:
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                return RevokeKind.UNKNOWN, None
            self._retire_challenges(device_id, now)
            if device.status is DeviceStatus.REVOKED:
                return RevokeKind.ALREADY, device
            updated = Device(
                device_id=device.device_id,
                account_id=device.account_id,
                public_key=device.public_key,
                status=DeviceStatus.REVOKED,
                created_at=device.created_at,
                revoked_at=now,
            )
            self._devices[device_id] = updated
            return RevokeKind.REVOKED, updated

    def add_allowlist(self, entry: AllowlistEntry) -> bool:
        """Return True when the tuple was inserted."""
        with self._lock:
            key = entry.key()
            if key in self._allowlist:
                return False
            self._allowlist[key] = entry
            return True

    def remove_allowlist(self, key: tuple[str, str, str, str]) -> bool:
        with self._lock:
            if key not in self._allowlist:
                return False
            del self._allowlist[key]
            return True

    def allowlist(self) -> tuple[AllowlistEntry, ...]:
        with self._lock:
            return tuple(self._allowlist[key] for key in sorted(self._allowlist))

    def apply_stats(
        self,
        *,
        device_id: str,
        account_active: AccountActive,
        processed_audio_ms: int,
        segments_accepted: int,
        segments_rejected: int,
        rtf: str,
    ) -> UpdateKind:
        with self._lock:
            kind = self._writable(device_id, account_active)
            if kind is not UpdateKind.OK:
                return kind
            current = self._stats[device_id]
            if current.stats_initialized and (
                processed_audio_ms < current.processed_audio_ms
                or segments_accepted < current.segments_accepted
                or segments_rejected < current.segments_rejected
            ):
                return UpdateKind.REJECTED
            self._stats[device_id] = Statistic(
                online_duration_seconds=current.online_duration_seconds,
                processed_audio_ms=processed_audio_ms,
                segments_accepted=segments_accepted,
                segments_rejected=segments_rejected,
                rtf=rtf,
                health_state=current.health_state,
                health_observed_at=current.health_observed_at,
                stats_initialized=True,
            )
            return UpdateKind.OK

    def apply_health(
        self,
        *,
        device_id: str,
        account_active: AccountActive,
        state: HealthState,
        observed_at: datetime,
    ) -> UpdateKind:
        with self._lock:
            kind = self._writable(device_id, account_active)
            if kind is not UpdateKind.OK:
                return kind
            current = self._stats[device_id]
            if current.health_observed_at is not None and observed_at < current.health_observed_at:
                return UpdateKind.STALE
            self._stats[device_id] = Statistic(
                online_duration_seconds=current.online_duration_seconds,
                processed_audio_ms=current.processed_audio_ms,
                segments_accepted=current.segments_accepted,
                segments_rejected=current.segments_rejected,
                rtf=current.rtf,
                health_state=state,
                health_observed_at=observed_at,
                stats_initialized=current.stats_initialized,
            )
            return UpdateKind.OK

    def apply_online(
        self,
        *,
        device_id: str,
        account_active: AccountActive,
        whole_seconds: int,
    ) -> UpdateKind:
        with self._lock:
            kind = self._writable(device_id, account_active)
            if kind is not UpdateKind.OK:
                return kind
            if whole_seconds < 0:
                return UpdateKind.REJECTED
            current = self._stats[device_id]
            self._stats[device_id] = Statistic(
                online_duration_seconds=current.online_duration_seconds + whole_seconds,
                processed_audio_ms=current.processed_audio_ms,
                segments_accepted=current.segments_accepted,
                segments_rejected=current.segments_rejected,
                rtf=current.rtf,
                health_state=current.health_state,
                health_observed_at=current.health_observed_at,
                stats_initialized=current.stats_initialized,
            )
            return UpdateKind.OK

    def add_audit(self, record: AuditRecord) -> None:
        with self._lock:
            self._audits.append(record)

    def audits(self) -> tuple[AuditRecord, ...]:
        with self._lock:
            return tuple(self._audits)

    def enrollments(self) -> tuple[Enrollment, ...]:
        with self._lock:
            return tuple(self._enrollments[key] for key in sorted(self._enrollments))

    def device(self, device_id: str) -> Device | None:
        with self._lock:
            return self._devices.get(device_id)

    def devices_for(self, account_id: str) -> tuple[Device, ...]:
        with self._lock:
            matched = [
                device for device in self._devices.values() if device.account_id == account_id
            ]
            return tuple(sorted(matched, key=lambda device: device.device_id))

    def statistic(self, device_id: str) -> Statistic | None:
        with self._lock:
            return self._stats.get(device_id)

    def challenges_for(self, device_id: str) -> tuple[Challenge, ...]:
        with self._lock:
            matched = [
                challenge
                for challenge in self._challenges.values()
                if challenge.device_id == device_id
            ]
            return tuple(sorted(matched, key=lambda challenge: challenge.challenge_id))

    def _match_enrollment(self, verifier: bytes) -> Enrollment | None:
        found: Enrollment | None = None
        for row in self._enrollments.values():
            if hmac.compare_digest(row.verifier, verifier):
                found = row
        return found

    def _pending(self, account_id: str, now: datetime) -> bool:
        return any(
            row.account_id == account_id and row.used_at is None and now < row.expires_at
            for row in self._enrollments.values()
        )

    def _quota_open(self, device_id: str, now: datetime) -> bool:
        hits = [
            item for item in self._challenge_times.get(device_id, []) if now - item < QUOTA_WINDOW
        ]
        self._challenge_times[device_id] = hits
        return len(hits) < REQUEST_QUOTA

    def _retire_challenges(self, device_id: str, now: datetime) -> None:
        for challenge in list(self._challenges.values()):
            if challenge.device_id == device_id and challenge.used_at is None:
                self._consume_challenge(challenge, now)
        self._admissions.pop(device_id, None)

    def _consume_challenge(self, challenge: Challenge, now: datetime) -> None:
        self._challenges[challenge.challenge_id] = Challenge(
            challenge_id=challenge.challenge_id,
            device_id=challenge.device_id,
            nonce=None,
            created_at=challenge.created_at,
            expires_at=challenge.expires_at,
            used_at=challenge.used_at or now,
        )

    def _admission_live(self, device_id: str, now: datetime) -> bool:
        admission = self._admissions.get(device_id)
        return (
            admission is not None and admission.consumed_at is None and now < admission.expires_at
        )

    def _consume_live_admission(self, device_id: str, now: datetime) -> None:
        admission = self._admissions.get(device_id)
        if admission is None or admission.consumed_at is not None or now >= admission.expires_at:
            return
        self._admissions[device_id] = Admission(
            device_id=device_id,
            expires_at=admission.expires_at,
            consumed_at=now,
        )

    def _allowlist_keys(self) -> frozenset[tuple[str, str, str, str]]:
        return frozenset(self._allowlist)

    def _writable(self, device_id: str, account_active: AccountActive) -> UpdateKind:
        device = self._devices.get(device_id)
        if device is None:
            return UpdateKind.REJECTED
        if device.status is not DeviceStatus.ACTIVE or not account_active(device.account_id):
            return UpdateKind.DEVICE_REVOKED
        return UpdateKind.OK

    def _evict_idle_buckets(self, now: datetime) -> None:
        idle = [
            key for key, hits in self._ip_hits.items() if not hits or now - hits[-1] >= QUOTA_WINDOW
        ]
        for key in idle:
            del self._ip_hits[key]
