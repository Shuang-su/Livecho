from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

from livecho_protocol.binary import PcmHeaderV1, encode_header
from livecho_protocol.errors import StableCode
from livecho_protocol.models import LeaseCancelV1, ViewerCursorV1, WorkerResumeV1
from livecho_protocol.parser import canonical_digest
from livecho_protocol.runtime import LeaseRuntimeState
from livecho_protocol.state import (
    ActiveLease,
    CancellationRegistry,
    JsonSequenceWindow,
    LiveViewerCursor,
    LiveWorkerCursor,
    PcmSequenceWindow,
    RevisionDomain,
    StreamOrderingState,
    decide_viewer_resume,
    decide_worker_resume,
    immutable_projection,
    revision_identity,
    revision_projection,
)

from tests.protocol.conftest import (
    CONNECTION_ID,
    LEASE_ID,
    MESSAGE_ID,
    MESSAGE_ID_2,
    SESSION_ID,
    worker_envelope,
)


def test_json_sequence_fifo_has_exact_255_256_boundary() -> None:
    window = JsonSequenceWindow(0)
    for seq in range(256):
        digest = canonical_digest({"seq": str(seq)})
        assert window.preview(seq, MESSAGE_ID, digest).code == StableCode.ACCEPTED
        window.commit(seq, MESSAGE_ID, digest)
    for seq in range(256):
        assert (
            window.preview(seq, MESSAGE_ID, canonical_digest({"seq": str(seq)})).code
            == StableCode.SEQ_DUPLICATE
        )
    window.commit(256, MESSAGE_ID, canonical_digest({"seq": "256"}))
    assert len(window.retained_sequences) == 256
    assert window.retained_sequences[0] == 1
    assert (
        window.preview(0, MESSAGE_ID, canonical_digest({"seq": "0"})).code
        == StableCode.RESYNC_REQUIRED
    )
    assert (
        window.preview(1, MESSAGE_ID, canonical_digest({"seq": "1"})).code
        == StableCode.SEQ_DUPLICATE
    )
    assert (
        window.preview(1, MESSAGE_ID_2, canonical_digest({"seq": "1"})).code
        == StableCode.SEQ_CONFLICT
    )
    assert window.preview(258, MESSAGE_ID, b"x" * 32).code == StableCode.SEQ_GAP


def test_pcm_sequence_boundary_retains_no_records() -> None:
    window = PcmSequenceWindow(0)
    for seq in range(256):
        assert window.preview(seq).code == StableCode.ACCEPTED
        window.commit(seq)
    for seq in range(256):
        assert window.preview(seq).code == StableCode.SEQ_DUPLICATE
    window.commit(256)
    assert vars(window) == {"start_seq": 0, "next_expected_seq": 257}
    assert window.preview(0).code == StableCode.RESYNC_REQUIRED
    assert window.preview(1).code == StableCode.SEQ_DUPLICATE


def _revision_values(message: dict[str, object]) -> tuple[bytes, bytes]:
    return canonical_digest(revision_projection(message)), canonical_digest(
        immutable_projection(message)
    )


