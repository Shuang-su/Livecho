"""Accepted-v1 metadata integration, without constructing an audio payload.

The header parser is replaced with already validated metadata in these tests. Existing
Issue #3 codec/golden tests remain unchanged and run separately in make verify.
"""

from __future__ import annotations

import pytest
from livecho_protocol import binary
from livecho_protocol.binary import PcmHeaderV1, PcmLeaseState, encode_header
from livecho_protocol.errors import StableCode

LEASE = "00000000-0000-4000-8000-000000000001"


def test_original_pts_overlap_end_flag_and_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    lease = PcmLeaseState(lease_id=LEASE, epoch=1, input_start_seq=0)
    starts = [0, 1000, 2000, 3000, 4000, 5000, 5200, 6200, 7200, 8200, 9200, 10200]
    for seq, pts in enumerate(starts):
        header = PcmHeaderV1(LEASE, 1, seq, pts, 16000, 32000, seq in (5, 11))
        assert len(encode_header(header)) == 56  # Metadata only, not a PCM frame.
        monkeypatch.setattr(binary, "decode_header", lambda frame, header=header: header)
        assert lease.accept(b"", session_buffered_bytes=300000).code == StableCode.ACCEPTED
        assert (
            lease.buffered_bytes == (seq % 6 + 1) * 32000
            if seq % 6 != 5
            else lease.buffered_bytes == 0
        )
    assert lease.sequence.next_expected_seq == 12
    assert lease.buffered_bytes == 0


def test_short_last_frame_followed_by_nonrewinding_onset(monkeypatch: pytest.MonkeyPatch) -> None:
    lease = PcmLeaseState(lease_id=LEASE, epoch=1, input_start_seq=0)
    for seq, pts, samples in [(0, 0, 8960), (1, 560, 960)]:
        header = PcmHeaderV1(LEASE, 1, seq, pts, samples, samples * 2, True)
        monkeypatch.setattr(binary, "decode_header", lambda frame, header=header: header)
        assert lease.accept(b"").code == StableCode.ACCEPTED
        assert lease.buffered_bytes == 0
    bad = PcmHeaderV1(LEASE, 1, 2, 540, 320, 640, True)
    monkeypatch.setattr(binary, "decode_header", lambda _: bad)
    assert lease.accept(b"").code == StableCode.AUDIO_PTS_INVALID
    assert lease.sequence.next_expected_seq == 2
    assert lease.last_pts_ms == 560
    lease.clear()
    assert lease.accept(b"").code == StableCode.LEASE_CLOSED
