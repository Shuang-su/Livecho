# Evidence: Long-session state lifecycle and resynchronization

## Protocol runtime integration assignment — 2026-11-27

- User request: “继续让 Claude Code 推进多 worker 阶段，先解决 #62 的设备持钥证明与连接绑定，再把 #27 的轮换和重同步接入运行时。”
- Implementer Codex, branch `codex/issue-27-runtime-protocol` from main
  `cae5ccd`. Claude Code was assigned a separate design review of the private
  protocol-runtime boundary from first-party inputs only.
- Reviewed the current Issue #27 and owner confirmation, all four accepted
  artifacts, this repository's ordering, PCM metadata, models, lease
  coordinator and protocol tests. The assignment is to connect those existing
  protocol primitives and add focused tests. It excludes changes to app
  listeners, the worker gateway, scheduling policy, the presentation app,
  negotiated schemas, and real audio. The earlier planning work did not
  open reference-project code, fixtures, schemas, or assets. No such
  material informs this implementation.

### Runtime integration checkpoint

- Claude Code reported `claude-opus-5-5` for its independent design review.
  Codex applied the review against the existing code and model types. The
  adapter stages both validated #27 wire notices before changing the lease
  or epoch. It reuses the lease coordinator, the two existing ordering
  domains, and the rotation tombstones. Only the protocol runtime owns the
  shared revision records. Actual control and PCM header acceptance advance
  the cursor counters. The new epoch's media floor is frozen so a worker final
  can be projected to viewers within the same epoch.
- Capacity produces `epoch_rotated` without accepting the candidate. An
  explicit backend replacement is successful and yields the same notice
  pair with reason `lease_replaced`. The old lease is retired and its PCM
  accounting cleared before a successor can be installed. An exact viewer
  cursor emits no gap notice. Other same-session cursors follow the accepted
  expired, retired and unknown cases.
- Service, scheduler, worker CLI and browser wiring are follow-on consumer
  changes. The draft #15 application handoff is in its own branch. The
  original #9 fixture uses minor 0. No generated schemas or wire versions
  changed.

| Command | Observed result, 2026-11-27 |
| --- | --- |
| `uv run --no-sync pytest -q tests/protocol` | 84 passed, including 6 new runtime cases. |
| `uv run --no-sync ruff check packages/protocol/python/livecho_protocol tests/protocol` | Passed. |
| `uv run --no-sync mypy packages/protocol/python/livecho_protocol tests/protocol` | No issues in 19 source files. |
| `make protocol-check` | Generated protocol artifacts match. |
| `make verify` | Passed. 1,009 Python tests, 1 stress case deselected, 428 JS tests, artifact/codegen checks and build passed. |

New tests cover both real ordering domains at capacity, exact sequence and older
epoch handling, old PCM accounting release, successor PTS and text floors,
cursor outcomes, terminal-session fencing, and a notice validation failure
before commit. PCM cases use header metadata without audio payloads.

## Artifact approval

- Artifact PR: Pending.
- Status: Proposed; documentation only. Implementation is not included.
- Approved by/date: Pending @Shuang-su review and merge.
- Authoring base: `a1f1c22c42944e42feaf9a1682acdfcbc8ffcb98` (`main`).
- Branch: `issue/27-long-session-state`.

## Requirements-author exposure and assignment

- Identity/role/date: Cursor cloud agent, independent author for
  `docs/changes/27-long-session-state/**` only, 2026-11-17. This is authority to
  prepare the draft, not owner approval and not authority to implement.
- Assignment source: the task asked for the next unblocked Livecho issue under
  AGENTS.md and CONTRIBUTING.md. #9 and #11 fixture slices are already on main.
  Their remaining acceptance is real MLX / product evidence, which this draft
  does not take. #27 depends only on merged #3 and has no artifact directory yet.
- Repository inputs read: `AGENTS.md`, `CONTRIBUTING.md`, `docs/changes/README.md`,
  the four `_template` files, `docs/roadmap.md`, `docs/requirements-index.md`,
  `docs/changes/3-protocol-v1-contract/spec.md` (transport, models, ordering,
  rejection codes, version policy, PCM header), `docs/changes/3-protocol-v1-contract/plan.md`
  (artifact-then-implementation order), `docs/changes/10-event-normalization/intent.md`
  and `plan.md` (docs-only PR shape), `docs/policy/independent-implementation.md`
  (current decision and pull-request gate), and the current protocol modules
  `models.py`, `state.py`, `compatibility.py`, `errors.py`, and `scalars.py`
  so the new minor names the same fields the accepted code already uses.
- GitHub inputs read 2026-11-17: open issues #9, #11, #12, #13–#19, #27, #28,
  #29, #30, #31, #38; issue bodies for #9, #11, #12, #27, #28, #30; #11 comments;
  open pull requests (none); closed pull requests #51–#55 for branch and
  artifact-before-implementation practice. #31 and #38 bodies were not used as
  requirements.
- Exclusions: no reference repository, upstream source, test, fixture, schema,
  screenshot, or research summary was opened. No model, dataset, or audio was
  downloaded. No known upstream contribution is an input. Policy text that names
  reference repositories was seen only as Livecho's own license record.
- Assignment decision: author this documentation artifact only. A fresh
  implementer exposure record and a separate reviewer are required before the
  later protocol implementation.

## Automated verification

Commands below were run from this worktree on 2026-11-17 against base
`a1f1c22`, before commit. The diff was the four untracked Markdown files in
this directory.

