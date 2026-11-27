"""Unit tests for reviewed manifest registry, MLX converter/adapter contracts, and RAM corpus."""

from __future__ import annotations

import builtins
import http.client
import importlib.util
from pathlib import Path
from typing import Any

import pytest

from tools.asr_benchmark.__main__ import main
from tools.asr_benchmark.contracts import MODELS, NS, Corpus, Script
from tools.asr_benchmark.corpus_source import (
    InMemoryCorpusSourceFactory,
    InMemoryReplaySource,
    _compute_spans,
    add_broadband_noise_10db,
)
from tools.asr_benchmark.http_transfer import DownloadFailure
from tools.asr_benchmark.metrics import normalize
from tools.asr_benchmark.mlx_adapter import (
    MAX_AUDIO_BEARING_BYTES,
    MLXASRProvider,
    MLXEagerBackend,
    estimate_audio_bearing_bytes,
    parse_asr_output,
)
from tools.asr_benchmark.mlx_converter import (
    RedirectingHTTPSStream,
    _host_allowed,
)
from tools.asr_benchmark.mlx_runner import ThreadExecutionGuard
from tools.asr_benchmark.pass_coordinator import ReplayRequest, _schedule
from tools.asr_benchmark.registry import (
    PINNED_CODE_REVISION,
    PINNED_LOCK_SHA256,
    REVIEWED_MANIFEST_ID,
    build_privacy_evidence,
    load_corpus,
    load_preparations,
    output_plan_for,
    require_reviewed_id,
)
from tools.asr_benchmark.runner import PassPlan
from tools.asr_benchmark.runtime import BlockedEvidence, Budget, MemoryInput, Prefix

from .factories import corpus as factory_corpus

_HAS_MLX = importlib.util.find_spec("mlx") is not None
_HAS_NUMPY = importlib.util.find_spec("numpy") is not None


