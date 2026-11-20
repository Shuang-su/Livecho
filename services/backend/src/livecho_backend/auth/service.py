"""Invite, magic-link, and session operations for Issue #12."""

from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from .config import AuthConfig, can_send
from .crypto import (
    decode_secret,
    encode_secret,
    magic_link_text,
    magic_link_verifier,
    session_verifier,
)
from .mail import MailSender, OutboundMail
from .records import MAGIC_LINK_TTL, SESSION_TTL, Account, AccountStatus, Principal, Role, Session
from .store import InviteKind, MemoryAuthStore, PrepareKind

Clock = Callable[[], datetime]
RandomBytes = Callable[[int], bytes]
NewId = Callable[[], str]


class RedeemKind(StrEnum):
    OK = "ok"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class RedeemResult:
    kind: RedeemKind
    cookie_value: str | None = None


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid4())


class AuthService:
    """Coordinates the memory store and the mail port. It does not log bearers."""

    def __init__(
        self,
        store: MemoryAuthStore,
        config: AuthConfig,
        mailer: MailSender,
        *,
        clock: Clock | None = None,
        random_bytes: RandomBytes | None = None,
        new_id: NewId | None = None,
    ) -> None:
        self.store = store
        self.config = config
        self.mailer = mailer
        self._clock = clock or _now
        self._random_bytes = random_bytes or secrets.token_bytes
        self._new_id = new_id or _new_id

    def request_magic_link(self, email: str, client_ip: str) -> None:
        now = self._clock()
        account = self.store.account_by_email(email)
        token: bytes | None = None
        verifier: bytes | None = None
        link_id: str | None = None
        origin = self.config.public_origin
        signing_key = self.config.signing_key
        sendable = (
            can_send(self.config)
            and account is not None
            and signing_key is not None
            and origin is not None
        )
        if sendable and signing_key is not None:
            token = self._random_bytes(32)
            if len(token) != 32:
                token = None
            else:
                verifier = magic_link_verifier(signing_key, token)
                link_id = self._new_id()
        prepared = self.store.prepare_magic_link(
            account=account,
            ip=client_ip,
            now=now,
            verifier=verifier,
            link_id=link_id,
            can_send=sendable and token is not None,
            created_at=now,
            expires_at=now + MAGIC_LINK_TTL,
        )
        if (
            prepared.kind is not PrepareKind.MINTED
            or token is None
            or link_id is None
            or origin is None
            or account is None
        ):
            return
        message = OutboundMail(
            recipient=account.email,
            idempotency_key=link_id,
            text=magic_link_text(origin, encode_secret(token)),
        )
        if not self.mailer.send(message):
            self.mailer.send(message)

    def redeem(self, token: str) -> RedeemResult:
        signing_key = self.config.signing_key
        raw = decode_secret(token)
        if signing_key is None or raw is None:
            return RedeemResult(RedeemKind.INVALID)
        now = self._clock()
        link = self.store.consume_magic_link(magic_link_verifier(signing_key, raw), now)
        if link is None:
            return RedeemResult(RedeemKind.INVALID)
        account = self.store.claim_account_for_session(link.account_id)
        if account is None:
            return RedeemResult(RedeemKind.INVALID)
        cookie_secret = self._random_bytes(32)
        if len(cookie_secret) != 32:
            return RedeemResult(RedeemKind.INVALID)
        session = Session(
            session_id=self._new_id(),
            account_id=account.account_id,
            verifier=session_verifier(signing_key, cookie_secret),
            created_at=now,
            expires_at=now + SESSION_TTL,
            revoked_at=None,
        )
        self.store.insert_session(session)
        return RedeemResult(RedeemKind.OK, encode_secret(cookie_secret))

    def principal_for_cookie(self, cookie_value: str | None) -> Principal | None:
        signing_key = self.config.signing_key
        if signing_key is None or cookie_value is None:
            return None
        raw = decode_secret(cookie_value)
        if raw is None:
            return None
        session = self.store.session_by_verifier(session_verifier(signing_key, raw))
        if session is None or session.revoked_at is not None:
            return None
        now = self._clock()
        if now >= session.expires_at:
            return None
        account = self.store.account_by_id(session.account_id)
        if account is None or account.status is not AccountStatus.ACTIVE:
            return None
        return Principal(
            account_id=account.account_id,
            role=account.role,
            status=account.status,
        )

    def revoke_cookie(self, cookie_value: str | None) -> None:
        signing_key = self.config.signing_key
        if signing_key is None or cookie_value is None:
            return
        raw = decode_secret(cookie_value)
        if raw is None:
            return
        self.store.revoke_live_session(session_verifier(signing_key, raw), self._clock())

    def account_for_principal(self, principal: Principal) -> Account | None:
        account = self.store.account_by_id(principal.account_id)
        if account is None or account.status is not AccountStatus.ACTIVE:
            return None
        return account

    def create_invite(self, email: str, role: Role) -> tuple[InviteKind, Account]:
        return self.store.plan_invite(
            email=email,
            role=role,
            now=self._clock(),
            account_id=self._new_id(),
        )

    def list_accounts(self) -> tuple[Account, ...]:
        return self.store.list_accounts()

    def set_role(self, actor_id: str, target_id: str, role: Role) -> tuple[str, Account | None]:
        return self.store.apply_role(actor_id=actor_id, target_id=target_id, new_role=role)

    def disable(self, actor_id: str, target_id: str) -> tuple[str, Account | None]:
        return self.store.apply_disable(actor_id=actor_id, target_id=target_id, now=self._clock())

    def revoke_session(self, session_id: str) -> bool:
        return self.store.revoke_session_id(session_id, self._clock())
