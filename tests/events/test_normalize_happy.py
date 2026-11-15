from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tests.events.conftest import FIXED_CLOCK, ROOM_ID, SESSION_ID


def test_happy_path_each_class(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    items = [
        load_fixture("danmaku_ok.json"),
        load_fixture("superchat_ok.json"),
        load_fixture("status_ok.json"),
        load_fixture("transcript_companion_ok.json"),
    ]
    result = engine.normalize_batch(items)
    assert result.alerts == []
    assert len(result.records) == 4
    assert [r["class"] for r in result.records] == [
        "danmaku",
        "superchat",
        "status",
        "transcript_companion",
    ]
    for record in result.records:
        assert set(record.keys()) == {
            "schema_version",
            "class",
            "source_event_id",
            "source_ts",
            "received_ts",
            "room_id",
            "session_id",
            "payload",
        }
        assert record["schema_version"] == 1
        assert record["room_id"] == ROOM_ID
        assert record["session_id"] == SESSION_ID.lower()
        assert record["received_ts"] == FIXED_CLOCK
        assert "seq" not in record
        assert "event_id" not in record
        assert "revision" not in record

    assert result.records[0]["payload"] == {
        "text": "synthetic hello",
        "sender_display": "FixtureUser",
    }
    assert result.records[1]["payload"] == {
        "text": "synthetic support",
        "sender_display": "FixturePatron",
        "amount_display": "30",
        "currency_code": "CNY",
    }
    assert result.records[2]["payload"] == {"status": "live", "reason_code": "fixture_live"}
    assert result.records[3]["payload"] == {
        "text": "synthetic caption companion",
        "start_ms": 1000,
        "end_ms": 2500,
        "is_final": True,
    }
    assert len(engine.queue) == 4
