"""Synchronized reservation metadata; reserve before touching any audio allocation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from threading import RLock

from .contracts import AudioError, Reason

CANONICAL_LIMIT = 960_000
PROCESS_LIMIT = 16_777_216
NONCANONICAL_LIMIT = 4 * 1024 * 1024
DECODER_LIMIT = 8 * 1024 * 1024
WINDOW_MS = 30_000


class Owner(StrEnum):
    RING = "ring"
    SEGMENT = "segment"
    SCRATCH = "scratch"
    PIPE = "pipe"
    PREROLL = "preroll"
    CONTEXT = "context"
    OTHER = "other"
    SOURCE = "source"
    DECODER = "decoder"


PARTITIONS = {
    Owner.RING: 512_000,
    Owner.SEGMENT: 192_000,
    Owner.SCRATCH: 32_000,
    Owner.PIPE: 64_000,
    Owner.PREROLL: 12_800,
    Owner.CONTEXT: 25_600,
    Owner.OTHER: 121_600,
}


@dataclass(frozen=True, slots=True)
class Interval:
    start: int
    end: int

    def __post_init__(self) -> None:
        if type(self.start) is not int or type(self.end) is not int:
            raise AudioError(Reason.METADATA_INVALID)
        if not 0 <= self.start < self.end:
            raise AudioError(Reason.METADATA_INVALID)


@dataclass(frozen=True, slots=True)
class Usage:
    canonical: int
    all_audio: int
    media_span_ms: int
    peak_canonical: int
    peak_all_audio: int


@dataclass(slots=True)
class _Entry:
    owner: Owner
    size: int
    canonical: bool
    interval: Interval
    references: int = 1


class Reservation:
    """Borrowing counts the same physical allocation until the final owner releases."""

    def __init__(self, ledger: Ledger, identity: int) -> None:
        self._ledger = ledger
        self._identity = identity
        self._released = False

    @property
    def valid(self) -> bool:
        with self._ledger._lock:
            return not self._released and self._identity in self._ledger._entries

    def borrow(self) -> Reservation:
        with self._ledger._lock:
            self.require_valid()
            self._ledger._entries[self._identity].references += 1
            return Reservation(self._ledger, self._identity)

    def require_valid(self) -> None:
        if not self.valid:
            raise AudioError(Reason.HANDLE_INVALID)

    def on_clear(self, clear: Callable[[], None]) -> None:
        with self._ledger._lock:
            self.require_valid()
            self._ledger._cleaners[self._identity] = clear

    def move_interval(self, interval: Interval) -> None:
        """Update a reserved pipe's currently retained media envelope before admission."""
        with self._ledger._lock:
            self.require_valid()
            other = [
                entry.interval
                for identity, entry in self._ledger._entries.items()
                if identity != self._identity
            ]
            span = max([interval.end, *(item.end for item in other)]) - min(
                [interval.start, *(item.start for item in other)]
            )
            if span > WINDOW_MS:
                raise AudioError(Reason.BUDGET_EXCEEDED)
            self._ledger._entries[self._identity].interval = interval

    def release(self) -> None:
        with self._ledger._lock:
            if self._released:
                return
            self._released = True
            entry = self._ledger._entries.get(self._identity)
            if entry is not None:
                entry.references -= 1
                if entry.references == 0:
                    del self._ledger._entries[self._identity]
                    self._ledger._cleaners.pop(self._identity, None)


