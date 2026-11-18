"""Process-local identity store. Verifiers only; no plaintext bearers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from threading import Lock

from .policy import role_change_block
from .records import (
    ADDRESS_QUOTA,
    ADDRESS_WINDOW,
    IP_QUOTA,
    IP_WINDOW,
    Account,
    AccountStatus,
    MagicLink,
    Role,
    Session,
)


class InviteKind(StrEnum):
    CREATED = "created"
    SAME_ROLE = "same_role"
    ROLE_CONFLICT = "role_conflict"
    DISABLED = "disabled"


class BootstrapError(Exception):
    """Bootstrap refused. The message never includes an email address."""


class PrepareKind(StrEnum):
    NOOP = "noop"
    REUSED = "reused"
    MINTED = "minted"


@dataclass(frozen=True, slots=True)
class PreparedLink:
    kind: PrepareKind
    link_id: str | None = None


class MemoryAuthStore:
    """One process-local allowlist, magic-link, and session store."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._accounts: dict[str, Account] = {}
        self._email_index: dict[str, str] = {}
        self._links: dict[str, MagicLink] = {}
        self._links_by_verifier: dict[bytes, str] = {}
        self._sessions: dict[str, Session] = {}
        self._sessions_by_verifier: dict[bytes, str] = {}
        self._ip_hits: dict[str, list[datetime]] = {}

    def bootstrap_admin(self, email: str, now: datetime, account_id: str) -> Account:
        with self._lock:
            if self._accounts:
                raise BootstrapError("store is not empty")
            account = Account(
                account_id=account_id,
                email=email,
                role=Role.ADMIN,
                status=AccountStatus.ACTIVE,
                created_at=now,
                disabled_at=None,
            )
            self._accounts[account_id] = account
            self._email_index[email] = account_id
            return account

    def account_by_email(self, email: str) -> Account | None:
        with self._lock:
            account_id = self._email_index.get(email)
            if account_id is None:
                return None
            return self._accounts[account_id]

    def account_by_id(self, account_id: str) -> Account | None:
        with self._lock:
            return self._accounts.get(account_id)

    def list_accounts(self) -> tuple[Account, ...]:
        with self._lock:
            return tuple(self._accounts[key] for key in sorted(self._accounts))

    def plan_invite(
        self,
        *,
        email: str,
        role: Role,
        now: datetime,
        account_id: str,
    ) -> tuple[InviteKind, Account]:
        with self._lock:
            existing_id = self._email_index.get(email)
            if existing_id is not None:
                current = self._accounts[existing_id]
                if current.status is AccountStatus.DISABLED:
                    return InviteKind.DISABLED, current
                if current.role is role:
                    return InviteKind.SAME_ROLE, current
                return InviteKind.ROLE_CONFLICT, current
            account = Account(
                account_id=account_id,
                email=email,
                role=role,
                status=AccountStatus.INVITED,
                created_at=now,
                disabled_at=None,
            )
            self._accounts[account_id] = account
            self._email_index[email] = account_id
            return InviteKind.CREATED, account

    def apply_role(
        self,
        *,
        actor_id: str,
        target_id: str,
        new_role: Role,
    ) -> tuple[str, Account | None]:
        with self._lock:
            target = self._accounts.get(target_id)
            if target is None:
                return "not_found", None
            admins = sum(
                1
                for account in self._accounts.values()
                if account.role is Role.ADMIN and account.status is not AccountStatus.DISABLED
            )
            block = role_change_block(
                actor_id=actor_id,
                target_id=target.account_id,
                target_role=target.role,
                target_status=target.status,
                new_role=new_role,
                active_admin_count=admins,
            )
            if block is not None:
                return block, target
            updated = Account(
                account_id=target.account_id,
                email=target.email,
                role=new_role,
                status=target.status,
                created_at=target.created_at,
                disabled_at=target.disabled_at,
            )
            self._accounts[target_id] = updated
            return "updated", updated

    def apply_disable(
        self,
        *,
        actor_id: str,
        target_id: str,
        now: datetime,
    ) -> tuple[str, Account | None]:
        if actor_id == target_id:
            current = self.account_by_id(target_id)
            return "self_disable", current
        updated = self.disable_account(target_id, now)
        if updated is None:
            return "not_found", None
        return "disabled", updated

    def disable_account(self, account_id: str, now: datetime) -> Account | None:
        with self._lock:
            current = self._accounts.get(account_id)
            if current is None:
                return None
            updated = Account(
                account_id=current.account_id,
                email=current.email,
                role=current.role,
                status=AccountStatus.DISABLED,
                created_at=current.created_at,
                disabled_at=current.disabled_at or now,
            )
            self._accounts[account_id] = updated
            for link_id, link in list(self._links.items()):
                if link.account_id == account_id and link.used_at is None and now < link.expires_at:
                    self._links[link_id] = MagicLink(
                        link_id=link.link_id,
                        account_id=link.account_id,
                        verifier=link.verifier,
                        created_at=link.created_at,
                        expires_at=now,
                        used_at=None,
                    )
            for session_id, session in list(self._sessions.items()):
                if session.account_id == account_id and session.revoked_at is None:
                    self._sessions[session_id] = Session(
                        session_id=session.session_id,
                        account_id=session.account_id,
                        verifier=session.verifier,
                        created_at=session.created_at,
                        expires_at=session.expires_at,
                        revoked_at=now,
                    )
            return updated

    def active_admin_count(self) -> int:
        with self._lock:
            return sum(
                1
                for account in self._accounts.values()
                if account.role is Role.ADMIN and account.status is not AccountStatus.DISABLED
            )

    def prepare_magic_link(
        self,
        *,
        account: Account | None,
        ip: str,
        now: datetime,
        verifier: bytes | None,
        link_id: str | None,
        can_send: bool,
        created_at: datetime,
        expires_at: datetime,
    ) -> PreparedLink:
        """Count the client request, then mint at most one unexpired unused link."""
        with self._lock:
            allowed_ip = self._record_ip(ip, now)
            eligible = (
                can_send
                and account is not None
                and account.status in {AccountStatus.INVITED, AccountStatus.ACTIVE}
                and verifier is not None
                and link_id is not None
            )
            if not eligible or account is None or verifier is None or link_id is None:
                return PreparedLink(PrepareKind.NOOP)
            reusable = self._reusable(account.account_id, now)
            if reusable is not None:
                return PreparedLink(PrepareKind.REUSED, reusable.link_id)
            if not allowed_ip:
                return PreparedLink(PrepareKind.NOOP)
            if self._minted_since(account.account_id, now - ADDRESS_WINDOW) >= ADDRESS_QUOTA:
                return PreparedLink(PrepareKind.NOOP)
            link = MagicLink(
                link_id=link_id,
                account_id=account.account_id,
                verifier=verifier,
                created_at=created_at,
                expires_at=expires_at,
                used_at=None,
            )
            self._links[link_id] = link
            self._links_by_verifier[verifier] = link_id
            return PreparedLink(PrepareKind.MINTED, link_id)

    def magic_links_for(self, account_id: str) -> tuple[MagicLink, ...]:
        with self._lock:
            return tuple(link for link in self._links.values() if link.account_id == account_id)

    def consume_magic_link(self, verifier: bytes, now: datetime) -> MagicLink | None:
        """Set used_at once. A second caller, expiry, or unknown verifier loses."""
        with self._lock:
            link_id = self._links_by_verifier.get(verifier)
            if link_id is None:
                return None
            link = self._links[link_id]
            if link.used_at is not None or now >= link.expires_at:
                return None
            updated = MagicLink(
                link_id=link.link_id,
                account_id=link.account_id,
                verifier=link.verifier,
                created_at=link.created_at,
                expires_at=link.expires_at,
                used_at=now,
            )
            self._links[link_id] = updated
            return updated

    def claim_account_for_session(self, account_id: str) -> Account | None:
        with self._lock:
            current = self._accounts.get(account_id)
            if current is None or current.status is AccountStatus.DISABLED:
                return None
            if current.status is AccountStatus.INVITED:
                current = Account(
                    account_id=current.account_id,
                    email=current.email,
                    role=current.role,
                    status=AccountStatus.ACTIVE,
                    created_at=current.created_at,
                    disabled_at=None,
                )
                self._accounts[account_id] = current
            return current

    def insert_session(self, session: Session) -> None:
        with self._lock:
            self._sessions[session.session_id] = session
            self._sessions_by_verifier[session.verifier] = session.session_id

    def session_by_verifier(self, verifier: bytes) -> Session | None:
        with self._lock:
            session_id = self._sessions_by_verifier.get(verifier)
            if session_id is None:
                return None
            return self._sessions[session_id]

    def revoke_live_session(self, verifier: bytes, now: datetime) -> bool:
        with self._lock:
            session_id = self._sessions_by_verifier.get(verifier)
            if session_id is None:
                return False
            session = self._sessions[session_id]
            if session.revoked_at is not None or now >= session.expires_at:
                return False
            self._sessions[session_id] = Session(
                session_id=session.session_id,
                account_id=session.account_id,
                verifier=session.verifier,
                created_at=session.created_at,
                expires_at=session.expires_at,
                revoked_at=now,
            )
            return True

    def revoke_session_id(self, session_id: str, now: datetime) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            if session.revoked_at is None:
                self._sessions[session_id] = Session(
                    session_id=session.session_id,
                    account_id=session.account_id,
                    verifier=session.verifier,
                    created_at=session.created_at,
                    expires_at=session.expires_at,
                    revoked_at=now,
                )
            return True

    def _record_ip(self, ip: str, now: datetime) -> bool:
        hits = [item for item in self._ip_hits.get(ip, []) if now - item < IP_WINDOW]
        hits.append(now)
        self._ip_hits[ip] = hits
        return len(hits) <= IP_QUOTA

    def _reusable(self, account_id: str, now: datetime) -> MagicLink | None:
        for link in self._links.values():
            if link.account_id == account_id and link.used_at is None and now < link.expires_at:
                return link
        return None

    def _minted_since(self, account_id: str, start: datetime) -> int:
        return sum(
            1
            for link in self._links.values()
            if link.account_id == account_id and link.created_at > start
        )
