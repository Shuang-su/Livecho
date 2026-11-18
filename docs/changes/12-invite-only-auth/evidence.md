# Evidence: Invite-only magic-link authentication and roles

## Artifact approval

- Artifact PR: [#57](https://github.com/Shuang-su/Livecho/pull/57), merged as
  `878163eacb01514f78580db8d2a5f77db8394c66` on 2026-11-18.
- Status: Owner merged intent, spec, and plan. Implementation follows on a new
  branch and does not rewrite those three files.
- Approved by/date: @Shuang-su / 2026-11-18 (merge of #57).
- Authoring base: `a1f1c22c42944e42feaf9a1682acdfcbc8ffcb98` (`main` at authoring).
- Implementation base: `8fbfa8a8ea359e6d1dd9778c216b489b47630366` (`main`), which
  contains #57 and the merged #27 protocol implementation `8fbfa8a`.
- Branch: `issue/12-invite-only-auth-impl`.

## Requirements-author exposure and assignment

- Identity/role/date: Cursor cloud agent, independent author for
  `docs/changes/12-invite-only-auth/**` only, 2026-11-17. This is authority to
  prepare the draft, not owner approval and not authority to implement.
- Assignment source: the task asked for a documentation-only contract for
  Issue #12. Direct dependencies #2 and #4 are already closed. Implementation
  of auth, mail, sessions, and roles is out of scope for this pull request.
- Repository inputs read: `AGENTS.md`, `CONTRIBUTING.md`, `docs/changes/README.md`,
  the four `_template` files, `docs/roadmap.md`, `docs/requirements-index.md`
  (index rows that name #12), `docs/security/alpha-threat-model.md` (role
  matrix and auth controls), `docs/security/data-lifecycle-and-deletion.md`
  (`DATA-ACCOUNT-IDENTITY`, `DATA-AUTH-BEARER`),
  `docs/operations/railway-secrets.md` (sealed `RESEND_API_KEY` and
  `LIVECHO_SESSION_SIGNING_KEY`), `docs/architecture/adr/0001-alpha-modular-monolith.md`
  (`FLOW-ALLOW-010`), `docs/policy/independent-implementation.md` (author
  exposure rule), `docs/changes/4-railway-deployment-skeleton/intent.md`,
  `spec.md`, `plan.md`, and `evidence.md` (secret slots and the no-schema
  guard), `docs/changes/2-architecture-risk-boundaries/spec.md` (role table),
  and the local-vertical routes `/health` and `/api/viewer/ws`.
- GitHub inputs read 2026-11-17: Issue #12 body and the 2026-09-26 owner
  comment that points at #31 without changing token or session requirements;
  open pull request #56 (format only; that branch was not edited).
- External fact used: Resend's send-email `Idempotency-Key` header, from
  <https://resend.com/docs/api-reference/emails/send-email>, reviewed
  2026-11-17. The page's sample API key was not copied.
- Exclusions: no reference repository, upstream auth source, test, fixture,
  schema, screenshot, or research summary was opened. No model, dataset, audio,
  or live Resend credential was downloaded. No known upstream contribution is
  an input.
- Assignment decision: author this documentation artifact only. A fresh
  implementer exposure record and a separate reviewer are required before the
  later auth implementation. Owner merge of intent, spec, and plan is required
  before that code.

## Automated verification

Commands below were run from this worktree on 2026-11-17 against base
`a1f1c22`, on branch `issue/12-invite-only-auth`, before the artifact commit.
`uv` 0.12.1 was installed for the user account because it was not on `PATH`;
the checker itself is the standard-library script CI runs.

| Command | Result | Date/commit |
| --- | --- | --- |
| `LIVECHO_HEAD_REF=issue/12-invite-only-auth python3 tools/check_change_artifacts.py` | Exit 0. `change artifacts: ok`. Python 3.12.3. | 2026-11-17 / staged tree |
| `LIVECHO_HEAD_REF=issue/12-invite-only-auth uv run python tools/check_change_artifacts.py` | Exit 0. `change artifacts: ok`. | 2026-11-17 / staged tree |
| `LIVECHO_HEAD_REF=issue/12-invite-only-auth make artifacts` | Exit 0. `change artifacts: ok`. | 2026-11-17 / staged tree |
| `uv run pytest -q tests/foundation/test_repository_contract.py` | Exit 0. `40 passed`. | 2026-11-17 / staged tree |
| `git diff --check` | Exit 0. No whitespace errors. | 2026-11-17 / staged tree |
| Local Markdown link check | Exit 0. `local links checked: 4`; `local links ok`. | 2026-11-17 / staged tree |
| `git diff --cached --name-only origin/main` | Exit 0. Exactly the four files in this directory. | 2026-11-17 / staged tree |

`make verify` is the GitHub `Verify` workflow and was not run locally. Live
Resend, Railway variable writes, and production auth were not run. A local
failure that is unrelated to these four files, if one appears in CI, is not a
contract defect.

## Manual or hardware evidence

Not applicable. This pull request does not send mail, mint a session, call
Resend, or run MLX, CUDA, live ingest, or a browser login. No audio bytes were
created.

## Review findings

Artifact review: the owner merged #57. Codex review of that documentation
commit reported no findings. Auth code was blocked until that merge and is in
scope only on `issue/12-invite-only-auth-impl`.

## Implementer exposure and assignment

- Identity/role/paths/date: Cursor cloud agent, Issue #12 implementer for
  `services/backend/src/livecho_backend/auth/**`, `tests/auth/**`, and this
  evidence file, 2026-11-18. This record is committed before those Python
  paths are edited.
- Assignment source: the owner merged #57, then asked for the accepted #12
  contract to be implemented on a new branch from current `main`. The pull
  request must reference #12 and must not use a closing keyword.
- Repository inputs read before code: `AGENTS.md`, `CONTRIBUTING.md`, the four
  accepted files in `docs/changes/12-invite-only-auth/`, live Issue #12 (body
  still lists the original acceptance criteria; GitHub shows it closed by
  @Shuang-su at 2026-11-18T03:42:19Z with reason `completed`), the backend
  package layout, `create_local_vertical_app` health and viewer routes,
  `.env.example`, and `pyproject.toml`. No reference authentication
  implementation, upstream source, fixture, or screenshot was opened.
- External fact carried from the accepted spec, not re-derived: Resend's
  `Idempotency-Key` header. No sample provider key is copied.
- Assignment decision: implement the accepted memory-adapter auth application
  and offline tests. Do not add `db/migrations/`, because that path requires
  the already accepted Issue #4 first-schema guard replacement and is not
  needed for the offline contract tests. Do not provision secrets, call
  Resend, or enable production mail or sessions.
- Independent reviewer: required before merge. This author does not merge the
  implementation pull request.

## Deviations

None relative to this draft. The branch is `issue/12-invite-only-auth` so the
artifact lifecycle check can read issue 12. A `cursor/…` name fails that check.
Product code is intentionally absent.

## Release and rollback evidence

Not deployed. No production traffic, real email, live Resend credential, or
production auth is enabled. Rollback of this pull request deletes the four new
Markdown files and leaves runtime behavior unchanged.

## Implementation verification

Commands below were run on 2026-11-18 from `issue/12-invite-only-auth-impl`
after `make bootstrap`. The auth module under test is
`50656755412fb9445b0cdfd907c62e3a450a32d1`. `make verify` is the GitHub
`Verify` workflow's entry point. Live Resend, Railway provisioning, and
production auth were not run.

| Command | Result | Date/commit |
| --- | --- | --- |
| `uv run pytest -q tests/auth` | Exit 0. `27 passed`. | 2026-11-18 / `5065675` |
| `uv run ruff check services/backend/src/livecho_backend/auth tests/auth` | Exit 0. `All checks passed`. | 2026-11-18 / `5065675` |
| `uv run mypy services/backend/src/livecho_backend/auth tests/auth` | Exit 0. `Success: no issues found in 19 source files`. | 2026-11-18 / `5065675` |
| `LIVECHO_HEAD_REF=issue/12-invite-only-auth-impl make verify` | Exit 0. ruff check and format; mypy 170 files; pytest `973 passed, 1 deselected`; Railway 63, protocol 314, web 51; `change artifacts: ok`; protocol codegen ok; production build ok. | 2026-11-18 / `5065675` |
| `git diff --check` | Exit 0. | 2026-11-18 / `5065675` |
| `rg -n 'RESEND_API_KEY=\\|LIVECHO_SESSION_SIGNING_KEY=' services/backend/src/livecho_backend/auth tests/auth` | No matches. | 2026-11-18 / `5065675` |

The implementation keeps `LIVECHO_EMAIL_ENABLED` false in `.env.example` and
does not add `db/migrations/`. Identity state is the process-local memory
adapter from the spec. A Postgres schema would also have to replace the Issue
#4 no-schema guard; that gate is not taken here. `create_auth_app()` does not
read the process environment, so a present `RESEND_API_KEY` cannot send mail
from the default app. The Resend request builder is invoked only through an
injected transport in tests.

GitHub showed Issue #12 already closed by @Shuang-su at 2026-11-18T03:42:19Z
with reason `completed`, at the artifact merge. This implementation references
#12 and does not use a closing keyword.

Skipped and not passes: live Resend delivery, sealed-variable provisioning,
staging or production sessions, and any deployment.
