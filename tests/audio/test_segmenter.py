from __future__ import annotations

import pytest
from livecho_backend.audio.contracts import AudioError, Segment
from livecho_backend.audio.segmenter import Segmenter, energy_is_speech

from .test_contracts import binding


def feed(segmenter: Segmenter, count: int, speech: bool) -> list[Segment]:
    results = []
    for _ in range(count):
        segment = segmenter.push(segmenter.next_sample, speech=speech)
        if segment is not None:
            results.append(segment)
    return results


def test_energy_threshold_integer_equality_without_generating_samples() -> None:
    # These are scalar control values, not stored/derived audio samples or hashes.
    numerator = 320 * 32768**2
    assert not energy_is_speech(numerator // 10000)
    assert energy_is_speech((numerator + 9999) // 10000)
    with pytest.raises(AudioError):
        energy_is_speech(-1)


@pytest.mark.parametrize("frames,emits", [(1, False), (2, False), (3, True)])
def test_onset_exactly_three_and_eof(frames: int, emits: bool) -> None:
    segmenter = Segmenter(binding())
    assert feed(segmenter, frames, True) == []
    result = segmenter.eof()
    assert (result is not None) == emits
    if result is not None:
        assert (result.start_pts, result.end_pts, result.close_reason) == (0, 60, "eof")
    else:
        assert segmenter.below_onset_samples == frames * 320
    assert segmenter.eof() is None


@pytest.mark.parametrize("silence,expected", [(24, []), (25, [560]), (26, [560])])
def test_480_500_520_ms_silence(silence: int, expected: list[int]) -> None:
    segmenter = Segmenter(binding())
    feed(segmenter, 3, True)
    results = feed(segmenter, silence, False)
    assert [segment.end_pts for segment in results] == expected
    assert all(segment.close_reason == "silence" for segment in results)


def test_returning_speech_before_500ms_resets_silence() -> None:
    segmenter = Segmenter(binding())
    feed(segmenter, 3, True)
    assert feed(segmenter, 24, False) == []
    feed(segmenter, 1, True)
    assert feed(segmenter, 24, False) == []
    result = feed(segmenter, 1, False)[0]
    assert (result.start_pts, result.end_pts) == (0, 1060)


def test_preroll_200ms_before_trigger_and_clamps_to_attempt() -> None:
    segmenter = Segmenter(binding())
    feed(segmenter, 30, False)
    feed(segmenter, 3, True)
    segment = segmenter.eof()
    assert segment is not None
    assert (segment.start_pts, segment.new_start_pts, segment.end_pts) == (400, 400, 660)


def test_exact_6s_then_800ms_context_and_5200ms_new_audio() -> None:
    segmenter = Segmenter(binding())
    assert feed(segmenter, 299, True) == []
    first = feed(segmenter, 1, True)[0]
    assert (first.start_pts, first.end_pts, first.sample_count) == (0, 6000, 96000)
    assert segmenter.retain_from == 5200 * 16
    assert feed(segmenter, 259, True) == []
    second = feed(segmenter, 1, True)[0]
    assert (second.start_pts, second.new_start_pts, second.end_pts) == (5200, 6000, 11200)
    assert (second.left_context_samples, second.sample_count) == (12800, 96000)
    assert segmenter.eof() is None


def test_context_without_new_speech_is_not_emitted() -> None:
    segmenter = Segmenter(binding())
    feed(segmenter, 300, True)
    assert feed(segmenter, 25, False) == []
    assert segmenter.eof() is None


def test_short_silence_closed_segment_cannot_rewind_preroll() -> None:
    segmenter = Segmenter(binding())
    feed(segmenter, 3, True)
    first = feed(segmenter, 25, False)[0]
    assert first.end_pts == 560
    feed(segmenter, 3, True)
    second = segmenter.eof()
    assert second is not None
    assert (second.start_pts, second.new_start_pts, second.end_pts) == (560, 560, 620)
    assert second.left_context_samples == 0


def test_silence_and_maximum_equality_close_once_without_context() -> None:
    segmenter = Segmenter(binding())
    feed(segmenter, 275, True)
    result = feed(segmenter, 25, False)
    assert len(result) == 1
    assert result[0].end_pts == 6000
    assert result[0].close_reason == "silence"
    assert segmenter.retain_from == 96000


def test_silence_does_not_accumulate_ring_and_clear_blocks_callbacks() -> None:
    segmenter = Segmenter(binding())
    feed(segmenter, 5000, False)
    assert segmenter.next_sample - segmenter.retain_from == 3200
    segmenter.clear()
    with pytest.raises(AudioError):
        segmenter.push(segmenter.next_sample, speech=True)
