# Alpha data lifecycle and deletion controls

## Status and scope

This record implements the documentation decision in Issue #2. It defines mandatory
requirements for later runtime Issues; it does **not** claim that a database, archive,
deletion worker, backup policy, or audio guard is implemented. Production persistence
of normalized events or raw business payloads remains disabled until Issue #16 provides
executable controls and the repository owner accepts the applicable source, rights,
provider, and residual-risk records.

Authorization is deny-by-default. Unless this record identifies a narrower approved
public live projection, every class below is restricted. A shorter source, rights, law,
contract, or platform limit always overrides a longer project limit. Missing, stale, or
ambiguous evidence disables new persistence and publication; it never creates an
unlimited retention grant.

Stable identifiers in this record are compatibility references for later Issues. They
name requirements, not wire fields or runtime schemas.

## Control registry

| Control ID | Required decision | Later evidence owners / integration dependencies |
| --- | --- | --- |
| `CTRL-DATA-RESTRICTED-DEFAULT` | Data is restricted unless a current, per-source and per-field record approves its purpose, audience, retention/review rule, and deletion trigger. | Issues #10, #12, #13, #16, and #17 |
| `CTRL-AUDIO-RAM-ONLY` | Every audio representation is bounded in RAM and is excluded from all persistence, retry, logging, telemetry, crash, and fixture paths. | Issues #3, #8, #14, and #15 |
| `CTRL-RAW-BOUNDARY` | Sanitized raw payloads may enter only an authenticated-encryption path and a private managed boundary; ordinary APIs never receive them. | Issues #10 and #16 |
| `CTRL-AUTH-EXPIRY` | Bearer credentials have the maximum lifetimes, single-use rules, verifier storage, revocation, and purge behavior below. | Issues #12 and #13 |
| `CTRL-AUDIT-PAYLOAD-FREE` | Security, safety-control, raw-access, and deletion audit records contain control metadata but no protected payload. | Issues #12, #13, #16, #17, and #19 |
| `CTRL-DELETION-STATE` | A deletion selects exactly one typed target—canonical room or immutable session—enforces room-over-session dominance and exact-scope idempotent cascade, and reports three truthful states with immutable late-SLA evidence. | Issue #16 |
| `CTRL-BACKUP-EVIDENCE` | Every cache, replica, object version, export, and backup window is enumerated and evidenced; an unknown bound blocks production persistence or restored authentication. | Issues #4, #12, #13, #16, and #19 |
| `CTRL-RESTORE-REPLAY` | A restore is offline and globally disabled until stateful/stateless pre-restore credentials are rejected and current deletion/revocation checkpoints and safety state are replayed and verified. | Issues #4, #12, #13, #16, and #19 |
| `CTRL-IDENTITY-RESTORE-REVOCATION` | Typed pseudonymous account/device checkpoints and auth-invalidation state survive application backups, and every stateful/stateless pre-restore credential is server-rejected before any traffic or authentication. | Issues #4, #12, #13, #16, and #19 |

## Normative lifecycle matrix

