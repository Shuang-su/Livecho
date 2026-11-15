"""Issue #2 actor matrix for room ingest control (deny by default)."""

from __future__ import annotations

from typing import Literal

Actor = Literal["anonymous", "invited", "contributor", "operator", "admin"]

_CONTROL_ACTORS: frozenset[Actor] = frozenset({"operator", "admin"})


def may_control_room(actor: Actor) -> bool:
    return actor in _CONTROL_ACTORS
