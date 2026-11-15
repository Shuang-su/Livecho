from __future__ import annotations

import json
import socket
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from livecho_backend.ingest.diagnostics import redact_url
from livecho_backend.ingest.session import IngestSession


def test_import_and_fixture_path_open_no_sockets(
    monkeypatch: pytest.MonkeyPatch,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    def forbid(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("ingest fixture path must not open sockets")

    monkeypatch.setattr(socket, "socket", forbid)
    session = IngestSession()
    assert (
        session.start_fixture(
            "operator",
            "123456",
            load_fixture("live_free.json"),
            playback_url="https://play.example.test/x",
            force_safety_enabled=True,
        )
        is None
    )
    session.note_stall()
    session.reconnect_fixture(load_fixture("live_free.json"), wall_delta_ms=1)
    session.stop(actor="operator")


def test_fixtures_contain_no_secrets() -> None:
    root = (
        Path(__file__).resolve().parents[2]
        / "services"
        / "backend"
        / "src"
        / "livecho_backend"
        / "ingest"
        / "fixtures"
    )
    forbidden = ("http://", "https://", "token", "cookie", "sessdata", "bili_jct")
    for path in root.glob("*.json"):
        text = path.read_text(encoding="utf-8").lower()
        for needle in forbidden:
            assert needle not in text, f"{path.name} contains {needle}"
        json.loads(path.read_text(encoding="utf-8"))


def test_redact_url_strips_query() -> None:
    assert redact_url("https://play.example.test/path?token=secret") == (
        "https://play.example.test/redacted"
    )
