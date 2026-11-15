"""Session timeline ordering and fixture mutable-event admission rules."""

from __future__ import annotations

import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from livecho_protocol.errors import Decision, StableCode
from livecho_protocol.models import PROTOCOL_MINOR, VIEWER_PROTOCOL
from livecho_protocol.state import REVISION_DOMAIN_CAPACITY, StreamOrderingState

from .config import FIXTURE_ADMISSION_INTERVAL_MS, FIXTURE_FINAL_DEADLINE_MS


class FixtureScheduleError(Exception):
    """Fixture control or schedule violated accepted bounds."""


class FixtureDeadlineMissed(FixtureScheduleError):
    """A fixture partial was not finalized within the 1,000 ms deadline."""


class RevisionCapacityExceeded(FixtureScheduleError):
    """A new timeline identity cannot be admitted without state change."""


TERMINAL_SESSION_STATUSES = frozenset({"stopping", "stopped", "failed"})


def utc_stamp() -> str:
    """Return an RFC 3339 UTC timestamp string."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def event_is_terminal(message: Mapping[str, Any]) -> bool:
    """Return whether a timeline event is a terminal session status."""
    if message.get("type") != "viewer.timeline_event":
        return False
    payload = message.get("payload")
    if not isinstance(payload, Mapping):
        return False
    status = payload.get("status")
    return isinstance(status, str) and status in TERMINAL_SESSION_STATUSES


def transcript_is_partial(message: Mapping[str, Any]) -> bool:
    payload = message.get("payload")
    if not isinstance(payload, Mapping):
        return False
    return "segment_id" in payload and not bool(payload.get("is_final", False))


def transcript_is_final(message: Mapping[str, Any]) -> bool:
    payload = message.get("payload")
    if not isinstance(payload, Mapping):
        return False
    return "segment_id" in payload and bool(payload.get("is_final", False))


@dataclass(slots=True)
class MutableFixtureEvent:
    """At most one open fixture partial and its finalization deadline."""

    event_id: str
    revision_one_at: float
    deadline_at: float


@dataclass(slots=True)
class LocalTimeline:
    """Backend-owned viewer timeline with v1 ordering and fixture admission."""

    session_id: str
    room_id: str
    epoch: int = 1
    ordering: StreamOrderingState = field(init=False)
    next_seq: int = 1
    session_status: str = "stopped"
    reason_code: str | None = None
    mutable: MutableFixtureEvent | None = None
    last_mutable_final_monotonic: float = 0.0

    def __post_init__(self) -> None:
        self.ordering = StreamOrderingState(
            session_id=self.session_id,
            lease_id=None,
            epoch=self.epoch,
            start_seq=self.next_seq,
            revision_capacity=REVISION_DOMAIN_CAPACITY,
        )

    def reset_session(self, *, room_id: str | None = None) -> None:
        """Replace the session identity and clear ordering state."""
        self.session_id = str(uuid.uuid4())
        self.epoch = 1
        self.next_seq = 1
        self.session_status = "stopped"
        self.reason_code = None
        self.mutable = None
        self.last_mutable_final_monotonic = 0.0
        if room_id is not None:
            self.room_id = room_id
        self.ordering = StreamOrderingState(
            session_id=self.session_id,
            lease_id=None,
            epoch=self.epoch,
            start_seq=self.next_seq,
            revision_capacity=REVISION_DOMAIN_CAPACITY,
        )

    def fresh_admission_allowed(self, now: float | None = None) -> bool:
        """Fresh subscribe is safe only when no mutable object is open.

        The 2,000 ms admission interval gates the schedule's next mutable
        object, not viewer admission after a final.
        """
        del now  # reserved for clock injection in tests
        return self.mutable is None

    def mutable_open_allowed(self, now: float | None = None) -> bool:
        """The schedule may open another mutable object only after the interval."""
        if self.mutable is not None:
            return False
        if self.last_mutable_final_monotonic <= 0:
            return True
        reference = time.monotonic() if now is None else now
        elapsed_ms = (reference - self.last_mutable_final_monotonic) * 1_000
        return elapsed_ms >= FIXTURE_ADMISSION_INTERVAL_MS

    def open_mutable(self, event_id: str, now: float | None = None) -> None:
        """Mark revision 1 of a fixture transcript as mutable."""
        reference = time.monotonic() if now is None else now
        if not self.mutable_open_allowed(reference):
            raise FixtureScheduleError("fixture admission interval not elapsed")
        self.mutable = MutableFixtureEvent(
            event_id=event_id,
            revision_one_at=reference,
            deadline_at=reference + FIXTURE_FINAL_DEADLINE_MS / 1_000,
        )

    def close_mutable(self, event_id: str, now: float | None = None) -> None:
        """Finalize the sole mutable fixture object."""
        if self.mutable is None or self.mutable.event_id != event_id:
            return
        reference = time.monotonic() if now is None else now
        if reference > self.mutable.deadline_at:
            raise FixtureDeadlineMissed("fixture partial missed final deadline")
        self.mutable = None
        self.last_mutable_final_monotonic = reference

    def check_mutable_deadline(self, now: float | None = None) -> None:
        if self.mutable is None:
            return
        reference = time.monotonic() if now is None else now
        if reference > self.mutable.deadline_at:
            raise FixtureDeadlineMissed("fixture partial missed final deadline")

    def allocate_seq(self) -> int:
        seq = self.next_seq
        self.next_seq += 1
        return seq

    def envelope_fields(self) -> dict[str, object]:
        return {
            "protocol": VIEWER_PROTOCOL,
            "protocol_minor": PROTOCOL_MINOR,
            "message_id": str(uuid.uuid4()),
            "sent_at": utc_stamp(),
        }

    def accept_timeline_event(self, message: Mapping[str, Any]) -> Decision:
        """Validate and commit one outbound timeline event."""
        decision = self.ordering.accept(message)
        if decision.code == StableCode.REVISION_CAPACITY_EXCEEDED:
            raise RevisionCapacityExceeded("revision domain capacity exceeded")
        if not decision.accepted:
            return decision
        payload = message.get("payload")
        if isinstance(payload, Mapping) and "status" in payload:
            self.session_status = str(payload["status"])
            reason = payload.get("reason_code")
            self.reason_code = str(reason) if reason is not None else None
        if transcript_is_partial(message):
            self.open_mutable(str(message["event_id"]))
        elif transcript_is_final(message):
            self.close_mutable(str(message["event_id"]))
        return decision