| Data ID and class | Location and lifetime | Access and deletion rule |
| --- | --- | --- |
| `DATA-AUDIO-EPHEMERAL`: PCM, encoded audio, audio base64, stream buffers, and audio-bearing derivatives | Conforming backend, decoder, transport, and worker RAM only. Every representation covers at most 30 seconds of monotonic PTS/media time. Missing, conflicting, or non-monotonic duration metadata disqualifies data from every retained buffer. For s16le/16 kHz/mono audio, each backend room/session and each active worker lease separately has a hard aggregate ceiling of 960,000 bytes across rings, in-flight copies, and overlap. Alpha permits one active room and one active audio lease; standby workers receive no PCM until promotion. Each process has a 16,777,216-byte (16 MiB) aggregate ceiling across **all** audio-bearing buffers, including decoder and transport internals. Issues #3 and #8 may set lower limits. There is no audio retry queue: a retry may reference only data still within the existing ring/in-flight budget. Audio must never enter disk, temporary files, databases, queues, logs, telemetry, crash/core dumps, fixtures, caches, or object storage. | Evict consumed frames immediately. Clear audio on segment, session, or lease completion; cancellation; timeout; disconnect; disable; denylist; and teardown. Conforming workers must clear RAM, but a hostile host can copy it; `RISK-WORKER-AUDIO-RETENTION` remains a High residual and is not an erasure guarantee. Transcripts are restricted normalized events and must not embed a recoverable audio representation. |
| `DATA-PLAYBACK-SECRET`: playback URL/token/cookie or upstream credential | Trusted backend ingest memory only during the active connect or refresh operation. Never persisted and never sent to a worker or browser. | Stop use, close the platform session, and clear the local reference after use, refresh, stop, disable, or error. Request upstream revocation only where supported. Every diagnostic redacts both key and value. |
| `DATA-NORMALIZED-EVENT`: normalized event and room/session metadata | Restricted by default. Production Postgres persistence is disabled until Issue #16 implements these controls and a current per-source/per-field record approves purpose, publication, retention/review, and deletion triggers. There is no platform-independent default TTL. Missing or expired evidence stops new persistence and publication. | Anonymous APIs expose only the approved normalized live subset; invited history requires separate authorization. A room selector hides/blocks the canonical room and purges room metadata plus every current/historical/pending/late/restored session; a session selector hides/blocks and purges only the uniquely resolved immutable session and preserves siblings/shared room state. Active stores must purge within 24 hours. |
| `DATA-RAW-BUSINESS`: sanitized raw business payload | Production persistence is disabled until the normalized-data gates and Issue #16 sanitization, key, encryption, audit, manifest, and deletion controls pass. If enabled, raw data may exist only in the private Bucket after credentials, playback locators, excess identity, and every audio representation are rejected or removed, then compressed and encrypted with AES-256-GCM using separate keys. It has no platform-independent TTL. | Admin-only managed export with per-access audit. Never an ordinary/public API response or browser cache. Delete every object/version in the selected room-wide or session-only scope from active storage within 24 hours. Sanitization, encryption, key, audit, manifest, or storage failure prevents archival and must not spill raw data into Postgres, logs, queues, or temporary files. |
| `DATA-ACCOUNT-IDENTITY`: invite/account identity | Disabled until Issue #12. Then only the invited email, role, and minimum account/revocation state may remain while the account is active. | Subject or admin access only. Revoke access immediately. An approved account deletion purges identifying active-store fields within 24 hours and writes the typed pseudonymous recovery checkpoint required by `CTRL-IDENTITY-RESTORE-REVOCATION`; an application-data restore must not recreate the account or its authority. |
| `DATA-AUTH-BEARER`: authentication, enrollment, and session bearer secret | Disabled until its owning Issue. A magic link is single-use and valid for at most 15 minutes; a worker enrollment token is single-use and valid for at most 24 hours; a session cookie is individually revocable and valid for at most 30 days. The database stores only a verifier hash plus expiry/use state. Plaintext exists only in the intended Resend email or initiating client flow, never in a database, log, telemetry event, or URL analytics. | Expiry, use, or revocation immediately prevents future server acceptance; this does not claim erasure of plaintext in an email/client. Account/device deletion revokes related tokens and sessions immediately and purges active verifier/session rows within 24 hours. Every restore purges/revokes all restored magic-link, enrollment-token, session-verifier, and session rows and advances/reconciles a recovery-protected monotonic auth-invalidation generation or non-restorable signing/verifier key version. All pre-restore stateful/stateless credentials remain server-rejected, and current verification secret material is never restored from an application backup. Issue #12 owns account authentication/session evidence; Issue #13 owns worker enrollment evidence. |
| `DATA-WORKER-DEVICE`: device identity and aggregate worker statistics | Disabled until Issue #13. Then limited to device public key, status, allowlisted capabilities, online/processed duration, success rate, RTF, and recent health while registered. | A contributor sees only that contributor's aggregates; an admin manages devices. Revoke immediately. Device/account deletion purges identifying active-store fields within 24 hours and writes a typed pseudonymous recovery checkpoint; a restore must replay it before accepting device authentication or traffic. |
| `DATA-AUDIT`: security, control, deletion, and raw-access audit | Append-only actor/control result, timestamps, object class, safety generation, opaque manifest reference/count, and integrity metadata for 365 days. It contains no account/device checkpoint target, event body, email, public key, secret, playback locator, audio, transcript, or digest of low-entropy/raw values. Any opaque actor reference remains restricted pseudonymous data. Keyed integrity digests cover canonical manifest/control records, never deleted content. | Restricted admin/auditor access. After 365 days, purge active audit rows within 24 hours unless a documented incident hold names an owner and expiry. The payload-free field contract is also defined by `CTRL-AUDIT-PAYLOAD-FREE` in the incident runbook. |
| `DATA-DELETION-TOMBSTONE`: room/session deletion manifest/tombstone | Exactly one typed selector (`room` bound to a canonical room or `session` bound to a uniquely resolved immutable session), opaque target reference, deletion state, safety generation, timestamps, and payload-free counts only. It must be held separately from restorable application data and be available to every restore. | A room tombstone dominates every child-session tombstone and replays over room metadata plus every current, historical, pending, late-discovered, or restored session belonging to that room; a later session request cannot narrow or overwrite it. A session tombstone replays only over that session and its derivatives. Retain while any live/history store, object version, export, replica, or backup can reintroduce the selected scope and through at least one successful restore verification after the last backup window. It contains no raw, identity, event, transcript, or audio content. |
| `DATA-IDENTITY-REVOCATION-CHECKPOINT`: account/device deletion or revocation checkpoint | Restricted pseudonymous control data held in the separate encrypted, integrity-protected recovery copy: typed random immutable never-reused internal account/device reference, operation (`deleted` or `revoked`), monotonic control generation, timestamp, and payload-free result. Never email, role, device public key, IP address, bearer/verifier hash, content, or an unkeyed digest of a low-entropy value. | A permanent deletion checkpoint is never converted back to a reversible revocation; a current revocation generation cannot be rolled back by a backup. Retain until the longest enumerated backup/object window that can reintroduce the target has passed and through one successful post-window restore, then delete under an audited rule. Access is narrowly authorized and audited because even opaque references are linkable pseudonymous identity. |
| `DATA-MANAGED-RAW-EXPORT`: managed raw export and access capability | Disabled until Issue #16. The access capability lasts at most 15 minutes; an encrypted managed export object lasts at most 24 hours. Alpha forbids untracked local plaintext copies by default. | Per-access admin audit. Revoke/delete every managed object in the selected room-wide or exact-session scope within 24 hours. Revoking authorization prevents future access but does not claim erasure of plaintext already disclosed. Introducing such disclosure requires a named High residual, a bounded destination, and owner acceptance. |
| `DATA-DERIVED-COPY`: cache, index, replica, object version, or backup | Never an independent source of truth. Active copies follow the 24-hour purge SLA. Each production configuration must enumerate its actual schedules, object-version behavior, recovery window, and deletion/purge evidence. | Restore remains offline and globally disabled until protected auth-invalidation state rejects pre-restore credentials and typed room-all-session/session-exact plus account/device deletion/revocation records and current safety/denylist state replay successfully. Unknown, conflicting, unbounded, or untested provider behavior blocks production persistence and restored authentication. |

