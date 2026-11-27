# ADR 0002: M3 Ultra MLX ASR Model Evaluation and `neither_qualifies` Decision

Status: Accepted (delegated owner authorization for Issue #5)
Date: 2026-11-27
Decision owners: `@Shuang-su` (delegated via orchestrator M1 run on Apple M3 Ultra host)
Scope: Issue #5 M3 Ultra MLX benchmark (`m3-ultra-qwen3-asr-v1`) evaluating affine 8-bit group-64 MLX realizations of `Qwen/Qwen3-ASR-1.7B` and `Qwen/Qwen3-ASR-0.6B`
Supersedes: None (implements the model-decision ADR gate required by `docs/architecture/adr/0001-alpha-modular-monolith.md` and `docs/changes/5-mlx-benchmark/spec.md`)

## Assurance and approval state

- **Approved artifact set**: `docs/changes/5-mlx-benchmark/intent.md`, `docs/changes/5-mlx-benchmark/spec.md`, `docs/changes/5-mlx-benchmark/plan.md` (unmodified).
- **Reviewed manifest bundle**: `m3-ultra-qwen3-asr-v1` (`benchmarks/asr/manifests/m3-ultra-qwen3-asr-v1.preparations.json`, `benchmarks/asr/manifests/m3-ultra-qwen3-asr-v1.inferences.json`, `benchmarks/asr/manifests/m3-ultra-qwen3-asr-v1.corpus.json`).
- **Complete 24-repetition report**: `benchmarks/asr/reports/m3-ultra-qwen3-asr-v1-20261127T143708Z.json` (`run_id=m3-ultra-qwen3-asr-v1-20261127T143708Z`, `missing=[]`, `repetitions=24`, `Decision.state="neither_qualifies"`).
- **No post-hoc gate relaxation**: Fixed thresholds in `tools/asr_benchmark/report.py` (`evaluate()`) and `tools/asr_benchmark/metrics.py` (`stitch()`, `boundary_counts()`) were preserved untouched.

## Context

Issue #5 requires an independent, clean-room MLX forward pass and affine 8-bit group-64 conversion harness on protected Apple M3 Ultra hardware to compare `Qwen/Qwen3-ASR-1.7B` and `Qwen/Qwen3-ASR-0.6B` across four windows (`1s`, `2s`, `4s`, `6s`), three fresh-process repetitions in alternating model order (`24` total runs), clean and `10 dB SNR` broadband-noise conditions over 60 balanced 12-second scripts (`12` per stratum across `mandarin`, `names`, `numbers`, `code_switching`, `continuous`), plus 60 seconds of silence per repetition.

### Verified Host, Environment, and Model Provenance

- **Host hardware & OS**: `Apple M3 Ultra`, `32` CPU cores, `80` GPU cores, `549,755,813,888` B (`512 GiB`) unified memory, macOS build `26A428`, `ac-normal`, `thermal_status=nominal`, `sysctl vm.swapusage` = `total = 0.00M used = 0.00M free = 0.00M (encrypted)`, `RLIMIT_CORE=(0, 0)`.
- **Toolchain & lock**: Python `3.12.13`, `mlx==0.31.1` (`Device(gpu, 0)`, Metal available), `numpy==2.4.4`, `safetensors==0.7.0`, `tokenizers==0.22.2` (Darwin-arm64 marker-gated in `pyproject.toml`), `uv.lock` SHA-256 `a2f58cd48bef9bdffc7a7ac1fc8de70724ae31e7389e16dbd293036c606d95c2`, pinned code revision `95885aa33523fba9a9bd9857a30b1d0a2352151e`.
- **Clean-room MLX adapter (`tools/asr_benchmark/mlx_adapter.py`)**: Implemented independently using only `mlx.core`, `mlx.nn`, `numpy`, `safetensors`, and `tokenizers` (no `mlx-audio`, `torch`, `transformers`, `LocalAI-WeKnora`, or LAPLACE code). Uses 128-bin Whisper log-Mel in RAM, 1-chunk Conv2d audio tower, 24/18-layer attention encoder with 104-token block mask, 28-layer Qwen3 GQA decoder (`q_norm`/`k_norm`, `RoPE` base `1,000,000`), and 8-bit group-64 quantized KV cache (`_MAX_KV_POSITIONS = 220`), bounding audio-bearing allocations strictly `<= 15,279,616 B` (`<= 16,777,216 B` cap).
- **Upstream & converted model assets (stored outside Git at `~/.cache/livecho/asr_models`)**:
  - `Qwen/Qwen3-ASR-1.7B`: Apache-2.0, Hugging Face revision `7278e1e70fe206f11671096ffdd38061171dd6e5` / ModelScope mirror parity revision `a04930dbe5419bfee073f7cade734f572689a3a8` (11 source assets, `708` tensor rules); preparation SHA-256 `d8e2ca03963285178084054fd41c461d3bc7696442285e65fec2418f7e1e66da`; converted `model.safetensors` `2,500,527,858 B`, SHA-256 `26cd49585ec0e24cc3dffcd60d6bc484ab0e8cf4a59baf5aac253dcfa4a939bd`.
  - `Qwen/Qwen3-ASR-0.6B`: Apache-2.0, Hugging Face revision `5eb144179a02acc5e5ba31e748d22b0cf3e303b0` / ModelScope mirror parity revision `4ce9cc728b473a5aedbe7b6e1ea45646316824dc` (9 source assets, `612` tensor rules); preparation SHA-256 `5edef17a0b2c8694cec217782bd4b43cc32d68910a189c26172e342bfeda8544`; converted `model.safetensors` `1,000,936,771 B`, SHA-256 `cf02ddc8cb529b8e4df1f2ae2f9a78872927751e2224c9bb8edb91335c06caa9`.
- **In-memory corpus (`m3-ultra-qwen3-asr-v1.corpus.json`, SHA-256 `062044b0e3c91961d6ac2d9fe16b733757204e93a347644c4a63d28b07bd474e`)**: 60 scripts balanced across `speaker-linfei`, `speaker-tingting`, and `speaker-meijia` synthesized in RAM via Swift `AVSpeechSynthesizer.write(_:toBufferCallback:)` -> FFmpeg `pipe:0 -> pipe:1` (`pcm_s16le`, `16,000 Hz`, mono), zero audio files written to disk (`write_sinks_passed=True` across all 24 processes).

## Measured Results

### 1. Complete 24-Repetition Matrix (`benchmarks/asr/reports/m3-ultra-qwen3-asr-v1-20261127T143708Z.json`)

The full 24-repetition run executed with `max_workers=24` (all 24 child processes overlapping on the single M3 Ultra Metal GPU). Every privacy, silence, memory-footprint, and coverage invariant passed across all 24 fresh processes (`missing=[]`):

- **Privacy & footprint**: `audio_pageouts=0` on all 24 runs; `teardown_passed=True` and `write_sinks_passed=True` on all 24 runs; `silence_nonempty_finals=0` and `silence_nonempty_partials=0` on all 24 runs (`60s` silence per run); `incremental_peak_physical_bytes` `7.14–7.16 GiB` (`1.7B`) and `2.95–2.97 GiB` (`0.6B`), strictly `< 8.0 GiB`; `peak_audio_bytes <= 15,279,616 B` (`<= 16,777,216 B`); `peak_canonical_bytes <= 601,600 B` (`<= 960,000 B`); `peak_media_duration_ns = 12.0s` (`<= 30s`).
- **Cold-load timing**: `1.7B` load `p50=7.09–7.54s` / `p95=7.59–7.95s` (`<= 30s`); `0.6B` load `p50=3.01–3.19s` / `p95=3.17–3.54s` (`<= 30s`).
- **Accuracy & stability at `6s` window (3-repetition aggregate, 180 clean + 180 noise scripts per model)**:

| Model | Cond | Micro CER (Gate) | Names Exact | Numbers Exact | English Exact | Rewrite Freq (<=0.25) | Rewrite Sev (<=0.10) | Boundary Dup (<=0.01) | Boundary Omi (<=0.02) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `1.7B` | `clean` | **1.13%** (<=10%) | 33/36 (**91.7%**) | 36/36 (**100.0%**) | 36/36 (**100.0%**) | 169/1336 (**12.6%**) | 570/12299 (**4.6%**) | 6/156 (**3.85% FAIL**) | 0/156 (**0.0%**) |
| `1.7B` | `noise` | **1.37%** (<=20%) | 33/36 (**91.7%**) | 36/36 (**100.0%**) | 33/36 (**91.7%**) | 333/1992 (**16.7%**) | 1730/21244 (**8.1%**) | 6/156 (**3.85% FAIL**) | 0/156 (**0.0%**) |
| `0.6B` | `clean` | **1.69%** (<=10%) | 36/36 (**100.0%**) | 33/36 (**91.7%**) | 36/36 (**100.0%**) | 335/2162 (**15.5%**) | 1257/21868 (**5.7%**) | 12/156 (**7.69% FAIL**) | 0/156 (**0.0%**) |
| `0.6B` | `noise` | **2.53%** (<=20%) | 36/36 (**100.0%**) | 30/36 (**83.3%**) | 33/36 (**91.7%**) | 497/2287 (**21.7%**) | 2078/23397 (**8.9%**) | 6/156 (**3.85% FAIL**) | 0/156 (**0.0%**) |

Per-stratum `1.7B` `6s` CER: `clean` `mandarin=1.25%`, `names=1.43%`, `numbers=1.43%`, `code_switching=0.85%`, `continuous=0.69%` (all `<= 15%`); `noise` `mandarin=1.07%`, `names=1.61%`, `numbers=0.90%`, `code_switching=2.55%`, `continuous=0.69%` (all `<= 25%`).

- **Contended 24-worker matrix latencies (`max_workers=24`, p50 / p95)**:
  - `1.7B` (`w=1..6`): `rtf p95 = 1.454–2.212` (`> 0.70`), `first_partial_ns p95 = 1,777–4,493 ms`, `provider_first_text_ns p95 = 836–1,444 ms`, `provider_final_ns p95 = 925–2,154 ms`, `speech_end_to_final_ns p95 = 1,579–3,620 ms`, plus `missing_partial` (`failed_sample`) on `1s`/`2s` where Metal queue wait pushed provisionals past segment close.
  - `0.6B` (`w=1..6`): `rtf p95 = 1.344–1.487` (`> 0.70`), `first_partial_ns p95 = 1,505–3,158 ms`, `provider_first_text_ns p95 = 587–846 ms`, `provider_final_ns p95 = 633–1,461 ms`.

### 2. Isolated Single-Process Verification (`1` worker, Zero GPU Contention)

Because running 24 MLX processes concurrently on one Metal GPU caused ~8x–10x command-queue serialization (`task-793`), single-process isolated baselines (`task-823` and `task-811`) were measured on the identical compiled adapter and models:

- **Uncontended latency & RTF (`task-823`, single process on M3 Ultra)**:
  - `1.7B w=1`: `rtf p95 = 0.386` (`<= 0.70`), `provider_first_text_ns p95 = 114.4 ms` (`<= 750 ms`), `first_partial_ns p95 = 574.0 ms` (`<= 1,500 ms`), `provider_final_ns p95 = 109.1 ms` (`<= 700 ms`), `speech_end_to_final_ns p95 = 117.3 ms` (`<= 2,600 ms`).
  - `1.7B w=6`: `rtf p95 = 0.656` (`<= 0.70`), `provider_first_text_ns p95 = 88.5 ms` (`<= 750 ms`), `first_partial_ns p95 = 1,394.0 ms` (`<= 1,500 ms`), `provider_final_ns p95 = 212.5 ms` (`<= 2,000 ms`), `speech_end_to_final_ns p95 = 213.4 ms` (`<= 2,600 ms`).
  - `0.6B w=1`: `rtf p95 = 0.247` (`<= 0.70`), `provider_first_text_ns p95 = 305.8 ms` (`<= 750 ms`), `first_partial_ns p95 = 557.6 ms` (`<= 1,500 ms`), `provider_final_ns p95 = 69.2 ms` (`<= 700 ms`), `speech_end_to_final_ns p95 = 71.9 ms` (`<= 2,600 ms`).
  - `0.6B w=6`: `rtf p95 = 0.540` (`<= 0.70`), `provider_first_text_ns p95 = 78.3 ms` (`<= 750 ms`), `first_partial_ns p95 = 1,489.3 ms` (`<= 1,500 ms`), `provider_final_ns p95 = 161.4 ms` (`<= 2,000 ms`), `speech_end_to_final_ns p95 = 162.2 ms` (`<= 2,600 ms`).
  - Furthermore, an isolated `s-00-00-mandarin` and `s-04-00-continuous` `1s` check (`task-834`, `task-850`) passed all `12/12` segments (`tp_ns != None`, `fails=[]`).
- **Isolated `boundary_duplicate` root-cause check (`task-811`, single process across all 12 `continuous` scripts)**:
  - `1.7B w=4 clean`: `boundary_duplicate = 8/98` (`8.16% > 1.0%`), `omissions = 0/98` (`s-04-01`: `...高效语音` + `笑语音识别...` = `2`; `s-04-10`: `...地域的` + `与地狱的...` and `...最柔软的` + `被柔软的...` = `6`).
  - `1.7B w=6 clean`: `boundary_duplicate = 2/52` (`3.85% > 1.0%`), `omissions = 0/52` (`s-04-07`: `...声音年轻` + `因年轻的学子们...` = `2`).
  - Root cause: When a stateless `transcribe()` call starts on an arbitrary `800 ms` PCM slice boundary that splits an active Chinese syllable mid-phoneme (e.g., `-īn` in `声音`, `g-` in `高效`, `z-` in `最`), Qwen3-ASR emits a 1-character acoustic artifact (`因`, `笑`, `被`) before the overlapping words. Because `tools/asr_benchmark/metrics.py:stitch()` requires an exact suffix-prefix character match (`merged[-size:] == normalized[:size]`), a single substituted boundary prefix character prevents overlap stripping and causes the remaining overlapping characters (`2–3` chars per seam) to be counted as boundary duplicates.

## Decision

1. **Selected benchmark decision**: **`neither_qualifies`** (evaluated identically by `tools/asr_benchmark/report.py:evaluate()` on the complete 24-repetition report `benchmarks/asr/reports/m3-ultra-qwen3-asr-v1-20261127T143708Z.json` with zero gate relaxation).
   - Even when eliminating multi-process GPU contention (`task-823`, where both `1.7B` and `0.6B` pass every uncontended RTF and latency gate, and `1.7B` achieves `1.13%` clean / `1.37%` noise micro CER and `91.7–100%` target exactness at `6s`), **both models fail the fixed `<= 1.0%` `boundary_duplicate` gate at `4s` and `6s` under stateless overlap decoding + exact suffix-prefix stitching** (`1.7B`: `3.85%` at `6s`, `8.16%` at `4s`; `0.6B`: `7.69%` at `6s`, `15.31%` at `4s`).
2. **Production model deployment remains blocked**: Neither `Qwen/Qwen3-ASR-1.7B` nor `Qwen/Qwen3-ASR-0.6B` is promoted to production worker defaults under Issue #5. Follow-on runtime work (Issue #8 / #9 streaming alignment or punctuation/overlap-aware stitching) must address cross-segment overlap boundary handling before re-evaluating model promotion, and `mlx_runner.py` defaults `max_workers=1` so future benchmark runs execute strictly sequentially without cross-process Metal GPU contention.
3. **Host runner default**: `tools/asr_benchmark/mlx_runner.py:run_benchmark_matrix` sets `max_workers: int = 1` as the default so future operator runs measure true uncontended single-process latencies without Metal queue contention.

## Consequences

- **Positive**:
  - Issue #5's entire protected-host acquisition, affine 8-bit group-64 MLX conversion, clean-room MLX Qwen3-ASR inference adapter, RAM-only 60-script Swift+FFmpeg corpus, privacy/no-paging/no-write-sink enforcement, and 24-repetition evaluation harness are verified end-to-end on real Apple M3 Ultra hardware.
  - `Qwen/Qwen3-ASR-1.7B` demonstrates strong raw accuracy (`1.13%` clean / `1.37%` noise CER at `6s`, `91.7–100%` target exactness) and passes uncontended M3 Ultra latency/RTF thresholds (`rtf=0.386` at `1s`, `0.656` at `6s`, `final=109–213 ms`, `7.16 GiB <= 8 GiB` peak RSS).
- **Negative / Follow-up required**:
  - Production ASR worker enablement (`workers/mlx`) cannot yet claim a qualified model; a follow-up runtime/stitching issue must either resolve mid-syllable overlap boundary artifacts (e.g., edit-tolerant overlap stitching or stateful streaming decoder alignment) or obtain explicit owner approval for revised boundary handling.
  - Sequential `max_workers=1` execution of all 24 × 25.25-minute passes takes ~10.1 hours; future multi-pass optimization (such as KV-cache preallocation / `mx.compile` on the Qwen3 decoder loop) can reduce per-call GPU utilization from `65.6%` if multi-worker scheduling is ever reconsidered.
