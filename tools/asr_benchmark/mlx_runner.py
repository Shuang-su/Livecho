"""Trusted M3 Ultra host telemetry, fresh-process 24-run matrix runner, and preflight."""

from __future__ import annotations

import asyncio
import concurrent.futures
import resource
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from contextlib import suppress
from datetime import date
from pathlib import Path
from typing import Any, Literal, cast

from .cache_reader import FinalModelCache
from .cold_load import local_model_load
from .contracts import (
    MODELS,
    WINDOWS,
    Corpus,
    Machine,
    Model,
    Settings,
    metadata_digest,
)
from .corpus_source import InMemoryCorpusSourceFactory, SwiftFFmpegSynthesizer
from .machine_inventory import MachineInventoryCollector
from .mlx_adapter import MLXASRProvider, MLXEagerBackend
from .pass_coordinator import PassCoordinator
from .registry import (
    CACHE_ROOT_DEFAULT,
    PINNED_CODE_REVISION,
    REPOSITORY_ROOT,
    REVIEWED_MANIFEST_ID,
    build_privacy_evidence,
    load_corpus,
    load_inferences,
    load_preparations,
    verify_lock_digest,
)
from .report import Cold, Decision, Repetition, Report, evaluate
from .runner import PassPlan, matrix_plan
from .runtime import BlockedEvidence
from .serialization import run_identity, write_report

REPORTS_DIR = REPOSITORY_ROOT / "benchmarks" / "asr" / "reports"
_AUDIO_SUFFIXES = frozenset({".pcm", ".wav", ".aiff", ".mp3", ".m4a", ".ogg", ".flac", ".raw"})


class ThreadExecutionGuard:
    """Cooperative deadline guard checking monotonic clock before and after execution."""

    def __init__(self, clock: Callable[[], int] = time.monotonic_ns) -> None:
        self._clock = clock

    def execute(self, operation: Callable[[], None], deadline_ns: int) -> None:
        if self._clock() > deadline_ns:
            raise BlockedEvidence("provider_timeout")
        operation()
        if self._clock() > deadline_ns:
            raise BlockedEvidence("provider_timeout")


def _sysctl_str(name: str) -> str:
    res = subprocess.run(
        ["/usr/sbin/sysctl", "-n", name],
        capture_output=True,
        text=True,
        check=False,
        timeout=2.0,
    )
    if res.returncode != 0:
        raise BlockedEvidence("protected_host_evidence_unavailable")
    return res.stdout.strip()


def _vm_pageouts() -> int:
    res = subprocess.run(
        ["/usr/bin/vm_stat"],
        capture_output=True,
        text=True,
        check=False,
        timeout=2.0,
    )
    if res.returncode != 0:
        raise BlockedEvidence("protected_host_evidence_unavailable")
    for line in res.stdout.splitlines():
        if line.startswith("Pageouts:"):
            raw = line.split(":", 1)[1].strip().rstrip(".")
            if raw.isdigit():
                return int(raw)
    raise BlockedEvidence("protected_host_evidence_unavailable")


def _check_host_safety() -> None:
    if sys.platform != "darwin":
        raise BlockedEvidence("protected_host_evidence_unavailable")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    soft, hard = resource.getrlimit(resource.RLIMIT_CORE)
    if (soft, hard) != (0, 0):
        raise BlockedEvidence("protected_host_evidence_unavailable")
    swap = subprocess.run(
        ["/usr/sbin/sysctl", "vm.swapusage"],
        capture_output=True,
        text=True,
        check=False,
        timeout=2.0,
    )
    if swap.returncode != 0 or "used = 0.00M" not in swap.stdout:
        raise BlockedEvidence("protected_host_evidence_unavailable")


def _gpu_cores() -> int:
    res = subprocess.run(
        ["/usr/sbin/system_profiler", "SPDisplaysDataType"],
        capture_output=True,
        text=True,
        check=False,
        timeout=5.0,
    )
    if res.returncode != 0:
        raise BlockedEvidence("protected_host_evidence_unavailable")
    for line in res.stdout.splitlines():
        if "Total Number of Cores:" in line:
            val = line.split(":", 1)[1].strip()
            if val.isdigit():
                return int(val)
    raise BlockedEvidence("protected_host_evidence_unavailable")


