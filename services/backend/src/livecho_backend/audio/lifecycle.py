"""Serialized control state and deadlines; no timers, audio retry queue, or wire mutation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .contracts import AudioError, Reason
from .ledger import Interval


class State(StrEnum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    BACKPRESSURED = "backpressured"
    RETRY_WAIT = "retry_wait"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


RETRYABLE = frozenset(
    (
        Reason.INPUT_STALLED,
        Reason.DECODER_EXIT,
        Reason.DECODER_PIPE,
        Reason.DECODER_START_TIMEOUT,
    )
)


@dataclass(slots=True)
class Metrics:
    dropped_ms: dict[Reason, int] = field(default_factory=dict)
    trimmed_silence_ms: int = 0
    below_onset_ms: int = 0
    unmeasurable_input: int = 0
    pause_ms: int = 0
    stall_ms: int = 0
    retries: int = 0
    reaps: int = 0
    reap_failures: int = 0

    def drop(self, reason: Reason, intervals: list[Interval]) -> None:
        end = -1
        unique = 0
        for interval in sorted(intervals, key=lambda item: item.start):
            unique += max(0, interval.end - max(end, interval.start))
            end = max(end, interval.end)
        self.dropped_ms[reason] = self.dropped_ms.get(reason, 0) + unique


class Lifecycle:
    """One pipeline owner invokes this synchronously, including gate-close before awaits."""

    def __init__(self, *, restartable: bool) -> None:
        self.state = State.IDLE
        self.reason: Reason | None = None
        self.generation = 0
        self.gate_open = False
        self.restartable = restartable
        self.metrics = Metrics()
        self._last_clock = 0
        self._started = 0
        self._progress = 0
        self._pause: int | None = None
        self._before_pause = State.RUNNING
        self._retry_at: int | None = None
        self._retry_count = 0
        self._terminal_requested = False
        self._eof = False
        self._eof_deadline: int | None = None
        self.continuity_broken = False

    def _time(self, now: int) -> None:
        if type(now) is not int or now < self._last_clock:
            raise AudioError(Reason.METADATA_INVALID)
        self._last_clock = now

    def start(self, now: int, *, admitted: bool) -> int:
        self._time(now)
        if not admitted or self.state not in (State.IDLE, State.RETRY_WAIT):
            raise AudioError(Reason.ADMISSION_CLOSED)
        if self.state == State.RETRY_WAIT and (self._retry_at is None or now < self._retry_at):
            raise AudioError(Reason.ADMISSION_CLOSED)
        self.generation += 1
        self.state = State.STARTING
        self.gate_open = True
        self._started = self._progress = now
        self._pause = None
        self._eof = False
        self._eof_deadline = None
        self.reason = None
        return self.generation

    def require(self, generation: int) -> None:
        if not self.gate_open or generation != self.generation:
            self.abort(Reason.ADMISSION_CLOSED)
            raise AudioError(Reason.ADMISSION_CLOSED)

    def progress(self, now: int, *, canonical: bool = False) -> None:
        self._time(now)
        if self.state not in (State.STARTING, State.RUNNING):
            raise AudioError(Reason.ADMISSION_CLOSED)
        self._progress = now
        if canonical:
            self.state = State.RUNNING

    def pause(self, now: int) -> None:
        self._time(now)
        if self.state not in (State.RUNNING, State.STARTING, State.BACKPRESSURED):
            raise AudioError(Reason.ADMISSION_CLOSED)
        if self._pause is None:
            self._pause = now
            self._before_pause = self.state
        self.state = State.BACKPRESSURED
        self.gate_open = False

    def resume(self, now: int, *, reserved: bool, admitted: bool) -> bool:
        self._time(now)
        if self.state != State.BACKPRESSURED or self._pause is None:
            return False
        if not admitted:
            self.abort(Reason.DISABLED, terminal=True)
            return False
        if now - self._pause >= 500:
            self.abort(Reason.CONSUMER_SLOW, terminal=True)
            return False
        if reserved:
            self.metrics.pause_ms += now - self._pause
            self._progress += now - self._pause
            self._started += now - self._pause
            self._pause = None
            self.state = self._before_pause
            self.gate_open = not self._eof
            return True
        return False

    def eof(self, now: int, *, handle_pending: bool) -> None:
        self._time(now)
        self.gate_open = False
        self._eof = True
        self._terminal_requested = True
        self._eof_deadline = now + 1000 if handle_pending else now
        self.state = State.STOPPING

    def remaining_ms(self, now: int) -> int:
        self._time(now)
        anchor = self._started if self.state == State.STARTING else self._progress
        return max(0, anchor + 2000 - now)

    def tick(self, now: int) -> None:
        self._time(now)
        if self.state == State.STARTING and now - self._started >= 2000:
            self.abort(Reason.DECODER_START_TIMEOUT)
        elif self.state == State.RUNNING and now - self._progress >= 2000:
            self.metrics.stall_ms += now - self._progress
            self.abort(Reason.INPUT_STALLED)
        elif (
            self.state == State.BACKPRESSURED
            and self._pause is not None
            and now - self._pause >= 500
        ):
            self.metrics.pause_ms += now - self._pause
            self.abort(Reason.CONSUMER_SLOW, terminal=True)

    def abort(self, reason: Reason, *, terminal: bool = False) -> None:
        # This method contains no await: late source/consumer callbacks immediately lose authority.
        self.gate_open = False
        self.generation += 1
        self.reason = reason
        self._terminal_requested |= terminal or reason not in RETRYABLE
        self.state = State.STOPPING

    def cleaned(self, now: int, *, reaped: bool, admitted: bool) -> None:
        self._time(now)
        if self.state != State.STOPPING:
            return
        if not reaped:
            self.metrics.reap_failures += 1
            self.reason = Reason.DECODER_REAP_FAILED
            self.state = State.FAILED
        elif self.reason is None and self._eof:
            self.metrics.reaps += 1
            self.state = State.STOPPED
        elif (
            admitted
            and self.restartable
            and not self._terminal_requested
            and self.reason in RETRYABLE
            and self._retry_count < 2
        ):
            self.metrics.reaps += 1
            self._retry_at = now + (250, 1000)[self._retry_count]
            self._retry_count += 1
            self.metrics.retries += 1
            self.continuity_broken = True
            self.state = State.RETRY_WAIT
        else:
            self.metrics.reaps += 1
            self.state = (
                State.STOPPED
                if self.reason
                in (
                    Reason.CANCELLED,
                    Reason.DISABLED,
                    Reason.DENYLISTED,
                    Reason.SESSION_END,
                    Reason.LEASE_END,
                    Reason.SHUTDOWN,
                )
                else State.FAILED
            )

    def retry_due(self, now: int, *, admitted: bool) -> bool:
        self._time(now)
        if self.state != State.RETRY_WAIT:
            return False
        if not admitted:
            self.abort(Reason.DISABLED, terminal=True)
            return False
        return self._retry_at is not None and now >= self._retry_at
