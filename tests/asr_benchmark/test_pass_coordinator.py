import asyncio
from collections.abc import Callable, Sequence
from dataclasses import replace
from threading import Event, RLock

import pytest

from tools.asr_benchmark import pass_coordinator as coordinator
from tools.asr_benchmark.contracts import NS, InferenceManifest, Script, Settings, Window
from tools.asr_benchmark.pass_coordinator import (
    PassCoordinator,
    PassExecutionFailure,
    PassObservations,
    PreparedCall,
    ReplayRequest,
    SegmentSpan,
)
from tools.asr_benchmark.report import ScriptScore
from tools.asr_benchmark.runner import PassPlan, SegmentText, matrix_plan, score_script
from tools.asr_benchmark.runtime import (
    Allocation,
    BlockedEvidence,
    Budget,
    MemoryInput,
    Prefix,
    PrefixScheduler,
    TextUpdate,
)

from .factories import corpus

TICK = 250_000_000


class Clock:
    def __init__(self) -> None:
        self.now = 0
        self.lock = RLock()

    def __call__(self) -> int:
        with self.lock:
            return self.now

    def advance(self, now: int) -> None:
        with self.lock:
            self.now = max(self.now, now)


class Guard:
    """A cooperative text-double guard, not a real provider deadline implementation."""

    def __init__(self, clock: Clock):
        self.clock = clock

    def execute(self, operation: Callable[[], None], deadline_ns: int) -> None:
        operation()
        if self.clock() > deadline_ns:
            raise BlockedEvidence("provider_timeout")


class Provider:
    def __init__(self, clock: Clock):
        self.clock = clock
        self.source: Source | None = None
        self.completed: list[tuple[int, int, int, str]] = []
        self.calls: list[tuple[int, int, int, str, int]] = []
        self.started = Event()
        self.release_work = Event()
        self.release_work.set()
        self.closed = 0
        self.active = 0
        self.max_active = 0
        self.fail = False
        self.empty_partials = False
        self.token_limit = False
        self.limit_phase: str | None = None
        self.silence_text = False
        self.close_failure = False
        self.pending: tuple[int, int, int, str] | None = None

    def load(self, manifest: InferenceManifest, settings: Settings) -> None:
        raise AssertionError("coordinator must not invent a model-load operation")

    def transcribe(self, memory_view: MemoryInput, timing: Prefix) -> TextUpdate:
        assert memory_view.view.nbytes == 0  # Empty opaque borrow, no audio generated.
        assert self.source is not None
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        record = (self.source.number, memory_view.start_pts_ns, memory_view.end_pts_ns, timing.kind)
        self.calls.append((*record, self.clock()))
        self.pending = record
        self.started.set()
        self.release_work.wait()
        if self.fail:
            self.active -= 1
            raise RuntimeError("private provider diagnostics must not escape")
        text = "原始测试文字"
        if self.source.request.phase == "silence" and not self.silence_text:
            text = ""
        if timing.kind == "provisional" and self.empty_partials:
            text = ""
        self.clock.advance(self.clock() + 1_000)
        limited = self.token_limit or self.source.request.phase == self.limit_phase
        return TextUpdate(text, self.clock(), 512 if limited else 4)

    def synchronize(self) -> None:
        assert self.pending is not None
        self.completed.append(self.pending)
        self.active -= 1
        self.pending = None

    def close(self) -> None:
        assert self.active == 0
        self.closed += 1
        if self.close_failure:
            raise RuntimeError("private cleanup details")