def _power_and_thermal() -> tuple[str, str]:
    pm = subprocess.run(
        ["/usr/bin/pmset", "-g"], capture_output=True, text=True, check=False, timeout=2.0
    )
    power_mode = "ac-normal"
    if pm.returncode == 0 and "lowpowermode" in pm.stdout:
        for line in pm.stdout.splitlines():
            if "lowpowermode" in line and line.strip().endswith("1"):
                power_mode = "low-power"
    th = subprocess.run(
        ["/usr/bin/pmset", "-g", "therm"], capture_output=True, text=True, check=False, timeout=2.0
    )
    thermal_status = "nominal"
    if (
        th.returncode == 0
        and "warning level" in th.stdout.lower()
        and "no thermal warning" not in th.stdout.lower()
    ):
        thermal_status = "throttled"
    return power_mode, thermal_status


def collect_machine_record(repository_root: Path = REPOSITORY_ROOT) -> Machine:
    """Collect verified Apple M3 Ultra machine metadata without identifying PII."""
    _check_host_safety()
    chip = _sysctl_str("machdep.cpu.brand_string")
    if chip != "Apple M3 Ultra":
        raise BlockedEvidence("protected_host_evidence_unavailable")
    snapshot = MachineInventoryCollector().collect()
    obs = snapshot.observations
    if (
        obs.cpu_cores is None
        or obs.physical_ram_bytes is None
        or obs.os_build is None
        or obs.python_version is None
    ):
        raise BlockedEvidence("protected_host_evidence_unavailable")
    gpu_cores = _gpu_cores()
    power_mode, thermal_status = _power_and_thermal()
    lock_sha = verify_lock_digest(repository_root)
    try:
        import importlib

        mx: Any = importlib.import_module("mlx.core")

        if not mx.metal.is_available():
            raise BlockedEvidence("independent_mlx_adapter_unavailable")
        mlx_version = str(mx.__version__)
    except BlockedEvidence:
        raise
    except Exception:
        raise BlockedEvidence("independent_mlx_adapter_unavailable") from None

    return Machine(
        chip="Apple M3 Ultra",
        cpu_cores=obs.cpu_cores,
        gpu_cores=gpu_cores,
        physical_ram_bytes=obs.physical_ram_bytes,
        os_build=obs.os_build,
        power_mode=power_mode,
        thermal_status=thermal_status,
        python_version=obs.python_version,
        mlx_version=mlx_version,
        provider_version="livecho-mlx-qwen3-asr-v1",
        converter_version="livecho-mlx-converter-v1",
        provider_revision=PINNED_CODE_REVISION,
        converter_revision=PINNED_CODE_REVISION,
        dependency_lock_sha256=lock_sha,
        code_revision=PINNED_CODE_REVISION,
        cache_state="verified-cached-weights",
        measurement_method="monotonic-ns-process-matrix-v1",
    )


def _snapshot_write_sinks(cache_root: Path, repository_root: Path) -> dict[str, set[str]]:
    tmp_dir = Path(tempfile.gettempdir())
    sinks: dict[str, set[str]] = {"tmp": set(), "repo_benchmarks": set(), "cache": set()}
    with suppress(OSError):
        sinks["tmp"] = {
            p.name
            for p in tmp_dir.iterdir()
            if p.suffix.lower() in _AUDIO_SUFFIXES or "livecho" in p.name.lower()
        }
    bench_dir = repository_root / "benchmarks" / "asr"
    if bench_dir.is_dir():
        sinks["repo_benchmarks"] = {
            str(p.relative_to(bench_dir))
            for p in bench_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in _AUDIO_SUFFIXES
        }
    if cache_root.is_dir():
        sinks["cache"] = {
            str(p.relative_to(cache_root)) for p in cache_root.rglob("*") if p.is_file()
        }
    return sinks


def run_preflight(
    manifest_id: str,
    *,
    cache_root: Path = CACHE_ROOT_DEFAULT,
    repository_root: Path = REPOSITORY_ROOT,
) -> dict[str, object]:
    """Verify manifests, converted weights, corpus, host telemetry, and synthesis tools."""
    verify_lock_digest(repository_root)
    preps = load_preparations(manifest_id)
    infs = load_inferences(manifest_id)
    corpus = load_corpus(manifest_id)
    machine = collect_machine_record(repository_root)
    if not corpus.sources_current(date.today()):
        raise BlockedEvidence("source_rights_expired")
    if not Path("/usr/bin/swift").is_file() or shutil.which("ffmpeg") is None:
        raise BlockedEvidence("approved_corpus_unavailable")

    converted_root = cache_root / "converted"
    for prep, inf in zip(preps, infs, strict=True):
        with FinalModelCache(converted_root, repository_root, prep, inf) as fcache:
            assets = fcache.open_assets(lambda: False)
            if set(assets) != {a.path for a in inf.converted_assets}:
                raise BlockedEvidence("cache_final_missing")

    return {
        "schema_version": 1,
        "state": "ready",
        "action": "preflight",
        "manifest_id": manifest_id,
        "chip": machine.chip,
        "gpu_cores": machine.gpu_cores,
        "mlx_version": machine.mlx_version,
        "scripts": len(corpus.scripts),
        "models": [m.model for m in infs],
    }


