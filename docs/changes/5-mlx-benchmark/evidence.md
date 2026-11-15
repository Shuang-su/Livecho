# Evidence: M3 Ultra MLX benchmark requirements

## Artifact approval

- Artifact PR: [#33](https://github.com/Shuang-su/Livecho/pull/33); draft,
  documentation only, does not close Issue #5.
- Approved by/date: Pending @Shuang-su review and merge.
- Base: `67fc6ed`; reviewed owning Issue #5 on 2026-10-02.

## Requirements-author exposure and provenance

- Author: `/root/asr_audio_specs` (OpenAI Codex), independent requirements author,
  `docs/changes/5-mlx-benchmark/**`, 2026-10-02.
- Livecho inputs: supplied AGENTS instructions, repository AGENTS, change templates,
  roadmap, owning Issues #5/#8, accepted Issue #1–#4 intent/spec/plan/evidence material
  relevant to artifact gating, audio/protocol and deployment boundaries, Issue #2 ADR,
  threat/lifecycle/policy records, Makefile and artifact-validator branch convention.
  Long unrelated accepted-file output was truncated; no claim of full line-by-line
  review of unrelated infrastructure or recovery algorithms is made.
- The accepted independent-implementation policy exposes repository names, immutable
  license metadata, and its historical author's summarized-exposure declaration. No
  linked LAPLACE repository, source, tests, schemas, fixtures, configuration, docs,
  assets, screenshot, or distinctive behavior summary was opened for this assignment.
  Issue #31 and external research reports were not read. No upstream prior contribution
  is known in this context. Do not treat this as an implementation exposure clearance.
- Primary vendor pages below were viewed, including their inline API examples, solely
  for publicly documented capabilities. A broad MLX search also returned incidental
  third-party search snippets (DeepWiki, mirrors, Reddit); none was opened or used as
  a requirement. This exposure is disclosed rather than described as zero exposure.
- Assignment: requirements only. Implementation unassigned. `/root/artifact_review`
  performs independent read-only requirements review; owner decision is pending.

## Primary fact/source register

Access date: 2026-10-02. Pages are mutable; exact dependency/asset revisions are a
later pre-run manifest gate, not invented in this document.

| Source | Fact used and limit |
| --- | --- |
| [Qwen 0.6B model card](https://huggingface.co/Qwen/Qwen3-ASR-0.6B) and [Qwen 1.7B model card](https://huggingface.co/Qwen/Qwen3-ASR-1.7B) | Official model identities, Apache-2.0 label, Hugging Face/ModelScope acquisition entries and ndarray input. The described package backends are transformers/vLLM; no local MLX performance or compatibility is inferred. License label is not completed asset approval. |
| [MLX quantize](https://ml-explore.github.io/mlx/build/html/python/_autosummary/mlx.core.quantize.html), displayed 0.32.3 | Affine quantization supports 8 bits and group size 64. This API capability does not prove Qwen tensor compatibility. |
| [MLX compilation](https://ml-explore.github.io/mlx/build/html/usage/compile.html), displayed 0.32.3 | Evaluation/warmup matters when timing lazy/compiled work. Livecho owns its own run design and thresholds. |
| [Hugging Face download guide](https://huggingface.co/docs/huggingface_hub/guides/download) | Revision-bound file/snapshot retrieval and model cache behavior; Livecho restricts it to manifest-listed model assets. |

The attempted MLX `usage/benchmarking.html` URL was unavailable and supports no claim.
No model asset, audio, corpus, source repository, or CUDA artifact was downloaded.
FFmpeg's official pipe documentation was also opened for the separate Issue #8 draft;
it is not a source of model-selection requirements.

## Automated verification

| Exact command | Result | Date/tree |
| --- | --- | --- |
| `make bootstrap` | Passed; frozen uv and pnpm installs; no model/audio download | 2026-10-02 artifact worktree |
| `git diff --check` | Passed; no whitespace errors | 2026-10-02 artifact worktree |
| `make artifacts` | Passed; `change artifacts: ok` | 2026-10-02 artifact worktree |
| `make verify` | Passed; Ruff, mypy, TypeScript, 107 pytest tests, 128 protocol and 63 Railway Vitest tests, artifact/protocol checks and build | 2026-10-02 artifact worktree |
| `git diff --cached --check && make artifacts && git diff --cached --stat` | Passed after design fixes; exactly four Issue #5 Markdown additions | 2026-10-02 / `7016dca` |

[GitHub Verify](https://github.com/Shuang-su/Livecho/actions/runs/37024511675)
passed for initial artifact head `7016dca`; evidence-only follow-up has separate CI.

## Manual or hardware evidence

Not run. No model is selected; no local MLX compatibility, latency, CER, memory,
no-persistence, source permission, host no-paging, or mirror-parity result is claimed.
The exact manifests, corpus, protected hardware run and decision ADR remain mandatory.
Artifact thresholds are proposed local decisions for owner review, not measurements.

## Review findings

- Independent reviewer `/root/artifact_review` found three P2 ambiguities. Resolved by
  separating approved acquisition/conversion preparation from final converted-asset
  inference approval, defining first-provisional/final call clocks and metric
  populations, and explicitly applying boundary quality gates to both 4/6-second
  overlap runs. Re-review confirmed the fixes; these are specification fixes, not
  runtime test claims.
- Cross-draft review found that #8's completed segments cannot supply this local
  benchmark's early partials. The specification now labels prefix access benchmark-only,
  prohibits an inferred end-to-end claim and requires an owning runtime artifact before
  adding incremental delivery. No unpublished draft is made normative for the other.
- Final independent read-only review by `/root/artifact_review`, 2026-10-02, examined
  all eight Issue #5/#8 artifact files, owning Issues and accepted local constraints.
  It reported no remaining actionable artifact-design findings after the fixes.
  Reviewer made no edits or runtime/hardware tests and opened no external/reference
  source, Issue #31 body, or research output. Owner approval remains pending.
- The owning Issue explicitly separates licensed human speech from synthetic protocol
  input. The artifact keeps human benchmark audio entirely outside `LeaseV1`.
- Accepted ADR has no model-specific decision. The plan requires an owner-approved
  measured ADR instead of claiming the requested fallback is already authorized.
- Full machine footprint and audio-buffer limits are separate; neither enlarges the
  other. An unaccountable provider/host blocks real audio rather than weakening the cap.

## Deviations

Branch uses `codex/issue-5-mlx-benchmark-spec` to satisfy the existing artifact checker.
No product implementation, accepted-artifact rewrite, or policy relaxation.

## Release and rollback evidence

Not deployed. All production switches remain unchanged and disabled. This documentation
does not authorize a model download, hardware run, real worker audio, or public output.

## Guarded implementation port verification — 2026-11-15

Implementer: Cursor Auto (cloud agent). Base: current `main` at
`d73f2e27f8c431cdf2f00df8dc9ca70af4426e95` (includes merged Issue #9 fixture slice).
Branch: `issue/5-asr-benchmark-impl`.

### Prior work reviewed (not approved evidence)

Parked closed draft PR [#36](https://github.com/Shuang-su/Livecho/pull/36) on
`codex/issue-5-asr-benchmark-impl` (head `a78837e`, reviewed implementation
`491c0bb`) was inspected as prior art only. This PR does **not** merge that
46-commit history. Reviewed trees under `tools/asr_benchmark/`,
`tests/asr_benchmark/`, and `benchmarks/asr/README.md` were ported onto current
main as a new branch, then integrity checks were tightened for coarse-timestamp
Linux filesystems (content re-hash on promote/finish/validate) so same-size
mutation tests remain honest. Accepted `intent.md` / `spec.md` / `plan.md` were
not rewritten. Old publication-reconciliation evidence from #36 is not reused as
runtime acceptance.

### Commands and results

```sh
make asr-benchmark-check
```

Exit 0. Ruff/mypy ok; `608 passed` under `tests/asr_benchmark`.

```sh
make verify
```

Exit 0. Notable: mypy ok (90 source files); `uv run pytest -q -m "not stress"` →
`771 passed, 1 deselected`; protocol/web/railway tests and build ok;
`change artifacts: ok`; `protocol generated artifacts: ok`.

```sh
git diff --check
```

Exit 0.

```sh
uv run python -m tools.asr_benchmark prepare-models --manifest demo-manifest --source huggingface
uv run python -m tools.asr_benchmark preflight --manifest demo-manifest
uv run python -m tools.asr_benchmark run --manifest demo-manifest
```

Each exits **2** with JSON
`state=blocked_evidence` and reasons
`reviewed_manifest_unavailable`, `independent_mlx_adapter_unavailable`,
`approved_corpus_unavailable`, `protected_host_evidence_unavailable`.
No model download, audio, or scoring runs.

### What this PR implements (Linux/CI-safe)

- Closed manifest/report/metric/decision contracts and synthetic text tests
- PassPlan coordinator, supervisor, preparation/cache/transfer doubles
- Hugging Face HTTPS/Range preparation shaping (tests inject streams; no live fetch in CI)
- Model-only cache / converted store / verified readers with content integrity
- Blocked CLI registry (`prepare-models` / `preflight` / `run`)
- `make asr-benchmark-check`

### Remaining acceptance gates (not claimed; not waived)

- Owner-approved immutable preparation + final inference manifests (exact asset
  digests, conversion map, licenses) and a non-empty execution registry
- **Independent MLX Qwen adapter** (quantize/load/transcribe) with dependency pin
  evidence — cannot be measured on this Linux CI host
- **ModelScope** official HTTP contract still missing → no ModelScope adapter/fallback
- Qualified 60-script consenting-speaker corpus with in-RAM-only audio acquisition
- Trusted **M3 Ultra** protected-host evidence: no-paging/no-dump, cold/warm full
  matrices for 1/2/4/6 s windows, ≥3 repetitions, RTF/memory/latency percentiles,
  CER/boundary/partial gates
- Owner-approved **model-decision ADR** (`qualified_1_7b` / `qualified_0_6b` /
  `neither_qualifies` / `blocked_evidence`)
- No production, Bilibili, account, worker, or Issue #9 `synthetic_mlx` enablement

Hardware/manual gates require an authorized Apple Silicon operator on a reviewed
commit; this agent does not access user machines or paid services for that evidence.
Missing hardware evidence keeps the Issue open and selection blocked.

## 2026-11-15 — Critical review hardening (PR #46, same branch)

Implementer: Cursor Auto (cloud agent). Review of the #36-ported tree against
accepted #5 artifacts and current `main`. “Reviewed” on the closed draft is
**not** treated as owner approval or hardware evidence.

### Findings fixed on this PR

1. **Important / safety default** — `download_asset` / `prepare_sources` /
   `conversion_session` used `HTTPSResponse` as the default `response_factory`,
   so omitting the kwarg could open TLS sockets. Defaults now call
   `transport_not_injected()` → `BlockedEvidence("transport_not_injected")`.
   Explicit `HTTPSResponse` remains operator opt-in only.
2. **Important / scoring contract** — `score_script` left `ScriptScore.failure`
   unset even when segments failed (`provider_timeout` / mapped
   `provider_failure`). Propagated so report-level cold failure is not relying
   solely on nested segment inspection for this path.
3. **Regression coverage** — fail-closed transport (no `open_connection`),
   same-size+mtime-restored partial refuse promotion, script failure mapping /
   evaluate cold failure.

### Commands and results

```sh
make asr-benchmark-check
```

Exit 0. `614 passed` under `tests/asr_benchmark`.

```sh
make verify
```

Exit 0. `uv run pytest -q -m "not stress"` → `777 passed, 1 deselected`.

CLI prepare/preflight/run still exit **2** / `blocked_evidence`. No live
download, audio, MLX, or hardware claims. Issue #5 remains open; real execution
gates remain closed.

### Residual (not blocking CI-safe merge of this control-plane slice)

- `evaluate()` trusts persisted report edit counts (text is discarded by design);
  tampered-on-disk reports are an operator-host concern, not CI import risk.
- Live `HTTPSResponse` still exists for trusted opt-in; never exercised by
  defaults or CI.
- Apple Silicon / MLX / ModelScope / corpus / ADR gates unchanged and unmet.
