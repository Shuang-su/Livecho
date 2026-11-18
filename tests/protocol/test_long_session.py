"""Issue #27 minor-1 rotation, continuity, and minor-0 retain behavior."""

from livecho_protocol.compatibility import negotiate_viewer, negotiate_worker
from livecho_protocol.errors import StableCode
from livecho_protocol.golden import _public_values
from livecho_protocol.long_session import (
    ROTATION_TOMBSTONE_CAPACITY,
    SESSION_REVISION_CEILING,
    Minor1Session,
)
from livecho_protocol.models import LeaseV1, ViewerSubscribeV1, WorkerHelloV1
from livecho_protocol.scalars import UINT64_MAX
from livecho_protocol.state import REVISION_DOMAIN_CAPACITY, RevisionDomain


def _fill(session: Minor1Session, domain: str, count: int, *, start_ms: int = 0) -> None:
    for index in range(count):
        start = start_ms + index
        decision = session.admit(
            domain,  # type: ignore[arg-type]
            f"object-{index}",
            start_ms=start,
            end_ms=start + 1,
        )
        assert decision.code == StableCode.ACCEPTED, decision.code


def test_minor0_domain_does_not_rotate() -> None:
    domain = RevisionDomain()
    for index in range(REVISION_DOMAIN_CAPACITY):
        identity = ("worker.transcript", "session", "lease", 1, f"object-{index}")
        preview = domain.preview(identity, 1, b"a", b"b", False)
        assert preview.decision.code == StableCode.ACCEPTED
        domain.commit(identity, preview)
    overflow = domain.preview(
        ("worker.transcript", "session", "lease", 1, "object-overflow"),
        1,
        b"a",
        b"b",
        False,
    )
    assert overflow.decision.code == StableCode.REVISION_CAPACITY_EXCEEDED
    assert domain.size == REVISION_DOMAIN_CAPACITY


def test_each_domain_rotates_on_its_own_ceiling() -> None:
    session = Minor1Session("session")
    _fill(session, "worker", REVISION_DOMAIN_CAPACITY)
    assert session.viewer.size == 0
    rotated = session.admit(
        "worker", "overflow", start_ms=REVISION_DOMAIN_CAPACITY, end_ms=REVISION_DOMAIN_CAPACITY + 1
    )
    assert rotated.code == StableCode.EPOCH_ROTATED
    assert session.epoch == 2
    assert session.worker.size == 0
    assert session.viewer.size == 0
    assert session.revision_record_count == 0
    _fill(session, "viewer", REVISION_DOMAIN_CAPACITY)
    assert session.worker.size == 0
    rotated = session.admit("viewer", "overflow", start_ms=0, end_ms=1)
    assert rotated.code == StableCode.EPOCH_ROTATED
    assert session.epoch == 3
    assert len(session.tombstones) == 2


def test_three_crossings_stay_within_the_session_ceiling() -> None:
    session = Minor1Session("session")
    for _ in range(3):
        _fill(session, "worker", REVISION_DOMAIN_CAPACITY)
        assert session.revision_record_count <= SESSION_REVISION_CEILING
        decision = session.admit("worker", "overflow")
        assert decision.code == StableCode.EPOCH_ROTATED
        assert session.worker.size == 0
        assert session.viewer.size == 0
    assert session.epoch == 4
    assert len(session.tombstones) == 3


def test_existing_identity_update_does_not_rotate() -> None:
    session = Minor1Session("session")
    _fill(session, "worker", REVISION_DOMAIN_CAPACITY)
    updated = session.admit("worker", "object-0", revision=2, start_ms=0, end_ms=1)
    assert updated.code == StableCode.ACCEPTED
    assert session.epoch == 1
    duplicate = session.admit("worker", "object-0", revision=2, start_ms=0, end_ms=1)
    assert duplicate.code == StableCode.REVISION_DUPLICATE


def test_final_is_immutable_and_closed_epoch_cannot_mutate_it() -> None:
    session = Minor1Session("session")
    assert (
        session.admit("worker", "final", is_final=True, start_ms=0, end_ms=10).code
        == StableCode.ACCEPTED
    )
    assert (
        session.admit("worker", "final", revision=2, is_final=True, start_ms=0, end_ms=10).code
        == StableCode.OBJECT_FINAL
    )
    assert session.media_continue_ms == 10
    _fill(session, "worker", REVISION_DOMAIN_CAPACITY - 1, start_ms=10)
    assert (
        session.admit("worker", "overflow", start_ms=10, end_ms=11).code == StableCode.EPOCH_ROTATED
    )
    assert session.epoch_decision(1).code == StableCode.EPOCH_STALE
    assert session.epoch_decision(2).code == StableCode.ACCEPTED
    assert session.media_continue_ms == 10


