# Specification: Worker invite registration, device identity, and contribution statistics

Normative terms **must**, **must not**, and **may** apply to the later Issue #13
implementation. This document does not enable that implementation.

Accepted contracts this spec uses without rewriting:

- The #12 role matrix and the ban on a second account role or account session
  in [the #12 spec](../12-invite-only-auth/spec.md)
- `WorkerHelloV1`, `ModelManifestRefV1`, `HeartbeatV1`, and `WorkerStatsV1` in
  [the #3 spec](../3-protocol-v1-contract/spec.md)
- The local `enroll` boundary in [the #6 spec](../6-local-mlx-worker/spec.md)
- `DATA-AUTH-BEARER`, `DATA-WORKER-DEVICE`, and `CTRL-AUTH-EXPIRY` in
  [the data lifecycle](../../security/data-lifecycle-and-deletion.md)
- `CTRL-WORKER-PROTOCOL`, `CTRL-WORKER-REVOCATION`, and
  `CTRL-AUDIT-PAYLOAD-FREE` in
  [the threat model](../../security/alpha-threat-model.md) and
  [the incident runbook](../../operations/incident-disable-and-recovery.md)

The owner comment on Issue #13 (2026-09-26,
[comment](https://github.com/Shuang-su/Livecho/issues/13#issuecomment-5847331545))
is an unapproved pointer to Issue #31. It is not an input that adds
self-service enrollment, a public leaderboard, or extra contribution metrics.
These boundaries from that comment are already required here: device public-key
identity, replay protection, per-device revocation, the model allowlist, and
no platform credentials sent to workers.

The issue body's "Hello backend/model/revision/SHA" is the existing
`ModelManifestRefV1` tuple: `provider`, `model_id`, `revision`, and `sha256`.
`sha256` is the lowercase 64-character SHA-256 digest already defined by
Issue #3. This spec adds no Hello field.

## Behavior

### Actors

| Actor | How it is established |
| --- | --- |
| Administrator | An active #12 `admin` session. Actions: `device.issue_enrollment`, `device.manage`. |
| Contributor reader | An active #12 `contributor` session reading `statistics.read_own` for that same account. An admin may read a named account. |
| Worker | No account session. It presents a one-time enrollment token, then a signed challenge. |

A worker route must not set `livecho_session` and must not grant a role.
Account authorization uses the #12 `authorize` decision. Viewer, operator, and
anonymous principals stay denied for the admin and statistics actions. Public
live viewing stays anonymous. `GET /health`, `GET /healthz`, and
`/api/viewer/ws` stay session-free.

Device authentication is an admission for one later Hello decision. It is not
an account session and not a second login system.

### Enrollment token

`POST /api/worker/enrollment-tokens` is `device.issue_enrollment` (admin only).
The JSON object is exactly `{"account_id":"<lowercase uuid>"}`.

The account must exist, have role `contributor`, and have status `active`.
Any other stored account returns `409` and `{"error":"account_ineligible"}`.
An unknown account returns `404` and `{"error":"not_found"}` only after the
caller is authorized as admin. A non-admin receives `403` and
`{"error":"forbidden"}` with no existence check.

A new token uses 32 bytes from a cryptographic generator, returned once as
unpadded base64url. Success returns `201` and
`{"enrollment_id","account_id","expires_at","token"}`. `expires_at` is
`created_at` plus 24 hours, formatted as UTC with millisecond precision and a
`Z` suffix. The token field appears only in that response.

The server stores the account id, a 32-byte HMAC-SHA-256 verifier, `created_at`,
`expires_at`, and `used_at`. The verifier is HMAC-SHA-256 over the label
`livecho-worker-enrollment-v1`, one `0x00` byte, and the raw token bytes, keyed
by a 32-byte key supplied in memory. That label must not verify as the #12
magic-link label or the #12 session label. The plaintext token and the HMAC key
must not be stored. Lookup uses a constant-time compare on the verifier.

While an unused row for that account is unexpired, a later issuance returns
`409` and `{"error":"enrollment_pending"}` and includes no token. The server
has no plaintext to show again. Expiry and use are the invalidation conditions
named by the issue. This contract does not add early replacement.

Redeem is one conditional update that sets `used_at` only when it is still null
and `expires_at` is in the future. Exactly one concurrent redeem wins. Expiry
is absolute. A token is rejected when now is at or after `created_at` plus 24
hours.

The default application receives the HMAC key as an argument. It must not read
`LIVECHO_SESSION_SIGNING_KEY`, `RESEND_API_KEY`, or any other process
environment variable. A missing key returns `503` and `{"error":"unavailable"}`
and writes no row.

### Device enrollment

`POST /api/worker/devices` accepts exactly `{"token","public_key"}`. It does
not read or set an account cookie.

`public_key` is the unpadded base64url form of a 32-byte raw RFC 8032 Ed25519
public key. The body must not contain a private key. Any extra key, including
`private_key`, returns `422` and `{"error":"invalid_body"}` and must not use
the token.

A well-formed request with a bad, used, expired, or unknown token, or a token
whose account is no longer an active contributor, returns `401` and
`{"error":"rejected"}`. Those failures share one body. A malformed body does
not consume the token. The winning update requires the verifier to match, the
row to be unused and unexpired, and the account to still be an active
contributor. When the verifier matches and the account check fails, that same
update marks the row used so the token cannot be presented again. An unknown
verifier changes no row.

Success returns `201` and `{"device_id","account_id"}`. `device_id` is a
server-generated lowercase UUIDv4. The device row stores `device_id`,
`account_id`, the 32 public-key bytes, status `active`, `created_at`, and
`revoked_at: null`. It has no private-key column, no email column, and no token
column. The response must not echo the token or the public key.

### Signed challenges

`POST /api/worker/devices/{device_id}/challenges` accepts exactly `{}`.
`device_id` is a lowercase hyphenated UUID.

Success returns `201` and `{"challenge_id","nonce","expires_at"}`. The nonce is
32 cryptographic bytes as unpadded base64url. `expires_at` is `created_at` plus
120 seconds, absolute, using the same timestamp form as the enrollment token.
The server stores the nonce until the challenge is consumed, then deletes the
nonce bytes and keeps `used_at` so the challenge id cannot be reused.

Issuing a challenge marks any previous unused challenge for that device used,
without creating an admission, and invalidates any unconsumed Hello admission
for that device. Only the newest challenge can still succeed.

A challenge request for an unknown device, a revoked device, or a device whose
account is not an active contributor returns `401` and `{"error":"rejected"}`
and stores no challenge.

`POST /api/worker/challenges/{challenge_id}/verify` accepts exactly
`{"device_id","signature"}`. `signature` is unpadded base64url of the 64-byte
Ed25519 signature over this message:

```text
livecho-worker-challenge-v1 || 0x00 || device_id ASCII || 0x00 || challenge_id ASCII || 0x00 || raw nonce
```

`device_id` and `challenge_id` are lowercase hyphenated UUID strings. The
server verifies that signature with the stored public key. The private key is
never an input.

A well-formed signature that fails verification consumes that challenge.
A second verify, a verify after expiry, a verify of a replaced challenge, and
a verify with no stored nonce return `401` and `{"error":"rejected"}`. A
malformed body returns `422` and does not consume a challenge. Success returns
`204` with an empty body and stores one Hello admission for that device, with
the same `expires_at` as the challenge. The admission is not a cookie.

Quotas, enforced before a new challenge or a verify is attempted:

| Key | Quota | Window |
| --- | --- | --- |
| Known device, newly stored challenges | 30 | rolling 15 minutes |
| Client IP, challenge and verify requests combined | 30 | rolling 15 minutes |
| Client IP, `POST /api/worker/devices` | 30 | rolling 15 minutes |

The client IP is the immediate peer address. This contract does not trust
`X-Forwarded-For`. A missing peer uses one shared fallback bucket per route
family. The IP buckets count every request, including malformed bodies. When
the IP quota is already exceeded, the response is `401` and
`{"error":"rejected"}` so invalid JSON cannot bypass the quota. Under quota,
a malformed body is still `422` and does not consume a token or a challenge.
A well-formed request over the device quota returns that same `401` body, stores
no new challenge, and leaves the current unused challenge as it was. A path
`device_id` that is not a lowercase UUID returns `401` when under the IP quota
and counts only against the IP bucket. Rate-limit buckets are process memory.
They must not be written onto the device row or into logs.

The 120-second lifetime and the quotas above are bounds of this spec. The
issue body requires replay protection and a 24-hour enrollment token. It does
not state these two numbers. The 120-second bound matches the accepted lease
maximum. The count of 30 matches the accepted #12 client quota.

### Revocation

`POST /api/worker/devices/{device_id}/revoke` is `device.manage`. It has no
body. Success and a repeat revoke of the same device return `204`. The device
status becomes `revoked`, `revoked_at` is set on the first revoke, unused
challenges and admissions for that device become unusable, and the bound
account's role and status stay as they were. Other devices of that account
stay active.

An unknown device returns `404` and `{"error":"not_found"}` for an admin, and
`403` and `{"error":"forbidden"}` for every other principal, with no existence
check in the non-admin response.

A revoked device, and a device whose account is not an active contributor,
fails later challenge, verify, Hello admission, health, stats, and online-time
updates. Account disable remains the #12 route. This contract does not change
that route's status codes. The device check reads the account and fails closed
when the account is not an active contributor.

There is no un-revoke. Key rotation is a new device enrollment, not an edit of
the stored public key.

### Allowlist

Allowlist routes are `device.manage`.

| Route | Success |
| --- | --- |
| `POST /api/worker/allowlist` with exactly `provider`, `model_id`, `revision`, `sha256` | `201` on insert, `200` when that tuple already exists |
| `DELETE /api/worker/allowlist` with the same object | `204` when removed, `404` and `{"error":"not_found"}` when absent |
| `GET /api/worker/allowlist` | `200` and a JSON array of those objects, sorted by `provider`, `model_id`, `revision`, then `sha256` |

Each field must satisfy the accepted `ModelManifestRefV1` rules, including a
lowercase 64-character SHA-256 digest. A URL, path, command, or extra key
returns `422` and `{"error":"invalid_body"}`. The list may be empty. This
contract does not insert a real MLX manifest or a CUDA manifest. Tests use a
synthetic tuple. CUDA remains mock/contract-only under Issue #18.

### Hello decision

`admit_hello` is a function the later Issue #14 gateway must call before it
issues a lease. Issue #13 does not mount `livecho.worker.v1` and does not
create a `LeaseV1`.

The input is a `WorkerHelloV1` plus the `device_id` that #14 associates with
the connection. The manifest and capability decision is the existing
`negotiate_worker` function, called with the admin allowlist as
`(provider, model_id, revision, sha256)` tuples. #13 must not replace that
function with a minor-0-only capability list. In particular it must not reject
a Hello solely because `negotiate_worker` selected minor 1 for
`protocol.epoch-rotation`. #13 adds no protocol error code.

The decision applies this order and stops at the first failure:

1. Unknown `device_id`: audit `rejected`.
2. Revoked device, or account no longer an active contributor: audit
   `device_revoked`. Consume a live admission if one exists.
3. Missing, expired, consumed, or mismatched admission, or `worker_id` not
   equal to `device_id`: audit `signature_invalid`. Consume a live admission
   when one exists.
4. `negotiate_worker` returns `manifest_not_allowed` or `capability_required`:
   consume the admission, audit `capability_rejected`, and report that same
   protocol code.
5. `negotiate_worker` returns any other rejection: consume the admission,
   audit `rejected`, and report that protocol code unchanged.

Otherwise consume the admission and return accepted. A consumed admission
cannot admit a second Hello. Two concurrent admissions produce one winner.
Success authorizes no PCM, no real audio, and no model download.

`worker_id` equality is a binding on the existing Hello field. It is not a new
field. Empty manifest lists and tuples that miss the allowlist already produce
`manifest_not_allowed` from `negotiate_worker`, including a provider that is
not listed. This contract inserts no CUDA manifest.

### Statistics

The published object for one device contains exactly these keys:

| Key | Meaning |
| --- | --- |
| `device_id` | Server device id |
| `online_duration_seconds` | Integer seconds accumulated from closed online intervals |
| `processed_seconds` | Integer floor of the latest accepted cumulative `processed_audio_ms / 1000` |
| `success_rate` | Null, or a decimal string |
| `rtf` | Null, or a decimal string copied from the latest accepted `realtime_factor` |
| `recent_health` | Null, or `{"state","observed_at"}` |

`success_rate` is `segments_accepted / (segments_accepted + segments_rejected)`
from that same latest `WorkerStatsV1`, truncated toward zero to at most six
digits after the decimal point, with trailing zeros and a trailing decimal
point removed. The denominator zero yields null, not `1` and not `0`. `state`
is `ready`, `busy`, `draining`, or `error`. `observed_at` uses the timestamp
form above.

`GET /api/worker/statistics` is `statistics.read_own`.

- A contributor with no query receives `200` and `{"devices":[...]}` for that
  account's active devices, sorted by `device_id`.
- A contributor query `account_id` equal to the caller returns the same list.
  Any other `account_id` returns `403` and `{"error":"forbidden"}` with no
  existence check.
- An admin must pass `account_id` and then receives active and revoked devices
  for that account. An admin with no query receives `422` and
  `{"error":"invalid_body"}`. An unknown account returns `404` and
  `{"error":"not_found"}` only for an admin.
- An anonymous caller receives `401` and `{"error":"unauthenticated"}`.

The response must not include email, public keys, tokens, segment counters,
`processed_audio_ms`, points, currency, danmaku counts, or leaderboard fields.
Internal counters used to compute the rate are not response fields.

Update functions, called by tests now and by #14 later:

- `record_stats` accepts the cumulative counters and `realtime_factor` from one
  accepted `WorkerStatsV1` and nothing else. A lower cumulative counter rejects
  the whole update and leaves the previous aggregate. Equal counters may
  refresh `rtf`.
- `record_health` accepts one heartbeat state and `observed_at`. An older
  `observed_at` leaves the previous health in place.
- `note_online` adds `floor(ended_at - started_at)` whole seconds. A negative
  interval is rejected. Sub-second remainder is discarded per call and is not
  carried.

Each update on a revoked or unknown device is rejected, leaves aggregates
unchanged, and is audited. Danmaku volume is not a parameter and is not an
input to `success_rate` or RTF.

`GET /api/worker/devices?account_id=` is `device.manage`. It returns identity
rows `device_id`, `account_id`, `status`, `public_key`, `created_at`, and
`revoked_at`, sorted by `device_id`. `public_key` is unpadded base64url.
Statistics stay on the statistics route. Contributors receive `403`.

### Audit stand-in

Every rejection named above appends one in-memory audit record: time, action,
result code, object class (`enrollment`, `device`, `hello`, or `statistics`),
and a server-issued account id or device id when that id already exists. The
record must not contain email, token, verifier, nonce, signature, public key,
IP address, transcript, audio, or a digest of the token. Unknown
attacker-supplied ids are omitted. This list is the #13 stand-in for
`CTRL-AUDIT-PAYLOAD-FREE`. The 365-day audit store remains Issue #16.

Result codes used in that stand-in are `ok`, `enrollment_pending`,
`account_ineligible`, `not_found`, `invalid_body`, `unavailable`, `rejected`,
`capability_rejected`, `signature_invalid`, `device_revoked`, and
`rate_limited`. Worker-facing HTTP bodies stay the generic `rejected` body
where this spec says so.

## Interfaces and compatibility

The later implementation may add:

- `services/backend/src/livecho_backend/worker_identity/` and
  `tests/worker_identity/`
- `create_worker_identity_app`, unmounted by default
- an injected account lookup and principal resolver that use #12 types
- the decision functions `admit_hello`, `record_stats`, `record_health`, and
  `note_online`
- one process-local memory adapter

It must import #12 authorization rather than copy a second matrix. It must not
change #12 route status codes. It must not modify `packages/protocol/`,
`workers/mlx/`, `db/migrations/`, `.env.example`, CI workflows, or Railway
config. `LIVECHO_EMAIL_ENABLED` stays false. `LIVECHO_PERSISTENCE_ENABLED`
stays false. No new secret name is added.

JSON responses use `Content-Type: application/json`, `Cache-Control: no-store`,
and compact JSON with no insignificant whitespace. Timestamps in this spec use
the protocol's millisecond `Z` form. Clocks and random bytes are injectable.
Tests must not write tokens, keys, signatures, or audio to disk.

The Ed25519 verify operation is RFC 8032 over the message specified above.
The package that performs it is an open decision in the plan. This artifact
does not add that dependency.

No change to `epoch`, `seq`, or `revision` is in scope. A signature field
inside `WorkerHelloV1` would be a protocol change and is out of scope.

## Failure modes and disable path

| Condition | Outcome |
| --- | --- |
| HMAC key absent | Issuance returns `503` and stores nothing. Existing tests that inject a key still run. |
| Unused enrollment token still live | Second issuance returns `409` and no token. |
| Bad, used, or expired enrollment token | `401` `rejected`. The row that exists stays used or expired. |
| Extra `private_key` field | `422`, token not consumed, nothing stored. |
| Replay or expired challenge | `401` `rejected`, audited `signature_invalid`. |
| Revoked device | Further worker calls fail. The account row is unchanged. |
| Empty allowlist or mismatched tuple | Hello decision audits `capability_rejected` and reports `manifest_not_allowed`. |
| Over quota | Same `401` body as an unknown device. No new challenge. |
| Account no longer active | Device operations fail closed. #12 disable status codes stay as they are. |

To stop enrollment later, stop constructing the worker-identity app with a
key and stop mounting it. This issue has no production flag to turn on, and
no production deployment to roll back. Durable restore rejection of old
enrollment verifiers stays with Issues #4, #16, and #19. A future store must
reject restored enrollment verifiers. This memory adapter has no backup and
must not claim that drill.

## Security, privacy, and data lifecycle

- Trust boundary: workers are untrusted. The backend stores the public key and
  verifies signatures. It never receives the private key and never sends
  platform or archive credentials to the worker.
- Enrollment plaintext exists only in the admin response that created it. Logs
  of that route may contain the actor account id, the target account id, the
  action, and the result code. They must not contain the token, URL, verifier,
  key, email, or public key.
- Device deletion and the typed recovery checkpoint follow the existing
  lifecycle text. This issue's local revoke stops one device. It does not
  implement `open(E)`, the checkpoint copy, or restore replay, and it must not
  weaken those rules. Production device authentication stays off until that
  evidence exists.
- Statistics are contributor-own or admin, per the #12 matrix. They are
  operational aggregates, not financial data.
- Community-worker audio stays synthetic. A successful Hello decision is not a
  real-PCM grant. `RISK-WORKER-AUDIO-RETENTION` is unchanged.
- Tests generate keys in process memory and discard them at teardown.

## Acceptance criteria

- [ ] An enrollment token is returned once, the stored row holds the HMAC
      verifier rather than the token, a second use fails, and the token is
      rejected at and after 24 hours from `created_at`.
- [ ] The device row and every response and log lack a private key. The server
      stores the 32-byte Ed25519 public key. A `private_key` field is rejected
      and does not consume a well-formed unused token.
- [ ] A challenge is rejected after use, after replacement, and at expiry. Two
      verifies of one challenge produce one success. Revoking a device leaves
      the account role and status unchanged and fails later authentication for
      that device only.
- [ ] `admit_hello` accepts a Hello only when `worker_id` equals the device
      id, a live admission exists, and `negotiate_worker` accepts the Hello
      against the admin allowlist. A manifest mismatch is audited
      `capability_rejected` and keeps `manifest_not_allowed`. A Hello that
      `negotiate_worker` accepts for minor 1 is not rejected for advertising
      `protocol.epoch-rotation`. No protocol field, `epoch`, `seq`, or
      `revision` change is required.
- [ ] Statistics responses contain only `device_id` and the five metrics
      defined above. Success rate is derived from accepted and rejected
      segment counters. Danmaku volume, points, cash, and leaderboard fields
      are absent.
- [ ] Disallowed manifest claims, signature failures, and revoked devices are
      rejected and appended to the payload-free audit stand-in.
- [ ] The implementation diff does not add self-service enrollment, a public
      leaderboard, live Resend calls, production secrets, real ASR, live
      Bilibili ingest, wired danmaku or superchat, real community-worker PCM,
      or real CUDA.
