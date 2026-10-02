from collections.abc import Callable
from datetime import timedelta

import pytest
from pydantic import ValidationError

from tools.asr_benchmark.contracts import MODELS, NS, Corpus, Machine
from tools.asr_benchmark.report import (
    Cell,
    Count,
    Report,
    ScriptScore,
    Segment,
    cell_populations,
    cold_populations,
    evaluate,
)
from tools.asr_benchmark.runner import SegmentText, matrix_plan, score_script
from tools.asr_benchmark.timing import Call, SegmentTiming

from .factories import corpus, report, timing


def alter_run(source: Report, index: int, **updates: object) -> Report:
    runs = list(source.repetitions)
    runs[index] = runs[index].model_copy(update=updates)
    return source.model_copy(update={"repetitions": tuple(runs)})


def alter_cell(source: Report, update: Callable[[Cell], Cell], window: int = 6) -> Report:
    index = next(
        i
        for i, run in enumerate(source.repetitions)
        if run.model == MODELS[0] and run.window_seconds == window
    )
    run = source.repetitions[index]
    return alter_run(source, index, cells=(update(run.cells[0]), run.cells[1]))


def map_scores(cell: Cell, update: Callable[[ScriptScore], ScriptScore]) -> Cell:
    return cell.model_copy(update={"scripts": tuple(update(s) for s in cell.scripts)})


def map_segments(cell: Cell, update: Callable[[Segment], Segment]) -> Cell:
    return map_scores(
        cell,
        lambda score: score.model_copy(
            update={
                "segments": tuple(update(segment) for segment in score.segments),
            }
        ),
    )


def test_complete_matrix_all_decision_branches_and_both_models_required() -> None:
    good = report()
    assert evaluate(good).state == "qualified_1_7b"
    failed_large = alter_run(good, 0, silence_nonempty_finals=1)
    assert evaluate(failed_large).state == "qualified_0_6b"
    failed_both = alter_run(failed_large, 1, silence_nonempty_partials=1)
    assert evaluate(failed_both).state == "neither_qualifies"
    incomplete = good.model_copy(update={"repetitions": good.repetitions[:-1]})
    assert evaluate(incomplete).state == "blocked_evidence"
    assert evaluate(good.model_copy(update={"interrupted": True})).state == "blocked_evidence"


def test_missing_source_manifest_privacy_and_process_evidence_block() -> None:
    good = report()
    assert evaluate(
        good.model_copy(update={"scored_on": good.scored_on + timedelta(days=1)})
    ).missing
    assert evaluate(good.model_copy(update={"manifests": good.manifests[:1]})).missing
    assert evaluate(alter_run(good, 0, process_id=good.repetitions[1].process_id)).missing
    assert evaluate(alter_run(good, 0, order=1)).missing
    assert evaluate(good.model_copy(update={"corpus_sha256": "0" * 64})).missing
    assert evaluate(
        alter_cell(good, lambda c: c.model_copy(update={"scripts": c.scripts[:-1]}))
    ).missing
    assert evaluate(
        alter_cell(
            good,
            lambda c: map_scores(
                c,
                lambda s: s.model_copy(
                    update={
                        "reference_characters": 41,
                    }
                ),
            ),
        )
    ).missing
    assert evaluate(
        alter_cell(
            good,
            lambda c: map_segments(
                c,
                lambda s: s.model_copy(
                    update={
                        "timing": s.timing.model_copy(update={"t0_ns": 0}),
                    }
                ),
            ),
        )
    ).missing


@pytest.mark.parametrize(
    "field,limit",
    [
        ("incremental_peak_physical_bytes", 8 * 1024**3),
        ("peak_canonical_bytes", 960_000),
        ("peak_audio_bytes", 16_777_216),
        ("peak_media_duration_ns", 30 * NS),
    ],
)
def test_memory_threshold_equality_and_just_outside(field: str, limit: int) -> None:
    assert evaluate(alter_run(report(), 0, **{field: limit})).state == "qualified_1_7b"
    assert evaluate(alter_run(report(), 0, **{field: limit + 1})).state == "qualified_0_6b"


def test_cold_population_not_pooled_with_warm_and_load_boundary() -> None:
    good = report()
    cold = good.repetitions[0].cold
    at_limit = cold.model_copy(
        update={
            "ready_ns": cold.load_start_ns + 30 * NS,
            "first_inference_start_ns": 31 * NS,
            "first_inference_end_ns": 31 * NS + 1,
            "first_final_ns": 32 * NS,
        }
    )
    # Move only process-start/load observations while preserving its first-final clock.
    at_limit = cold.model_copy(
        update={
            "process_start_ns": 0,
            "load_start_ns": 0,
            "ready_ns": 30 * NS,
            "first_inference_start_ns": 31 * NS,
            "first_inference_end_ns": 31 * NS + 1,
            "first_final_ns": 32 * NS,
        }
    )
    changed = alter_run(good, 0, cold=at_limit)
    # The changed cold end overlaps the first warm row: this must block.
    assert evaluate(changed).state == "blocked_evidence"
    populations = cold_populations(good)
    assert all(v["load_ns"]["count"] == 3 for v in populations.values())
    assert all(v["load_ns"]["p95"] == NS - 1 for v in populations.values())


