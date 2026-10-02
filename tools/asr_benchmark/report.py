"""Complete matrix validation and fixed Issue #5 gates. Never selects from a partial run."""

from collections import Counter
from datetime import date
from typing import Literal, Self

from pydantic import model_validator

from .contracts import (
    MODELS,
    NS,
    STRATA,
    WINDOWS,
    Closed,
    Condition,
    Corpus,
    Digest,
    Identifier,
    InferenceManifest,
    Machine,
    Model,
    Nonnegative,
    Positive,
    PreparationManifest,
    PrivacyEvidence,
    Settings,
    SpanClass,
    Window,
    metadata_digest,
)
from .conversion import bind_inference
from .metrics import normalize, percentiles
from .runtime import BlockedEvidence
from .timing import SegmentTiming


class Count(Closed):
    numerator: Nonnegative
    denominator: Nonnegative

    @property
    def ratio(self) -> float | None:
        return self.numerator / self.denominator if self.denominator else None


class SpanScore(Closed):
    kind: SpanClass
    exact: Count

    @model_validator(mode="after")
    def count(self) -> Self:
        if self.exact.numerator > self.exact.denominator:
            raise ValueError("span_count")
        return self


class Segment(Closed):
    start_ns: Nonnegative
    end_ns: Positive
    timing: SegmentTiming
    rewrite_frequency: Count
    rewrite_severity: Count
    finalization_changes: Count
    failure: (
        Literal[
            "input_stall",
            "provider_timeout",
            "invalid_timing",
            "budget_exceeded",
            "digest_failure",
            "cancelled",
            "provider_failure",
            "output_limit",
            "missing_partial",
        ]
        | None
    ) = None

    @model_validator(mode="after")
    def consistency(self) -> Self:
        if self.end_ns - self.start_ns != self.timing.new_duration_ns:
            raise ValueError("segment_duration")
        if self.rewrite_frequency.denominator != max(0, self.timing.evaluated_prefixes - 1):
            raise ValueError("rewrite_pairs")
        for count in (self.rewrite_frequency, self.rewrite_severity, self.finalization_changes):
            if count.numerator > count.denominator:
                raise ValueError("rewrite_count")
        return self


class ScriptScore(Closed):
    script_id: Identifier
    substitutions: Nonnegative
    deletions: Nonnegative
    insertions: Nonnegative
    reference_characters: Positive
    targets: tuple[SpanScore, ...]
    boundary_duplicate: Count
    boundary_omission: Count
    segments: tuple[Segment, ...]
    failure: (
        Literal[
            "input_stall",
            "provider_timeout",
            "invalid_timing",
            "budget_exceeded",
            "digest_failure",
            "cancelled",
            "provider_failure",
        ]
        | None
    ) = None

    @model_validator(mode="after")
    def consistency(self) -> Self:
        if self.substitutions + self.deletions > self.reference_characters:
            raise ValueError("alignment_counts")
        if len({score.kind for score in self.targets}) != len(self.targets):
            raise ValueError("target_duplicate")
        if self.boundary_duplicate.denominator != self.boundary_omission.denominator:
            raise ValueError("boundary_denominators")
        if self.boundary_omission.numerator > self.boundary_omission.denominator:
            raise ValueError("boundary_omissions")
        return self


class Cell(Closed):
    condition: Condition
    scripts: tuple[ScriptScore, ...]


class Cold(Closed):
    script_id: Identifier
    condition: Literal["clean"]
    process_start_ns: Nonnegative
    load_start_ns: Nonnegative
    ready_ns: Nonnegative
    first_inference_start_ns: Nonnegative
    first_inference_end_ns: Nonnegative
    first_final_ns: Nonnegative

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if not (
            self.process_start_ns
            <= self.load_start_ns
            <= self.ready_ns
            <= self.first_inference_start_ns
            <= self.first_inference_end_ns
            <= self.first_final_ns
        ):
            raise ValueError("cold_timing")
        return self


