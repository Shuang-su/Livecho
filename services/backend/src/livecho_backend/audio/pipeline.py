"""One serialized source/decoder/buffer owner with no stored or background audio retry."""

from __future__ import annotations

import asyncio
import os
import time
from collections import deque
from collections.abc import Callable
from contextlib import suppress

from .contracts import (
    CANONICAL,
    FRAME_BYTES,
    FRAME_MS,
    FRAME_SAMPLES,
    AudioError,
    Binding,
    EndOfInput,
    InputOrder,
    MemoryAudioSource,
    Reason,
    Segment,
    SourceFactory,
)
from .ledger import PROCESS_ADMISSION, PROCESS_BYTES, Interval, Ledger, Owner, Reservation
from .lifecycle import Lifecycle, State
from .memory import OwnedBuffer, SegmentHandle, WritableView
from .preflight import RuntimePermit
from .segmenter import Segmenter, detect_speech
from .supervisor import DecoderSupervisor


def monotonic_ms() -> int:
    return time.monotonic_ns() // 1_000_000


def read_owned(fd: int, buffer: OwnedBuffer, offset: int) -> int:
    view = memoryview(buffer._data)[offset:]
    try:
        try:
            return os.readv(fd, [view])
        except BlockingIOError:
            return -1
        except OSError:
            raise AudioError(Reason.DECODER_PIPE) from None
    finally:
        view.release()


def write_owned(fd: int, buffer: OwnedBuffer, offset: int) -> int:
    view = memoryview(buffer._data)[offset:]
    try:
        try:
            return os.write(fd, view)
        except BlockingIOError:
            return 0
        except OSError:
            raise AudioError(Reason.DECODER_PIPE) from None
    finally:
        view.release()


