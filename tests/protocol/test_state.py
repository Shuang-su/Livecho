from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest
from livecho_protocol.binary import (
    HEADER_LENGTH,
    LEASE_AUDIO_BUDGET,
    MAX_PAYLOAD_LENGTH,
    PROCESS_AUDIO_BUDGET,
    PcmHeaderV1,
    encode_header,
)
from livecho_protocol.errors import ProtocolValidationError, StableCode
from livecho_protocol.models import LeaseCancelV1, LeaseV1, ViewerCursorV1, WorkerResumeV1
from livecho_protocol.parser import canonical_digest
from livecho_protocol.runtime import LeaseRuntimeCoordinator
from livecho_protocol.scalars import UINT64_MAX
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


def test_sequence_exhaustion_rejects_before_cursor_overflow() -> None:
    digest = canonical_digest({"seq": str(UINT64_MAX)})
    json_window = JsonSequenceWindow(UINT64_MAX)
    assert json_window.preview(UINT64_MAX, MESSAGE_ID, digest).code == StableCode.RESYNC_REQUIRED
    with pytest.raises(ValueError, match="sequence space is exhausted"):
        json_window.commit(UINT64_MAX, MESSAGE_ID, digest)
    assert json_window.next_expected_seq == UINT64_MAX

    pcm_window = PcmSequenceWindow(UINT64_MAX)
    assert pcm_window.preview(UINT64_MAX).code == StableCode.RESYNC_REQUIRED
    with pytest.raises(ValueError, match="PCM sequence space is exhausted"):
        pcm_window.commit(UINT64_MAX)
    assert pcm_window.next_expected_seq == UINT64_MAX


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
    assert (
        domain.preview(revision_identity(overflow), 2, full, immutable, False).decision.code
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
    assert registry.tombstones == {}

    registry = CancellationRegistry()
    registry.add_active(ActiveLease(LEASE_ID, SESSION_ID, 1, 1))
    assert registry.cancel(message, raw, now).code == StableCode.ACCEPTED
    registry.prune(now + timedelta(seconds=120))
    assert registry.active == {}
    assert registry.tombstones == {}


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
    assert not hasattr(registry, "closed")


def test_cancellation_closes_pcm_and_output_atomically(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    lease = LeaseV1.model_validate(valid_messages["LeaseV1"])
    coordinator = LeaseRuntimeCoordinator()
    coordinator.session_teardown(SESSION_ID)
    runtime = coordinator.create(lease)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    output = deepcopy(valid_messages["TranscriptSegmentV1"])
    assert runtime.accept_output(output, now=now).code == StableCode.ACCEPTED

    header = PcmHeaderV1(LEASE_ID, 1, 0, 0, 1, 2)
    frame = bytearray(encode_header(header)) + bytearray(header.payload_length)
    assert runtime.accept_pcm(frame, now=now).code == StableCode.ACCEPTED
    assert runtime.buffered_audio_bytes == 2

    raw = _cancel()
    cancellation = LeaseCancelV1.model_validate(raw)
    assert runtime.cancel(cancellation, raw, now).code == StableCode.ACCEPTED
    assert runtime.buffered_audio_bytes == 0
    assert runtime.output_revision_count == 0
    assert runtime.accept_pcm(frame, now=now).code == StableCode.LEASE_CLOSED
    assert runtime.accept_output(output, now=now).code == StableCode.LEASE_CLOSED
    assert runtime.cancel(cancellation, raw, now).code == StableCode.CANCEL_DUPLICATE


def test_non_sequenced_lease_revision_updates_cancellation_cas(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    initial_raw = deepcopy(valid_messages["LeaseV1"])
    initial = LeaseV1.model_validate(initial_raw)
    coordinator = LeaseRuntimeCoordinator()
    coordinator.session_teardown(SESSION_ID)
    runtime = coordinator.create(initial)
    now = datetime(2026, 1, 1, tzinfo=UTC)

    replay_raw = {**initial_raw, "message_id": MESSAGE_ID_2}
    replay = LeaseV1.model_validate(replay_raw)
    assert runtime.accept_lease_update(replay, now=now).code == StableCode.REVISION_DUPLICATE

    update_raw = {
        **initial_raw,
        "message_id": "00000000-0000-4000-8000-000000000003",
        "revision": "2",
    }
    update = LeaseV1.model_validate(update_raw)
    assert runtime.accept_lease_update(update, now=now).code == StableCode.ACCEPTED
    assert runtime.lease_revision == 2

    immutable_raw = {
        **update_raw,
        "message_id": "00000000-0000-4000-8000-000000000004",
        "revision": "3",
        "room_id": "changed-room",
    }
    immutable = LeaseV1.model_validate(immutable_raw)
    assert runtime.accept_lease_update(immutable, now=now).code == StableCode.REVISION_IMMUTABLE
    assert runtime.lease_revision == 2

    cancel_raw = {**_cancel(), "expected_revision": "2"}
    cancellation = LeaseCancelV1.model_validate(cancel_raw)
    assert runtime.cancel(cancellation, cancel_raw, now).code == StableCode.ACCEPTED


def test_runtime_expires_before_pcm_output_lease_update_or_cancellation(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    lease_raw = deepcopy(valid_messages["LeaseV1"])
    lease = LeaseV1.model_validate(lease_raw)
    coordinator = LeaseRuntimeCoordinator()
    coordinator.session_teardown(SESSION_ID)
    runtime = coordinator.create(lease)
    before = datetime(2026, 1, 1, 0, 1, 59, 999000, tzinfo=UTC)
    deadline = datetime(2026, 1, 1, 0, 2, tzinfo=UTC)
    output = deepcopy(valid_messages["TranscriptSegmentV1"])
    frame = bytearray(encode_header(PcmHeaderV1(LEASE_ID, 1, 0, 0, 1, 2))) + bytearray(2)

    assert runtime.accept_pcm(frame, now=before).code == StableCode.ACCEPTED
    assert runtime.accept_output(output, now=deadline).code == StableCode.LEASE_EXPIRED
    assert runtime.buffered_audio_bytes == 0
    assert runtime.output_revision_count == 0
    assert runtime.accept_pcm(frame, now=deadline).code == StableCode.LEASE_EXPIRED
    assert runtime.accept_lease_update(lease, now=deadline).code == StableCode.LEASE_EXPIRED

    cancel_raw = _cancel()
    cancellation = LeaseCancelV1.model_validate(cancel_raw)
    assert runtime.cancel(cancellation, cancel_raw, deadline).code == StableCode.LEASE_EXPIRED
    assert not runtime.cancellation_active


def test_runtime_coordinator_prunes_idle_expired_runtime(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    coordinator = LeaseRuntimeCoordinator()
    coordinator.session_teardown(SESSION_ID)
    runtime = coordinator.create(LeaseV1.model_validate(valid_messages["LeaseV1"]))
    now = datetime(2026, 1, 1, tzinfo=UTC)
    deadline = datetime(2026, 1, 1, 0, 2, tzinfo=UTC)
    frame = bytearray(encode_header(PcmHeaderV1(LEASE_ID, 1, 0, 0, 1, 2))) + bytearray(2)

    assert runtime.accept_pcm(frame, now=now).code == StableCode.ACCEPTED
    assert coordinator.buffered_audio_bytes == 2

    LeaseRuntimeCoordinator().prune(deadline)

    assert runtime.buffered_audio_bytes == 0
    assert coordinator.buffered_audio_bytes == 0
    assert coordinator.session_buffered_audio_bytes(SESSION_ID) == 0
    assert not runtime.cancellation_active
    assert runtime.accept_pcm(frame, now=deadline).code == StableCode.LEASE_EXPIRED


def test_higher_epoch_replacement_retires_prior_runtime(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    coordinator = LeaseRuntimeCoordinator()
    coordinator.session_teardown(SESSION_ID)
    previous = coordinator.create(LeaseV1.model_validate(valid_messages["LeaseV1"]))
    now = datetime(2026, 1, 1, tzinfo=UTC)
    frame = bytearray(encode_header(PcmHeaderV1(LEASE_ID, 1, 0, 0, 1, 2))) + bytearray(2)
    output = deepcopy(valid_messages["TranscriptSegmentV1"])

    assert previous.accept_pcm(frame, now=now).code == StableCode.ACCEPTED
    assert previous.accept_output(output, now=now).code == StableCode.ACCEPTED

    replacement_raw = {
        **deepcopy(valid_messages["LeaseV1"]),
        "message_id": "00000000-0000-4000-8000-000000000090",
        "lease_id": "00000000-0000-4000-8000-000000000091",
        "epoch": "2",
    }
    replacement = coordinator.create(LeaseV1.model_validate(replacement_raw))

    assert previous.buffered_audio_bytes == 0
    assert previous.output_revision_count == 0
    assert not previous.cancellation_active
    assert previous.accept_pcm(frame, now=now).code == StableCode.LEASE_CLOSED
    assert replacement.cancellation_active
    assert coordinator.buffered_audio_bytes == 0
    assert coordinator.session_buffered_audio_bytes(SESSION_ID) == 0
    coordinator.session_teardown(SESSION_ID)


def test_invalid_replacement_is_rejected_before_live_state_retirement(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    coordinator = LeaseRuntimeCoordinator()
    coordinator.session_teardown(SESSION_ID)
    previous = coordinator.create(LeaseV1.model_validate(valid_messages["LeaseV1"]))
    now = datetime(2026, 1, 1, tzinfo=UTC)
    frame = bytearray(encode_header(PcmHeaderV1(LEASE_ID, 1, 0, 0, 1, 2))) + bytearray(2)
    output = deepcopy(valid_messages["TranscriptSegmentV1"])
    assert previous.accept_pcm(frame, now=now).code == StableCode.ACCEPTED
    assert previous.accept_output(output, now=now).code == StableCode.ACCEPTED
    assert coordinator.active_lease_count == 1

    invalid_raw = {
        **deepcopy(valid_messages["LeaseV1"]),
        "message_id": "00000000-0000-4000-8000-000000000090",
        "lease_id": "00000000-0000-4000-8000-000000000091",
        "epoch": "2",
        "revision": "2",
    }
    with pytest.raises(ProtocolValidationError) as invalid:
        coordinator.create(LeaseV1.model_validate(invalid_raw))

    assert invalid.value.code == StableCode.REVISION_GAP
    assert coordinator.active_lease_count == 1
    assert previous.cancellation_active
    assert previous.buffered_audio_bytes == 2
    assert previous.output_revision_count == 1
    assert previous.accept_pcm(frame, now=now).code == StableCode.SEQ_DUPLICATE
    coordinator.session_teardown(SESSION_ID)


def test_stale_epoch_runtime_creation_is_rejected(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    coordinator = LeaseRuntimeCoordinator()
    coordinator.session_teardown(SESSION_ID)
    current_raw = {
        **deepcopy(valid_messages["LeaseV1"]),
        "message_id": "00000000-0000-4000-8000-000000000090",
        "lease_id": "00000000-0000-4000-8000-000000000091",
        "epoch": "2",
    }
    current = coordinator.create(LeaseV1.model_validate(current_raw))

    with pytest.raises(ProtocolValidationError) as stale:
        coordinator.create(LeaseV1.model_validate(valid_messages["LeaseV1"]))

    assert stale.value.code == StableCode.EPOCH_STALE
    now = datetime(2026, 1, 1, tzinfo=UTC)
    frame = bytearray(
        encode_header(PcmHeaderV1(current.lease_id, current.epoch, 0, 0, 1, 2))
    ) + bytearray(2)
    assert current.accept_pcm(frame, now=now).code == StableCode.ACCEPTED
    coordinator.prune(datetime(2026, 1, 1, 0, 2, tzinfo=UTC))
    with pytest.raises(ProtocolValidationError) as stale_after_expiry:
        coordinator.create(LeaseV1.model_validate(valid_messages["LeaseV1"]))
    assert stale_after_expiry.value.code == StableCode.EPOCH_STALE
    coordinator.session_teardown(SESSION_ID)


def test_equal_epoch_runtime_creation_requires_existing_state_reuse(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    coordinator = LeaseRuntimeCoordinator()
    coordinator.session_teardown(SESSION_ID)
    current = coordinator.create(LeaseV1.model_validate(valid_messages["LeaseV1"]))
    duplicate_raw = {
        **deepcopy(valid_messages["LeaseV1"]),
        "message_id": "00000000-0000-4000-8000-000000000090",
        "lease_id": "00000000-0000-4000-8000-000000000091",
    }

    with pytest.raises(ProtocolValidationError) as duplicate:
        coordinator.create(LeaseV1.model_validate(duplicate_raw))

    assert duplicate.value.code == StableCode.RESYNC_REQUIRED
    now = datetime(2026, 1, 1, tzinfo=UTC)
    frame = bytearray(encode_header(PcmHeaderV1(current.lease_id, 1, 0, 0, 1, 2))) + bytearray(2)
    assert current.accept_pcm(frame, now=now).code == StableCode.ACCEPTED
    coordinator.session_teardown(SESSION_ID)


def test_end_of_segment_releases_runtime_pcm_ledgers(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    coordinator = LeaseRuntimeCoordinator()
    coordinator.session_teardown(SESSION_ID)
    runtime = coordinator.create(LeaseV1.model_validate(valid_messages["LeaseV1"]))
    now = datetime(2026, 1, 1, tzinfo=UTC)
    first = bytearray(encode_header(PcmHeaderV1(LEASE_ID, 1, 0, 0, 1, 2))) + bytearray(2)
    end = bytearray(encode_header(PcmHeaderV1(LEASE_ID, 1, 1, 1, 1, 2, True))) + bytearray(2)

    assert runtime.accept_pcm(first, now=now).code == StableCode.ACCEPTED
    assert coordinator.buffered_audio_bytes == 2
    assert coordinator.session_buffered_audio_bytes(SESSION_ID) == 2
    assert runtime.accept_pcm(end, now=now).code == StableCode.ACCEPTED
    assert runtime.buffered_audio_bytes == 0
    assert coordinator.buffered_audio_bytes == 0
    assert coordinator.session_buffered_audio_bytes(SESSION_ID) == 0
    coordinator.session_teardown(SESSION_ID)


def test_session_teardown_closes_all_runtime_state_domains(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    lease_raw = deepcopy(valid_messages["LeaseV1"])
    lease = LeaseV1.model_validate(lease_raw)
    coordinator = LeaseRuntimeCoordinator()
    coordinator.session_teardown(SESSION_ID)
    runtime = coordinator.create(lease)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    output = deepcopy(valid_messages["TranscriptSegmentV1"])
    frame = bytearray(encode_header(PcmHeaderV1(LEASE_ID, 1, 0, 0, 1, 2))) + bytearray(2)

    assert runtime.accept_pcm(frame, now=now).code == StableCode.ACCEPTED
    assert runtime.accept_output(output, now=now).code == StableCode.ACCEPTED
    LeaseRuntimeCoordinator().session_teardown(SESSION_ID)

    assert runtime.buffered_audio_bytes == 0
    assert runtime.output_revision_count == 0
    with pytest.raises(RuntimeError, match="lease revision state is cleared"):
        _ = runtime.lease_revision
    assert not runtime.cancellation_active
    assert runtime.accept_pcm(frame, now=now).code == StableCode.LEASE_CLOSED
    assert runtime.accept_output(output, now=now).code == StableCode.LEASE_CLOSED
    assert runtime.accept_lease_update(lease, now=now).code == StableCode.LEASE_CLOSED

    cancel_raw = _cancel()
    cancellation = LeaseCancelV1.model_validate(cancel_raw)
    assert runtime.cancel(cancellation, cancel_raw, now).code == StableCode.LEASE_CLOSED


def test_runtime_coordinator_enforces_process_pcm_budget_and_releases_bytes(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    coordinator = LeaseRuntimeCoordinator()
    coordinator.session_teardown(SESSION_ID)
    runtimes = []
    session_ids = []
    for index in range(18):
        session_id = f"{index + 700:08x}-0000-4000-8000-{index + 700:012x}"
        session_ids.append(session_id)
        lease_raw = {
            **deepcopy(valid_messages["LeaseV1"]),
            "message_id": f"{index + 500:08x}-0000-4000-8000-{index + 500:012x}",
            "lease_id": f"{index + 600:08x}-0000-4000-8000-{index + 600:012x}",
            "session_id": session_id,
        }
        runtimes.append(coordinator.create(LeaseV1.model_validate(lease_raw)))

    frame = bytearray(HEADER_LENGTH + MAX_PAYLOAD_LENGTH)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    frames_per_lease = LEASE_AUDIO_BUDGET // MAX_PAYLOAD_LENGTH
    accepted_frames = PROCESS_AUDIO_BUDGET // MAX_PAYLOAD_LENGTH
    for index in range(accepted_frames):
        runtime = runtimes[index // frames_per_lease]
        sequence = index % frames_per_lease
        frame[:HEADER_LENGTH] = encode_header(
            PcmHeaderV1(runtime.lease_id, 1, sequence, sequence, 16_000, MAX_PAYLOAD_LENGTH)
        )
        assert runtime.accept_pcm(frame, now=now).code == StableCode.ACCEPTED

    next_runtime = runtimes[accepted_frames // frames_per_lease]
    next_sequence = accepted_frames % frames_per_lease
    frame[:HEADER_LENGTH] = encode_header(
        PcmHeaderV1(next_runtime.lease_id, 1, next_sequence, next_sequence, 16_000, 32_000)
    )
    assert coordinator.buffered_audio_bytes == accepted_frames * MAX_PAYLOAD_LENGTH
    assert next_runtime.accept_pcm(frame, now=now).code == StableCode.AUDIO_BUDGET_EXCEEDED

    runtimes[0].consume_pcm(MAX_PAYLOAD_LENGTH)
    assert next_runtime.accept_pcm(frame, now=now).code == StableCode.ACCEPTED
    assert coordinator.buffered_audio_bytes == accepted_frames * MAX_PAYLOAD_LENGTH
    for session_id in session_ids:
        coordinator.session_teardown(session_id)
    assert coordinator.buffered_audio_bytes == 0


def test_runtime_coordinator_enforces_lease_and_session_pcm_budget(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    coordinator = LeaseRuntimeCoordinator()
    coordinator.session_teardown(SESSION_ID)
    runtime = coordinator.create(LeaseV1.model_validate(valid_messages["LeaseV1"]))

    frame = bytearray(HEADER_LENGTH + MAX_PAYLOAD_LENGTH)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    frames_per_session = LEASE_AUDIO_BUDGET // MAX_PAYLOAD_LENGTH
    for sequence in range(frames_per_session):
        frame[:HEADER_LENGTH] = encode_header(
            PcmHeaderV1(runtime.lease_id, 1, sequence, sequence, 16_000, MAX_PAYLOAD_LENGTH)
        )
        assert runtime.accept_pcm(frame, now=now).code == StableCode.ACCEPTED

    frame[:HEADER_LENGTH] = encode_header(
        PcmHeaderV1(
            runtime.lease_id,
            1,
            frames_per_session,
            frames_per_session,
            16_000,
            MAX_PAYLOAD_LENGTH,
        )
    )
    assert coordinator.session_buffered_audio_bytes(SESSION_ID) == LEASE_AUDIO_BUDGET
    assert runtime.accept_pcm(frame, now=now).code == StableCode.AUDIO_BUDGET_EXCEEDED
    runtime.consume_pcm(MAX_PAYLOAD_LENGTH)
    assert runtime.accept_pcm(frame, now=now).code == StableCode.ACCEPTED
    coordinator.session_teardown(SESSION_ID)
    assert coordinator.session_buffered_audio_bytes(SESSION_ID) == 0
    assert coordinator.buffered_audio_bytes == 0


def test_cancellation_cannot_close_a_different_runtime(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    coordinator = LeaseRuntimeCoordinator()
    coordinator.session_teardown(SESSION_ID)
    lease_a = LeaseV1.model_validate(valid_messages["LeaseV1"])
    lease_b_raw = {
        **deepcopy(valid_messages["LeaseV1"]),
        "message_id": "00000000-0000-4000-8000-000000000090",
        "lease_id": "00000000-0000-4000-8000-000000000091",
        "session_id": "00000000-0000-4000-8000-000000000092",
    }
    lease_b = LeaseV1.model_validate(lease_b_raw)
    runtime_a = coordinator.create(lease_a)
    runtime_b = coordinator.create(lease_b)
    cancel_b_raw = {
        **_cancel(),
        "lease_id": lease_b.lease_id,
        "session_id": lease_b.session_id,
    }
    cancel_b = LeaseCancelV1.model_validate(cancel_b_raw)
    now = datetime(2026, 1, 1, tzinfo=UTC)

    assert runtime_a.cancel(cancel_b, cancel_b_raw, now).code == StableCode.BINDING_MISMATCH
    frame_a = bytearray(encode_header(PcmHeaderV1(runtime_a.lease_id, 1, 0, 0, 1, 2))) + bytearray(
        2
    )
    frame_b = bytearray(encode_header(PcmHeaderV1(runtime_b.lease_id, 1, 0, 0, 1, 2))) + bytearray(
        2
    )
    assert runtime_a.accept_pcm(frame_a, now=now).code == StableCode.ACCEPTED
    assert runtime_b.accept_pcm(frame_b, now=now).code == StableCode.ACCEPTED
    assert runtime_b.cancel(cancel_b, cancel_b_raw, now).code == StableCode.ACCEPTED
    assert runtime_b.accept_pcm(frame_b, now=now).code == StableCode.LEASE_CLOSED
    assert runtime_a.accept_pcm(frame_a, now=now).code == StableCode.SEQ_DUPLICATE
    coordinator.session_teardown(SESSION_ID)
    coordinator.session_teardown(lease_b.session_id)


def test_runtime_coordinator_enforces_process_wide_tombstone_capacity(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    coordinator = LeaseRuntimeCoordinator()
    coordinator.session_teardown(SESSION_ID)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    first_runtime = None
    first_cancel = None
    first_raw = None
    for index in range(65):
        lease_id = f"{index + 100:08x}-0000-4000-8000-{index + 100:012x}"
        lease_raw = {
            **deepcopy(valid_messages["LeaseV1"]),
            "message_id": f"{index + 200:08x}-0000-4000-8000-{index + 200:012x}",
            "lease_id": lease_id,
            "epoch": str(index + 1),
        }
        runtime = coordinator.create(LeaseV1.model_validate(lease_raw))
        cancel_raw = {
            **_cancel(f"{index + 300:08x}-0000-4000-8000-{index + 300:012x}"),
            "lease_id": lease_id,
            "epoch": str(index + 1),
        }
        cancellation = LeaseCancelV1.model_validate(cancel_raw)
        assert runtime.cancel(
            cancellation, cancel_raw, now + timedelta(milliseconds=index)
        ).accepted
        if index == 0:
            first_runtime = runtime
            first_cancel = cancellation
            first_raw = cancel_raw

    assert coordinator.tombstone_count == 64
    assert LeaseRuntimeCoordinator().tombstone_count == 64
    assert first_runtime is not None and first_cancel is not None and first_raw is not None
    assert first_runtime.cancel(first_cancel, first_raw, now).code == StableCode.LEASE_CLOSED


def test_runtime_coordinator_prunes_idle_tombstones(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    coordinator = LeaseRuntimeCoordinator()
    coordinator.session_teardown(SESSION_ID)
    runtime = coordinator.create(LeaseV1.model_validate(valid_messages["LeaseV1"]))
    now = datetime(2026, 1, 1, tzinfo=UTC)
    cancel_raw = _cancel()
    cancellation = LeaseCancelV1.model_validate(cancel_raw)
    assert runtime.cancel(cancellation, cancel_raw, now).code == StableCode.ACCEPTED
    assert coordinator.tombstone_count == 1

    LeaseRuntimeCoordinator().prune(now + timedelta(seconds=120))
    assert coordinator.tombstone_count == 0
    assert runtime.cancel(cancellation, cancel_raw, now).code == StableCode.LEASE_CLOSED


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
