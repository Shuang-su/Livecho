"""Drive the real owner loop with metadata-only decoder, source, and storage doubles.

No double contains bytes, samples, an encoded waveform, or a sample-derived digest.
These checks deliberately do not establish audio conversion or host safety.
"""

from __future__ import annotations

import asyncio
import builtins
import io
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from livecho_backend.audio import pipeline
from livecho_backend.audio.contracts import EOF, AudioError, Binding, Chunk, Reason
from livecho_backend.audio.ledger import PROCESS_BYTES, Interval, Ledger, Owner
from livecho_backend.audio.lifecycle import State
from livecho_backend.audio.memory import SegmentHandle

from .test_contracts import binding


class MetadataBuffer:
    live_count = 0

    def __init__(
        self,
        permit: Any,
        ledger: Ledger,
        owner: Owner,
        size: int,
        interval: Interval,
        *,
        canonical: bool = True,
    ) -> None:
        self.size = size
        self.reservation = ledger.reserve(owner, size, interval, canonical=canonical)
        self.reservation.on_clear(self.clear)
        self.live = True
        self.transferred = 0
        MetadataBuffer.live_count += 1

    def transfer(self, destination: MetadataBuffer, offset: int = 0) -> None:
        assert self.live and destination.live
        assert 0 <= offset <= destination.size - self.size
        destination.transferred += self.size

    def clear(self) -> None:
        if self.live:
            self.live = False
            MetadataBuffer.live_count -= 1
            self.reservation.release()

    def read_sample(self, index: int) -> int:
        raise AssertionError("metadata-only test must never read a sample")


class MetadataWriter:
    def __init__(self, buffer: MetadataBuffer, allowed: Any) -> None:
        self.size = buffer.size
        self.complete = False
        self.written_samples = 0
        self.revoked = False

    def revoke(self) -> None:
        self.revoked = True


class ControlIO:
    def __init__(self, total_frames: int) -> None:
        self.total_frames = total_frames
        self.written = 0
        self.read = 0
        self.input_closed = False
        self.reaped = False
        self.opens = 0
        self.source_closes = 0
        self.malformed = False
        self.fail_read = False
        self.reap_success = True
        self.late_exit = False

    def read_into(self, fd: int, buffer: MetadataBuffer, offset: int) -> int:
        if self.fail_read:
            raise AudioError(Reason.DECODER_PIPE)
        if self.read < self.written:
            self.read += 1
            return 640
        return 0 if self.input_closed else -1

    def write_from(self, fd: int, buffer: MetadataBuffer, offset: int) -> int:
        self.written += 1
        return buffer.size


class MetadataSource:
    def __init__(self, control: ControlIO) -> None:
        self.control = control
        self.binding: Binding | None = None
        self.index = 0

    async def open(self, value: Binding) -> None:
        self.binding = value
        self.control.opens += 1

    async def read(self, target: MetadataWriter) -> Any:
        assert self.binding is not None
        assert not target.revoked
        if self.index == self.control.total_frames:
            return EOF
        source_format = self.binding.source_format
        target.complete = True
        result = Chunk(
            chunk_index=self.index + (1 if self.control.malformed else 0),
            start_sample=self.index * source_format.frame_samples,
            sample_count=source_format.frame_samples,
            source_format=source_format,
        )
        self.index += 1
        return result

    async def close(self) -> None:
        self.control.source_closes += 1


def install_doubles(monkeypatch: pytest.MonkeyPatch, control: ControlIO) -> Any:
    class MetadataDecoder:
        failure_reason = None

        def __init__(self, permit: Any, source_format: Any) -> None:
            self.input_fd = 1
            self.output_fd = 2

        def start(self) -> None:
            control.written = control.read = 0
            control.input_closed = False

        def ready(self) -> bool:
            return True

        def check(self) -> None:
            pass

        def completed(self) -> bool:
            if control.late_exit:
                raise AudioError(Reason.DECODER_EXIT)
            return True

        def finish_input(self) -> None:
            control.input_closed = True

        def close(self) -> bool:
            control.reaped = control.reap_success
            return control.reap_success

    monkeypatch.setattr(pipeline, "OwnedBuffer", MetadataBuffer)
    monkeypatch.setattr(pipeline, "WritableView", MetadataWriter)
    monkeypatch.setattr(pipeline, "DecoderSupervisor", MetadataDecoder)
    monkeypatch.setattr(pipeline, "read_owned", control.read_into)
    monkeypatch.setattr(pipeline, "write_owned", control.write_from)
    monkeypatch.setattr(pipeline, "detect_speech", lambda _: True)
    # The token is a control double, never supplied to the real OwnedBuffer or decoder.
    permit = SimpleNamespace(
        require=lambda: None,
        build=SimpleNamespace(inventory=SimpleNamespace(parent_noncanonical_bytes=8192)),
    )
    return permit


