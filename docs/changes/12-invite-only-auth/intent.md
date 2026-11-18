# Intent: Invite-only magic-link authentication and roles

## Issue and owner

- GitHub Issue: [#12](https://github.com/Shuang-su/Livecho/issues/12)
- Human owner: @Shuang-su
- Stage/area/risk: `stage:m2`, `area:auth`, `type:security`, `risk:high`

## Problem

History, contribution statistics, and operator controls need an identity that can be
revoked and audited per person. A shared access code cannot do that. The repository
has no invite allowlist, no sign-in path, and no server-side check that distinguishes
viewer, contributor, operator, and admin. Public live viewing must stay usable
without an account.

## Desired outcome

### This documentation merge

Lock the implementation contract for a later, separate pull request:

1. An operator-managed invite allowlist. Only an invited address can obtain a
   session. Requesting a link for an uninvited address and an invited address
   returns the same `202` body.
2. A Resend magic link whose token lasts 15 minutes, works once, and is stored
   only as a verifier hash.
3. A session cookie with `Secure`, `HttpOnly`, and `SameSite=Lax`, an absolute
   lifetime of 30 days, and individual revocation.
4. One deny-by-default role matrix for every protected action. Anonymous callers
   keep the public live surface. Viewer, contributor, operator, and admin are
   not a single ladder.
5. Mail sends are idempotent, rate limited, and logged without the address,
   token, link, cookie, or provider secret.
6. `RESEND_API_KEY` and `LIVECHO_SESSION_SIGNING_KEY` stay Railway sealed
   variables. Staging and production values are issued independently. Both stay
   absent in this change.

Merging these documents does not send mail, mint a production session, provision
a secret, or turn on production traffic.

### Explicitly deferred

- Worker enrollment tokens, device records, and contributor statistics storage.
  Issue #13 consumes the role matrix and must not invent a second account system.
- Normalized history, raw archive, account-deletion checkpoints, and restore
  replay. Issue #16 consumes this contract and the accepted #2 lifecycle rules.
- The invited history/statistics UI and the operator/admin console. Issue #17
  consumes the same matrix and must not grant a role by presenting a page.
- Passwords, public registration, and social or Bilibili OAuth. The owner comment
  on #12 (2026-09-26) points at [#31](https://github.com/Shuang-su/Livecho/issues/31)
  and states that the comment does not change the token or session requirements
  and does not approve a replacement spec. This contract keeps the issue body's
  exclusions.

## Non-goals

- Requiring a session for public live viewing, including `GET /health`,
  `GET /healthz`, and `/api/viewer/ws`.
- Passwords, password reset, magic-link-plus-password, public self-signup, or
  Google, GitHub, or Bilibili sign-in.
- Account linking, conflict merge, or treating a refused platform login as the
  absence of a Livecho identity.
- Enabling `LIVECHO_EMAIL_ENABLED`, writing a Resend key or session signing key,
  deploying auth, or opening production traffic.
- Real ASR, live Bilibili ingest, wire danmaku or superchat, or CUDA.
- Rewriting Issue #13, #16, or #17, or editing their artifact directories.

## Constraints and data impact

- Depend on merged #2 and #4. Honor `CTRL-AUTHZ-DENY-BY-DEFAULT`,
  `CTRL-AUTH-EXPIRY`, `CTRL-AUTH-KEY-LIFECYCLE`, `CTRL-SECRET-CONTAINMENT`,
  `CTRL-AUDIT-PAYLOAD-FREE`, and `FLOW-ALLOW-010` as already written. This
  contract does not restate the #16 deletion state machine or the #4 maintenance
  fence, and it does not weaken either one.
- Data classification: identity. Stored fields are the normalized invited email,
  one application role, account status, and verifier hashes with expiry and use
  state. Plaintext tokens and cookies exist only in the intended email or the
  browser that redeemed the link. No audio, raw event, playback locator, or
  provider secret is stored or logged.
- Repository-owner governance is not an application role. An admin session cannot
  accept a residual risk or bypass a platform restriction.
- The local fixture viewer app stays anonymous. #12 must not wrap it with a
  session requirement.

## Success signal

A reviewer can point at one matrix row per protected action and at tests that
deny every other principal. Invited and uninvited link requests are
byte-identical `202` responses. A database dump of a spent or live token contains
the hash and not the secret. The session cookie carries the three required
attributes and stops working after revoke or 30 days. This documentation merge
succeeds when those rules are in the spec and the diff contains no application
code.

## Human decision

- Status: Proposed; documentation only. Auth code is forbidden until the
  repository owner merges this directory's `intent.md`, `spec.md`, and `plan.md`.
- Approved by/date: Pending @Shuang-su review and merge.
- Production email, production sessions, and secret provisioning: not decided
  here.
