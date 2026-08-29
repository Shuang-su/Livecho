"""Composable lease-local state proving terminal expiry and cancellation behavior."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .binary import PROCESS_AUDIO_BUDGET, PcmLeaseState
from .errors import Decision, StableCode
from .models import LeaseCancelV1, LeaseV1
from .scalars import parse_timestamp
from .state import ActiveLease, CancellationRegistry, LeaseRevisionState, StreamOrderingState

_PROCESS_CANCELLATIONS = CancellationRegistry()


class _ProcessPcmBudget:
    """Process-wide logical count for ephemeral PCM bytes currently awaiting consumption."""

    def __init__(self) -> None:
        self.buffered_bytes = 0

    def add(self, byte_count: int) -> None:
        if byte_count < 0 or self.buffered_bytes + byte_count > PROCESS_AUDIO_BUDGET:
            raise RuntimeError("invalid process PCM budget increase")
        self.buffered_bytes += byte_count

    def release(self, byte_count: int) -> None:
        if byte_count < 0 or byte_count > self.buffered_bytes:
            raise RuntimeError("invalid process PCM budget release")
        self.buffered_bytes -= byte_count


_PROCESS_PCM_BUDGET = _ProcessPcmBudget()


class LeaseRuntimeCoordinator:
    """Process-scoped owner for lease runtimes and bounded cancellation tombstones."""

    def __init__(self) -> None:
        self._cancellations = _PROCESS_CANCELLATIONS
        self._runtimes = _PROCESS_RUNTIMES
        self._process_pcm = _PROCESS_PCM_BUDGET

    @property
    def tombstone_count(self) -> int:
        return len(self._cancellations.tombstones)

    @property
    def buffered_audio_bytes(self) -> int:
        return self._process_pcm.buffered_bytes

    def create(self, lease: LeaseV1) -> LeaseRuntimeState:
        runtime = LeaseRuntimeState(
            lease=lease,
            cancellations=self._cancellations,
            process_pcm=self._process_pcm,
        )
        self._runtimes.setdefault(runtime.session_id, set()).add(runtime)
        return runtime

    def prune(self, now: datetime) -> None:
        self._cancellations.prune(now)

    def session_teardown(self, session_id: str) -> None:
        for runtime in self._runtimes.pop(session_id, set()):
            runtime._session_teardown()
        self._cancellations.session_teardown(session_id)


class LeaseRuntimeState:
    """Pure in-memory protocol state for one synthetic lease, without scheduling."""

    def __init__(
        self,
        *,
        lease: LeaseV1,
        cancellations: CancellationRegistry,
        process_pcm: _ProcessPcmBudget,
    ) -> None:
        self.lease_id = lease.lease_id
        self.session_id = lease.session_id
        self.epoch = int(lease.epoch)
        self.expires_at = parse_timestamp(lease.expires_at)
        self._terminal_code: StableCode | None = None
        self._allow_cancel_replay = False
        self._cancellations = cancellations
        self._process_pcm = process_pcm
        self._cancellations.add_active(
            ActiveLease(self.lease_id, self.session_id, self.epoch, int(lease.revision))
        )
        self._pcm = PcmLeaseState(
            lease_id=self.lease_id,
            epoch=self.epoch,
            input_start_seq=int(lease.input_start_seq),
        )
        self._output = StreamOrderingState(
            session_id=self.session_id,
            lease_id=self.lease_id,
            epoch=self.epoch,
            start_seq=int(lease.output_start_seq),
        )
        self._lease = LeaseRevisionState(
            session_id=self.session_id,
            lease_id=self.lease_id,
            epoch=self.epoch,
        )
        initial = self._lease.accept(lease.model_dump(mode="json"))
        if initial.code != StableCode.ACCEPTED:
            raise ValueError("initial lease revision was not accepted")

    @property
    def buffered_audio_bytes(self) -> int:
        return self._pcm.buffered_bytes

    @property
    def output_next_expected_seq(self) -> int:
        return self._output.sequence.next_expected_seq

    @property
    def output_revision_count(self) -> int:
        return self._output.revisions.size

    @property
    def lease_revision(self) -> int:
        record = self._lease.revisions.record(
            ("worker.lease", self.session_id, self.lease_id, self.epoch, self.lease_id)
        )
        if record is None:
            raise RuntimeError("lease revision state is cleared")
        return record.current_revision

    @property
    def cancellation_active(self) -> bool:
        return self.lease_id in self._cancellations.active

    def _clear_state(self) -> None:
        buffered_bytes = self._pcm.buffered_bytes
        self._pcm.clear()
        self._process_pcm.release(buffered_bytes)
        self._output.clear()
        self._lease.clear()

    def _session_teardown(self) -> None:
        self._clear_state()
        self._allow_cancel_replay = False
        if self._terminal_code is None:
            self._terminal_code = StableCode.LEASE_CLOSED

    def _expire_if_due(self, now: datetime) -> Decision | None:
        if self._terminal_code is not None:
            return Decision(self._terminal_code)
        if now < self.expires_at:
            return None
        self._clear_state()
        self._cancellations.expire_active(self.lease_id)
        self._terminal_code = StableCode.LEASE_EXPIRED
        return Decision(StableCode.LEASE_EXPIRED)

    def accept_pcm(
        self,
        frame: bytes | bytearray | memoryview,
        *,
        now: datetime,
    ) -> Decision:
        terminal = self._expire_if_due(now)
        if terminal is not None:
            return terminal
        before = self._pcm.buffered_bytes
        decision = self._pcm.accept(
            frame,
            process_buffered_bytes=self._process_pcm.buffered_bytes,
        )
        if decision.code == StableCode.ACCEPTED:
            self._process_pcm.add(self._pcm.buffered_bytes - before)
        return decision

    def consume_pcm(self, byte_count: int) -> None:
        self._pcm.consume(byte_count)
        self._process_pcm.release(byte_count)

    def accept_output(self, message: Mapping[str, Any], *, now: datetime) -> Decision:
        terminal = self._expire_if_due(now)
        if terminal is not None:
            return terminal
        return self._output.accept(message)

    def accept_lease_update(
        self,
        message: LeaseV1,
        *,
        now: datetime,
    ) -> Decision:
        terminal = self._expire_if_due(now)
        if terminal is not None:
            return terminal
        decision = self._lease.accept(message.model_dump(mode="json"))
        if decision.code == StableCode.ACCEPTED:
            self._cancellations.update_active_revision(self.lease_id, int(message.revision))
        return decision

    def cancel(self, message: LeaseCancelV1, raw: Mapping[str, Any], now: datetime) -> Decision:
        terminal = self._expire_if_due(now)
        if terminal is not None and (
            terminal.code == StableCode.LEASE_EXPIRED or not self._allow_cancel_replay
        ):
            return terminal
        decision = self._cancellations.cancel(message, raw, now)
        if decision.code == StableCode.ACCEPTED:
            self._clear_state()
            self._terminal_code = StableCode.LEASE_CLOSED
            self._allow_cancel_replay = True
        return decision


_PROCESS_RUNTIMES: dict[str, set[LeaseRuntimeState]] = {}
