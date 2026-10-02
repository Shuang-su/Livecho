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

## Verified reader and local load boundary assignment, 2026-10-03

The same independent author `/root/asr_implementation` continues with the bounded
final-cache reader and local eager-load boundary. `/root/audio_code_readiness` remains
the independent reviewer. Before this batch's code, the author rechecked AGENTS, owning
Issue #5, accepted intent/spec/plan and the existing evidence/code context. No additional
external sources, model implementation, weights or audio were accessed. Earlier policy
and primary-document exposures above remain applicable; this is not a no-exposure claim.
Scope is final-manifest-bound read-only handles and injected backend cleanup, not HTTPS,
converted-asset writing, actual MLX loading, fresh-process proof or scored cold results.

### Reader/load implementation boundary

`FinalModelCache` binds the separate final inference manifest using the existing
preparation/source/tensor-map/dependency contract, and selects only its converted
asset digest/length entries. It uses the preparation digest/canonical source revision/
converted digest namespace. Source cache bytes are eligible only if exactly identical
to that independently approved converted entry; missing converted assets never fall
back to source files. This neither manufactures final approval nor registers a model.
The converted-asset writer remains unimplemented; tests place original ordinary notice
text at fixed content keys to exercise read semantics, not conversion or tensor loading.

All final files are verified before the backend sees a handle. Duplicate-content path
labels share one nonblocking lock and read-only descriptor, avoiding self-contention.
Their borrowed lifetime is shared; the backend must not close individual aliases. Reads
are offset/count bounded with exact integer types, use a position-independent descriptor
read, and validate inode, file-name identity, private regular-file status, length and
mtime/ctime before and after access. No public raw descriptor/path is exposed. Reader
errors invalidate subsequent use. The cache root must already exist; this read entry
point does not create an empty model cache and call it verified.

`local_model_load` requires matching provider/dependency pins and unloaded backend
state, passes only the verified final asset mapping with local-only/no-remote-code
parameters, and synchronizes before readiness. Its required injected guard contains
verification, initialization, synchronization, reader cleanup and the ready timestamp.
Every failure/cancellation/close path attempts all reader and backend cleanup. Retained
borrowed readers are closed before readiness is yielded; backend lifetime ends on
context exit. The result is only `LocalLoadBoundaries`; it never constructs a `Cold`,
process-freshness assertion, scored report or hardware measurement. Backend properties,
flags and the guard are contracts awaiting independently verified real implementations,
not proof that arbitrary Python callbacks cannot use the network or retain model state.

Remaining independently writable work: fixed allowlisted HTTPS/range/response handling
and bounded-transfer integration, model-only converted-output writer with actual digests,
and process/acquisition/deadline orchestration with failure tests. Real eager model loading
still needs the exact independently authored MLX operator/weight/feature/token contracts
and backend. Final model/source/rights approval, no-paging/no-dump host evidence, fresh
process repetitions, real corpus scoring and the decision ADR remain separate acceptance
gates. No further code scope is taken in this reader/load batch.

Verification and exact independent review for this batch follow below.

Pre-code assignment commit: `7b9effb`. Exact reader/load code:
`4df7696a06faa970a6caa9aa330d6c4ff7a3fca7`. Author verification on 2026-10-03
Asia/Shanghai:

- `uv run ruff check tools/asr_benchmark/cache_reader.py tools/asr_benchmark/cold_load.py
  tests/asr_benchmark/test_cache_reader.py` and matching Ruff format/mypy checks passed.
  `uv run pytest -q tests/asr_benchmark/test_cache_reader.py` passed **49 in 0.28s**.
- Exact code head `4df7696`: `make asr-benchmark-check` passed all Ruff/format/mypy checks
  and **178 tests in 38.23s**. `make verify` passed at 01:21 with **285 pytest in
  41.15s**, **128 protocol Vitest**, **63 Railway Vitest**, all lint/type checks,
  artifacts/protocol checks and build.
- `git diff --check` passed; no accepted intent/spec/plan or protocol file changed.

Independent reviewer `/root/audio_code_readiness` reviewed exact `4df7696`, both new
modules and all new tests, the minimal `_root_fd(create=False)` change, and README/
evidence. Its independent `uv run pytest -q tests/asr_benchmark/test_cache_reader.py`
passed **49 tests in 0.27s**. Additional ordinary-notice temporary-directory reproductions
confirmed: corruption in the last physical asset prevents every backend initialize call
and releases all earlier locks; equal-content aliases can alternate tail/prefix reads
without cursor drift; and cancellation at the ready-clock after loading closes retained
readers and backend, with replacement locks available. It reported no remaining
actionable finding in this bounded scope. It did not repeat old suites or fetch external
sources, load models/audio, execute a real provider, or claim process/hardware/privacy
evidence. The author/reviewer quota gates returned exit 0 before/after this batch.

## HTTPS follow-up exposure checkpoint, 2026-10-03

Author `/root/asr_implementation` began a bounded request/response/transfer integration
assignment after verified code `4df7696` and evidence head `12aa322`. **No product code
or tests for this HTTPS batch were written before the following exposure, and none have
been written after it.** The existing reader/cache implementations predate this lookup.