## Audio budget and teardown invariants

`CTRL-AUDIO-RAM-ONLY` applies independently at every component crossing. It is not
satisfied merely because the primary ring is 30 seconds: overlap, in-flight transport,
decoder internals, copies awaiting a worker, and the active worker's ring all count
toward their applicable ceilings. Implementations must reject input before retaining it
when duration cannot be established from monotonic media time. Backpressure drops or
rejects audio inside the current budget; it must never create a persistent or separate
retry buffer.

The 960,000-byte ceiling is the exact 30-second canonical s16le/16 kHz/mono budget
(`30 * 16,000 * 2`). It applies separately to the one active backend room/session and
the one active worker lease. The process-wide 16,777,216-byte ceiling is not an extra
per-room allowance. Standby workers receive no PCM until one is promoted and the prior
lease is no longer active. Lease revocation prevents future disclosure and triggers
conforming-client clearing; it does not prove that a malicious host erased a copy.

Executable evidence is deliberately deferred: Issue #3 owns bounded protocol metadata
and rejection fixtures; Issue #8 owns decoder/VAD/ring memory accounting and crash-path
proof; Issue #14 owns lease-scoped acceptance, cancellation, and late-frame rejection;
Issue #15 owns single-active-lease promotion/failover without a retry queue. Until those
checks exist and `RISK-WORKER-AUDIO-RETENTION` is individually accepted for real PCM,
community-worker audio is synthetic only.

