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

## Bounded follow-up implementation and primary-source audit

Draft implementation PR: [#36](https://github.com/Shuang-su/Livecho/pull/36), first
pushed review checkpoint `8646e25`; attached to the Codex task. It does not close #5.
On 2026-10-03 the same implementation author additionally read the official pages below,
including inline usage examples, and official Hugging Face API/configuration metadata.
No example was copied/executed; no vendor model source, community adapter, reference
repository, Issue #31, model weights, tokenizer contents or audio was fetched.

| Primary input | Captured fact and limit |
| --- | --- |
| [Qwen technical report v1, section 2.1](https://arxiv.org/html/2601.21337v1) | AuT/projector/Qwen architecture, 128-channel features and eightfold encoder downsampling. These architectural facts do not define the full operator graph or prove a local MLX implementation. |
| [Official 1.7B model card](https://huggingface.co/Qwen/Qwen3-ASR-1.7B), [0.6B card](https://huggingface.co/Qwen/Qwen3-ASR-0.6B) | Described package backends remain transformers/vLLM. Inline API examples were exposed but not executed, copied or used to enable their automatic downloads. |
| [1.7B config at `7278e1e70fe206f11671096ffdd38061171dd6e5`](https://huggingface.co/Qwen/Qwen3-ASR-1.7B/blob/7278e1e70fe206f11671096ffdd38061171dd6e5/config.json) | Candidate shape facts: encoder width/layers/heads 1024/24/16, decoder width/layers/KV-heads/head-width 2048/28/8/128. This is candidate metadata, not an approved asset manifest. |
| [0.6B config at `5eb144179a02acc5e5ba31e748d22b0cf3e303b0`](https://huggingface.co/Qwen/Qwen3-ASR-0.6B/blob/5eb144179a02acc5e5ba31e748d22b0cf3e303b0/config.json) | Encoder width/layers/heads 896/18/14, decoder width/layers/KV-heads/head-width 1024/28/8/128. Candidate metadata only. |
| [Pinned 1.7B preprocessing metadata](https://huggingface.co/Qwen/Qwen3-ASR-1.7B/blob/7278e1e70fe206f11671096ffdd38061171dd6e5/preprocessor_config.json), [pinned 0.6B metadata](https://huggingface.co/Qwen/Qwen3-ASR-0.6B/blob/5eb144179a02acc5e5ba31e748d22b0cf3e303b0/preprocessor_config.json) | 128 features, FFT 400, hop 160; identifies a Whisper feature extractor but does not pin its full mathematical/padding/normalization implementation. No waveform was requested. |
| [MLX quantize](https://ml-explore.github.io/mlx/build/html/python/_autosummary/mlx.core.quantize.html), [synchronize](https://ml-explore.github.io/mlx/build/html/python/_autosummary/mlx.core.synchronize.html), displayed version 0.32.3 | Affine quantization supports group 64 and 8 bits; returns packed values, scales and biases; last dimension must divide the group size. Synchronization is stream/device scoped. These APIs support the injected conversion-call contract, not an installed or pinned MLX dependency. |

The web reader could not retrieve the Hugging Face model API endpoints. A bounded
standard-library HTTPS metadata read retrieved each model's `sha`, then only the pinned
`config.json` and `preprocessor_config.json` into RAM and printed selected scalar facts.
No downloaded asset file or network/auth diagnostics was saved. Only independently
written shape facts and links enter this change.

Additional code now implements the exact existing four-field protocol projection,
frozen-identity report parsing/serialization/text-sink writing, affine conversion-call
dispatch with evaluation/synchronization, persistent text-only transfer checkpoints and
verification-before-atomic-promotion coordination against a metadata cache double.
The new JSON roundtrip test exposed strict-model pre-validation losing native JSON
array/date semantics; explicit array/ISO-date handling fixes that without permitting
boolean/integer/float literal coercion.

The candidate shape planner calculates 58,720,256 bytes for a conventional full-layer
K+V cache with 512 positions and two-byte elements (`2 * 28 * 8 * 128 * 512 * 2`). That
specific audio-conditioned layout alone exceeds the 16,777,216-byte process audio cap.
This rejects that layout, **not** every possible MLX implementation. A different bounded
recomputation/cache strategy may be independently implemented and proved; the budget
is not relaxed. This is a shape calculation, not measured memory usage.

### Remaining work after this bounded batch

- Independently writable code still includes concrete model-only HTTPS/cache I/O,
  same-inode verification/promotion, a real-time acquisition/process runner and a
  cancellation guard. Existing interfaces/tests constrain them but do not implement
  these backends. They require deliberate filesystem/transport/termination failure
  tests; no hardware benchmark is needed merely to write that code.
- Exact AuT convolution/padding/chunk masks, projector, Qwen decoder/position encoding,
  token framing, feature normalization and weight-name/layout conversion remain missing.
  The consulted paper/configs are insufficient to invent those details. The next code
  step is to establish each exact operator/shape contract from permitted primary
  documentation, then independently implement and test model operations without weights.
  No statement is made that this work is impossible or blocked solely by hardware.
- Runtime asset loading additionally needs reviewed dependency pins, complete tensor/
  asset manifests, conversion licenses/notices and approvals. Real equivalence/quality
  and memory/timing tests need approved weights and the qualified source corpus.
- Real audio execution additionally needs a complete allocation inventory, actual
  bounded deadline termination and protected-host no-paging/no-dump evidence. It remains
  disabled; an empty directory or a model's size does not satisfy these gates.

Independent reviewer `/root/audio_code_readiness` inspected accepted local requirements
and the implementation only, without editing code or fetching external sources. Its
bounded scope included contracts/report, runtime/instrumentation/runner/timing,
conversion/preparation/serialization/adapter planning/CLI and selected tests. It found
two instrumentation defects: supplied input duration could differ from the reported
prefix denominator, and a failing initial clock read could strand a reservation. The
author bound prefix+overlap to the reserved/prepared duration before provider use and
moved that initial clock read before reservation; metadata-only regressions cover both.
Exact final review and updated verification outcomes follow after the stable checkpoint.

At exact code head `48ee3632ce897add26e3b59dfa709d57cf02a8e2`, the isolated reviewer
confirmed both fixes and reported no remaining actionable finding in the bounded scope.
Its independent command `uv run pytest -q tests/asr_benchmark/test_instrumentation.py
tests/asr_benchmark/test_artifacts.py tests/asr_benchmark/test_controls.py` passed 42
tests in 2.51 seconds. It did not rerun the full repository suite or independently
validate external model metadata, hardware, MLX, upstream similarity or legal clearance.

Author verification on that code head, 2026-10-03 Asia/Shanghai:

- `make asr-benchmark-check`: passed Ruff/format/mypy and **83 tests**.
- `make verify`: passed Ruff/format/mypy/TypeScript, **190 pytest**, **128 protocol
  Vitest**, **63 Railway Vitest**, artifacts/protocol checks and build (00:42).
- `git diff --check`: passed. No accepted Issue #5 intent/spec/plan or protocol file changed.

The earlier new report-roundtrip test failed while native JSON arrays/dates were
mistakenly rejected; it passed after the documented strict conversion repair. No scoring
or operational runtime result is inferred from these deterministic test results.

## Model-only cache backend follow-up, 2026-10-03

The same assigned implementation author implemented `model_cache.py` and original
notice-text temporary-directory tests. The only additional external exposure was the
official [Python 3.12 os documentation](https://docs.python.org/3.12/library/os.html)
for directory-relative open/replace and no-follow flags and
[fcntl documentation](https://docs.python.org/3.12/library/fcntl.html) for nonblocking
advisory locks. No implementation source or examples were copied. This continues the
same Issue/PR and independent review assignment; accepted intent/spec/plan are unchanged.

The backend opens a private cache outside Git, detects `.git` files as well as
directories, walks ancestors without following symlinks and keeps a directory descriptor
for all subsequent I/O. Names derive only from the preparation/revision/asset identity.
One nonblocking lock protects each asset transaction. Partial/checkpoint files must be
private regular files with one link. Actual length governs resume offsets; checkpoint
identity and offsets must agree. Model-asset hashing reads at most the manifest length
plus one byte and cannot follow unbounded concurrent growth. Final promotion requires
the held inode, matching file-name inode, unchanged size/mtime/ctime and manifest SHA;
it fsyncs before/after rename and preserves any pre-existing final asset.

Failure tests cover overwrite/truncate/append after verification, inode swaps, symlinks,
hardlinks, FIFO rejection, root/ancestor substitution, a second controller, wrong length/
digest/offset/checkpoint, cancellation, failed writes/replace/fsync and cleanup continuation.
Normal close preserves an interrupted model partial; exceptional context exit discards
it and releases descriptors/lock. The backend does not log exception payloads or paths.
Reviewer preliminary inspection identified FIFO-open blocking and an unbounded hash-to-EOF
loop; both were corrected before the stable snapshot and have bounded regressions.

These tests write only a short independently written notice and checkpoint JSON, never
audio, audio hashes, samples, weights, downloaded vendor text or generated model assets.
No model execution or registry authority is added. Cooperating clients in a private
operator cache are the lock boundary; hostile same-user processes or failed storage
cannot be claimed safe merely from these tests. A failed filesystem cleanup returns a
closed error after attempting all cleanup stages; it is not a secure-erasure guarantee.

Remaining implementation is now more specific: fixed allowlisted HTTPS transport and
response/range handling, integration with the bounded retry controller, and a verified
final-cache reader/cold loader can still be independently written with text doubles.
They need transport/read/failure contracts and tests, not benchmark hardware. They are
outside this bounded cache-write batch and remain unregistered. The exact model operator
and feature/token framing contracts, MLX graph/converter, acquisition/process runner and
real cancellation guard listed above remain code gaps. Candidate architecture metadata
does not supply those complete contracts. Approved assets/provenance, source corpus,
protected-host inventory and complete M3 Ultra scoring/ADR remain separate evidence gates.
This cache backend does not turn the always-blocked CLI into an operational benchmark.

Stable snapshot verification and independent review are recorded below when completed.

Stable cache code commit: `7c8ad30edafe3de013d444debbbf35412890cb1f`.
Author verification on 2026-10-03 Asia/Shanghai:

- Initial `uv run ruff check tools/asr_benchmark/model_cache.py
  tests/asr_benchmark/test_model_cache.py` found two test-context SIM117 style findings;
  they were corrected with no behavior change. Ruff format/check and focused mypy then
  passed; initial `uv run pytest -q tests/asr_benchmark/test_model_cache.py` passed 41.
- After additional path/promotion/checkpoint regressions, `make asr-benchmark-check`
  passed Ruff/format/mypy and **129 tests in 37.87s**. The subsequent two-line addition
  of nonblocking open flags for partial/lock files was included in the full check below.
- Exact code head `7c8ad30`: `make verify` passed at 01:00, with Ruff/format/mypy,
  TypeScript checks, **236 pytest in 40.87s**, **128 protocol Vitest**, **63 Railway
  Vitest**, artifact/protocol checks and build. This includes all 46 new cache cases.
- `git diff --check` passed; accepted Issue #5 intent/spec/plan and protocol unchanged.

Independent reviewer `/root/audio_code_readiness` reviewed exact `7c8ad30`, including
all new cache implementation/tests and the preparation docstring/README/evidence.
It independently ran `uv run pytest -q tests/asr_benchmark/test_model_cache.py`:
**46 passed in 0.23s**. Separate ordinary-notice reproductions confirmed a FIFO fails
as `checkpoint_invalid` within 0.25 seconds; a same-inode overwrite with restored mtime
still fails promotion through the ctime check with no final file; and a descriptor-close
callback that closes then raises cancellation still attempts/closes all three descriptors
and releases the lock. It reported no remaining actionable finding in this bounded scope.
No old suite was repeated by the reviewer. It read only accepted local requirements and
this implementation/evidence; no new external fetch, network/model/audio/provider run,
hardware proof, upstream-expression comparison or legal clearance is claimed. Quota
gates returned exit 0 before and after this batch and the independent review.
