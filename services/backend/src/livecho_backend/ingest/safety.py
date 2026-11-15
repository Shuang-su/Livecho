"""In-memory kill switch and room denylist. Process start is globally disabled."""

from __future__ import annotations

from dataclasses import dataclass, field

from .actors import Actor, may_control_room
from .gates import Reason


@dataclass
class SafetyControls:
    """Local contract double for #2 safety semantics. Not a durable journal."""

    globally_enabled: bool = False
    denylist: set[str] = field(default_factory=set)
    generation: int = 0
    audit: list[dict[str, str | int]] = field(default_factory=list)

    def enable_global(self, actor: Actor) -> Reason | None:
        # Admin technical re-enable still requires owner preconditions out of scope;
        # this fixture path never flips production on via empty evidence.
        if actor != "admin":
            return "actor_forbidden"
        return "ingest_disabled"  # refuse enable without owner evidence

    def disable_global(self, actor: Actor) -> Reason | None:
        if not may_control_room(actor):
            return "actor_forbidden"
        self.globally_enabled = False
        self.generation += 1
        self.audit.append({"action": "global_disable", "generation": self.generation})
        return None

    def add_denylist(self, actor: Actor, room_id: str) -> Reason | None:
        if not may_control_room(actor):
            return "actor_forbidden"
        if not room_id:
            return "selector_invalid"
        self.denylist.add(room_id)
        self.generation += 1
        self.audit.append(
            {"action": "denylist_add", "room_id": room_id, "generation": self.generation}
        )
        return None

    def is_denied(self, room_id: str) -> bool:
        return room_id in self.denylist

    def may_start(self, room_id: str) -> Reason | None:
        if not self.globally_enabled:
            return "ingest_disabled"
        if self.is_denied(room_id):
            return "room_denied"
        return None
