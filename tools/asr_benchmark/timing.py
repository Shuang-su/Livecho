"""One-clock observation validation and disjoint-work RTF."""

from typing import Literal, Self

from pydantic import model_validator

from .contracts import NS, Closed, Nonnegative, Positive


class Call(Closed):
    kind: Literal["provisional", "final"]
    preparation_start_ns: Nonnegative
    preparation_end_ns: Nonnegative
    execution_start_ns: Nonnegative
    execution_end_ns: Nonnegative
    input_duration_ns: Positive
    overlap_duration_ns: Nonnegative
    synchronized: Literal[True]
    output_tokens: Nonnegative

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if not (
            self.preparation_start_ns
            <= self.preparation_end_ns
            <= self.execution_start_ns
            <= self.execution_end_ns
        ):
            raise ValueError("call_timing")
        if self.overlap_duration_ns >= self.input_duration_ns or self.output_tokens > 512:
            raise ValueError("call_bounds")
        return self

    @property
    def work_ns(self) -> int:
        return (self.preparation_end_ns - self.preparation_start_ns) + (
            self.execution_end_ns - self.execution_start_ns
        )

    @property
    def rtf(self) -> float:
        return self.work_ns / self.input_duration_ns


class SegmentTiming(Closed):
    t0_ns: Nonnegative
    te_ns: Nonnegative
    tc_ns: Nonnegative
    tp_ns: Nonnegative | None
    tf_ns: Nonnegative
    new_duration_ns: Positive
    calls: tuple[Call, ...]
    missed_partial_opportunities: Nonnegative
    evaluated_prefixes: Nonnegative

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if not self.t0_ns <= self.te_ns <= self.tc_ns <= self.tf_ns:
            raise ValueError("segment_timing")
        if not self.calls or self.calls[-1].kind != "final":
            raise ValueError("final_call_missing")
        if any(call.kind != "provisional" for call in self.calls[:-1]):
            raise ValueError("final_call_order")
        if self.evaluated_prefixes != len(self.calls) - 1:
            raise ValueError("prefix_count")
        opportunities = (self.new_duration_ns - 1) // 250_000_000
        if self.evaluated_prefixes + self.missed_partial_opportunities != opportunities:
            raise ValueError("partial_opportunities")
        previous_end = self.t0_ns
        for call in self.calls:
            if call.preparation_start_ns < previous_end:
                raise ValueError("concurrent_calls")
            previous_end = call.execution_end_ns
            prefix_duration = call.input_duration_ns - call.overlap_duration_ns
            if (
                prefix_duration > self.new_duration_ns
                or call.preparation_start_ns < self.t0_ns + prefix_duration
            ):
                raise ValueError("prefix_eligibility")
        final = self.calls[-1]
        if final.preparation_start_ns < self.tc_ns or self.tf_ns != final.execution_end_ns:
            raise ValueError("final_observation")
        if any(call.preparation_start_ns >= self.tc_ns for call in self.calls[:-1]):
            raise ValueError("provisional_after_close")
        if final.input_duration_ns - final.overlap_duration_ns != self.new_duration_ns:
            raise ValueError("rtf_denominator")
        if self.tp_ns is not None and not any(
            call.execution_start_ns <= self.tp_ns <= call.execution_end_ns
            for call in self.calls[:-1]
        ):
            raise ValueError("partial_observation")
        return self

    def measures(self) -> dict[str, float]:
        final = self.calls[-1]
        result = {
            "rtf": sum(call.work_ns for call in self.calls) / self.new_duration_ns,
            "segmentation_wait_ns": float(self.tc_ns - self.te_ns),
            "final_queue_wait_ns": float(final.preparation_start_ns - self.tc_ns),
            "provider_final_ns": float(self.tf_ns - final.execution_start_ns),
            "speech_end_to_final_ns": float(self.tf_ns - self.te_ns),
        }
        if self.tp_ns is not None:
            result["first_partial_ns"] = float(self.tp_ns - self.t0_ns)
            result["provider_first_text_ns"] = float(self.tp_ns - self.calls[0].execution_start_ns)
        return result

    @property
    def failed(self) -> bool:
        return self.tp_ns is None or any(
            call.output_tokens == 512 or call.execution_end_ns - call.execution_start_ns > 10 * NS
            for call in self.calls
        )
