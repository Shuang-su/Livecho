from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURE_DIR = (
    Path(__file__).resolve().parents[2]
    / "services"
    / "backend"
    / "src"
    / "livecho_backend"
    / "ingest"
    / "fixtures"
)


@pytest.fixture
def load_fixture() -> Any:
    def _load(name: str) -> dict[str, Any]:
        payload = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("fixture must be an object")
        return payload

    return _load
