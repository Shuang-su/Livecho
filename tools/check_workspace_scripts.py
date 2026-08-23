"""Require every JavaScript workspace to implement the verification contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOTS = ("apps", "packages")
REQUIRED_SCRIPTS = ("lint", "typecheck", "test", "build")


def workspace_package_files(repository_root: Path = REPOSITORY_ROOT) -> list[Path]:
    """Return package manifests immediately below configured workspace roots."""
    manifests: list[Path] = []
    for root_name in WORKSPACE_ROOTS:
        root = repository_root / root_name
        if root.is_dir():
            manifests.extend(sorted(root.glob("*/package.json")))
    return manifests


def validation_errors(repository_root: Path = REPOSITORY_ROOT) -> list[str]:
    """Return missing or invalid workspace-script errors."""
    errors: list[str] = []
    for manifest in workspace_package_files(repository_root):
        relative = manifest.relative_to(repository_root)
        try:
            document: Any = json.loads(manifest.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            errors.append(f"invalid workspace manifest {relative}: {error}")
            continue
        scripts = document.get("scripts") if isinstance(document, dict) else None
        if not isinstance(scripts, dict):
            errors.append(f"workspace manifest has no scripts object: {relative}")
            continue
        missing = [name for name in REQUIRED_SCRIPTS if not scripts.get(name)]
        if missing:
            errors.append(f"workspace {relative.parent} missing scripts: {', '.join(missing)}")
    return errors


def main() -> int:
    """Print validation failures and return a process exit code."""
    errors = validation_errors()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("workspace scripts: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