Intended primary documentation opened: [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)
(including Range, Content-Range and Content-Length section links), Hugging Face
[model downloads](https://huggingface.co/docs/hub/models-downloading) and
[file download API](https://huggingface.co/docs/huggingface_hub/package_reference/file_download),
[Python 3.12 http.client](https://docs.python.org/3.12/library/http.client.html), and
[ModelScope model download documentation](https://www.modelscope.cn/docs/models/download).
The ModelScope page returned no readable body. No model/asset endpoint was requested.

A subsequent search was mistakenly not restricted using the tool's domain filter. Its
result snippets exposed implementation and example expression outside the intended
primary-documentation scope. The author did not click these results, open repositories,
copy/execute their examples, fetch weights/audio or use them to write code. Exposure was
nevertheless real and is not treated as zero. Results included the following sources;
only provenance locations are recorded here, not their implementation expression:

| Search-result source | Material exposed in the search output |
| --- | --- |
| [ModelScope SDK file_download.py](https://github.com/modelscope/modelscope/blob/master/modelscope/hub/file_download.py) | Download-function source/docstring fragment; moving branch, no immutable revision established. |
| [Third-party ModelScope fork](https://github.com/AiTH-Solutions/platform-llm-modelscope/blob/master/modelscope/hub/file_download.py) | Download/cache source fragment; moving branch, no immutable revision established. |
| [modelpull platform document](https://github.com/l17728/modelpull/blob/main/docs/v2.0/06-platform-and-ecosystem.md) | Third-party source-driver design and endpoint summary; moving branch, no immutable revision established. |
| [ModelScope speaker-verification model page](https://www.modelscope.cn/models/damo/speech_campplus_sv_zh-cn_16k-common) | Example API code and audio URL strings, not media contents. |
| [ModelScope language-recognition model page](https://www.modelscope.cn/models/iic/speech_eres2net_base_lre_en-cn_16k/) | Example API and setup commands, not repository or media contents. |
| [ModelScope separation model page](https://modelscope.cn/models/iic/speech_flatflocoformer_separation_timefrequency_8k_middle_libri2mix360) | Example API/persistence code and explanatory text, not media contents. |
| [ModelScope community ComfyUI page](https://community.modelscope.cn/6641a99e8dd48c198fa263a2.html) | Download command examples. |
| [ModelScope community MistoLine page](https://community.modelscope.cn/6644261a931dbe49ec6c8f64.html) | Download/setup and helper-script examples. |
| [ModelScope community llamafile page](https://community.modelscope.cn/65bc887128cf1d21b5200a30.html) | Download/execution examples. |
| [ModelScope issue 592](https://github.com/modelscope/modelscope/issues/592) | Third-party issue code and error text. This is not Livecho Issue #31, which was not accessed. |
| [ModelScope community SD-WebUI page](https://community.modelscope.cn/6641afca5b9cb1600612c5e1.html) | Download/setup examples. |
| [ModelScope paraformer model page](https://modelscope.cn/models/zhgqpower/speech_paraformer_large_asr_mtl-16k-common-vocab11666-onnx) | Example API code and source URLs, not repository or media contents. |

The author stopped this module's implementation immediately and reported the event to
the coordinator without relaying the implementation snippets to the isolated reviewer.
The coordinator assigned this author no further implementation of the corresponding
HTTPS/download/transfer modules and will arrange an unexposed replacement author with
the isolated reviewer unchanged. No exception is requested. No endpoint compatibility,
legal clearance, new implementation
or new test result is claimed from this lookup. The existing executable registry remains
empty and Issue #5 remains incomplete. This exposure-only checkpoint changes no accepted
intent/spec/plan, code, tests, protocol, model authority or runtime setting.

## Replacement HTTPS/transfer assignment (before code), 2026-10-03

- Author: `/root/audio_implementation` (OpenAI Codex GUI subagent), independently
  assigned to fixed allowlisted HTTPS request/response/Range handling and integration
  with `PreparationTransfer`/`ModelOnlyCache`. Planned paths are
  `tools/asr_benchmark/http_transfer.py`, `tools/asr_benchmark/model_download.py`,
  focused `tests/asr_benchmark/` tests, directly required preparation/cache interfaces,
  README and this evidence. Isolated reviewer: `/root/audio_code_readiness`.
- The coordinator released the write handoff after verifying metadata-only exposure
  checkpoint `e64f90d4b4a57d29a1e0981ab6075dee000c7869`. The prior author is excluded
  from this corresponding module. No exception to the source-isolation policy is used.
- Actual earlier exposure: this replacement author implemented accepted Issue #8 and
  read official FFmpeg command/protocol documentation (including pipe/file/cache and
  protocol-list descriptions), Python 3.12 OS/subprocess documentation, and the Linux
  parent-death-signal manual. No HTTP/model-download SDK source, third-party downloader
  expression, source-derived summary, screenshot, or earlier implementation advice was
  supplied or viewed. No prior contribution to the reference projects is known.
- Local policy metadata exposure includes reference names/revisions/paths/license
  classifications and its historical author's exposure statement. Issue #8 evidence
  described another author's Qwen/MLX/Hugging Face primary-document reads; this author
  did not open their contents. Owning Issue #8/#5 comments incidentally mention Issue
  #31 and Cap/Soniox experience boundaries; Issue #31's body and linked materials were
  not read. This is a disclosure of context, not a zero-exposure claim.
- Inputs for this assignment: AGENTS, owning Issue #5 body/comments, all four accepted
  Issue #5 artifacts, unchanged independent-implementation policy, local preparation,
  cache, manifest/CLI/runtime contracts, README and related original tests. The exposure
  event above was read only as recorded provenance locations/material categories; no
  external event link, snippet, implementation summary or recommendation was opened.
- Decision: write independently from accepted Livecho requirements and directly opened
  official API/HTTP standards only. Missing endpoint/redirect authority stays blocked;
  no inferred ModelScope endpoint or mirror fallback is permitted. The execution
  registry remains empty. No real model, audio, converter, MLX provider or benchmark
  execution is authorized by this assignment. Tests use original ordinary text and
  transport/control doubles only. This record is committed before new module code.

## Independent HTTPS and preparation integration, 2026-10-03 (Asia/Shanghai)

Author `/root/audio_implementation` wrote this batch after assignment commit
`f85f21e98249777a9f1ee78f2f33ced9dc31b97a`. Reviewer remains
`/root/audio_code_readiness`; the coordinator additionally reads transport cancellation
and deadline ownership. The prior exposed author supplied no module code or advice.
No accepted intent/spec/plan or public protocol is changed.

Actual new external reads were direct primary documentation only:

- [HTTP semantics, RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html), Range and
  Content-Range sections: status, inclusive range offsets and representation length.
- [Hugging Face model downloads](https://huggingface.co/docs/hub/models-downloading)
  and [file-download API documentation](https://huggingface.co/docs/huggingface_hub/package_reference/file_download),
  including `hf_hub_url`'s documented resolve-path example and immutable revision
  parameter. The pages also displayed API usage examples and cache/CDN descriptions;
  no linked SDK source, repository implementation or third-party example was opened.
- [Python 3.12 asyncio streams](https://docs.python.org/3.12/library/asyncio-stream.html),
  including TLS connection parameters, bounded reads, stream limits and shutdown APIs.
  Inline official TCP/HTTP/socket examples were visible. No example was copied.
- The reviewer supplied RFC 9110's Retry-After interpretation and section location,
  with no third-party implementation expression. The local client conservatively stops
  when a temporary error includes this header rather than ignoring a server cooldown.

No search was performed by the replacement author. No link from the exposure incident,
Issue #31 body, reference repository, external implementation memo or source snippet was
read. These primary descriptions and accepted local requirements inform original code;
this disclosure does not claim absence of all context or legal clearance.

Implemented scope:

- `http_transfer.py`: manifest-selected immutable repository/revision/asset requests,
  escaped path segments, fixed HTTPS authority, certificate/hostname verification,
  bounded headers/reads, exact initial/suffix status/length/range/identity validation.
  No credential/proxy/environment URL support, redirects or mirror fallback. A server
  response never supplies new request authority. Unsupported ModelScope endpoint
  authority is explicitly `download_endpoint_unverified` before opening a cache entry.
- `model_download.py`: one asset per explicit call, response revocation before retry,
  shared remaining 60-second network no-progress deadline and late-result rejection,
  maximum three attempts with 1/2-second waits, terminal authentication/permission/
  integrity/cooldown failures, bounded body appends and actual SHA verification before
  existing same-inode atomic promotion. Started attempts are persisted before requests.
- Actual offsets must agree with an explicit checkpoint to resume. Missing/stale
  nonempty partial metadata cannot reset the attempt budget. Complete interrupted
  partials, even after attempt three, are locally verified without a fourth request or
  a Range starting at EOF. Cancellation retains only an already committed matching
  checkpoint; half-finished writes/checkpoint failures invalidate the partial.
- Synchronous response abort and entry cleanup cannot be abandoned by a second task
  cancellation. Start/read operations that suppress cancellation cannot commit late
  results; a connection that returns late is aborted before request emission. Cache
  fsync/hash operations are synchronous bounded-chunk work: the async deadline bounds
  network waits and rejects late network results, not preemptive disk/hash latency.

Verification before isolated review (local 2026-10-03, UTC+08:00):

- `make asr-benchmark-check` — passed: ruff lint/format, strict mypy (29 files),
  **250 passed in 36.32s**. The 72 added cases cover original HTTP metadata and original
  notice text with transport/stream doubles, resume/retry/cancel/deadline/cache faults.
- `git diff --check` — passed. GUI gates before/after tool batches returned active.
- No socket, model request, model/audio download, model/MLX execution, converted writer
  or hardware benchmark was performed. The executable registry remains empty. The
  transport's real endpoint/TLS/CDN compatibility is unmeasured; redirects and ModelScope
  are blocked. Immutable approved model records, actual conversion/MLX implementation,
  consenting corpus, protected-host evidence and measured hardware gates remain open.

Final verification/review at code head
`9e39a7191dab96bf50cd5a7397cdd9f16b0f6e08`, 2026-10-03 around 01:57–02:02
Asia/Shanghai (UTC+08:00):

- `make verify` — exit 0: ruff lint/format (51 files), strict mypy (51 files), workspace
  lint/typechecks, **357 pytest passed in 37.83s**, **128 protocol Vitest tests**,
  **63 Railway Vitest tests**, change-artifact checks, protocol-generation check and
  all builds passed. Existing accepted protocol tests ran unchanged; this is not a
  new authorization for real audio/model execution. No dependency or lock changed;
  the earlier recorded `make bootstrap` remains the workspace setup for this batch.
- Isolated `/root/audio_code_readiness` read the new HTTP/coordinator modules, both
  new test files, necessary preparation/cache diffs and README/evidence at the exact
  clean code head above. Independent command
  `uv run pytest -q tests/asr_benchmark/test_http_transfer.py tests/asr_benchmark/test_model_download.py`
  — **72 passed in 0.23s**. Independent `git diff --check` — exit 0.
- The reviewer separately used an in-memory stdin Python probe against original notice
  doubles: a 503 response with Retry-After 120 made only one attempt, read no body,
  slept zero times and invalidated/released the entry; a resumed 10-byte partial receiving
  200 instead of 206 waited its one-second restore delay, made one request at offset 10,
  read no body and invalidated/released the entry. Both passed without a socket. These
  supplement the checked-in regressions, not real endpoint acceptance.
- The reviewer confirmed the earlier Retry-After finding is resolved and reported no
  remaining actionable finding in this bounded review. Its only new external read was
  [RFC 9110 section 10.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3);
  no SDK/third-party downloader expression or prior exposure snippets were received.
  The reviewer did not rerun the full suite. `/root` separately reviewed local transport
  cancellation/deadline control flow at the same head, without edits or repeated tests;
  this is a read-only supplemental review, not independent TLS/DNS/host evidence.

This batch is internal implementation progress, not Issue #5 acceptance. PR #36 remains
a draft; no model is selected and no merge, deployment or real benchmark is performed.

## Source-asset collection assignment (before code), 2026-10-03 (UTC+08:00)

- Author: `/root/audio_implementation`, OpenAI Codex GUI subagent. New bounded assignment:
  verified preparation source-asset collection and acquisition orchestration, planned
  `source_cache.py` / `preparation_run.py`, focused tests, necessary shared model-cache/
  reader interfaces, README and evidence. Isolated reviewer: `/root/audio_code_readiness`.
  `/root` supplements lifecycle/permission review read-only. Existing PR #36 remains
  the one Issue #5 implementation PR; no other author is writing this batch.
- Earlier actual context/exposure is fully retained in the replacement assignment and
  HTTPS integration records above, including official API examples and local policy
  metadata. Those disclosures apply to this assignment; no zero-context claim is made.
  The previous author's exclusion from corresponding HTTP/download modules continues.
  No incident link, snippet, implementation advice or excluded material was received.
- New reads: refreshed owning Issue #5 body/comments, AGENTS, accepted intent/spec/plan,
  evidence and unchanged policy; existing local conversion, instrumentation, cold-load,
  final reader, cache, transfer, runner and related original tests. All four artifacts
  were previously read in full and reviewed again for this batch; no new external
  source lookup, third-party repository, Issue #31 body or SDK source was opened.
- Implement independently from these accepted local requirements and existing Livecho
  interfaces. The collection must verify actual source files and expose all borrowed
  readers only after the complete set verifies. Only genuinely missing assets may be
  acquired through the existing restricted downloader. Corruption, identity mismatch
  or unsafe files must not become a missing-file fallback. Keep preparation authority
  separate from inference and return no approved inference manifest.
- Tests remain original ordinary text and transport/control doubles only. No real
  network/model/audio, MLX, converted-output writer or process runner work is included.
  Registry remains empty, ModelScope/redirect acquisition remains blocked, and no
  accepted intent/spec/plan or public protocol change is authorized. This assignment
  record is committed before implementation.

## Verified preparation source collection, 2026-10-03 (UTC+08:00)

Author `/root/audio_implementation` implemented this batch after assignment
`e7be8357b92861ed648ebfa10ee13adbae8bd345`; no additional external source was read.
The original source/exposure record above remains applicable. This batch adds:

- `VerifiedSourceAssets`, bound to a revalidated preparation manifest, the exact cache
  manifest digest, and explicitly selected mirror mode/revision. It hashes actual files
  and shares one locked reader for content aliases. All members must verify before a
  read-only mapping is exposed. It accepts no final-inference authority and generates
  no converted digest or approved inference manifest.
- `prepare_sources`, an async context owning all collection readers/locks while borrowing
  the caller-owned cache. It probes the entire existing set, downloads only missing
  physical identities through the restricted single-asset downloader, revalidates the
  complete set before delivery, and revokes every borrowed reader on exit or failure.
  Actual files must verify even if an injected downloader claims success.
- Reader reuse with explicit ownership of an already-held entry lock. Borrowed readers
  close their file descriptor but not that entry; owning readers close both. Only ENOENT
  from opening the locked final file produces `MissingModelAsset`. Corruption, unsafe
  files, permission failures and lock contention are terminal, not acquisition fallbacks.
- Single-asset download now verifies an existing final under its acquired lock before
  emitting any network request, covering completion by another cooperating cache client
  after the collection's missing probe. Callback and task cancellation are checked on
  local-completion paths and before/after network/retry awaits; cancellation observed
  in progress prevents further chunk writes. No preemption of synchronous disk/hash
  operations is claimed. Existing partial/checkpoint retention rules remain enforced.

ModelScope's endpoint remains unimplemented and blocked. A fully cached source collection
with the selected ModelScope revision may be verified/read locally; a missing member
cannot invoke that endpoint or silently switch to Hugging Face. Redirect handling and the
empty executable registry are unchanged. No socket/model/audio/MLX/converter/process
execution, model selection, public protocol change or accepted artifact amendment occurs.

Pre-review focused verification:

- `uv run pytest -q tests/asr_benchmark/test_source_preparation.py tests/asr_benchmark/test_model_download.py tests/asr_benchmark/test_cache_reader.py`
  — **109 passed in 0.62s**, with 29 new source-collection cases. Tests write only the
  original ordinary notice doubles; no weight/tokenizer/audio content is created.
- `uv run ruff check tools/asr_benchmark tests/asr_benchmark/test_source_preparation.py`
  and `uv run mypy tools/asr_benchmark tests/asr_benchmark/test_source_preparation.py`
  — passed (21 mypy files). Early lint/type feedback was corrected before this run.

- `make asr-benchmark-check` — passed: ruff lint/format, strict mypy (32 files),
  **279 passed in 34.88s**. `git diff --check` — exit 0.

Final verification and review at code head
`7450cf824b774db1b2fb91dabb5fad72896b9ffe`, 2026-10-03 around 02:25–02:28
Asia/Shanghai (UTC+08:00):

- `make verify` — exit 0: ruff lint/format and strict mypy (54 files), workspace
  lint/typechecks, **386 pytest passed in 37.22s**, **128 protocol Vitest tests**,
  **63 Railway Vitest tests**, artifact checks, protocol-generation check and builds.
  Existing protocol tests ran unchanged; no audio/model-runtime admission is inferred.
  Dependencies/locks are unchanged, using the previously recorded workspace bootstrap.
- Isolated `/root/audio_code_readiness` reviewed both new modules/tests and all reader,
  cache and download changes plus README/evidence at that exact clean head. Independent
  `uv run pytest -q tests/asr_benchmark/test_source_preparation.py tests/asr_benchmark/test_model_download.py tests/asr_benchmark/test_cache_reader.py`
  — **109 passed in 0.60s**. Independent `git diff --check` — exit 0.
- The reviewer additionally ran a stdin Python probe: while a missing asset downloaded
  from the original notice/response doubles, a progress callback changed an earlier
  probed file's bytes without changing its length. The collection rejected delivery
  with `cache_reader_unavailable`; the sole response closed, all physical entry locks
  reopened, the newly completed valid asset remained cached, and the caller's parent
  cache stayed open. Exit 0. No complete mapping escaped and no socket was opened.
- No remaining actionable finding was reported. The reviewer ran the focused suite,
  not the full repository suite, and read no new external source in this batch. Earlier
  permitted primary-source exposure remains recorded. `/root` separately reviewed local
  ownership/permission/cancellation control flow read-only without tests or edits;
  its two early cancellation observations were addressed before the stable code head.
- GUI gates before/after batches and long tool boundaries returned active. These are
  local text/control/filesystem checks, not real network/model/MLX/host acceptance.
  Execution registry remains empty; converted output, actual conversion/inference,
  audio/source/process orchestration and hardware evidence remain outstanding.

This batch updates the same draft PR #36 without merging, deployment or closing Issue #5.

### Exact independent mutation probe command

The reviewer executed the following command at reviewed code head
`7450cf824b774db1b2fb91dabb5fad72896b9ffe`, with working directory
`/Users/szmg/.codex/worktrees/livecho-5-asr-impl/Livecho`. It returned exit 0 in 0.03s
and printed the final literal below. The original stdin was subsequently saved verbatim
at `/Users/szmg/.codex/monitors/livecho-20261002/reviews/source-collection-mutation-7450cf8.py`.
Its SHA-256, checked during this documentation follow-up, is
`e90e6915a744b06d28e0f1eb4fd03a4677794f92264633349cf1037ef1cf1b5c`.
The script is included here so remote reviewers do not need that local file.

```sh
uv run python - <<'PY'
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from tools.asr_benchmark.model_cache import ModelOnlyCache
from tools.asr_benchmark.preparation_run import prepare_sources
from tools.asr_benchmark.runtime import BlockedEvidence
from tests.asr_benchmark.test_source_preparation import (
    Factory, assert_unlocked, content, file_path, manifest, populate,
)
from tests.asr_benchmark.test_model_download import Clock

with TemporaryDirectory() as temporary:
    base = Path(temporary).resolve()
    record = manifest()
    existing = record.source_assets[0]
    missing = record.source_assets[1]
    with ModelOnlyCache(base / 'cache', base / 'repo', record, 'huggingface') as cache:
        populate(cache, (existing,))
        factory, clock = Factory(), Clock()
        delivered = False
        changed = False
        def on_progress(item):
            global changed
            if item.outcome == 'partial' and not changed:
                assert item.asset_label != existing.path
                payload = content(existing)
                file_path(base, existing).write_bytes(b'X' + payload[1:])
                changed = True
        async def exercise():
            global delivered
            async with prepare_sources(record, 'huggingface', cache,
                                       response_factory=factory, clock=clock,
                                       sleep=clock.sleep, progress=on_progress):
                delivered = True
        try:
            asyncio.run(exercise())
        except BlockedEvidence as error:
            assert str(error) == 'cache_reader_unavailable', str(error)
        else:
            raise AssertionError('mutated original asset set was delivered')
        assert changed and not delivered and len(factory.responses) == 1
        assert all(response.closed for response in factory.responses)
        assert file_path(base, missing).read_bytes() == content(missing)
        assert not cache.closed
        assert_unlocked(cache)
        print('mutation during missing-asset acquisition: complete mapping not delivered; valid new final preserved; response closed; every lock reusable; parent cache open')
PY
```

This follow-up copied the preserved command into evidence; it did not rerun the probe,
tests or `make verify`. `git diff --exit-code 7450cf824b774db1b2fb91dabb5fad72896b9ffe -- . ':(exclude)docs/changes/5-mlx-benchmark/evidence.md'`
returned exit 0, confirming all non-evidence files equal the reviewed code snapshot.
`git diff --check` also returned exit 0. Only this evidence document changes. The
proposed conversion-session batch remains a future checkpoint; no next-batch code is
started here and no stronger tensor-erasure or synchronous deadline claim is added.

## Conversion-session assignment and interface (before code), 2026-10-03 (UTC+08:00)

- Author `/root/audio_implementation`, OpenAI Codex GUI subagent; isolated reviewer
  `/root/audio_code_readiness`, with `/root` providing read-only lifecycle review.
  Assignment: `conversion_session.py`, focused original text/token tests, the minimum
  required dispatcher validation fix, README and evidence on the existing Issue #5 PR.
- Prior exposure remains exactly the author records above: accepted local requirements,
  local code/tests/policy metadata and the enumerated direct primary documents. New
  reads refresh the owning Issue, all accepted artifacts and local conversion/source/
  cache interfaces. No new external source or excluded author's implementation advice
  was accessed. Reviewer feedback derives from these existing local interfaces only.
  This record precedes code. No accepted intent/spec/plan or public protocol changes.

The preparation-only backend contract for this batch is:

- A synchronous cooperative backend extends the existing `ConversionBackend` operations
  with `converter_revision`, `dependency_lock_sha256`, an `unloaded` state, eager
  `load_sources(preparation, borrowed_readers, local_files_only=True,
  trust_remote_code=False)`, and `close()`. Pin strings/state are interface assertions,
  not proof of actual source revision, isolated execution or host behavior.
- Admission validates the preparation/cache binding, exact converter/lock pins and fresh
  `unloaded is True` before acquisition or backend operations. Ownership transfers to the
  session only after these checks succeed. Before that, rejection performs no backend
  methods and the caller retains cleanup responsibility. After admission, every path
  closes the backend; the caller continues to own its cache.
- Only the complete actual-file-verified mapping from `prepare_sources` enters the eager
  decoder. It returns an exact tuple of named tensor records so duplicate names remain
  detectable. Records must exactly cover the manifest. Source tensors are evaluated and
  synchronized while readers remain borrowed, readers are revalidated, then closed.
  The backend must own everything needed after reader closure and report loaded state.
- Before quantizing anything, describe every tensor and bind each returned rule name to
  its requested name; revalidate shape metadata and the complete dtype/classification/
  operation inventory. Reuse the existing dispatcher for retain and affine 8-bit/group-64
  operations. No new operator implementation, output serialization or inference call.
- Check cooperative cancellation/pin stability before and after backend stages and before
  delivering results. The returned preparation-only borrowed mapping becomes unavailable
  on scope exit and releases its own references; backend close owns cooperative tensor
  cleanup. Already escaped raw tensor references cannot be revoked or erased by Python
  wrappers. No strong erasure, synchronous-compute deadline or actual MLX claim is made.
- Registry remains empty. Tests use original notices and opaque token/control doubles,
  without real network/model/audio, MLX, writer, process runner, or inference approval.

## Preparation conversion-session implementation, 2026-10-03 (UTC+08:00)

Author `/root/audio_implementation` implemented `conversion_session.py` and its original
text/token tests after pre-code assignment/interface commit
`eecf9c8554549780d2fefae02b3a4f0aec5419c1`. No new external source was read. The
existing dispatcher received the minimum name/shape validation and cleanup changes.

The session validates preparation/cache identity, converter/lock pins and fresh unloaded
state before acquisition or backend methods. Rejection before admission leaves ownership
with the caller and calls no backend methods. After admission, the session closes the
backend on every exit, while the caller continues owning its cache. Only actual verified
source readers from `prepare_sources` reach the eager local-only/no-remote-code decoder.
It must return an exact named tuple inventory, evaluate/synchronize, report loaded state
and pass reader revalidation. The readers close before the existing dispatcher runs.
All descriptions are now individually bound to requested names and strictly revalidated,
so swapped names or `model_copy`/`model_construct` shape bypasses cannot reach quantization.

The output is a preparation-only borrowed mapping; no source/converted writer, inference
manifest approval, transcribe call or executable registration is introduced. The backend
contract owns cooperative tensor cleanup. This layer clears its containers and temporary
references on failure/cancellation/exit, including retained local traceback paths. It
cannot erase references already escaped to callers or third-party traceback frames.
Likewise, pin properties are interface assertions, not independently verified source
revision, and post-call cancellation checks are not preemptive synchronous deadlines.

Root's early read-only feedback identified local reference retention during cancellation.
The author added cleanup of the session's converted/source containers and loop locals,
dispatcher partial results under `BaseException`, and wrapper operation/result locals.
Three author-run opaque weakref regressions retain the cancellation exception/traceback
and cover eager-load return, quantized-output evaluation and complete dispatcher return;
the locally owned token references release and backend close occurs exactly once. These
are author-executed tests, not independent executions by root.

Pre-review verification:

- `uv run ruff check tools/asr_benchmark tests/asr_benchmark/test_conversion_session.py`
  — passed.
- `uv run mypy tools/asr_benchmark tests/asr_benchmark/test_conversion_session.py`
  — passed, 22 files.
- `uv run pytest -q tests/asr_benchmark/test_conversion_session.py tests/asr_benchmark/test_artifacts.py`
  — **42 passed in 2.89s**, including 38 new session cases and directly related existing
  artifact/dispatcher checks. Only original notices and opaque tokens were used.

- `make asr-benchmark-check && git diff --check` — passed: ruff check/format and
  mypy (34 files), **317 passed in 37.39s**, and whitespace checks clean.

Final verification and independent review, recorded 2026-10-03 02:58 UTC+08:00:

- Stable code head: `a98b10cef62b15cd0528c361523b91dda7b78c7c`.
- Author: `make verify` — exit 0; **424 pytest passed in 42.06s**, **128 protocol
  Vitest** and **63 Railway Vitest** tests passed, ruff check/format and mypy (56
  files), workspace scripts, change artifacts, protocol generation and builds passed.
  The existing accepted protocol codec tests retain their in-memory synthetic-byte
  scope; no new real model/audio/network/MLX execution was introduced.
- Independent reviewer `/root/audio_code_readiness` confirmed the same clean code
  head before and after executing
  `uv run pytest -q tests/asr_benchmark/test_conversion_session.py tests/asr_benchmark/test_artifacts.py::test_conversion_calls_only_the_exact_affine_interface_and_synchronizes tests/asr_benchmark/test_controls.py::test_conversion_requires_exact_classified_inventory_and_shape`
  — **40 passed in 0.45s**, and `git diff --check` — exit 0. This selection differs
  from the author's 42-test command above. The reviewer read the new session/tests,
  dispatcher changes, README and evidence, focusing on pins, source authority and
  exhaustive inventory. No remaining actionable finding; no new external source read.
- Root independently supplemented lifecycle/owned-reference review at the same code
  head and found no remaining actionable issue. Root's check was read-only: no test
  execution, real MLX or hardware proof. The three weakref regressions were run by
  the author and included in the isolated reviewer's 40-test command; root did not
  execute them. Neither review claims revocation of escaped raw tensor references.
- All GUI gate checks before/after these batches returned active. This final record
  changes evidence only; `git diff a98b10cef62b15cd0528c361523b91dda7b78c7c --exit-code -- tools tests benchmarks/asr/README.md`
  and `git diff --check` both passed before the evidence-only commit. No tests were
  rerun for the documentation addition.

The reviewer also executed this exact command once, from
`/Users/szmg/.codex/worktrees/livecho-5-asr-impl/Livecho`:

```sh
uv run python - < /Users/szmg/.codex/monitors/livecho-20261002/reviews/conversion-negative-shape-a98b10c.py
```

The saved original script's SHA-256 is
`f1a2d3b66a596c8b9a763b6be91e091a9ef813661f7ac281cd14ba4e2d9c187c`.
The author read the script and checked this digest without re-executing it. Its full
stdin contents are included for remote reproducibility:

```python
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.asr_benchmark.conversion import TensorShape
from tools.asr_benchmark.conversion_session import conversion_session
from tools.asr_benchmark.model_cache import ModelOnlyCache
from tools.asr_benchmark.runtime import BlockedEvidence
from tests.asr_benchmark.test_conversion_session import (
    Backend, assert_released, manifest, populate,
)

with TemporaryDirectory() as temporary:
    base = Path(temporary).resolve()
    record = manifest()
    with ModelOnlyCache(base / 'cache', base / 'repo', record, 'huggingface') as cache:
        populate(cache)
        backend = Backend()
        first = record.tensor_map[0]
        backend.descriptions[first.name] = TensorShape.model_construct(
            rule=first, shape=(128, -64)
        )
        delivered = False
        def forbidden_transport():
            raise AssertionError('complete cache unexpectedly requested transport')
        async def exercise():
            global delivered
            async with conversion_session(
                record, 'huggingface', cache, backend,
                response_factory=forbidden_transport,
            ):
                delivered = True
        try:
            asyncio.run(exercise())
        except BlockedEvidence as error:
            assert str(error) == 'tensor_description_invalid', str(error)
        else:
            raise AssertionError('negative tensor dimension reached conversion output')
        assert not delivered and 'quantize' not in backend.events
        assert backend.events == [
            'load', 'evaluate_source', 'synchronize_source',
            'describe:' + first.name, 'close',
        ]
        assert backend.closed and all(reader.closed for reader in backend.readers.values())
        assert_released(cache)
        print('model_construct negative dimension: rejected before quantization; no output or transport; owned backend/readers closed; cache locks reusable')
```

Actual result: exit 0 in 0.0476s; output was the script's final print text. The
negative dimension was rejected as `tensor_description_invalid` before quantization,
without yielding a mapping or requesting transport; backend/readers closed and cache
locks were reusable. Input consisted solely of original notice text and opaque control
tokens. This is no evidence for model serialization, actual MLX compatibility, fresh
processes, protected hosts or scored hardware results; those acceptance gaps stay open.

## Converted storage assignment before code, 2026-10-03 (UTC+08:00)

- Author `/root/audio_implementation`; isolated reviewer `/root/audio_code_readiness`;
  root supplements read-only transaction/lifecycle review. This assignment follows
  `f1c9b75f939c968e07420944ffb8fd207180ede6` in the same Issue #5 draft PR/worktree.
- Exposure is not zero: the prior records of accepted local requirements, local code,
  policy/reference-name/license metadata and permitted primary API/standard reads remain
  applicable. For this batch the author refreshed Issue #5 (including its existing
  review-question comment), AGENTS, all four accepted change artifacts (focusing on
  added evidence), independent-implementation policy and existing cache/reader/contracts/
  conversion code/tests. No new external documentation, reference implementation or
  excluded incident expression was read. The original exposed author is not consulted.
- Scope: `tools/asr_benchmark/converted_store.py`, original ordinary-text/control tests,
  README and evidence only, except a minimal existing cache boundary correction if
  demonstrated necessary. No actual model serialization, tensor bytes, audio, network,
  MLX, inference approval, public protocol or registry change. No source asset SHA is
  invented to open an output transaction.

The pre-code storage contract is:

- A closed output plan binds the exact preparation digest, converter revision and lock
  digest. Its unique model-only output labels declare path/kind and per-file byte caps,
  with a total byte cap and complete weights/tokenizer/config/notice kinds. Internal
  resource ceilings are 256 labels, 64 GiB per file and 128 GiB total; the plan declares
  equal or smaller caps. These are storage admission ceilings, not measured model sizes
  or an expansion of any audio allocation limit. Path validation follows existing model
  asset rules. Every label must finish once; unknown/duplicate/missing output fails.
- `ConversionStaging` is a synchronous preparation-only context. Each `open_output`
  lends a sequential bounded-chunk sink without exposing paths or file descriptors.
  Actual size/hash come from the private held regular-file fd after writing, with
  nofollow, link-count, same-inode/fingerprint checks and fsync. Cooperative cancellation
  is checked around bounded I/O; synchronous syscalls have no claimed hard deadline.
- The Git-external private cache uses a preparation-scoped single-writer lock and a
  private uniquely named transaction staging directory. Published content uses the exact
  existing `FinalModelCache` identity `(preparation_sha256, canonical source_revision,
  actual_output_sha256)` and per-asset lock naming, never a selected mirror revision.
  Equal content aliases share one physical asset; existing assets must pass actual
  size/hash verification and are never overwritten, repaired or deleted by this layer.
- The authoritative **complete-set publication point is one atomic receipt rename**,
  followed by directory fsync, after every output asset is validated and durable. Per-file
  renames are not an atomic set. The closed receipt contains actual asset metadata and
  plan/preparation/converter/lock bindings, explicitly marked unapproved; it contains no
  Approval or inference authority. It is not accepted as an InferenceManifest.
- Before that commit point, a failure/crash can leave already published immutable model
  assets without a receipt. They confer no complete-set authority, are retained and may
  be reused only after fresh hash verification. Cleanup removes only this transaction's
  staging. Crash-abandoned UUID stages are not automatically adopted/deleted. After a
  receipt rename but failed fsync/return, outcome is uncertain: preserve the receipt and
  assets and require a reopen that validates the full set. Never report successful
  completion before fsync. Retry with identical receipt is idempotent; a conflicting
  receipt is terminal and cannot replace prior output.
- Reopening checks receipt identity/inventory/caps and hashes all referenced assets under
  their existing locks. This proves stored bytes and metadata only, not serializer format,
  quantization semantics, rights, MLX compatibility or owner approval. This batch does not
  wire a serializer or authorize inference. Tests persist only original ordinary text.

## Converted storage implementation, 2026-10-03 (UTC+08:00)

Author `/root/audio_implementation` implemented the storage contract after pre-code
commit `ca344c17e0698e0e46eb27acbd42b0ad76f5103f`, using only the recorded local
requirements and existing code. No new external source was read. `converted_store.py`
adds closed output plans, bounded borrowed sinks, actual fd size/SHA verification,
canonical final-cache identity/locks, content alias reuse, and an unapproved complete-set
receipt. `bind_inference` now strictly revalidates both manifest schemas so a receipt or
an unapproved lookalike cannot act as an inference manifest. No Approval is created.

The complete-set commit is the receipt rename followed by directory fsync, after durable
individual asset publication. Errors before that point preserve earlier immutable assets
without granting complete-set authority. Errors after rename preserve the receipt and
assets; a reopen rehashes visible bytes but does not repair a failed directory fsync.
An identical commit retry revalidates the entire prior set and fsyncs again; it does not
repair a damaged/missing previously committed asset. Unknown orphan stages are retained,
and cleanup removes only names/inodes owned by this transaction. Cooperative locks and
injected faults do not prove malicious-host or actual power-loss durability guarantees.

Root's read-only draft review identified the fd between output creation and a second
fallible stat; the author added explicit local ownership cleanup and targeted tests for
both stat boundaries and the stage-directory open failure. Root also clarified visible
receipt revalidation versus durability retry. All tests so far were run by the author:

- `uv run ruff format tools/asr_benchmark/converted_store.py tests/asr_benchmark/test_converted_store.py`
  and `uv run ruff check tools/asr_benchmark/converted_store.py tests/asr_benchmark/test_converted_store.py`
  — passed after routine style corrections.
- `uv run mypy tools/asr_benchmark/converted_store.py tests/asr_benchmark/test_converted_store.py`
  — passed, 2 files, after using the imported `os` directly in fault injections.
- `uv run pytest -q tests/asr_benchmark/test_converted_store.py` — initial full fault
  matrix **58 passed in 0.34s**, then expanded fd/substitution/canonical-identity matrix
  **66 passed in 0.35s**. Subsequent final checks are recorded below; no network, model,
  tensor/audio bytes, MLX, serializer or inference execution occurred.

Final verification and review, recorded 2026-10-03 03:34 UTC+08:00:

- Initial code snapshot `c525c7754a1e5a7f7093f2bc4ccf52f5dde758cf` passed
  `make asr-benchmark-check && git diff --check`: **384 passed in 40.16s**, ruff
  check/format and mypy (36 files), whitespace check clean. The author then identified
  missing receipt-byte readback before publication and added bounded payload equality,
  length and stable inode/fingerprint checks plus same-length/append regressions.
- Final code head is `f71db2fb4de8955b4799212f3e29f668270cdffc`. Author commands
  `uv run ruff check tools/asr_benchmark/converted_store.py tests/asr_benchmark/test_converted_store.py`,
  `uv run ruff format --check tools/asr_benchmark/converted_store.py tests/asr_benchmark/test_converted_store.py`,
  `uv run mypy tools/asr_benchmark/converted_store.py tests/asr_benchmark/test_converted_store.py`
  and `uv run pytest -q tests/asr_benchmark/test_converted_store.py` passed: 2 files,
  **69 tests in 0.38s**.
- Author ran `make asr-benchmark-check && make verify` at that final code head:
  specialized **386 passed in 40.28s** with ruff/format/mypy (36 files); complete
  verification **493 pytest passed in 39.49s**, **128 protocol Vitest**, **63 Railway
  Vitest**, ruff/format/mypy (58 files), workspace scripts, change artifacts, protocol
  generation and builds all passed, exit 0. Existing accepted in-memory protocol-byte
  tests are unchanged. No new runtime audio admission or real model execution occurred.
- Isolated reviewer `/root/audio_code_readiness` checked that same clean head before
  and after the actual command
  `uv run pytest -q tests/asr_benchmark/test_converted_store.py tests/asr_benchmark/test_cache_reader.py::test_final_binding_mismatch_fails_before_cache_open tests/asr_benchmark/test_cache_reader.py::test_preparation_files_cannot_substitute_for_converted_files tests/asr_benchmark/test_controls.py::test_conversion_requires_exact_classified_inventory_and_shape`
  — **75 passed in 0.38s**, comprising 69 storage cases and 6 selected binding cases;
  `git diff --check` passed. This is a different selection from the author's 69-test
  command. The reviewer read the new store/tests, strict manifest binding, README and
  evidence, focusing on closed plan/pins/bounds, fd hashing, receipt authority and final
  cache compatibility. No remaining actionable finding; no new external source read.
- Root independently reviewed publication/cleanup control flow and the receipt readback
  delta at `f71db2f`, with no remaining actionable finding. Root did not execute tests.
  These tests and the independent probe below perform real filesystem I/O with original
  ordinary text and control doubles; they execute no real model/audio/network/serializer/
  MLX operations. They do not establish power-loss durability, actual format correctness,
  rights approval, trusted-host behavior or measured model quality.
- All GUI gates before/after work remained active. The final addition changes evidence
  only; `git diff f71db2fb4de8955b4799212f3e29f668270cdffc --exit-code -- tools tests benchmarks/asr/README.md`
  and `git diff --check` passed before its commit. No tests/probes were rerun for the
  documentation-only record.

Independent probe: from
`/Users/szmg/.codex/worktrees/livecho-5-asr-impl/Livecho`, the reviewer executed exactly
once:

```sh
uv run python - < /Users/szmg/.codex/monitors/livecho-20261002/reviews/converted-receipt-authority-f71db2f.py
```

The saved script SHA-256 is
`318d4485dd301ad05dad84f3b0eee6cf0bb0fc185d67e70e20edc0b8f030040e`.
The author read and hashed this file without re-execution. The exact stdin script is:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from tools.asr_benchmark.cache_reader import FinalModelCache
from tools.asr_benchmark.contracts import metadata_digest
from tools.asr_benchmark.conversion import TensorInventory
from tools.asr_benchmark.runtime import BlockedEvidence
from tests.asr_benchmark.factories import preparation
from tests.asr_benchmark.test_converted_store import owner, read, write_all

with TemporaryDirectory() as temporary:
    base = Path(temporary).resolve()
    source = preparation()
    with owner(base) as store:
        write_all(store)
        receipt = store.commit()
    assert read(base) == receipt
    assert receipt.status == 'unapproved'
    assert not hasattr(receipt, 'approval') and not hasattr(receipt, 'inference_rights')
    fields = {
        'schema_version': 1,
        'manifest_id': 'unapproved-storage-probe',
        'model': source.model,
        'source_revision': source.source_revision,
        'preparation_sha256': metadata_digest(source),
        'converted_assets': receipt.outputs,
        'tensor_map_sha256': metadata_digest(TensorInventory(tensors=source.tensor_map)),
        'provider_revision': source.converter_revision,
        'dependency_lock_sha256': source.dependency_lock_sha256,
    }
    lookalike = SimpleNamespace(**fields, model_dump=lambda: dict(fields))
    root_calls = []
    def forbidden_root(*args, **kwargs):
        root_calls.append(True)
        raise AssertionError('unapproved metadata reached final-cache filesystem access')
    with patch('tools.asr_benchmark.cache_reader._root_fd', forbidden_root):
        try:
            FinalModelCache(base / 'cache', base / 'repo', source, lookalike)
        except BlockedEvidence as error:
            assert str(error) == 'inference_preparation_mismatch', str(error)
        else:
            raise AssertionError('unapproved lookalike entered final cache')
    assert root_calls == []
    assert read(base) == receipt and receipt.status == 'unapproved'
    print('valid stored bytes and matching outer identity do not confer inference authority: missing approval/rights rejected before cache open; receipt remains unapproved')
```

Actual result: exit 0 in 0.155s; output was the script's final print text. Actual stored
notice assets and receipt reopened successfully. Matching outer model/preparation/revision/
tensor-map/lock/output identity without Approval and inference rights was rejected with
`inference_preparation_mismatch` before any final-cache root access; the receipt remained
unapproved. This probe does not approve an inference manifest or execute a provider.
