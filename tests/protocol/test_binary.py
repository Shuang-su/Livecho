from __future__ import annotations

import pytest
from livecho_protocol.binary import (
    HEADER_LENGTH,
    PcmHeaderV1,
    PcmLeaseState,
    decode_header,
    encode_header,
)
from livecho_protocol.errors import ProtocolValidationError, StableCode
from livecho_protocol.scalars import UINT64_MAX

from tests.protocol.conftest import LEASE_ID


def _frame(header: PcmHeaderV1) -> bytearray:
    """Construct minimal synthetic bytes in memory; never persist or print them."""
    return bytearray(encode_header(header)) + bytearray(header.payload_length)


def test_header_is_exactly_56_bytes_and_round_trips_metadata() -> None:
    header = PcmHeaderV1(LEASE_ID, 1, 0, 0, 1, 2, True)
    encoded = encode_header(header)
    assert len(encoded) == HEADER_LENGTH == 56
    assert decode_header(_frame(header)) == header


def test_header_uint64_overflow_is_a_stable_structural_rejection() -> None:
    overflowing = UINT64_MAX + 1
    headers = (
        PcmHeaderV1(LEASE_ID, overflowing, 0, 0, 1, 2),
        PcmHeaderV1(LEASE_ID, 1, overflowing, 0, 1, 2),
        PcmHeaderV1(LEASE_ID, 1, 0, overflowing, 1, 2),
    )
    for header in headers:
        with pytest.raises(ProtocolValidationError) as invalid:
            encode_header(header)
        assert invalid.value.code == StableCode.BINARY_HEADER_INVALID


def test_invalid_flags_and_sizes_reject_without_budget_change() -> None:
    state = PcmLeaseState(lease_id=LEASE_ID, epoch=1, input_start_seq=0)
    frame = _frame(PcmHeaderV1(LEASE_ID, 1, 0, 0, 1, 2))
    frame[6] = 0x80
    assert state.accept(frame).code == StableCode.BINARY_HEADER_INVALID
    assert state.buffered_bytes == 0
    assert state.sequence.next_expected_seq == 0

    large = bytearray(32_057)
    assert state.accept(large).code == StableCode.BINARY_FRAME_TOO_LARGE
    assert state.buffered_bytes == 0


def test_pcm_pts_sequence_and_budget_are_transactional() -> None:
    state = PcmLeaseState(lease_id=LEASE_ID, epoch=1, input_start_seq=0, lease_budget=4)
    first = _frame(PcmHeaderV1(LEASE_ID, 1, 0, 10, 1, 2))
    assert state.accept(first).code == StableCode.ACCEPTED
    assert state.accept(first).code == StableCode.SEQ_DUPLICATE

    bad_pts = _frame(PcmHeaderV1(LEASE_ID, 1, 1, 9, 1, 2))
    assert state.accept(bad_pts).code == StableCode.AUDIO_PTS_INVALID
    assert state.sequence.next_expected_seq == 1
    assert state.buffered_bytes == 2

    second = _frame(PcmHeaderV1(LEASE_ID, 1, 1, 10, 1, 2))
    assert state.accept(second).code == StableCode.ACCEPTED
    overflow = _frame(PcmHeaderV1(LEASE_ID, 1, 2, 11, 1, 2))
    assert state.accept(overflow).code == StableCode.AUDIO_BUDGET_EXCEEDED
    assert state.sequence.next_expected_seq == 2
    assert state.buffered_bytes == 4
    state.clear()
    assert state.buffered_bytes == 0
    assert state.sequence.next_expected_seq == 0
    assert state.accept(first).code == StableCode.LEASE_CLOSED


def test_end_of_segment_releases_pcm_without_resetting_ordering() -> None:
    state = PcmLeaseState(lease_id=LEASE_ID, epoch=1, input_start_seq=0, lease_budget=4)
    first = _frame(PcmHeaderV1(LEASE_ID, 1, 0, 10, 1, 2))
    end = _frame(PcmHeaderV1(LEASE_ID, 1, 1, 11, 1, 2, True))
    next_segment = _frame(PcmHeaderV1(LEASE_ID, 1, 2, 12, 1, 2))

    assert state.accept(first).code == StableCode.ACCEPTED
    assert state.buffered_bytes == 2
    assert state.accept(end).code == StableCode.ACCEPTED
    assert state.buffered_bytes == 0
    assert state.sequence.next_expected_seq == 2
    assert state.accept(next_segment).code == StableCode.ACCEPTED
    assert state.buffered_bytes == 2
