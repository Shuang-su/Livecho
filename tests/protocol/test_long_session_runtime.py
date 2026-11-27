"""Minor-1 protocol integration with synthetic control and PCM metadata."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from livecho_protocol.binary import PcmHeaderV1
from livecho_protocol.compatibility import manifest_key
from livecho_protocol.errors import StableCode
from livecho_protocol.golden import _public_values
from livecho_protocol.long_session import ROTATION_TOMBSTONE_CAPACITY, Minor1SessionRuntime
from livecho_protocol.models import (
    EpochRotatedV1,
    LeaseV1,
    LeaseV1Minor1,
    TimelineEventV1Minor1,
    TranscriptSegmentV1Minor1,
    ViewerCursorV1,
    ViewerResyncV1,
)
from livecho_protocol.parser import canonical_json, parse_control
from livecho_protocol.runtime import LeaseRuntimeCoordinator
from livecho_protocol.state import REVISION_DOMAIN_CAPACITY
from pydantic import ValidationError

SESSION = "00000000-0000-4000-8000-000000000627"
ROOM = "synthetic-room"
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _id(value: int) -> str:
    return f"00000000-0000-4000-8000-{value:012x}"


def _lease(epoch: int = 1) -> LeaseV1Minor1:
    fields = _public_values()["LeaseV1Minor1"]
    return LeaseV1Minor1.model_validate(
        fields | {"session_id": SESSION, "epoch": str(epoch), "lease_id": _id(0x2000 + epoch)}
    )


def _worker(
    lease: LeaseV1Minor1,
    seq: int,
    *,
    start_ms: int = 0,
    is_final: bool = False,
) -> TranscriptSegmentV1Minor1:
    fields = _public_values()["TranscriptSegmentV1Minor1"]
    return TranscriptSegmentV1Minor1.model_validate(
        fields
        | {
            "session_id": SESSION,
            "lease_id": lease.lease_id,
            "epoch": lease.epoch,
            "seq": str(seq),
            "segment_id": _id(0x4000 + seq),
            "message_id": _id(0x8000 + seq),
            "start_ms": start_ms,
            "end_ms": start_ms + 100,
            "is_final": is_final,
        }
    )


def _viewer(epoch: int, seq: int, transcript: TranscriptSegmentV1Minor1) -> TimelineEventV1Minor1:
    fields = _public_values()["TimelineEventV1Minor1"]
    return TimelineEventV1Minor1.model_validate(
        fields
        | {
            "session_id": SESSION,
            "epoch": str(epoch),
            "seq": str(seq),
            "event_id": _id(0xC000 + seq),
            "message_id": _id(0x10000 + seq),
            "payload": transcript.model_dump(include=set(fields["payload"]), mode="json"),
        }
    )


def _cursor(epoch: int, seq: int, session: str = SESSION) -> ViewerCursorV1:
    return ViewerCursorV1(session_id=session, epoch=str(epoch), next_seq=str(seq))


def _header(lease: LeaseV1Minor1, seq: int, pts_ms: int) -> PcmHeaderV1:
    return PcmHeaderV1(
        lease_id=lease.lease_id,
        epoch=int(lease.epoch),
        seq=seq,
        pts_ms=pts_ms,
        sample_count=320,
        payload_length=640,
        protocol_minor=1,
    )


@pytest.fixture
def session() -> Iterator[tuple[Minor1SessionRuntime, LeaseRuntimeCoordinator]]:
    coordinator = LeaseRuntimeCoordinator(
        accepted_manifests=frozenset({manifest_key(_lease().model_manifest)})
    )
    runtime = Minor1SessionRuntime(SESSION, ROOM, leases=coordinator)
    try:
        assert runtime.install_lease(_lease(), now=NOW).code == StableCode.ACCEPTED
        yield runtime, coordinator
    finally:
        runtime.close()


def test_replacement_retires_old_pcm_and_emits_the_two_closed_messages(
    session: tuple[Minor1SessionRuntime, LeaseRuntimeCoordinator],
) -> None:
    runtime, leases = session
    primary = _lease()
    final = _worker(primary, 1, start_ms=100, is_final=True)
    assert runtime.accept_worker(final, now=NOW).decision.code == StableCode.ACCEPTED
    projected = _viewer(1, 1, final)
    assert runtime.accept_viewer_event(projected, now=NOW).decision.code == StableCode.ACCEPTED
    assert runtime.accept_pcm_header(_header(primary, 1, 100), now=NOW).code == StableCode.ACCEPTED
    assert leases.session_buffered_audio_bytes(SESSION) == 640

    update = runtime.replace_lease(now=NOW)
    assert update.decision.code == StableCode.ACCEPTED
    assert update.rotation is not None
    worker, _ = parse_control(
        canonical_json(update.rotation.worker.model_dump(mode="json")), EpochRotatedV1
    )
    viewer, _ = parse_control(
        canonical_json(update.rotation.viewer.model_dump(mode="json")), ViewerResyncV1
    )
    assert (worker.closed_epoch, worker.opened_epoch, worker.lease_id) == (
        "1",
        "2",
        primary.lease_id,
    )
    assert (worker.reason, worker.media_continue_ms, worker.pcm_continue_pts) == (
        "lease_replaced",
        200,
        "120",
    )
    assert (viewer.reason, viewer.epoch, viewer.next_seq, viewer.media_continue_ms, viewer.gap) == (
        "epoch_rotated",
        "2",
        "1",
        200,
        True,
    )
    assert runtime.revision_record_count == 0
    assert leases.session_buffered_audio_bytes(SESSION) == 0
    assert runtime.accept_worker(final, now=NOW).decision.code == StableCode.EPOCH_STALE
    assert runtime.accept_viewer_event(projected, now=NOW).decision.code == StableCode.EPOCH_STALE
    assert (
        runtime.accept_pcm_header(_header(primary, 2, 120), now=NOW).code == StableCode.EPOCH_STALE
    )

    successor = _lease(2)
    assert runtime.install_lease(successor, now=NOW).code == StableCode.ACCEPTED
    assert (
        runtime.accept_pcm_header(_header(successor, 1, 119), now=NOW).code
        == StableCode.AUDIO_PTS_INVALID
    )
    assert (
        runtime.accept_pcm_header(_header(successor, 1, 120), now=NOW).code == StableCode.ACCEPTED
    )
    assert (
        runtime.accept_pcm_header(_header(successor, 2, 139), now=NOW).code
        == StableCode.AUDIO_PTS_INVALID
    )
    regressed = _worker(successor, 1, start_ms=199)
    assert (
        runtime.accept_worker(regressed, now=NOW).decision.code == StableCode.MEDIA_TIME_REGRESSED
    )
    legal = _worker(successor, 1, start_ms=200, is_final=True)
    assert runtime.accept_worker(legal, now=NOW).decision.code == StableCode.ACCEPTED


@pytest.mark.parametrize("trigger", ["worker", "viewer"])
def test_real_ordering_rotates_only_after_an_exact_next_capacity_candidate(
    session: tuple[Minor1SessionRuntime, LeaseRuntimeCoordinator], trigger: str
) -> None:
    runtime, _ = session
    lease = _lease()

    def submit(seq: int) -> StableCode:
        transcript = _worker(lease, seq)
        if trigger == "worker":
            return runtime.accept_worker(transcript, now=NOW).decision.code
        return runtime.accept_viewer_event(_viewer(1, seq, transcript), now=NOW).decision.code

    for seq in range(1, REVISION_DOMAIN_CAPACITY + 1):
        assert submit(seq) == StableCode.ACCEPTED
    assert runtime.revision_record_count == REVISION_DOMAIN_CAPACITY + 1
    assert submit(REVISION_DOMAIN_CAPACITY) == StableCode.SEQ_DUPLICATE
    assert submit(REVISION_DOMAIN_CAPACITY + 2) == StableCode.SEQ_GAP
    assert runtime.epoch == 1
    assert submit(REVISION_DOMAIN_CAPACITY + 1) == StableCode.EPOCH_ROTATED
    assert (runtime.epoch, runtime.viewer_next_seq, runtime.revision_record_count) == (2, 1, 0)
    retired = runtime._session.tombstones[-1]
    if trigger == "worker":
        assert retired.output_next_seq == REVISION_DOMAIN_CAPACITY + 1
    else:
        assert retired.viewer_next_seq == REVISION_DOMAIN_CAPACITY + 1


def test_cursor_paths_use_the_live_ordering_state_and_bounded_tombstones(
    session: tuple[Minor1SessionRuntime, LeaseRuntimeCoordinator],
) -> None:
    runtime, _ = session
    assert (
        runtime.accept_viewer_event(_viewer(1, 1, _worker(_lease(), 1)), now=NOW).decision.code
        == StableCode.ACCEPTED
    )
    result, notice = runtime.viewer_cursor(_cursor(1, 2), now=NOW)
    assert result.code == StableCode.ACCEPTED and notice is None
    result, notice = runtime.viewer_cursor(_cursor(1, 1), now=NOW)
    assert result.code == StableCode.RESYNC_REQUIRED
    assert notice is not None and (notice.reason, notice.next_seq) == ("cursor_expired", "2")
    result, notice = runtime.viewer_cursor(_cursor(1, 2, _id(0x628)), now=NOW)
    assert result.code == StableCode.BINDING_MISMATCH and notice is None
    assert runtime.replace_lease(now=NOW).decision.code == StableCode.ACCEPTED
    result, notice = runtime.viewer_cursor(_cursor(1, 2), now=NOW)
    assert result.code == StableCode.RESYNC_REQUIRED
    assert notice is not None and (notice.reason, notice.next_seq) == ("epoch_rotated", "1")
    for _ in range(ROTATION_TOMBSTONE_CAPACITY):
        assert runtime.replace_lease(now=NOW).decision.code == StableCode.ACCEPTED
    result, notice = runtime.viewer_cursor(_cursor(1, 2), now=NOW)
    assert result.code == StableCode.RESYNC_REQUIRED
    assert notice is not None and (notice.reason, notice.gap) == ("cursor_unknown", True)
    assert (
        runtime.accept_worker(_worker(_lease(), 1), now=NOW).decision.code
        == StableCode.EPOCH_UNKNOWN
    )


def test_invalid_or_terminal_lease_cannot_revive_a_retired_session(
    session: tuple[Minor1SessionRuntime, LeaseRuntimeCoordinator],
) -> None:
    runtime, _ = session
    legacy = LeaseV1.model_validate(_public_values()["LeaseV1"])
    assert runtime.install_lease(legacy, now=NOW).code == StableCode.UNSUPPORTED_MINOR
    assert runtime.install_lease(_lease(2), now=NOW).code == StableCode.EPOCH_UNKNOWN
    assert runtime.replace_lease(now=NOW).decision.code == StableCode.ACCEPTED
    successor = _lease(2)
    same_id = successor.model_copy(update={"lease_id": _lease().lease_id})
    assert runtime.install_lease(same_id, now=NOW).code == StableCode.BINDING_MISMATCH
    expired = NOW + timedelta(minutes=2)
    assert runtime.install_lease(successor, now=expired).code == StableCode.LEASE_EXPIRED
    assert (runtime.epoch, runtime.viewer_next_seq, runtime.revision_record_count) == (2, 1, 0)
    runtime.close()
    assert runtime.install_lease(successor, now=NOW).code == StableCode.BINDING_MISMATCH
    assert runtime.replace_lease(now=NOW).rotation is None


def test_failed_notice_validation_leaves_the_old_lease_and_cursors_live(
    session: tuple[Minor1SessionRuntime, LeaseRuntimeCoordinator],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, leases = session
    primary = _lease()
    assert runtime.accept_pcm_header(_header(primary, 1, 0), now=NOW).code == StableCode.ACCEPTED
    assert runtime.accept_worker(_worker(primary, 1), now=NOW).decision.code == StableCode.ACCEPTED
    monkeypatch.setattr("livecho_protocol.long_session.uuid4", lambda: "invalid-id")
    with pytest.raises(ValidationError):
        runtime.replace_lease(now=NOW)
    assert (runtime.epoch, runtime.viewer_next_seq, runtime.revision_record_count) == (1, 1, 2)
    assert runtime._session.tombstones == []
    assert leases.session_buffered_audio_bytes(SESSION) == 640
    assert runtime.accept_pcm_header(_header(primary, 2, 20), now=NOW).code == StableCode.ACCEPTED
    assert runtime.accept_worker(_worker(primary, 2), now=NOW).decision.code == StableCode.ACCEPTED