def create_pipeline(monkeypatch: pytest.MonkeyPatch, control: ControlIO) -> pipeline.AudioPipeline:
    permit = install_doubles(monkeypatch, control)
    factory = SimpleNamespace(restartable=False, create=lambda: MetadataSource(control))
    return pipeline.AudioPipeline(permit, binding(), factory, lambda: True, lambda: None)


@pytest.mark.parametrize(
    "frames,expected",
    [
        (0, []),
        (2, []),
        (3, [(0, 0, 60)]),
        (300, [(0, 0, 6000)]),
        (320, [(0, 0, 6000), (5200, 6000, 6400)]),
    ],
)
def test_owner_loop_eof_overlap_and_every_owner_cleared(
    monkeypatch: pytest.MonkeyPatch, frames: int, expected: list[tuple[int, int, int]]
) -> None:
    control = ControlIO(frames)
    owner = create_pipeline(monkeypatch, control)

    async def scenario() -> list[tuple[int, int, int]]:
        await owner.start()
        segments = []
        while (handle := await owner.next_segment()) is not None:
            metadata = handle.metadata
            segments.append((metadata.start_pts, metadata.new_start_pts, metadata.end_pts))
            handle.release()
        return segments

    assert asyncio.run(scenario()) == expected
    assert owner.lifecycle.state == State.STOPPED
    assert owner.ledger.usage.all_audio == 0
    assert MetadataBuffer.live_count == 0
    assert control.reaped
    assert control.source_closes == 1
    if frames == 2:
        assert owner.lifecycle.metrics.below_onset_ms == 40


