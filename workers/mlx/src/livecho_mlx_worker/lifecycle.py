"""One-owner worker lifecycle. Generation tokens are not wire epochs."""

from __future__ import annotations

from enum import StrEnum


class State(StrEnum):
    STOPPED = "stopped"
    ENROLLING = "enrolling"
    DIAGNOSING = "diagnosing"
    CONNECTING = "connecting"
    READY = "ready"
    RECEIVING = "receiving"
    TRANSCRIBING = "transcribing"
    STOPPING = "stopping"
    FAILED = "failed"


_TRANSITIONS: dict[State, frozenset[State]] = {
    State.STOPPED: frozenset({State.ENROLLING, State.DIAGNOSING, State.CONNECTING}),
    State.ENROLLING: frozenset({State.STOPPED, State.FAILED}),
    State.DIAGNOSING: frozenset({State.STOPPED, State.FAILED}),
    State.CONNECTING: frozenset({State.READY, State.STOPPING, State.FAILED}),
    State.READY: frozenset({State.RECEIVING, State.STOPPING, State.FAILED}),
    State.RECEIVING: frozenset({State.TRANSCRIBING, State.STOPPING, State.FAILED}),
    State.TRANSCRIBING: frozenset({State.READY, State.STOPPING, State.FAILED}),
    State.STOPPING: frozenset({State.STOPPED, State.FAILED}),
    State.FAILED: frozenset({State.STOPPED}),
}


class Lifecycle:
    def __init__(self) -> None:
        self.state = State.STOPPED
        self.generation = 0
        self.admission_open = False

    def transition(self, target: State) -> None:
        if target not in _TRANSITIONS[self.state]:
            raise RuntimeError(f"invalid_transition:{self.state}->{target}")
        self.state = target
        if target in {State.STOPPED, State.FAILED, State.STOPPING}:
            self.admission_open = False
        if target == State.CONNECTING:
            self.generation += 1

    def open_admission(self) -> None:
        if self.state not in {State.READY, State.RECEIVING, State.TRANSCRIBING}:
            raise RuntimeError("admission_closed")
        self.admission_open = True

    def close_admission(self) -> None:
        self.admission_open = False
