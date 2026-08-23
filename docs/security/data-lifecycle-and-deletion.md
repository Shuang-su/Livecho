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
| `CTRL-DELETION-STATE` | Room/session deletion is idempotent and reports three truthful states, including immutable late-SLA evidence. | Issue #16 |
| `CTRL-BACKUP-EVIDENCE` | Every cache, replica, object version, export, and backup window is enumerated and evidenced; an unknown bound blocks production persistence. | Issues #4, #16, and #19 |
| `CTRL-RESTORE-REPLAY` | A restore is offline and globally disabled until current tombstones and safety state are replayed and verified. | Issues #4, #16, and #19 |

## Normative lifecycle matrix

| Data ID and class | Location and lifetime | Access and deletion rule |
| --- | --- | --- |
| `DATA-AUDIO-EPHEMERAL`: PCM, encoded audio, audio base64, stream buffers, and audio-bearing derivatives | Conforming backend, decoder, transport, and worker RAM only. Every representation covers at most 30 seconds of monotonic PTS/media time. Missing, conflicting, or non-monotonic duration metadata disqualifies data from every retained buffer. For s16le/16 kHz/mono audio, each backend room/session and each active worker lease separately has a hard aggregate ceiling of 960,000 bytes across rings, in-flight copies, and overlap. Alpha permits one active room and one active audio lease; standby workers receive no PCM until promotion. Each process has a 16,777,216-byte (16 MiB) aggregate ceiling across **all** audio-bearing buffers, including decoder and transport internals. Issues #3 and #8 may set lower limits. There is no audio retry queue: a retry may reference only data still within the existing ring/in-flight budget. Audio must never enter disk, temporary files, databases, queues, logs, telemetry, crash/core dumps, fixtures, caches, or object storage. | Evict consumed frames immediately. Clear audio on segment, session, or lease completion; cancellation; timeout; disconnect; disable; denylist; and teardown. Conforming workers must clear RAM, but a hostile host can copy it; `RISK-WORKER-AUDIO-RETENTION` remains a High residual and is not an erasure guarantee. Transcripts are restricted normalized events and must not embed a recoverable audio representation. |
| `DATA-PLAYBACK-SECRET`: playback URL/token/cookie or upstream credential | Trusted backend ingest memory only during the active connect or refresh operation. Never persisted and never sent to a worker or browser. | Stop use, close the platform session, and clear the local reference after use, refresh, stop, disable, or error. Request upstream revocation only where supported. Every diagnostic redacts both key and value. |
| `DATA-NORMALIZED-EVENT`: normalized event and room/session metadata | Restricted by default. Production Postgres persistence is disabled until Issue #16 implements these controls and a current per-source/per-field record approves purpose, publication, retention/review, and deletion triggers. There is no platform-independent default TTL. Missing or expired evidence stops new persistence and publication. | Anonymous APIs expose only the approved normalized live subset; invited history requires separate authorization. A canonical room/session deletion hides and blocks immediately, then purges active stores within 24 hours. |
| `DATA-RAW-BUSINESS`: sanitized raw business payload | Production persistence is disabled until the normalized-data gates and Issue #16 sanitization, key, encryption, audit, manifest, and deletion controls pass. If enabled, raw data may exist only in the private Bucket after credentials, playback locators, excess identity, and every audio representation are rejected or removed, then compressed and encrypted with AES-256-GCM using separate keys. It has no platform-independent TTL. | Admin-only managed export with per-access audit. Never an ordinary/public API response or browser cache. Delete all room/session objects and versions from active storage within 24 hours. Sanitization, encryption, key, audit, manifest, or storage failure prevents archival and must not spill raw data into Postgres, logs, queues, or temporary files. |
| `DATA-ACCOUNT-IDENTITY`: invite/account identity | Disabled until Issue #12. Then only the invited email, role, and minimum account/revocation state may remain while the account is active. | Subject or admin access only. Revoke access immediately. An approved account deletion purges identifying active-store fields within 24 hours and retains only the payload-free audit/tombstone record required below. |
| `DATA-AUTH-BEARER`: authentication, enrollment, and session bearer secret | Disabled until its owning Issue. A magic link is single-use and valid for at most 15 minutes; a worker enrollment token is single-use and valid for at most 24 hours; a session cookie is individually revocable and valid for at most 30 days. The database stores only a verifier hash plus expiry/use state. Plaintext exists only in the intended Resend email or initiating client flow, never in a database, log, telemetry event, or URL analytics. | Expiry, use, or revocation immediately prevents future acceptance. Plaintext retained in a previously delivered email is inert and cannot become valid again. Account/device deletion revokes related tokens and sessions immediately and purges active verifier/session rows within 24 hours. Issue #12 owns account authentication/session evidence; Issue #13 owns worker enrollment evidence. |
| `DATA-WORKER-DEVICE`: device identity and aggregate worker statistics | Disabled until Issue #13. Then limited to device public key, status, allowlisted capabilities, online/processed duration, success rate, RTF, and recent health while registered. | A contributor sees only that contributor's aggregates; an admin manages devices. Revoke immediately. Device/account deletion purges identifying active-store fields within 24 hours. |
| `DATA-AUDIT`: security, control, deletion, and raw-access audit | Append-only actor/control result, timestamps, object class, safety generation, and integrity metadata for 365 days. It contains no event body, email, secret, playback locator, audio, transcript, or digest of low-entropy/raw values. Keyed integrity digests cover canonical manifest/control records, never deleted content. | Restricted admin/auditor access. After 365 days, purge active audit rows within 24 hours unless a documented incident hold names an owner and expiry. The payload-free field contract is also defined by `CTRL-AUDIT-PAYLOAD-FREE` in the incident runbook. |
| `DATA-DELETION-TOMBSTONE`: deletion manifest/tombstone | Opaque room/session target, deletion state, safety generation, timestamps, and payload-free counts only. It must be held separately from restorable application data and be available to every restore. | Retain while any live/history store, object version, export, replica, or backup can reintroduce the target and through at least one successful restore verification after the last backup window. It contains no raw, identity, event, transcript, or audio content. |
| `DATA-MANAGED-RAW-EXPORT`: managed raw export and access capability | Disabled until Issue #16. The access capability lasts at most 15 minutes; an encrypted managed export object lasts at most 24 hours. Alpha forbids untracked local plaintext copies by default. | Per-access admin audit. Revoke/delete the managed object within 24 hours or immediately when its room/session is deleted. Revoking authorization prevents future access but does not claim erasure of plaintext already disclosed. Introducing such disclosure requires a named High residual, a bounded destination, and owner acceptance. |
| `DATA-DERIVED-COPY`: cache, index, replica, object version, or backup | Never an independent source of truth. Active copies follow the 24-hour purge SLA. Each production configuration must enumerate its actual schedules, object-version behavior, recovery window, and deletion/purge evidence. | Restore remains offline and globally disabled until current safety/denylist state and deletion records replay successfully. Unknown, unbounded, or untested provider behavior blocks production persistence. |

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