@pytest.mark.parametrize("failure", ["metadata", "decoder_pipe"])
def test_owner_failure_never_reports_success_and_clears(
    monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    control = ControlIO(300)
    control.malformed = failure == "metadata"
    control.fail_read = failure == "decoder_pipe"
    owner = create_pipeline(monkeypatch, control)

    async def scenario() -> None:
        await owner.start()
        with pytest.raises(AudioError):
            await owner.next_segment()

    asyncio.run(scenario())
    assert owner.lifecycle.state == State.FAILED
    assert owner.ledger.usage.all_audio == 0
    assert MetadataBuffer.live_count == 0
    assert control.reaped
    if failure == "metadata":
        assert owner.lifecycle.metrics.unmeasurable_input == 1


def test_late_decoder_exit_after_exact_output_does_not_publish_eof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = ControlIO(3)
    control.late_exit = True
    owner = create_pipeline(monkeypatch, control)

    async def scenario() -> None:
        await owner.start()
        with pytest.raises(AudioError, match="decoder_exit"):
            await owner.next_segment()

    asyncio.run(scenario())
    assert owner.lifecycle.state == State.FAILED
    assert control.reaped
    assert owner.ledger.usage.all_audio == 0


def test_consumer_holds_handle_owner_fails_at_pause_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = ControlIO(320)
    owner = create_pipeline(monkeypatch, control)

    async def scenario() -> None:
        await owner.start()
        handle = await owner.next_segment()
        assert handle is not None
        await asyncio.sleep(0.55)
        with pytest.raises(AudioError, match="consumer_slow"):
            await owner.next_segment()
        assert handle.released

    asyncio.run(scenario())
    assert owner.ledger.usage.all_audio == 0
    assert MetadataBuffer.live_count == 0

    assert owner.lifecycle.metrics.dropped_ms == {Reason.CONSUMER_SLOW: 6000}


def test_cancel_while_handle_is_out_invalidates_and_reaps(monkeypatch: pytest.MonkeyPatch) -> None:
    control = ControlIO(320)
    owner = create_pipeline(monkeypatch, control)

    async def scenario() -> None:
        await owner.start()
        handle = await owner.next_segment()
        assert handle is not None
        await owner.close(Reason.DISABLED)
        await owner.close(Reason.DISABLED)
        assert handle.released
        with pytest.raises(AudioError, match="audio_handle_invalid"):
            handle.read_sample(0)

    asyncio.run(scenario())
    assert MetadataBuffer.live_count == 0
    assert control.reaped


def test_cancel_before_owner_first_runs_releases_admission(monkeypatch: pytest.MonkeyPatch) -> None:
    control = ControlIO(0)
    first = create_pipeline(monkeypatch, control)
    second = create_pipeline(monkeypatch, control)

    async def scenario() -> None:
        await first.start()
        await first.close()
        assert first.lifecycle.state == State.STOPPED
        await second.start()
        assert await second.next_segment() is None

    asyncio.run(scenario())


def test_concurrent_close_joins_cleanup_instead_of_cancelling_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = ControlIO(0)
    owner = create_pipeline(monkeypatch, control)
    entered = asyncio.Event()

    async def resistant_open(self: MetadataSource, value: Binding) -> None:
        self.binding = value
        entered.set()
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            await asyncio.sleep(0.2)

    monkeypatch.setattr(MetadataSource, "open", resistant_open)

    async def scenario() -> None:
        await owner.start()
        await entered.wait()
        first = asyncio.create_task(owner.close())
        await asyncio.sleep(0.01)
        await owner.close()
        await first

    asyncio.run(scenario())
    assert control.reaped
    assert owner.ledger.usage.all_audio == 0
    assert MetadataBuffer.live_count == 0
    assert owner.lifecycle.state in (State.STOPPED, State.FAILED)


def test_open_and_read_share_first_output_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    control = ControlIO(3)
    owner = create_pipeline(monkeypatch, control)
    original_read = MetadataSource.read

    async def slow_open(self: MetadataSource, value: Binding) -> None:
        self.binding = value
        await asyncio.sleep(1.2)

    async def slow_read(self: MetadataSource, target: MetadataWriter) -> Any:
        await asyncio.sleep(1.2)
        return await original_read(self, target)

    monkeypatch.setattr(MetadataSource, "open", slow_open)
    monkeypatch.setattr(MetadataSource, "read", slow_read)

    async def scenario() -> None:
        started = time.monotonic()
        await owner.start()
        with pytest.raises(AudioError, match="decoder_start_timeout"):
            await owner.next_segment()
        assert time.monotonic() - started < 2.3

    asyncio.run(scenario())
    assert control.written == 0
    assert control.reaped
    assert MetadataBuffer.live_count == 0


def test_source_close_cancellation_still_finishes_every_cleanup_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = ControlIO(3)
    owner = create_pipeline(monkeypatch, control)

    async def cancelled_close(self: MetadataSource) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(MetadataSource, "close", cancelled_close)

    async def scenario() -> None:
        await owner.start()
        handle = await owner.next_segment()
        assert handle is not None
        handle.release()
        with pytest.raises(AudioError, match="audio_admission_closed"):
            await owner.next_segment()
        assert owner.lifecycle.state == State.FAILED
        assert owner.ledger.usage.all_audio == 0
        assert PROCESS_BYTES.current == 0
        replacement = create_pipeline(monkeypatch, ControlIO(0))
        await replacement.start()
        await replacement.close()

    asyncio.run(scenario())
    assert control.reaped
    assert MetadataBuffer.live_count == 0


@pytest.mark.parametrize("release", [True, False])
def test_reserve_exhaustion_pauses_without_allocating_and_is_bounded(
    monkeypatch: pytest.MonkeyPatch,
    release: bool,
) -> None:
    control = ControlIO(3)
    owner = create_pipeline(monkeypatch, control)
    reserved = owner.ledger.reserve(Owner.SCRATCH, 32000, Interval(0, 20))

    async def scenario() -> None:
        await owner.start()
        await asyncio.sleep(0.05)
        assert owner.lifecycle.state == State.BACKPRESSURED
        assert MetadataBuffer.live_count == 0
        if release:
            reserved.release()
            handle = await owner.next_segment()
            assert handle is not None
            handle.release()
            assert await owner.next_segment() is None
        else:
            with pytest.raises(AudioError, match="audio_budget_exceeded"):
                await owner.next_segment()

    asyncio.run(scenario())
    assert control.reaped
    assert owner.ledger.usage.all_audio == 0
    assert MetadataBuffer.live_count == 0


def test_handle_expiry_cannot_be_overridden_by_consumer(monkeypatch: pytest.MonkeyPatch) -> None:
    from livecho_backend.audio.contracts import Segment

    ledger = Ledger()
    buffer = MetadataBuffer(None, ledger, Owner.SEGMENT, 1920, Interval(0, 60))
    metadata = Segment(
        binding=binding(),
        segment_index=0,
        start_pts=0,
        new_start_pts=0,
        end_pts=60,
        sample_count=960,
        left_context_samples=0,
        close_reason="eof",
    )
    handle = SegmentHandle(metadata, buffer, time.monotonic_ns() // 1_000_000 - 1000)  # type: ignore[arg-type]
    with pytest.raises(AudioError, match="audio_handle_invalid"):
        handle.read_sample(0)
    assert handle.released
    assert ledger.usage.all_audio == 0


@pytest.mark.parametrize("fault", [False, True])
def test_control_run_attempts_no_file_or_log_writes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    fault: bool,
) -> None:
    control = ControlIO(3)
    control.malformed = fault
    owner = create_pipeline(monkeypatch, control)
    writes: list[str] = []

    def reject(*args: Any, **kwargs: Any) -> Any:
        writes.append("rejected-before-retention")
        raise AssertionError("persistence is forbidden")

    monkeypatch.setattr(builtins, "open", reject)
    monkeypatch.setattr(io, "open", reject)
    monkeypatch.setattr(Path, "write_bytes", reject)
    monkeypatch.setattr(Path, "write_text", reject)

    async def scenario() -> None:
        await owner.start()
        if fault:
            with pytest.raises(AudioError):
                await owner.next_segment()
            return
        handle = await owner.next_segment()
        assert handle is not None
        handle.release()
        assert await owner.next_segment() is None

    asyncio.run(scenario())
    assert writes == []
    assert list(tmp_path.iterdir()) == []
    assert not caplog.records
    assert MetadataBuffer.live_count == 0