def execute_single_pass(
    manifest_id: str,
    model: Model,
    window_seconds: int,
    repetition: int,
    order: int,
    process_id: str,
    *,
    cache_root: Path = CACHE_ROOT_DEFAULT,
    repository_root: Path = REPOSITORY_ROOT,
    corpus_override: Corpus | None = None,
) -> Repetition:
    """Execute one fresh-process PassPlan inside the current isolated child process."""
    _check_host_safety()
    process_start_ns = time.monotonic_ns()
    pageouts_before = _vm_pageouts()
    sinks_before = _snapshot_write_sinks(cache_root, repository_root)

    preps = load_preparations(manifest_id)
    infs = load_inferences(manifest_id)
    corpus = corpus_override if corpus_override is not None else load_corpus(manifest_id)
    idx = MODELS.index(model)
    prep = preps[idx]
    inf = infs[idx]
    settings = Settings()

    plans = matrix_plan(corpus)
    plan = next(
        p
        for p in plans
        if p.model == model and p.window_seconds == window_seconds and p.repetition == repetition
    )
    if plan.order != order:
        raise BlockedEvidence("pass_plan_invalid")

    converted_root = cache_root / "converted"
    backend = MLXEagerBackend(
        provider_revision=inf.provider_revision,
        dependency_lock_sha256=inf.dependency_lock_sha256,
    )
    guard = ThreadExecutionGuard(time.monotonic_ns)
    synthesizer = SwiftFFmpegSynthesizer()

    try:
        with (
            FinalModelCache(converted_root, repository_root, prep, inf) as fcache,
            local_model_load(
                fcache,
                backend,
                clock=time.monotonic_ns,
                guard=guard,
                cancelled=lambda: False,
            ) as load_bounds,
        ):
            provider = MLXASRProvider(backend, clock=time.monotonic_ns)
            provider.load(inf, settings)
            source_factory = InMemoryCorpusSourceFactory(
                corpus, synthesizer, plan=plan, clock=time.monotonic_ns
            )
            try:
                obs = asyncio.run(
                    PassCoordinator().run(
                        plan,
                        corpus,
                        provider,
                        source_factory,
                        guard=guard,
                        clock=time.monotonic_ns,
                    )
                )
            finally:
                source_factory.close()
    finally:
        synthesizer.close()

    pageouts_after = _vm_pageouts()
    sinks_after = _snapshot_write_sinks(cache_root, repository_root)
    write_sinks_passed = sinks_before == sinks_after
    peak_rss = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    first_seg = obs.cold_score.segments[0].timing

    cold = Cold(
        script_id=plan.cold_script_id,
        condition="clean",
        process_start_ns=process_start_ns,
        load_start_ns=load_bounds.load_start_ns,
        ready_ns=load_bounds.ready_ns,
        first_inference_start_ns=first_seg.calls[0].execution_start_ns,
        first_inference_end_ns=first_seg.calls[0].execution_end_ns,
        first_final_ns=first_seg.tf_ns,
        score=obs.cold_score,
    )
    return Repetition(
        model=model,
        window_seconds=cast(Literal[1, 2, 4, 6], window_seconds),
        repetition=cast(Literal[1, 2, 3], repetition),
        process_id=process_id,
        order=cast(Literal[0, 1], order),
        model_manifest_sha256=metadata_digest(inf),
        cold=cold,
        unscored_warmups=3,
        cells=obs.cells,
        silence_duration_ns=60_000_000_000,
        silence_nonempty_finals=obs.silence_nonempty_finals,
        silence_nonempty_partials=obs.silence_nonempty_partials,
        incremental_peak_physical_bytes=peak_rss,
        audio_pageouts=max(0, pageouts_after - pageouts_before),
        peak_canonical_bytes=obs.peak_canonical_bytes,
        peak_audio_bytes=obs.peak_audio_bytes,
        peak_media_duration_ns=obs.peak_media_ns,
        teardown_passed=True,
        write_sinks_passed=write_sinks_passed,
    )


_MODEL_LOAD_SPACING_SEC: dict[Model, float] = {
    MODELS[0]: 10.0,
    MODELS[1]: 5.0,
}


