"""Composable lease-local state proving terminal expiry and cancellation behavior."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .binary import LEASE_AUDIO_BUDGET, PROCESS_AUDIO_BUDGET, PcmLeaseState
from .compatibility import manifest_key
from .errors import Decision, ProtocolValidationError, StableCode
from .models import LeaseCancelV1, LeaseV1
from .scalars import parse_timestamp
from .state import ActiveLease, CancellationRegistry, LeaseRevisionState, StreamOrderingState

_PROCESS_CANCELLATIONS = CancellationRegistry()


class _ProcessPcmBudget:
    """Process-wide logical count for ephemeral PCM bytes currently awaiting consumption."""

    def __init__(self) -> None:
        self.buffered_bytes = 0
        self._session_bytes: dict[str, int] = {}

    def session_bytes(self, session_id: str) -> int:
        return self._session_bytes.get(session_id, 0)

    def add(self, session_id: str, byte_count: int) -> None:
        session_bytes = self.session_bytes(session_id)
        if (
            byte_count < 0
            or session_bytes + byte_count > LEASE_AUDIO_BUDGET
            or self.buffered_bytes + byte_count > PROCESS_AUDIO_BUDGET
        ):
            raise RuntimeError("invalid process PCM budget increase")
        self.buffered_bytes += byte_count
        self._session_bytes[session_id] = session_bytes + byte_count

    def release(self, session_id: str, byte_count: int) -> None:
        session_bytes = self.session_bytes(session_id)
        if byte_count < 0 or byte_count > session_bytes or byte_count > self.buffered_bytes:
            raise RuntimeError("invalid process PCM budget release")
        self.buffered_bytes -= byte_count
        remaining = session_bytes - byte_count
        if remaining == 0:
            self._session_bytes.pop(session_id, None)
        else:
            self._session_bytes[session_id] = remaining


_PROCESS_PCM_BUDGET = _ProcessPcmBudget()


class LeaseRuntimeCoordinator:
    """Process-scoped owner for lease runtimes and bounded cancellation tombstones."""

    def __init__(
        self,
        *,
        accepted_manifests: frozenset[tuple[str, str, str, str]],
    ) -> None:
        self._accepted_manifests = accepted_manifests
        self._cancellations = _PROCESS_CANCELLATIONS
        self._runtimes = _PROCESS_RUNTIMES
        self._session_epochs = _PROCESS_SESSION_EPOCHS
        self._process_pcm = _PROCESS_PCM_BUDGET

    @property
    def tombstone_count(self) -> int:
        return len(self._cancellations.tombstones)

    @property
    def active_lease_count(self) -> int:
        return len(self._cancellations.active)

    @property
    def buffered_audio_bytes(self) -> int:
        return self._process_pcm.buffered_bytes

    def session_buffered_audio_bytes(self, session_id: str) -> int:
        return self._process_pcm.session_bytes(session_id)

    def create(self, lease: LeaseV1) -> LeaseRuntimeState:
        if manifest_key(lease.model_manifest) not in self._accepted_manifests:
            raise ProtocolValidationError(StableCode.MANIFEST_NOT_ALLOWED)
        replacement_epoch = int(lease.epoch)
        current_epoch = self._session_epochs.get(lease.session_id)
        if current_epoch is not None and replacement_epoch < current_epoch:
            raise ProtocolValidationError(StableCode.EPOCH_STALE)
        if current_epoch == replacement_epoch:
            raise ProtocolValidationError(StableCode.RESYNC_REQUIRED)
        runtime = LeaseRuntimeState(
            lease=lease,
            cancellations=self._cancellations,
            process_pcm=self._process_pcm,
        )
        session_runtimes = self._runtimes.setdefault(lease.session_id, set())
        for previous in tuple(session_runtimes):
            if previous.epoch < replacement_epoch:
                previous._session_teardown()
                session_runtimes.remove(previous)
        runtime._activate()
        self._session_epochs[lease.session_id] = replacement_epoch
        session_runtimes.add(runtime)
        return runtime

    def prune(self, now: datetime) -> None:
        self._cancellations.prune(now)
        for session_id, runtimes in tuple(self._runtimes.items()):
            for runtime in tuple(runtimes):
                if runtime._expire_if_due(now) is not None:
                    runtimes.remove(runtime)
            if not runtimes:
                del self._runtimes[session_id]

    def session_teardown(self, session_id: str) -> None:
        for runtime in self._runtimes.pop(session_id, set()):
            runtime._session_teardown()
        self._session_epochs.pop(session_id, None)
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
        self._activated = False
        self._cancellations = cancellations
        self._process_pcm = process_pcm
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
            raise ProtocolValidationError(initial.code)

    def _activate(self) -> None:
        if self._activated:
            raise RuntimeError("lease runtime is already active")
        self._cancellations.add_active(
            ActiveLease(self.lease_id, self.session_id, self.epoch, self.lease_revision)
        )
        self._activated = True

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
        self._process_pcm.release(self.session_id, buffered_bytes)
        self._output.clear()
        self._lease.clear()

    def _session_teardown(self) -> None:
        self._clear_state()
        self._cancellations.expire_active(self.lease_id)
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
            session_buffered_bytes=self._process_pcm.session_bytes(self.session_id),
            process_buffered_bytes=self._process_pcm.buffered_bytes,
        )
        if decision.code == StableCode.ACCEPTED:
            buffered_delta = self._pcm.buffered_bytes - before
            if buffered_delta > 0:
                self._process_pcm.add(self.session_id, buffered_delta)
            elif buffered_delta < 0:
                self._process_pcm.release(self.session_id, -buffered_delta)
        return decision

    def consume_pcm(self, byte_count: int) -> None:
        self._pcm.consume(byte_count)
        self._process_pcm.release(self.session_id, byte_count)

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
        if self._allow_cancel_replay and self._cancellations.has_tombstone_message(
            self.lease_id, message.message_id, now
        ):
            return self._cancellations.cancel(message, raw, now)
        if message.lease_id != self.lease_id or message.session_id != self.session_id:
            return Decision(StableCode.BINDING_MISMATCH)
        received_epoch = int(message.epoch)
        if received_epoch < self.epoch:
            return Decision(StableCode.EPOCH_STALE)
        if received_epoch > self.epoch:
            return Decision(StableCode.EPOCH_UNKNOWN)
        decision = self._cancellations.cancel(message, raw, now)
        if (
            self._terminal_code == StableCode.LEASE_CLOSED
            and decision.code == StableCode.LEASE_UNKNOWN
        ):
            return Decision(StableCode.LEASE_CLOSED)
        if decision.code == StableCode.ACCEPTED:
            self._clear_state()
            self._terminal_code = StableCode.LEASE_CLOSED
            self._allow_cancel_replay = True
        return decision


_PROCESS_RUNTIMES: dict[str, set[LeaseRuntimeState]] = {}
_PROCESS_SESSION_EPOCHS: dict[str, int] = {}
