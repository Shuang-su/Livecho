from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
from livecho_backend.audio.contracts import CANONICAL, AudioError, SourceFormat
from livecho_backend.audio.ledger import Interval, Ledger, Owner
from livecho_backend.audio.memory import OwnedBuffer
from livecho_backend.audio.preflight import (
    APPROVED_BUILDS,
    APPROVED_HOSTS,
    AllocationInventory,
    ApprovedBuild,
    RuntimePermit,
    fixed_arguments,
    main,
    preflight,
)
from livecho_backend.audio.supervisor import DecoderSupervisor, terminate_and_reap


def build() -> ApprovedBuild:
    # Metadata example only: neither a downloaded executable nor an approval record.
    return ApprovedBuild(
        "unapproved-example",
        Path("/trusted/ffmpeg"),
        "0" * 64,
        "unapproved-version",
        "pending",
        "pending",
        AllocationInventory(8192, 8192, 64000, 4096, 4096, "pending"),
    )


def test_missing_evidence_fails_before_process_or_audio_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def prohibited(*args: Any, **kwargs: Any) -> Any:
        calls.append("unexpected-io")
        raise AssertionError("preflight must reject first")

    monkeypatch.setattr(subprocess, "run", prohibited)
    monkeypatch.setattr(subprocess, "Popen", prohibited)
    monkeypatch.setattr(Path, "open", prohibited)
    assert not APPROVED_BUILDS
    assert not APPROVED_HOSTS
    with pytest.raises(AudioError, match="audio_budget_unverified"):
        preflight("local-ffmpeg", "local-host")
    assert calls == []


def test_constructor_cannot_mint_permit_or_allocate(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(AudioError, match="audio_budget_unverified"):
        RuntimePermit(object(), build(), None)  # type: ignore[arg-type]

    class Denied:
        def require(self) -> None:
            raise AudioError.__new__(AudioError)

    ledger = Ledger()
    with pytest.raises(AudioError):
        OwnedBuffer(Denied(), ledger, Owner.RING, 640, Interval(0, 20))  # type: ignore[arg-type]
    assert ledger.usage.all_audio == 0


@pytest.mark.parametrize(
    "source_format",
    [
        CANONICAL,
        SourceFormat(encoding="pcm_s16le", sample_rate_hz=48000, channels=2),
    ],
)
def test_arguments_are_fixed_raw_pipes(source_format: SourceFormat) -> None:
    arguments = fixed_arguments(build(), source_format)
    assert arguments[0] == "/trusted/ffmpeg"
    assert arguments[-1] == "pipe:1"
    assert arguments[arguments.index("-i") + 1] == "pipe:0"
    assert arguments.count("4096") == 2
    assert arguments.count("-protocol_whitelist") == 2
    assert arguments.count("pipe") == 2
    assert "-nostdin" in arguments and "-nostats" in arguments
    assert not any(value in arguments for value in ("-report", "file", "cache", "http", "-y"))
    assert arguments.index("-f") < arguments.index("-i")


@pytest.mark.parametrize(
    "field,value",
    [
        ("decoder_audio_bytes", 8388609),
        ("parent_noncanonical_bytes", 4194305),
        ("stdin_capacity", 65536),
        ("stdout_capacity", 0),
        ("evidence_id", ""),
    ],
)
def test_unbounded_inventory_rejected(field: str, value: object) -> None:
    from dataclasses import asdict

    data = asdict(build().inventory)
    data[field] = value
    with pytest.raises(AudioError, match="audio_budget_unverified"):
        AllocationInventory(**data).validate()


def test_runtime_check_is_failure_not_successful_skip(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 2
    assert "audio_budget_unverified" in capsys.readouterr().out


class ChildDouble:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls: list[str | float] = []
        self.dead = False

    def poll(self) -> int | None:
        return 0 if self.dead else None

    def terminate(self) -> None:
        self.calls.append("term")

    def kill(self) -> None:
        self.calls.append("kill")

    def wait(self, timeout: float) -> int:
        self.calls.append(timeout)
        if self.failures:
            self.failures -= 1
            raise subprocess.TimeoutExpired("fixed-child-double", timeout)
        self.dead = True
        return 0


@pytest.mark.parametrize(
    "failures,expected,calls",
    [
        (0, True, ["term", 0.5]),
        (1, True, ["term", 0.5, "kill", 0.5]),
        (2, False, ["term", 0.5, "kill", 0.5]),
    ],
)
def test_bounded_term_kill_reap_with_metadata_child_double(
    failures: int, expected: bool, calls: list[str | float]
) -> None:
    child = ChildDouble(failures)
    assert terminate_and_reap(child) == expected
    assert child.calls == calls
    if expected:
        assert terminate_and_reap(child)
        assert child.calls == calls


def test_clean_child_exit_preserves_completed_readiness_until_stdout_drained() -> None:
    from types import SimpleNamespace

    supervisor = DecoderSupervisor.__new__(DecoderSupervisor)
    supervisor.process = SimpleNamespace(poll=lambda: 0)  # type: ignore[assignment]
    supervisor._ready = -1
    supervisor.check()
    assert supervisor.ready()
