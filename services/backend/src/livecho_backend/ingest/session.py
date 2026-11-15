"""Owner-serialized room ingest state machine (fixture/contract path)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .actors import Actor, may_control_room
from .eligibility import evaluate_fixture_metadata
from .gates import Reason, evidence_blockers, real_acquisition_allowed
from .resolve import resolve_room_id
from .safety import SafetyControls


class RoomState(StrEnum):
    OFFLINE = "OFFLINE"
    STARTING = "STARTING"
    LIVE = "LIVE"
    STALLED = "STALLED"
    RECONNECTING = "RECONNECTING"
    ENDED = "ENDED"


# Spec defaults: ≤ 8 attempts and ≤ 120 s total wall unless revised.
MAX_RECONNECT_ATTEMPTS = 8
MAX_RECONNECT_WALL_MS = 120_000
BACKOFF_BASE_MS = 250
BACKOFF_CAP_MS = 8_000


@dataclass
class IngestSession:
    safety: SafetyControls = field(default_factory=SafetyControls)
    state: RoomState = RoomState.OFFLINE
    room_id: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    reconnect_attempts: int = 0
    reconnect_wall_ms: int = 0
    _playback_url: str | None = None
    _session_token: str | None = None
    _audio_held: bool = False

    def _emit(self, reason: str | None = None) -> None:
        self.events.append(
            {
                "schema_version": 1,
                "state": self.state.value,
                "reason": reason,
                "counters": {
                    "reconnect_attempts": self.reconnect_attempts,
                    "reconnect_wall_ms": self.reconnect_wall_ms,
                },
                "fixture_not_live_integration": True,
            }
        )

    def _clear_secrets_and_audio(self) -> None:
        self._playback_url = None
        self._session_token = None
        self._audio_held = False

    @property
    def has_playback_secrets(self) -> bool:
        return self._playback_url is not None or self._session_token is not None

    def backoff_ms(self, attempt: int) -> int:
        if attempt < 1:
            return 0
        delay = BACKOFF_BASE_MS * (2 ** (attempt - 1))
        return int(min(delay, BACKOFF_CAP_MS))

    def start_real(self, actor: Actor, selector: str) -> Reason:
        """Real acquisition path: always fail-closed while registries stay empty."""
        if not may_control_room(actor):
            return "actor_forbidden"
        room_id = resolve_room_id(selector)
        if room_id is None:
            return "selector_invalid"
        blocked = self.safety.may_start(room_id)
        if blocked is not None:
            return blocked
        if not real_acquisition_allowed():
            # Prefer the first hard evidence blocker.
            blockers = evidence_blockers()
            return blockers[0] if blockers else "acquisition_channel_unselected"
        return "acquisition_channel_unselected"

    def start_fixture(
        self,
        actor: Actor,
        selector: str,
        metadata: dict[str, Any],
        *,
        playback_url: str | None = None,
        session_token: str | None = None,
        force_safety_enabled: bool = False,
    ) -> Reason | None:
        """Drive the state machine with synthetic metadata. No sockets."""
        if not may_control_room(actor):
            return "actor_forbidden"
        if self.state not in {RoomState.OFFLINE, RoomState.ENDED}:
            return "eligibility_failed"
        room_id = resolve_room_id(selector)
        if room_id is None:
            return "selector_invalid"

        # Process default is disabled; fixture tests may enable a local double only.
        if force_safety_enabled:
            self.safety.globally_enabled = True
        gate = self.safety.may_start(room_id)
        if gate is not None:
            self.state = RoomState.OFFLINE if self.state == RoomState.OFFLINE else RoomState.ENDED
            self._emit(gate)
            return gate

        eligibility = evaluate_fixture_metadata(metadata)
        if eligibility.room_id != room_id:
            self._emit("selector_invalid")
            return "selector_invalid"
        if eligibility.reason is not None:
            self.state = RoomState.ENDED
            self._clear_secrets_and_audio()
            self._emit(eligibility.reason)
            return eligibility.reason

        self.room_id = room_id
        self.reconnect_attempts = 0
        self.reconnect_wall_ms = 0
        self.state = RoomState.STARTING
        self._emit(None)
        # Fixture "anonymous public play confirmed" — hold secrets in RAM only.
        self._playback_url = playback_url
        self._session_token = session_token
        self._audio_held = False  # fixture path never admits audio
        self.state = RoomState.LIVE
        self._emit(None)
        return None

    def note_stall(self) -> None:
        if self.state != RoomState.LIVE:
            return
        self.state = RoomState.STALLED
        self._emit("eligibility_failed")

    def reconnect_fixture(
        self,
        metadata: dict[str, Any],
        *,
        wall_delta_ms: int,
        playback_url: str | None = None,
        session_token: str | None = None,
    ) -> Reason | None:
        if self.state not in {RoomState.STALLED, RoomState.RECONNECTING}:
            return "eligibility_failed"
        if self.room_id is None:
            return "selector_invalid"
        gate = self.safety.may_start(self.room_id)
        if gate is not None:
            self.stop(reason=gate)
            return gate

        self.reconnect_attempts += 1
        self.reconnect_wall_ms += max(0, wall_delta_ms)
        delay = self.backoff_ms(self.reconnect_attempts)
        self.reconnect_wall_ms += delay
        # Clear prior locators before any replacement (never reuse stale URL).
        self._clear_secrets_and_audio()
        self.state = RoomState.RECONNECTING
        self._emit(None)

        if (
            self.reconnect_attempts > MAX_RECONNECT_ATTEMPTS
            or self.reconnect_wall_ms > MAX_RECONNECT_WALL_MS
        ):
            self.state = RoomState.ENDED
            self._emit("retry_exhausted")
            return "retry_exhausted"

        eligibility = evaluate_fixture_metadata(metadata)
        if eligibility.reason is not None or eligibility.room_id != self.room_id:
            reason: Reason = eligibility.reason or "eligibility_failed"
            self.state = RoomState.ENDED
            self._emit(reason)
            return reason

        self._playback_url = playback_url
        self._session_token = session_token
        self.state = RoomState.LIVE
        self._emit(None)
        return None

    def stop(self, actor: Actor | None = None, reason: Reason = "operator_stop") -> Reason | None:
        if actor is not None and not may_control_room(actor):
            return "actor_forbidden"
        self._clear_secrets_and_audio()
        if self.state != RoomState.OFFLINE:
            self.state = RoomState.ENDED
        self._emit(reason)
        return None

    def apply_disable(self, actor: Actor) -> Reason | None:
        err = self.safety.disable_global(actor)
        if err is not None:
            return err
        if self.state not in {RoomState.OFFLINE, RoomState.ENDED}:
            self.stop(reason="ingest_disabled")
        return None

    def apply_denylist(self, actor: Actor, room_id: str) -> Reason | None:
        err = self.safety.add_denylist(actor, room_id)
        if err is not None:
            return err
        if self.room_id == room_id and self.state not in {RoomState.OFFLINE, RoomState.ENDED}:
            self.stop(reason="room_denied")
        return None

    def handoff_playback_url_to_audio(self) -> Reason:
        """#8 forbids playback-URL handoff; always refuse."""
        return "encoded_admission_missing"

    def snapshot_events(self) -> tuple[dict[str, Any], ...]:
        # Ensure secrets never appear on emitted events.
        for event in self.events:
            assert "playback" not in event
            assert "token" not in event
            assert "url" not in event
        return tuple(self.events)