class Source:
    def __init__(self, owner: "Factory", request: ReplayRequest, budget: Budget, origin: int):
        self.owner, self.request, self.budget, self.origin = owner, request, budget, origin
        self.number = len(owner.opened)
        self.pts = 0
        self.closed = 0
        self.released = 0
        self.borrowed: list[memoryview] = []
        self.retired: list[int] = []
        self.sequence = 0
        self.segments = tuple(
            SegmentSpan(
                start,
                min(start + request.window_ns, request.duration_ns),
                min(start + request.window_ns, request.duration_ns),
            )
            for start in range(0, request.duration_ns, request.window_ns)
        )
        self.read_cancelled = False
        self.storage_id = f"source-{self.number}"
        budget.reserve(Allocation(self.storage_id, 0, TICK, 1, 0), lambda: None)

    async def advance(self, deadline_ns: int) -> int | None:
        try:
            return await self._advance(deadline_ns)
        except asyncio.CancelledError:
            self.read_cancelled = True
            raise

    async def _advance(self, deadline_ns: int) -> int | None:
        owner, provider = self.owner, self.owner.provider
        # Normal doubles wait for each applicable call. The busy test deliberately
        # continues source eligibility through the first segment's close instead.
        busy = self.number == 0 and self.pts < owner.busy_until
        if busy and self.pts == TICK:
            while not provider.started.is_set():
                await asyncio.sleep(0)
        needs_call = self.request.phase != "warmup" or self.pts == self.request.duration_ns
        if self.pts and needs_call and not busy:
            while not any(
                n == self.number and end >= self.pts for n, _start, end, _kind in provider.completed
            ):
                await asyncio.sleep(0)
        if self.pts == self.request.duration_ns:
            if owner.extra_progress:
                return self.pts + 1
            return None
        if owner.abort_after is not None and self.number >= owner.abort_after:
            return None
        if owner.stall_at is not None and self.pts >= owner.stall_at:
            owner.clock.advance(deadline_ns)
            provider.release_work.set()
            return None
        if owner.error:
            raise RuntimeError("private source diagnostics")
        if owner.bad_pts:
            return -1
        self.pts += TICK
        if not owner.ahead:
            owner.clock.advance(self.origin + self.pts)
        if busy and self.pts >= owner.busy_until:
            provider.release_work.set()
        await asyncio.sleep(0)
        return self.pts

    def call_input(self, start_ns: int, end_ns: int) -> PreparedCall:
        self.sequence += 1
        duration = end_ns - start_ns
        if self.owner.mismatch:
            duration += 1
        allocation = Allocation(
            f"call-{self.number}-{self.sequence}",
            start_ns,
            start_ns + duration,
            16_777_216 if self.owner.over_budget else 1,
            0,
        )

        def prepare() -> MemoryInput:
            assert allocation.allocation_id in self.budget._live
            view = memoryview(bytearray())
            self.borrowed.append(view)
            if self.owner.prepare_failure:
                raise RuntimeError("private preparation details")
            return MemoryInput(view, start_ns, end_ns)

        def release() -> None:
            self.released += 1
            if self.owner.release_failure:
                raise RuntimeError("private release details")

        return PreparedCall(allocation, prepare, release)

    def retire_before(self, pts_ns: int) -> None:
        self.retired.append(pts_ns)
        if self.owner.retire_failure:
            raise RuntimeError("private retirement details")
        # This double owns only one metadata allocation, never a retained corpus.
        self.budget.release(self.storage_id)

    def close(self) -> None:
        assert self.owner.provider.active == 0
        self.closed += 1
        self.budget.release(self.storage_id)
        for view in self.borrowed:
            view.release()
        if self.owner.close_failure:
            raise RuntimeError("private source cleanup details")


class Factory:
    def __init__(self, clock: Clock, provider: Provider):
        self.clock, self.provider = clock, provider
        self.opened: list[Source] = []
        self.requests: list[ReplayRequest] = []
        self.abort_after: int | None = None
        self.busy_until = 0
        self.stall_at: int | None = None
        self.ahead = self.bad_pts = self.extra_progress = self.error = False
        self.mismatch = self.over_budget = self.prepare_failure = False
        self.release_failure = self.retire_failure = self.close_failure = False
        self.schedule_change: Callable[[Source], None] = lambda source: None

    def __call__(self, request: ReplayRequest, budget: Budget, origin_ns: int) -> Source:
        source = Source(self, request, budget, origin_ns)
        self.schedule_change(source)
        self.opened.append(source)
        self.requests.append(request)
        self.provider.source = source
        return source


def setup(window: Window = 6) -> tuple[PassPlan, Clock, Provider, Factory]:
    plan = next(item for item in matrix_plan(corpus()) if item.window_seconds == window)
    clock = Clock()
    provider = Provider(clock)
    return plan, clock, provider, Factory(clock, provider)


def run(plan: PassPlan, clock: Clock, provider: Provider, factory: Factory) -> PassObservations:
    return asyncio.run(
        PassCoordinator().run(plan, corpus(), provider, factory, guard=Guard(clock), clock=clock)
    )


