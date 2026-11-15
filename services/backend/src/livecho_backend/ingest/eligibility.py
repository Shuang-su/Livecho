"""Eligibility checks against desensitized fixture metadata. No network."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .gates import Reason

EligibilityStatus = Literal[
    "eligible_live_free",
    "offline",
    "login_required",
    "payment_required",
    "geo_restricted",
    "drm_restricted",
    "rate_limited",
    "schema_invalid",
]


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    status: EligibilityStatus
    reason: Reason | None
    room_id: str | None


_REQUIRED = ("room_id", "live", "access", "geo_ok", "drm_ok", "rate_ok")


def evaluate_fixture_metadata(payload: dict[str, Any]) -> EligibilityResult:
    if not isinstance(payload, dict) or any(key not in payload for key in _REQUIRED):
        return EligibilityResult("schema_invalid", "schema_invalid", None)

    room = payload.get("room_id")
    room_id = str(room) if isinstance(room, int | str) else None
    if room_id is None:
        return EligibilityResult("schema_invalid", "schema_invalid", None)

    access = payload.get("access")
    if access == "login_required":
        return EligibilityResult("login_required", "login_required", room_id)
    if access == "payment_required":
        return EligibilityResult("payment_required", "payment_required", room_id)
    if access != "free_anonymous":
        return EligibilityResult("schema_invalid", "schema_invalid", room_id)

    if payload.get("geo_ok") is not True:
        return EligibilityResult("geo_restricted", "geo_restricted", room_id)
    if payload.get("drm_ok") is not True:
        return EligibilityResult("drm_restricted", "drm_restricted", room_id)
    if payload.get("rate_ok") is not True:
        return EligibilityResult("rate_limited", "rate_limited", room_id)
    if payload.get("live") is not True:
        return EligibilityResult("offline", "offline", room_id)

    return EligibilityResult("eligible_live_free", None, room_id)
