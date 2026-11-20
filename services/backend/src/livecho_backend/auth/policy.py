"""Deny-by-default role matrix. Roles are not a ladder."""

from __future__ import annotations

from enum import StrEnum

from .records import AccountStatus, Principal, Role


class Action(StrEnum):
    SESSION_READ_SELF = "session.read_self"
    SESSION_REVOKE_SELF = "session.revoke_self"
    ACCOUNT_READ_SELF = "account.read_self"
    INVITE_CREATE = "invite.create"
    INVITE_LIST = "invite.list"
    ACCOUNT_SET_ROLE = "account.set_role"
    ACCOUNT_DISABLE = "account.disable"
    SESSION_REVOKE_OTHER = "session.revoke_other"
    HISTORY_READ = "history.read"
    STATISTICS_READ_OWN = "statistics.read_own"
    DEVICE_ISSUE_ENROLLMENT = "device.issue_enrollment"
    DEVICE_MANAGE = "device.manage"
    ROOM_CONTROL = "room.control"
    DENYLIST_ADD = "denylist.add"
    SAFETY_DISABLE = "safety.disable"
    DENYLIST_REMOVE = "denylist.remove"
    SAFETY_REENABLE = "safety.reenable"
    DELETION_REQUEST = "deletion.request"
    RAW_EXPORT = "raw.export"


class Decision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    ROLE_ONLY = "role_only"


HANDLER_OWNER: dict[Action, str] = {
    Action.SESSION_READ_SELF: "#12",
    Action.SESSION_REVOKE_SELF: "#12",
    Action.ACCOUNT_READ_SELF: "#12",
    Action.INVITE_CREATE: "#12",
    Action.INVITE_LIST: "#12",
    Action.ACCOUNT_SET_ROLE: "#12",
    Action.ACCOUNT_DISABLE: "#12",
    Action.SESSION_REVOKE_OTHER: "#12",
    Action.HISTORY_READ: "#17",
    Action.STATISTICS_READ_OWN: "#13/#17",
    Action.DEVICE_ISSUE_ENROLLMENT: "#13",
    Action.DEVICE_MANAGE: "#13",
    Action.ROOM_CONTROL: "#17",
    Action.DENYLIST_ADD: "#17",
    Action.SAFETY_DISABLE: "#17",
    Action.DENYLIST_REMOVE: "#17",
    Action.SAFETY_REENABLE: "#17",
    Action.DELETION_REQUEST: "#16/#17",
    Action.RAW_EXPORT: "#16",
}

_ANY_ACTIVE = {
    Action.SESSION_READ_SELF,
    Action.SESSION_REVOKE_SELF,
    Action.ACCOUNT_READ_SELF,
    Action.HISTORY_READ,
}
_OPERATOR = {
    Action.ROOM_CONTROL,
    Action.DENYLIST_ADD,
    Action.SAFETY_DISABLE,
}
_ADMIN = {
    Action.INVITE_CREATE,
    Action.INVITE_LIST,
    Action.ACCOUNT_SET_ROLE,
    Action.ACCOUNT_DISABLE,
    Action.SESSION_REVOKE_OTHER,
    Action.DEVICE_ISSUE_ENROLLMENT,
    Action.DEVICE_MANAGE,
    Action.DELETION_REQUEST,
}
_ROLE_ONLY = {
    Action.DENYLIST_REMOVE,
    Action.SAFETY_REENABLE,
    Action.RAW_EXPORT,
}


def authorize(
    principal: Principal | None,
    action: Action,
    *,
    target_account_id: str | None = None,
) -> Decision:
    """Return allow, deny, or role_only. role_only is not permission to act."""
    if principal is None or principal.status is not AccountStatus.ACTIVE:
        return Decision.DENY
    if action in _ROLE_ONLY:
        if principal.role is Role.ADMIN:
            return Decision.ROLE_ONLY
        return Decision.DENY
    if action is Action.STATISTICS_READ_OWN:
        if principal.role is Role.ADMIN:
            return Decision.ALLOW
        if principal.role is Role.CONTRIBUTOR and target_account_id == principal.account_id:
            return Decision.ALLOW
        return Decision.DENY
    if action in _ANY_ACTIVE:
        return Decision.ALLOW
    if action in _OPERATOR and principal.role in {Role.OPERATOR, Role.ADMIN}:
        return Decision.ALLOW
    if action in _ADMIN and principal.role is Role.ADMIN:
        return Decision.ALLOW
    return Decision.DENY


def role_change_block(
    *,
    actor_id: str,
    target_id: str,
    target_role: Role,
    target_status: AccountStatus,
    new_role: Role,
    active_admin_count: int,
) -> str | None:
    """Return a conflict code, or None when the change may proceed."""
    if target_status is AccountStatus.DISABLED:
        return "account_disabled"
    if actor_id == target_id:
        return "self_role_change"
    if target_role is Role.ADMIN and new_role is not Role.ADMIN and active_admin_count <= 1:
        return "last_admin"
    return None
