from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from livecho_backend.events.validate import MAX_BATCH, MAX_ITEM_BYTES


def _base(load_fixture: Callable[[str], dict[str, Any]]) -> dict[str, Any]:
    return copy.deepcopy(load_fixture("danmaku_ok.json"))


def test_extra_top_level_key_rejected(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    item = _base(load_fixture)
    item["extra"] = "nope"
    result = engine.normalize_batch([item])
    assert result.records == []
    assert result.alerts[0]["reason"] == "schema_invalid"


def test_extra_body_key_is_schema_invalid_not_text_invalid(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    item = _base(load_fixture)
    item["body"]["color"] = "#fff"
    result = engine.normalize_batch([item])
    assert result.records == []
    assert result.alerts[0]["reason"] == "schema_invalid"


def test_sensitive_key_refused(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    item = _base(load_fixture)
    item["body"]["Cookie"] = "secret-value"
    result = engine.normalize_batch([item])
    assert result.records == []
    assert result.alerts[0]["reason"] == "sensitive_field_refused"
    # Alerts stay payload-free.
    dumped = str(result.alerts)
    assert "secret-value" not in dumped
    assert "synthetic hello" not in dumped


def test_nested_body_object_schema_invalid(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    item = _base(load_fixture)
    item["body"]["text"] = "ok"
    item["body"]["meta"] = {"x": 1}
    result = engine.normalize_batch([item])
    assert result.records == []
    assert result.alerts[0]["reason"] == "schema_invalid"


def test_oversize_text_text_invalid(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    item = _base(load_fixture)
    item["body"]["text"] = "x" * 513
    result = engine.normalize_batch([item])
    assert result.records == []
    assert result.alerts[0]["reason"] == "text_invalid"


def test_non_nfc_text_invalid(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    item = _base(load_fixture)
    # U+0065 U+0301 is NFD for é; NFC would be U+00E9.
    item["body"]["text"] = "cafe\u0301"
    result = engine.normalize_batch([item])
    assert result.records == []
    assert result.alerts[0]["reason"] == "text_invalid"


def test_batch_too_large(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    item = _base(load_fixture)
    items = []
    for i in range(MAX_BATCH + 1):
        clone = copy.deepcopy(item)
        clone["source_event_id"] = f"syn-dm-{i:04d}"
        items.append(clone)
    result = engine.normalize_batch(items)
    assert result.records == []
    assert result.alerts[0]["reason"] == "batch_too_large"
    assert engine.dedup_size == 0


def test_item_byte_cap(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    item = _base(load_fixture)
    # Byte cap is checked before top-level allowlist; pad forces schema_invalid.
    item["pad"] = "x" * (MAX_ITEM_BYTES + 64)
    import json

    encoded = json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode()
    assert len(encoded) > MAX_ITEM_BYTES
    result = engine.normalize_batch([item])
    assert result.records == []
    assert result.alerts[0]["reason"] == "schema_invalid"


def test_unknown_class_rejected(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    item = _base(load_fixture)
    item["fixture_class"] = "gift"
    result = engine.normalize_batch([item])
    assert result.alerts[0]["reason"] == "schema_invalid"


def test_bool_not_int_for_ms(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    item = load_fixture("transcript_companion_ok.json")
    item = copy.deepcopy(item)
    item["body"]["start_ms"] = False
    item["body"]["end_ms"] = True
    result = engine.normalize_batch([item])
    assert result.alerts[0]["reason"] == "schema_invalid"


def test_transcript_range_cap(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    item = copy.deepcopy(load_fixture("transcript_companion_ok.json"))
    item["body"]["start_ms"] = 0
    item["body"]["end_ms"] = 30_001
    result = engine.normalize_batch([item])
    assert result.alerts[0]["reason"] == "schema_invalid"


def test_invalid_room_binding() -> None:
    from livecho_backend.events import NormalizeEngine

    bad = NormalizeEngine(
        room_id="",
        session_id="not-a-uuid",
        clock=lambda: "2026-01-15T12:00:00.000Z",
    )
    result = bad.normalize_batch([])
    assert result.alerts[0]["reason"] == "schema_invalid"