class Ledger:
    """One session or one lease. Processes share a separate process ledger below."""

    def __init__(self, *, decoder: bool = False) -> None:
        self._lock = RLock()
        self._entries: dict[int, _Entry] = {}
        self._cleaners: dict[int, Callable[[], None]] = {}
        self._next = 0
        self._closed = False
        self._peak_canonical = 0
        self._peak_audio = 0
        self._decoder = decoder

    @property
    def usage(self) -> Usage:
        with self._lock:
            entries = list(self._entries.values())
            span = max((e.interval.end for e in entries), default=0) - min(
                (e.interval.start for e in entries), default=0
            )

            return Usage(
                sum(e.size for e in entries if e.canonical),
                sum(e.size for e in entries),
                span,
                self._peak_canonical,
                self._peak_audio,
            )

    def within_window(self, interval: Interval) -> bool:
        with self._lock:
            entries = list(self._entries.values())
            return (
                max([interval.end, *(e.interval.end for e in entries)])
                - min([interval.start, *(e.interval.start for e in entries)])
                <= WINDOW_MS
            )

    def reserve(
        self, owner: Owner, size: int, interval: Interval, *, canonical: bool = True
    ) -> Reservation:
        with self._lock:
            if self._closed:
                raise AudioError(Reason.ADMISSION_CLOSED)
            if (
                type(size) is not int
                or size <= 0
                or not isinstance(owner, Owner)
                or not isinstance(interval, Interval)
                or type(canonical) is not bool
            ):
                raise AudioError(Reason.METADATA_INVALID)
            entries = list(self._entries.values())
            total = sum(e.size for e in entries)
            canonical_bytes = sum(e.size for e in entries if e.canonical)
            span = max([interval.end, *(e.interval.end for e in entries)]) - min(
                [interval.start, *(e.interval.start for e in entries)]
            )
            partition_bytes = sum(e.size for e in entries if e.owner == owner)
            invalid_partition = canonical and (
                owner not in PARTITIONS or partition_bytes + size > PARTITIONS.get(owner, 0)
            )
            if (
                invalid_partition
                or (canonical and canonical_bytes + size > CANONICAL_LIMIT)
                or total + size > (DECODER_LIMIT if self._decoder else PROCESS_LIMIT)
                or (
                    not canonical
                    and total - canonical_bytes + size
                    > (DECODER_LIMIT if self._decoder else NONCANONICAL_LIMIT)
                )
                or span > WINDOW_MS
            ):
                raise AudioError(Reason.BUDGET_EXCEEDED)
            self._next += 1
            self._entries[self._next] = _Entry(owner, size, canonical, interval)
            self._peak_canonical = max(
                self._peak_canonical, canonical_bytes + (size if canonical else 0)
            )
            self._peak_audio = max(self._peak_audio, total + size)
            return Reservation(self, self._next)

    def close_and_clear_memory(self) -> None:
        """Close admission and clear Python owners while pipe reservations remain charged."""
        with self._lock:
            self._closed = True
            cleaners = list(self._cleaners.values())
        # No lock inversion with an in-progress buffer operation holding its own lock.
        for clear in cleaners:
            clear()

    def clear(self) -> None:
        """Clear memory and invalidate reservations after pipes/child have been closed."""
        self.close_and_clear_memory()
        with self._lock:
            self._entries.clear()
            self._cleaners.clear()


class ProcessAdmission:
    """Alpha allows exactly one session and no replacement before confirmed reaping."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._owner: object | None = None

    def acquire(self, owner: object) -> None:
        with self._lock:
            if self._owner is not None:
                raise AudioError(Reason.ADMISSION_CLOSED)
            self._owner = owner

    def release(self, owner: object, *, reaped: bool) -> None:
        with self._lock:
            if self._owner is owner and reaped:
                self._owner = None


PROCESS_ADMISSION = ProcessAdmission()


class ProcessBytes:
    """Physical aggregate shared by every OwnedBuffer, even across consumer ledgers."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.current = 0
        self.peak = 0

    def reserve(self, size: int) -> Callable[[], None]:
        with self._lock:
            if type(size) is not int or size <= 0 or self.current + size > PROCESS_LIMIT:
                raise AudioError(Reason.BUDGET_EXCEEDED)
            self.current += size
            self.peak = max(self.peak, self.current)
        released = False

        def release() -> None:
            nonlocal released
            with self._lock:
                if not released:
                    released = True
                    self.current -= size

        return release


PROCESS_BYTES = ProcessBytes()