class AudioPipeline:
    """Completed segments only. Callers own wire lease/epoch/sequence assignment.

    Use start(), next_segment(), and close(). The owner task enforces deadlines even
    when a consumer stops calling next_segment. RuntimePermit is never issued until
    checked-in decoder/host evidence passes preflight.
    """

    def __init__(
        self,
        permit: RuntimePermit,
        binding: Binding,
        factory: SourceFactory,
        admitted: Callable[[], bool],
        continuity_broken: Callable[[], None],
    ) -> None:
        permit.require()
        self.permit = permit
        self.binding = binding
        self.factory = factory
        self._admitted = admitted
        self._continuity_broken = continuity_broken
        self.lifecycle = Lifecycle(restartable=factory.restartable)
        self.ledger = Ledger()
        self._decoder: DecoderSupervisor | None = None
        self._source: MemoryAudioSource | None = None
        self._owner_task: asyncio.Task[None] | None = None
        self._source_task: asyncio.Task[object] | None = None
        self._ring: deque[tuple[int, OwnedBuffer]] = deque()
        self._scratch: OwnedBuffer | None = None
        self._input: OwnedBuffer | None = None
        self._writer: WritableView | None = None
        self._handle: SegmentHandle | None = None
        self._delivered = False
        self._changed = asyncio.Event()
        self._allocations: list[Reservation] = []
        self._release_inventory: Callable[[], None] | None = None
        self._input_frames = 0
        self._output_frames = 0
        self._acknowledged_end = 0
        self._reaped = True
        self._close_started = False
        self._last_trimmed = 0
        self._last_below_onset = 0

    async def start(self) -> None:
        if self._owner_task is not None or self._close_started:
            raise AudioError(Reason.ADMISSION_CLOSED)
        self.permit.require()
        if not self._admitted():
            raise AudioError(Reason.ADMISSION_CLOSED)
        PROCESS_ADMISSION.acquire(self)
        self._owner_task = asyncio.create_task(self._run())

    async def next_segment(self) -> SegmentHandle | None:
        if self._owner_task is None:
            raise AudioError(Reason.ADMISSION_CLOSED)
        while True:
            if self._handle is not None and not self._delivered:
                self._delivered = True
                return self._handle
            if self._owner_task.done():
                if self.lifecycle.state == State.FAILED:
                    raise AudioError(self.lifecycle.reason or Reason.DECODER_EXIT)
                return None
            self._changed.clear()
            await self._changed.wait()

    async def close(self, reason: Reason = Reason.CANCELLED) -> None:
        task = self._owner_task
        if self._close_started or (task is not None and task.done()):
            if task is not None:
                with suppress(asyncio.CancelledError):
                    await asyncio.shield(task)
            return
        self._close_started = True
        self.lifecycle.abort(reason, terminal=True)
        if self._writer is not None:
            self._writer.revoke()
        if self._handle is not None:
            self._handle.invalidate()
        if task is not None and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await asyncio.shield(task)
        # A task cancelled before its coroutine first runs never enters _run.finally.
        # No decoder/audio exists in that case, but its Alpha admission still needs
        # explicit release and its waiting consumers need a terminal notification.
        if self.lifecycle.state == State.STOPPING:
            self.lifecycle.cleaned(monotonic_ms(), reaped=self._reaped, admitted=False)
        if task is None or task.done():
            PROCESS_ADMISSION.release(self, reaped=self._reaped)
            self._changed.set()

    async def _run(self) -> None:
        try:
            attempt = 0
            while True:
                generation = self.lifecycle.start(monotonic_ms(), admitted=self._admitted())
                binding = self.binding.model_copy(
                    update={"attempt_id": f"{self.binding.attempt_id[:110]}:{attempt}"}
                )
                try:
                    await self._attempt(binding, generation)
                except AudioError as error:
                    if error.reason == Reason.METADATA_INVALID:
                        self.lifecycle.metrics.unmeasurable_input += 1
                    self.lifecycle.abort(error.reason)
                except asyncio.CancelledError:
                    if self.lifecycle.reason is None:
                        self.lifecycle.abort(Reason.CANCELLED, terminal=True)
                except Exception:
                    # Exception text/traceback can contain producer bodies; retain only code.
                    self.lifecycle.abort(Reason.METADATA_INVALID, terminal=True)
                    self.lifecycle.metrics.unmeasurable_input += 1
                finally:
                    cleanup = asyncio.create_task(self._cleanup())
                    try:
                        await asyncio.shield(cleanup)
                    except asyncio.CancelledError:
                        # Only this task owns cleanup; cancelling a caller cannot
                        # interrupt descriptor closure, zeroing, or child reaping.
                        await cleanup
                self.lifecycle.cleaned(
                    monotonic_ms(), reaped=self._reaped, admitted=self._admitted()
                )
                if self.lifecycle.state != State.RETRY_WAIT:
                    break
                self._continuity_broken()
                while not self.lifecycle.retry_due(monotonic_ms(), admitted=self._admitted()):
                    if self.lifecycle.state != State.RETRY_WAIT:
                        return
                    await asyncio.sleep(0.01)
                if not self._admitted():
                    self.lifecycle.abort(Reason.DISABLED, terminal=True)
                    return
                attempt += 1
                self.ledger = Ledger()
        finally:
            # Cancellation during a retry delay has no source/decoder/audio to revive.
            PROCESS_ADMISSION.release(self, reaped=self._reaped)
            self._changed.set()

    async def _source_read(self, generation: int) -> object:
        assert self._source is not None and self._writer is not None
        self._source_task = asyncio.create_task(self._source.read(self._writer))
        remaining = self.lifecycle.remaining_ms(monotonic_ms())
        done, _ = await asyncio.wait({self._source_task}, timeout=remaining / 1000)
        self._writer.revoke()
        self.lifecycle.tick(monotonic_ms())
        if self.lifecycle.state == State.STOPPING:
            raise AudioError(self.lifecycle.reason or Reason.INPUT_STALLED)
        self.lifecycle.require(generation)
        if not done:
            self._source_task.cancel()
            raise AudioError(Reason.INPUT_STALLED)
        result = self._source_task.result()
        self._source_task = None
        return result

    async def _attempt(self, binding: Binding, generation: int) -> None:
        self._input_frames = self._output_frames = self._acknowledged_end = 0
        self._last_trimmed = self._last_below_onset = 0
        inventory = self.permit.build.inventory
        self._release_inventory = PROCESS_BYTES.reserve(inventory.parent_noncanonical_bytes + 64000)
        # Conservative fixed inventory reservations are in addition to individually
        # counted Python allocations. The exact approved profile must fit both.
        self._allocations = [
            self.ledger.reserve(Owner.PIPE, 64_000, Interval(0, 20)),
            self.ledger.reserve(
                Owner.DECODER,
                inventory.parent_noncanonical_bytes,
                Interval(0, 20),
                canonical=False,
            ),
        ]
        self._decoder = DecoderSupervisor(self.permit, binding.source_format)
        self._reaped = False
        self._decoder.start()
        self._source = self.factory.create()
        await self._bounded_open(binding)
        order = InputOrder(binding)
        segmenter = Segmenter(binding)
        input_offset = output_offset = 0
        input_eof = False
        while True:
            now = monotonic_ms()
            if not self._admitted():
                raise AudioError(Reason.DISABLED)
            self.lifecycle.tick(now)
            if self.lifecycle.state == State.STOPPING:
                raise AudioError(self.lifecycle.reason or Reason.CANCELLED)
            self._decoder.check()
            if not self._decoder.ready():
                await asyncio.sleep(0.001)
                continue
            if self._handle is not None:
                if self._handle.released:
                    if not self._handle.consumed:
                        raise AudioError(Reason.CONSUMER_SLOW)
                    self._acknowledged_end = self._handle.metadata.end_pts
                    self._handle = None
                    self._delivered = False
                    self.lifecycle.resume(now, reserved=True, admitted=self._admitted())
                else:
                    if now >= self._handle.deadline_ms:
                        raise AudioError(Reason.CONSUMER_SLOW)
                    await asyncio.sleep(0.001)
                    continue
            pts = self._output_frames * FRAME_MS
            if self._scratch is None:
                self._scratch = await self._buffer(
                    Owner.SCRATCH,
                    FRAME_BYTES,
                    Interval(pts, pts + FRAME_MS),
                )
            # readv fills owned memory directly; no bytes result or async StreamReader copy.
            count = read_owned(self._decoder.output_fd, self._scratch, output_offset)
            if count == 0:
                if not input_eof or output_offset or self._output_frames != self._input_frames:
                    raise AudioError(Reason.METADATA_INVALID)
                # Pipe EOF alone does not prove decoder success. Observe its direct
                # watchdog's clean completion before publishing the final segment.
                completion_deadline = monotonic_ms() + 500
                while not self._decoder.completed():
                    if not self._admitted():
                        raise AudioError(Reason.DISABLED)
                    if monotonic_ms() >= completion_deadline:
                        raise AudioError(Reason.DECODER_EXIT)
                    await asyncio.sleep(0.001)
                metadata = segmenter.eof()
                self._sync_segment_metrics(segmenter)
                if metadata is not None:
                    await self._handoff(metadata, now)
                self.lifecycle.eof(monotonic_ms(), handle_pending=self._handle is not None)
                while self._handle is not None and not self._handle.released:
                    if not self._admitted() or monotonic_ms() >= self._handle.deadline_ms:
                        raise AudioError(Reason.CONSUMER_SLOW)
                    await asyncio.sleep(0.001)
                if self._handle is not None and not self._handle.consumed:
                    raise AudioError(Reason.CONSUMER_SLOW)
                return
            if count > 0:
                output_offset += count
                if output_offset == FRAME_BYTES:
                    if self._output_frames >= self._input_frames:
                        raise AudioError(Reason.METADATA_INVALID)
                    frame = await self._buffer(
                        Owner.RING,
                        FRAME_BYTES,
                        Interval(pts, pts + FRAME_MS),
                    )
                    self._scratch.transfer(frame)
                    self._scratch.clear()
                    self._scratch = None
                    output_offset = 0
                    self._ring.append((self._output_frames * FRAME_SAMPLES, frame))
                    metadata = segmenter.push(
                        self._output_frames * FRAME_SAMPLES,
                        speech=detect_speech(frame.read_sample),
                    )
                    self._sync_segment_metrics(segmenter)
                    self._output_frames += 1
                    self.lifecycle.progress(monotonic_ms(), canonical=True)
                    if metadata is not None:
                        await self._handoff(metadata, now)
                        self.lifecycle.pause(monotonic_ms())
                    while self._ring and self._ring[0][0] < segmenter.retain_from:
                        self._ring.popleft()[1].clear()
                    continue
            if (
                self._input is None
                and not input_eof
                and self._input_frames - self._output_frames < 100
            ):
                # The fixed 64,000-byte canonical transport reservation covers at
                # most 100 complete frames, including every decoder-held input frame.
                self.lifecycle.require(generation)
                input_pts = self._input_frames * FRAME_MS
                envelope = Interval(pts, max(pts + FRAME_MS, input_pts + FRAME_MS))
                for reservation in self._allocations:
                    reservation.move_interval(envelope)
                self._input = await self._buffer(
                    Owner.SCRATCH if binding.source_format == CANONICAL else Owner.SOURCE,
                    binding.source_format.frame_bytes,
                    Interval(input_pts, input_pts + FRAME_MS),
                    canonical=binding.source_format == CANONICAL,
                )
                self._writer = WritableView(
                    self._input,
                    lambda: self.lifecycle.gate_open and self.lifecycle.generation == generation,
                )
                chunk = await self._source_read(generation)
                if isinstance(chunk, EndOfInput):
                    if self._writer.written_samples:
                        raise AudioError(Reason.METADATA_INVALID)
                    self._input.clear()
                    self._input = None
                    self._decoder.finish_input()
                    input_eof = True
                else:
                    from .contracts import Chunk

                    if not isinstance(chunk, Chunk) or not self._writer.complete:
                        raise AudioError(Reason.METADATA_INVALID)
                    order.accept(chunk)
                    self._input_frames += 1
                    self.lifecycle.progress(monotonic_ms())
                self._writer = None
            if self._input is not None:
                self.lifecycle.require(generation)
                written = write_owned(self._decoder.input_fd, self._input, input_offset)
                input_offset += written
                if input_offset == self._input.size:
                    self._input.clear()
                    self._input = None
                    input_offset = 0
            await asyncio.sleep(0.001)

    async def _bounded_open(self, binding: Binding) -> None:
        assert self._source is not None
        self._source_task = asyncio.create_task(self._source.open(binding))
        remaining = self.lifecycle.remaining_ms(monotonic_ms())
        done, _ = await asyncio.wait({self._source_task}, timeout=remaining / 1000)
        self.lifecycle.tick(monotonic_ms())
        if self.lifecycle.state == State.STOPPING:
            raise AudioError(self.lifecycle.reason or Reason.DECODER_START_TIMEOUT)
        if not done:
            self._source_task.cancel()
            raise AudioError(Reason.INPUT_STALLED)
        self._source_task.result()
        self._source_task = None

    async def _handoff(self, metadata: Segment, now: int) -> None:
        if self._handle is not None:
            raise AudioError(Reason.CONSUMER_SLOW)
        buffer = await self._buffer(
            Owner.SEGMENT,
            metadata.sample_count * 2,
            Interval(metadata.start_pts, metadata.end_pts),
        )
        try:
            start = metadata.start_pts * 16
            for sample, frame in self._ring:
                if sample >= start:
                    frame.transfer(buffer, (sample - start) * 2)
            self._handle = SegmentHandle(metadata, buffer, monotonic_ms())
            self._delivered = False
            self._changed.set()
        except BaseException:
            buffer.clear()
            raise

    async def _buffer(
        self, owner: Owner, size: int, interval: Interval, *, canonical: bool = True
    ) -> OwnedBuffer:
        deadline: int | None = None
        while True:
            now = monotonic_ms()
            if not self._admitted():
                raise AudioError(Reason.DISABLED)
            if deadline is not None and now >= deadline:
                raise AudioError(Reason.BUDGET_EXCEEDED)
            try:
                # Probe reservations only; no audio allocation is made during pause.
                reservation = self.ledger.reserve(owner, size, interval, canonical=canonical)
                try:
                    physical = PROCESS_BYTES.reserve(size)
                    physical()
                finally:
                    reservation.release()
                if deadline is not None and not self.lifecycle.resume(
                    now, reserved=True, admitted=self._admitted()
                ):
                    raise AudioError(Reason.BUDGET_EXCEEDED)
                return OwnedBuffer(
                    self.permit, self.ledger, owner, size, interval, canonical=canonical
                )
            except AudioError as error:
                if error.reason != Reason.BUDGET_EXCEEDED or not self.ledger.within_window(
                    interval
                ):
                    raise
                if deadline is None:
                    deadline = now + 500
                self.lifecycle.pause(now)
                await asyncio.sleep(0.001)

    def _sync_segment_metrics(self, segmenter: Segmenter) -> None:
        trimmed = segmenter.trimmed_silence_samples // 16
        below = segmenter.below_onset_samples // 16
        self.lifecycle.metrics.trimmed_silence_ms += trimmed - self._last_trimmed
        self.lifecycle.metrics.below_onset_ms += below - self._last_below_onset
        self._last_trimmed = trimmed
        self._last_below_onset = below

    async def _cleanup(self) -> None:
        self.lifecycle.gate_open = False
        if self._writer is not None:
            self._writer.revoke()
        pending_source = self._source_task
        self._source_task = None
        if pending_source is not None:
            pending_source.cancel()
        if self.lifecycle.reason is not None:
            if self._handle is not None and self._handle.consumed:
                self._acknowledged_end = max(self._acknowledged_end, self._handle.metadata.end_pts)
            intervals = [
                Interval(max(self._acknowledged_end, sample // 16), (sample + FRAME_SAMPLES) // 16)
                for sample, _ in self._ring
                if (sample + FRAME_SAMPLES) // 16 > self._acknowledged_end
            ]
            if self._handle is not None and not self._handle.consumed:
                intervals.append(
                    Interval(self._handle.metadata.new_start_pts, self._handle.metadata.end_pts)
                )
            if self._input_frames > self._output_frames:
                intervals.append(
                    Interval(self._output_frames * FRAME_MS, self._input_frames * FRAME_MS)
                )
            self.lifecycle.metrics.drop(self.lifecycle.reason, intervals)
        if self._handle is not None:
            self._handle.invalidate()
            self._handle = None
        for buffer in (self._scratch, self._input):
            if buffer is not None:
                buffer.clear()
        self._scratch = self._input = None
        while self._ring:
            self._ring.popleft()[1].clear()
        # Clear copied consumer allocations before the first teardown await, too.
        self.ledger.close_and_clear_memory()
        if self._decoder is not None:
            try:
                self._reaped = self._decoder.close()
            except Exception:
                self._reaped = False
                self.lifecycle.abort(Reason.DECODER_REAP_FAILED, terminal=True)
            if self._decoder.failure_reason is not None and self.lifecycle.reason is None:
                self.lifecycle.abort(self._decoder.failure_reason)
            self._decoder = None
        if pending_source is not None:
            done, _ = await asyncio.wait({pending_source}, timeout=0.05)
            if not done:
                self.lifecycle.abort(Reason.ADMISSION_CLOSED, terminal=True)
            elif not pending_source.cancelled():
                with suppress(Exception):
                    pending_source.result()
        if self._source is not None:
            task = asyncio.create_task(self._source.close())
            done, _ = await asyncio.wait({task}, timeout=0.5)
            if not done:
                task.cancel()
                self.lifecycle.abort(Reason.ADMISSION_CLOSED, terminal=True)
            else:
                try:
                    task.result()
                except (Exception, asyncio.CancelledError):
                    self.lifecycle.abort(Reason.ADMISSION_CLOSED, terminal=True)
            self._source = None
        for reservation in self._allocations:
            reservation.release()
        self._allocations.clear()
        if self._release_inventory is not None:
            self._release_inventory()
            self._release_inventory = None
        self.ledger.clear()
        self._changed.set()
