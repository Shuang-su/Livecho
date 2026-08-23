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
ISSUE_BRANCH_PATTERN = re.compile(
    r"^(?:codex/)?issue(?:-|/)([1-9][0-9]*)-[a-z0-9]+(?:-[a-z0-9]+)*$"
)


def _is_regular_file(path: Path) -> bool:
    """Return whether path is a regular file rather than a followed symlink."""
    return path.is_file() and not path.is_symlink()


def _required_file_errors(
    directory: Path,
    non_regular_paths: set[Path],
    label: str = "artifact",
) -> tuple[list[str], set[Path]]:
    """Validate one artifact directory's four required files."""
    errors: list[str] = []
    reported_non_regular: set[Path] = set()
    entry_names = {path.name for path in directory.iterdir()}
    for filename in REQUIRED_FILES:
        artifact = directory / filename
        artifact_relative = artifact.relative_to(REPOSITORY_ROOT)
        artifact_path = artifact_relative.as_posix()
        if filename not in entry_names:
            errors.append(f"missing {label}: {artifact_path}")
            continue
        if artifact.is_symlink() or artifact_relative in non_regular_paths:
            errors.append(f"{label} must be a regular file: {artifact_path}")
            reported_non_regular.add(artifact_relative)
            continue
        if not artifact.is_file():
            errors.append(f"missing {label}: {artifact_path}")
            continue
        if not artifact.read_text(encoding="utf-8").strip():
            errors.append(f"empty {label}: {artifact_path}")
    return errors, reported_non_regular


def artifact_content_errors(
    changes_root: Path = CHANGES_ROOT,
    tracked_non_regular: set[Path] | None = None,
) -> list[str]:
    """Validate every artifact directory currently present in the working tree."""
    errors: list[str] = []
    tracked_non_regular = tracked_non_regular or set()
    relative_root = changes_root.relative_to(REPOSITORY_ROOT)
    relative_component = Path()
    component_root = REPOSITORY_ROOT
    for component in relative_root.parts:
        if not component_root.is_dir():
            return [f"missing change root: {relative_root.as_posix()}"]
        relative_component /= component
        entry_names = {path.name for path in component_root.iterdir()}
        if component not in entry_names:
            if any(name.casefold() == component.casefold() for name in entry_names):
                return [
                    "change artifact root component must use exact case: "
                    f"{relative_component.as_posix()}"
                ]
            return [f"missing change root: {relative_root.as_posix()}"]
        component_root /= component
        if component_root.is_symlink() or relative_component in tracked_non_regular:
            return [
                "change artifact root component must be a regular directory: "
                f"{relative_component.as_posix()}"
            ]
    if not changes_root.is_dir():
        return [f"missing change root: {relative_root.as_posix()}"]

    non_regular_paths = set(tracked_non_regular)
    non_regular_paths.update(
        path.relative_to(REPOSITORY_ROOT) for path in changes_root.rglob("*") if path.is_symlink()
    )
    reported_non_regular: set[Path] = set()
    for directory in sorted(changes_root.iterdir()):
        directory_relative = directory.relative_to(REPOSITORY_ROOT)
        directory_path = directory_relative.as_posix()
        non_regular_entry = directory_relative in non_regular_paths
        if directory.name == "_template":
            if non_regular_entry or not directory.is_dir():
                errors.append(
                    f"change artifact template must be a regular directory: {directory_path}"
                )
                if non_regular_entry:
                    reported_non_regular.add(directory_relative)
            else:
                template_errors, template_reported = _required_file_errors(
                    directory,
                    non_regular_paths,
                    label="template artifact",
                )
                errors.extend(template_errors)
                reported_non_regular.update(template_reported)
            continue
        if directory.name.startswith("_"):
            errors.append(f"invalid change directory name: {directory.name}")
            if non_regular_entry:
                reported_non_regular.add(directory_relative)
            continue
        if non_regular_entry:
            if CHANGE_DIRECTORY_PATTERN.fullmatch(directory.name):
                errors.append(
                    f"change artifact directory must be a regular directory: {directory_path}"
                )
            else:
                errors.append(f"invalid change directory name: {directory.name}")
            reported_non_regular.add(directory_relative)
            continue
        if not directory.is_dir():
            if directory.name != "README.md" and not directory.name.startswith("."):
                errors.append(f"invalid change directory name: {directory.name}")
            continue
        if not CHANGE_DIRECTORY_PATTERN.fullmatch(directory.name):
            errors.append(f"invalid change directory name: {directory.name}")
            continue
        artifact_errors, artifact_reported = _required_file_errors(
            directory,
            non_regular_paths,
        )
        errors.extend(artifact_errors)
        reported_non_regular.update(artifact_reported)

    unreported_non_regular = sorted(
        path.as_posix()
        for path in non_regular_paths - reported_non_regular
        if path.is_relative_to(relative_root)
    )
    if unreported_non_regular:
        errors.append(
            "change artifacts cannot contain non-regular entries: "
            + ", ".join(unreported_non_regular)
        )
    return errors


