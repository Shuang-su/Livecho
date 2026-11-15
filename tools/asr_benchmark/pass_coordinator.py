"""Cooperative in-process pass execution, without model or hardware authority.

Sources and guards remain injected, unregistered contracts. One worker executes calls;
source progress continues on the event loop. Neither cancellation nor a thread timeout
proves termination: teardown always waits for the actual worker to finish.
"""

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from dataclasses import dataclass
from threading import Event, RLock
from time import monotonic_ns
from typing import Literal, Protocol, cast

from .contracts import NS, Condition, Corpus, Script, Window
from .instrumentation import CallResult, ExecutionGuard, instrument_call
from .pass_control import validate_plan
from .report import Cell, ScriptScore
from .runner import PassPlan, SegmentText, score_script
from .runtime import (
    Allocation,
    BlockedEvidence,
    Budget,
    MemoryInput,
    Prefix,
    PrefixScheduler,
    ProgressWatch,
    Provider,
)
from .timing import SegmentTiming


@dataclass(frozen=True)
class SegmentSpan:
    start_ns: int
    end_ns: int
    speech_end_ns: int


@dataclass(frozen=True)
class ReplayRequest:
    phase: Literal["cold", "warm", "warmup", "silence"]
    condition: Condition
    script: Script | None
    duration_ns: int
    window_ns: int
    overlap_ns: int


@dataclass(frozen=True)
class PreparedCall:
    """Hooks only; no input allocation may precede instrument_call's reservation."""

    allocation: Allocation
    prepare: Callable[[], MemoryInput]
    release: Callable[[], None]


class ReplaySource(Protocol):
    segments: tuple[SegmentSpan, ...]

    async def advance(self, deadline_ns: int) -> int | None:
        """Replay to the next increasing PTS, or EOF after the complete duration.

        Use the supplied origin/clock; never read ahead of real-time eligibility.
        Storage must be reserved in the shared budget before allocation. This method
        and call-input preparation can overlap; borrowed call inputs stay immutable.
        Cancellation must end the advance before its task returns or raises.
        """
        ...

    def call_input(self, start_ns: int, end_ns: int) -> PreparedCall:
        """Return metadata/hooks only; preparation runs on the single worker."""
        ...

    def retire_before(self, pts_ns: int) -> None:
        """Release consumed source storage, preserving any required left context."""
        ...

    def close(self) -> None:
        """Release source-owned allocations after advance and calls have ended."""
        ...


class SourceFactory(Protocol):
    def __call__(self, request: ReplayRequest, budget: Budget, origin_ns: int) -> ReplaySource:
        """Open one source session; clean up locally if opening cannot return it."""
        ...


@dataclass(frozen=True)
class PassObservations:
    """Reduced observations only: no Cold, Repetition, Report or privacy assertion."""

    plan: PassPlan
    cold_score: ScriptScore
    cells: tuple[Cell, ...]
    unscored_warmups: int
    silence_duration_ns: int
    silence_nonempty_finals: int
    silence_nonempty_partials: int
    peak_audio_bytes: int
    peak_canonical_bytes: int
    peak_media_ns: int


class PassExecutionFailure(BlockedEvidence):
    def __init__(self, reason: str, completed_scripts: int):
        super().__init__(reason)
        self.completed_scripts = completed_scripts


class _SharedBudget(Budget):
    """Serialize accounting across source and call owners, including release hooks."""

    def __init__(self) -> None:
        super().__init__()
        self.lock = RLock()

    def reserve(self, allocation: Allocation, release: Callable[[], None]) -> None:
        with self.lock:
            super().reserve(allocation, release)

    def release(self, allocation_id: str) -> None:
        with self.lock:
            super().release(allocation_id)

    def close(self) -> None:
        with self.lock:
            super().close()


class _Clock:
    def __init__(self, clock: Callable[[], int]):
        self.clock = clock
        self.last = -1
        self.lock = RLock()

    def __call__(self) -> int:
        with self.lock:
            try:
                now = self.clock()
            except BaseException:
                raise BlockedEvidence("invalid_timing") from None
            if type(now) is not int or now < 0 or now < self.last:
                raise BlockedEvidence("invalid_timing")
            self.last = now
            return now


