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

## Implementation assignment and exposure (before code)

- Author: `/root/asr_implementation` (OpenAI Codex), 2026-10-02; assigned independently
  to `tools/asr_benchmark/**`, `benchmarks/asr/**`, benchmark tests and Makefile wiring.
  Independent post-implementation reviewer: `/root/audio_code_readiness` (assignment
  corrected before code because the proposed new reviewer could not be allocated).
- Accepted base: `df9f498ba1c5f2496e2ad69fa5b4ff2fd5c599cd`; owner-authorized artifact
  PR #33 is merged. The historical artifact-stage pending labels above are retained.
- Inputs viewed: supplied instructions, repository AGENTS, owning Issue #5, all four
  Issue #5 change artifacts, the independent-implementation policy, relevant accepted
  architecture/lifecycle audio controls, accepted Issue #2 requirements in a partially
  truncated read, Makefile, pyproject, and local path inventory. Unrelated long
  architecture/recovery output was truncated; full unrelated line review is not claimed.
- The local policy disclosed reference repository names, pinned license/path metadata,
  and its historical author's exposure declaration. This is disclosed metadata exposure,
  not a claim of zero context. No reference repository content, Issue #31, external
  research memo, source, tests, schema, fixture, configuration, screenshot, or distinctive
  behavior summary was accessed for this assignment; no prior contribution is known in
  this agent's supplied context. Vendor links in accepted evidence were read as local
  citations only at assignment time; no external page has yet been opened.
- Assignment decision: implement solely from accepted Livecho requirements. No upstream
  copying or MIT-copy exception is requested. Exact model/source/provider/host evidence
  remains unavailable; the local executable entry points must fail closed without it.
  This record is committed before implementation. No model or audio download is authorized.

## Implementation checkpoint (2026-10-03 Asia/Shanghai)

The implementation branch is `codex/issue-5-asr-benchmark-impl`, rebased onto accepted
`origin/main` `93d8b0a`. Pre-code assignment commits are `f2177ee` and `078fb2b`; the
first code checkpoint is `838a914`. Rebase changed their IDs, not their ordering.

Implemented independently from the accepted Issue #5 requirements:

- Closed preparation/inference/corpus/machine/privacy/settings and report contracts,
  canonical metadata digests, mirror parity and preparation-to-inference binding,
  exhaustive tensor inventory/8-bit group-64 conversion planning (metadata only).
- Unicode normalization, deterministic CER alignment/ties, exact target spans,
  bounded overlap stitching and boundary counts, partial/finalization rewrite counts,
  nearest-rank percentiles, disjoint preparation/execution RTF and clock validation.
- Alternating independent-process run plans, 60-script/stratum/condition/window/repeat
  coverage and fixed model decision gates. Cold observations retain their own full
  score/call rows. Missing matrices/evidence block; measured failures never disappear.
- Prefix coalescing/final priority, source stall/PTS controls, reservation-before-
  preparation, aggregate ownership accounting, injected deadline/synchronization
  instrumentation, and cancellation/error teardown. Tests use metadata-only doubles;
  empty borrowed views contain no samples and do not establish host privacy guarantees.
- Separate bounded model-transfer control plane with resumable offsets, immutable
  revision invalidation, progress, attempt/delay/no-progress and integrity controls.
  Transfer tests contain only asset labels/lengths/digests/outcomes, never model bytes.
- Manual local commands and `make asr-benchmark-check`. Execution registry is empty;
  caller-provided IDs/flags cannot enable a provider, network access or model loading.

### Verification commands and results

