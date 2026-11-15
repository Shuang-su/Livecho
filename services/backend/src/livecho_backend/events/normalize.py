"""In-process normalize/dedup engine. Never publishes to Timeline/WS."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .validate import (
    MAX_BATCH,
    OUTPUT_KEYS,
    validate_fixture_item,
    validate_room_session,
)

DEDUP_CAPACITY = 4_096
QUEUE_CAPACITY = 256


def _utc_stamp() -> str:
    now = datetime.now(UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


@dataclass
class NormalizeResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    alerts: list[dict[str, Any]] = field(default_factory=list)
    counters: dict[str, int] = field(default_factory=dict)

    def _count(self, key: str) -> None:
        self.counters[key] = self.counters.get(key, 0) + 1

    def alert(self, reason: str) -> None:
        self._count(reason)
        # Payload-free: reason + counters only.
        self.alerts.append({"reason": reason, "counters": dict(self.counters)})


@dataclass
class NormalizeEngine:
    """One-owner normalize session. Process-memory only.

    Dedup identity is (room_id, session_id, source_event_id). Because an engine
    instance is bound to one room/session, the map stores source_event_id only.
    """

    room_id: str
    session_id: str
    clock: Callable[[], str] = _utc_stamp
    _dedup: set[str] = field(default_factory=set)
    _queue: deque[dict[str, Any]] = field(default_factory=deque)

    def clear(self) -> None:
        self._dedup.clear()
        self._queue.clear()

    def clear_dedup(self) -> None:
        self._dedup.clear()

    @property
    def queue(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._queue)

    @property
    def dedup_size(self) -> int:
        return len(self._dedup)

    def normalize_batch(self, items: list[object]) -> NormalizeResult:
        result = NormalizeResult()
        binding = validate_room_session(self.room_id, self.session_id)
        if binding is not None:
            result.alert(binding)
            return result
        if not isinstance(items, list):
            result.alert("schema_invalid")
            return result
        if len(items) > MAX_BATCH:
            result.alert("batch_too_large")
            return result

        session_id = self.session_id.lower()
        for item in items:
            parsed, error = validate_fixture_item(item)
            if error is not None or parsed is None:
                result.alert(error or "schema_invalid")
                continue
            key = parsed["source_event_id"]
            if key in self._dedup:
                result.alert("duplicate_suppressed")
                continue
            if len(self._dedup) >= DEDUP_CAPACITY:
                result.alert("dedup_capacity")
                continue
            record = {
                "schema_version": 1,
                "class": parsed["fixture_class"],
                "source_event_id": parsed["source_event_id"],
                "source_ts": parsed["source_ts"],
                "received_ts": self.clock(),
                "room_id": self.room_id,
                "session_id": session_id,
                "payload": parsed["payload"],
            }
            if set(record.keys()) != OUTPUT_KEYS:
                result.alert("schema_invalid")
                continue
            self._dedup.add(key)
            result.records.append(record)
            self._enqueue(record, result)
        return result

    def _enqueue(self, record: dict[str, Any], result: NormalizeResult) -> None:
        if len(self._queue) >= QUEUE_CAPACITY:
            self._queue.popleft()
            result.alert("queue_overflow")
        self._queue.append(record)
