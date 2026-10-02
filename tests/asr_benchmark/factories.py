"""Synthetic metadata records, never installed in an executable allowlist."""

from datetime import date
from functools import lru_cache
from typing import Literal, cast

from tools.asr_benchmark.contracts import (
    MODELS,
    NS,
    Approval,
    Asset,
    CharacterTime,
    Condition,
    Corpus,
    InferenceManifest,
    Machine,
    Mirror,
    Model,
    PreparationManifest,
    PrivacyEvidence,
    Rights,
    Script,
    Settings,
    Source,
    SpanClass,
    Stratum,
    Target,
    TensorRule,
    Window,
    metadata_digest,
)
from tools.asr_benchmark.conversion import TensorInventory
from tools.asr_benchmark.report import (
    Cell,
    Cold,
    Count,
    Repetition,
    Report,
    ScriptScore,
    Segment,
    SpanScore,
)
from tools.asr_benchmark.runner import matrix_plan
from tools.asr_benchmark.timing import Call, SegmentTiming

DIGEST = "0123456789abcdef" * 4
REVISION = "0123456789" * 4
TODAY = date(2026, 10, 2)
APPROVAL = Approval(
    owner="test-owner",
    reviewer="test-reviewer",
    approved_on=TODAY,
    evidence_id="test-only",
)


def preparation(model: Model = MODELS[0]) -> PreparationManifest:
    assets = tuple(
        Asset(
            path=path,
            size=100,
            sha256=DIGEST,
            kind=cast(Literal["weights", "tokenizer", "config", "notice"], kind),
        )
        for path, kind in (
            ("model.safetensors", "weights"),
            ("tokenizer.json", "tokenizer"),
            ("config.json", "config"),
            ("NOTICE.txt", "notice"),
        )
    )
    rights = Rights(
        license_id="test-only",
        notice_ids=("test-notice",),
        use_scope="local-preparation",
        approval=APPROVAL,
    )
    return PreparationManifest(
        manifest_id="test-preparation",
        model=model,
        source_revision=REVISION,
        source_assets=assets,
        source_rights=rights,
        tokenizer_rights=rights,
        conversion_rights=rights,
        converter_revision=REVISION,
        dependency_lock_sha256=DIGEST,
        tensor_map=(
            TensorRule(
                name="independent_test_matrix",
                source_dtype="float32",
                operation="affine-8bit-group64",
                classification="linear",
            ),
        ),
        mirrors=tuple(
            Mirror(
                mode=cast(Literal["huggingface", "modelscope"], mode),
                repository=model,
                revision=REVISION,
                assets=assets,
                approval=APPROVAL,
            )
            for mode in ("huggingface", "modelscope")
        ),
        approval=APPROVAL,
    )


def inference(model: Model) -> InferenceManifest:
    prep = preparation(model)
    return InferenceManifest(
        manifest_id="test-inference",
        model=model,
        preparation_sha256=metadata_digest(prep),
        converted_assets=prep.source_assets,
        tensor_map_sha256=metadata_digest(TensorInventory(tensors=prep.tensor_map)),
        provider_revision=REVISION,
        dependency_lock_sha256=DIGEST,
        inference_rights=Rights(
            license_id="test-only",
            notice_ids=("test-notice",),
            use_scope="local-inference",
            approval=APPROVAL,
        ),
        approval=APPROVAL,
    )


@lru_cache
def corpus() -> Corpus:
    rights = Rights(
        license_id="test-only",
        notice_ids=("test-notice",),
        use_scope="transient-benchmark",
        approval=APPROVAL,
    )
    sources = tuple(
        Source(
            source_id=f"source-{i}",
            publisher_id="test-publisher",
            speaker_id=f"speaker-{i}",
            consent_evidence_id="test-consent",
            adult_consent=True,
            item_id=f"item-{i}",
            immutable_version="test-v1",
            transient_processing=True,
            reference_retention=True,
            result_retention=True,
            reproducible_rendition=True,
            expires_on=TODAY,
            revoked=False,
            rights=rights,
        )
        for i in range(3)
    )
    strata: tuple[Stratum, ...] = ("mandarin", "names", "numbers", "code_switching", "continuous")
    scripts = tuple(
        Script(
            script_id=f"script-{i:02d}-{j:02d}",
            stratum=stratum,
            source_id=f"source-{j % 3}",
            reference=f"春夏秋冬天地山川风雨雷电江河湖海东西南北青红黄白日月星辰花草树木人间故事{i:02d}{j:02d}",
            character_times=tuple(
                CharacterTime(
                    start_ns=k * 300_000_000,
                    end_ns=(k + 1) * 300_000_000,
                )
                for k in range(40)
            ),
            targets=(
                Target(kind="name", start=0, end=2),
                Target(kind="number", start=2, end=4),
                Target(kind="english", start=4, end=6),
            ),
            noise_seed=i * 12 + j,
        )
        for i, stratum in enumerate(strata)
        for j in range(12)
    )
    return Corpus(corpus_id="test-corpus", sources=sources, scripts=scripts, approval=APPROVAL)


