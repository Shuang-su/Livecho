"""Offline creation of the first admin. Not a serving route and not a mail send."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from .normalize import normalize_email
from .records import Account
from .store import BootstrapError, MemoryAuthStore

__all__ = ["BootstrapError", "bootstrap_first_admin"]


def bootstrap_first_admin(
    store: MemoryAuthStore,
    email: str,
    *,
    now: datetime | None = None,
    account_id: str | None = None,
) -> Account:
    """Insert one active admin when the store is empty. Do not print the address."""
    normalized = normalize_email(email)
    if normalized is None:
        raise BootstrapError("invalid email")
    return store.bootstrap_admin(
        normalized,
        now if now is not None else datetime.now(UTC),
        account_id if account_id is not None else str(uuid4()),
    )