## Identity revocation and restore rollback

`CTRL-IDENTITY-RESTORE-REVOCATION` prevents an older application-data backup from
recreating deleted authority. Before an account/device deletion or revocation is reported
complete, its typed checkpoint must be committed to the separate encrypted, integrity-
protected recovery boundary and pass read-back verification. A permanent deletion
checkpoint can never become a reversible revocation, and neither form may be overwritten
by a lower generation. Typed internal IDs are random, immutable, and never reused. An
account deletion cascades to its roles, invites, devices, statistics, tokens, and sessions;
a device deletion invalidates only that device's authority plus its enrollment/session
state unless the account is also targeted.

The checkpoint is linkable pseudonymous control data, not anonymous data. It contains no
email, role, device public key, IP address, verifier hash, bearer, event, transcript, or
other user content, and never uses an unkeyed digest of a low-entropy value. Access is
narrowly authorized, encrypted, integrity protected, and audited by opaque manifest
reference/count. If commit, read-back, integrity, or access control fails, the affected
authentication path and restored environment remain disabled; an application-database
row is never the sole record of a deletion or revocation.

Every restore must, while isolated and forced off:

1. purge or revoke every restored magic-link, worker-enrollment, session-verifier, and
   session row regardless of its backed-up expiry or use flag, and advance a recovery-
   protected monotonic auth invalidation generation or signing/verifier key version so a
   stateless pre-restore credential is also rejected; the current version/root and current
   verification secret material live outside application-data backups, and restored old
   key material is never made current or retained in the active verification set;
2. replay every current typed pseudonymous account/device checkpoint to purge or keep
   revoked the restored account, role, invite, device, statistics, verifier, and session
   rows;
3. verify that presenting every sampled pre-restore link/cookie/token is rejected and
   that deleted accounts/devices cannot receive newly issued authority; and
4. only then continue with room/session deletion replay and safety-state reconciliation.

This intentionally requires fresh authentication and enrollment after a restore. It is
safer than attempting to distinguish a legitimately current bearer from state rolled
back by the backup. It does not claim erasure of plaintext still present in an email or
client; it guarantees server rejection. A fresh, non-restored, separately audited admin
recovery authentication may request re-enable after every other gate passes, avoiding a
dependency on the invalid restored admin session. Issue #12 owns account/session behavior,
Issue #13 owns device and enrollment behavior, Issue #16 owns the separate checkpoint and
auth-invalidation inventory, and Issues #4/#19 own the pre-traffic restore proof.

## Room/session deletion state machine

`CTRL-DELETION-STATE` accepts exactly one typed selector, never a required composite:

- `room(canonical_room_id)` selects the canonical room's room-level metadata and every
  current, historical, pending, late-discovered, or restored session belonging to it. It
  blocks new start/reconnect/write/publication for that room while the tombstone applies.
- `session(immutable_session_id)` must resolve uniquely to one session and its owning
  canonical room. It selects only that session and its derivatives; unrelated sessions
  and shared room-level state remain outside the deletion scope. If the selected session
  is active, its ingest/reconnect, lease, audio, locator, and export paths stop immediately.

None, both variants, an ambiguous alias, a caller-supplied parent conflict, or a missing/
non-unique authoritative session resolution is a denial, not a fallback to a broader or
narrower destructive target. Block the widest safely identified exposure (the known room
when proven; otherwise global off), escalate, and do not begin guessed purge. The caller
never has to provide a room for a session selector and cannot override the backend's
authoritative parent-room lookup.

