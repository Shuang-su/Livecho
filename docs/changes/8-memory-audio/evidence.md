# Evidence: Bounded RAM audio requirements

## Artifact approval

- Artifact PR: [#34](https://github.com/Shuang-su/Livecho/pull/34); draft,
  documentation only, does not close Issue #8.
- Approved by/date: Pending @Shuang-su review and merge.
- Base: `67fc6ed`; owning Issue #8 read on 2026-10-02.

## Requirements-author exposure and provenance

- Author: `/root/asr_audio_specs` (OpenAI Codex), independent requirements author,
  `docs/changes/8-memory-audio/**`, 2026-10-02.
- Livecho inputs: supplied and local AGENTS, owning Issues #8/#5, change templates and
  roadmap, accepted Issue #1–#4 artifact material relevant to artifact gating, audio,
  protocol and deployment; Issue #2 ADR, security/lifecycle/policy records; Makefile,
  artifact checker, and the accepted `livecho_protocol/binary.py` PTS predicate and
  end-of-segment lifecycle references. Unrelated long recovery/infrastructure output
  was truncated; no complete line-by-line review of unrelated sections is claimed.
- Reading the accepted independent-implementation policy exposed repository names,
  license metadata and its historical author's exposure statement. No linked LAPLACE
  source/test/schema/fixture/config/docs/assets, screenshots, expression-bearing
  summaries or prior research reports were inspected. Issue #31 was not read. No prior
  contribution to those projects is known in this task context.
- Also authored the separate unmerged Issue #5 benchmark draft. That draft is not an
  accepted requirements source for this Issue. Qwen model cards, MLX API/compilation,
  and Hugging Face download docs were viewed for #5; a broad MLX search showed incidental
  third-party snippets (DeepWiki, mirrors, Reddit), none opened or used as requirements.
- Primary source for this draft: [FFmpeg pipe protocol documentation](https://ffmpeg.org/ffmpeg-protocols.html#pipe),
  viewed 2026-10-02, including inline examples. It documents pipe descriptors and
  bounded I/O block size; it does not prove a process memory cap or no-persistence.
- Assignment is requirements only. `/root/artifact_review` performed independent
  read-only requirements review; implementation assignment remains pending. No source,
  model, dataset, audio, decoder binary, or runtime code
  was downloaded or added during drafting.

## Requirement source map

| Requirement | Source |
| --- | --- |
| Independent synthetic memory input, supervised FFmpeg, 400–600 ms silence, 6 seconds, approximately 800 ms context | Owning Issue #8; this proposal fixes exact behavior locally |
| 30-second media span, 960,000 canonical session/lease bytes, 16,777,216 audio bytes per process, single active room/lease | Accepted Issue #2 spec; ADR `DEC-WORKER-001`; lifecycle `CTRL-AUDIO-RAM-ONLY` |
| Synthetic leases, unchanged binary header/size/ordering/PTS/end flag | Accepted Issue #3 spec and implementation; independent overlap interpretation still required |
| Production default-off, no platform/secret/worker publication enablement | Accepted Issues #2/#4 and Bilibili policy |
| No reference-derived implementation, fresh exposure assignment and isolated review | Accepted independent-implementation policy |
| Pipe descriptors and 4,096-byte I/O block choice | Official FFmpeg pipe capability; size is a Livecho choice, not a vendor memory guarantee |

## Automated verification

| Exact command | Result | Date/tree |
| --- | --- | --- |
| `make bootstrap` | Passed; frozen uv and pnpm installs; no decoder/audio download | 2026-10-02 artifact worktree |
| `git diff --check` | Passed; no whitespace errors | 2026-10-02 artifact worktree |
| `make artifacts` | Passed; `change artifacts: ok` | 2026-10-02 artifact worktree |
| `make verify` | Passed; Ruff, mypy, TypeScript, 107 pytest tests, 128 protocol and 63 Railway Vitest tests, artifact/protocol checks and build | 2026-10-02 artifact worktree |
| `git diff --cached --check && make artifacts && git diff --cached --stat` | Passed after design fixes; exactly four Issue #8 Markdown additions | 2026-10-02 / `60bf7fb` |

## Manual or hardware evidence

No decoder, audio input, VAD, host memory, process teardown or no-persistence validation
has run. This artifact describes required executable evidence; it does not supply it.
FFmpeg build/license/digest, internal allocation proof and no-paging/crash guarantees
are unverified, so audio preflight cannot be considered approved.

## Review findings

- Independent read-only reviewer `/root/artifact_review` checked overlap against accepted
  Issue #3 prose as well as local behavior: nondecreasing original header starts permit
  the proposed 5000 -> 5200 sequence; <=1-second frame, lease and terminal-clear rules
  still apply. Executable compatibility evidence remains pending implementation.
- Review found that ordinary pre-roll after a short silence-closed segment could resend
  earlier PTS. The specification now resets/clamps pre-roll at the emitted end, with a
  dedicated acceptance case. Only forced-duration splits retain the stated context.
- Cross-draft review found #5's benchmark-only provisional prefix access is absent from
  this completed-segment interface. This artifact now states final-caption scope and
  requires a separate accepted runtime decision before early partial delivery.
- Final independent read-only review by `/root/artifact_review`, 2026-10-02, examined
  all eight Issue #5/#8 artifact files, owning Issues and accepted local constraints.
  It confirmed all reported fixes and no remaining actionable artifact-design finding.
  No reviewer edits, runtime/hardware tests, external/reference pages, Issue #31 body,
  or research outputs were involved. This is paper compatibility review only;
  executable overlap, decoder allocation and host guarantees remain pending.
- A 30-second PCM ring would consume the entire canonical allowance before overlap or
  transport. The proposed ring is 16 seconds with explicit reservation partitions.
- Only fixed raw PCM input is admitted first; this avoids claiming that a synthetic
  conversion test proves safety of arbitrary encoded or network media.
- Proposed completed-segment framing preserves actual PTS across 800 ms context, but
  compatibility requires independent review of both accepted prose and behavior.
  The current validator alone is insufficient evidence of permission.
- Byte scans alone cannot prove OS paging/crash safety. The artifact explicitly blocks
  runtime admission until the stronger host/allocation evidence exists.

## Deviations

Uses branch `codex/issue-8-memory-audio-spec` for the repository's accepted naming rule.
No implementation, protocol edit, accepted-artifact rewrite, or production enablement.

## Release and rollback evidence

Not deployed. No production data, live source, model, worker connection or audio is used.

## Independent implementation assignment (before runtime code)

- Author: `/root/audio_implementation` (OpenAI Codex GUI subagent), 2026-10-02.
- Assignment: independently implement Issue #8 under
  `services/backend/src/livecho_backend/audio/`, `tests/audio/`, and the directly
  required Make/Python configuration and this evidence file. The isolated reviewer is
  `/root/audio_code_readiness`; the reviewer does not author this implementation.
- Owner-approved prerequisite: PR #34 merged at
  `93d8b0a4b3e147ce0b7df903f118060117d56f0a`; the parent supplied the owner's explicit
  approval/merge authorization. Accepted intent/spec/plan are unchanged.
- Actual source context before code: the supplied AGENTS.md and local copy; owning
  Issue #8 body and its comment; every file in `docs/changes/8-memory-audio/`;
  accepted independent-implementation policy; relevant accepted Issue #2 architecture,
  audio lifecycle and policy material; accepted Issue #3 protocol specification; local
  repository Makefile/Python configuration and file inventory. Long combined reads of
  architecture, lifecycle, Issue #4 and protocol material were truncated; no complete
  line-by-line review of unrelated infrastructure is claimed.
- The independent-implementation policy exposed its upstream repository names,
  revision/path/license metadata and historical author's exposure statements. The
  owning Issue comment incidentally mentions Issue #31 and Cap's media-cache boundary;
  neither Issue #31 nor a linked reference, implementation, screenshot, research memo,
  upstream source/test/fixture/schema/configuration/docs/assets, or expression-bearing
  upstream summary was opened. No prior upstream contributions are known in this task
  context. No reference source is an implementation input.
- Decision: assign a fresh implementation from accepted Livecho requirements and
  primary standard/vendor documentation only. No external source has been used as of
  this record. Additional primary references, if needed, will be named below.
- Runtime limitation already identified: this checkout contains no approved FFmpeg
  executable/allocation inventory or trusted no-paging/crash evidence. Audio admission
  must fail closed. Metadata/control doubles can run before that evidence; those runs
  cannot establish decoder or host acceptance, and no actual audio is generated merely
  to make an acceptance test appear green.

## Implementation status (2026-10-03, Asia/Shanghai)

The implementation PR is a draft and does **not** close Issue #8 or authorize audio
runtime admission. The accepted intent/spec/plan remain unchanged. Runtime code exists
under `services/backend/src/livecho_backend/audio/`; the approved build and host
registries in `preflight.py` are deliberately empty. `preflight()` rejects before
executable probing, process creation, or audio allocation with
`audio_budget_unverified`. A locally installed broad FFmpeg build or a momentary
zero-swap observation is not substituted for the missing evidence.

Implementation PR: [#37](https://github.com/Shuang-su/Livecho/pull/37). Runtime/test
commit: `14585113819d45a4a279a9dbbc0b24be0b7e5f6d`; preceding exposure/assignment
commit: `39bdb36`. Follow-up evidence commits do not change that reviewed code.

Implemented controls:

- Closed synthetic binding, two exact raw formats, complete 20 ms source frames,
  exact-next local metadata validation, and explicit EOF; source writers are bounded
  and revoked after each read. No URL, arbitrary command/options, encoded media,
  credentials, model, network source, or persisted input interface is introduced.
- Synchronized per-owner canonical reservations, the 960,000-byte session limit,
  30,000 ms retained envelope, 4 MiB parent noncanonical and 8 MiB decoder inventory
  limits, and a shared 16,777,216-byte physical allocation counter. Reservations
  precede buffers/copies; shared ownership counts once, and copies reserve again.
  The fixed canonical transport allowance bounds outstanding input to 100 frames.
- Revocable memory owners and completed segment handles; cleanup clears registered
  consumer copies as well as ring/scratch/input allocations before teardown awaits.
  Consumer release is distinct from failure/expiry invalidation. The deadline uses
  the owner clock, never a consumer-supplied timestamp.
- Integer energy threshold and sample-clock VAD/segment decisions, 3-frame onset,
  bounded 200 ms pre-roll, 25-frame silence closure, exact 6-second cap and continuous
  800 ms context. Ordinary pre-roll cannot rewind an emitted segment end.
- One serialized asynchronous owner, 500 ms backpressure, a shared 2-second initial
  output deadline, source stalls, 1-second handle expiry, terminal gate invalidation,
  two session-wide reconnect delays (250/1,000 ms), and a continuity-break callback.
  No wire epoch or sequence is generated or changed.
- Fixed raw-pipe FFmpeg arguments, exact 4,096-byte pipe capacity checks on the gated
  Linux path, no shell, discarded stderr, stripped environment, disabled core dumps,
  and an independent watchdog that directly owns the decoder process group.
  Parent-liveness EOF triggers bounded TERM/KILL/reap. Linux parent-death signaling
  captures the watchdog identity before fork. Reaping and successful decoding are
  separate outcomes; EOF final publication waits for clean decoder completion.

### Additional implementation inputs

The implementer read the accepted local protocol metadata codec/state and test
configuration while writing compatibility tests. Primary documentation viewed during
implementation was the official [FFmpeg command reference](https://ffmpeg.org/ffmpeg.html),
[FFmpeg pipe protocol](https://ffmpeg.org/ffmpeg-protocols.html#pipe), Python 3.12
[subprocess](https://docs.python.org/3.12/library/subprocess.html) and
[OS vectored I/O](https://docs.python.org/3.12/library/os.html#os.readv) documentation,
and the Linux man-pages project's
[PR_SET_PDEATHSIG reference](https://man7.org/linux/man-pages/man2/PR_SET_PDEATHSIG.2const.html).
These supplied API/option semantics, not an allocation or privacy guarantee. No linked
vendor source code, upstream reference repository, Issue #31 body, audio/model/dataset,
or external research memo was opened or downloaded. The parent relayed local FFmpeg
and swap observations; neither was used as admission evidence.

### Deterministic verification and its limits

`tests/audio/` creates no PCM array, sample fixture, waveform encoding, or audio digest.
It uses independently specified metadata expectations, scalar threshold arithmetic,
reservation records, and process/source/buffer doubles that contain only control
values. The owner-loop tests exercise the real asynchronous pipeline with those
doubles; they do not execute FFmpeg, resample audio, establish native buffer erasure,
or prove OS/process-tree behavior.

The unchanged, accepted Issue #3 tests remain part of `make verify`. Their existing
minimal in-memory binary codec arrays are permitted by that specification; they are
not new Issue #8 runtime admission, and they do not establish the missing host proof.
The new overlap checks pass metadata through the unchanged lease/sequence/budget
validator with its binary parser substituted by validated headers. Existing v1
fixtures and generated protocol files remain byte-for-byte unchanged. Full audio
transport integration remains Issue #9's separately accounted responsibility.

| Exact command | Result | Date / scope |
| --- | --- | --- |
| `make bootstrap` | Passed; frozen uv/pnpm installation, no audio/decoder/model download | 2026-10-02, implementation worktree |
| `make audio-check` | Passed, 102 control-only tests; target explicitly reports trusted runtime acceptance pending | 2026-10-03, implementation worktree |
| `make verify` | Passed: Ruff, mypy, TypeScript, 209 pytest tests, 128 protocol and 63 Railway Vitest tests, artifact/protocol checks and build | 2026-10-03, implementation worktree |
| `make protocol-check` | Passed; generated protocol artifacts unchanged | 2026-10-03, implementation worktree |
| `git diff --check` | Passed | 2026-10-03, implementation worktree |
| `make audio-runtime-check` | **Blocked as required, exit 2:** `audio_budget_unverified`; not a passing or skipped decoder acceptance result | 2026-10-03, implementation worktree |

The first 81-test pass found one strict-literal boolean coercion defect and two test
attribute typos; all were fixed before the passing runs above. Additional owner-loop
regressions were added for review findings, rather than treating the initial suite as
decoder/host acceptance.

### Allocation and privacy evidence still required

The accounting table in the accepted spec is enforced as reservations. It is **not** an
audited FFmpeg/CPython allocation inventory. No exact executable/version/license and
dependency inventory has been approved, no audited decoder/resampler allocation bound
has been supplied, and no supported host proves nonpaging memory and crash-collector
exclusion. The runtime path therefore remains unavailable on this checkout, including
the current macOS host. Adding a metadata record without the owner-reviewed supporting
evidence would not complete acceptance.

Pending trusted checks include actual conversion and sample values for both source
formats; native buffer/copy erasure; decoder/resampler tails; every real pipe/allocation
owner; abnormal FFmpeg exit and TERM resistance; parent SIGKILL/backend restart;
watchdog death and descriptor inheritance; actual process identities and reaping;
and no-paging/crash behavior. `make audio-runtime-check` intentionally cannot turn any
of those pending requirements into a successful skip.

Normal and injected metadata-failure owner-loop runs intercept file writes before
retaining/printing a body, inspect their empty sandbox temporary directory and logs,
and assert zero remaining buffer owners. No database, object-store, persistent queue,
or cache adapter is added to this module. These application-level controls do not prove
kernel swap/dump safety or no-write behavior of an unapproved decoder; those remain
required trusted evidence. No audio or reversible audio artifact was written.

### Independent review and handoff

Named reviewer `/root/audio_code_readiness` performed read-only review from accepted
Livecho requirements and this implementation, with metadata-only reproductions. Review
found pre-first-run cancellation leaking Alpha admission, concurrent close interrupting
cleanup, incomplete loss/onset metrics, an incorrectly renewed startup deadline, and
clean/late decoder-exit races, and a producer `close()` cancellation bypassing accounting
release. The implementation now has dedicated regressions for
those cases. On 2026-10-03 the reviewer confirmed the exact clean code commit
`14585113819d45a4a279a9dbbc0b24be0b7e5f6d` with no remaining actionable finding in the
bounded review. No upstream expression was supplied by the reviewer or used for fixes.

Independent reviewer verification:

- `PYTHONPATH=services/backend/src:packages/protocol/python uv run pytest -q tests/audio`:
  101 passed in 5.73 seconds before the final source-close regression.
- `PYTHONPATH=services/backend/src:packages/protocol/python uv run pytest -q tests/audio/test_pipeline_control.py tests/audio/test_preflight_supervisor.py`:
  33 passed in 5.70 seconds including the final regression.
- The original source-close-cancellation reproduction then returned a terminal
  `audio_admission_closed`, confirmed decoder reaping, zero ledger/process bytes and
  live buffer owners, released Alpha admission, and did not cancel the owner task.
- The reviewer re-read the exact committed cleanup and regression, but did not claim
  to rerun the author's full `make verify` or execute an actual audio/decoder process.
- Reviewer exposure was accepted Issue #8 planning and Issue #30 local index work,
  local policy/reference-name/license metadata, and Issue #31 title/status only.
  No Issue #31 body, reference expression, external research, audio, model, or real
  child execution was involved. This records a local code/control review, not an
  upstream-expression comparison or a legal conclusion.

The completed-segment API is intended for Issue #9 after the pending evidence gates
pass. It does not provide incremental prefix access, partial-caption timing, a public
endpoint, a platform adapter, or a production enable switch. Disable/cancel invalidates
local capabilities immediately; a failed reap retains the Alpha admission fence.
Rollback has no audio recovery/replay because no audio state is persisted.
