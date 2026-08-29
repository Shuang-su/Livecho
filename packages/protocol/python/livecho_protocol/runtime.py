"""Composable lease-local state proving terminal cancellation behavior."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .binary import PcmLeaseState
from .errors import Decision, StableCode
from .models import LeaseCancelV1
from .state import ActiveLease, CancellationRegistry, StreamOrderingState


class LeaseRuntimeState:
    """Pure in-memory protocol state for one synthetic lease, without scheduling."""

    def __init__(
        self,
        *,
        lease_id: str,
        session_id: str,
        epoch: int,
        revision: int,
        input_start_seq: int,
        output_start_seq: int,
    ) -> None:
        self.lease_id = lease_id
        self.session_id = session_id
        self.cancellations = CancellationRegistry()
        self.cancellations.add_active(ActiveLease(lease_id, session_id, epoch, revision))
        self.pcm = PcmLeaseState(
            lease_id=lease_id,
            epoch=epoch,
            input_start_seq=input_start_seq,
        )
        self.output = StreamOrderingState(
            session_id=session_id,
            lease_id=lease_id,
            epoch=epoch,
            start_seq=output_start_seq,
        )

    def cancel(self, message: LeaseCancelV1, raw: Mapping[str, Any], now: datetime) -> Decision:
        decision = self.cancellations.cancel(message, raw, now)
        if decision.code == StableCode.ACCEPTED:
            self.pcm.clear()
            self.output.clear()
        return decision