def test_media_time_continues_across_epochs_and_resets_for_a_new_session() -> None:
    session = Minor1Session("session")
    assert (
        session.admit("worker", "spoken", is_final=True, start_ms=0, end_ms=40).code
        == StableCode.ACCEPTED
    )
    session.replace_lease()
    assert session.epoch == 2
    assert (
        session.admit("worker", "regressed", start_ms=39, end_ms=50).code
        == StableCode.MEDIA_TIME_REGRESSED
    )
    assert session.worker.size == 0
    assert (
        session.admit("worker", "continued", is_final=True, start_ms=40, end_ms=80).code
        == StableCode.ACCEPTED
    )
    assert session.note_pcm(80, 16000).code == StableCode.ACCEPTED
    assert session.pcm_continue_pts == 1080
    assert session.note_pcm(79, 16).code == StableCode.AUDIO_PTS_INVALID
    fresh = Minor1Session("other")
    assert fresh.media_continue_ms == 0
    assert (
        fresh.admit("worker", "restart", is_final=True, start_ms=0, end_ms=5).code
        == StableCode.ACCEPTED
    )


def test_cursors_distinguish_resume_from_gap() -> None:
    session = Minor1Session("session")
    session.viewer_next_seq = 4
    resumed, notice = session.viewer_cursor("session", 1, 4)
    assert resumed.code == StableCode.ACCEPTED
    assert notice is None
    expired, notice = session.viewer_cursor("session", 1, 1)
    assert expired.code == StableCode.RESYNC_REQUIRED
    assert notice is not None and notice.reason == "cursor_expired" and notice.gap
    session.replace_lease()
    rotated, notice = session.viewer_cursor("session", 1, 4)
    assert rotated.code == StableCode.RESYNC_REQUIRED
    assert notice is not None and notice.reason == "epoch_rotated" and notice.gap
    unknown, notice = session.viewer_cursor("session", 9, 1)
    assert unknown.code == StableCode.RESYNC_REQUIRED
    assert notice is not None and notice.reason == "cursor_unknown" and notice.gap
    mismatch, notice = session.viewer_cursor("else", 2, 1)
    assert mismatch.code == StableCode.BINDING_MISMATCH
    assert notice is None


def test_tombstones_evict_and_epoch_does_not_wrap() -> None:
    session = Minor1Session("session")
    for _ in range(ROTATION_TOMBSTONE_CAPACITY + 1):
        assert session.replace_lease().code == StableCode.EPOCH_ROTATED
    assert len(session.tombstones) == ROTATION_TOMBSTONE_CAPACITY
    assert session.epoch_decision(1).code == StableCode.EPOCH_UNKNOWN
    assert session.epoch_decision(2).code == StableCode.EPOCH_STALE
    session.epoch = UINT64_MAX
    assert session.replace_lease().code == StableCode.EPOCH_EXHAUSTED
    assert session.epoch == UINT64_MAX


def test_negotiation_selects_minor1_only_for_the_specified_offer() -> None:
    hello = WorkerHelloV1.model_validate(_public_values()["WorkerHelloV1"])
    allow = frozenset({("synthetic", "fixture-asr", "1", "a" * 64)})
    assert negotiate_worker(hello, allow).selected_minor == 0
    offered = hello.model_copy(
        update={
            "supported_minors": [0, 1],
            "capabilities": ["asr.transcribe", "protocol.binary-pcm", "protocol.epoch-rotation"],
        }
    )
    assert negotiate_worker(offered, allow).selected_minor == 1
    minor0_only = hello.model_copy(update={"supported_minors": [1]})
    assert negotiate_worker(minor0_only, allow).decision.code == StableCode.UNSUPPORTED_MINOR
    viewer = ViewerSubscribeV1.model_validate(_public_values()["ViewerSubscribeV1"])
    assert negotiate_viewer(viewer).selected_minor == 0
    assert (
        negotiate_viewer(viewer.model_copy(update={"supported_minors": [0, 1]})).selected_minor == 1
    )
    assert (
        negotiate_viewer(viewer.model_copy(update={"supported_minors": [1]})).decision.code
        == StableCode.UNSUPPORTED_MINOR
    )
    lease = LeaseV1.model_validate(_public_values()["LeaseV1"])
    assert lease.audio_origin == "synthetic"