def timing(window: Window = 6, overlap: int = 0, origin: int = 0) -> SegmentTiming:
    partials = tuple(
        Call(
            kind="provisional",
            preparation_start_ns=tick,
            preparation_end_ns=tick + 1_000_000,
            execution_start_ns=tick + 1_000_000,
            execution_end_ns=tick + 2_000_000,
            input_duration_ns=tick + overlap,
            overlap_duration_ns=overlap,
            synchronized=True,
            output_tokens=2,
        )
        for tick in range(250_000_000, window * NS, 250_000_000)
    )
    final = Call(
        kind="final",
        preparation_start_ns=window * NS,
        preparation_end_ns=window * NS + 1_000_000,
        execution_start_ns=window * NS + 1_000_000,
        execution_end_ns=window * NS + 2_000_000,
        input_duration_ns=window * NS + overlap,
        overlap_duration_ns=overlap,
        synchronized=True,
        output_tokens=2,
    )
    result = SegmentTiming(
        t0_ns=0,
        te_ns=window * NS,
        tc_ns=window * NS,
        tp_ns=252_000_000,
        tf_ns=window * NS + 2_000_000,
        new_duration_ns=window * NS,
        calls=(*partials, final),
        missed_partial_opportunities=0,
        evaluated_prefixes=len(partials),
    )
    clock_fields = (
        "preparation_start_ns",
        "preparation_end_ns",
        "execution_start_ns",
        "execution_end_ns",
    )
    return result.model_copy(
        update={
            "t0_ns": origin,
            "te_ns": result.te_ns + origin,
            "tc_ns": result.tc_ns + origin,
            "tp_ns": 252_000_000 + origin,
            "tf_ns": result.tf_ns + origin,
            "calls": tuple(
                call.model_copy(
                    update={field: getattr(call, field) + origin for field in clock_fields}
                )
                for call in result.calls
            ),
        }
    )


def script_score(script: Script, window: Window, origin: int = 0) -> ScriptScore:
    segments = tuple(
        Segment(
            start_ns=start * NS,
            end_ns=(start + window) * NS,
            timing=timing(
                window,
                800_000_000
                if (start > 0 and script.stratum == "continuous" and window in (4, 6))
                else 0,
                origin + start * NS,
            ),
            rewrite_frequency=Count(numerator=0, denominator=window * 4 - 2),
            rewrite_severity=Count(numerator=0, denominator=2),
            finalization_changes=Count(numerator=0, denominator=1),
        )
        for start in range(0, 12, window)
    )
    boundary = (
        sum(
            t.start_ns < s.start_ns and t.end_ns > s.start_ns - 800_000_000
            for s in segments[1:]
            for t in script.character_times
        )
        if script.stratum == "continuous" and window in (4, 6)
        else 0
    )
    return ScriptScore(
        script_id=script.script_id,
        substitutions=0,
        insertions=0,
        deletions=0,
        reference_characters=40,
        targets=tuple(
            SpanScore(kind=cast(SpanClass, kind), exact=Count(numerator=1, denominator=1))
            for kind in ("name", "number", "english")
        ),
        boundary_duplicate=Count(numerator=0, denominator=boundary),
        boundary_omission=Count(numerator=0, denominator=boundary),
        segments=segments,
    )


@lru_cache
def report() -> Report:
    current_corpus = corpus()
    manifests = tuple(inference(model) for model in MODELS)
    repetitions = tuple(
        Repetition(
            model=plan.model,
            window_seconds=plan.window_seconds,
            repetition=cast(Literal[1, 2, 3], plan.repetition),
            process_id=f"process-{index}",
            order=cast(Literal[0, 1], plan.order),
            model_manifest_sha256=metadata_digest(manifests[MODELS.index(plan.model)]),
            cold=Cold(
                script_id=plan.cold_script_id,
                condition="clean",
                process_start_ns=0,
                load_start_ns=1,
                ready_ns=NS,
                first_inference_start_ns=2 * NS,
                first_inference_end_ns=2 * NS + 1,
                first_final_ns=3 * NS,
            ),
            unscored_warmups=3,
            cells=tuple(
                Cell(
                    condition=cast(Condition, condition),
                    scripts=tuple(
                        script_score(
                            s,
                            plan.window_seconds,
                            (condition_index * 60 + script_index + 1) * 20 * NS,
                        )
                        for script_index, s in enumerate(current_corpus.scripts)
                    ),
                )
                for condition_index, condition in enumerate(("clean", "noise"))
            ),
            silence_duration_ns=60_000_000_000,
            silence_nonempty_finals=0,
            silence_nonempty_partials=0,
            incremental_peak_physical_bytes=1024,
            audio_pageouts=0,
            peak_canonical_bytes=1024,
            peak_audio_bytes=1024,
            peak_media_duration_ns=6 * NS,
            teardown_passed=True,
            write_sinks_passed=True,
        )
        for index, plan in enumerate(matrix_plan(current_corpus))
    )
    return Report(
        run_id="test-only",
        scored_on=TODAY,
        corpus=current_corpus,
        corpus_sha256=metadata_digest(current_corpus),
        manifests=manifests,
        preparations=tuple(preparation(model) for model in MODELS),
        machine=Machine(
            chip="Apple M3 Ultra",
            cpu_cores=32,
            gpu_cores=80,
            physical_ram_bytes=96 * 1024**3,
            os_build="test-only",
            power_mode="test-only",
            thermal_status="test-only",
            python_version="test-only",
            mlx_version="unavailable",
            provider_version="unavailable",
            converter_version="unavailable",
            dependency_lock_sha256=DIGEST,
            code_revision=REVISION,
            cache_state="verified-cached-weights",
            measurement_method="test",
        ),
        privacy=PrivacyEvidence(
            evidence_id="test-only",
            reviewed_code_revision=REVISION,
            host_evidence_id="test-only",
            allocation_inventory_id="test-only",
            write_sink_observation_id="test-only",
            no_paging=True,
            no_core_dumps=True,
            no_audio_tracing=True,
            no_tensor_dumps=True,
            no_profiler_snapshots=True,
            no_media_cache=True,
            teardown_failure_injection=True,
            approval=APPROVAL,
        ),
        settings=Settings(),
        repetitions=repetitions,
        interrupted=False,
    )
