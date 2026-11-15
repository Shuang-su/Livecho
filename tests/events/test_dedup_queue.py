from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from livecho_backend.events.normalize import DEDUP_CAPACITY, QUEUE_CAPACITY


def test_duplicate_suppressed_single_emit(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    item = load_fixture("danmaku_ok.json")
    first = engine.normalize_batch([item])
    second = engine.normalize_batch([item])
    assert len(first.records) == 1
    assert second.records == []
    assert second.alerts[0]["reason"] == "duplicate_suppressed"
    assert second.counters["duplicate_suppressed"] == 1
    assert len(engine.queue) == 1


def test_reorder_and_reconnect_retained_dedup(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    a = load_fixture("danmaku_ok.json")
    b = load_fixture("superchat_ok.json")
    c = load_fixture("status_ok.json")
    # First feed in order a,b,c
    r1 = engine.normalize_batch([a, b, c])
    assert [x["source_event_id"] for x in r1.records] == [
        "syn-dm-001",
        "syn-sc-001",
        "syn-st-001",
    ]
    # Reorder + re-feed (reconnect simulation with retained dedup)
    r2 = engine.normalize_batch([c, a, b])
    assert r2.records == []
    assert r2.counters.get("duplicate_suppressed") == 3
    assert len(engine.queue) == 3


def test_reconnect_after_clear_dedup_allows_reemit(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    item = load_fixture("danmaku_ok.json")
    engine.normalize_batch([item])
    engine.clear_dedup()
    again = engine.normalize_batch([item])
    assert len(again.records) == 1
    # Queue still holds both retained copies after clear_dedup (queue uncleared).
    assert len(engine.queue) == 2


def test_dedup_capacity_drops_without_insert(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    base = load_fixture("danmaku_ok.json")
    # Fill to capacity in chunks to avoid batch_too_large.
    filled = 0
    while filled < DEDUP_CAPACITY:
        chunk: list[dict[str, Any]] = []
        for i in range(min(256, DEDUP_CAPACITY - filled)):
            item = copy.deepcopy(base)
            item["source_event_id"] = f"syn-fill-{filled + i:05d}"
            chunk.append(item)
        result = engine.normalize_batch(chunk)
        # Filling past QUEUE_CAPACITY legitimately emits queue_overflow; ignore those.
        assert all(a["reason"] == "queue_overflow" for a in result.alerts)
        assert len(result.records) == len(chunk)
        filled += len(chunk)
    assert engine.dedup_size == DEDUP_CAPACITY
    overflow = copy.deepcopy(base)
    overflow["source_event_id"] = "syn-fill-overflow"
    blocked = engine.normalize_batch([overflow])
    assert blocked.records == []
    assert blocked.alerts[0]["reason"] == "dedup_capacity"
    assert engine.dedup_size == DEDUP_CAPACITY


def test_queue_overflow_drops_oldest_and_counts(
    engine: Any,
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    base = load_fixture("danmaku_ok.json")
    # Clear dedup between batches so we can emit more than DEDUP while testing queue.
    # Actually we need unique ids up to QUEUE_CAPACITY+N without hitting dedup_capacity.
    assert QUEUE_CAPACITY < DEDUP_CAPACITY
    produced = 0
    while produced < QUEUE_CAPACITY + 3:
        chunk = []
        for i in range(min(256, QUEUE_CAPACITY + 3 - produced)):
            item = copy.deepcopy(base)
            item["source_event_id"] = f"syn-q-{produced + i:05d}"
            chunk.append(item)
        result = engine.normalize_batch(chunk)
        produced += len(chunk)
        if produced <= QUEUE_CAPACITY:
            assert "queue_overflow" not in result.counters
    assert len(engine.queue) == QUEUE_CAPACITY
    assert engine.queue[0]["source_event_id"] == "syn-q-00003"
    # Last three inserts each overflowed once.
    # Recount via a fresh overflow-producing call is awkward; inspect last batch alerts
    # by replaying a known overflow.
    probe = copy.deepcopy(base)
    probe["source_event_id"] = "syn-q-probe"
    overflowed = engine.normalize_batch([probe])
    assert overflowed.counters["queue_overflow"] == 1
    assert len(engine.queue) == QUEUE_CAPACITY
    assert engine.queue[-1]["source_event_id"] == "syn-q-probe"
    assert engine.queue[0]["source_event_id"] == "syn-q-00004"
