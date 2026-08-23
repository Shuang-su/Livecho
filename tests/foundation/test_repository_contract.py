from __future__ import annotations

from pathlib import Path

from tools.check_change_artifacts import REQUIRED_FILES, validation_errors

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_change_artifacts_are_complete() -> None:
    assert validation_errors() == []


def test_bootstrap_change_has_every_required_artifact() -> None:
    change = REPOSITORY_ROOT / "docs" / "changes" / "1-repository-foundation"
    assert {path.name for path in change.iterdir() if path.is_file()} == set(REQUIRED_FILES)


def test_agent_guidance_contains_product_invariants() -> None:
    guidance = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "Audio is ephemeral" in guidance
    assert "Never add remote shell" in guidance
    assert "CUDA remains mock/contract-only" in guidance
