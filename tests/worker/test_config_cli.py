from __future__ import annotations

import json
import platform
from pathlib import Path
from uuid import uuid4

import pytest
from livecho_mlx_worker.cli import main
from livecho_mlx_worker.config import WorkerConfig, load_config
from livecho_mlx_worker.gates import EXECUTION_REGISTRY
from pydantic import ValidationError


def test_enroll_writes_closed_config_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "mlx-worker.json"
    worker_id = str(uuid4())
    code = main(
        [
            "enroll",
            "--config",
            str(path),
            "--worker-id",
            worker_id,
            "--manifest-id",
            "pending-manifest",
            "--host-evidence-id",
            "pending-host",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["state"] == "ok"
    assert payload["fixture_not_speech_recognition"] is True
    config = load_config(path)
    assert config.endpoint_id == "loopback-local-v1"
    assert config.worker_id == worker_id
    assert set(config.model_dump()) == {
        "schema_version",
        "endpoint_id",
        "worker_id",
        "manifest_id",
        "host_evidence_id",
    }


def test_enroll_rejects_arbitrary_endpoint(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "bad.json"
    code = main(
        [
            "enroll",
            "--config",
            str(path),
            "--endpoint-id",
            "https://evil.example",
            "--worker-id",
            str(uuid4()),
            "--manifest-id",
            "x",
            "--host-evidence-id",
            "y",
        ]
    )
    assert code == 2
    assert json.loads(capsys.readouterr().out)["state"] == "invalid_configuration"
    assert not path.exists()


def test_config_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        WorkerConfig.model_validate(
            {
                "endpoint_id": "loopback-local-v1",
                "worker_id": str(uuid4()),
                "manifest_id": "m",
                "host_evidence_id": "h",
                "download_url": "https://example",
            }
        )


def test_doctor_and_run_are_evidence_blocked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "mlx-worker.json"
    assert (
        main(
            [
                "enroll",
                "--config",
                str(path),
                "--worker-id",
                str(uuid4()),
                "--manifest-id",
                "pending-manifest",
                "--host-evidence-id",
                "pending-host",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert EXECUTION_REGISTRY == ()
    doctor = main(["doctor", "--config", str(path)])
    doctor_out = json.loads(capsys.readouterr().out)
    assert doctor == 2
    assert doctor_out["state"] == "blocked_evidence"
    assert "reviewed_manifest_unavailable" in doctor_out["reasons"]
    assert doctor_out["real_mlx_partial_support"] is False
    if platform.system() != "Darwin":
        assert "non_apple_silicon_mlx" in doctor_out["reasons"]

    run = main(["run", "--config", str(path)])
    run_out = json.loads(capsys.readouterr().out)
    assert run == 2
    assert run_out["state"] == "blocked_evidence"
    assert "execution_registry_closed" in run_out["reasons"]
    assert run_out["loads_mlx"] is False
    assert run_out["downloads"] is False


def test_benchmark_stays_blocked_and_does_not_select_model(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["benchmark", "--config", str(tmp_path / "missing.json")])
    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["state"] == "blocked_evidence"
    assert payload["selects_model"] is False
