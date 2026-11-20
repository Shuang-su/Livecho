# Intent: Worker invite registration, device identity, and contribution statistics

## Issue and owner

- GitHub Issue: [#13](https://github.com/Shuang-su/Livecho/issues/13)
- Human owner: @Shuang-su
- Stage/area/risk: `stage:m2`, `area:worker`, `type:security`, `risk:high`

## Problem

Community workers need an invite-only registration path, a device identity that
can be revoked without disabling the contributor account, a model allowlist,
and a non-financial contribution record. The repository has account roles from
Issue #12 and a closed worker protocol from Issue #3. It has no admin-issued
worker enrollment token, no server-side device public key, no signed-challenge
check, and no contributor-visible aggregate limited to the fields Issue #13
names.

The local MLX `enroll` command from Issue #6 writes loopback configuration. It
does not create a community device.

## Desired outcome

### This documentation merge

Lock the implementation contract for a later, separate pull request:

1. An administrator issues a 24-hour single-use worker registration token for
   one active contributor account. The token is shown once. The database stores
   only a verifier hash. The token expires 24 hours after creation or when it
   is used.
2. The worker enrolls an Ed25519 public key with that token. Later calls
   authenticate with a signed server challenge. The private key stays on the
   worker. The server stores the public key only.
3. Challenges are single-use and expire. Replayed challenges fail. Revoking a
   device stops that device and leaves the contributor account unchanged.
4. A schema-valid `WorkerHelloV1` is admitted only when its model reference
   matches the admin allowlist on provider, model id, revision, and SHA-256
   digest. This contract does not add Hello fields and does not change
   `epoch`, `seq`, or `revision`.
5. Stored contribution statistics expose online duration, processed seconds,
   success rate, RTF, and recent health. They include no points, cash,
   redeemable benefit, or financial field.
6. A disallowed model claim, a signature failure, and a revoked device are
   rejected and written to a payload-free audit stand-in.

Merging these documents does not enroll a worker, mount the new routes, send
mail, mint a production session, provision a secret, or turn on production
traffic.

### Explicitly deferred

- Self-service device enrollment by a logged-in user, a richer contribution
  taxonomy, and a public leaderboard. The owner comment on #13 (2026-09-26,
  [comment](https://github.com/Shuang-su/Livecho/issues/13#issuecomment-5847331545))
  points at [#31](https://github.com/Shuang-su/Livecho/issues/31) and states
  that this direction conflicts with the invite-only premise and needs an
  approved spec change first. This contract does not adopt that direction.
  Device public-key identity, replay protection, per-device revocation, the
  model allowlist, and the ban on sending platform credentials to workers
  remain in force.
- The worker WebSocket gateway, heartbeat transport, and lease issuance.
  Issue #14 calls the decision functions defined here.
- The invited statistics screen. Issue #17 renders it. This contract returns
  JSON fields only and adds no app-facing copy.
- The durable account/device checkpoint store, backup replay, and restore
  drill. Issues #4, #16, and #19 already own that evidence. Local revoke in
  this contract is not that drill.
- The pinned Python package that verifies RFC 8032 Ed25519. The plan records
  that choice as blocking implementation. This pull request adds no dependency.

## Non-goals

- Distributing arbitrary code, shell, containers, or server-provided download
  URLs to workers.
- Sending Bilibili credentials, cookies, signed playback URLs, archive keys,
  or other platform secrets to workers.
- Points, cash, redeemable benefits, public leaderboards, or using danmaku
  upload volume as an ASR scoring input.
- Synthetic-check counts, accepted-work breakdowns, and duplicate, rejected,
  or expired result counters as separate published statistics.
- Self-service enrollment, public registration, or a second account system.
- Changing Issue #12's role matrix, cookie, or magic-link rules.
- Changing the protocol package, `epoch`, `seq`, or `revision`.
- Enabling `LIVECHO_EMAIL_ENABLED`, writing `RESEND_API_KEY` or
  `LIVECHO_SESSION_SIGNING_KEY`, deploying auth, or opening production traffic.
- Real ASR, live Bilibili ingest, wired danmaku or superchat, real PCM for
  community workers, or real CUDA.
- Hardware attestation of Apple Silicon. Invite issuance and the model
  allowlist are the controls this issue specifies.
- Rewriting the Issue #6 local `enroll` command into cloud enrollment.

## Constraints and data impact

- Depend on merged #3, #6, and #12. #12 is on `main` at `f62951f`. Honor
  `CTRL-AUTH-EXPIRY`, `CTRL-AUTH-KEY-LIFECYCLE`, `CTRL-AUTHZ-DENY-BY-DEFAULT`,
  `CTRL-WORKER-PROTOCOL`, `CTRL-WORKER-REVOCATION`, `CTRL-WORKER-SYNTHETIC-ONLY`,
  `CTRL-AUDIT-PAYLOAD-FREE`, `DATA-AUTH-BEARER`, and `DATA-WORKER-DEVICE` as
  already written. This contract does not weaken the #16 deletion and restore
  rules.
- Call the existing #12 actions `device.issue_enrollment`, `device.manage`,
  and `statistics.read_own`. Do not add a role. Do not issue an account
  session cookie from a worker route.
- Data classification: identity. Stored community-worker fields are the
  enrollment verifier, device public key, device status, allowlisted manifest
  tuples, and the five aggregate fields. Plaintext enrollment tokens exist
  only in the single admin response that minted them. No audio, raw event,
  playback locator, private key, or provider secret is stored or logged.
- Alpha scope stays one operator-selected public free room, invite-only
  workers, an anonymous public live page, synthetic audio for community
  workers, CUDA mock/contract-only, and production traffic off.
- App-facing product copy is zh-Hans-CN. These artifacts stay in the English
  used by the accepted change documents. This issue adds no screen copy.

## Success signal

A reviewer can trace each Issue #13 acceptance checkbox to a spec rule and a
later test. A database dump of an enrollment token contains the verifier and
not the token. A device record contains a public key and not a private key.
Revoking one device leaves the account active. A Hello whose provider, model,
revision, or digest is off the allowlist is rejected and audited. The
statistics object has only the five named metrics. The diff of this pull
request contains the four files in this directory and no application code.

## Human decision

- Status: Proposed; documentation only. Worker-enrollment code is forbidden
  until the repository owner merges this directory's `intent.md`, `spec.md`,
  and `plan.md`, and until the owner names the Ed25519 package recorded in
  the plan.
- Approved by/date: Pending @Shuang-su review and merge.
- Production enrollment, production auth, and secret provisioning: not decided
  here.
- Issue #31 self-service enrollment: not adopted.
