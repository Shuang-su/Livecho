"""Enrollment, device proof, Hello admission, and contribution statistics."""

from __future__ import annotations

import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_DOWN, Decimal
from typing import Protocol, cast
from urllib.parse import parse_qsl
from uuid import uuid4

from livecho_protocol.compatibility import negotiate_worker
from livecho_protocol.errors import StableCode
from livecho_protocol.models import ModelManifestRefV1, WorkerHelloV1, WorkerStatsV1
from livecho_protocol.scalars import UUID4_PATTERN
from pydantic import ValidationError

from livecho_backend.auth.crypto import encode_secret
from livecho_backend.auth.policy import Action, Decision, authorize
from livecho_backend.auth.records import Account, AccountStatus, Principal, Role

from .clock import format_timestamp, utc_millis
from .crypto import (
    acceptable_public_key,
    decode_unpadded,
    enrollment_verifier,
)
from .log import log_worker
from .records import (
    CHALLENGE_TTL,
    ENROLLMENT_TTL,
    FAMILY_CHALLENGES,
    FAMILY_DEVICES,
    IP_FALLBACK,
    AllowlistEntry,
    AuditRecord,
    AuditResult,
    Device,
    DeviceStatus,
    Enrollment,
    HealthState,
    ObjectClass,
)
from .store import (
    ChallengeKind,
    IssueKind,
    MemoryWorkerIdentityStore,
    Negotiate,
    RedeemKind,
    RevokeKind,
    UpdateKind,
    VerifyKind,
)

Clock = Callable[[], datetime]
RandomBytes = Callable[[int], bytes]
NewId = Callable[[], str]
PrincipalResolver = Callable[[str | None], Principal | None]
_HEALTH: frozenset[str] = frozenset({"ready", "busy", "draining", "error"})


class AccountLookup(Protocol):
    """Read-only account port. Issue #12's memory store satisfies it."""

    def account_by_id(self, account_id: str) -> Account | None: ...


class _EmptyAccounts:
    def account_by_id(self, account_id: str) -> Account | None:
        return None


@dataclass(frozen=True, slots=True)
class ApiResult:
    status: int
    payload: dict[str, object] | list[dict[str, object]] | None = None


@dataclass(frozen=True, slots=True)
class HelloDecision:
    accepted: bool
    protocol_code: str
    audit_result: str
    selected_minor: int | None = None


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid4())


def _error(status: int, code: str) -> ApiResult:
    return ApiResult(status, {"error": code})


def _active_contributor(account: Account | None) -> bool:
    return (
        account is not None
        and account.role is Role.CONTRIBUTOR
        and account.status is AccountStatus.ACTIVE
    )


def is_uuid4(value: object) -> bool:
    return isinstance(value, str) and UUID4_PATTERN.fullmatch(value) is not None


def format_success_rate(accepted: int, rejected: int) -> str | None:
    """Truncate ``accepted / (accepted + rejected)`` toward zero, to six places."""
    total = accepted + rejected
    if total == 0:
        return None
    quotient = Decimal(accepted) / Decimal(total)
    truncated = quotient.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
    return _trim_decimal(format(truncated, "f"))


def format_decimal(value: float) -> str:
    """Copy a short JSON number into a decimal string without trailing zeros."""
    return _trim_decimal(format(Decimal(str(value)), "f"))


def _trim_decimal(text: str) -> str:
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


