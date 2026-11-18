# Implementation plan: Invite-only magic-link authentication and roles

## Order of work

1. **This pull request is documentation only.** Merge `intent.md`, `spec.md`,
   and `plan.md` before any auth code. The diff is the four files in
   `docs/changes/12-invite-only-auth/`. Do not close #12. Do not edit
   `issue/27-long-session-state` or stack on it.
2. After owner merge, open a separate implementation branch from that `main`
   commit. Append a fresh implementer exposure record to `evidence.md` before
   editing Python or web files. A requirements-author record is not a
   substitute.
3. Add the repository port, memory adapter, HMAC verifiers, and injected clock.
   Unit-test normalization, the identical `202` body, 15-minute expiry,
   single-use compare-and-set, 30-day absolute session expiry, and revocation
   before mounting routes.
4. Mount the HTTP routes and `GET /login/continue` on the auth application.
   Do not register them on `create_local_vertical_app`. Do not require a
   cookie on `/health`, `/healthz`, or `/api/viewer/ws`.
5. Add the decision function for every matrix row, including rows whose
   handlers belong to #13, #16, and #17. Table-test anonymous, viewer,
   contributor, operator, and admin. Deny is the expected result wherever the
   spec does not say allow.
6. Add the in-memory mail sink. Assert one idempotency key per magic-link row,
   no second send while that row is unused and unexpired, and no sink write
   when the address is unknown, the flag is false, or a quota is exhausted.
   Do not call Resend. Do not add the Resend SDK.
7. Keep `LIVECHO_EMAIL_ENABLED=false` and do not add secret names or values to
   `.env.example`. If the implementation introduces `db/migrations/`, replace
   the Issue #4 no-schema guard in that same change and follow the accepted #4
   first-schema rules. Do not apply a migration to Railway.
8. Confirm `git diff` does not touch worker enrollment, history or raw archive,
   the #17 console, protocol packages, ingest, or CUDA paths except for the
   auth module and its tests. Append implementation commands to this issue's
   `evidence.md` only. Do not rewrite the merged intent, spec, or plan.
9. Open one implementation pull request that closes #12 only after that
   evidence is recorded. #13, #16, and #17 stay in their own later changes.

## Verification

**This artifact pull request:**

- `LIVECHO_HEAD_REF=issue/12-invite-only-auth uv run python tools/check_change_artifacts.py`
- `LIVECHO_HEAD_REF=issue/12-invite-only-auth make artifacts`
- `git diff --check`
- Local Markdown link check for the four new files
- `git diff --name-only origin/main` lists only those four files

**Later implementation pull request:**

- `uv run pytest -q` for the new auth tests and `tests/local_vertical`
- A test that invited and uninvited `202` bodies compare equal
- A test that a stored magic-link row has no plaintext token column
- A test that the `Set-Cookie` header contains `Secure`, `HttpOnly`, and
  `SameSite=Lax`, and that a revoked cookie receives `401`
- The full matrix test, including default deny
- `make verify`
- `git diff --check`
- A scan of the diff for `RESEND_API_KEY=` values, session-key values, audio
  fixtures, and paths outside the auth module, its tests, and this evidence
  file

Skipped live Resend, Railway provisioning, and production-auth checks stay
recorded as not run. They are not passes.

## Rollout and rollback

No flag, secret, or deployment changes in either pull request. Mail stays off
because `LIVECHO_EMAIL_ENABLED` remains false and no sealed key is written.
Public live viewing stays anonymous. Rollback of the implementation reverts the
auth module and any migration that landed with it. Rollback of this
documentation pull request deletes the four new Markdown files and leaves
runtime behavior unchanged.

A later owner who enables staging mail must issue a new staging
`RESEND_API_KEY` and a new staging `LIVECHO_SESSION_SIGNING_KEY`, distinct from
production, through the existing sealed-variable path. That enablement is not
authorized here.

## Open decisions

None for Issue #12. Address comparison, the `202` body, token and session
lifetimes, cookie attributes, the role matrix, quotas, idempotency, and the
prohibition on passwords, public registration, and social OAuth are fixed
above. Replacing the invite-only premise with Issue #31 requires a new
owner-merged artifact before code that depends on that replacement. A change
to any rule in the spec needs the same kind of review before code that depends
on the change.