class Repetition(Closed):
    model: Model
    window_seconds: Window
    repetition: Literal[1, 2, 3]
    process_id: Identifier  # Opaque run-local ID, never an OS PID/hostname.
    order: Literal[0, 1]
    model_manifest_sha256: Digest
    cold: Cold
    unscored_warmups: Literal[3]
    cells: tuple[Cell, ...]
    silence_duration_ns: Literal[60_000_000_000]
    silence_nonempty_finals: Nonnegative
    silence_nonempty_partials: Nonnegative
    incremental_peak_physical_bytes: Nonnegative
    audio_pageouts: Nonnegative
    peak_canonical_bytes: Nonnegative
    peak_audio_bytes: Nonnegative
    peak_media_duration_ns: Nonnegative
    teardown_passed: bool
    write_sinks_passed: bool


class Report(Closed):
    schema_version: Literal[1] = 1
    run_id: Identifier
    scored_on: date
    measurement_scope: Literal["provider-local-pipeline"] = "provider-local-pipeline"
    corpus: Corpus
    corpus_sha256: Digest
    manifests: tuple[InferenceManifest, ...]
    preparations: tuple[PreparationManifest, ...]
    machine: Machine
    privacy: PrivacyEvidence
    settings: Settings
    repetitions: tuple[Repetition, ...]
    interrupted: bool


class Decision(Closed):
    state: Literal["blocked_evidence", "neither_qualifies", "qualified_1_7b", "qualified_0_6b"]
    missing: tuple[str, ...]
    failed_1_7b: tuple[str, ...]
    failed_0_6b: tuple[str, ...]
    owner_adr_required: Literal[True] = True


