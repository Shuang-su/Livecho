from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

FIXTURE_DIR = (
    Path(__file__).resolve().parents[2]
    / "services"
    / "backend"
    / "src"
    / "livecho_backend"
    / "events"
    / "fixtures"
)

ROOM_ID = "syn-room-001"
SESSION_ID = "11111111-1111-4111-8111-111111111111"
FIXED_CLOCK = "2026-01-15T12:30:00.000Z"


@pytest.fixture
def load_fixture() -> Callable[[str], dict[str, Any]]:
    def _load(name: str) -> dict[str, Any]:
        payload = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("fixture must be an object")
        return payload

    return _load


@pytest.fixture
def engine() -> Any:
    from livecho_backend.events import NormalizeEngine

    return NormalizeEngine(room_id=ROOM_ID, session_id=SESSION_ID, clock=lambda: FIXED_CLOCK)
