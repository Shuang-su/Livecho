"""Validate the repository's versioned change-artifact contract."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CHANGES_ROOT = REPOSITORY_ROOT / "docs" / "changes"
REQUIRED_FILES = ("intent.md", "spec.md", "plan.md", "evidence.md")
ACCEPTED_BEFORE_IMPLEMENTATION = ("intent.md", "spec.md", "plan.md")
CHANGE_DIRECTORY_PATTERN = re.compile(r"^[1-9][0-9]*-[a-z0-9]+(?:-[a-z0-9]+)*$")
ISSUE_BRANCH_PATTERN = re.compile(r"^(?:codex/)?issue(?:-|/)([1-9][0-9]*)-")


def artifact_content_errors(changes_root: Path = CHANGES_ROOT) -> list[str]:
    """Validate every artifact directory currently present in the working tree."""
    errors: list[str] = []
    if not changes_root.is_dir():
        return [f"missing change root: {changes_root.relative_to(REPOSITORY_ROOT)}"]

    for directory in sorted(changes_root.iterdir()):
        if not directory.is_dir() or directory.name.startswith("_"):
            continue
        if not CHANGE_DIRECTORY_PATTERN.fullmatch(directory.name):
            errors.append(f"invalid change directory name: {directory.name}")
        for filename in REQUIRED_FILES:
            artifact = directory / filename
            if not artifact.is_file():
                errors.append(f"missing artifact: {artifact.relative_to(REPOSITORY_ROOT)}")
                continue
            if not artifact.read_text(encoding="utf-8").strip():
                errors.append(f"empty artifact: {artifact.relative_to(REPOSITORY_ROOT)}")
    return errors


def issue_number_from_branch(branch: str) -> int | None:
    """Extract the Issue number from an approved implementation branch name."""
    match = ISSUE_BRANCH_PATTERN.fullmatch(branch) or ISSUE_BRANCH_PATTERN.match(branch)
    return int(match.group(1)) if match else None


def is_artifact_only_change(issue_number: int, changed_paths: set[str]) -> bool:
    """Return whether every changed path belongs to this Issue's artifact directory."""
    artifact_prefix = f"docs/changes/{issue_number}-"
    return bool(changed_paths) and all(path.startswith(artifact_prefix) for path in changed_paths)


def _git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _changed_paths(base_ref: str) -> set[str]:
    tracked = _git("diff", "--name-only", "--diff-filter=ACMRDT", base_ref)
    untracked = _git("ls-files", "--others", "--exclude-standard")
    return {path for path in (*tracked.splitlines(), *untracked.splitlines()) if path}


def _base_ref(branch: str) -> str | None:
    configured = os.environ.get("LIVECHO_BASE_SHA", "").strip()
    if configured:
        return configured
    if branch in {"main", "master"}:
        return None
    try:
        return _git("rev-parse", "--verify", "origin/main")
    except subprocess.CalledProcessError:
        return None


def _base_artifact_paths(base_ref: str, issue_number: int) -> list[str]:
    tree = _git("ls-tree", "-r", "--name-only", base_ref, "docs/changes")
    prefix = f"docs/changes/{issue_number}-"
    return [path for path in tree.splitlines() if path.startswith(prefix)]


def _is_empty_repository_bootstrap(base_ref: str) -> bool:
    protected_paths = _git(
        "ls-tree",
        "-r",
        "--name-only",
        base_ref,
        "AGENTS.md",
        "docs/changes",
    )
    return not protected_paths


def lifecycle_errors() -> list[str]:
    """Enforce artifact-only PRs and merged artifacts before implementation."""
    branch = os.environ.get("LIVECHO_HEAD_REF", "").strip() or _git("branch", "--show-current")
    if branch in {"main", "master"}:
        return []

    issue_number = issue_number_from_branch(branch)
    if issue_number is None:
        return ["change branch must match codex/issue-<number>-<slug> or issue/<number>-<slug>"]

    base_ref = _base_ref(branch)
    if base_ref is None:
        return ["cannot determine the main/base commit for change-artifact validation"]

    changed_paths = _changed_paths(base_ref)
    if not changed_paths or is_artifact_only_change(issue_number, changed_paths):
        return []
    if issue_number == 1:
        if _is_empty_repository_bootstrap(base_ref):
            return []
        return ["Issue 1 bootstrap exception is closed after the foundation reaches main"]

    base_paths = _base_artifact_paths(base_ref, issue_number)
    directories = {path.rsplit("/", 1)[0] for path in base_paths}
    if len(directories) != 1:
        return [
            f"implementation for Issue {issue_number} requires exactly one matching artifact "
            f"directory already present in base {base_ref[:12]}"
        ]

    directory = directories.pop()
    missing = [
        filename
        for filename in ACCEPTED_BEFORE_IMPLEMENTATION
        if f"{directory}/{filename}" not in base_paths
    ]
    if missing:
        return [
            f"base artifact {directory} is not accepted for implementation; missing: "
            + ", ".join(missing)
        ]
    return []


def validation_errors() -> list[str]:
    """Return all artifact and lifecycle errors without mutating the repository."""
    return [*artifact_content_errors(), *lifecycle_errors()]


def main() -> int:
    """Print validation failures and return a process exit code."""
    errors = validation_errors()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("change artifacts: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