def assert_closed(factory: Factory, provider: Provider) -> None:
    assert provider.closed == 1 and provider.active == 0
    assert all(source.closed == 1 and source.budget.live_count == 0 for source in factory.opened)
    for source in factory.opened:
        for view in source.borrowed:
            with pytest.raises(ValueError):
                _ = view.nbytes


@pytest.mark.parametrize("window", [1, 6])
def test_complete_pass_orders_cold_warmup_all_scripts_and_silence(window: Window) -> None:
    plan, clock, provider, factory = setup(window)
    provider.silence_text = window == 6
    result = run(plan, clock, provider, factory)
    assert len(factory.requests) == 125
    assert [request.phase for request in factory.requests[:4]] == ["cold", *["warmup"] * 3]
    assert factory.requests[0].script is not None
    assert factory.requests[0].script.script_id == plan.cold_script_id
    assert factory.requests[0].condition == "clean"
    for condition, requests in zip(
        ("clean", "noise"), (factory.requests[4:64], factory.requests[64:124]), strict=True
    ):
        assert tuple(r.script.script_id for r in requests if r.script) == plan.script_ids
        assert all(r.phase == "warm" and r.condition == condition for r in requests)
    assert factory.requests[-1].phase == "silence"
    assert factory.requests[-1].duration_ns == 60 * NS
    warmups = [call for call in provider.calls if call[0] in (1, 2, 3)]
    assert len(warmups) == 3 and all(
        c[2] - c[1] == window * NS and c[3] == "final" for c in warmups
    )
    assert result.cold_score.script_id == plan.cold_script_id
    assert len(result.cells) == 2 and all(len(cell.scripts) == 60 for cell in result.cells)
    if window == 6:
        assert result.silence_nonempty_finals == 10
        assert result.silence_nonempty_partials == 230
    else:
        assert result.silence_nonempty_finals == result.silence_nonempty_partials == 0
    assert provider.max_active == 1
    assert not hasattr(result, "cold") and not hasattr(result, "teardown_passed")
    assert not hasattr(result, "write_sinks_passed") and not hasattr(result, "process_id")
    if window == 6:
        continuous = next(s for s in factory.opened if s.request.overlap_ns)
        assert continuous.retired == [6 * NS - 800_000_000, 12 * NS - 800_000_000]
        assert any(
            n == continuous.number and start == 6 * NS - 800_000_000
            for n, start, _end, _kind, _now in provider.calls
        )
    assert_closed(factory, provider)


def test_busy_provider_does_not_pause_source_and_final_replaces_missed_ticks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, clock, provider, factory = setup(1)
    factory.busy_until = NS
    provider.release_work.clear()
    factory.abort_after = 1
    scores = capture_scores(monkeypatch)
    with pytest.raises(PassExecutionFailure, match="^incomplete_source$") as failure:
        run(plan, clock, provider, factory)
    assert failure.value.completed_scripts == 1
    first = provider.calls[:2]
    assert [(start, end, kind) for _n, start, end, kind, _now in first] == [
        (0, TICK, "provisional"),
        (0, NS, "final"),
    ]
    assert first[1][-1] >= NS
    timing = scores[0].segments[0].timing
    assert timing.tc_ns == NS and timing.evaluated_prefixes == 1
    assert timing.missed_partial_opportunities == 2
    assert timing.measures()["final_queue_wait_ns"] >= 0
    assert provider.max_active == 1
    assert_closed(factory, provider)


@pytest.mark.parametrize(
    "reason,attribute,value",
    [
        ("incomplete_source", "abort_after", 0),
        ("invalid_timing", "bad_pts", True),
        ("source_ahead_of_clock", "ahead", True),
        ("pass_execution_failed", "error", True),
        ("input_stall", "stall_at", 0),
        ("allocation_mismatch", "mismatch", True),
        ("budget_exceeded", "over_budget", True),
        ("provider_failure", "prepare_failure", True),
        ("teardown_failed", "release_failure", True),
        ("pass_execution_failed", "retire_failure", True),
        ("teardown_failed", "close_failure", True),
        ("invalid_timing", "extra_progress", True),
    ],
)
def test_failures_never_return_completed_observations(
    reason: str, attribute: str, value: object
) -> None:
    plan, clock, provider, factory = setup()
    setattr(factory, attribute, value)
    with pytest.raises(PassExecutionFailure, match=f"^{reason}$") as failure:
        run(plan, clock, provider, factory)
    assert failure.value.completed_scripts == 0
    assert provider.closed == 1 and factory.opened[0].closed == 1
    if attribute != "release_failure":
        assert_closed(factory, provider)
    else:
        assert factory.opened[0].budget.tainted