def _schedule(request: ReplayRequest, source: ReplaySource) -> tuple[SegmentSpan, ...]:
    spans = source.segments
    if type(spans) is not tuple or not 1 <= len(spans) <= 256:
        raise BlockedEvidence("segment_schedule_invalid")
    previous = 0
    for span in spans:
        if (
            type(span) is not SegmentSpan
            or any(
                type(value) is not int for value in (span.start_ns, span.end_ns, span.speech_end_ns)
            )
            or span.start_ns != previous
            or not span.start_ns <= span.speech_end_ns <= span.end_ns <= request.duration_ns
            or not 0 < span.end_ns - span.start_ns <= request.window_ns
        ):
            raise BlockedEvidence("segment_schedule_invalid")
        if request.script is not None:
            speech = tuple(
                timing
                for timing in request.script.character_times
                if timing.start_ns < span.end_ns and timing.end_ns > span.start_ns
            )
            # Existing SegmentTiming/score_script require contiguous new-audio ranges
            # and t0-based prefix eligibility. Do not mislabel leading silence as speech.
            if not speech or speech[0].start_ns > span.start_ns:
                raise BlockedEvidence("speech_onset_unsupported")
            if span.speech_end_ns != min(speech[-1].end_ns, span.end_ns):
                raise BlockedEvidence("segment_schedule_invalid")
            # A window/EOF endpoint cannot bypass an earlier annotated silence.
            # Inspect the next speech interval too: using only the supplied span's
            # last speech end would overlook an internal pause followed by speech.
            limit = min(span.start_ns + request.window_ns, request.duration_ns)
            speech_end = span.start_ns
            for timing in request.script.character_times:
                if timing.end_ns <= span.start_ns:
                    continue
                if timing.start_ns >= min(limit, speech_end + 500_000_000):
                    break
                speech_end = min(limit, timing.end_ns)
            if span.end_ns != min(limit, speech_end + 500_000_000):
                raise BlockedEvidence("segment_schedule_invalid")
        if (
            span.end_ns != request.duration_ns
            and span.end_ns - span.start_ns != request.window_ns
            and span.end_ns != span.speech_end_ns + 500_000_000
        ):
            raise BlockedEvidence("segment_schedule_invalid")
        previous = span.end_ns
    if previous != request.duration_ns:
        raise BlockedEvidence("incomplete_source")
    if request.phase == "warmup" and len(spans) != 1:
        raise BlockedEvidence("warmup_shape_invalid")
    return spans


async def _settle[T](future: asyncio.Future[T]) -> None:
    """Join even after repeated caller cancellation; never equate cancel with exit."""
    while not future.done():
        try:
            await asyncio.shield(future)
        except asyncio.CancelledError:
            continue
        except BaseException:
            break
    with suppress(BaseException):
        future.result()


