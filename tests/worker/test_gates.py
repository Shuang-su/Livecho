from __future__ import annotations

from livecho_mlx_worker.gates import (
    APPROVED_HOST_EVIDENCE,
    APPROVED_MANIFESTS,
    APPROVED_MODEL_DECISIONS,
    EXECUTION_REGISTRY,
    evidence_blockers,
    real_run_allowed,
)


def test_checked_in_registries_remain_empty() -> None:
    assert APPROVED_MANIFESTS == ()
    assert APPROVED_MODEL_DECISIONS == ()
    assert APPROVED_HOST_EVIDENCE == ()
    assert EXECUTION_REGISTRY == ()
    assert not real_run_allowed()
    assert "execution_registry_closed" in evidence_blockers(require_execution=True)
    assert "reviewed_manifest_unavailable" in evidence_blockers()
