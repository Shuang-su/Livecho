# Evidence: Worker invite registration, device identity, and contribution statistics

## Artifact approval

- Artifact PR: Pending. This pull request is documentation only.
- Status: Proposed. Worker-identity code waits until the owner merges
  `intent.md`, `spec.md`, and `plan.md`, and until the owner names the Ed25519
  package in the plan.
- Approved by/date: Pending @Shuang-su review and merge.
- Authoring base: `f62951f2b5a083610a92d155d28afa19e4159dbe` (`main`). That
  commit is the squash-merged Issue #12 implementation from PR #59.
- Branch: `issue/13-worker-invite-identity`.

## Requirements-author exposure and assignment

- Identity/role/date: Cursor cloud agent, independent author for
  `docs/changes/13-worker-invite-identity/**` only, 2026-11-20. This is
  authority to prepare the draft, not owner approval and not authority to
  implement.
- Assignment source: the task asked for a documentation-only contract for
  Issue #13. The task states that #3 and #6 are closed and that #12 is on
  `main` at `f62951f`. Implementation of enrollment, device keys, challenges,
  and statistics is out of scope for this pull request.
- Repository inputs read: `AGENTS.md`, `CONTRIBUTING.md`,
  `docs/changes/README.md`, the four `_template` files,
  `.github/pull_request_template.md`, `docs/roadmap.md` (the #13 row),
  `docs/requirements-index.md` (`IDX-WORKER-IDENTITY-STATS` and the #31 note
  in the #30 spec), `docs/policy/independent-implementation.md` (author
  exposure rule), `docs/security/data-lifecycle-and-deletion.md`
  (`DATA-AUTH-BEARER`, `DATA-WORKER-DEVICE`, the #13 ownership row),
  `docs/security/alpha-threat-model.md` (worker and auth controls),
  `docs/operations/incident-disable-and-recovery.md` (device revocation
  procedure), `docs/changes/3-protocol-v1-contract/spec.md` (Hello, manifest,
  capabilities, version policy), `docs/changes/6-local-mlx-worker/spec.md`
  (local `enroll` is not community enrollment),
  `docs/changes/12-invite-only-auth/intent.md`, `spec.md`, `plan.md`, and
  `evidence.md`, `tools/check_change_artifacts.py` (branch pattern and
  artifact-only rule), `Makefile` (`artifacts`, `verify`), `pyproject.toml`
  (no Ed25519 dependency), and the existing auth modules `policy.py`,
  `crypto.py`, `records.py`, and `app.py` (matrix actions and HMAC labels
  already on `main`).
- GitHub inputs read 2026-11-20: Issue #13 body and the 2026-09-26 owner
  comment that points at #31 and says that direction conflicts with the
  invite-only premise. Issue #31's body was not opened.
- External fact used: RFC 8032 names the Ed25519 signature algorithm the issue
  body already requires. No RFC text is copied. No sample key is copied.
- Exclusions: no reference repository, upstream worker source, test, fixture,
  schema, screenshot, or research summary was opened. No model, dataset,
  audio, or live credential was downloaded. No known upstream contribution is
  an input.
- Assignment decision: author this documentation artifact only. A fresh
  implementer exposure record, a named Ed25519 package, and a separate
  reviewer are required before the later implementation. Owner merge of
  intent, spec, and plan is required before that code.

## Automated verification

Commands below were run from this worktree on 2026-11-20 against base
`f62951f`, on branch `issue/13-worker-invite-identity`. `uv` 0.12.1 was
installed into the user account because it was not on `PATH`. The checker is
the standard-library script CI runs. `make verify` ran before this result
table was inserted. The artifact, whitespace, link, and path commands were
run again after the table was written.

| Command | Result | Date/commit |
| --- | --- | --- |
| `LIVECHO_HEAD_REF=issue/13-worker-invite-identity uv run python tools/check_change_artifacts.py` | Exit 0. `change artifacts: ok`. | 2026-11-20 / documentation tree |
| `LIVECHO_HEAD_REF=issue/13-worker-invite-identity make artifacts` | Exit 0. `change artifacts: ok`. | 2026-11-20 / documentation tree |
| `make verify` | Exit 0. ruff check passed; ruff format, 170 files already formatted; mypy, no issues in 170 source files; pytest `974 passed, 1 deselected`; Railway vitest 63, protocol vitest 314, web vitest 51; `change artifacts: ok`; `protocol generated artifacts: ok`; web production build ok. | 2026-11-20 / tree before this table text |
| `git diff --check` | Exit 0. No whitespace errors. | 2026-11-20 / documentation tree |
| Local Markdown link check | Exit 0. `local links checked: 6`; `local links ok`. | 2026-11-20 / documentation tree |
| `git diff --name-only origin/main` and untracked files | Exit 0. Exactly the four files in this directory. | 2026-11-20 / documentation tree |

`make verify` is the GitHub `Verify` workflow's local entry point. It was run
on this branch. Live enrollment, Resend, Railway provisioning, production
auth, MLX, CUDA, and live ingest were not run. A documentation-only tree has
no implementation verification to record.

## Manual or hardware evidence

Not applicable. This pull request does not enroll a device, sign a challenge,
call Resend, or run MLX, CUDA, live ingest, or a browser. No audio bytes were
created.

## Review findings

No review findings yet. Owner review is pending. This author does not merge
the pull request and does not close Issue #13.

## Deviations

None relative to the issue body premises. The #31 self-service direction is
recorded as not adopted. The branch is `issue/13-worker-invite-identity` so
the artifact lifecycle check can read issue 13. A `cursor/…` name fails that
check. Product code is intentionally absent. `docs/changes/README.md` and
`docs/requirements-index.md` are unchanged: the change README does not require
a new directory to be listed, and an artifact-only diff must stay under
`docs/changes/13-`.

## Release and rollback evidence

Not deployed. No production traffic, real email, live credential, production
auth, community-worker PCM, or CUDA runtime is enabled. Rollback of this pull
request deletes the four new Markdown files and leaves runtime behavior
unchanged.
