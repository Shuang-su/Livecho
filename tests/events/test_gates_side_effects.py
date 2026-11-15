from __future__ import annotations

import json
import socket
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from livecho_backend.events import (
    FLAGS,
    attempt_archive,
    attempt_live_adapter,
    attempt_wire_publish,
)


def test_feature_flags_remain_closed() -> None:
    assert FLAGS.live_chat_adapter is False
    assert FLAGS.wire_publish is False
    assert FLAGS.raw_archive is False
    assert attempt_live_adapter() == "live_adapter_disabled"
    assert attempt_wire_publish() == "wire_publish_disabled"
    assert attempt_archive() == "archive_disabled"


def test_import_and_normalize_open_no_sockets(
    monkeypatch: pytest.MonkeyPatch,
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    def forbid(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("events normalize path must not open sockets")

    monkeypatch.setattr(socket, "socket", forbid)
    result = engine.normalize_batch([load_fixture("danmaku_ok.json")])
    assert len(result.records) == 1
    assert attempt_live_adapter() == "live_adapter_disabled"
    assert attempt_wire_publish() == "wire_publish_disabled"
    assert attempt_archive() == "archive_disabled"


def test_normalize_writes_no_chat_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    writes: list[Path] = []
    real_open = Path.open

    def tracking_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        mode = args[0] if args else kwargs.get("mode", "r")
        if isinstance(mode, str) and any(flag in mode for flag in ("w", "a", "x", "+")):
            writes.append(self)
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", tracking_open)
    # Also block builtin open for write modes used by helpers.
    builtin_open = open

    def guarded_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            raise AssertionError(f"unexpected write to {file!r}")
        return builtin_open(file, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", guarded_open)
    result = engine.normalize_batch(
        [
            load_fixture("danmaku_ok.json"),
            load_fixture("superchat_ok.json"),
        ]
    )
    assert len(result.records) == 2
    assert writes == []
    assert list(tmp_path.iterdir()) == []


def test_fixtures_are_synthetic_and_secret_free() -> None:
    root = (
        Path(__file__).resolve().parents[2]
        / "services"
        / "backend"
        / "src"
        / "livecho_backend"
        / "events"
        / "fixtures"
    )
    forbidden = (
        "http://",
        "https://",
        "cookie",
        "sessdata",
        "bili_jct",
        "password",
        "authorization",
    )
    for path in root.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for needle in forbidden:
            assert needle not in lowered, f"{path.name} contains {needle}"
        assert "synthetic" in lowered or "fixture" in lowered
        payload = json.loads(text)
        assert isinstance(payload, dict)
        assert set(payload.keys()) == {"fixture_class", "source_event_id", "source_ts", "body"}


def test_alerts_never_echo_payload_fields(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    item = load_fixture("danmaku_ok.json")
    item = dict(item)
    item["body"] = dict(item["body"])
    item["body"]["text"] = "VISIBLE_CHAT_SHOULD_NOT_LOG"
    item["body"]["sender_display"] = "VISIBLE_SENDER"
    # Force reject via nested object after sensitive scan of names only — use oversize.
    item["body"]["text"] = "x" * 513
    result = engine.normalize_batch([item])
    assert result.alerts[0]["reason"] == "text_invalid"
    blob = json.dumps(result.alerts)
    assert "VISIBLE" not in blob
    assert "sender" not in blob
    assert set(result.alerts[0].keys()) == {"reason", "counters"}