@pytest.mark.parametrize("malformed", ["short", "gap", "speech_end", "oversize", "early", "count"])
def test_segment_schedule_rejected_before_provider(malformed: str) -> None:
    plan, clock, provider, factory = setup()

    def change(source: Source) -> None:
        if malformed == "short":
            source.segments = source.segments[:1]
        elif malformed == "gap":
            source.segments = (SegmentSpan(1, 6 * NS, 6 * NS), source.segments[1])
        elif malformed == "speech_end":
            source.segments = (SegmentSpan(0, 6 * NS, 5 * NS), source.segments[1])
        elif malformed == "oversize":
            source.segments = (SegmentSpan(0, 12 * NS, 12 * NS),)
        elif malformed == "early":
            source.segments = (
                SegmentSpan(0, NS, NS),
                SegmentSpan(NS, 6 * NS, 6 * NS),
                source.segments[1],
            )
        else:
            source.segments = source.segments * 129

    factory.schedule_change = change
    with pytest.raises(PassExecutionFailure):
        run(plan, clock, provider, factory)
    assert provider.calls == []
    assert_closed(factory, provider)


def capture_scores(monkeypatch: pytest.MonkeyPatch) -> list[ScriptScore]:
    scores: list[ScriptScore] = []

    def score(script: Script, observations: Sequence[SegmentText], window: Window) -> ScriptScore:
        result = score_script(script, observations, window)
        scores.append(result)
        return result

    monkeypatch.setattr(coordinator, "score_script", score)
    return scores


@pytest.mark.parametrize("missing_partial", [True, False])
def test_measured_failures_are_retained(
    monkeypatch: pytest.MonkeyPatch, missing_partial: bool
) -> None:
    plan, clock, provider, factory = setup()
    provider.empty_partials = missing_partial
    provider.token_limit = not missing_partial
    scores = capture_scores(monkeypatch)
    # Exercise only the actual cold score reduction, then deliberately incomplete pass.
    factory.abort_after = 1
    with pytest.raises(PassExecutionFailure, match="incomplete_source") as failure:
        run(plan, clock, provider, factory)
    assert failure.value.completed_scripts == 1
    assert len(scores) == 1
    expected = "missing_partial" if missing_partial else "output_limit"
    assert all(segment.failure == expected for segment in scores[0].segments)
    assert len(factory.opened) == 2
    assert_closed(factory, provider)


@pytest.mark.parametrize("kind", ["provider", "provider_close", "callback"])
def test_provider_and_callback_faults_are_sanitized(kind: str) -> None:
    plan, clock, provider, factory = setup()
    provider.fail = kind == "provider"
    provider.close_failure = kind == "provider_close"
    factory.abort_after = 0 if kind == "provider_close" else None

    def cancelled() -> bool:
        if kind == "callback":
            raise OSError("private callback path")
        return False

    expected = {
        "provider": "provider_failure",
        "provider_close": "teardown_failed",
        "callback": "cancellation_check_failed",
    }[kind]
    with pytest.raises(PassExecutionFailure, match=f"^{expected}$"):
        asyncio.run(
            PassCoordinator().run(
                plan,
                corpus(),
                provider,
                factory,
                guard=Guard(clock),
                clock=clock,
                cancelled=cancelled,
            )
        )
    assert provider.closed == 1


def test_repeated_task_cancellation_waits_for_actual_worker_before_cleanup() -> None:
    plan, clock, provider, factory = setup()
    provider.release_work.clear()

    async def exercise() -> None:
        task = asyncio.create_task(
            PassCoordinator().run(
                plan, corpus(), provider, factory, guard=Guard(clock), clock=clock
            )
        )
        while not provider.started.is_set():
            await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0.01)
        task.cancel()
        await asyncio.sleep(0.01)
        assert not task.done()
        assert provider.closed == 0 and factory.opened[0].closed == 0
        provider.release_work.set()
        with pytest.raises(PassExecutionFailure, match="^cancelled$"):
            await task

    asyncio.run(exercise())
    assert_closed(factory, provider)