| Command | Result | Date/commit |
| --- | --- | --- |
| `make bootstrap` | Exit 0. uv 0.12.1 created `.venv` and installed the frozen Python lock. pnpm 11.21.0 installed the frozen workspace with `--ignore-scripts`. | 2026-11-17 / uncommitted |
| `make artifacts` | Exit 0. `change artifacts: ok`. | 2026-11-17 / uncommitted |
| `LIVECHO_HEAD_REF=issue/27-long-session-state uv run python tools/check_change_artifacts.py` | Exit 0. `change artifacts: ok`. | 2026-11-17 / uncommitted |
| Local Markdown link check | Exit 0. `local links ok: 1`. | 2026-11-17 / uncommitted |
| `LIVECHO_HEAD_REF=issue/27-long-session-state make verify` | Exit 2 at `uv run pytest -q -m "not stress"`: 934 passed, 1 failed, 1 deselected. Lint, format, mypy, and workspace typecheck had already passed. The failure is `tests/asr_benchmark/test_converted_store.py::test_actual_receipt_aliases_idempotence_and_independent_final_manifest`: the idempotent re-commit changes `st_atime` by one second on this filesystem (`atime` updates on read). That test and store are unchanged from `main`. The same suite on prior GitHub runs reported 935 passed. | 2026-11-17 / uncommitted |
| `pnpm test` | Exit 0. Railway 63, protocol 262 plus browser-entry check, web 51. | 2026-11-17 / uncommitted |
| `uv run python tools/protocol_codegen.py --check` | Exit 0. `protocol generated artifacts: ok`. | 2026-11-17 / uncommitted |
| `pnpm build` | Exit 0. Protocol, Railway, and web production builds completed. | 2026-11-17 / uncommitted |

`git diff --name-only origin/main` is empty until the files are tracked. After
`git add`, the name-only diff must be exactly the four files below. No product
code, schema, or fixture was modified.

## Manual or hardware evidence

Not applicable. This pull request does not run MLX, CUDA, live ingest, or a
browser session. No audio bytes were created.

## Review findings

Codex review on `271c593`
([comment](https://github.com/Shuang-su/Livecho/pull/56#discussion_r4601395290))
found that a minor-1 connection rejected every `protocol_minor: 0` envelope
while the schema section left reused messages on minor 0. A replacement lease,
transcript, timeline event, ack, or error then had no legal encoding. The spec
and plan now require a closed minor-1 twin for every post-selection message,
and leave minor-0 `protocol_minor` literals at 0. Hello and subscribe stay
pre-selection minor-0 requests. After that edit,
`LIVECHO_HEAD_REF=issue/27-long-session-state uv run python tools/check_change_artifacts.py`
exited 0 (`change artifacts: ok`) and the local Markdown link check reported
`local links ok: 1`.

Codex review on `a9ce345`
([comment](https://github.com/Shuang-su/Livecho/pull/56#discussion_r4608955922))
found the memory paragraph counted one revision domain of 4,096 while the
session machine keeps a worker-output domain and a viewer domain. The spec now
gives each of those domains its own 4,096 ceiling, adds the single lease
record, and sets the session ceiling at 8,193 revision records. A crossing in
either full domain rotates both. Owner review of the revised text is still
pending.

## Deviations

None relative to this draft. The branch is `issue/27-long-session-state` so the
artifact lifecycle check can read an issue number. Product code is intentionally
absent until these artifacts are on `main`. The single pytest failure is an
atime comparison in the existing #5 store test on this machine's filesystem; it
is not a change in this diff.

## Implementation

- Branch: `issue/27-long-session-state-impl`, based on `1968239` (`main`, after
  this artifact directory merged in #56).
- Scope: `packages/protocol/**`, `tests/protocol/**`, and this evidence file.
  No backend, web, worker, or ingest changes. `audio_origin` stays `synthetic`.

The historical goldens `version.worker_supported_minor_missing` and
`version.viewer_supported_minor_missing` send `supported_minors: [1]` and expect
`unsupported_minor`. Those codes stay. A worker offer of only minor 1 is
accepted only with the exact three capabilities. A viewer selects minor 1 only
when the offer contains both 0 and 1. That keeps the accepted "existing golden
codes stay" rule.

Codex review on `c66dee8` required three contract alignments, now in this
branch: TypeScript rejects an `EpochRotatedV1` whose opened epoch is not the
closed epoch plus one; `lease_id` accepts a UUIDv4 or the exact zero UUID when
no lease is active; PCM encode/decode and lease acceptance use the negotiated
minor, with minor 0 remaining the default.

| Command | Result |
| --- | --- |
| `uv run pytest -q tests/protocol` | 77 passed after the review fixes below |
| `uv run pytest -q tests/protocol/test_long_session.py` | 9 passed. Counts cover 4,095/4,096/4,097 on each domain, three crossings, ceiling 8,193, and no epoch wrap. |
| `pnpm --filter @livecho/protocol test` | 314 passed after the review fixes, browser entry ok |
| `uv run python tools/protocol_codegen.py --check` | `protocol generated artifacts: ok` |
| `uv run mypy packages/protocol/python tests/protocol` | no issues |
| `uv run pytest -q tests/protocol/test_state.py::test_accept_pcm_enforces_the_lease_negotiated_minor` | Passed. `LeaseRuntimeState.accept_pcm` for a `LeaseV1Minor1` rejects header minor 0 and accepts header minor 1; a minor-0 lease does the reverse. Budget stays 0 on rejection. |
| `make verify` | Exit 0 after wiring `lease.protocol_minor` into `PcmLeaseState`. 946 pytest passed, 1 deselected; protocol 314; web 51; railway 63; artifacts and protocol drift ok. |

## Release and rollback evidence

Not deployed. Rollback of the implementation reverts the Pydantic source and
the generated schema, types, and fixtures together. Minor-0 fixtures keep their
previous codes. A reader without minor 1 rejects those envelopes.
