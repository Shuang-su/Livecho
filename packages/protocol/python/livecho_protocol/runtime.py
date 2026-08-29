"""Composable lease-local state proving terminal expiry and cancellation behavior."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .binary import PcmLeaseState
from .errors import Decision, StableCode
from .models import LeaseCancelV1, LeaseV1
from .scalars import parse_timestamp
from .state import ActiveLease, CancellationRegistry, LeaseRevisionState, StreamOrderingState


class LeaseRuntimeState:
    """Pure in-memory protocol state for one synthetic lease, without scheduling."""

    def __init__(
        self,
        *,
        lease: LeaseV1,
    ) -> None:
        self.lease_id = lease.lease_id
        self.session_id = lease.session_id
        self.epoch = int(lease.epoch)
        self.expires_at = parse_timestamp(lease.expires_at)
        self._terminal_code: StableCode | None = None
        self.cancellations = CancellationRegistry()
        self.cancellations.add_active(
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

    def _expire_if_due(self, now: datetime) -> Decision | None:
        if self._terminal_code is not None:
            return Decision(self._terminal_code)
        if now < self.expires_at:
            return None
        self._pcm.clear()
        self._output.clear()
        self._lease.clear()
        self.cancellations.expire_active(self.lease_id)
        self._terminal_code = StableCode.LEASE_EXPIRED
        return Decision(StableCode.LEASE_EXPIRED)

    def accept_pcm(
        self,
        frame: bytes | bytearray | memoryview,
        *,
        now: datetime,
        process_buffered_bytes: int = 0,
    ) -> Decision:
        terminal = self._expire_if_due(now)
        if terminal is not None:
            return terminal
        return self._pcm.accept(frame, process_buffered_bytes=process_buffered_bytes)

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
            self.cancellations.update_active_revision(self.lease_id, int(message.revision))
        return decision

    def cancel(self, message: LeaseCancelV1, raw: Mapping[str, Any], now: datetime) -> Decision:
        terminal = self._expire_if_due(now)
        if terminal is not None and terminal.code == StableCode.LEASE_EXPIRED:
            return terminal
        decision = self.cancellations.cancel(message, raw, now)
        if decision.code == StableCode.ACCEPTED:
            self._pcm.clear()
            self._output.clear()
            self._lease.clear()
            self._terminal_code = StableCode.LEASE_CLOSED
        return decision
