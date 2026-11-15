"""Fresh synthetic generation, only after the same host admission as the decoder."""

from __future__ import annotations

from .contracts import EOF, AudioError, Binding, BoundedWriter, Chunk, EndOfInput, Reason
from .preflight import RuntimePermit


class SyntheticSource:
    """A finite locally generated signal; no fixtures, encoded body, file, or locator."""

    def __init__(self, permit: RuntimePermit, frames: int) -> None:
        permit.require()
        if type(frames) is not int or not 0 <= frames <= 1500:
            raise AudioError(Reason.METADATA_INVALID)
        self._permit = permit
        self._frames = frames
        self._binding: Binding | None = None
        self._index = 0
        self._closed = False

    async def open(self, binding: Binding) -> None:
        self._permit.require()
        if self._binding is not None or self._closed:
            raise AudioError(Reason.ADMISSION_CLOSED)
        self._binding = binding

    async def read(self, target: BoundedWriter) -> Chunk | EndOfInput:
        if self._binding is None or self._closed:
            raise AudioError(Reason.ADMISSION_CLOSED)
        if self._index == self._frames:
            return EOF
        source_format = self._binding.source_format
        if target.size != source_format.frame_bytes:
            raise AudioError(Reason.METADATA_INVALID)
        count = source_format.frame_samples
        start = self._index * count
        # Generate a modest square wave directly into the already reserved writer.
        for index in range(count):
            sample = 2048 if ((start + index) * 880 // source_format.sample_rate_hz) % 2 else -2048
            for channel in range(source_format.channels):
                target.write_sample(index * source_format.channels + channel, sample)
        result = Chunk(
            chunk_index=self._index,
            start_sample=start,
            sample_count=count,
            source_format=source_format,
        )
        self._index += 1
        return result

    async def close(self) -> None:
        self._closed = True
        self._binding = None


class SyntheticFactory:
    restartable = True

    def __init__(self, permit: RuntimePermit, frames: int) -> None:
        self._permit = permit
        self._frames = frames

    def create(self) -> SyntheticSource:
        return SyntheticSource(self._permit, self._frames)
