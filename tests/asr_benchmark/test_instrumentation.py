from collections.abc import Callable

import pytest

from tools.asr_benchmark.contracts import NS, InferenceManifest, Settings
from tools.asr_benchmark.instrumentation import instrument_call
from tools.asr_benchmark.runtime import (
    Allocation,
    BlockedEvidence,
    Budget,
    MemoryInput,
    Prefix,
    TextUpdate,
)


class Clock:
    now = 0

    def __call__(self) -> int:
        return self.now


class MetadataGuard:
    """Only contract tests; cannot interrupt a hung backend and is never registered."""

    def __init__(self, clock: Clock) -> None:
        self.clock = clock
        self.deadlines: list[int] = []

    def execute(self, operation: Callable[[], None], deadline_ns: int) -> None:
        self.deadlines.append(deadline_ns)
        operation()
        if self.clock() > deadline_ns:
            raise BlockedEvidence("provider_timeout")


class MetadataProvider:
    def __init__(self, clock: Clock, failure: bool = False) -> None:
        self.clock = clock
        self.synchronized = False
        self.failure = failure

    def load(self, manifest: InferenceManifest, settings: Settings) -> None:
        pass

    def transcribe(self, memory_view: MemoryInput, timing: Prefix) -> TextUpdate:
        assert memory_view.view.nbytes == 0
        if self.failure:
            raise RuntimeError("private diagnostics")
        self.clock.now += 2_000_000
        return TextUpdate("测 试!", self.clock(), 2)

    def synchronize(self) -> None:
        self.clock.now += 3_000_000
        self.synchronized = True

    def close(self) -> None:
        pass


@pytest.mark.parametrize("failure", [False, True])
def test_synchronization_and_cleanup_even_after_provider_failure(failure: bool) -> None:
    clock = Clock()
    budget = Budget()
    provider = MetadataProvider(clock, failure)
    guard = MetadataGuard(clock)
    released = []
    view = memoryview(bytearray())  # Empty metadata-only borrow, no audio samples.

    def prepare() -> MemoryInput:
        assert budget.live_count == 1  # Reservation precedes even preparation.
        clock.now += 1_000_000
        return MemoryInput(view, 0, NS)

    def run() -> None:
        result = instrument_call(
            provider=provider,
            prefix=Prefix(NS, "final"),
            allocation=Allocation("metadata", 0, NS, 1, 0),
            budget=budget,
            prepare=prepare,
            release=lambda: released.append("released"),
            clock=clock,
            guard=guard,
            cancelled=lambda: False,
            overlap_ns=0,
        )
        assert provider.synchronized
        assert result.text == "测试" and result.delivered_ns == 6_000_000
        assert result.observation.work_ns == 6_000_000
        assert guard.deadlines == [10 * NS, 10 * NS + 1_000_000]

    if failure:
        with pytest.raises(BlockedEvidence, match="^provider_failure$"):
            run()
    else:
        run()
    assert released == ["released"] and budget.live_count == 0
    with pytest.raises(ValueError):
        _ = view.nbytes


def test_cancel_after_preparation_still_clears_reservation() -> None:
    clock = Clock()
    budget = Budget()
    released = []
    cancelled = False

    def prepare() -> MemoryInput:
        nonlocal cancelled
        cancelled = True
        return MemoryInput(memoryview(bytearray()), 0, NS)

    with pytest.raises(BlockedEvidence, match="cancelled"):
        instrument_call(
            provider=MetadataProvider(clock),
            prefix=Prefix(NS, "final"),
            allocation=Allocation("metadata", 0, NS, 1, 0),
            budget=budget,
            prepare=prepare,
            release=lambda: released.append("released"),
            clock=clock,
            guard=MetadataGuard(clock),
            cancelled=lambda: cancelled,
            overlap_ns=0,
        )
    assert released == ["released"] and budget.live_count == 0


def test_allocation_duration_is_bound_to_prefix_and_overlap_before_provider_call() -> None:
    clock = Clock()
    budget = Budget()
    calls = []

    def prepare() -> MemoryInput:
        calls.append("prepare")
        return MemoryInput(memoryview(bytearray()), 0, 2 * NS)

    with pytest.raises(BlockedEvidence, match="allocation_mismatch"):
        instrument_call(
            provider=MetadataProvider(clock),
            prefix=Prefix(NS, "final"),
            allocation=Allocation("metadata", 0, 2 * NS, 1, 0),
            budget=budget,
            prepare=prepare,
            release=lambda: None,
            clock=clock,
            guard=MetadataGuard(clock),
            cancelled=lambda: False,
            overlap_ns=0,
        )
    assert calls == [] and budget.live_count == 0


def test_initial_clock_failure_cannot_strand_a_reservation() -> None:
    clock = Clock()
    budget = Budget()

    def failed_clock() -> int:
        raise RuntimeError("private clock diagnostic")

    with pytest.raises(BlockedEvidence, match="invalid_timing"):
        instrument_call(
            provider=MetadataProvider(clock),
            prefix=Prefix(NS, "final"),
            allocation=Allocation("metadata", 0, NS, 1, 0),
            budget=budget,
            prepare=lambda: MemoryInput(memoryview(bytearray()), 0, NS),
            release=lambda: None,
            clock=failed_clock,
            guard=MetadataGuard(clock),
            cancelled=lambda: False,
            overlap_ns=0,
        )
    assert budget.live_count == 0
