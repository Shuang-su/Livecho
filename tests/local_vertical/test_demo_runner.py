"""CLI demo-runner smoke tests for the fixture_timeline local vertical."""

from __future__ import annotations

import asyncio
import json
import socket

import pytest
from livecho_backend.local_vertical.config import LocalVerticalConfig, LocalVerticalMode
from livecho_backend.local_vertical.runner import main
from livecho_backend.local_vertical.schedule import FixtureScheduleSpec, validate_fixture_schedule
from livecho_backend.local_vertical.timeline import FixtureScheduleError


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_demo_completes_with_two_segments(capsys: pytest.CaptureFixture[str]) -> None:
    port = _free_port()
    code = main(["--port", str(port), "--segments", "2"])
    captured = capsys.readouterr()
    assert code == 0, captured.out + captured.err
    assert "fixture_complete" in captured.out


def test_blocked_mlx_returns_two_with_blocked_evidence(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["--mode", "synthetic_mlx"])
    captured = capsys.readouterr()
    assert code == 2
    combined = captured.out + captured.err
    assert "blocked_evidence" in combined
    payload = json.loads(combined.strip().splitlines()[-1])
    assert payload["outcome"] == "blocked_evidence"
    assert payload["mode"] == "synthetic_mlx"
    assert payload["real_asr_evidence"] is False


def test_invalid_schedule_exceeds_sixty_second_bound() -> None:
    with pytest.raises(FixtureScheduleError, match="60 second"):
        validate_fixture_schedule(FixtureScheduleSpec(segments=999, interval_ms=3_000))


def test_invalid_schedule_cli_returns_two(capsys: pytest.CaptureFixture[str]) -> None:
    port = _free_port()
    code = main(
        [
            "--port",
            str(port),
            "--segments",
            "999",
            "--interval-ms",
            "3000",
        ]
    )
    captured = capsys.readouterr()
    assert code == 2, captured.out + captured.err
    assert "blocked_evidence" in captured.out or "60 second" in captured.out


def test_open_fixture_session_requires_fixture_mode() -> None:
    async def scenario() -> None:
        from livecho_backend.local_vertical.service import LocalVerticalService, ModeBlockedError

        service = LocalVerticalService(
            LocalVerticalConfig(mode=LocalVerticalMode.SYNTHETIC_MLX, port=0)
        )
        with pytest.raises(ModeBlockedError):
            await service.open_fixture_session()

    asyncio.run(scenario())
