from __future__ import annotations

from typing import Any

import pytest
from livecho_backend.audio.contracts import (
    CANONICAL,
    AudioError,
    Binding,
    Chunk,
    InputOrder,
    SourceFormat,
)
from pydantic import ValidationError


def binding(source_format: SourceFormat = CANONICAL) -> Binding:
    return Binding(
        room_id="synthetic-room",
        session_id="session-1",
        attempt_id="attempt-1",
        origin="synthetic",
        source_format=source_format,
    )


@pytest.mark.parametrize("rate,channels,size", [(16000, 1, 640), (48000, 2, 3840)])
def test_only_exact_formats(rate: int, channels: int, size: int) -> None:
    source_format = SourceFormat.model_validate(
        {
            "encoding": "pcm_s16le",
            "sample_rate_hz": rate,
            "channels": channels,
        }
    )
    assert source_format.frame_bytes == size
    order = InputOrder(binding(source_format))
    for index in range(10):
        chunk = Chunk(
            chunk_index=index,
            start_sample=index * source_format.frame_samples,
            sample_count=source_format.frame_samples,
            source_format=source_format,
        )
        assert order.accept(chunk) == index * 20


@pytest.mark.parametrize(
    "change",
    [
        {"sample_rate_hz": 44100},
        {"channels": 2},
        {"encoding": "wav"},
        {"url": "forbidden"},
        {"sample_rate_hz": "16000"},
        {"channels": True},
    ],
)
def test_format_rejects_coercion_and_extensions(change: dict[str, Any]) -> None:
    value = CANONICAL.model_dump()
    value.update(change)
    with pytest.raises(ValidationError):
        SourceFormat.model_validate(value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("sample_count", 319),
        ("sample_count", 321),
        ("sample_count", 0),
        ("sample_count", -1),
        ("sample_count", float("nan")),
        ("start_sample", -1),
        ("chunk_index", True),
        ("duration", 20),
    ],
)
def test_malformed_frame_rejected(field: str, value: object) -> None:
    data = dict(chunk_index=0, start_sample=0, sample_count=320, source_format=CANONICAL)
    data[field] = value
    with pytest.raises(ValidationError):
        Chunk.model_validate(data)


def test_sequence_rejection_does_not_advance_local_clock() -> None:
    order = InputOrder(binding())
    good = Chunk(chunk_index=0, start_sample=0, sample_count=320, source_format=CANONICAL)
    assert order.accept(good) == 0
    for malformed in (
        good,
        good.model_copy(update={"chunk_index": 2, "start_sample": 320}),
        good.model_copy(update={"chunk_index": 1, "start_sample": 640}),
    ):
        with pytest.raises(AudioError):
            order.accept(malformed)
        assert (order.next_index, order.next_sample) == (1, 320)


def test_closed_binding_rejects_runtime_configuration() -> None:
    for name in ("url", "path", "command", "container", "credentials", "metadata"):
        data = binding().model_dump()
        data[name] = "not-admitted"
        with pytest.raises(ValidationError):
            Binding.model_validate(data)
