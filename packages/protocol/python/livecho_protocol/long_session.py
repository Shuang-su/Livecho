"""Minor-1 long-session rotation. Minor 0 keeps the unchanged revision domain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .errors import Decision, StableCode
from .parser import canonical_digest
from .scalars import UINT64_MAX
from .state import REVISION_DOMAIN_CAPACITY, RevisionDomain, RevisionIdentity

ROTATION_TOMBSTONE_CAPACITY = 8
SESSION_REVISION_CEILING = REVISION_DOMAIN_CAPACITY * 2 + 1
DomainName = Literal["worker", "viewer"]
RotationReason = Literal["revision_capacity", "lease_replaced"]


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


class Minor1Session:
    """One session, two revision domains, and a bounded rotation tombstone ring."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.epoch = 1
        self.worker = RevisionDomain()
        self.viewer = RevisionDomain()
        self.lease_open = False
        self.media_continue_ms = 0
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
        if target.record(identity) is None and start_ms < self.media_continue_ms:
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
        if len(self.tombstones) == ROTATION_TOMBSTONE_CAPACITY:
            self.tombstones.pop(0)
        self.tombstones.append(
            RotationTombstone(
                closed_epoch=self.epoch,
                input_next_seq=self.input_next_seq,
                output_next_seq=self.output_next_seq,
                viewer_next_seq=self.viewer_next_seq,
                media_continue_ms=self.media_continue_ms,
                pcm_continue_pts=self.pcm_continue_pts,
                reason=reason,
            )
        )
        self.epoch += 1
        self.worker = RevisionDomain()
        self.viewer = RevisionDomain()
        self.lease_open = False
        self.input_next_seq = 1
        self.output_next_seq = 1
        self.viewer_next_seq = 1
        return Decision(StableCode.EPOCH_ROTATED)


def _digest(*parts: object) -> bytes:
    return canonical_digest({"parts": [str(part) for part in parts]})