def issue_number_from_branch(branch: str) -> int | None:
    """Extract the Issue number from an approved implementation branch name."""
    match = ISSUE_BRANCH_PATTERN.fullmatch(branch)
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


def _tracked_non_regular_artifact_paths() -> set[Path]:
    """Find invalid leaves and non-regular entries in the Git index change tree."""
    index = _git("ls-files", "--stage", "-z", "--", "docs")
    non_regular: set[Path] = set()
    regular_modes = {"100644", "100755"}
    for entry in index.split("\0"):
        if not entry:
            continue
        try:
            metadata, path_text = entry.split("\t", maxsplit=1)
            mode = metadata.split(" ", maxsplit=1)[0]
        except (IndexError, ValueError):
            continue
        path = Path(path_text)
        if path.parts in {("docs",), ("docs", "changes")}:
            non_regular.add(path)
            continue
        if path.parts[:2] != ("docs", "changes"):
            continue
        if mode not in regular_modes:
            non_regular.add(path)
            continue
        invalid_directory = len(path.parts) == 3 and path.name != "README.md"
        if invalid_directory:
            non_regular.add(path)
    return non_regular


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
    tree = _git("ls-tree", "-r", base_ref, "docs/changes")
    prefix = f"docs/changes/{issue_number}-"
    paths: list[str] = []
    required_names = set(REQUIRED_FILES)
    for entry in tree.splitlines():
        try:
            metadata, path = entry.split("\t", maxsplit=1)
            mode, object_type, _object_id = metadata.split(" ", maxsplit=2)
        except ValueError:
            continue
        artifact = Path(path)
        if (
            mode in {"100644", "100755"}
            and object_type == "blob"
            and path.startswith(prefix)
            and len(artifact.parts) == 4
            and artifact.parts[:2] == ("docs", "changes")
            and CHANGE_DIRECTORY_PATTERN.fullmatch(artifact.parts[2])
            and artifact.name in required_names
        ):
            paths.append(path)
    return paths


def _current_issue_artifact_errors(
    issue_number: int, changes_root: Path = CHANGES_ROOT
) -> list[str]:
    directories = sorted(
        path
        for path in changes_root.glob(f"{issue_number}-*")
        if path.is_dir() and not path.is_symlink() and CHANGE_DIRECTORY_PATTERN.fullmatch(path.name)
    )
    if len(directories) != 1:
        return [
            f"change for Issue {issue_number} requires exactly one complete artifact "
            "directory in the resulting tree"
        ]
    directory = directories[0]
    entry_names = {path.name for path in directory.iterdir()}
    missing = [
        filename
        for filename in REQUIRED_FILES
        if filename not in entry_names or not _is_regular_file(directory / filename)
    ]
    if missing:
        return [
            f"resulting artifact {directory.relative_to(REPOSITORY_ROOT)} is missing: "
            + ", ".join(missing)
        ]
    return []


def _foreign_issue_artifact_errors(issue_number: int, changed_paths: set[str]) -> list[str]:
    """Reject changing another Issue's artifacts on the current Issue branch."""
    foreign_directories: set[str] = set()
    for path_text in changed_paths:
        path = Path(path_text)
        if len(path.parts) < 3 or path.parts[:2] != ("docs", "changes"):
            continue
        directory = path.parts[2]
        if not CHANGE_DIRECTORY_PATTERN.fullmatch(directory):
            continue
        directory_issue_number = int(directory.split("-", maxsplit=1)[0])
        if directory_issue_number != issue_number:
            foreign_directories.add(f"docs/changes/{directory}")

    if foreign_directories:
        return [
            f"change for Issue {issue_number} cannot modify artifacts for other Issues: "
            + ", ".join(sorted(foreign_directories))
        ]
    return []


