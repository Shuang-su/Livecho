# Evidence: Bounded RAM audio requirements

## Artifact approval

- Artifact PR: Pending creation; documentation only, does not close Issue #8.
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
- Assignment is requirements only. Implementation and independent reviewer clearance
  remain pending. No source, model, dataset, audio, decoder binary, or runtime code
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
