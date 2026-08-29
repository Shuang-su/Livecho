from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from livecho_protocol.errors import SUCCESS_CODES
from livecho_protocol.golden import GoldenCaseV1, evaluate_case

from tools.protocol_codegen import GENERATED_DIRECTORIES, drift_errors, generate_into

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPOSITORY_ROOT / "packages" / "protocol" / "fixtures"


def _load_cases() -> list[dict[str, Any]]:
    manifest: dict[str, Any] = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    paths = [*manifest["accepted"], *manifest["rejected"]]
    return [json.loads((FIXTURES / path).read_text(encoding="utf-8")) for path in paths]


def test_all_generated_golden_cases_match_python_decisions() -> None:
    cases = _load_cases()
    assert len(cases) == 123
    assert len({case["case_id"] for case in cases}) == len(cases)
    for case in cases:
        validated = GoldenCaseV1.model_validate(case)
        result = evaluate_case(case)
        assert result.value == validated.code, validated.case_id
        assert (result in SUCCESS_CODES) == (validated.expect == "accepted"), validated.case_id


def test_binary_golden_cases_contain_metadata_only() -> None:
    for case in _load_cases():
        if case["model"] != "PcmHeaderV1":
            continue
        assert set(case) == {"case_id", "model", "expect", "code", "binary_header"}
        assert "payload" not in case["binary_header"]
        assert "digest" not in case["binary_header"]


def _copy_generated(destination: Path) -> None:
    for directory in GENERATED_DIRECTORIES:
        source = REPOSITORY_ROOT / directory
        shutil.copytree(source, destination / directory)


def test_drift_checker_detects_mutation_deletion_and_extra_file(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    generate_into(expected)
    _copy_generated(actual)
    assert drift_errors(expected, actual) == []

    changed = actual / "packages/protocol/schema/compatibility.json"
    changed.write_text("{}\n", encoding="utf-8")
    assert drift_errors(expected, actual) == [
        "changed generated file: packages/protocol/schema/compatibility.json"
    ]
    shutil.copy2(expected / "packages/protocol/schema/compatibility.json", changed)

    deleted = actual / "packages/protocol/src/generated/protocol-v1.ts"
    deleted.unlink()
    assert drift_errors(expected, actual) == [
        "missing generated file: packages/protocol/src/generated/protocol-v1.ts"
    ]
    shutil.copy2(expected / "packages/protocol/src/generated/protocol-v1.ts", deleted)

    extra = actual / "packages/protocol/schema/unexpected.json"
    extra.write_text("{}\n", encoding="utf-8")
    assert drift_errors(expected, actual) == [
        "unexpected generated file: packages/protocol/schema/unexpected.json"
    ]


def test_generated_surface_contains_required_models_and_no_audio_artifact() -> None:
    types = (REPOSITORY_ROOT / "packages/protocol/src/generated/protocol-v1.ts").read_text(
        encoding="utf-8"
    )
    for name in (
        "TimelineEventV1",
        "TranscriptSegmentV1",
        "WorkerHelloV1",
        "LeaseV1",
        "HeartbeatV1",
        "WorkerStatsV1",
    ):
        assert f"interface {name}" in types

    forbidden_suffixes = {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".opus", ".pcm", ".wav"}
    assert not [path for path in FIXTURES.rglob("*") if path.suffix.lower() in forbidden_suffixes]


def test_public_schema_has_no_locator_execution_or_audio_storage_field() -> None:
    schema_root = REPOSITORY_ROOT / "packages" / "protocol" / "schema"
    forbidden = {
        "audio_base64",
        "audio_bytes",
        "command",
        "container",
        "cookie",
        "credential",
        "download_url",
        "environment",
        "filesystem_path",
        "options",
        "pcm",
        "raw_payload",
        "signed_playback_url",
        "uri",
        "url",
    }

    def property_names(value: Any) -> set[str]:
        if isinstance(value, dict):
            names = (
                set(value.get("properties", {}))
                if isinstance(value.get("properties"), dict)
                else set()
            )
            return names.union(*(property_names(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(property_names(item) for item in value))
        return set()

    for path in schema_root.glob("*.schema.json"):
        if path.name == "GoldenCaseV1.schema.json":
            continue
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert property_names(schema).isdisjoint(forbidden), path.name