class WorkerIdentityService:
    """Coordinates the memory adapter. It does not read the process environment."""

    def __init__(
        self,
        store: MemoryWorkerIdentityStore,
        accounts: AccountLookup,
        *,
        enrollment_key: bytes | None = None,
        clock: Clock | None = None,
        random_bytes: RandomBytes | None = None,
        new_id: NewId | None = None,
    ) -> None:
        self.store = store
        self.accounts = accounts
        self._enrollment_key = enrollment_key
        self._clock = clock or _now
        self._random_bytes = random_bytes or secrets.token_bytes
        self._new_id = new_id or _new_id

    def issue_enrollment(self, principal: Principal | None, raw_body: bytes) -> ApiResult:
        denied = self._denied(principal, Action.DEVICE_ISSUE_ENROLLMENT, "-")
        if denied is not None:
            return denied
        assert principal is not None
        parsed = _object(raw_body, frozenset({"account_id"}))
        account_id = None if parsed is None else parsed.get("account_id")
        if not is_uuid4(account_id):
            self._record("device.issue_enrollment", "invalid_body", "enrollment", principal)
            return _error(422, "invalid_body")
        assert isinstance(account_id, str)
        if self._key() is None:
            self._record(
                "device.issue_enrollment",
                "unavailable",
                "enrollment",
                principal,
                target=account_id,
            )
            return _error(503, "unavailable")
        account = self.accounts.account_by_id(account_id)
        if account is None:
            self._record(
                "device.issue_enrollment",
                "not_found",
                "enrollment",
                principal,
                target=account_id,
                audit_account=False,
            )
            return _error(404, "not_found")
        if not _active_contributor(account):
            self._record(
                "device.issue_enrollment",
                "account_ineligible",
                "enrollment",
                principal,
                target=account_id,
            )
            return _error(409, "account_ineligible")
        token = self._random(32)
        verifier_key = self._key()
        if token is None or verifier_key is None:
            self._record(
                "device.issue_enrollment",
                "unavailable",
                "enrollment",
                principal,
                target=account_id,
            )
            return _error(503, "unavailable")
        now = self._instant()
        enrollment_id = self._new_id()
        kind = self.store.try_issue(
            Enrollment(
                enrollment_id=enrollment_id,
                account_id=account_id,
                verifier=enrollment_verifier(verifier_key, token),
                created_at=now,
                expires_at=now + ENROLLMENT_TTL,
                used_at=None,
            )
        )
        if kind is IssueKind.PENDING:
            self._record(
                "device.issue_enrollment",
                "enrollment_pending",
                "enrollment",
                principal,
                target=account_id,
            )
            return _error(409, "enrollment_pending")
        if kind is not IssueKind.CREATED:
            self._record(
                "device.issue_enrollment",
                "unavailable",
                "enrollment",
                principal,
                target=account_id,
            )
            return _error(503, "unavailable")
        self._record("device.issue_enrollment", "ok", "enrollment", principal, target=account_id)
        return ApiResult(
            201,
            {
                "enrollment_id": enrollment_id,
                "account_id": account_id,
                "expires_at": format_timestamp(now + ENROLLMENT_TTL),
                "token": encode_secret(token),
            },
        )

    def enroll_device(self, raw_body: bytes, client_ip: str) -> ApiResult:
        now = self._instant()
        if not self.store.consume_ip(FAMILY_DEVICES, _peer(client_ip), now):
            self._audit("device.enroll", "rate_limited", "enrollment", now=now)
            return _error(401, "rejected")
        parsed = _object(raw_body, frozenset({"token", "public_key"}))
        token = None if parsed is None else decode_unpadded(parsed.get("token"), 32)
        public_key = None if parsed is None else decode_unpadded(parsed.get("public_key"), 32)
        if token is None or public_key is None or not acceptable_public_key(public_key):
            self._audit("device.enroll", "invalid_body", "enrollment", now=now)
            return _error(422, "invalid_body")
        verifier_key = self._key()
        if verifier_key is None:
            self._audit("device.enroll", "unavailable", "enrollment", now=now)
            return _error(503, "unavailable")
        kind, account_id, device = self.store.redeem(
            verifier=enrollment_verifier(verifier_key, token),
            now=now,
            account_active=self._contributor_active,
            device_id=self._new_id(),
            public_key=public_key,
        )
        if kind is RedeemKind.CREATED and device is not None:
            self._audit(
                "device.enroll",
                "ok",
                "device",
                account_id=device.account_id,
                device_id=device.device_id,
                now=now,
            )
            return ApiResult(201, {"device_id": device.device_id, "account_id": device.account_id})
        if kind is RedeemKind.UNAVAILABLE:
            self._audit(
                "device.enroll",
                "unavailable",
                "enrollment",
                account_id=account_id,
                now=now,
            )
            return _error(503, "unavailable")
        self._audit("device.enroll", "rejected", "enrollment", account_id=account_id, now=now)
        return _error(401, "rejected")

    def issue_challenge(self, device_id: str, raw_body: bytes, client_ip: str) -> ApiResult:
        now = self._instant()
        known = self.store.device(device_id) if is_uuid4(device_id) else None
        if not self.store.consume_ip(FAMILY_CHALLENGES, _peer(client_ip), now):
            self._audit(
                "device.challenge",
                "rate_limited",
                "device",
                account_id=None if known is None else known.account_id,
                device_id=None if known is None else known.device_id,
                now=now,
            )
            return _error(401, "rejected")
        if _object(raw_body, frozenset()) is None:
            self._audit(
                "device.challenge",
                "invalid_body",
                "device",
                account_id=None if known is None else known.account_id,
                device_id=None if known is None else known.device_id,
                now=now,
            )
            return _error(422, "invalid_body")
        if known is None:
            self._audit("device.challenge", "rejected", "device", now=now)
            return _error(401, "rejected")
        nonce = self._random(32)
        if nonce is None:
            self._audit(
                "device.challenge",
                "unavailable",
                "device",
                account_id=known.account_id,
                device_id=known.device_id,
                now=now,
            )
            return _error(503, "unavailable")
        kind, challenge = self.store.issue_challenge(
            device_id=known.device_id,
            now=now,
            account_active=self._contributor_active,
            challenge_id=self._new_id(),
            nonce=nonce,
            expires_at=now + CHALLENGE_TTL,
        )
        if kind is ChallengeKind.ISSUED and challenge is not None and challenge.nonce is not None:
            self._audit(
                "device.challenge",
                "ok",
                "device",
                account_id=known.account_id,
                device_id=known.device_id,
                now=now,
            )
            return ApiResult(
                201,
                {
                    "challenge_id": challenge.challenge_id,
                    "nonce": encode_secret(challenge.nonce),
                    "expires_at": format_timestamp(challenge.expires_at),
                },
            )
        if kind is ChallengeKind.QUOTA:
            self._audit(
                "device.challenge",
                "rate_limited",
                "device",
                account_id=known.account_id,
                device_id=known.device_id,
                now=now,
            )
            return _error(401, "rejected")
        if kind is ChallengeKind.REVOKED:
            self._audit(
                "device.challenge",
                "device_revoked",
                "device",
                account_id=known.account_id,
                device_id=known.device_id,
                now=now,
            )
            return _error(401, "rejected")
        if kind is ChallengeKind.UNAVAILABLE:
            self._audit(
                "device.challenge",
                "unavailable",
                "device",
                account_id=known.account_id,
                device_id=known.device_id,
                now=now,
            )
            return _error(503, "unavailable")
        self._audit("device.challenge", "rejected", "device", now=now)
        return _error(401, "rejected")

    def verify_challenge(self, challenge_id: str, raw_body: bytes, client_ip: str) -> ApiResult:
        now = self._instant()
        if not self.store.consume_ip(FAMILY_CHALLENGES, _peer(client_ip), now):
            self._audit("device.verify", "rate_limited", "device", now=now)
            return _error(401, "rejected")
        parsed = _object(raw_body, frozenset({"device_id", "signature"}))
        device_id = None if parsed is None else parsed.get("device_id")
        signature = None if parsed is None else decode_unpadded(parsed.get("signature"), 64)
        if not is_uuid4(device_id) or signature is None:
            self._audit("device.verify", "invalid_body", "device", now=now)
            return _error(422, "invalid_body")
        assert isinstance(device_id, str)
        if not is_uuid4(challenge_id):
            self._audit("device.verify", "rejected", "device", now=now)
            return _error(401, "rejected")
        kind, account_id, stored_device = self.store.verify(
            challenge_id=challenge_id,
            device_id=device_id,
            signature=signature,
            now=now,
            account_active=self._contributor_active,
        )
        if kind is VerifyKind.OK:
            self._audit(
                "device.verify",
                "ok",
                "device",
                account_id=account_id,
                device_id=stored_device,
                now=now,
            )
            return ApiResult(204)
        if kind is VerifyKind.DEVICE_REVOKED:
            result: AuditResult = "device_revoked"
        elif kind is VerifyKind.SIGNATURE_INVALID:
            result = "signature_invalid"
        else:
            result = "rejected"
        self._audit(
            "device.verify",
            result,
            "device",
            account_id=account_id,
            device_id=stored_device,
            now=now,
        )
        return _error(401, "rejected")

    def revoke_device(
        self,
        principal: Principal | None,
        device_id: str,
        raw_body: bytes,
    ) -> ApiResult:
        denied = self._denied(principal, Action.DEVICE_MANAGE, "-")
        if denied is not None:
            return denied
        assert principal is not None
        known = self.store.device(device_id) if is_uuid4(device_id) else None
        if raw_body != b"":
            self._record_known_device(principal, "invalid_body", known)
            return _error(422, "invalid_body")
        if known is None:
            self._record_known_device(principal, "not_found", None)
            return _error(404, "not_found")
        kind, device = self.store.revoke(known.device_id, self._instant())
        if kind is RevokeKind.UNKNOWN or device is None:
            self._record_known_device(principal, "not_found", None)
            return _error(404, "not_found")
        self._record_known_device(principal, "ok", device)
        return ApiResult(204)

    def add_allowlist(self, principal: Principal | None, raw_body: bytes) -> ApiResult:
        denied = self._denied(principal, Action.DEVICE_MANAGE, "-")
        if denied is not None:
            return denied
        assert principal is not None
        entry = _manifest(raw_body)
        if entry is None:
            self._record("device.manage", "invalid_body", "device", principal)
            return _error(422, "invalid_body")
        created = self.store.add_allowlist(entry)
        self._record("device.manage", "ok", "device", principal)
        return ApiResult(201 if created else 200, cast(dict[str, object], entry.body()))

    def remove_allowlist(self, principal: Principal | None, raw_body: bytes) -> ApiResult:
        denied = self._denied(principal, Action.DEVICE_MANAGE, "-")
        if denied is not None:
            return denied
        assert principal is not None
        entry = _manifest(raw_body)
        if entry is None:
            self._record("device.manage", "invalid_body", "device", principal)
            return _error(422, "invalid_body")
        if not self.store.remove_allowlist(entry.key()):
            self._record("device.manage", "not_found", "device", principal)
            return _error(404, "not_found")
        self._record("device.manage", "ok", "device", principal)
        return ApiResult(204)

    def list_allowlist(self, principal: Principal | None) -> ApiResult:
        denied = self._denied(principal, Action.DEVICE_MANAGE, "-")
        if denied is not None:
            return denied
        assert principal is not None
        body = [cast(dict[str, object], entry.body()) for entry in self.store.allowlist()]
        self._record("device.manage", "ok", "device", principal)
        return ApiResult(200, body)

    def read_statistics(self, principal: Principal | None, query: str) -> ApiResult:
        if principal is None:
            return _error(401, "unauthenticated")
        account_query = _account_query(query)
        if account_query.invalid:
            return _error(422, "invalid_body")
        if principal.role is Role.ADMIN:
            if account_query.account_id is None:
                return _error(422, "invalid_body")
            target = account_query.account_id
            if authorize(principal, Action.STATISTICS_READ_OWN, target_account_id=target) is not (
                Decision.ALLOW
            ):
                return _error(403, "forbidden")
            if self.accounts.account_by_id(target) is None:
                return _error(404, "not_found")
            return ApiResult(200, {"devices": self._statistics(target, include_revoked=True)})
        target = account_query.account_id or principal.account_id
        if authorize(principal, Action.STATISTICS_READ_OWN, target_account_id=target) is not (
            Decision.ALLOW
        ):
            return _error(403, "forbidden")
        return ApiResult(200, {"devices": self._statistics(target, include_revoked=False)})

    def list_devices(self, principal: Principal | None, query: str) -> ApiResult:
        denied = self._denied(principal, Action.DEVICE_MANAGE, "-")
        if denied is not None:
            return denied
        assert principal is not None
        account_query = _account_query(query)
        if account_query.invalid or account_query.account_id is None:
            self._record("device.manage", "invalid_body", "device", principal)
            return _error(422, "invalid_body")
        account_id = account_query.account_id
        if self.accounts.account_by_id(account_id) is None:
            self._record(
                "device.manage",
                "not_found",
                "device",
                principal,
                target=account_id,
                audit_account=False,
            )
            return _error(404, "not_found")
        rows = [self._identity_row(device) for device in self.store.devices_for(account_id)]
        self._record(
            "device.manage",
            "ok",
            "device",
            principal,
            target=account_id,
            account_id=account_id,
        )
        return ApiResult(200, rows)

    def admit_hello(self, hello: WorkerHelloV1, device_id: str) -> HelloDecision:
        def negotiate(keys: frozenset[tuple[str, str, str, str]]) -> tuple[str, bool, int | None]:
            result = negotiate_worker(hello, keys)
            return (
                result.decision.code.value,
                result.decision.code is StableCode.ACCEPTED,
                result.selected_minor,
            )

        now = self._instant()
        audit_result, protocol_code, minor, account_id = self.store.decide_hello(
            device_id=device_id,
            worker_id=hello.worker_id,
            now=now,
            account_active=self._contributor_active,
            negotiate=cast(Negotiate, negotiate),
        )
        stored = cast(AuditResult, audit_result)
        self._audit(
            "hello.admit",
            stored,
            "hello",
            account_id=account_id,
            device_id=device_id if account_id is not None else None,
            now=now,
        )
        return HelloDecision(
            accepted=audit_result == "ok",
            protocol_code=protocol_code,
            audit_result=stored,
            selected_minor=minor,
        )

    def record_stats(self, device_id: str, stats: WorkerStatsV1) -> bool:
        kind = self.store.apply_stats(
            device_id=device_id,
            account_active=self._contributor_active,
            processed_audio_ms=int(stats.processed_audio_ms),
            segments_accepted=int(stats.segments_accepted),
            segments_rejected=int(stats.segments_rejected),
            rtf=format_decimal(stats.realtime_factor),
        )
        return self._finish_update(device_id, kind, "statistics.record")

    def record_health(self, device_id: str, state: str, observed_at: datetime) -> bool:
        if state not in _HEALTH:
            return False
        kind = self.store.apply_health(
            device_id=device_id,
            account_active=self._contributor_active,
            state=cast(HealthState, state),
            observed_at=utc_millis(observed_at),
        )
        return self._finish_update(device_id, kind, "statistics.health")

    def note_online(self, device_id: str, started_at: datetime, ended_at: datetime) -> bool:
        started = utc_millis(started_at)
        ended = utc_millis(ended_at)
        if ended < started:
            seconds = -1
        else:
            delta = ended - started
            seconds = delta.days * 86400 + delta.seconds
        kind = self.store.apply_online(
            device_id=device_id,
            account_active=self._contributor_active,
            whole_seconds=seconds,
        )
        return self._finish_update(device_id, kind, "statistics.online")

    def _statistics(self, account_id: str, *, include_revoked: bool) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for device in self.store.devices_for(account_id):
            if include_revoked or device.status is DeviceStatus.ACTIVE:
                rows.append(self._public_statistic(device))
        return rows

    def _public_statistic(self, device: Device) -> dict[str, object]:
        stat = self.store.statistic(device.device_id)
        online = 0 if stat is None else stat.online_duration_seconds
        processed = 0
        rate: str | None = None
        rtf: str | None = None
        health: dict[str, str] | None = None
        if stat is not None and stat.stats_initialized:
            processed = stat.processed_audio_ms // 1000
            rate = format_success_rate(stat.segments_accepted, stat.segments_rejected)
            rtf = stat.rtf
        if (
            stat is not None
            and stat.health_state is not None
            and stat.health_observed_at is not None
        ):
            health = {
                "state": stat.health_state,
                "observed_at": format_timestamp(stat.health_observed_at),
            }
        return {
            "device_id": device.device_id,
            "online_duration_seconds": online,
            "processed_seconds": processed,
            "success_rate": rate,
            "rtf": rtf,
            "recent_health": health,
        }

    def _identity_row(self, device: Device) -> dict[str, object]:
        return {
            "device_id": device.device_id,
            "account_id": device.account_id,
            "status": device.status.value,
            "public_key": encode_secret(device.public_key),
            "created_at": format_timestamp(device.created_at),
            "revoked_at": None
            if device.revoked_at is None
            else format_timestamp(device.revoked_at),
        }

    def _contributor_active(self, account_id: str) -> bool:
        return _active_contributor(self.accounts.account_by_id(account_id))

    def _denied(
        self,
        principal: Principal | None,
        action: Action,
        target: str,
    ) -> ApiResult | None:
        if principal is None:
            return _error(401, "unauthenticated")
        if authorize(principal, action, target_account_id=target) is not Decision.ALLOW:
            return _error(403, "forbidden")
        return None

    def _finish_update(self, device_id: str, kind: UpdateKind, action: str) -> bool:
        if kind is UpdateKind.OK or kind is UpdateKind.STALE:
            return True
        device = self.store.device(device_id)
        result: AuditResult = "device_revoked" if kind is UpdateKind.DEVICE_REVOKED else "rejected"
        self._audit(
            action,
            result,
            "statistics",
            account_id=None if device is None else device.account_id,
            device_id=None if device is None else device.device_id,
        )
        return False

    def _record_known_device(
        self,
        principal: Principal,
        result: AuditResult,
        device: Device | None,
    ) -> None:
        """Log and audit a revoke using store identifiers, never the raw path."""
        if device is None:
            self._record(
                "device.manage",
                result,
                "device",
                principal,
                target="-",
                audit_account=False,
            )
            return
        self._record(
            "device.manage",
            result,
            "device",
            principal,
            target=device.device_id,
            account_id=device.account_id,
            device_id=device.device_id,
        )

    def _record(
        self,
        action: str,
        result: AuditResult,
        object_class: ObjectClass,
        principal: Principal,
        *,
        target: str = "-",
        account_id: str | None = None,
        device_id: str | None = None,
        audit_account: bool = True,
    ) -> None:
        log_worker(action, principal.account_id, target, result)
        if account_id is not None:
            stored_account: str | None = account_id
        elif audit_account and target != "-":
            stored_account = target
        else:
            stored_account = None
        self._audit(
            action,
            result,
            object_class,
            account_id=stored_account,
            device_id=device_id,
        )

    def _audit(
        self,
        action: str,
        result: AuditResult,
        object_class: ObjectClass,
        *,
        account_id: str | None = None,
        device_id: str | None = None,
        now: datetime | None = None,
    ) -> None:
        self.store.add_audit(
            AuditRecord(
                time=self._instant() if now is None else now,
                action=action,
                result=result,
                object_class=object_class,
                account_id=account_id,
                device_id=device_id,
            )
        )

    def _key(self) -> bytes | None:
        key = self._enrollment_key
        if key is None or len(key) != 32:
            return None
        return key

    def _random(self, size: int) -> bytes | None:
        raw = self._random_bytes(size)
        if len(raw) != size:
            return None
        return raw

    def _instant(self) -> datetime:
        return utc_millis(self._clock())