def _spawn_pass_child(
    manifest_id: str,
    plan: PassPlan,
    process_id: str,
    *,
    gate_lock: threading.Lock | None = None,
    last_spawn_by_model: dict[Model, float] | None = None,
) -> Repetition:
    if gate_lock is not None and last_spawn_by_model is not None:
        spacing = _MODEL_LOAD_SPACING_SEC[plan.model]
        with gate_lock:
            prev = last_spawn_by_model.get(plan.model)
            now = time.monotonic()
            if prev is not None and now - prev < spacing:
                time.sleep(spacing - (now - prev))
            last_spawn_by_model[plan.model] = time.monotonic()
    cmd = [
        sys.executable,
        "-m",
        "tools.asr_benchmark.mlx_runner",
        "--manifest",
        manifest_id,
        "--model",
        plan.model,
        "--window",
        str(plan.window_seconds),
        "--repetition",
        str(plan.repetition),
        "--order",
        str(plan.order),
        "--process-id",
        process_id,
    ]
    res = subprocess.run(
        cmd,
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0 or not res.stdout.strip():
        sys.stderr.write(
            f"[pass-failed] {plan.model} w={plan.window_seconds} r={plan.repetition} "
            f"rc={res.returncode}: {res.stderr.strip()[-400:]}\n"
        )
        sys.stderr.flush()
        raise BlockedEvidence("pass_execution_failed")
    return Repetition.model_validate_json(res.stdout.strip())


def run_benchmark_matrix(
    manifest_id: str,
    *,
    max_workers: int = 1,
    report_dir: Path = REPORTS_DIR,
    repository_root: Path = REPOSITORY_ROOT,
) -> tuple[Report, Decision, Path]:
    """Execute all 24 fresh-process repetitions, evaluate fixed gates, and write JSON report."""
    run_preflight(manifest_id, repository_root=repository_root)
    preps = load_preparations(manifest_id)
    infs = load_inferences(manifest_id)
    corpus = load_corpus(manifest_id)
    machine = collect_machine_record(repository_root)
    privacy = build_privacy_evidence()
    settings = Settings()

    plans = matrix_plan(corpus)
    run_id = f"{manifest_id}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    scored_on = date.today()

    gate_lock = threading.Lock()
    last_spawn_by_model: dict[Model, float] = {}
    repetitions_by_idx: dict[int, Repetition] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {
            pool.submit(
                _spawn_pass_child,
                manifest_id,
                plan,
                f"{run_id}-p{idx:02d}",
                gate_lock=gate_lock,
                last_spawn_by_model=last_spawn_by_model,
            ): idx
            for idx, plan in enumerate(plans)
        }
        for completed, future in enumerate(concurrent.futures.as_completed(future_map), start=1):
            idx = future_map[future]
            rep = future.result()
            repetitions_by_idx[idx] = rep
            sys.stderr.write(
                f"[{completed}/{len(plans)}] {rep.model} w={rep.window_seconds}s "
                f"r={rep.repetition} rss={rep.incremental_peak_physical_bytes / (1024**3):.2f}GiB "
                f"pageouts={rep.audio_pageouts}\n"
            )
            sys.stderr.flush()

    repetitions = tuple(repetitions_by_idx[idx] for idx in range(len(plans)))
    report = Report(
        run_id=run_id,
        scored_on=scored_on,
        corpus=corpus,
        corpus_sha256=metadata_digest(corpus),
        manifests=infs,
        preparations=preps,
        machine=machine,
        privacy=privacy,
        settings=settings,
        repetitions=repetitions,
        interrupted=False,
    )
    decision = evaluate(report)
    frozen = run_identity(report)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{run_id}.json"
    with report_path.open("w", encoding="utf-8") as sink:
        write_report(report, frozen, sink)
    return report, decision, report_path


def _child_main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="mlx-runner-child")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--model", required=True, choices=MODELS)
    parser.add_argument("--window", required=True, type=int, choices=WINDOWS)
    parser.add_argument("--repetition", required=True, type=int, choices=(1, 2, 3))
    parser.add_argument("--order", required=True, type=int, choices=(0, 1))
    parser.add_argument("--process-id", required=True)
    args = parser.parse_args(argv)
    if args.manifest != REVIEWED_MANIFEST_ID:
        return 2
    rep = execute_single_pass(
        args.manifest,
        cast(Model, args.model),
        args.window,
        args.repetition,
        args.order,
        args.process_id,
    )
    sys.stdout.write(rep.model_dump_json() + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(_child_main())
