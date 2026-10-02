from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from livecho_backend.audio.contracts import AudioError, Reason
from livecho_backend.audio.ledger import (
    DECODER_LIMIT,
    NONCANONICAL_LIMIT,
    PARTITIONS,
    Interval,
    Ledger,
    Owner,
    ProcessAdmission,
    ProcessBytes,
)


def test_all_partitions_fill_exact_960000_without_allocating_audio() -> None:
    ledger = Ledger()
    reservations = [
        ledger.reserve(owner, size, Interval(0, 30000)) for owner, size in PARTITIONS.items()
    ]
    assert ledger.usage.canonical == 960000
    with pytest.raises(AudioError, match="audio_budget_exceeded"):
        ledger.reserve(Owner.RING, 1, Interval(0, 20))
    assert ledger.usage.canonical == 960000
    for reservation in reservations:
        reservation.release()
    assert ledger.usage.canonical == 0
    assert ledger.usage.peak_canonical == 960000


def test_borrow_owns_same_allocation_copy_reserves_again_and_clear_revokes() -> None:
    ledger = Ledger()
    original = ledger.reserve(Owner.RING, 640, Interval(0, 20))
    borrowed = original.borrow()
    duplicate = ledger.reserve(Owner.SEGMENT, 640, Interval(0, 20))
    assert ledger.usage.canonical == 1280
    original.release()
    assert borrowed.valid
    assert ledger.usage.canonical == 1280
    borrowed.release()
    assert ledger.usage.canonical == 640
    ledger.clear()
    assert not duplicate.valid
    with pytest.raises(AudioError, match="audio_handle_invalid"):
        duplicate.borrow()
    duplicate.release()
    ledger.clear()
    assert ledger.usage.all_audio == 0


def test_clear_calls_every_memory_owner_before_returning() -> None:
    ledger = Ledger()
    calls: list[str] = []
    reservation = ledger.reserve(Owner.RING, 640, Interval(0, 20))
    reservation.on_clear(lambda: calls.append("cleared"))
    ledger.clear()
    ledger.clear()
    assert calls == ["cleared"]
    with pytest.raises(AudioError, match="audio_admission_closed"):
        ledger.reserve(Owner.RING, 640, Interval(0, 20))


def test_media_window_uses_union_envelope_not_sum_or_bytes() -> None:
    ledger = Ledger()
    first = ledger.reserve(Owner.RING, 1, Interval(0, 20))
    second = ledger.reserve(Owner.OTHER, 1, Interval(29980, 30000))
    assert ledger.usage.media_span_ms == 30000
    with pytest.raises(AudioError):
        ledger.reserve(Owner.OTHER, 1, Interval(30000, 30020))
    with pytest.raises(AudioError):
        second.move_interval(Interval(30000, 30020))
    assert ledger.usage.media_span_ms == 30000
    first.release()
    second.move_interval(Interval(30000, 30020))
    assert ledger.usage.media_span_ms == 20


@pytest.mark.parametrize("decoder,limit", [(False, NONCANONICAL_LIMIT), (True, DECODER_LIMIT)])
def test_noncanonical_process_partitions(decoder: bool, limit: int) -> None:
    ledger = Ledger(decoder=decoder)
    ledger.reserve(Owner.DECODER, limit, Interval(0, 20), canonical=False)
    with pytest.raises(AudioError):
        ledger.reserve(Owner.SOURCE, 1, Interval(0, 20), canonical=False)
    assert ledger.usage.all_audio == limit


def test_reservation_is_synchronized_before_allocation() -> None:
    ledger = Ledger()

    def reserve(_: int) -> bool:
        try:
            ledger.reserve(Owner.SEGMENT, 192000, Interval(0, 6000))
            return True
        except AudioError as error:
            assert error.reason == Reason.BUDGET_EXCEEDED
            return False

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(reserve, range(16)))
    assert sum(results) == 1
    assert ledger.usage.canonical == 192000


def test_no_second_room_or_replacement_until_reaped() -> None:
    admission = ProcessAdmission()
    first, second = object(), object()
    admission.acquire(first)
    admission.release(first, reaped=False)
    admission.release(second, reaped=True)
    with pytest.raises(AudioError):
        admission.acquire(second)
    admission.release(first, reaped=True)
    admission.acquire(second)


def test_all_process_copies_share_exact_16777216_limit() -> None:
    process = ProcessBytes()
    release = process.reserve(16_777_216)
    with pytest.raises(AudioError, match="audio_budget_exceeded"):
        process.reserve(1)
    assert process.current == 16_777_216
    release()
    release()
    assert process.current == 0
    assert process.peak == 16_777_216


@pytest.mark.parametrize("start,end", [(0, 0), (-1, 20), (20, 0), (0, float("nan"))])
def test_unknown_or_malformed_duration_never_reserved(start: int, end: int) -> None:
    with pytest.raises(AudioError):
        Interval(start, end)
