from __future__ import annotations

from pathlib import Path

import pytest

from tools import check_change_artifacts
from tools.check_change_artifacts import (
    REQUIRED_FILES,
    is_artifact_only_change,
    issue_number_from_branch,
    validation_errors,
)
from tools.check_workspace_scripts import validation_errors as workspace_errors

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def write_workspace_config(repository_root: Path, *patterns: str) -> None:
    lines = ["packages:", *(f"  - {pattern}" for pattern in patterns)]
    (repository_root / "pnpm-workspace.yaml").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def test_change_artifacts_are_complete() -> None:
    assert validation_errors() == []


def test_bootstrap_change_has_every_required_artifact() -> None:
    change = REPOSITORY_ROOT / "docs" / "changes" / "1-repository-foundation"
    assert {path.name for path in change.iterdir() if path.is_file()} == set(REQUIRED_FILES)


@pytest.mark.parametrize(
    ("branch", "issue_number"),
    [
        ("codex/issue-2-architecture-artifacts", 2),
        ("issue/19-alpha-acceptance", 19),
        ("feature/untracked-change", None),
        ("codex/issue-2-", None),
    ],
)
def test_issue_number_from_branch(branch: str, issue_number: int | None) -> None:
    assert issue_number_from_branch(branch) == issue_number


def test_only_the_current_issues_artifact_directory_is_artifact_only() -> None:
    assert is_artifact_only_change(2, {"docs/changes/2-architecture/intent.md"})
    assert not is_artifact_only_change(
        2,
        {"docs/changes/2-architecture/intent.md", "apps/web/package.json"},
    )


def test_implementation_requires_artifacts_in_the_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIVECHO_HEAD_REF", "codex/issue-2-architecture")
    monkeypatch.setattr(check_change_artifacts, "_base_ref", lambda branch: "base-sha")
    monkeypatch.setattr(
        check_change_artifacts,
        "_changed_paths",
        lambda base: {"apps/web/package.json"},
    )
    monkeypatch.setattr(check_change_artifacts, "_durable_base_artifact_errors", lambda base: [])
    monkeypatch.setattr(check_change_artifacts, "_current_issue_artifact_errors", lambda issue: [])
    monkeypatch.setattr(
        check_change_artifacts, "_accepted_artifact_rewrite_errors", lambda base, paths: []
    )
    monkeypatch.setattr(check_change_artifacts, "_base_artifact_paths", lambda base, issue: [])

    assert check_change_artifacts.lifecycle_errors() == [
        "implementation for Issue 2 requires exactly one matching artifact directory "
        "already present in base base-sha"
    ]


def test_implementation_accepts_complete_base_artifacts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIVECHO_HEAD_REF", "issue/2-architecture")
    monkeypatch.setattr(check_change_artifacts, "_base_ref", lambda branch: "base-sha")
    monkeypatch.setattr(
        check_change_artifacts,
        "_changed_paths",
        lambda base: {"services/backend/pyproject.toml"},
    )
    monkeypatch.setattr(check_change_artifacts, "_durable_base_artifact_errors", lambda base: [])
    monkeypatch.setattr(check_change_artifacts, "_current_issue_artifact_errors", lambda issue: [])
    monkeypatch.setattr(
        check_change_artifacts, "_accepted_artifact_rewrite_errors", lambda base, paths: []
    )
    monkeypatch.setattr(
        check_change_artifacts,
        "_base_artifact_paths",
        lambda base, issue: [
            "docs/changes/2-architecture/intent.md",
            "docs/changes/2-architecture/spec.md",
            "docs/changes/2-architecture/plan.md",
            "docs/changes/2-architecture/evidence.md",
        ],
    )

    assert check_change_artifacts.lifecycle_errors() == []


def test_issue_one_exception_closes_after_bootstrap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIVECHO_HEAD_REF", "codex/issue-1-late-change")
    monkeypatch.setattr(check_change_artifacts, "_base_ref", lambda branch: "post-bootstrap")
    monkeypatch.setattr(
        check_change_artifacts,
        "_changed_paths",
        lambda base: {"services/backend/pyproject.toml"},
    )
    monkeypatch.setattr(check_change_artifacts, "_durable_base_artifact_errors", lambda base: [])
    monkeypatch.setattr(check_change_artifacts, "_current_issue_artifact_errors", lambda issue: [])
    monkeypatch.setattr(
        check_change_artifacts, "_is_empty_repository_bootstrap", lambda base: False
    )

    assert check_change_artifacts.lifecycle_errors() == [
        "Issue 1 bootstrap exception is closed after the foundation reaches main"
    ]


