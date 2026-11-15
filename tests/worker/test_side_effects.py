from __future__ import annotations

import builtins
import socket
import subprocess
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from livecho_mlx_worker import cli
from livecho_mlx_worker.fixture_session import FixtureBinding, FixtureSession


def test_import_and_fixture_path_open_no_sockets_or_subprocesses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbid_socket(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("fixture path must not open sockets")

    def forbid_popen(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("fixture path must not spawn processes")

    monkeypatch.setattr(socket, "socket", forbid_socket)
    monkeypatch.setattr(subprocess, "Popen", forbid_popen)
    monkeypatch.setattr(subprocess, "run", forbid_popen)

    session = FixtureSession(
        FixtureBinding(
            lease_id=str(uuid4()),
            session_id=str(uuid4()),
            epoch="1",
            output_start_seq=0,
        )
    )
    session.start()
    session.emit_partial_then_final()
    session.cancel()


def test_run_does_not_write_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "cfg.json"
    assert (
        cli.main(
            [
                "enroll",
                "--config",
                str(config),
                "--worker-id",
                str(uuid4()),
                "--manifest-id",
                "m",
                "--host-evidence-id",
                "h",
            ]
        )
        == 0
    )
    capsys.readouterr()

    writes: list[str] = []

    def track_open(path: Any, *args: Any, **kwargs: Any) -> Any:
        mode = args[0] if args else kwargs.get("mode", "r")
        if isinstance(mode, str) and any(flag in mode for flag in ("w", "a", "x", "+")):
            writes.append(str(path))
        return real_open(path, *args, **kwargs)

    real_open = builtins.open
    monkeypatch.setattr(builtins, "open", track_open)
    assert cli.main(["run", "--config", str(config)]) == 2
    assert writes == []
    # Only the enroll config should exist under tmp_path.
    assert list(tmp_path.iterdir()) == [config]
