"""Require every JavaScript workspace to implement the verification contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_CONFIG = "pnpm-workspace.yaml"
REQUIRED_SCRIPTS = ("lint", "typecheck", "test", "build")


def workspace_package_files(repository_root: Path = REPOSITORY_ROOT) -> list[Path]:
    """Ask pnpm to return manifests using pnpm's own workspace glob semantics."""
    if not (repository_root / WORKSPACE_CONFIG).is_file():
        raise ValueError(f"missing {WORKSPACE_CONFIG}")

    result = subprocess.run(
        ["pnpm", "list", "--recursive", "--depth", "-1", "--json"],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or f"pnpm exited with status {result.returncode}"
        raise ValueError(f"pnpm workspace discovery failed: {detail}")
    try:
        projects: Any = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ValueError(f"pnpm returned invalid workspace JSON: {error}") from error
    if not isinstance(projects, list):
        raise ValueError("pnpm workspace discovery did not return a project list")

    repository = repository_root.resolve()
    manifests: set[Path] = set()
    for index, project in enumerate(projects):
        path_text = project.get("path") if isinstance(project, dict) else None
        if not isinstance(path_text, str) or not path_text.strip():
            raise ValueError(f"pnpm workspace project {index} has no path")
        project_path = Path(path_text).resolve()
        try:
            project_path.relative_to(repository)
        except ValueError as error:
            raise ValueError(f"pnpm workspace escapes repository: {project_path}") from error
        manifest = project_path / "package.json"
        if not manifest.is_file():
            raise ValueError(f"pnpm workspace has no package.json: {project_path}")
        manifests.add(manifest)
    return sorted(manifests)


def validation_errors(repository_root: Path = REPOSITORY_ROOT) -> list[str]:
    """Return missing or invalid workspace-script errors."""
    errors: list[str] = []
    try:
        manifests = workspace_package_files(repository_root)
    except (OSError, ValueError) as error:
        return [f"invalid workspace configuration: {error}"]
    for manifest in manifests:
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
        missing = [
            name
            for name in REQUIRED_SCRIPTS
            if not isinstance(scripts.get(name), str) or not scripts[name].strip()
        ]
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
