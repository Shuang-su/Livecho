"""Closed local contracts. Local indices are never wire sequence or epoch fields."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

FRAME_SAMPLES = 320
FRAME_MS = 20
FRAME_BYTES = 640
MAX_SAMPLES = 96_000
CONTEXT_SAMPLES = 12_800


class Reason(StrEnum):
    BUDGET_UNVERIFIED = "audio_budget_unverified"
    BUDGET_EXCEEDED = "audio_budget_exceeded"
    METADATA_INVALID = "audio_metadata_invalid"
    ADMISSION_CLOSED = "audio_admission_closed"
    HANDLE_INVALID = "audio_handle_invalid"
    CONSUMER_SLOW = "consumer_slow"
    INPUT_STALLED = "input_stalled"
    DECODER_EXIT = "decoder_exit"
    DECODER_PIPE = "decoder_pipe"
    DECODER_START_TIMEOUT = "decoder_start_timeout"
    DECODER_REAP_FAILED = "decoder_reap_failed"
    WATCHDOG_EXIT = "watchdog_exit"
    CANCELLED = "cancelled"
    DISABLED = "disabled"
    DENYLISTED = "denylisted"
    SESSION_END = "session_end"
    LEASE_END = "lease_end"
    SHUTDOWN = "shutdown"
    UNMEASURABLE = "unmeasurable_input"


class AudioError(Exception):
    """The sole public diagnostic contains an allowlisted code, never source text."""

    def __init__(self, reason: Reason) -> None:
        self.reason = reason
        super().__init__(reason.value)


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)


class SourceFormat(ClosedModel):
    encoding: Literal["pcm_s16le"]
    sample_rate_hz: Literal[16000, 48000]
    channels: Literal[1, 2]

    @field_validator("sample_rate_hz", "channels", mode="before")
    @classmethod
    def exact_integer(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("audio_metadata_invalid")
        return value

    @model_validator(mode="after")
    def supported_pair(self) -> SourceFormat:
        if (self.sample_rate_hz, self.channels) not in ((16000, 1), (48000, 2)):
            raise ValueError("audio_metadata_invalid")
        return self

    @property
    def frame_samples(self) -> int:
        return self.sample_rate_hz // 50

    @property
    def frame_bytes(self) -> int:
        return self.frame_samples * self.channels * 2


CANONICAL = SourceFormat(encoding="pcm_s16le", sample_rate_hz=16000, channels=1)


class Binding(ClosedModel):
    room_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._:-]*$")
    session_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._:-]*$")
    attempt_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._:-]*$")
    origin: Literal["synthetic"]
    source_format: SourceFormat


class Chunk(ClosedModel):
    chunk_index: int = Field(ge=0)
    start_sample: int = Field(ge=0)
    sample_count: int = Field(gt=0)
    source_format: SourceFormat

    @model_validator(mode="after")
    def complete_frame(self) -> Chunk:
        if self.sample_count != self.source_format.frame_samples:
            raise ValueError("audio_metadata_invalid")
        return self


class EndOfInput(ClosedModel):
    kind: Literal["eof"] = "eof"


EOF = EndOfInput()


class BoundedWriter(Protocol):
    """Revocable writable view: no escaping Python buffer-protocol aliases."""

    @property
    def size(self) -> int: ...

    def write_sample(self, index: int, sample: int) -> None: ...


class MemoryAudioSource(Protocol):
    async def open(self, binding: Binding) -> None: ...

    async def read(self, target: BoundedWriter) -> Chunk | EndOfInput: ...

    async def close(self) -> None: ...


class SourceFactory(Protocol):
    @property
    def restartable(self) -> bool: ...

    def create(self) -> MemoryAudioSource: ...


class Segment(ClosedModel):
    binding: Binding
    segment_index: int = Field(ge=0)
    start_pts: int = Field(ge=0)
    new_start_pts: int = Field(ge=0)
    end_pts: int = Field(gt=0)
    sample_count: int = Field(gt=0, le=MAX_SAMPLES)
    left_context_samples: int = Field(ge=0, le=CONTEXT_SAMPLES)
    close_reason: Literal["silence", "max_duration", "eof"]
    audio_format: SourceFormat = CANONICAL

    @model_validator(mode="after")
    def ranges(self) -> Segment:
        if (
            self.audio_format != CANONICAL
            or not self.start_pts <= self.new_start_pts < self.end_pts
            or (self.end_pts - self.start_pts) * 16 != self.sample_count
            or (self.new_start_pts - self.start_pts) * 16 != self.left_context_samples
            or self.left_context_samples not in (0, CONTEXT_SAMPLES)
        ):
            raise ValueError("audio_metadata_invalid")
        return self


class InputOrder:
    def __init__(self, binding: Binding) -> None:
        self.binding = binding
        self.next_index = 0
        self.next_sample = 0

    def accept(self, chunk: Chunk) -> int:
        # Model construction/copy helpers can bypass Pydantic validation; producer
        # objects must still pass the closed contract at this admission boundary.
        try:
            if type(chunk) is not Chunk:
                raise AudioError(Reason.METADATA_INVALID)
            chunk = Chunk.model_validate(chunk.model_dump())
        except ValidationError:
            raise AudioError(Reason.METADATA_INVALID) from None
        if (
            chunk.source_format != self.binding.source_format
            or chunk.chunk_index != self.next_index
            or chunk.start_sample != self.next_sample
        ):
            raise AudioError(Reason.METADATA_INVALID)
        pts = self.next_sample * 1000 // self.binding.source_format.sample_rate_hz
        self.next_index += 1
        self.next_sample += chunk.sample_count
        return pts
