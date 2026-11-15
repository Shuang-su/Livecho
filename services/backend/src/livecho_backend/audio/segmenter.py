"""Sample-clock segmentation decisions. This module does not allocate or retain PCM."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable

from .contracts import (
    CONTEXT_SAMPLES,
    FRAME_SAMPLES,
    MAX_SAMPLES,
    AudioError,
    Binding,
    Reason,
    Segment,
)


def energy_is_speech(sum_squares: int, sample_count: int = FRAME_SAMPLES) -> bool:
    """Exact threshold; Python integers cannot overflow, and there is no float rounding."""
    if (
        type(sum_squares) is not int
        or sample_count != FRAME_SAMPLES
        or not 0 <= sum_squares <= FRAME_SAMPLES * 32768**2
    ):
        raise AudioError(Reason.METADATA_INVALID)
    return sum_squares * 10000 >= FRAME_SAMPLES * 32768**2


def detect_speech(read_sample: Callable[[int], int]) -> bool:
    total = 0
    for index in range(FRAME_SAMPLES):
        sample = read_sample(index)
        if type(sample) is not int or not -32768 <= sample <= 32767:
            raise AudioError(Reason.METADATA_INVALID)
        total += sample * sample
    return energy_is_speech(total)


class Segmenter:
    """Metadata owner paired with a separately charged memory ring by the pipeline."""

    def __init__(self, binding: Binding) -> None:
        self.binding = binding
        self.next_sample = 0
        self.next_segment = 0
        self._start: int | None = None
        self._new_start = 0
        self._left = 0
        self._speech_run = 0
        self._silence_run = 0
        self._new_speech = False
        self._floor = 0
        self._onset_start = 0
        self._closed = False
        self.trimmed_silence_samples = 0
        self.below_onset_samples = 0
        self._pending: deque[tuple[int, bool]] = deque()

    @property
    def retain_from(self) -> int:
        if self._start is not None:
            return self._start
        # Preserve 200 ms preceding the onset candidate, plus its 1-2 trigger frames.
        anchor = self._onset_start if self._speech_run else self.next_sample
        return max(self._floor, anchor - 3200)

    def push(self, start_sample: int, *, speech: bool) -> Segment | None:
        if self._closed or start_sample != self.next_sample or type(speech) is not bool:
            raise AudioError(Reason.METADATA_INVALID)
        self.next_sample += FRAME_SAMPLES
        if self._start is None:
            self._pending.append((start_sample, speech))
            if speech:
                if self._speech_run == 0:
                    self._onset_start = start_sample
                self._speech_run += 1
                if self._speech_run == 3:
                    self._start = max(self._floor, self._onset_start - 3200)
                    self._new_start = self._start
                    self._new_speech = True
                    self._silence_run = 0
                    self._pending.clear()
            else:
                self.below_onset_samples += self._speech_run * FRAME_SAMPLES
                self._speech_run = 0
            while self._pending and self._pending[0][0] < self.retain_from:
                _, was_speech = self._pending.popleft()
                if not was_speech:
                    self.trimmed_silence_samples += FRAME_SAMPLES
            return None
        if speech:
            self._new_speech = True
            self._silence_run = 0
        else:
            self._silence_run += 1
        if self._silence_run == 25:
            return self._finish("silence")
        if self.next_sample - self._start == MAX_SAMPLES:
            return self._finish("max_duration")
        return None

    def _finish(self, reason: str) -> Segment | None:
        assert self._start is not None
        result = None
        if self._new_speech:
            result = Segment(
                binding=self.binding,
                segment_index=self.next_segment,
                start_pts=self._start // 16,
                new_start_pts=self._new_start // 16,
                end_pts=self.next_sample // 16,
                sample_count=self.next_sample - self._start,
                left_context_samples=self._left,
                close_reason=reason,  # type: ignore[arg-type]
            )
            self.next_segment += 1
        continuous = reason == "max_duration" and self._silence_run == 0
        self._floor = self.next_sample
        self._start = self.next_sample - CONTEXT_SAMPLES if continuous else None
        self._new_start = self.next_sample
        self._left = CONTEXT_SAMPLES if continuous else 0
        self._speech_run = 0
        self._silence_run = 0
        self._new_speech = False
        return result

    def eof(self) -> Segment | None:
        if self._closed:
            return None
        result = self._finish("eof") if self._start is not None else None
        self.below_onset_samples += self._speech_run * FRAME_SAMPLES
        self.clear()
        return result

    def clear(self) -> None:
        self._closed = True
        self._start = None
        self._left = 0
        self._speech_run = 0
        self._silence_run = 0
        self._new_speech = False
        self._floor = self.next_sample
        self.trimmed_silence_samples += sum(
            FRAME_SAMPLES for _, speech in self._pending if not speech
        )
        self._pending.clear()
