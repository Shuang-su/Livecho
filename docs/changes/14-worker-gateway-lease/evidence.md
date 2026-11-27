# Evidence: Worker gateway, heartbeat, and lease state machine

## Upgrade proof revision for PR #62

- 2026-11-27, local branch `codex/issue-14-gateway-proof-binding` from PR #62
  head `b751c29`. User request: “继续让 Claude Code 推进多 worker 阶段，先解决
  #62 的设备持钥证明与连接绑定，再把 #27 的轮换和重同步接入运行时。”
- Claude Code reported `claude-opus-5-5` and drafted the requirements and
  acceptance matrix from the Livecho #13 contract and #62 draft. Codex checked
  the #13 store and quota path, reviewed the draft, and applied the documentation
  revision. This assignment covers documentation only. No reference-project
  code, tests, schemas, screenshots, or assets supplied requirements.
- The upgrade verifies a fresh challenge under a separate signature domain
  covering the actual RFC 6455 request key. Only the resulting socket can use
  the verified context. The public device id and standalone #13 HTTP admission
  provide no gateway authorization. A new verified proof supersedes a pending
  context. Challenge issuance alone cannot invalidate an already verified socket.
- Addressed the [P2 error-code review](https://github.com/Shuang-su/Livecho/pull/62#discussion_r4674191520)
  in the local specification and future test matrix. The two error schemas
  still use the existing closed `code` enum.
- `python3 -B tools/check_change_artifacts.py`, `git diff --cached --check`,
  and relative Markdown link validation passed. The branch changes only the
  four #14 artifacts. Cryptographic, WSS, proxy, and runtime verification remain
  tests for the implementation PR after the owner merges this revision.

## Artifact approval

- Artifact PR: Pending. This pull request is documentation only.
- Status: Proposed. Gateway code waits until the owner merges `intent.md`,
  `spec.md`, and `plan.md`.
- Approved by/date: Pending @Shuang-su review and merge.
- Authoring base: `cae5ccd951e1c761163d372dc83558c016ee96d5` (`main`). That
  commit is the squash merge of PR #61, "Implement Issue #13 worker invite
  identity and contribution statistics (#61)".
- Branch: `issue/14-worker-gateway-lease`.

## Requirements-author exposure and assignment

- Identity/role/date: Cursor cloud agent, independent author for
  `docs/changes/14-worker-gateway-lease/**` only, 2026-11-24. This is
  authority to prepare the draft, not owner approval and not authority to
  implement.
- Assignment source: the task asked for a documentation-only contract for
  Issue #14, starting from `cae5ccd951e1c761163d372dc83558c016ee96d5` and not
  rebased onto any other commit. The task states that #3 is closed, that #13
  remains open with its contract and memory adapter already on `main`, and
  that #27 remains open with its protocol implementation already on `main`
  through PR #58. Implementation of the gateway is out of scope for this pull
  request.
- Repository inputs read: `AGENTS.md`, `CONTRIBUTING.md`,
  `docs/changes/README.md`, the four `_template` files,
  `.github/pull_request_template.md`, `docs/roadmap.md` (the #14 row),
  `docs/policy/independent-implementation.md` (author exposure rule and the
  worker-transport requirements row), `docs/security/alpha-threat-model.md`
  (worker controls and worker threats), `docs/security/data-lifecycle-and-deletion.md`
  (the #14 ownership row and `DATA-AUDIO-EPHEMERAL`),
  `docs/changes/3-protocol-v1-contract/spec.md`,
  `docs/changes/13-worker-invite-identity/intent.md`, `spec.md`, and
  `plan.md`, `docs/changes/27-long-session-state/intent.md` and `spec.md`,
  `docs/changes/6-local-mlx-worker/spec.md` (remote lifecycle is later),
  `docs/changes/8-memory-audio/spec.md` (canonical byte rate),
  `docs/changes/9-local-caption-vertical/spec.md` (worker path is not mounted
  by the fixture), `tools/check_change_artifacts.py` (branch pattern and
  artifact-only rule), and `Makefile` (`artifacts`, `verify`). Code read on
  this commit, as the contract to call rather than to change:
  `worker_identity/service.py`, `worker_identity/store.py`,
  `worker_identity/clock.py`, `local_vertical/config.py`,
  `livecho_protocol/models.py`, `livecho_protocol/runtime.py`,
  `livecho_protocol/state.py` (`decide_worker_resume`),
  `livecho_protocol/binary.py`, `livecho_protocol/compatibility.py`,
  `livecho_protocol/long_session.py`, and `livecho_protocol/errors.py`.
- GitHub inputs read 2026-11-24: Issue #14 body and the 2026-09-26 owner
  comment
  `https://github.com/Shuang-su/Livecho/issues/14#issuecomment-5847331711`.
  Issue #31's body was not opened. The task describes #31 as a research
  proposal, and the comment does not adopt it.
- External facts used: none beyond the repository and that GitHub issue. No
  RFC text, vendor API, or reference-project message layout was copied. The
  5-second and 20-second numbers are the issue body's. The frame sizes and
  the 32,000-byte realtime second are the accepted #3 and #8 contracts.
- Exclusions: no reference repository, upstream worker source, test, fixture,
  schema, screenshot, or research summary was opened. No model, dataset,
  audio, or live credential was downloaded. No known upstream contribution is
  an input. The author did not inspect `laplace-live/chatterbox`,
  `laplace-live/event-bridge`, or `laplace-live/ws`.
- Assignment decision: author this documentation artifact only. A fresh
  implementer exposure record and a separate reviewer are required before the
  later implementation. Owner merge of intent, spec, and plan is required
  before that code.

## Automated verification

Commands below were run from this worktree on 2026-11-24 against base
`cae5ccd951e1c761163d372dc83558c016ee96d5`, on branch
`issue/14-worker-gateway-lease`. `uv` 0.12.1 and `pnpm` 11.21.0 were used.
`make bootstrap` completed before `make verify` (frozen `uv sync` and frozen
`pnpm install --ignore-scripts`). `make verify` ran before this result table
was inserted. The artifact, whitespace, link, and path commands were run
again after the table was written.

| Command | Result | Date/commit |
| --- | --- | --- |
| `LIVECHO_HEAD_REF=issue/14-worker-gateway-lease uv run python tools/check_change_artifacts.py` | Exit 0. `change artifacts: ok`. | 2026-11-24 / documentation tree |
| `LIVECHO_HEAD_REF=issue/14-worker-gateway-lease make artifacts` | Exit 0. `change artifacts: ok`. | 2026-11-24 / documentation tree |
| `make verify` | Exit 0. ruff check passed; ruff format, 187 files already formatted; mypy, no issues in 187 source files; pytest `1003 passed, 1 deselected`; Railway vitest 63, protocol vitest 314, web vitest 51; `change artifacts: ok`; `protocol generated artifacts: ok`; web production build ok. | 2026-11-24 / tree before this table text |
| `git diff --check` | Exit 0. No whitespace errors. | 2026-11-24 / documentation tree |
| Local Markdown link check | Exit 0. `local links checked: 6`; `local links ok`. | 2026-11-24 / documentation tree |
| `git diff --name-only origin/main` and untracked files | Exit 0. Exactly the four files in this directory. | 2026-11-24 / documentation tree |

`make verify` is the GitHub `Verify` workflow's local entry point. It was run
on this branch. Live gateway sockets, live ingest, real ASR, CUDA, Resend,
Railway provisioning, and production auth were not run. A documentation-only
tree has no implementation verification to record.

## Manual or hardware evidence

Not applicable. This pull request does not open a worker socket, sign a
challenge, send PCM, or run MLX, CUDA, live ingest, or a browser. No audio
bytes were created.

## Review findings

Owner review is pending. This author does not merge the pull request and does
not close Issue #13 or Issue #14.

## Deviations

None relative to the issue body premises. The #31 research direction is
recorded as not adopted. Successor leases are recorded as not legal in this
issue, which is the `lease_replaced` decision #27 assigns here. The branch is
`issue/14-worker-gateway-lease` so the artifact lifecycle check can read
issue 14. A `cursor/…` name fails that check. Product code is intentionally
absent. `docs/changes/README.md` and `docs/requirements-index.md` are
unchanged: the change README does not require a new directory to be listed,
and an artifact-only diff must stay under `docs/changes/14-`.

## Release and rollback evidence

Not deployed. No production traffic, production auth, mail, live credential,
community-worker PCM, real ASR, or CUDA runtime is enabled. Rollback of this
pull request deletes the four new Markdown files and leaves runtime behavior
unchanged.