@dataclass(frozen=True, slots=True)
class _AccountQuery:
    invalid: bool
    account_id: str | None = None


def _account_query(query: str) -> _AccountQuery:
    pairs = parse_qsl(query, keep_blank_values=True)
    if not pairs:
        return _AccountQuery(False, None)
    if len(pairs) != 1 or pairs[0][0] != "account_id" or not is_uuid4(pairs[0][1]):
        return _AccountQuery(True)
    return _AccountQuery(False, pairs[0][1])


def _object(raw: bytes, keys: frozenset[str]) -> dict[str, object] | None:
    try:
        value: object = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    parsed: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            return None
        parsed[key] = item
    if set(parsed) != keys:
        return None
    return parsed


def _peer(client_ip: str) -> str:
    return client_ip or IP_FALLBACK


def _manifest(raw: bytes) -> AllowlistEntry | None:
    parsed = _object(raw, frozenset({"provider", "model_id", "revision", "sha256"}))
    if parsed is None:
        return None
    try:
        model = ModelManifestRefV1.model_validate(parsed)
    except ValidationError:
        return None
    return AllowlistEntry(
        provider=model.provider,
        model_id=model.model_id,
        revision=model.revision,
        sha256=model.sha256,
    )


def build_service(
    *,
    store: MemoryWorkerIdentityStore | None = None,
    accounts: AccountLookup | None = None,
    enrollment_key: bytes | None = None,
    clock: Clock | None = None,
    random_bytes: RandomBytes | None = None,
    new_id: NewId | None = None,
) -> WorkerIdentityService:
    return WorkerIdentityService(
        store if store is not None else MemoryWorkerIdentityStore(),
        accounts if accounts is not None else _EmptyAccounts(),
        enrollment_key=enrollment_key,
        clock=clock,
        random_bytes=random_bytes,
        new_id=new_id,
    )