The idempotency key includes selector type plus opaque target reference. Each request
cascades across normalized/transcript rows, indexes, caches, manifests, raw objects and
versions, managed exports/capabilities, replicas, leases, and every other enumerated path
in its scope. A room tombstone dominates child-session tombstones; a later session request
cannot narrow/overwrite the room block, while an earlier session manifest may be linked
into the room manifest without resetting evidence or reviving data. Retrying that selector
continues the existing manifest. Shared aggregates/caches must be purged or recomputed so
a session deletion reveals no selected data without deleting or hiding sibling sessions.

The only externally reportable states are:

1. `hidden`: immediately applies the selector-specific block and hides every selected
   public, ordinary, history, cache, and pending-publication path. This state is entered
   after a valid selector and before destructive work; it persists through any later
   ownership/store ambiguity and every partial failure. Pre-selector ambiguity uses the
   safe containment posture above and never invents a typed manifest.
2. `active-purge-complete`: every room child session/path or exact-session derivative in
   scope has been enumerated, purged, and verified, and a session-only proof confirms
   sibling sessions and shared room state were not deleted. It records an immutable
   completion timestamp. The service-level objective is 24 hours from request acceptance.
   A successful retry after that deadline still enters this state, but permanently records
   `sla_breached=true`; lateness must never be hidden by resetting a request time.
3. `final-retention-window-satisfied`: requires `active-purge-complete`, expiry or
   verified deletion of every managed export, and expiry of every enumerated
   provider-declared backup/object-version window or verifiable provider purge
   evidence. An unknown or untracked plaintext copy prevents this state. A backup that
   is protected by replay but still retained must be reported as retained, never as
   final satisfaction.

The final state proves the documented application, provider-control, and contract
boundary only. It does **not** claim physical-media erasure, instantaneous destruction,
or recall of plaintext already disclosed outside the managed boundary. Provider wording
such as “permanently deleted” is provider evidence, not a Livecho claim about underlying
media.

### Required deletion sequence

1. Authenticate and authorize an admin deletion request. Require exactly one typed room
   or session selector; canonicalize the room or resolve the immutable session and parent
   room from the authoritative index without accepting a missing/non-unique/conflicting
   match. Invalid scope triggers the safe block/escalation above but no guessed purge.
2. Atomically enter `hidden` for the selected scope. A room selector blocks that room's
   new ingest/reconnect, all its session visibility, leases, exports, and persistence. A
   session selector blocks only that session's visibility/derivatives and stops its
   ingest, lease, audio, locator, and export paths if active. Write the typed tombstone
   and a payload-free audit result.
3. Enumerate the selected scope against the versioned store inventory captured by Issue
   #16. For a room selector, enumerate every session for that canonical room on every
   retry/replay; for a session selector, enumerate only that uniquely resolved session.
   Purge normalized rows, indexes, caches, replicas, raw objects/versions, manifests,
   managed exports, and derived/shared projections using idempotent operations.
4. Verify every active store and scope boundary. A room manifest cannot complete while
   any child session/path is unenumerated or unchecked; a session manifest cannot complete
   without proving its derivatives are gone and siblings/shared room state remain. An
   ownership ambiguity or partial failure keeps the safe block, records only a payload-
   free code/count, schedules idempotent retry, and forbids active completion.
5. Enter `active-purge-complete` only after all active checks pass, preserving the
   original request time and the truthful SLA result.
6. Track every backup, object-version, and export window. Enter
   `final-retention-window-satisfied` only when all stated conditions above are proven;
   retain the tombstone through one successful post-window restore verification.

Audit counts, keyed manifest digests, and failure metadata must never contain or hash
raw, identity, transcript, event-body, secret, locator, or audio content. Backups may
remain immutable only while inaccessible to application traffic and only if every
restore rejects stateful/stateless pre-restore credentials and replays the current
deletion/revocation checkpoints before any traffic is admitted. The exact forced-off
recovery procedure is `CTRL-RESTORE-REPLAY` in
`docs/operations/incident-disable-and-recovery.md`.

