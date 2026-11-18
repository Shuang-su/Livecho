"""Identity records for the Issue #12 memory adapter.

Columns match the accepted spec. Plaintext tokens and cookie secrets are not
fields on these records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

MAGIC_LINK_TTL = timedelta(minutes=15)
SESSION_TTL = timedelta(days=30)
SESSION_MAX_AGE_SECONDS = 2_592_000
ADDRESS_QUOTA = 5
ADDRESS_WINDOW = timedelta(hours=24)
IP_QUOTA = 30
IP_WINDOW = timedelta(minutes=15)
IP_FALLBACK = "missing-peer"


class Role(StrEnum):
    VIEWER = "viewer"
    CONTRIBUTOR = "contributor"
    OPERATOR = "operator"
    ADMIN = "admin"


class AccountStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class Account:
    account_id: str
    email: str
    role: Role
    status: AccountStatus
    created_at: datetime
    disabled_at: datetime | None


@dataclass(frozen=True, slots=True)
class MagicLink:
    link_id: str
    account_id: str
    verifier: bytes
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None


@dataclass(frozen=True, slots=True)
class Session:
    session_id: str
    account_id: str
    verifier: bytes
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


@dataclass(frozen=True, slots=True)
class Principal:
    account_id: str
    role: Role
    status: AccountStatus
