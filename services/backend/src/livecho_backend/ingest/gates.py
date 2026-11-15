"""Closed-by-default acquisition, rights, and audio-admission registries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Reason = Literal[
    "acquisition_channel_unselected",
    "rights_basis_missing",
    "ingest_disabled",
    "room_denied",
    "audio_budget_unverified",
    "encoded_admission_missing",
    "actor_forbidden",
    "selector_invalid",
    "eligibility_failed",
    "login_required",
    "payment_required",
    "geo_restricted",
    "drm_restricted",
    "rate_limited",
    "schema_invalid",
    "offline",
    "retry_exhausted",
    "operator_stop",
]


@dataclass(frozen=True, slots=True)
class AcquisitionChannel:
    identity: str
    host_allowlist: tuple[str, ...]
    evidence_id: str


@dataclass(frozen=True, slots=True)
class RightsEvidence:
    identity: str
    room_id: str
    action: str
    evidence_id: str


# Deliberately empty. Fixture/contract tests never populate production rows.
ACQUISITION_CHANNELS: tuple[AcquisitionChannel, ...] = ()
RIGHTS_EVIDENCE: tuple[RightsEvidence, ...] = ()
ENCODED_ADMISSION_EVIDENCE: tuple[str, ...] = ()
PRODUCTION_INGEST_DEFAULT = False  # BILI-DEC-001 OFF


def evidence_blockers() -> tuple[Reason, ...]:
    reasons: list[Reason] = []
    if not ACQUISITION_CHANNELS:
        reasons.append("acquisition_channel_unselected")
    if not RIGHTS_EVIDENCE:
        reasons.append("rights_basis_missing")
    if not ENCODED_ADMISSION_EVIDENCE:
        reasons.append("encoded_admission_missing")
    reasons.append("audio_budget_unverified")
    return tuple(reasons)


def blocked_reasons() -> tuple[Reason, ...]:
    return evidence_blockers()


def real_acquisition_allowed() -> bool:
    return (
        bool(ACQUISITION_CHANNELS)
        and bool(RIGHTS_EVIDENCE)
        and bool(ENCODED_ADMISSION_EVIDENCE)
        and PRODUCTION_INGEST_DEFAULT is True
    )
