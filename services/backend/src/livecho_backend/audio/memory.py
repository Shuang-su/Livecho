"""Revocable memory ownership. Native buffer aliases never cross the consumer boundary."""

from __future__ import annotations

import time
from collections.abc import Callable
from threading import RLock

from .contracts import AudioError, Reason, Segment
from .ledger import PROCESS_BYTES, Interval, Ledger, Owner, Reservation
from .preflight import RuntimePermit


class OwnedBuffer:
    def __init__(
        self,
        permit: RuntimePermit,
        ledger: Ledger,
        owner: Owner,
        size: int,
        interval: Interval,
        *,
        canonical: bool = True,
    ) -> None:
        permit.require()
        self._ledger = ledger
        self._reservation = ledger.reserve(owner, size, interval, canonical=canonical)
        self._lock = RLock()
        self._live = True
        try:
            self._release_process = PROCESS_BYTES.reserve(size)
            self._data = bytearray(size)
            self._reservation.on_clear(self.clear)
        except BaseException:
            self._reservation.release()
            if hasattr(self, "_release_process"):
                self._release_process()
            raise

    @property
    def size(self) -> int:
        return len(self._data)

    def _check(self) -> None:
        self._reservation.require_valid()
        if not self._live:
            raise AudioError(Reason.HANDLE_INVALID)

    def read_sample(self, index: int) -> int:
        with self._lock:
            self._check()
            if type(index) is not int:
                raise AudioError(Reason.METADATA_INVALID)
            offset = index * 2
            if not 0 <= offset < self.size - 1:
                raise AudioError(Reason.METADATA_INVALID)
            value = self._data[offset] | self._data[offset + 1] << 8
            return value - 65536 if value >= 32768 else value

    def write_sample(self, index: int, sample: int) -> None:
        with self._lock:
            self._check()
            if type(index) is not int or type(sample) is not int or not -32768 <= sample <= 32767:
                raise AudioError(Reason.METADATA_INVALID)
            offset = index * 2
            if not 0 <= offset < self.size - 1:
                raise AudioError(Reason.METADATA_INVALID)
            value = sample & 65535
            self._data[offset] = value & 255
            self._data[offset + 1] = value >> 8

    def borrow(self) -> Reservation:
        with self._lock:
            self._check()
            return self._reservation.borrow()

    def transfer(self, destination: OwnedBuffer, offset: int = 0) -> None:
        """The destination is already reserved. Copy without temporary audio slices."""
        first, second = sorted((self, destination), key=id)
        with first._lock, second._lock:
            self._check()
            destination._check()
            if type(offset) is not int or offset < 0 or offset + self.size > destination.size:
                raise AudioError(Reason.METADATA_INVALID)
            for index in range(self.size):
                destination._data[offset + index] = self._data[index]

    def clear(self) -> None:
        with self._lock:
            if not self._live:
                return
            self._live = False
            for index in range(self.size):
                self._data[index] = 0
            self._reservation.release()
            self._release_process()


class WritableView:
    """One source read receives one capability; revoke it before validating its reply."""

    def __init__(self, buffer: OwnedBuffer, allowed: Callable[[], bool]) -> None:
        self._buffer = buffer
        self._allowed = allowed
        self._live = True
        self._written = 0

    @property
    def size(self) -> int:
        return self._buffer.size

    @property
    def complete(self) -> bool:
        return self._written * 2 == self.size

    @property
    def written_samples(self) -> int:
        return self._written

    def write_sample(self, index: int, sample: int) -> None:
        if not self._live or not self._allowed():
            raise AudioError(Reason.ADMISSION_CLOSED)
        if index != self._written:
            raise AudioError(Reason.METADATA_INVALID)
        self._buffer.write_sample(index, sample)
        self._written += 1

    def revoke(self) -> None:
        self._live = False


class SegmentHandle:
    def __init__(self, metadata: Segment, buffer: OwnedBuffer, now_ms: int) -> None:
        if buffer.size != metadata.sample_count * 2:
            raise AudioError(Reason.METADATA_INVALID)
        self._metadata = metadata
        self._buffer = buffer
        self._live = True
        self._consumed = False
        self.deadline_ms = now_ms + 1000

    @property
    def metadata(self) -> Segment:
        return self._metadata

    def read_sample(self, index: int) -> int:
        now_ms = time.monotonic_ns() // 1_000_000
        if not self._live or now_ms >= self.deadline_ms:
            self.invalidate()
            raise AudioError(Reason.HANDLE_INVALID)
        return self._buffer.read_sample(index)

    @property
    def released(self) -> bool:
        return not self._live

    @property
    def consumed(self) -> bool:
        return self._consumed

    def copy_to(self, permit: RuntimePermit, ledger: Ledger) -> OwnedBuffer:
        now_ms = time.monotonic_ns() // 1_000_000
        if not self._live or now_ms >= self.deadline_ms:
            self.invalidate()
            raise AudioError(Reason.HANDLE_INVALID)
        # Local consumer copies stay charged to the originating session. Issue #9's
        # worker handoff separately accounts its lease; arbitrary new ledgers cannot
        # evade this session's cap.
        if ledger is not self._buffer._ledger:
            raise AudioError(Reason.BUDGET_EXCEEDED)
        copy = OwnedBuffer(
            permit,
            ledger,
            Owner.SEGMENT,
            self._buffer.size,
            Interval(self.metadata.start_pts, self.metadata.end_pts),
        )
        try:
            self._buffer.transfer(copy)
        except BaseException:
            copy.clear()
            raise
        return copy

    def release(self) -> None:
        if self._live:
            self._consumed = time.monotonic_ns() // 1_000_000 < self.deadline_ms
        self.invalidate()

    def invalidate(self) -> None:
        if self._live:
            self._live = False
            self._buffer.clear()