## Current Railway provider evidence and production gate

The following provider observations were captured from official Railway documentation
on 2026-08-24. They describe available provider features; they do not prove that this
repository has selected or configured any schedule:

- Railway's [Postgres backup guide](https://docs.railway.com/guides/postgres-backups-restores)
  documents optional volume schedules of daily snapshots retained 6 days, weekly
  snapshots retained 1 month, and monthly snapshots retained 3 months. Its optional
  PITR layer retains four weekly full backups for a roughly four-week restore window,
  also described in the [PITR reference](https://docs.railway.com/volumes/point-in-time-recovery).
- Railway's [Bucket reference](https://docs.railway.com/storage-buckets) states that
  server-side encryption, object versioning, object locks, and bucket lifecycle
  configuration are not supported, and that a deleted bucket remains restorable for
  two days. Application-layer AES-256-GCM is therefore mandatory for any future raw
  object; provider privacy alone is insufficient.
- Railway's [Volume reference](https://docs.railway.com/volumes/reference) states that a
  deleted volume is restorable during a window of up to 48 hours before the provider
  reports permanent deletion.

Issue #16's implementation owner must recapture these mutable pages and the exact
production configuration during implementation review; the repository owner is the
governance review owner for accepting that bounded provider configuration. No immutable
provider-document revision was published on the pages captured above, so their canonical
URLs and capture date are recorded rather than inventing a revision.

No production plan/configuration, Postgres backup schedule, PITR selection, private
Bucket retention mechanism, backup inventory, or restore replay has yet been approved
or evidenced. The Bucket limitations also leave Issue #16 responsible for authenticated
client-side encryption and an independently integrity-protected safety, deletion,
revocation, and authentication-invalidation recovery copy. Consequently normalized and
raw production persistence stays **OFF** until Issue #16 records the configured maximum
window for every store and Issue #19 verifies restore replay. A provider-declared window
is a control boundary, not proof of physical erasure.

If any provider's maximum backup, recovery, object-version, or deletion window remains
unknown, or if a current deletion/revocation checkpoint cannot be made available to all
restores, production persistence and restored authentication remain disabled. Do not
guess a value from an unselected provider option.

## Implementation ownership and acceptance evidence

| Issue | Required evidence before its capability can be enabled |
| --- | --- |
| #3 | Protocol limits and golden fixtures for bounded frame metadata, monotonic media time, and rejection without persistence. |
| #8 | Measured backend/decoder/transport memory ceilings, no persistent/crash path, prompt eviction, and teardown tests. |
| #10 | Restricted normalization/public projection plus raw sanitization that rejects credentials, locators, excess identity, and audio. |
| #12 | Invite/account fields, 15-minute single-use magic link, 30-day revocable session, role checks, identity/token deletion, typed pseudonymous account checkpoint, stateful/stateless pre-restore credential rejection, and fresh recovery-admin authentication. |
| #13 | 24-hour single-use enrollment token, device identity/statistics minimization, typed revocation/purge checkpoint, restored credential/device-authority rejection, and no new issuance to deleted targets. |
| #14 | One active lease's bounded frame acceptance, cancellation/timeout/disconnect clearing, and rejection of late output. |
| #15 | One-active-room/lease scheduling, standby-without-PCM promotion, and failover without an audio retry queue. |
| #16 | Postgres/Bucket access, AES-256-GCM and separate keys, audit, managed export, store inventory, idempotent purge, truthful states, provider windows, exactly-one-selector rejection tests, room-all-sessions versus exact-session/sibling proofs, room-tombstone dominance/restore tests, account/device checkpoints, and the independent auth-invalidation/current-verification-material boundary. |
| #4/#19 | Startup/restore forced-off deployment behavior and a recovery drill proving stateful/stateless pre-restore credential rejection, old-key exclusion, fresh non-restored recovery-admin authentication, and deletion/revocation plus safety replay before traffic. |

Issue #2 supplies no runtime acceptance evidence. A later owner must record the exact
commands, provider configuration, restore results, residual risks, and source/rights
approval in the owning Issue before enabling the corresponding production path.
