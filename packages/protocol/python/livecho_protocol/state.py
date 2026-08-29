"""Pure, bounded in-memory protocol ordering and reconnect state machines."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .errors import Decision, StableCode
from .models import LeaseCancelV1, ViewerCursorV1, WorkerResumeV1
from .parser import canonical_digest
from .scalars import UINT64_MAX, parse_timestamp

SEQUENCE_WINDOW_CAPACITY = 256
REVISION_DOMAIN_CAPACITY = 4_096
CANCELLATION_TOMBSTONE_CAPACITY = 64
CANCELLATION_TOMBSTONE_TTL = timedelta(seconds=120)
ZERO_UUID = "00000000-0000-0000-0000-000000000000"


@dataclass(frozen=True, slots=True)
class SequenceRecord:
    message_id: str
    digest: bytes


class JsonSequenceWindow:
    """Exact-next JSON sequence state with a fixed 256-record FIFO."""

    def __init__(self, start_seq: int) -> None:
        self.start_seq = start_seq
        self.next_expected_seq = start_seq
        self._records: OrderedDict[int, SequenceRecord] = OrderedDict()

    @property
    def retained_sequences(self) -> tuple[int, ...]:
        return tuple(self._records)

    def preview(self, seq: int, message_id: str, digest: bytes) -> Decision:
        if seq < self.next_expected_seq:
            record = self._records.get(seq)
            if record is None:
                return Decision(StableCode.RESYNC_REQUIRED)
            if record.message_id == message_id and record.digest == digest:
                return Decision(StableCode.SEQ_DUPLICATE)
            return Decision(StableCode.SEQ_CONFLICT)
        if seq > self.next_expected_seq:
            return Decision(StableCode.SEQ_GAP)
        if seq == UINT64_MAX:
            return Decision(StableCode.RESYNC_REQUIRED)
        return Decision(StableCode.ACCEPTED)

    def commit(self, seq: int, message_id: str, digest: bytes) -> None:
        if seq != self.next_expected_seq:
            raise ValueError("only the exact next sequence can be committed")
        if seq == UINT64_MAX:
            raise ValueError("sequence space is exhausted")
        self._records[seq] = SequenceRecord(message_id=message_id, digest=digest)
        self.next_expected_seq += 1
        while len(self._records) > SEQUENCE_WINDOW_CAPACITY:
            self._records.popitem(last=False)

    def clear(self) -> None:
        self._records.clear()


class PcmSequenceWindow:
    """Record-free PCM replay arithmetic."""

    def __init__(self, start_seq: int) -> None:
        self.start_seq = start_seq
        self.next_expected_seq = start_seq

    @property
    def oldest_replayable_seq(self) -> int:
        return max(self.start_seq, self.next_expected_seq - SEQUENCE_WINDOW_CAPACITY)

    def preview(self, seq: int) -> Decision:
        if seq < self.oldest_replayable_seq:
            return Decision(StableCode.RESYNC_REQUIRED)
        if seq < self.next_expected_seq:
            return Decision(StableCode.SEQ_DUPLICATE)
        if seq > self.next_expected_seq:
            return Decision(StableCode.SEQ_GAP)
        if seq == UINT64_MAX:
            return Decision(StableCode.RESYNC_REQUIRED)
        return Decision(StableCode.ACCEPTED)

    def commit(self, seq: int) -> None:
        if seq != self.next_expected_seq:
            raise ValueError("only the exact next PCM sequence can be committed")
        if seq == UINT64_MAX:
            raise ValueError("PCM sequence space is exhausted")
        self.next_expected_seq += 1

    def clear(self) -> None:
        self.next_expected_seq = self.start_seq


type RevisionIdentity = tuple[str, str, str, int, str]


@dataclass(frozen=True, slots=True)
class RevisionRecord:
    current_revision: int
    projection_digest: bytes
    immutable_digest: bytes
    is_final: bool


@dataclass(frozen=True, slots=True)
class RevisionPreview:
    decision: Decision
    record: RevisionRecord | None = None


class RevisionDomain:
    """No-eviction revision records with an exact identity ceiling."""

    def __init__(self, capacity: int = REVISION_DOMAIN_CAPACITY) -> None:
        if capacity < 1 or capacity > REVISION_DOMAIN_CAPACITY:
            raise ValueError("invalid revision capacity")
        self.capacity = capacity
        self._records: dict[RevisionIdentity, RevisionRecord] = {}

    @property
    def size(self) -> int:
        return len(self._records)

    def record(self, identity: RevisionIdentity) -> RevisionRecord | None:
        return self._records.get(identity)

    def preview(
        self,
        identity: RevisionIdentity,
        revision: int,
        projection_digest: bytes,
        immutable_digest: bytes,
        is_final: bool,
    ) -> RevisionPreview:
        existing = self._records.get(identity)
        if existing is None:
            if len(self._records) >= self.capacity:
                return RevisionPreview(Decision(StableCode.REVISION_CAPACITY_EXCEEDED))
            if revision != 1:
                return RevisionPreview(Decision(StableCode.REVISION_GAP))
            return RevisionPreview(
                Decision(StableCode.ACCEPTED),
                RevisionRecord(revision, projection_digest, immutable_digest, is_final),
            )
        if revision < existing.current_revision:
            return RevisionPreview(Decision(StableCode.REVISION_STALE))
        if (
            revision == existing.current_revision
            and projection_digest == existing.projection_digest
        ):
            return RevisionPreview(Decision(StableCode.REVISION_DUPLICATE))
        if existing.is_final:
            return RevisionPreview(Decision(StableCode.OBJECT_FINAL))
        if revision == existing.current_revision:
            return RevisionPreview(Decision(StableCode.REVISION_CONFLICT))
        if revision > existing.current_revision + 1:
            return RevisionPreview(Decision(StableCode.REVISION_GAP))
        if immutable_digest != existing.immutable_digest:
            return RevisionPreview(Decision(StableCode.REVISION_IMMUTABLE))
        return RevisionPreview(
            Decision(StableCode.ACCEPTED),
            RevisionRecord(revision, projection_digest, immutable_digest, is_final),
        )

    def commit(self, identity: RevisionIdentity, preview: RevisionPreview) -> None:
        if preview.decision.code != StableCode.ACCEPTED or preview.record is None:
            raise ValueError("only accepted revisions can be committed")
        self._records[identity] = preview.record

    def clear(self) -> None:
        self._records.clear()


def revision_projection(message: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in message.items() if key not in {"message_id", "sent_at", "seq"}
    }


def immutable_projection(message: Mapping[str, Any]) -> dict[str, Any]:
    message_type = message.get("type")
    fields_by_type = {
        "worker.lease": (
            "type",
            "session_id",
            "lease_id",
            "room_id",
            "epoch",
            "issued_at",
            "expires_at",
            "input_start_seq",
            "output_start_seq",
            "model_manifest",
            "audio_format",
            "audio_origin",
        ),
        "worker.stats": (
            "type",
            "session_id",
            "lease_id",
            "stats_id",
            "epoch",
            "window_started_at",
            "window_ended_at",
        ),
        "worker.transcript": (
            "type",
            "session_id",
            "lease_id",
            "segment_id",
            "epoch",
            "start_ms",
            "end_ms",
        ),
    }
    if message_type in fields_by_type:
        return {field: message[field] for field in fields_by_type[message_type]}
    if message_type == "viewer.timeline_event":
        payload = message["payload"]
        if not isinstance(payload, Mapping):
            raise ValueError("timeline payload must be a mapping")
        projection = {
            field: message[field]
            for field in ("type", "session_id", "room_id", "event_id", "epoch", "occurred_at")
        }
        if "segment_id" in payload:
            projection.update(
                {
                    "payload_kind": "transcript",
                    "segment_id": payload["segment_id"],
                    "start_ms": payload["start_ms"],
                    "end_ms": payload["end_ms"],
                }
            )
        else:
            projection["payload_kind"] = "session_status"
        return projection
    raise ValueError("message type has no revision projection")


def revision_identity(message: Mapping[str, Any]) -> RevisionIdentity:
    message_type = str(message["type"])
    session_id = str(message["session_id"])
    lease_id = str(message.get("lease_id", ZERO_UUID))
    epoch = int(str(message["epoch"]))
    object_field = {
        "worker.lease": "lease_id",
        "worker.stats": "stats_id",
        "worker.transcript": "segment_id",
        "viewer.timeline_event": "event_id",
    }.get(message_type)
    if object_field is None:
        raise ValueError("message type has no revision identity")
    return message_type, session_id, lease_id, epoch, str(message[object_field])


def message_is_final(message: Mapping[str, Any]) -> bool:
    if message.get("type") == "worker.transcript":
        return bool(message["is_final"])
    if message.get("type") == "viewer.timeline_event":
        payload = message["payload"]
        return isinstance(payload, Mapping) and bool(payload.get("is_final", False))
    return False


class LeaseRevisionState:
    """Non-sequenced revision state for backend-issued lease messages."""

    def __init__(self, *, session_id: str, lease_id: str, epoch: int) -> None:
        self.session_id = session_id
        self.lease_id = lease_id
        self.epoch = epoch
        self.revisions = RevisionDomain(capacity=1)
        self.closed = False

    def accept(self, message: Mapping[str, Any]) -> Decision:
        if self.closed:
            return Decision(StableCode.LEASE_CLOSED)
        if message.get("session_id") != self.session_id or message.get("lease_id") != self.lease_id:
            return Decision(StableCode.BINDING_MISMATCH)
        received_epoch = int(str(message["epoch"]))
        if received_epoch < self.epoch:
            return Decision(StableCode.EPOCH_STALE)
        if received_epoch > self.epoch:
            return Decision(StableCode.EPOCH_UNKNOWN)
        identity = revision_identity(message)
        preview = self.revisions.preview(
            identity,
            int(str(message["revision"])),
            canonical_digest(revision_projection(message)),
            canonical_digest(immutable_projection(message)),
            False,
        )
        if preview.decision.code == StableCode.ACCEPTED:
            self.revisions.commit(identity, preview)
        return preview.decision

    def clear(self) -> None:
        self.revisions.clear()
        self.closed = True


class StreamOrderingState:
    """Sequence-before-revision precedence for one admitted stream domain."""

    def __init__(
        self,
        *,
        session_id: str,
        lease_id: str | None,
        epoch: int,
        start_seq: int,
        revision_capacity: int = REVISION_DOMAIN_CAPACITY,
    ) -> None:
        self.session_id = session_id
        self.lease_id = lease_id
        self.epoch = epoch
        self.sequence = JsonSequenceWindow(start_seq)
        self.revisions = RevisionDomain(revision_capacity)
        self.closed = False

    def _binding_decision(self, message: Mapping[str, Any]) -> Decision:
        if message.get("session_id") != self.session_id:
            return Decision(StableCode.BINDING_MISMATCH)
        if self.lease_id is not None and message.get("lease_id") != self.lease_id:
            return Decision(StableCode.BINDING_MISMATCH)
        received_epoch = int(str(message["epoch"]))
        if received_epoch < self.epoch:
            return Decision(StableCode.EPOCH_STALE)
        if received_epoch > self.epoch:
            return Decision(StableCode.EPOCH_UNKNOWN)
        return Decision(StableCode.ACCEPTED)

    def accept(self, message: Mapping[str, Any]) -> Decision:
        if self.closed:
            return Decision(StableCode.LEASE_CLOSED)
        binding = self._binding_decision(message)
        if not binding.accepted:
            return binding
        seq = int(str(message["seq"]))
        full_digest = canonical_digest(message)
        sequence = self.sequence.preview(seq, str(message["message_id"]), full_digest)
        if sequence.code != StableCode.ACCEPTED:
            return sequence
        if "revision" not in message:
            self.sequence.commit(seq, str(message["message_id"]), full_digest)
            return Decision(StableCode.ACCEPTED)
        identity = revision_identity(message)
        revision = self.revisions.preview(
            identity,
            int(str(message["revision"])),
            canonical_digest(revision_projection(message)),
            canonical_digest(immutable_projection(message)),
            message_is_final(message),
        )
        if not revision.decision.accepted:
            return revision.decision
        self.sequence.commit(seq, str(message["message_id"]), full_digest)
        if revision.decision.code == StableCode.ACCEPTED:
            self.revisions.commit(identity, revision)
        return revision.decision

    def clear(self) -> None:
        self.sequence.clear()
        self.revisions.clear()
        self.closed = True


@dataclass(frozen=True, slots=True)
class ActiveLease:
    lease_id: str
    session_id: str
    epoch: int
    revision: int


@dataclass(frozen=True, slots=True)
class CancellationTombstone:
    lease_id: str
    session_id: str
    epoch: int
    expected_revision: int
    message_id: str
    reason: str
    closed_at: datetime
    digest: bytes


class CancellationRegistry:
    """Atomic CAS cancellation with bounded replay tombstones; runtimes own terminal state."""

    def __init__(
        self,
        capacity: int = CANCELLATION_TOMBSTONE_CAPACITY,
        ttl: timedelta = CANCELLATION_TOMBSTONE_TTL,
    ) -> None:
        if capacity < 1 or capacity > CANCELLATION_TOMBSTONE_CAPACITY:
            raise ValueError("invalid tombstone capacity")
        self.capacity = capacity
        self.ttl = ttl
        self.active: dict[str, ActiveLease] = {}
        self.tombstones: OrderedDict[str, CancellationTombstone] = OrderedDict()

    def add_active(self, lease: ActiveLease) -> None:
        self.active[lease.lease_id] = lease

    def update_active_revision(self, lease_id: str, revision: int) -> None:
        lease = self.active.get(lease_id)
        if lease is None:
            raise ValueError("lease is not active")
        self.active[lease_id] = ActiveLease(
            lease_id=lease.lease_id,
            session_id=lease.session_id,
            epoch=lease.epoch,
            revision=revision,
        )

    def expire_active(self, lease_id: str) -> None:
        self.active.pop(lease_id, None)

    def prune(self, now: datetime) -> None:
        """Erase tombstones at the deadline even when no new cancellation arrives."""
        expired = [
            lease_id
            for lease_id, tombstone in self.tombstones.items()
            if now - tombstone.closed_at >= self.ttl
        ]
        for lease_id in expired:
            del self.tombstones[lease_id]

    def cancel(self, message: LeaseCancelV1, raw: Mapping[str, Any], now: datetime) -> Decision:
        self.prune(now)
        digest = canonical_digest(raw)
        for tombstone in self.tombstones.values():
            if tombstone.message_id == message.message_id:
                if tombstone.digest == digest:
                    return Decision(StableCode.CANCEL_DUPLICATE)
                return Decision(StableCode.CANCEL_CONFLICT)
        lease = self.active.get(message.lease_id)
        if lease is None:
            return Decision(StableCode.LEASE_UNKNOWN)
        if message.session_id != lease.session_id:
            return Decision(StableCode.BINDING_MISMATCH)
        epoch = int(message.epoch)
        if epoch < lease.epoch:
            return Decision(StableCode.EPOCH_STALE)
        if epoch > lease.epoch:
            return Decision(StableCode.EPOCH_UNKNOWN)
        expected_revision = int(message.expected_revision)
        if expected_revision < lease.revision:
            return Decision(StableCode.REVISION_STALE)
        if expected_revision > lease.revision:
            return Decision(StableCode.REVISION_GAP)
        if len(self.tombstones) >= self.capacity:
            self.tombstones.popitem(last=False)
        del self.active[lease.lease_id]
        self.tombstones[lease.lease_id] = CancellationTombstone(
            lease_id=lease.lease_id,
            session_id=lease.session_id,
            epoch=lease.epoch,
            expected_revision=lease.revision,
            message_id=message.message_id,
            reason=message.reason,
            closed_at=now,
            digest=digest,
        )
        return Decision(StableCode.ACCEPTED)

    def session_teardown(self, session_id: str) -> None:
        self.active = {
            key: value for key, value in self.active.items() if value.session_id != session_id
        }
        self.tombstones = OrderedDict(
            (key, value) for key, value in self.tombstones.items() if value.session_id != session_id
        )


@dataclass(frozen=True, slots=True)
class LiveWorkerCursor:
    connection_id: str
    lease_id: str
    session_id: str
    epoch: int
    next_input_seq: int
    next_output_seq: int
    expires_at: str


@dataclass(frozen=True, slots=True)
class LiveViewerCursor:
    session_id: str
    epoch: int
    next_seq: int


def decide_worker_resume(
    requested: WorkerResumeV1, live: LiveWorkerCursor | None, now: datetime
) -> Decision:
    if live is None:
        return Decision(StableCode.RESYNC_REQUIRED)
    if parse_timestamp(live.expires_at) <= now:
        return Decision(StableCode.LEASE_EXPIRED)
    if requested.session_id != live.session_id or requested.lease_id != live.lease_id:
        return Decision(StableCode.BINDING_MISMATCH)
    requested_epoch = int(requested.epoch)
    if requested_epoch < live.epoch:
        return Decision(StableCode.EPOCH_STALE)
    if requested_epoch > live.epoch:
        return Decision(StableCode.EPOCH_UNKNOWN)
    if (
        requested.connection_id != live.connection_id
        or int(requested.next_input_seq) != live.next_input_seq
        or int(requested.next_output_seq) != live.next_output_seq
    ):
        return Decision(StableCode.RESYNC_REQUIRED)
    return Decision(StableCode.ACCEPTED)


def decide_viewer_resume(requested: ViewerCursorV1, live: LiveViewerCursor | None) -> Decision:
    if live is None:
        return Decision(StableCode.RESYNC_REQUIRED)
    if requested.session_id != live.session_id:
        return Decision(StableCode.BINDING_MISMATCH)
    requested_epoch = int(requested.epoch)
    if requested_epoch < live.epoch:
        return Decision(StableCode.EPOCH_STALE)
    if requested_epoch > live.epoch:
        return Decision(StableCode.EPOCH_UNKNOWN)
    if int(requested.next_seq) != live.next_seq:
        return Decision(StableCode.RESYNC_REQUIRED)
    return Decision(StableCode.ACCEPTED)