@pytest.mark.parametrize("errors,expected", [(4, "qualified_1_7b"), (5, "qualified_0_6b")])
def test_clean_micro_cer_limit(errors: int, expected: str) -> None:
    changed = alter_cell(
        report(),
        lambda c: map_scores(
            c,
            lambda s: s.model_copy(
                update={
                    "substitutions": errors,
                }
            ),
        ),
    )
    assert evaluate(changed).state == expected


def test_quality_nonproduction_window_reports_but_does_not_replace_six_second_gate() -> None:
    changed = alter_cell(
        report(),
        lambda c: map_scores(
            c,
            lambda s: s.model_copy(
                update={
                    "substitutions": 40,
                }
            ),
        ),
        window=1,
    )
    assert evaluate(changed).state == "qualified_1_7b"
    failed = alter_cell(
        changed,
        lambda c: map_scores(
            c,
            lambda s: s.model_copy(
                update={
                    "substitutions": 40,
                }
            ),
        ),
    )
    assert evaluate(failed).state == "qualified_0_6b"


def test_partial_stability_denominator_and_missing_partial_are_failures() -> None:
    changed = alter_cell(
        report(),
        lambda c: map_segments(
            c,
            lambda s: s.model_copy(
                update={
                    "rewrite_severity": Count(numerator=1, denominator=10),
                }
            ),
        ),
    )
    assert evaluate(changed).state == "qualified_1_7b"
    changed = alter_cell(
        changed,
        lambda c: map_segments(
            c,
            lambda s: s.model_copy(
                update={
                    "rewrite_severity": Count(numerator=1, denominator=9),
                }
            ),
        ),
    )
    assert evaluate(changed).state == "qualified_0_6b"
    no_partial = alter_cell(
        report(),
        lambda c: map_segments(
            c,
            lambda s: s.model_copy(
                update={
                    "timing": s.timing.model_copy(update={"tp_ns": None}),
                }
            ),
        ),
        window=1,
    )
    assert evaluate(no_partial).state == "qualified_0_6b"
    assert any("failed_sample" in value for value in evaluate(no_partial).failed_1_7b)


def test_four_second_boundary_gate_cannot_be_skipped() -> None:
    def duplicate(score: ScriptScore) -> ScriptScore:
        denominator = score.boundary_duplicate.denominator
        return score.model_copy(
            update={
                "boundary_duplicate": Count(
                    numerator=1 if denominator else 0,
                    denominator=denominator,
                )
            }
        )

    assert (
        evaluate(alter_cell(report(), lambda c: map_scores(c, duplicate), 4)).state
        == "qualified_0_6b"
    )
    missing = alter_cell(
        report(),
        lambda c: map_scores(
            c,
            lambda s: s.model_copy(
                update={
                    "boundary_duplicate": Count(numerator=0, denominator=0),
                }
            ),
        ),
        4,
    )
    assert evaluate(missing).state == "blocked_evidence"


def test_timing_population_includes_every_call_and_rtf_excludes_replay_and_overlap() -> None:
    measured = timing(6, 800_000_000)
    assert measured.measures()["rtf"] == 48_000_000 / (6 * NS)
    assert measured.calls[-1].rtf == 2_000_000 / 6_800_000_000
    cell = report().repetitions[0].cells[0]
    populations = cell_populations(cell)
    assert populations["preparation_ns"]["count"] == populations["rtf"]["count"] * 4
    assert populations["final_queue_wait_ns"]["p95"] == 0


def test_invalid_timing_nonfinite_fields_and_unknown_machine_fields() -> None:
    measured = timing()
    data = measured.model_dump()
    data["tp_ns"] = data["tf_ns"]
    with pytest.raises(ValidationError, match="partial_observation"):
        SegmentTiming.model_validate(data)
    data = measured.calls[0].model_dump()
    data["execution_end_ns"] = float("nan")
    with pytest.raises(ValidationError):
        Call.model_validate(data)
    data = report().machine.model_dump()
    data["hostname"] = "private-host"
    with pytest.raises(ValidationError):
        Machine.model_validate(data)


def test_distinct_corpus_and_speaker_balance() -> None:
    data = corpus().model_dump()
    scripts = list(corpus().scripts)
    scripts[1] = scripts[1].model_copy(update={"reference": scripts[0].reference})
    data["scripts"] = tuple(scripts)
    with pytest.raises(ValidationError, match="distinct_scripts"):
        Corpus.model_validate(data)


def test_plan_alternates_models_and_scores_sorted_sources_in_independent_processes() -> None:
    plans = matrix_plan(corpus())
    assert len(plans) == 24
    assert plans[0].model == MODELS[0] and plans[8].model == MODELS[1]
    assert all(p.script_ids == tuple(sorted(p.script_ids)) and p.warmup_count == 3 for p in plans)


def test_transient_text_scoring_discards_text_from_report() -> None:
    script = corpus().scripts[0]
    observations = tuple(
        SegmentText(
            start_ns=start * NS,
            end_ns=(start + 6) * NS,
            partials=tuple(
                script.reference[start // 6 * 20 : start // 6 * 20 + min(i, 20)]
                for i in range(1, 24)
            ),
            final=script.reference[start // 6 * 20 : (start // 6 + 1) * 20],
            timing=timing(6, origin=start * NS),
        )
        for start in (0, 6)
    )
    scored = score_script(script, observations, 6)
    assert scored.substitutions == scored.deletions == scored.insertions == 0
    assert all(span.exact.numerator == span.exact.denominator for span in scored.targets)
    assert script.reference not in scored.model_dump_json()
