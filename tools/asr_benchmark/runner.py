"""Deterministic run planning and transient-text reduction for the local harness."""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from .contracts import MODELS, NS, WINDOWS, Corpus, Model, Script, Window
from .metrics import (
    align,
    boundary_counts,
    error_counts,
    normalize,
    rewrite_counts,
    stitch,
    target_exact,
)
from .report import Count, ScriptScore, Segment, SpanScore
from .runtime import BlockedEvidence
from .timing import SegmentTiming


@dataclass(frozen=True)
class PassPlan:
    model: Model
    window_seconds: Window
    repetition: int
    order: int
    cold_script_id: str
    warmup_count: int
    script_ids: tuple[str, ...]
    conditions: tuple[str, ...] = ("clean", "noise")
    silence_duration_ns: int = 60 * NS


def matrix_plan(corpus: Corpus) -> tuple[PassPlan, ...]:
    """Each item requires a new process; no model stays loaded across items."""
    scripts = tuple(sorted(script.script_id for script in corpus.scripts))
    plans = []
    for repetition in (1, 2, 3):
        models = MODELS if repetition % 2 else tuple(reversed(MODELS))
        for window in WINDOWS:
            for order, model in enumerate(models):
                plans.append(PassPlan(model, window, repetition, order, scripts[0], 3, scripts))
    return tuple(plans)


@dataclass(frozen=True)
class SegmentText:
    """Transient adapter text. The report retains counts, never these revisions."""

    start_ns: int
    end_ns: int
    partials: tuple[str, ...]
    final: str
    timing: SegmentTiming


def score_script(
    script: Script, observations: Sequence[SegmentText], window: Window
) -> ScriptScore:
    if not observations:
        raise BlockedEvidence("incomplete_script")
    segments = []
    intervals: list[tuple[int, int]] = []
    previous_end = 0
    for observation in observations:
        if not (
            observation.start_ns == previous_end
            and observation.start_ns < observation.end_ns <= script.duration_ns
            and observation.end_ns - observation.start_ns <= window * NS
        ):
            raise BlockedEvidence("invalid_timing")
        if len(observation.partials) != observation.timing.evaluated_prefixes:
            raise BlockedEvidence("partial_count")
        readable = any(normalize(partial) for partial in observation.partials)
        if readable != (observation.timing.tp_ns is not None):
            raise BlockedEvidence("partial_observation")
        for text in (*observation.partials, observation.final):
            if len(text) > 4096:
                raise BlockedEvidence("text_limit")
        rewrites = rewrite_counts(observation.partials)
        finalization = rewrite_counts((*observation.partials[-1:], observation.final))
        failure: Literal["missing_partial", "output_limit", "provider_timeout"] | None = None
        if observation.timing.tp_ns is None:
            failure = "missing_partial"
        elif any(call.output_tokens == 512 for call in observation.timing.calls):
            failure = "output_limit"
        elif any(
            call.execution_end_ns - call.execution_start_ns > 10 * NS
            for call in observation.timing.calls
        ):
            failure = "provider_timeout"
        segments.append(
            Segment(
                start_ns=observation.start_ns,
                end_ns=observation.end_ns,
                timing=observation.timing,
                rewrite_frequency=Count(
                    numerator=rewrites.changed_pairs, denominator=rewrites.pairs
                ),
                rewrite_severity=Count(
                    numerator=rewrites.rewritten_characters,
                    denominator=rewrites.old_characters,
                ),
                finalization_changes=Count(
                    numerator=finalization.changed_pairs,
                    denominator=finalization.pairs,
                ),
                failure=failure,
            )
        )
        if script.stratum == "continuous" and window in (4, 6) and previous_end:
            indices = [
                index
                for index, timing in enumerate(script.character_times)
                if timing.start_ns < previous_end and timing.end_ns > previous_end - 800_000_000
            ]
            if indices:
                intervals.append((indices[0], indices[-1] + 1))
            else:
                raise BlockedEvidence("boundary_coverage")
        previous_end = observation.end_ns
    if previous_end != script.duration_ns:
        raise BlockedEvidence("incomplete_script")
    finals = [observation.final for observation in observations]
    hypothesis = (
        stitch(finals)
        if script.stratum == "continuous" and window in (4, 6)
        else "".join(normalize(text) for text in finals)
    )
    errors = error_counts(script.reference, hypothesis)
    edits = align(script.reference, hypothesis)
    totals = Counter(target.kind for target in script.targets)
    exact = Counter(
        target.kind for target in script.targets if target_exact(edits, target.start, target.end)
    )
    boundaries = boundary_counts(script.reference, hypothesis, intervals)
    return ScriptScore(
        script_id=script.script_id,
        substitutions=errors.substitutions,
        deletions=errors.deletions,
        insertions=errors.insertions,
        reference_characters=errors.reference_characters,
        targets=tuple(
            SpanScore(
                kind=kind,
                exact=Count(numerator=exact[kind], denominator=total),
            )
            for kind, total in sorted(totals.items())
        ),
        boundary_duplicate=Count(
            numerator=boundaries.duplicates,
            denominator=boundaries.reference_characters,
        ),
        boundary_omission=Count(
            numerator=boundaries.omissions,
            denominator=boundaries.reference_characters,
        ),
        segments=tuple(segments),
    )