def _coverage(report: Report) -> list[str]:
    missing: list[str] = []
    if report.interrupted:
        missing.append("interrupted")
    if metadata_digest(report.corpus) != report.corpus_sha256:
        missing.append("corpus_digest")
    if not report.corpus.sources_current(report.scored_on):
        missing.append("source_rights")
    if report.machine.code_revision != report.privacy.reviewed_code_revision:
        missing.append("privacy_revision")
    manifests = {manifest.model: manifest for manifest in report.manifests}
    if set(manifests) != set(MODELS) or len(report.manifests) != 2:
        missing.append("manifest_inventory")
    preparations = {manifest.model: manifest for manifest in report.preparations}
    if set(preparations) != set(MODELS) or len(report.preparations) != 2:
        missing.append("preparation_inventory")
    for model, inference_manifest in manifests.items():
        if model not in preparations:
            missing.append("preparation_inventory")
        else:
            try:
                bind_inference(preparations[model], inference_manifest)
            except BlockedEvidence:
                missing.append("inference_preparation_binding")
    expected = {(model, window, rep) for model in MODELS for window in WINDOWS for rep in (1, 2, 3)}
    actual = {(r.model, r.window_seconds, r.repetition) for r in report.repetitions}
    if actual != expected or len(report.repetitions) != len(expected):
        missing.append("matrix")
    if len({r.process_id for r in report.repetitions}) != len(report.repetitions):
        missing.append("independent_processes")
    scripts = {s.script_id: s for s in report.corpus.scripts}
    first_script = min(scripts)
    for run in report.repetitions:
        label = f"{run.model}:{run.window_seconds}:{run.repetition}"
        manifest = manifests.get(run.model)
        if manifest is None or run.model_manifest_sha256 != metadata_digest(manifest):
            missing.append(f"{label}:manifest_digest")
        if manifest and manifest.dependency_lock_sha256 != report.machine.dependency_lock_sha256:
            missing.append(f"{label}:lock_digest")
        expected_order = (
            MODELS.index(run.model) if run.repetition % 2 else 1 - MODELS.index(run.model)
        )
        if run.order != expected_order or run.cold.script_id != first_script:
            missing.append(f"{label}:run_order")
        if {c.condition for c in run.cells} != {"clean", "noise"} or len(run.cells) != 2:
            missing.append(f"{label}:conditions")
        previous_execution_end = run.cold.first_final_ns
        for cell in run.cells:
            if [s.script_id for s in cell.scripts] != sorted(scripts):
                missing.append(f"{label}:{cell.condition}:script_inventory")
            for score in cell.scripts:
                script = scripts.get(score.script_id)
                if script is None:
                    continue
                if score.reference_characters != len(normalize(script.reference)):
                    missing.append(f"{label}:reference_denominator")
                targets = Counter(target.kind for target in script.targets)
                if {s.kind: s.exact.denominator for s in score.targets} != targets:
                    missing.append(f"{label}:target_denominator")
                end = 0
                boundary_denominator = 0
                origin = score.segments[0].timing.t0_ns if score.segments else 0
                for segment in score.segments:
                    if (
                        segment.timing.t0_ns != origin + segment.start_ns
                        or segment.timing.tc_ns != origin + segment.end_ns
                        or segment.timing.calls[0].preparation_start_ns < previous_execution_end
                    ):
                        missing.append(f"{label}:process_clock")
                    previous_execution_end = segment.timing.tf_ns
                    if segment.start_ns != end or not (
                        segment.start_ns < segment.end_ns <= 12 * NS
                        and segment.end_ns - segment.start_ns <= run.window_seconds * NS
                    ):
                        missing.append(f"{label}:segment_coverage")
                    end = segment.end_ns
                    overlap = (
                        800_000_000
                        if segment.start_ns > 0
                        and script.stratum == "continuous"
                        and run.window_seconds in (4, 6)
                        else 0
                    )
                    if any(c.overlap_duration_ns != overlap for c in segment.timing.calls):
                        missing.append(f"{label}:overlap_duration")
                    if (
                        script.stratum == "continuous"
                        and segment.timing.te_ns != segment.timing.tc_ns
                    ):
                        missing.append(f"{label}:continuous_timing")
                    if overlap:
                        boundary_denominator += sum(
                            timing.start_ns < segment.start_ns
                            and timing.end_ns > segment.start_ns - overlap
                            for timing in script.character_times
                        )
                if end != 12 * NS and score.failure is None:
                    missing.append(f"{label}:segment_coverage")
                if score.boundary_duplicate.denominator != boundary_denominator:
                    missing.append(f"{label}:boundary_denominator")
    return sorted(set(missing))


def cell_populations(cell: Cell) -> dict[str, dict[str, float | int]]:
    values: dict[str, list[float | int]] = {}
    for script in cell.scripts:
        for segment in script.segments:
            for name, value in segment.timing.measures().items():
                values.setdefault(name, []).append(value)
            for call in segment.timing.calls:
                values.setdefault("preparation_ns", []).append(
                    call.preparation_end_ns - call.preparation_start_ns
                )
                values.setdefault("per_call_rtf", []).append(call.rtf)
    return {name: percentiles(population) for name, population in values.items()}


def cold_populations(report: Report) -> dict[str, dict[str, dict[str, float | int]]]:
    result = {}
    for model in MODELS:
        for window in WINDOWS:
            rows = [
                r.cold
                for r in report.repetitions
                if r.model == model and r.window_seconds == window
            ]
            if rows:
                result[f"{model}:{window}"] = {
                    "load_ns": percentiles([r.ready_ns - r.load_start_ns for r in rows]),
                    "first_inference_ns": percentiles(
                        [r.first_inference_end_ns - r.first_inference_start_ns for r in rows]
                    ),
                    "first_final_from_process_ns": percentiles(
                        [r.first_final_ns - r.process_start_ns for r in rows]
                    ),
                }
    return result