def test_invalid_plan_or_corpus_does_not_transfer_ownership() -> None:
    plan, clock, provider, factory = setup()
    for invalid in (
        replace(plan, warmup_count=2),
        replace(plan, script_ids=plan.script_ids[:-1]),
        replace(plan, cold_script_id=plan.script_ids[-1]),
    ):
        with pytest.raises(BlockedEvidence, match="pass_plan_invalid"):
            run(invalid, clock, provider, factory)
    assert provider.closed == 0 and factory.opened == []


def test_stall_clock_remains_active_while_provider_is_busy() -> None:
    plan, clock, provider, factory = setup()
    factory.busy_until = NS
    factory.stall_at = TICK
    provider.release_work.clear()
    with pytest.raises(PassExecutionFailure, match="^input_stall$"):
        run(plan, clock, provider, factory)
    assert provider.started.is_set()
    assert_closed(factory, provider)


def test_late_provider_is_joined_and_cannot_return_a_complete_score() -> None:
    plan, clock, provider, factory = setup()
    factory.busy_until = 12 * NS
    provider.release_work.clear()
    with pytest.raises(PassExecutionFailure, match="^provider_timeout$") as failure:
        run(plan, clock, provider, factory)
    assert failure.value.completed_scripts == 0
    assert_closed(factory, provider)


def test_leading_silence_cannot_be_reported_as_speech_onset() -> None:
    plan, clock, provider, factory = setup()
    record = corpus()
    script = record.scripts[0]
    timing = script.character_times[0].model_copy(update={"start_ns": 100_000_000})
    script = script.model_copy(update={"character_times": (timing, *script.character_times[1:])})
    record = record.model_copy(update={"scripts": (script, *record.scripts[1:])})
    with pytest.raises(PassExecutionFailure, match="^speech_onset_unsupported$"):
        asyncio.run(
            PassCoordinator().run(plan, record, provider, factory, guard=Guard(clock), clock=clock)
        )
    assert provider.calls == []
    assert_closed(factory, provider)


def test_unscored_warmup_limit_cannot_be_counted_as_success() -> None:
    plan, clock, provider, factory = setup()
    provider.limit_phase = "warmup"
    with pytest.raises(PassExecutionFailure, match="^output_limit$") as failure:
        run(plan, clock, provider, factory)
    assert failure.value.completed_scripts == 1 and len(factory.opened) == 2
    assert_closed(factory, provider)


def test_cancellation_observed_during_cleanup_prevents_success() -> None:
    plan, clock, provider, factory = setup()
    with pytest.raises(PassExecutionFailure, match="^cancelled$") as failure:
        asyncio.run(
            PassCoordinator().run(
                plan,
                corpus(),
                provider,
                factory,
                guard=Guard(clock),
                clock=clock,
                cancelled=lambda: provider.closed > 0,
            )
        )
    assert failure.value.completed_scripts == 121
    assert_closed(factory, provider)


def test_reuse_and_plan_corpus_mismatch_are_rejected() -> None:
    plan, clock, provider, factory = setup()
    changed_ids = ("alternate", *plan.script_ids[1:])
    with pytest.raises(BlockedEvidence, match="plan_corpus_mismatch"):
        run(
            replace(plan, script_ids=changed_ids, cold_script_id=changed_ids[0]),
            clock,
            provider,
            factory,
        )
    assert provider.closed == 0
    factory.abort_after = 0
    owner = PassCoordinator()
    for reason in ("incomplete_source", "coordinator_reused"):
        with pytest.raises(BlockedEvidence, match=reason):
            asyncio.run(
                owner.run(plan, corpus(), provider, factory, guard=Guard(clock), clock=clock)
            )
    assert provider.closed == 1


def test_early_close_exact_tick_does_not_count_a_nonexistent_opportunity() -> None:
    scheduler = PrefixScheduler(6 * NS)
    scheduler.arrive(NS)
    scheduler.close_segment()
    assert scheduler.missed_opportunities == 3
    assert scheduler.take() == Prefix(NS, "final")