def _durable_base_artifact_errors(base_ref: str) -> list[str]:
    tree = _git("ls-tree", "-r", "--name-only", base_ref, "docs/changes")
    required_names = set(REQUIRED_FILES)
    deleted: list[str] = []
    non_regular: list[str] = []
    for path_text in tree.splitlines():
        path = Path(path_text)
        if (
            len(path.parts) == 4
            and path.parts[:2] == ("docs", "changes")
            and CHANGE_DIRECTORY_PATTERN.fullmatch(path.parts[2])
            and path.name in required_names
        ):
            artifact = REPOSITORY_ROOT / path
            if artifact.is_symlink():
                non_regular.append(path_text)
            elif not artifact.is_file():
                deleted.append(path_text)
    errors: list[str] = []
    if deleted:
        errors.append("accepted change artifacts cannot be deleted: " + ", ".join(sorted(deleted)))
    if non_regular:
        errors.append(
            "accepted change artifacts must remain regular files: " + ", ".join(sorted(non_regular))
        )
    return errors


def _accepted_artifact_rewrite_errors(base_ref: str, changed_paths: set[str]) -> list[str]:
    """Keep accepted decisions immutable while an implementation PR is in flight."""
    tree = _git("ls-tree", "-r", "--name-only", base_ref, "docs/changes")
    accepted_names = set(ACCEPTED_BEFORE_IMPLEMENTATION)
    rewritten = sorted(
        path_text
        for path_text in tree.splitlines()
        if (
            len((path := Path(path_text)).parts) == 4
            and path.parts[:2] == ("docs", "changes")
            and CHANGE_DIRECTORY_PATTERN.fullmatch(path.parts[2])
            and path.name in accepted_names
            and path_text in changed_paths
        )
    )
    if rewritten:
        return ["implementation cannot rewrite accepted artifacts: " + ", ".join(rewritten)]
    return []


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
    base_ref = _base_ref(branch)
    if branch in {"main", "master"} and base_ref is None:
        return []

    issue_number = issue_number_from_branch(branch)
    if issue_number is None:
        return ["change branch must match codex/issue-<number>-<slug> or issue/<number>-<slug>"]

    if base_ref is None:
        return ["cannot determine the main/base commit for change-artifact validation"]

    changed_paths = _changed_paths(base_ref)
    if not changed_paths:
        return []
    resulting_tree_errors = [
        *_durable_base_artifact_errors(base_ref),
        *_current_issue_artifact_errors(issue_number),
        *_foreign_issue_artifact_errors(issue_number, changed_paths),
    ]
    if resulting_tree_errors:
        return resulting_tree_errors
    if issue_number == 1:
        if _is_empty_repository_bootstrap(base_ref):
            return []
        return ["Issue 1 bootstrap exception is closed after the foundation reaches main"]
    if is_artifact_only_change(issue_number, changed_paths):
        return []

    rewrite_errors = _accepted_artifact_rewrite_errors(base_ref, changed_paths)
    if rewrite_errors:
        return rewrite_errors

    base_paths = _base_artifact_paths(base_ref, issue_number)
    directories = {path.rsplit("/", 1)[0] for path in base_paths}
    if len(directories) != 1:
        return [
            f"implementation for Issue {issue_number} requires exactly one matching artifact "
            f"directory already present in base {base_ref[:12]}"
        ]

    directory = directories.pop()
    missing = [
        filename for filename in REQUIRED_FILES if f"{directory}/{filename}" not in base_paths
    ]
    if missing:
        return [
            f"base artifact {directory} is not accepted for implementation; missing: "
            + ", ".join(missing)
        ]
    return []


def validation_errors() -> list[str]:
    """Return all artifact and lifecycle errors without mutating the repository."""
    tracked_non_regular = _tracked_non_regular_artifact_paths()
    return [
        *artifact_content_errors(tracked_non_regular=tracked_non_regular),
        *lifecycle_errors(),
    ]


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