def _quality(report: Report, run: Repetition, cell: Cell) -> list[str]:
    failures: list[str] = []
    scripts = {s.script_id: s for s in report.corpus.scripts}
    if run.window_seconds == 6:
        limits = (0.1, 0.15, 0.9) if cell.condition == "clean" else (0.2, 0.25, 0.8)
        for stratum in (None, *STRATA):
            selected = [
                score
                for score in cell.scripts
                if stratum is None or scripts[score.script_id].stratum == stratum
            ]
            errors = sum(s.substitutions + s.deletions + s.insertions for s in selected)
            denominator = sum(s.reference_characters for s in selected)
            if not denominator or errors / denominator > limits[0 if stratum is None else 1]:
                failures.append(f"cer:{stratum or 'micro'}")
        for kind in ("name", "number", "english"):
            counts = [t.exact for s in cell.scripts for t in s.targets if t.kind == kind]
            denominator = sum(count.denominator for count in counts)
            if not denominator or sum(c.numerator for c in counts) / denominator < limits[2]:
                failures.append(f"target:{kind}")
        for field, limit in (("rewrite_frequency", 0.25), ("rewrite_severity", 0.1)):
            counts = [getattr(segment, field) for s in cell.scripts for segment in s.segments]
            denominator = sum(count.denominator for count in counts)
            if not denominator or sum(c.numerator for c in counts) / denominator > limit:
                failures.append(field)
    if run.window_seconds in (4, 6):
        continuous = [s for s in cell.scripts if scripts[s.script_id].stratum == "continuous"]
        for field, limit in (("boundary_duplicate", 0.01), ("boundary_omission", 0.02)):
            counts = [getattr(s, field) for s in continuous]
            denominator = sum(c.denominator for c in counts)
            if not denominator or sum(c.numerator for c in counts) / denominator > limit:
                failures.append(field)
    return failures


def evaluate(report: Report) -> Decision:
    missing = _coverage(report)
    if missing:
        return Decision(
            state="blocked_evidence", missing=tuple(missing), failed_1_7b=(), failed_0_6b=()
        )
    failures: dict[Model, list[str]] = {model: [] for model in MODELS}
    for run in report.repetitions:
        current: list[str] = []
        if run.cold.ready_ns - run.cold.load_start_ns > 30 * NS:
            current.append("cold_load")
        if run.incremental_peak_physical_bytes > 8 * 1024**3:
            current.append("physical_footprint")
        if (
            run.audio_pageouts
            or run.peak_canonical_bytes > 960_000
            or run.peak_audio_bytes > 16_777_216
            or run.peak_media_duration_ns > 30 * NS
            or not run.teardown_passed
            or not run.write_sinks_passed
        ):
            current.append("privacy")
        if run.silence_nonempty_finals or run.silence_nonempty_partials:
            current.append("silence")
        for cell in run.cells:
            limits = {
                "rtf": 0.70,
                "segmentation_wait_ns": 600_000_000,
                "preparation_ns": 100_000_000,
                "first_partial_ns": 1_500_000_000,
                "provider_first_text_ns": 750_000_000,
                "provider_final_ns": min(2_000_000_000, 700_000_000 * run.window_seconds),
                "speech_end_to_final_ns": 2_600_000_000,
            }
            populations = cell_populations(cell)
            failed = [
                name
                for name, limit in limits.items()
                if name not in populations or populations[name]["p95"] > limit
            ]
            if any(score.failure for score in cell.scripts) or any(
                s.failure or s.timing.failed for score in cell.scripts for s in score.segments
            ):
                failed.append("failed_sample")
            failed.extend(_quality(report, run, cell))
            current.extend(f"{cell.condition}:{name}" for name in failed)
        failures[run.model].extend(
            f"{run.window_seconds}:{run.repetition}:{name}" for name in current
        )
    large, small = (tuple(sorted(set(failures[model]))) for model in MODELS)
    state: Literal["neither_qualifies", "qualified_1_7b", "qualified_0_6b"] = (
        "qualified_1_7b" if not large else "qualified_0_6b" if not small else "neither_qualifies"
    )
    return Decision(state=state, missing=(), failed_1_7b=large, failed_0_6b=small)
