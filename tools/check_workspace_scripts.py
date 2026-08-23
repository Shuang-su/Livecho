"""Require every JavaScript workspace to implement the verification contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_CONFIG = "pnpm-workspace.yaml"
REQUIRED_SCRIPTS = ("lint", "typecheck", "test", "build")
YAML_LIST_ITEM = re.compile(r"^\s*-\s*(?P<value>.+?)\s*$")


def workspace_patterns(repository_root: Path = REPOSITORY_ROOT) -> list[str]:
    """Read the packages list from pnpm-workspace.yaml, failing closed."""
    config = repository_root / WORKSPACE_CONFIG
    if not config.is_file():
        raise ValueError(f"missing {WORKSPACE_CONFIG}")

    patterns: list[str] = []
    in_packages = False
    for line_number, raw_line in enumerate(config.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw_line.strip()
        if not in_packages:
            if stripped == "packages:":
                in_packages = True
            continue
        if stripped and not raw_line[0].isspace():
            break
        if not stripped or stripped.startswith("#"):
            continue
        match = YAML_LIST_ITEM.fullmatch(raw_line)
        if match is None:
            raise ValueError(f"unsupported packages syntax on line {line_number}")
        value = match.group("value").split(" #", 1)[0].strip().strip("'\"")
        if not value:
            raise ValueError(f"empty workspace pattern on line {line_number}")
        relative = Path(value.removeprefix("!"))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"workspace pattern escapes repository: {value}")
        patterns.append(value)
    if not in_packages or not patterns:
        raise ValueError("pnpm-workspace.yaml must contain a non-empty packages list")
    return patterns


def workspace_package_files(repository_root: Path = REPOSITORY_ROOT) -> list[Path]:
    """Return manifests selected by the actual pnpm workspace patterns."""
    manifests: set[Path] = set()
    for configured_pattern in workspace_patterns(repository_root):
        excluded = configured_pattern.startswith("!")
        pattern = configured_pattern.removeprefix("!")
        matches = list(repository_root.glob(pattern))
        if excluded:
            excluded_roots = [path for path in matches if path.is_dir()]
            manifests = {
                manifest
                for manifest in manifests
                if not any(
                    manifest.parent == root or root in manifest.parents for root in excluded_roots
                )
            }
            continue
        for path in matches:
            manifest = path if path.name == "package.json" else path / "package.json"
            if manifest.is_file():
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
