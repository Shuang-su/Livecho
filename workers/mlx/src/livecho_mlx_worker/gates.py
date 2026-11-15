"""Closed-by-default evidence and execution registries.

No environment variable, CLI flag, or import-time probe can mint approvals. Owner-
reviewed rows must be added by a later evidence-bearing change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Reason = Literal[
    "reviewed_manifest_unavailable",
    "model_decision_adr_unavailable",
    "benchmark_report_unavailable",
    "host_evidence_unavailable",
    "audio_budget_unverified",
    "execution_registry_closed",
    "non_apple_silicon_mlx",
    "partial_unavailable",
    "invalid_configuration",
]


@dataclass(frozen=True, slots=True)
class ApprovedManifest:
    identity: str
    provider: str
    model_id: str
    revision: str
    sha256: str
    evidence_id: str


@dataclass(frozen=True, slots=True)
class ApprovedModelDecision:
    identity: str
    adr_path: str
    report_identity: str
    evidence_id: str


@dataclass(frozen=True, slots=True)
class ApprovedHostEvidence:
    identity: str
    platform: str
    evidence_id: str


@dataclass(frozen=True, slots=True)
class ExecutionPermit:
    identity: str
    manifest_identity: str
    host_identity: str
    evidence_id: str


# Deliberately empty. Fixture/contract tests never populate these.
APPROVED_MANIFESTS: tuple[ApprovedManifest, ...] = ()
APPROVED_MODEL_DECISIONS: tuple[ApprovedModelDecision, ...] = ()
APPROVED_HOST_EVIDENCE: tuple[ApprovedHostEvidence, ...] = ()
EXECUTION_REGISTRY: tuple[ExecutionPermit, ...] = ()


def evidence_blockers(*, require_execution: bool = False) -> tuple[Reason, ...]:
    """Hard blockers for real readiness / run. Does not include capability notices."""
    reasons: list[Reason] = []
    if not APPROVED_MANIFESTS:
        reasons.append("reviewed_manifest_unavailable")
    if not APPROVED_MODEL_DECISIONS:
        reasons.append("model_decision_adr_unavailable")
        reasons.append("benchmark_report_unavailable")
    if not APPROVED_HOST_EVIDENCE:
        reasons.append("host_evidence_unavailable")
        reasons.append("audio_budget_unverified")
    if require_execution and not EXECUTION_REGISTRY:
        reasons.append("execution_registry_closed")
    return tuple(reasons)


def capability_notices() -> tuple[Reason, ...]:
    """Honest capability gaps that do not alone imply invalid configuration."""
    return ("partial_unavailable",)


def blocked_reasons(*, require_execution: bool = False) -> tuple[Reason, ...]:
    return evidence_blockers(require_execution=require_execution) + capability_notices()


def real_run_allowed() -> bool:
    return not evidence_blockers(require_execution=True)