| Exact command | Actual result | Local date/tree |
| --- | --- | --- |
| `make bootstrap` | Passed: frozen uv/pnpm dependencies, no model/audio download | 2026-10-02 before code |
| `make asr-benchmark-check` | Passed: Ruff/format/mypy, 54 pytest tests | 2026-10-03 `838a914` |
| `make verify` on stale `df9f498` base | Failed: 160 pytest passed, foundation artifact test rejected missing newly accepted Issue #8 files; Ruff/mypy/TypeScript passed. Resolved by rebase, no accepted artifact deleted or rewritten | 2026-10-03 before rebase |
| `make verify` | Passed: 161 pytest, 128 protocol Vitest and 63 Railway Vitest; Ruff/format/mypy/TypeScript/artifacts/protocol/build | 2026-10-03 `838a914` |
| `git diff --check` | Passed | 2026-10-03 `838a914` |
| `make asr-benchmark-check` after review fixes | Passed: 73 pytest tests plus Ruff/format/mypy | 2026-10-03 working tree |
| `make verify` after review fixes | Passed: 180 pytest, 128 protocol Vitest and 63 Railway Vitest; Ruff/format/mypy/TypeScript/artifacts/protocol/build | 2026-10-03 00:21 Asia/Shanghai |
| `git diff --check` after review fixes | Passed | 2026-10-03 00:23 Asia/Shanghai |
| `uv run python -m tools.asr_benchmark prepare-models --manifest pending --source huggingface` | Expected exit 2, `blocked_evidence`; no download or write | 2026-10-03 |
| `uv run python -m tools.asr_benchmark preflight --manifest pending` | Expected exit 2, `blocked_evidence` | 2026-10-03 |
| `uv run python -m tools.asr_benchmark run --manifest pending` | Expected exit 2, `blocked_evidence`; no scoring or write | 2026-10-03 |

`pending` above is deliberately unapproved; no reviewed runtime manifest exists.
The synthetic fully populated report exists only in text/metadata test factories. Its
qualification branches test the rule; they are never model measurements or an allowlist.

### Read-only technical review and corrections

`/root` reviewed only accepted local requirements and this implementation and made no
code changes. It found cross-candidate provider/converter identity gaps, future-dated
approval acceptance, Pydantic numeric/boolean `Literal` coercion despite strict mode,
and provider/release cancellation skipping later cleanup. The implementation author
fixed all four and added regression tests including complete revalidated report input,
nested prerequisite approvals, malformed JSON scalar types and cancelled cleanup hooks.
This review does not replace the named isolated review or any similarity/license review.
Root independently reran its four metadata-only reproductions after the fixes: baseline
1.7B branch still qualifies in test data, a provider mismatch/future approval blocks,
boolean batch size is rejected, and cancelled provider close releases the allocation.
It reported no further confirmed finding in its reviewed scope: contracts, metrics,
timing, report/coverage/decision, runtime, preparation, conversion, instrumentation,
runner, CLI and selected tests. Root remains outside corresponding implementation
authorship; only accepted local requirements and this code supplied these findings.
No new provider implementation is covered by that checkpoint review.

### Incomplete acceptance and remaining code

This checkpoint is **not** completion of Issue #5 and does not select a model. No
hardware score, rights approval, source rendition, model download, network acquisition,
weight conversion or MLX inference was performed. No actual provider architecture or
model compatibility has been inferred from a model card.

Still missing code: independently authored Qwen encoder/decoder/feature extraction and
MLX conversion execution with an exhaustive real tensor map; reviewed pinned dependency
integration; a model-only network/cache backend with verified atomic promotion; bounded
real source acquisition/preprocessing and real-time process orchestration; and a proven
provider deadline guard. The current guard interface requires actual termination before
return/cleanup, but no real guard is installed. Missing hardware evidence alone is not
the reason these implementation items remain incomplete.

Still missing evidence/approvals: immutable source/model/converter/provider/mirror
provenance, per-source permissions and repeatable 60-script corpus, exact allocation
inventory and protected-host no-paging/no-dump/write-sink/failure evidence, complete real
M3 Ultra matrices and the owner-approved model-decision ADR. These are separate from
deterministic test coverage. No production, worker protocol, public API or CUDA change.

No third-party source, tests, fixtures, schema, configuration or assets were copied.
No audio representation (including synthetic samples), audio digest or model weight is
persisted by these tests. Metadata release/write-denial tests do not claim hostile-host
erasure, real provider memory bounds or proof that a real host cannot page audio.
