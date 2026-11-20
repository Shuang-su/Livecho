"""Independent matrix expectations. Deny is the default."""

from __future__ import annotations

from livecho_backend.auth.policy import (
    HANDLER_OWNER,
    Action,
    Decision,
    authorize,
    role_change_block,
)
from livecho_backend.auth.records import AccountStatus, Principal, Role

_ACTIVE = (Role.VIEWER, Role.CONTRIBUTOR, Role.OPERATOR, Role.ADMIN)


def _principal(role: Role, account_id: str = "self") -> Principal:
    return Principal(account_id=account_id, role=role, status=AccountStatus.ACTIVE)


def _expect(action: Action, role: Role | None, *, target: str | None = None) -> Decision:
    """Spec table encoded separately from authorize()."""
    if role is None:
        return Decision.DENY
    if action in {
        Action.DENYLIST_REMOVE,
        Action.SAFETY_REENABLE,
        Action.RAW_EXPORT,
    }:
        return Decision.ROLE_ONLY if role is Role.ADMIN else Decision.DENY
    if action is Action.STATISTICS_READ_OWN:
        if role is Role.ADMIN:
            return Decision.ALLOW
        if role is Role.CONTRIBUTOR and target == "self":
            return Decision.ALLOW
        return Decision.DENY
    if action in {
        Action.SESSION_READ_SELF,
        Action.SESSION_REVOKE_SELF,
        Action.ACCOUNT_READ_SELF,
        Action.HISTORY_READ,
    }:
        return Decision.ALLOW
    if action in {Action.ROOM_CONTROL, Action.DENYLIST_ADD, Action.SAFETY_DISABLE}:
        return Decision.ALLOW if role in {Role.OPERATOR, Role.ADMIN} else Decision.DENY
    if action in {
        Action.INVITE_CREATE,
        Action.INVITE_LIST,
        Action.ACCOUNT_SET_ROLE,
        Action.ACCOUNT_DISABLE,
        Action.SESSION_REVOKE_OTHER,
        Action.DEVICE_ISSUE_ENROLLMENT,
        Action.DEVICE_MANAGE,
        Action.DELETION_REQUEST,
    }:
        return Decision.ALLOW if role is Role.ADMIN else Decision.DENY
    return Decision.DENY


def test_every_action_and_principal_matches_the_spec_table() -> None:
    assert set(HANDLER_OWNER) == set(Action)
    roles: tuple[Role | None, ...] = (None, *_ACTIVE)
    for action in Action:
        for role in roles:
            principal = None if role is None else _principal(role)
            decision = authorize(principal, action, target_account_id="self")
            assert decision is _expect(action, role, target="self"), (action, role, decision)


def test_contributor_statistics_are_self_only() -> None:
    contributor = _principal(Role.CONTRIBUTOR, "self")
    assert (
        authorize(contributor, Action.STATISTICS_READ_OWN, target_account_id="other")
        is Decision.DENY
    )
    admin = _principal(Role.ADMIN, "admin")
    assert authorize(admin, Action.STATISTICS_READ_OWN, target_account_id="other") is Decision.ALLOW
    operator = _principal(Role.OPERATOR, "self")
    assert (
        authorize(operator, Action.STATISTICS_READ_OWN, target_account_id="self") is Decision.DENY
    )


def test_disabled_principal_is_denied() -> None:
    principal = Principal(account_id="self", role=Role.ADMIN, status=AccountStatus.DISABLED)
    for action in Action:
        assert authorize(principal, action, target_account_id="self") is Decision.DENY


def test_role_only_is_not_treated_as_allow() -> None:
    admin = _principal(Role.ADMIN)
    for action in (Action.DENYLIST_REMOVE, Action.SAFETY_REENABLE, Action.RAW_EXPORT):
        assert authorize(admin, action) is Decision.ROLE_ONLY


def test_last_admin_and_self_role_conflicts() -> None:
    assert (
        role_change_block(
            actor_id="admin",
            target_id="admin",
            target_role=Role.ADMIN,
            target_status=AccountStatus.ACTIVE,
            new_role=Role.VIEWER,
            active_admin_count=1,
        )
        == "self_role_change"
    )
    assert (
        role_change_block(
            actor_id="other",
            target_id="admin",
            target_role=Role.ADMIN,
            target_status=AccountStatus.ACTIVE,
            new_role=Role.VIEWER,
            active_admin_count=1,
        )
        == "last_admin"
    )
    assert (
        role_change_block(
            actor_id="admin-a",
            target_id="admin-b",
            target_role=Role.ADMIN,
            target_status=AccountStatus.ACTIVE,
            new_role=Role.VIEWER,
            active_admin_count=2,
        )
        is None
    )