class PassCoordinator:
    """Single-use owner. Valid admission transfers provider cleanup to this owner.

    The provider must already be ready; this layer neither loads it nor establishes
    process freshness. Before admission, invalid plans/corpus leave ownership with
    the caller. Source/guard contracts require cooperative completion and cleanup;
    no installed real implementation satisfies runtime admission today.
    """

    def __init__(self) -> None:
        self._used = False

    async def run(
        self,
        plan: PassPlan,
        corpus: Corpus,
        provider: Provider,
        sources: SourceFactory,
        *,
        guard: ExecutionGuard,
        clock: Callable[[], int] = monotonic_ns,
        cancelled: Callable[[], bool] = lambda: False,
    ) -> PassObservations:
        if self._used:
            raise BlockedEvidence("coordinator_reused")
        plan = validate_plan(plan)
        try:
            corpus = Corpus.model_validate(corpus.model_dump())
        except Exception:
            raise BlockedEvidence("corpus_invalid") from None
        if plan.script_ids != tuple(sorted(script.script_id for script in corpus.scripts)):
            raise BlockedEvidence("plan_corpus_mismatch")
        budget, now, stop = _SharedBudget(), _Clock(clock), Event()
        completed_scripts = 0
        failure: str | None = None
        output: PassObservations | None = None

        def poll_cancelled() -> bool:
            try:
                value = cancelled()
            except BaseException:
                stop.set()
                raise BlockedEvidence("cancellation_check_failed") from None
            if type(value) is not bool:
                stop.set()
                raise BlockedEvidence("cancellation_check_failed")
            if value:
                stop.set()
            return value

        def check() -> bool:
            return stop.is_set() or poll_cancelled()

        async def collect(request: ReplayRequest) -> tuple[ScriptScore | None, int, int]:
            nonlocal completed_scripts
            if check():
                raise BlockedEvidence("cancelled")
            result = await self._collect(
                request, sources, provider, budget, now, guard, check, stop, pool
            )
            if request.script is not None:
                completed_scripts += 1
            return result

        # The executor's shutdown follows an actual join of the one in-flight call.
        # A noncooperating injected guard/provider can hang; no success escapes it.
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="asr-pass") as pool:
            self._used = True
            try:
                by_id = {script.script_id: script for script in corpus.scripts}

                def request(
                    phase: Literal["cold", "warm"], condition: Condition, script_id: str
                ) -> ReplayRequest:
                    script = by_id[script_id]
                    overlap = (
                        800_000_000
                        if script.stratum == "continuous" and plan.window_seconds in (4, 6)
                        else 0
                    )
                    return ReplayRequest(
                        phase,
                        condition,
                        script,
                        script.duration_ns,
                        plan.window_seconds * NS,
                        overlap,
                    )

                cold_score, _, _ = await collect(request("cold", "clean", plan.cold_script_id))
                if cold_score is None:
                    raise BlockedEvidence("incomplete_script")
                for _ in range(plan.warmup_count):
                    await collect(
                        ReplayRequest(
                            "warmup",
                            "clean",
                            None,
                            plan.window_seconds * NS,
                            plan.window_seconds * NS,
                            0,
                        )
                    )
                cells = []
                for condition in ("clean", "noise"):
                    scores = []
                    for script_id in plan.script_ids:
                        score, _, _ = await collect(request("warm", condition, script_id))
                        if score is None:
                            raise BlockedEvidence("incomplete_script")
                        scores.append(score)
                    cells.append(Cell(condition=condition, scripts=tuple(scores)))
                _, finals, partials = await collect(
                    ReplayRequest(
                        "silence",
                        "clean",
                        None,
                        plan.silence_duration_ns,
                        plan.window_seconds * NS,
                        0,
                    )
                )
                if check():
                    raise BlockedEvidence("cancelled")
                output = PassObservations(
                    plan,
                    cold_score,
                    tuple(cells),
                    3,
                    plan.silence_duration_ns,
                    finals,
                    partials,
                    budget.peak_audio_bytes,
                    budget.peak_canonical_bytes,
                    budget.peak_media_ns,
                )
            except asyncio.CancelledError:
                failure = "cancelled"
            except BlockedEvidence as error:
                # Preserve only this layer's closed reason vocabulary.
                reason = str(error)
                failure = reason if reason in _REASONS else "pass_execution_failed"
            except BaseException:
                failure = "pass_execution_failed"
            finally:
                stop.set()
                for cleanup in (provider.close, budget.close):
                    try:
                        cleanup()
                    except BaseException:
                        failure = "teardown_failed"
                if failure is None:
                    try:
                        if poll_cancelled():
                            failure = "cancelled"
                    except BaseException:
                        failure = "cancellation_check_failed"
        if failure is not None:
            raise PassExecutionFailure(failure, completed_scripts) from None
        if output is None:
            raise PassExecutionFailure("incomplete_pass", completed_scripts)
        return output

    async def _collect(
        self,
        request: ReplayRequest,
        sources: SourceFactory,
        provider: Provider,
        budget: Budget,
        clock: Callable[[], int],
        guard: ExecutionGuard,
        cancelled: Callable[[], bool],
        stop: Event,
        pool: ThreadPoolExecutor,
    ) -> tuple[ScriptScore | None, int, int]:
        source: ReplaySource | None = None
        advance: asyncio.Task[int | None] | None = None
        call: asyncio.Future[CallResult | None] | None = None
        observations: list[SegmentText] = []
        calls: list[CallResult] = []
        try:
            origin = clock()
            source = sources(request, budget, origin)
            spans = _schedule(request, source)
            schedulers = [PrefixScheduler(request.window_ns) for _ in spans]
            watch = ProgressWatch(origin)
            eof, pts, events, index = False, 0, 0, 0
            finals = partials = 0
            loop = asyncio.get_running_loop()

            def execute(prefix: Prefix, span: SegmentSpan) -> CallResult | None:
                if cancelled():
                    raise BlockedEvidence("cancelled")
                # Thread dispatch itself is not preparation. A prefix whose segment
                # closed before it actually starts must yield to final preparation.
                if prefix.kind == "provisional" and clock() >= origin + span.end_ns:
                    return None
                overlap = request.overlap_ns if span.start_ns else 0
                start, end = span.start_ns - overlap, span.start_ns + prefix.new_duration_ns
                assert source is not None
                prepared = source.call_input(start, end)
                if (
                    prepared.allocation.start_pts_ns != start
                    or prepared.allocation.end_pts_ns != end
                ):
                    raise BlockedEvidence("allocation_mismatch")
                if prefix.kind == "provisional" and clock() >= origin + span.end_ns:
                    return None
                return instrument_call(
                    provider=provider,
                    prefix=prefix,
                    allocation=prepared.allocation,
                    budget=budget,
                    prepare=prepared.prepare,
                    release=prepared.release,
                    clock=clock,
                    guard=guard,
                    cancelled=cancelled,
                    overlap_ns=overlap,
                )

            while not eof or index < len(spans):
                if cancelled():
                    raise BlockedEvidence("cancelled")
                current = clock()
                if not eof:
                    watch.check(current)
                    if advance is None:
                        advance = asyncio.create_task(source.advance(watch.last_input_ns + 2 * NS))
                if call is not None and call.done():
                    result = call.result()
                    call = None
                    scheduler = schedulers[index]
                    was_final = scheduler.running is not None and scheduler.running.kind == "final"
                    scheduler.finish()
                    if result is None:
                        scheduler.evaluated_prefixes -= 1
                        scheduler.missed_opportunities += 1
                    else:
                        if request.script is None and result.observation.output_tokens == 512:
                            raise BlockedEvidence("output_limit")
                        calls.append(result)
                        if was_final:
                            span = spans[index]
                            partial_text = tuple(item.text for item in calls[:-1])
                            finals += bool(result.text)
                            partials += sum(bool(text) for text in partial_text)
                            if request.script is not None:
                                timing = SegmentTiming(
                                    t0_ns=origin + span.start_ns,
                                    te_ns=origin + span.speech_end_ns,
                                    tc_ns=origin + span.end_ns,
                                    tp_ns=next(
                                        (item.delivered_ns for item in calls[:-1] if item.text),
                                        None,
                                    ),
                                    tf_ns=result.delivered_ns,
                                    new_duration_ns=span.end_ns - span.start_ns,
                                    calls=tuple(item.observation for item in calls),
                                    missed_partial_opportunities=scheduler.missed_opportunities,
                                    evaluated_prefixes=scheduler.evaluated_prefixes,
                                )
                                observations.append(
                                    SegmentText(
                                        span.start_ns,
                                        span.end_ns,
                                        partial_text,
                                        result.text,
                                        timing,
                                    )
                                )
                            calls.clear()
                            source.retire_before(max(0, span.end_ns - request.overlap_ns))
                            index += 1
                # Source observations are handled before selecting the next call, so
                # a simultaneous close always replaces an unstarted provisional.
                if advance is not None and advance.done():
                    value = advance.result()
                    advance = None
                    current = clock()
                    watch.check(current)
                    events += 1
                    if events > 131072:
                        raise BlockedEvidence("source_event_limit")
                    if value is None:
                        if pts != request.duration_ns:
                            raise BlockedEvidence("incomplete_source")
                        eof = True
                    else:
                        if type(value) is not int or not pts < value <= request.duration_ns:
                            raise BlockedEvidence("invalid_timing")
                        if current < origin + value:
                            raise BlockedEvidence("source_ahead_of_clock")
                        watch.input(value, current)
                        pts = value
                        for span, scheduler in zip(spans, schedulers, strict=True):
                            duration = min(value, span.end_ns) - span.start_ns
                            if not scheduler.closed and duration > scheduler.latest_ns:
                                scheduler.arrive(duration)
                                if value >= span.end_ns:
                                    scheduler.close_segment()
                if call is None and index < len(spans):
                    scheduler = schedulers[index]
                    if request.phase != "warmup" or scheduler.closed:
                        prefix = scheduler.take()
                        if prefix is not None:
                            call = loop.run_in_executor(pool, execute, prefix, spans[index])
                pending = [future for future in (advance, call) if future is not None]
                if pending:
                    await asyncio.wait(pending, timeout=0.01, return_when=asyncio.FIRST_COMPLETED)
            if request.script is not None:
                score = score_script(
                    request.script, observations, cast(Window, request.window_ns // NS)
                )
                return score, finals, partials
            return None, finals, partials
        finally:
            # Stop new work, then join both owners before revoking borrowed storage.
            # An exceptional exit invalidates the whole pass, including earlier scores.
            if advance is not None or call is not None:
                stop.set()
            if advance is not None:
                advance.cancel()
                await _settle(advance)
            if call is not None:
                await _settle(call)
            calls.clear()
            observations.clear()
            try:
                if source is not None:
                    source.close()
            except BaseException:
                raise BlockedEvidence("teardown_failed") from None
            finally:
                source = None
                advance = None
                call = None
            if budget.live_count:
                raise BlockedEvidence("source_allocation_leak")


_REASONS = frozenset(
    {
        "cancelled",
        "cancellation_check_failed",
        "invalid_timing",
        "input_stall",
        "incomplete_source",
        "incomplete_script",
        "incomplete_pass",
        "source_event_limit",
        "source_ahead_of_clock",
        "source_allocation_leak",
        "segment_schedule_invalid",
        "speech_onset_unsupported",
        "warmup_shape_invalid",
        "allocation_mismatch",
        "allocation_invalid",
        "allocation_duplicate",
        "budget_exceeded",
        "teardown_failed",
        "provider_failure",
        "provider_timeout",
        "output_limit",
        "preparation_missing",
    }
)