def test_revision_domain_precedence_and_immutable_record(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    message = deepcopy(valid_messages["TranscriptSegmentV1"])
    domain = RevisionDomain()
    identity = revision_identity(message)
    full, immutable = _revision_values(message)
    first = domain.preview(identity, 1, full, immutable, False)
    assert first.decision.code == StableCode.ACCEPTED
    domain.commit(identity, first)
    assert (
        domain.preview(identity, 1, full, immutable, False).decision.code
        == StableCode.REVISION_DUPLICATE
    )

    changed_current = {**message, "text": "changed"}
    changed_full, changed_immutable = _revision_values(changed_current)
    assert (
        domain.preview(identity, 1, changed_full, changed_immutable, False).decision.code
        == StableCode.REVISION_CONFLICT
    )
    changed_time = {**message, "revision": "2", "end_ms": 1001}
    time_full, time_immutable = _revision_values(changed_time)
    assert (
        domain.preview(identity, 2, time_full, time_immutable, False).decision.code
        == StableCode.REVISION_IMMUTABLE
    )
    assert domain.record(identity) == first.record


def test_final_object_has_total_precedence(valid_messages: dict[str, dict[str, object]]) -> None:
    message = deepcopy(valid_messages["TranscriptSegmentV1"])
    domain = RevisionDomain()
    identity = revision_identity(message)
    full, immutable = _revision_values(message)
    first = domain.preview(identity, 1, full, immutable, False)
    domain.commit(identity, first)
    final_message = {**message, "revision": "2", "is_final": True}
    final_full, final_immutable = _revision_values(final_message)
    final = domain.preview(identity, 2, final_full, final_immutable, True)
    domain.commit(identity, final)
    assert (
        domain.preview(identity, 2, final_full, final_immutable, True).decision.code
        == StableCode.REVISION_DUPLICATE
    )
    assert (
        domain.preview(identity, 1, full, immutable, False).decision.code
        == StableCode.REVISION_STALE
    )
    changed = {**final_message, "text": "changed"}
    changed_full, _ = _revision_values(changed)
    assert (
        domain.preview(identity, 2, changed_full, immutable, True).decision.code
        == StableCode.OBJECT_FINAL
    )
    assert (
        domain.preview(identity, 3, changed_full, immutable, True).decision.code
        == StableCode.OBJECT_FINAL
    )


def test_revision_capacity_allows_existing_update_at_cap(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    domain = RevisionDomain()
    template = deepcopy(valid_messages["TranscriptSegmentV1"])
    first_identity = None
    first_message = None
    for index in range(4096):
        message = {
            **template,
            "segment_id": f"{index:08x}-0000-4000-8000-{index:012x}",
        }
        identity = revision_identity(message)
        full, immutable = _revision_values(message)
        preview = domain.preview(identity, 1, full, immutable, False)
        assert preview.decision.code == StableCode.ACCEPTED
        domain.commit(identity, preview)
        if index == 0:
            first_identity = identity
            first_message = message
    overflow = {**template, "segment_id": "00001000-0000-4000-8000-000000001000"}
    full, immutable = _revision_values(overflow)
    assert (
        domain.preview(revision_identity(overflow), 1, full, immutable, False).decision.code
        == StableCode.REVISION_CAPACITY_EXCEEDED
    )
    assert first_identity is not None and first_message is not None
    update = {**first_message, "revision": "2", "text": "updated"}
    update_full, update_immutable = _revision_values(update)
    assert (
        domain.preview(first_identity, 2, update_full, update_immutable, False).decision.code
        == StableCode.ACCEPTED
    )
    domain.clear()
    assert domain.size == 0
    assert (
        domain.preview(revision_identity(overflow), 1, full, immutable, False).decision.code
        == StableCode.ACCEPTED
    )


def test_stream_sequence_before_revision_and_no_state_change(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    state = StreamOrderingState(session_id=SESSION_ID, lease_id=LEASE_ID, epoch=1, start_seq=0)
    first = deepcopy(valid_messages["TranscriptSegmentV1"])
    assert state.accept(first).code == StableCode.ACCEPTED
    old_changed = {**first, "text": "changed"}
    assert state.accept(old_changed).code == StableCode.SEQ_CONFLICT

    next_duplicate = {
        **first,
        "message_id": MESSAGE_ID_2,
        "sent_at": "2026-01-01T00:00:01.000Z",
        "seq": "1",
    }
    assert state.accept(next_duplicate).code == StableCode.REVISION_DUPLICATE
    conflict = {
        **next_duplicate,
        "message_id": "00000000-0000-4000-8000-000000000003",
        "seq": "2",
        "text": "changed",
    }
    before = state.sequence.next_expected_seq
    assert state.accept(conflict).code == StableCode.REVISION_CONFLICT
    assert state.sequence.next_expected_seq == before


def _cancel(message_id: str = MESSAGE_ID, reason: str = "operator_stop") -> dict[str, object]:
    return {
        **worker_envelope("worker.lease_cancel", message_id),
        "lease_id": LEASE_ID,
        "session_id": SESSION_ID,
        "epoch": "1",
        "expected_revision": "1",
        "reason": reason,
    }


def test_cancellation_cas_tombstone_and_expiry() -> None:
    registry = CancellationRegistry()
    registry.add_active(ActiveLease(LEASE_ID, SESSION_ID, 1, 1))
    now = datetime(2026, 1, 1, tzinfo=UTC)
    raw = _cancel()
    message = LeaseCancelV1.model_validate(raw)
    assert registry.cancel(message, raw, now).code == StableCode.ACCEPTED
    assert registry.cancel(message, raw, now).code == StableCode.CANCEL_DUPLICATE
    changed_raw = _cancel(reason="session_end")
    changed = LeaseCancelV1.model_validate(changed_raw)
    assert registry.cancel(changed, changed_raw, now).code == StableCode.CANCEL_CONFLICT
    registry.session_teardown(SESSION_ID)
    assert registry.active == {}
    assert registry.closed == {}
    assert registry.tombstones == {}

    registry = CancellationRegistry()
    registry.add_active(ActiveLease(LEASE_ID, SESSION_ID, 1, 1))
    assert registry.cancel(message, raw, now).code == StableCode.ACCEPTED
    assert (
        registry.cancel(message, raw, now + timedelta(seconds=120)).code == StableCode.LEASE_CLOSED
    )


def test_cancellation_capacity_evicts_oldest_before_close() -> None:
    registry = CancellationRegistry(capacity=2)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    lease_ids: list[str] = []
    for index in range(3):
        lease_id = f"{index + 100:08x}-0000-4000-8000-{index + 100:012x}"
        message_id = f"{index + 200:08x}-0000-4000-8000-{index + 200:012x}"
        lease_ids.append(lease_id)
        registry.add_active(ActiveLease(lease_id, SESSION_ID, 1, 1))
        raw = {**_cancel(message_id), "lease_id": lease_id}
        assert registry.cancel(LeaseCancelV1.model_validate(raw), raw, now).accepted
        now += timedelta(seconds=1)
    assert tuple(registry.tombstones) == tuple(lease_ids[1:])


def test_cancellation_closes_pcm_and_output_atomically(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    runtime = LeaseRuntimeState(
        lease_id=LEASE_ID,
        session_id=SESSION_ID,
        epoch=1,
        revision=1,
        input_start_seq=0,
        output_start_seq=0,
    )
    output = deepcopy(valid_messages["TranscriptSegmentV1"])
    assert runtime.output.accept(output).code == StableCode.ACCEPTED

    header = PcmHeaderV1(LEASE_ID, 1, 0, 0, 1, 2)
    frame = bytearray(encode_header(header)) + bytearray(header.payload_length)
    assert runtime.pcm.accept(frame).code == StableCode.ACCEPTED
    assert runtime.pcm.buffered_bytes == 2

    raw = _cancel()
    cancellation = LeaseCancelV1.model_validate(raw)
    assert (
        runtime.cancel(cancellation, raw, datetime(2026, 1, 1, tzinfo=UTC)).code
        == StableCode.ACCEPTED
    )
    assert runtime.pcm.buffered_bytes == 0
    assert runtime.output.sequence.retained_sequences == ()
    assert runtime.output.revisions.size == 0
    assert runtime.pcm.accept(frame).code == StableCode.LEASE_CLOSED
    assert runtime.output.accept(output).code == StableCode.LEASE_CLOSED


def test_resume_requires_exact_live_cursor() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    worker = WorkerResumeV1.model_validate(
        {
            "connection_id": CONNECTION_ID,
            "lease_id": LEASE_ID,
            "session_id": SESSION_ID,
            "epoch": "1",
            "next_input_seq": "2",
            "next_output_seq": "3",
        }
    )
    live_worker = LiveWorkerCursor(
        CONNECTION_ID,
        LEASE_ID,
        SESSION_ID,
        1,
        2,
        3,
        "2026-01-01T00:01:00.000Z",
    )
    assert decide_worker_resume(worker, live_worker, now).code == StableCode.ACCEPTED
    assert decide_worker_resume(worker, None, now).code == StableCode.RESYNC_REQUIRED

    viewer = ViewerCursorV1.model_validate(
        {"session_id": SESSION_ID, "epoch": "1", "next_seq": "4"}
    )
    assert decide_viewer_resume(viewer, LiveViewerCursor(SESSION_ID, 1, 4)).accepted
    assert (
        decide_viewer_resume(viewer, LiveViewerCursor(SESSION_ID, 2, 4)).code
        == StableCode.EPOCH_STALE
    )