## Room/session deletion state machine

`CTRL-DELETION-STATE` is keyed by canonical `room_id` and immutable `session_id`. A
request is idempotent and cascades across normalized rows, indexes, caches, manifests,
raw objects and versions, managed exports, replicas, and every other enumerated active
store. Retrying the same target must continue the existing manifest rather than weaken
or reset its evidence.

The only externally reportable states are:

1. `hidden`: immediately denies new ingest/reconnects and blocks all public, ordinary,
   history, cache, and pending-publication visibility for the target. This state is
   entered before destructive work begins and persists through every partial failure.
2. `active-purge-complete`: every enumerated active store has been purged and verified,
   with an immutable completion timestamp. The service-level objective is 24 hours from
   request acceptance. A successful retry after that deadline still enters this state,
   but permanently records `sla_breached=true` in the incident/audit result; lateness
   must never be hidden by resetting a request time.
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

1. Authenticate and authorize an admin deletion request; resolve aliases to a canonical
   room ID and select immutable session IDs without accepting ambiguous matches.
2. Atomically enter `hidden`, block ingest and visibility, revoke relevant sessions,
   leases, export capabilities, and managed export access, and write the tombstone and a
   payload-free audit result.
3. Enumerate the target against the versioned store inventory captured by Issue #16.
   Purge normalized rows, indexes, caches, replicas, raw objects/versions, manifests,
   and managed exports using idempotent operations.
4. Verify every active store. A partial failure keeps the target hidden, records only a
   payload-free error code/count, schedules an idempotent retry, and cannot report
   active completion while any store is unchecked.
5. Enter `active-purge-complete` only after all active checks pass, preserving the
   original request time and the truthful SLA result.
6. Track every backup, object-version, and export window. Enter
   `final-retention-window-satisfied` only when all stated conditions above are proven;
   retain the tombstone through one successful post-window restore verification.

Audit counts, keyed manifest digests, and failure metadata must never contain or hash
raw, identity, transcript, event-body, secret, locator, or audio content. Backups may
remain immutable only while inaccessible to application traffic and only if every
restore replays the current tombstones before any traffic is admitted. The exact
forced-off recovery procedure is `CTRL-RESTORE-REPLAY` in
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
client-side encryption and an independently integrity-protected deletion/safety recovery
copy. Consequently normalized and raw production persistence stays **OFF** until Issue
#16 records the configured maximum window for every store and Issue #19 verifies restore
replay. A provider-declared window is a control boundary, not proof of physical erasure.

If any provider's maximum backup, recovery, object-version, or deletion window remains
unknown, or if a current tombstone cannot be made available to all restores, production
persistence remains disabled. Do not guess a value from an unselected provider option.

## Implementation ownership and acceptance evidence

| Issue | Required evidence before its capability can be enabled |
| --- | --- |
| #3 | Protocol limits and golden fixtures for bounded frame metadata, monotonic media time, and rejection without persistence. |
| #8 | Measured backend/decoder/transport memory ceilings, no persistent/crash path, prompt eviction, and teardown tests. |
| #10 | Restricted normalization/public projection plus raw sanitization that rejects credentials, locators, excess identity, and audio. |
| #12 | Invite/account fields, 15-minute single-use magic link, 30-day revocable session, role checks, and identity/token deletion. |
| #13 | 24-hour single-use enrollment token, device identity/statistics minimization, revocation, and purge. |
| #14 | One active lease's bounded frame acceptance, cancellation/timeout/disconnect clearing, and rejection of late output. |
| #15 | One-active-room/lease scheduling, standby-without-PCM promotion, and failover without an audio retry queue. |
| #16 | Postgres/Bucket access, AES-256-GCM and separate keys, audit, managed export, store inventory, idempotent purge, truthful states, provider windows, and tombstone recovery copy. |
| #4/#19 | Startup/restore forced-off deployment behavior and a recovery drill proving tombstone/safety replay before traffic. |

Issue #2 supplies no runtime acceptance evidence. A later owner must record the exact
commands, provider configuration, restore results, residual risks, and source/rights
approval in the owning Issue before enabling the corresponding production path.