def test_fork_branch_named_main_does_not_skip_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIVECHO_HEAD_REF", "main")
    monkeypatch.setenv("LIVECHO_BASE_SHA", "base-sha")

    assert check_change_artifacts.lifecycle_errors() == [
        "change branch must match codex/issue-<number>-<slug> or issue/<number>-<slug>"
    ]


def test_resulting_tree_requires_current_issue_artifacts(tmp_path: Path) -> None:
    assert check_change_artifacts._current_issue_artifact_errors(2, tmp_path) == [
        "change for Issue 2 requires exactly one complete artifact directory in the resulting tree"
    ]


def test_base_artifact_required_files_cannot_be_deleted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        check_change_artifacts,
        "_git",
        lambda *arguments: "docs/changes/2-architecture/intent.md",
    )

    assert check_change_artifacts._durable_base_artifact_errors("base-sha") == [
        "accepted change artifacts cannot be deleted: docs/changes/2-architecture/intent.md"
    ]


def test_implementation_cannot_rewrite_accepted_decisions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        check_change_artifacts,
        "_git",
        lambda *arguments: "\n".join(
            [
                "docs/changes/2-architecture/intent.md",
                "docs/changes/2-architecture/spec.md",
                "docs/changes/2-architecture/plan.md",
                "docs/changes/2-architecture/evidence.md",
            ]
        ),
    )

    assert check_change_artifacts._accepted_artifact_rewrite_errors(
        "base-sha",
        {
            "docs/changes/2-architecture/spec.md",
            "docs/changes/2-architecture/evidence.md",
            "services/backend/app.py",
        },
    ) == ["implementation cannot rewrite accepted artifacts: docs/changes/2-architecture/spec.md"]


def test_workspace_requires_every_verification_script(tmp_path: Path) -> None:
    write_workspace_config(tmp_path, "apps/*")
    package = tmp_path / "apps" / "web"
    package.mkdir(parents=True)
    (package / "package.json").write_text(
        '{"scripts":{"lint":"eslint ."}}',
        encoding="utf-8",
    )

    assert workspace_errors(tmp_path) == [
        "workspace apps/web missing scripts: typecheck, test, build"
    ]


def test_workspace_accepts_complete_verification_scripts(tmp_path: Path) -> None:
    write_workspace_config(tmp_path, "packages/*")
    package = tmp_path / "packages" / "protocol"
    package.mkdir(parents=True)
    (package / "package.json").write_text(
        '{"scripts":{"lint":"lint","typecheck":"types","test":"test","build":"build"}}',
        encoding="utf-8",
    )

    assert workspace_errors(tmp_path) == []


def test_workspace_checker_follows_new_configured_roots(tmp_path: Path) -> None:
    write_workspace_config(tmp_path, "services/*")
    package = tmp_path / "services" / "backend"
    package.mkdir(parents=True)
    (package / "package.json").write_text(
        '{"scripts":{"lint":"lint"}}',
        encoding="utf-8",
    )

    assert workspace_errors(tmp_path) == [
        "workspace services/backend missing scripts: typecheck, test, build"
    ]


def test_workspace_checker_uses_pnpm_glob_semantics(tmp_path: Path) -> None:
    write_workspace_config(tmp_path, "packages/{web,admin}")
    for package_name in ("web", "admin"):
        package = tmp_path / "packages" / package_name
        package.mkdir(parents=True)
        (package / "package.json").write_text(
            '{"name":"@livecho/' + package_name + '","version":"0.0.0","private":true,'
            '"scripts":{"lint":"lint"}}',
            encoding="utf-8",
        )

    assert workspace_errors(tmp_path) == [
        "workspace packages/admin missing scripts: typecheck, test, build",
        "workspace packages/web missing scripts: typecheck, test, build",
    ]


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
