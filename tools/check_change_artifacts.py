"""Validate the repository's versioned change-artifact contract."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CHANGES_ROOT = REPOSITORY_ROOT / "docs" / "changes"
REQUIRED_FILES = ("intent.md", "spec.md", "plan.md", "evidence.md")
CHANGE_DIRECTORY_PATTERN = re.compile(r"^[1-9][0-9]*-[a-z0-9]+(?:-[a-z0-9]+)*$")


def validation_errors() -> list[str]:
    """Return human-readable artifact errors without mutating the repository."""
    errors: list[str] = []
    if not CHANGES_ROOT.is_dir():
        return [f"missing change root: {CHANGES_ROOT.relative_to(REPOSITORY_ROOT)}"]

    for directory in sorted(CHANGES_ROOT.iterdir()):
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
