# Evidence: Long-session state lifecycle and resynchronization

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

## Release and rollback evidence

Not deployed. Rollback of this pull request deletes the four new Markdown files
and leaves protocol behavior unchanged.
