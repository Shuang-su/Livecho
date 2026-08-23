from __future__ import annotations

from pathlib import Path

import pytest

from tools.check_change_artifacts import REQUIRED_FILES, validation_errors

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_change_artifacts_are_complete() -> None:
    assert validation_errors() == []


def test_bootstrap_change_has_every_required_artifact() -> None:
    change = REPOSITORY_ROOT / "docs" / "changes" / "1-repository-foundation"
    assert {path.name for path in change.iterdir() if path.is_file()} == set(REQUIRED_FILES)


@pytest.mark.parametrize(
    "invariant",
    [
        "Audio is ephemeral",
        "Never add remote shell",
        "Never send Bilibili account credentials",
        "Raw event archives are encrypted",
        "`epoch`, `seq`, and `revision`",
        "Public ingest is limited",
        "CUDA remains mock/contract-only",
    ],
    ids=["audio", "worker-execution", "credentials", "archive", "protocol", "ingest", "cuda"],
)
def test_agent_guidance_contains_product_invariant(invariant: str) -> None:
    guidance = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert invariant in guidance
