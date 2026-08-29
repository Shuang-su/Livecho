"""Generate and byte-check every committed protocol artifact."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SOURCE = REPOSITORY_ROOT / "packages" / "protocol" / "python"
if str(PYTHON_SOURCE) not in sys.path:
    sys.path.insert(0, str(PYTHON_SOURCE))

from livecho_protocol.compatibility import COMPATIBILITY_MATRIX  # noqa: E402
from livecho_protocol.golden import GoldenCaseV1, all_cases  # noqa: E402
from livecho_protocol.models import PUBLIC_MODELS, ProtocolMessageV1  # noqa: E402

GENERATED_DIRECTORIES = (
    Path("packages/protocol/schema"),
    Path("packages/protocol/src/generated"),
    Path("packages/protocol/fixtures"),
)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _schema(model: type[Any]) -> dict[str, Any]:
    schema: dict[str, Any] = model.model_json_schema(mode="validation")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = f"https://livecho.invalid/protocol/v1/{model.__name__}.schema.json"
    return schema


def _aggregate_schema() -> dict[str, Any]:
    schema: dict[str, Any] = TypeAdapter(ProtocolMessageV1).json_schema(mode="validation")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://livecho.invalid/protocol/v1/protocol-v1.schema.json"
    schema["title"] = "ProtocolMessageV1"
    return schema


def _run_typescript_generator(schema: Path, output: Path) -> None:
    result = subprocess.run(
        [
            "pnpm",
            "--filter",
            "@livecho/protocol",
            "exec",
            "node",
            "scripts/generate-types.mjs",
            str(schema),
            str(output),
        ],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "TypeScript generation failed"
        raise RuntimeError(detail)


def generate_into(output_root: Path) -> None:
    """Write a complete deterministic generated tree below ``output_root``."""
    schema_root = output_root / "packages/protocol/schema"
    generated_root = output_root / "packages/protocol/src/generated"
    fixtures_root = output_root / "packages/protocol/fixtures"
    for model in sorted(PUBLIC_MODELS, key=lambda item: item.__name__):
        _write(schema_root / f"{model.__name__}.schema.json", _json_bytes(_schema(model)))
    _write(schema_root / "GoldenCaseV1.schema.json", _json_bytes(_schema(GoldenCaseV1)))
    aggregate = schema_root / "protocol-v1.schema.json"
    _write(aggregate, _json_bytes(_aggregate_schema()))
    _write(schema_root / "compatibility.json", _json_bytes(COMPATIBILITY_MATRIX))
    generated_root.mkdir(parents=True, exist_ok=True)
    _run_typescript_generator(aggregate, generated_root / "protocol-v1.ts")
    manifest: dict[str, Any] = {"accepted": [], "rejected": [], "version": 1}
    for case in all_cases():
        disposition = str(case["expect"])
        filename = str(case["case_id"]).replace(".", "__") + ".json"
        relative = f"{disposition}/{filename}"
        _write(fixtures_root / relative, _json_bytes(case))
        manifest[disposition].append(relative)
    _write(fixtures_root / "manifest.json", _json_bytes(manifest))


def _files(root: Path, directories: Iterable[Path]) -> dict[Path, bytes]:
    result: dict[Path, bytes] = {}
    for directory in directories:
        absolute = root / directory
        if not absolute.exists():
            continue
        for path in sorted(absolute.rglob("*")):
            if path.is_file():
                result[path.relative_to(root)] = path.read_bytes()
    return result


def drift_errors(expected_root: Path, actual_root: Path = REPOSITORY_ROOT) -> list[str]:
    expected = _files(expected_root, GENERATED_DIRECTORIES)
    actual = _files(actual_root, GENERATED_DIRECTORIES)
    errors: list[str] = []
    for path in sorted(expected.keys() - actual.keys()):
        errors.append(f"missing generated file: {path.as_posix()}")
    for path in sorted(actual.keys() - expected.keys()):
        errors.append(f"unexpected generated file: {path.as_posix()}")
    for path in sorted(expected.keys() & actual.keys()):
        if expected[path] != actual[path]:
            errors.append(f"changed generated file: {path.as_posix()}")
    return errors


def _replace_generated_directories(temporary_root: Path) -> None:
    """Commit all generated directories as one rollback-capable transaction."""
    backups: dict[Path, Path] = {}
    installed: list[Path] = []
    try:
        for directory in GENERATED_DIRECTORIES:
            target = REPOSITORY_ROOT / directory
            target.parent.mkdir(parents=True, exist_ok=True)
            backup = target.with_name(f".{target.name}.protocol-backup")
            if backup.exists():
                shutil.rmtree(backup)
            if target.exists():
                os.replace(target, backup)
                backups[target] = backup
        for directory in GENERATED_DIRECTORIES:
            target = REPOSITORY_ROOT / directory
            os.replace(temporary_root / directory, target)
            installed.append(target)
    except BaseException:
        for target in reversed(installed):
            if target.exists():
                shutil.rmtree(target)
        for target, backup in backups.items():
            if backup.exists():
                os.replace(backup, target)
        raise
    for backup in backups.values():
        if backup.exists():
            shutil.rmtree(backup)


def rewrite_generated() -> None:
    with tempfile.TemporaryDirectory(prefix=".protocol-generation-", dir=REPOSITORY_ROOT) as raw:
        temporary_root = Path(raw)
        generate_into(temporary_root)
        _replace_generated_directories(temporary_root)


def check_generated() -> list[str]:
    with tempfile.TemporaryDirectory(prefix="livecho-protocol-check-") as raw:
        expected_root = Path(raw)
        generate_into(expected_root)
        return drift_errors(expected_root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    if arguments.check:
        errors = check_generated()
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print("protocol generated artifacts: ok")
        return 0
    rewrite_generated()
    print("protocol generated artifacts: updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