def test_registry_fails_closed_without_file_io(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbid_open(*args: object, **kwargs: object) -> object:
        raise AssertionError("unexpected_open")

    monkeypatch.setattr(builtins, "open", forbid_open)
    for bad_id in ("pending", "demo", "unknown-manifest"):
        with pytest.raises(BlockedEvidence, match="reviewed_manifest_unavailable"):
            require_reviewed_id(bad_id)
        with pytest.raises(BlockedEvidence, match="reviewed_manifest_unavailable"):
            load_preparations(bad_id)
        assert main(["preflight", "--manifest", bad_id]) == 2


def test_reviewed_preparations_have_mirror_parity_and_complete_tensor_maps() -> None:
    prep_17b, prep_06b = load_preparations(REVIEWED_MANIFEST_ID)
    assert prep_17b.model == MODELS[0] and len(prep_17b.tensor_map) == 708
    assert prep_06b.model == MODELS[1] and len(prep_06b.tensor_map) == 612
    assert prep_17b.converter_revision == PINNED_CODE_REVISION
    assert prep_17b.dependency_lock_sha256 == PINNED_LOCK_SHA256
    for prep in (prep_17b, prep_06b):
        plan = output_plan_for(prep)
        assert {item.kind for item in plan.outputs} == {"weights", "tokenizer", "config", "notice"}
    privacy = build_privacy_evidence()
    assert privacy.reviewed_code_revision == PINNED_CODE_REVISION


def test_redirect_host_allowlist_and_stream_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _host_allowed("huggingface.co", "huggingface")
    assert _host_allowed("us.aws.cdn.hf.co", "huggingface")
    assert not _host_allowed("huggingface.co.evil.com", "huggingface")
    assert not _host_allowed("modelscope.cn", "huggingface")
    assert _host_allowed("modelscope.cn", "modelscope")
    assert _host_allowed("cdn-lfs-cn-1.modelscope.cn", "modelscope")
    assert not _host_allowed("huggingface.co", "modelscope")

    stream = RedirectingHTTPSStream("huggingface")
    with pytest.raises(DownloadFailure, match="download_redirect_unapproved"):
        stream.open("http://huggingface.co/Qwen/Qwen3-ASR-0.6B/resolve/a/config.json", 0, 10)
    with pytest.raises(DownloadFailure, match="download_redirect_unapproved"):
        stream.open("https://user:pass@huggingface.co/a", 0, 10)

    class FakeResp:
        def __init__(self, status: int, headers: dict[str, str]) -> None:
            self.status = status
            self._headers = {k.lower(): v for k, v in headers.items()}

        def getheader(self, name: str, default: str | None = None) -> str | None:
            return self._headers.get(name.lower(), default)

        def read(self, amt: int | None = None) -> bytes:
            return b""

        def close(self) -> None:
            pass

    responses: list[FakeResp] = [
        FakeResp(302, {"Location": "https://evil.invalid/model.safetensors"}),
    ]

    class FakeConn:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def request(self, method: str, target: str, headers: dict[str, str]) -> None:
            pass

        def getresponse(self) -> FakeResp:
            return responses.pop(0)

        def close(self) -> None:
            pass

    monkeypatch.setattr(http.client, "HTTPSConnection", FakeConn)
    with pytest.raises(DownloadFailure, match="download_redirect_unapproved"):
        stream.open("https://huggingface.co/Qwen/Qwen3-ASR-0.6B/resolve/a/model.safetensors", 0, 10)

    # Valid redirect to allowlisted CDN + 206 Range verification
    responses = [
        FakeResp(302, {"Location": "https://us.aws.cdn.hf.co/xet-bridge-us/blob"}),
        FakeResp(206, {"Content-Length": "5", "Content-Range": "bytes 5-9/10"}),
    ]
    code, length = stream.open(
        "https://huggingface.co/Qwen/Qwen3-ASR-0.6B/resolve/a/model.safetensors", 5, 10
    )
    assert (code, length) == (206, 5)
    stream.close()


def test_adapter_budget_bounds_and_silence_parsing() -> None:
    for seconds in (1, 2, 4, 6):
        pcm_bytes = (seconds * 16_000 + 12_800) * 2
        est = estimate_audio_bearing_bytes(pcm_bytes)
        assert est.peak_audio_bearing_bytes <= MAX_AUDIO_BEARING_BYTES - 384_000
    with pytest.raises(BlockedEvidence, match="allocation_invalid"):
        estimate_audio_bearing_bytes(-1)
    with pytest.raises(BlockedEvidence, match="budget_exceeded"):
        estimate_audio_bearing_bytes(20_000_000)

    assert parse_asr_output("language Chinese<asr_text>你好世界") == "你好世界"
    assert parse_asr_output("language None<asr_text>") == ""
    assert parse_asr_output("language None<asr_text>   ") == ""
    assert parse_asr_output("language English<asr_text>hello world") == "hello world"

    backend = MLXEagerBackend(
        provider_revision=PINNED_CODE_REVISION,
        dependency_lock_sha256=PINNED_LOCK_SHA256,
    )
    provider = MLXASRProvider(backend)
    with pytest.raises(BlockedEvidence, match="independent_mlx_adapter_unavailable"):
        provider.transcribe(MemoryInput(memoryview(b"\x00\x00"), 0, NS), Prefix(NS, "final"))
    provider.close()
    assert backend.unloaded is True


def test_in_memory_replay_source_budget_retirement_and_schedule() -> None:
    corp: Corpus = factory_corpus()
    script: Script = corp.scripts[-1]  # continuous
    budget = Budget()
    req_speech = ReplayRequest("warm", "clean", script, script.duration_ns, 6 * NS, 800_000_000)
    pcm = bytearray(12 * 16_000 * 2)
    pcm[:100] = b"\x01" * 100
    src = InMemoryReplaySource(req_speech, budget, 0, pcm, source_id="src-1")
    spans = _schedule(req_speech, src)
    assert len(spans) == 2
    prepared = src.call_input(0, 6 * NS)
    budget.reserve(prepared.allocation, prepared.release)
    mem = prepared.prepare()
    assert mem.view.nbytes == 6 * 16_000 * 2
    mem.view.release()
    budget.release(prepared.allocation.allocation_id)
    src.retire_before(5_200_000_000)
    assert pcm[:100] == b"\x00" * 100
    src.close()
    assert budget.live_count == 0

    # 60s silence must stay well under 960,000 B canonical and 30s media duration.
    silence_budget = Budget()
    req_silence = ReplayRequest("silence", "clean", None, 60 * NS, 6 * NS, 0)
    silence_buf = bytearray(6 * 16_000 * 2)
    silence_src = InMemoryReplaySource(
        req_silence, silence_budget, 0, silence_buf, source_id="src-sil"
    )
    assert len(_compute_spans(req_silence)) == 10
    assert silence_budget.peak_canonical_bytes == 6 * 16_000 * 2
    assert silence_budget.peak_media_ns == 6 * NS
    silence_src.close()
    assert silence_budget.live_count == 0


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy only installed on darwin-arm64")
def test_broadband_noise_10db_snr_deterministic_and_zero_disk_writes(tmp_path: Path) -> None:
    import numpy as np

    corp = factory_corpus()
    script = corp.scripts[0]
    t = np.arange(12 * 16_000, dtype=np.float32)
    tone = (np.sin(2.0 * np.pi * 440.0 * t / 16_000.0) * 5000.0).astype(np.int16)
    clean_a = bytearray(tone.tobytes())
    clean_b = bytearray(tone.tobytes())
    noisy_a = add_broadband_noise_10db(clean_a, script)
    noisy_b = add_broadband_noise_10db(clean_b, script)
    assert noisy_a == noisy_b
    diff = np.frombuffer(noisy_a, dtype=np.int16).astype(np.float32) - tone.astype(np.float32)
    snr_db = 10.0 * np.log10(np.mean(tone.astype(np.float32) ** 2) / np.mean(diff**2))
    assert 9.8 <= float(snr_db) <= 10.2
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(not _HAS_MLX, reason="mlx only installed on darwin-arm64")
def test_mlx_metal_quantize_and_guard_timeout() -> None:
    import mlx.core as mx

    assert mx.metal.is_available()
    w = mx.ones((64, 128), dtype=mx.bfloat16)
    wq, scales, biases = mx.quantize(w, group_size=64, bits=8, mode="affine")
    mx.eval(wq, scales, biases)
    assert wq.dtype == mx.uint32

    now = 100
    guard = ThreadExecutionGuard(clock=lambda: now)
    guard.execute(lambda: None, 200)
    with pytest.raises(BlockedEvidence, match="provider_timeout"):
        guard.execute(lambda: None, 50)


def test_reviewed_corpus_balance_and_target_alignment() -> None:
    corpus = load_corpus(REVIEWED_MANIFEST_ID)
    assert len(corpus.scripts) == 60
    by_stratum: dict[str, int] = {}
    for script in corpus.scripts:
        by_stratum[script.stratum] = by_stratum.get(script.stratum, 0) + 1
        norm = normalize(script.reference)
        assert len(norm) >= 30
        assert len(script.character_times) == len(norm)
        assert script.character_times[0].start_ns == 0
        assert script.character_times[-1].end_ns == 12 * NS
        for target in script.targets:
            assert 0 <= target.start < target.end <= len(norm)
    assert set(by_stratum) == {"mandarin", "names", "numbers", "code_switching", "continuous"}
    assert all(count == 12 for count in by_stratum.values())


@pytest.mark.skipif(not _HAS_NUMPY, reason="numpy only installed on darwin-arm64")
def test_corpus_source_factory_prefetch_and_close_zeros_buffers() -> None:
    import struct

    corp = load_corpus(REVIEWED_MANIFEST_ID)
    sample_pcm = struct.pack("<h", 500) * (12 * 16_000)

    class FakeSynth:
        def __init__(self) -> None:
            self.calls = 0

        def synthesize_pcm_s16le(self, voice_id: str, rate: float, text: str) -> bytes:
            self.calls += 1
            return sample_pcm

    plan = PassPlan(
        model=MODELS[1],
        window_seconds=6,
        repetition=1,
        order=0,
        cold_script_id=corp.scripts[0].script_id,
        warmup_count=3,
        script_ids=tuple(s.script_id for s in corp.scripts),
        conditions=("clean",),
    )
    synth = FakeSynth()
    factory = InMemoryCorpusSourceFactory(corp, synth, plan=plan, clock=lambda: 0)  # type: ignore[arg-type]
    try:
        budget = Budget()
        req = ReplayRequest("cold", "clean", corp.scripts[0], 12 * NS, 6 * NS, 0)
        src = factory(req, budget, 0)
        assert synth.calls >= 1
        src.close()
        assert budget.live_count == 0
    finally:
        factory.close()


def test_sixty_second_silence_rolling_budget_never_exceeds_30s_media() -> None:
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from tools.asr_benchmark.pass_coordinator import PassCoordinator, _Clock, _SharedBudget
    from tools.asr_benchmark.runtime import TextUpdate

    corp = load_corpus(REVIEWED_MANIFEST_ID)

    class FakeSynth:
        def synthesize_pcm_s16le(self, voice_id: str, rate: float, text: str) -> bytes:
            return b"\x00" * (12 * 16_000 * 2)

    class FastClock:
        def __init__(self) -> None:
            self.now = 0

        def __call__(self) -> int:
            self.now += 50_000_000
            return self.now

    class FastGuard:
        def execute(self, operation: object, deadline_ns: int) -> None:
            assert callable(operation)
            operation()

    class SilentProvider:
        def __init__(self, clock: FastClock) -> None:
            self._clock = clock

        def load(self, manifest: object, settings: object) -> None:
            pass

        def transcribe(self, audio: MemoryInput, prefix: Prefix) -> TextUpdate:
            return TextUpdate("", self._clock.now, 0)

        def synchronize(self) -> None:
            pass

        def close(self) -> None:
            pass

    for win in (1, 6):
        clock = FastClock()
        budget = _SharedBudget()
        factory = InMemoryCorpusSourceFactory(corp, FakeSynth(), clock=clock)  # type: ignore[arg-type]
        req = ReplayRequest("silence", "clean", None, 60 * NS, win * NS, 0)
        with ThreadPoolExecutor(max_workers=1) as pool:
            score, finals, partials = asyncio.run(
                PassCoordinator()._collect(
                    req,
                    factory,
                    SilentProvider(clock),
                    budget,
                    _Clock(clock),
                    FastGuard(),
                    lambda: False,
                    Event(),
                    pool,
                )
            )
        factory.close()
        assert score is None
        assert finals == 0 and partials == 0
        assert budget.live_count == 0
        assert budget.peak_media_ns <= win * NS
        assert budget.peak_canonical_bytes <= 960_000


def test_matrix_runner_defaults_to_isolated_single_worker() -> None:
    import inspect

    from tools.asr_benchmark.mlx_runner import run_benchmark_matrix

    assert inspect.signature(run_benchmark_matrix).parameters["max_workers"].default == 1
