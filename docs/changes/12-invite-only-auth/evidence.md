# Evidence: Invite-only magic-link authentication and roles

## Artifact approval

- Artifact PR: Pending.
- Status: Proposed; documentation only. Implementation is not included.
- Approved by/date: Pending @Shuang-su review and merge.
- Authoring base: `a1f1c22c42944e42feaf9a1682acdfcbc8ffcb98` (`main`).
- Branch: `issue/12-invite-only-auth`.

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

None yet. Owner review of the invite-only premise, the matrix, and the decision
not to adopt Issue #31 is still pending. Auth code stays blocked until that
review merges intent, spec, and plan.

## Deviations

None relative to this draft. The branch is `issue/12-invite-only-auth` so the
artifact lifecycle check can read issue 12. A `cursor/…` name fails that check.
Product code is intentionally absent.

## Release and rollback evidence

Not deployed. No production traffic, real email, live Resend credential, or
production auth is enabled. Rollback of this pull request deletes the four new
Markdown files and leaves runtime behavior unchanged.
