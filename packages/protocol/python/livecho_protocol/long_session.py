"""Minor-1 long-session rotation. Minor 0 keeps the unchanged revision domain."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from .binary import PcmHeaderV1
from .errors import Decision, ProtocolValidationError, StableCode
from .models import (
    EpochRotatedV1,
    HeartbeatV1,
    HeartbeatV1Minor1,
    LeaseV1,
    LeaseV1Minor1,
    TimelineEventV1,
    TimelineEventV1Minor1,
    TranscriptSegmentV1,
    TranscriptSegmentV1Minor1,
    TranscriptTimelinePayloadV1,
    ViewerCursorV1,
    ViewerResyncV1,
    WorkerStatsV1,
    WorkerStatsV1Minor1,
)
from .parser import canonical_digest
from .runtime import LeaseRuntimeCoordinator, LeaseRuntimeState
from .scalars import UINT64_MAX, ZERO_LEASE_ID, parse_timestamp
from .state import (
    REVISION_DOMAIN_CAPACITY,
    RevisionDomain,
    RevisionIdentity,
    StreamOrderingState,
)

ROTATION_TOMBSTONE_CAPACITY = 8
SESSION_REVISION_CEILING = REVISION_DOMAIN_CAPACITY * 2 + 1
DomainName = Literal["worker", "viewer"]
RotationReason = Literal["revision_capacity", "lease_replaced"]
type WorkerOutput = (
    HeartbeatV1
    | HeartbeatV1Minor1
    | WorkerStatsV1
    | WorkerStatsV1Minor1
    | TranscriptSegmentV1
    | TranscriptSegmentV1Minor1
)


@dataclass(frozen=True, slots=True)
class RotationTombstone:
    closed_epoch: int
    input_next_seq: int
    output_next_seq: int
    viewer_next_seq: int
    media_continue_ms: int
    pcm_continue_pts: int
    reason: RotationReason


@dataclass(frozen=True, slots=True)
class ViewerResync:
    epoch: int
    next_seq: int
    media_continue_ms: int
    reason: Literal["epoch_rotated", "cursor_expired", "cursor_unknown"]
    gap: bool = True


@dataclass(frozen=True, slots=True)
class SessionRotation:
    """Validated notices from one committed rotation."""

    worker: EpochRotatedV1
    viewer: ViewerResyncV1


@dataclass(frozen=True, slots=True)
class SessionUpdate:
    decision: Decision
    rotation: SessionRotation | None = None


class Minor1Session:
    """One session, two revision domains, and a bounded rotation tombstone ring."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.epoch = 1
        self.worker = RevisionDomain()
        self.viewer = RevisionDomain()
        self.lease_open = False
        self.media_continue_ms = 0
        self.epoch_media_floor_ms = 0
        self.pcm_continue_pts = 0
        self.input_next_seq = 1
        self.output_next_seq = 1
        self.viewer_next_seq = 1
        self.tombstones: list[RotationTombstone] = []

    @property
    def revision_record_count(self) -> int:
        lease_records = 1 if self.lease_open else 0
        return self.worker.size + self.viewer.size + lease_records

    def open_lease(self, *, input_start_seq: int = 1, output_start_seq: int = 1) -> Decision:
        if input_start_seq != 1 or output_start_seq != 1:
            return Decision(StableCode.SCHEMA_INVALID)
        self.lease_open = True
        self.input_next_seq = input_start_seq
        self.output_next_seq = output_start_seq
        return Decision(StableCode.ACCEPTED)

    def note_pcm(self, pts_ms: int, sample_count: int) -> Decision:
        if pts_ms < self.pcm_continue_pts:
            return Decision(StableCode.AUDIO_PTS_INVALID)
        self.pcm_continue_pts = pts_ms + (sample_count * 1000 // 16000)
        return Decision(StableCode.ACCEPTED)

    def admit(
        self,
        domain: DomainName,
        object_id: str,
        *,
        revision: int = 1,
        is_final: bool = False,
        start_ms: int = 0,
        end_ms: int = 1,
        projection: bytes | None = None,
        immutable: bytes | None = None,
    ) -> Decision:
        identity = self._identity(domain, object_id)
        target = self.worker if domain == "worker" else self.viewer
        if target.record(identity) is None and start_ms < self.epoch_media_floor_ms:
            return Decision(StableCode.MEDIA_TIME_REGRESSED)
        body = projection if projection is not None else _digest(object_id, revision, is_final)
        frozen = immutable if immutable is not None else _digest(object_id, start_ms, end_ms)
        preview = target.preview(identity, revision, body, frozen, is_final)
        if preview.decision.code == StableCode.REVISION_CAPACITY_EXCEEDED:
            return self._rotate("revision_capacity")
        if preview.decision.code == StableCode.ACCEPTED:
            target.commit(identity, preview)
            if is_final:
                self.media_continue_ms = max(self.media_continue_ms, end_ms)
        return preview.decision

    def replace_lease(self) -> Decision:
        return self._rotate("lease_replaced")

    def epoch_decision(self, epoch: int) -> Decision:
        if epoch == self.epoch:
            return Decision(StableCode.ACCEPTED)
        if any(item.closed_epoch == epoch for item in self.tombstones):
            return Decision(StableCode.EPOCH_STALE)
        return Decision(StableCode.EPOCH_UNKNOWN)

    def viewer_cursor(
        self, session_id: str, epoch: int, next_seq: int
    ) -> tuple[Decision, ViewerResync | None]:
        if session_id != self.session_id:
            return Decision(StableCode.BINDING_MISMATCH), None
        if epoch == self.epoch and next_seq == self.viewer_next_seq:
            return Decision(StableCode.ACCEPTED), None
        current = ViewerResync(
            epoch=self.epoch,
            next_seq=self.viewer_next_seq,
            media_continue_ms=self.media_continue_ms,
            reason="cursor_expired",
        )
        if epoch == self.epoch:
            return Decision(StableCode.RESYNC_REQUIRED), current
        if any(item.closed_epoch == epoch for item in self.tombstones):
            return Decision(StableCode.RESYNC_REQUIRED), ViewerResync(
                epoch=self.epoch,
                next_seq=self.viewer_next_seq,
                media_continue_ms=self.media_continue_ms,
                reason="epoch_rotated",
            )
        return Decision(StableCode.RESYNC_REQUIRED), ViewerResync(
            epoch=self.epoch,
            next_seq=self.viewer_next_seq,
            media_continue_ms=self.media_continue_ms,
            reason="cursor_unknown",
        )

    def _identity(self, domain: DomainName, object_id: str) -> RevisionIdentity:
        lease = (
            "00000000-0000-4000-8000-000000000020"
            if domain == "worker"
            else ("00000000-0000-0000-0000-000000000000")
        )
        kind = "worker.transcript" if domain == "worker" else "viewer.timeline_event"
        return (kind, self.session_id, lease, self.epoch, object_id)

    def _rotate(self, reason: RotationReason) -> Decision:
        if self.epoch == UINT64_MAX:
            return Decision(StableCode.EPOCH_EXHAUSTED)
        tombstone = RotationTombstone(
            closed_epoch=self.epoch,
            input_next_seq=self.input_next_seq,
            output_next_seq=self.output_next_seq,
            viewer_next_seq=self.viewer_next_seq,
            media_continue_ms=self.media_continue_ms,
            pcm_continue_pts=self.pcm_continue_pts,
            reason=reason,
        )
        next_tombstones = [*self.tombstones[1 - ROTATION_TOMBSTONE_CAPACITY :], tombstone]
        worker, viewer = RevisionDomain(), RevisionDomain()
        self.tombstones = next_tombstones
        self.epoch += 1
        self.worker, self.viewer = worker, viewer
        self.lease_open = False
        self.epoch_media_floor_ms = self.media_continue_ms
        self.input_next_seq = 1
        self.output_next_seq = 1
        self.viewer_next_seq = 1
        return Decision(StableCode.EPOCH_ROTATED)


class Minor1SessionRuntime:
    """Protocol runtime for a single minor-1 session owned by one backend loop."""

    def __init__(
        self,
        session_id: str,
        room_id: str,
        *,
        leases: LeaseRuntimeCoordinator,
    ) -> None:
        self._session = Minor1Session(session_id)
        self._room_id = room_id
        self._leases = leases
        self._lease: LeaseRuntimeState | None = None
        self._last_lease_id: str | None = None
        self._viewer = self._open_viewer_domain()
        self._closed = False

    @property
    def epoch(self) -> int:
        return self._session.epoch

    @property
    def viewer_next_seq(self) -> int:
        return self._session.viewer_next_seq

    @property
    def revision_record_count(self) -> int:
        return self._session.revision_record_count

    def install_lease(self, lease: LeaseV1 | LeaseV1Minor1, *, now: datetime) -> Decision:
        if lease.protocol_minor != 1:
            return Decision(StableCode.UNSUPPORTED_MINOR)
        if lease.room_id != self._room_id:
            return Decision(StableCode.BINDING_MISMATCH)
        bound = self._check_epoch(lease.session_id, int(lease.epoch))
        if not bound.accepted:
            return bound
        if self._lease is not None:
            return Decision(StableCode.RESYNC_REQUIRED)
        if lease.lease_id == self._last_lease_id:
            return Decision(StableCode.BINDING_MISMATCH)
        if (lease.revision, lease.input_start_seq, lease.output_start_seq) != ("1", "1", "1"):
            return Decision(StableCode.SCHEMA_INVALID)
        if parse_timestamp(lease.expires_at) <= now:
            return Decision(StableCode.LEASE_EXPIRED)
        try:
            self._lease = self._leases.create(
                lease,
                output_revisions=self._session.worker,
                media_floor_ms=self._session.epoch_media_floor_ms,
                pcm_floor_ms=self._session.pcm_continue_pts,
            )
        except ProtocolValidationError as error:
            return Decision(error.code)
        self._last_lease_id = lease.lease_id
        return self._session.open_lease()

    def accept_worker(self, message: WorkerOutput, *, now: datetime) -> SessionUpdate:
        if message.protocol_minor != 1:
            return SessionUpdate(Decision(StableCode.UNSUPPORTED_MINOR))
        bound = self._check_epoch(message.session_id, int(message.epoch))
        if not bound.accepted:
            return SessionUpdate(bound)
        if self._lease is None:
            return SessionUpdate(Decision(StableCode.LEASE_UNKNOWN))
        decision = self._lease.accept_output(message.model_dump(mode="json"), now=now)
        self._session.output_next_seq = self._lease.output_next_expected_seq
        if decision.code == StableCode.LEASE_EXPIRED:
            self._session.lease_open = False
        if (
            decision.code == StableCode.ACCEPTED
            and isinstance(message, TranscriptSegmentV1)
            and message.is_final
        ):
            self._note_final(message.end_ms)
        return self._complete_admission(decision, now)

    def accept_pcm_header(self, header: PcmHeaderV1, *, now: datetime) -> Decision:
        if header.protocol_minor != 1:
            return Decision(StableCode.BINARY_HEADER_INVALID)
        bound = self._check_epoch(self._session.session_id, header.epoch)
        if not bound.accepted:
            return bound
        if self._lease is None:
            return Decision(StableCode.LEASE_UNKNOWN)
        decision = self._lease.accept_pcm_header(header, now=now)
        if decision.code == StableCode.ACCEPTED:
            self._session.pcm_continue_pts = self._lease.pcm_continue_pts
            self._session.input_next_seq = self._lease.input_next_expected_seq
        if decision.code == StableCode.LEASE_EXPIRED:
            self._session.lease_open = False
        return decision

    def consume_pcm(self, byte_count: int) -> None:
        if self._lease is None:
            raise ProtocolValidationError(StableCode.LEASE_UNKNOWN)
        self._lease.consume_pcm(byte_count)

    def accept_viewer_event(
        self, event: TimelineEventV1 | TimelineEventV1Minor1, *, now: datetime
    ) -> SessionUpdate:
        if event.protocol_minor != 1:
            return SessionUpdate(Decision(StableCode.UNSUPPORTED_MINOR))
        if event.room_id != self._room_id:
            return SessionUpdate(Decision(StableCode.BINDING_MISMATCH))
        bound = self._check_epoch(event.session_id, int(event.epoch))
        if not bound.accepted:
            return SessionUpdate(bound)
        decision = self._viewer.accept(event.model_dump(mode="json"))
        self._session.viewer_next_seq = self._viewer.sequence.next_expected_seq
        if (
            decision.code == StableCode.ACCEPTED
            and isinstance(event.payload, TranscriptTimelinePayloadV1)
            and event.payload.is_final
        ):
            self._note_final(event.payload.end_ms)
        return self._complete_admission(decision, now)

    def viewer_cursor(
        self, cursor: ViewerCursorV1, *, now: datetime
    ) -> tuple[Decision, ViewerResyncV1 | None]:
        if self._closed:
            return Decision(StableCode.BINDING_MISMATCH), None
        decision, target = self._session.viewer_cursor(
            cursor.session_id, int(cursor.epoch), int(cursor.next_seq)
        )
        return decision, self._resync(target, now) if target is not None else None

    def replace_lease(self, *, now: datetime) -> SessionUpdate:
        """Apply an authorized same-session replacement. The caller chooses the worker."""
        return self._rotate("lease_replaced", now)

    def close(self) -> None:
        if self._closed:
            return
        self._leases.session_teardown(self._session.session_id)
        self._session.tombstones.clear()
        self._session.lease_open = False
        self._lease = None
        self._viewer.clear()
        self._closed = True

    def _check_epoch(self, session_id: str, epoch: int) -> Decision:
        if self._closed or session_id != self._session.session_id:
            return Decision(StableCode.BINDING_MISMATCH)
        return self._session.epoch_decision(epoch)

    def _open_viewer_domain(self) -> StreamOrderingState:
        return StreamOrderingState(
            session_id=self._session.session_id,
            lease_id=None,
            epoch=self.epoch,
            start_seq=1,
            revisions=self._session.viewer,
            media_floor_ms=self._session.epoch_media_floor_ms,
        )

    def _note_final(self, end_ms: int) -> None:
        self._session.media_continue_ms = max(self._session.media_continue_ms, end_ms)

    def _complete_admission(self, decision: Decision, now: datetime) -> SessionUpdate:
        if decision.code == StableCode.REVISION_CAPACITY_EXCEEDED:
            return self._rotate("revision_capacity", now)
        return SessionUpdate(decision)

    def _rotate(self, reason: RotationReason, now: datetime) -> SessionUpdate:
        if self._closed:
            return SessionUpdate(Decision(StableCode.BINDING_MISMATCH))
        if self.epoch == UINT64_MAX:
            return SessionUpdate(Decision(StableCode.EPOCH_EXHAUSTED))
        lease = self._lease
        lease_id = (
            lease.lease_id
            if lease is not None and lease.cancellation_active and now < lease.expires_at
            else ZERO_LEASE_ID
        )
        opened_epoch = self.epoch + 1
        # Build both messages before committing. No I/O runs inside the transition.
        worker = EpochRotatedV1(
            protocol="livecho.worker.v1",
            protocol_minor=1,
            type="worker.epoch_rotated",
            message_id=str(uuid4()),
            sent_at=_sent_at(now),
            session_id=self._session.session_id,
            lease_id=lease_id,
            closed_epoch=str(self.epoch),
            opened_epoch=str(opened_epoch),
            media_continue_ms=self._session.media_continue_ms,
            pcm_continue_pts=str(self._session.pcm_continue_pts),
            reason=reason,
        )
        viewer = self._resync(
            ViewerResync(opened_epoch, 1, self._session.media_continue_ms, "epoch_rotated"),
            now,
        )
        if lease is not None:
            self._leases.retire(lease)
        self._viewer.clear()
        decision = self._session._rotate(reason)
        self._lease = None
        self._viewer = self._open_viewer_domain()
        if reason == "lease_replaced":
            # A backend replacement is a successful transition, not a rejected frame.
            decision = Decision(StableCode.ACCEPTED)
        return SessionUpdate(decision, SessionRotation(worker, viewer))

    def _resync(self, target: ViewerResync, now: datetime) -> ViewerResyncV1:
        return ViewerResyncV1(
            protocol="livecho.viewer.v1",
            protocol_minor=1,
            type="viewer.resync",
            message_id=str(uuid4()),
            sent_at=_sent_at(now),
            session_id=self._session.session_id,
            room_id=self._room_id,
            epoch=str(target.epoch),
            next_seq=str(target.next_seq),
            media_continue_ms=target.media_continue_ms,
            reason=target.reason,
            gap=True,
        )


def _sent_at(now: datetime) -> str:
    return now.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _digest(*parts: object) -> bytes:
    return canonical_digest({"parts": [str(part) for part in parts]})
