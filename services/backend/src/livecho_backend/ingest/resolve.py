"""Canonical room_id resolution from operator selectors (fixture metadata only)."""

from __future__ import annotations

import re
from typing import Any

ROOM_ID = re.compile(r"^[1-9][0-9]{0,15}$")
ALIAS = re.compile(r"^live\.bilibili\.com/([1-9][0-9]{0,15})$")


def resolve_room_id(selector: str, alias_map: dict[str, str] | None = None) -> str | None:
    """Return one canonical room_id or None on ambiguity/failure."""
    raw = selector.strip()
    if not raw:
        return None
    if ROOM_ID.fullmatch(raw):
        return raw
    match = ALIAS.fullmatch(raw)
    if match:
        return match.group(1)
    if alias_map is not None and raw in alias_map:
        mapped = alias_map[raw]
        if ROOM_ID.fullmatch(mapped):
            return mapped
        return None
    return None


def parse_fixture_room(payload: dict[str, Any]) -> str | None:
    room = payload.get("room_id")
    if isinstance(room, int) and room > 0:
        return str(room)
    if isinstance(room, str) and ROOM_ID.fullmatch(room):
        return room
    return None
