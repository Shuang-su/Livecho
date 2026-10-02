"""In-process call instrumentation with required injected deadline enforcement.

There is deliberately no default guard: a real backend must independently demonstrate
termination, no in-flight audio escape and safe cleanup at its deadline before use.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from .contracts import NS
from .metrics import normalize
from .runtime import Allocation, BlockedEvidence, Budget, MemoryInput, Prefix, Provider
from .timing import Call


class ExecutionGuard(Protocol):
    def execute(self, operation: Callable[[], None], deadline_ns: int) -> None:
        """Return only after operation ends; on expiry terminate it before raising."""
        ...


@dataclass(frozen=True)
class CallResult:
    observation: Call
    text: str
    delivered_ns: int


def instrument_call(
    *,
    provider: Provider,
    prefix: Prefix,
    allocation: Allocation,
    budget: Budget,
    prepare: Callable[[], MemoryInput],
    release: Callable[[], None],
    clock: Callable[[], int],
    guard: ExecutionGuard,
    cancelled: Callable[[], bool],
    overlap_ns: int,
) -> CallResult:
    """Reserve all input/feature bytes before preparation; synchronize before delivery.

    `allocation` includes the reviewed provider's complete allocation bound, not just
    the input view. The CLI installs neither an approved provider nor a guard today.
    """
    if cancelled():
        raise BlockedEvidence("cancelled")
    if (
        type(prefix.new_duration_ns) is not int
        or not 0 < prefix.new_duration_ns <= 6 * NS
        or prefix.kind not in {"provisional", "final"}
        or type(overlap_ns) is not int
        or overlap_ns not in {0, 800_000_000}
        or allocation.end_pts_ns - allocation.start_pts_ns != prefix.new_duration_ns + overlap_ns
    ):
        raise BlockedEvidence("allocation_mismatch")
    try:
        preparation_start = clock()
    except BaseException:
        raise BlockedEvidence("invalid_timing") from None
    budget.reserve(allocation, release)
    prepared: MemoryInput | None = None
    preparation_end = execution_start = execution_end = preparation_start
    text = ""
    output_tokens = 0

    def prepare_input() -> None:
        nonlocal prepared, preparation_end
        prepared = prepare()
        preparation_end = clock()
        if not (
            prepared.start_pts_ns == allocation.start_pts_ns
            and prepared.end_pts_ns == allocation.end_pts_ns
            and prepared.view.nbytes <= allocation.audio_bytes
        ):
            raise BlockedEvidence("allocation_mismatch")

    def execute() -> None:
        nonlocal execution_end, text, output_tokens
        if prepared is None:
            raise BlockedEvidence("preparation_missing")
        update = provider.transcribe(prepared, prefix)
        provider.synchronize()
        execution_end = clock()
        if not execution_start <= update.observed_ns <= execution_end:
            raise BlockedEvidence("invalid_timing")
        if not 0 <= update.output_tokens <= 512 or len(update.text) > 4096:
            raise BlockedEvidence("output_limit")
        text, output_tokens = normalize(update.text), update.output_tokens

    try:
        guard.execute(prepare_input, preparation_start + 10 * NS)
        if cancelled():
            raise BlockedEvidence("cancelled")
        execution_start = clock()
        guard.execute(execute, execution_start + 10 * NS)
        if cancelled():
            raise BlockedEvidence("cancelled")
        if execution_end - execution_start > 10 * NS:
            raise BlockedEvidence("provider_timeout")
        observation = Call(
            kind=prefix.kind,
            preparation_start_ns=preparation_start,
            preparation_end_ns=preparation_end,
            execution_start_ns=execution_start,
            execution_end_ns=execution_end,
            input_duration_ns=prefix.new_duration_ns + overlap_ns,
            overlap_duration_ns=overlap_ns,
            synchronized=True,
            output_tokens=output_tokens,
        )
        return CallResult(observation, text, execution_end)
    except BlockedEvidence:
        raise
    except Exception:
        raise BlockedEvidence("provider_failure") from None
    finally:
        # Invalidate this borrow even when provider/guard throws; the owner's callback
        # clears all backing storage and provider features represented by the reservation.
        try:
            if prepared is not None:
                prepared.view.release()
        finally:
            budget.release(allocation.allocation_id)
