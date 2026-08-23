# Alpha incident disable, takedown, and recovery runbook

## Status, authority, and invariant

This is the documentation-only control contract required by the accepted Issue #2
specification. It describes future required behavior and paper/tabletop verification;
it does **not** assert that a
kill switch, denylist, safety journal, deletion worker, provider restore, or production
deployment exists. Later owning Issues must supply executable evidence before production
ingest or persistence is enabled.

The invariant is simple: uncertainty means **OFF**. Production ingest starts globally
disabled, and every process start, deployment, restart, backup restore, or disaster
recovery fork begins with a local forced-off latch. A backed-up `enabled` value is never
inherited. No authentication, viewer, ingest, worker, callback, or scheduled-job traffic
may reach a restored environment until the recovery gates in this record succeed.

Stable control identifiers name requirements for later Issues; they are not wire fields,
database schemas, CLI names, or claims of runtime implementation.

## Control registry and implementation ownership

| Control ID | Required behavior | Later evidence owners / integration dependencies |
| --- | --- | --- |
| `CTRL-SAFETY-DEFAULT-OFF` | Production ingest and every startup/restore are forced off; missing, stale, ambiguous, or conflicting state remains off. | Issues #4, #7, #16, and #19 |
| `CTRL-SAFETY-GENERATION` | Disable, enable, denylist-add, and denylist-remove decisions use a monotonic generation, append-only journal, and integrity-protected recovery copy outside restorable application-data backups. | Issues #4, #7, #16, #17, and #19 |
| `CTRL-ROOM-DENYLIST` | Eligibility and every reconnect use the canonical platform room ID; ambiguity or a denylist match denies operation. | Issues #7, #16, and #17 |
| `CTRL-DISABLE-CLEANUP` | Disablement stops platform activity, leases, transient audio/locators, reconnects, and publication without depending on the failing ingest path. | Issues #7, #8, #11, #14, #15, #16, #17, and #19 |
| `CTRL-RESTORE-REPLAY` | An offline restore rejects stateful/stateless pre-restore credentials, replays deletion/revocation checkpoints, and only then reconciles current safety/denylist state before admitting traffic. | Issues #4, #12, #13, #16, and #19 |
| `CTRL-IDENTITY-RESTORE-REVOCATION` | Typed pseudonymous account/device checkpoints and auth-invalidation state survive application backups; every stateful/stateless pre-restore credential is server-rejected before authentication or traffic. | Issues #4, #12, #13, #16, and #19 |
| `CTRL-REENABLE-GATE` | Only an admin may technically enable/remove, and only after current owner approval and every incident, rights, deletion, journal, recovery, and tabletop prerequisite passes. | Issues #7, #16, #17, and #19 |
| `CTRL-AUDIT-PAYLOAD-FREE` | Every safety, incident, deletion, and raw-access result is append-only and auditable without protected payload. | Issues #12, #13, #16, #17, and #19 |
| `CTRL-DELETION-FAIL-CLOSED` | A takedown hides and blocks immediately; partial purge never reports completion and remains blocked through idempotent retry. | Issues #11, #16, and #17 |
| `CTRL-WORKER-SYNTHETIC-ONLY` | Community workers receive synthetic audio unless the explicit rights and named High-residual gates for real PCM have passed. | Issues #8, #9, #14, and #15 |

`CTRL-AUDIO-RAM-ONLY`, `CTRL-BACKUP-EVIDENCE`, `CTRL-RESTORE-REPLAY`,
`CTRL-IDENTITY-RESTORE-REVOCATION`, `CTRL-AUDIT-PAYLOAD-FREE`, and
`CTRL-DELETION-FAIL-CLOSED` use the stable data classes, control definitions, and
three-state room/session deletion model in
`docs/security/data-lifecycle-and-deletion.md`.

## Roles and authorized actions

Authorization defaults to deny. Human governance and production credentials are
separate authorities.

| Actor | Permitted safety action | Prohibited safety action |
| --- | --- | --- |
| Anonymous viewer, invited viewer, contributor | None. They may use only their separately approved read/statistics surfaces. | Every ingest, denylist, kill-switch, deletion, restore, raw-export, role, key, and device-control action. |
| Operator | Select/start/stop an eligible room; add a canonical room ID to the denylist; invoke global emergency disable. | Global re-enable, denylist removal, raw export, deletion completion, role/key/device administration, or overriding a platform restriction. |
| Admin | Operator actions; role/invite/device control; deletion request; separately audited managed raw export; audited denylist removal; technical re-enable after all governance gates pass. | Bypassing repository-owner approval, accepting a residual risk, exposing raw data to ordinary APIs, or overriding platform/rights restrictions. |
| Repository owner | Approve ADRs, source/rights basis, production global enablement, and each named Critical/High residual risk as human governance. | The governance role is not an application role and grants no implicit platform, database, archive, email, key, or deployment credential access. |

An operator need not wait for an admin or repository owner to make the system safer:
global disable and denylist addition are immediate authorized actions. An admin's
technical ability to re-enable or remove never substitutes for the repository owner's
current approval of the triggering policy/risk decision.

## Durable safety state

### Monotonic generation and append-only journal

`CTRL-SAFETY-GENERATION` requires one backend-authoritative logical safety state:

- a monotonically increasing safety generation;
- the global ingest decision;
- the canonical room-ID denylist;
- an append-only sequence of disable, enable, add, and remove decisions;
- the current room/session deletion and account/device revocation checkpoints; and
- integrity metadata and references to any required owner approval.

The journal stores the payload-free fields below, not platform responses, room content,
credentials, raw events, transcripts, or audio. A safety transition is bound to its
predecessor generation. A stale, duplicated, rolled-back, missing, or conflicting
generation cannot replace a newer decision. An empty restored database is not evidence
that generation zero is current.

Issue #16 must maintain an encrypted, integrity-protected current recovery copy containing
enough of the latest safety/denylist state, journal integrity head, room/session deletion
checkpoint, typed pseudonymous account/device checkpoints, and monotonic authentication-
invalidation generation or key version to detect stale application-data backups. A
checkpoint target is a random immutable never-reused internal reference, not an email,
role, public key, bearer, canonical room ID, or unkeyed digest of a low-entropy value.
These references remain linkable pseudonymous data, so access is narrowly authorized and
audited by opaque manifest reference/count. The copy and current verification key
material are stored separately from restorable application-data backups. It is a safety
dependency, not a general raw-data backup, and contains no direct identity field, event,
transcript, audio, bearer/verifier, playback locator, or other user content.

### Safe transition rules

- **Global disable or denylist add:** an authorized operator/admin latches the local
  effect immediately. The backend allocates the next generation, appends the decision,
  and advances the recovery copy. If either durable write is unavailable or their
  integrity/freshness cannot be proven, the emergency local disable still succeeds and
  the effective posture remains globally disabled. No enable/remove may occur while the
  durable state is incomplete.
- **Global enable or denylist remove:** only an admin may request the transition, with a
  current recorded owner approval and all `CTRL-REENABLE-GATE` evidence. The new
  generation, append-only journal result, and separate recovery copy must all reconcile
  successfully before the transition can take effect. A partial write is a failed
  operation and leaves global ingest disabled; it must not be presented as success.
- **Canonical identity:** aliases and URLs resolve to one canonical Bilibili room ID
  before selection, eligibility, or denylist comparison. Resolution failure, ambiguity,
  stale state, or an unavailable configuration store is a denial, never a fallback.
- **Ongoing checks:** the effective global generation and canonical denylist are checked
  before each start and reconnect. A later denylist match or generation change invokes
  the same cleanup as an explicit emergency disable.

No safety operation may silently decrement/rebase a generation, truncate history,
reconstruct an enabled value from an application backup, or treat journal/recovery-copy
unavailability as permission to continue.

## Immediate disable and denylist procedure

The disable path must remain usable when the platform adapter or normal ingest state
machine is failing. On any security, rights/platform, credential, raw-access, worker,
deletion, control-integrity, or unknown-severity incident:

1. An operator/admin invokes global disable, or adds the resolved canonical room ID to
   the denylist. If room resolution is ambiguous, invoke global disable rather than
   guessing an ID.
2. `CTRL-SAFETY-DEFAULT-OFF` takes local effect immediately. Reject every new room
   start, reconnect, refresh, and worker assignment, including requests already queued
   but not started.
3. Apply the next safety generation and journal/recovery-copy rules above. A write
   failure cannot undo the local latch and raises a security alert.
4. Terminate the active Bilibili platform session and stop reading playback bytes and
   business events. There is no alternate endpoint, credentialed fallback, or scraper.
5. Revoke the active worker lease, reject late worker output, and send only the bounded
   versioned cancellation/control message allowed by the ASR protocol. Never send a
   shell command, execution field, code, container, or download URL.
6. Stop using and clear all local playback locators/credentials. Request upstream
   revocation only if the platform supports it. Clear all conforming backend/worker
   audio buffers under `CTRL-AUDIO-RAM-ONLY`; revocation limits future disclosure and
   does not claim erasure on a malicious host.
7. Hide pending publication and the affected room/session. If this is a takedown or
   deletion event, enter `hidden` and follow `CTRL-DELETION-FAIL-CLOSED`.
8. Append a `CTRL-AUDIT-PAYLOAD-FREE` result for each attempted control and notify the
   incident owner through an approved non-payload channel.

The effective result is safe only when starts/reconnects are denied, the platform
session is closed, the lease no longer authorizes output, transient backend state is
cleared, and pending publication is hidden. Audit or recovery-copy failure is itself an
incident; the system remains off rather than waiting on the failing ingest path.

## Takedown and partial deletion procedure

An admin deletion request uses canonical `room_id` and immutable `session_id`; an
operator may first stop/denylist the room but may not declare deletion complete.

1. Immediately set `hidden`, block ingest/reconnect and all visibility, revoke relevant
   leases and export capabilities, and persist the payload-free tombstone if the safety
   store is available. If persistence is unavailable, global disable remains active and
   the request is escalated; no content becomes visible again.
2. Enumerate and idempotently purge every active store named by Issue #16: normalized
   rows, indexes, caches, replicas, manifests, raw objects/versions, and managed exports.
3. A failed or unchecked store keeps the target `hidden`. Record only a stable error
   code and payload-free count, then retry idempotently. Never label the request
   `active-purge-complete` while any active store remains unchecked.
4. When all active stores verify empty, record the immutable completion timestamp. If
   more than 24 hours elapsed from the original request, transition truthfully to
   `active-purge-complete` with `sla_breached=true` and retain the incident result.
5. Do not report `final-retention-window-satisfied` until every managed export and every
   enumerated provider backup/object-version window has expired or supplied verifiable
   purge evidence. Retain the tombstone through at least one successful restore
   verification after the last window.

The states prove the documented control boundary, not physical-media erasure. Unknown
provider windows or untracked plaintext prevent final satisfaction and, under
`CTRL-BACKUP-EVIDENCE`, block production persistence.

## Account/device deletion or revocation and restored credential procedure

`CTRL-IDENTITY-RESTORE-REVOCATION` applies when an admin deletes or revokes an account or
device:

1. Record a typed operation (`deleted` or `revoked`) and scope. Account deletion revokes
   and cascades through roles, invites, devices, aggregate statistics, tokens, verifiers,
   and sessions. Device deletion affects only that device, its enrollment/session state,
   and device-scoped statistics unless the account is also targeted.
2. Stop new authentication, token/session issuance, enrollment, and worker assignment for
   the target immediately. A permanent deletion may never be downgraded to a reversible
   revocation, and a lower generation may never replace either operation.
3. Commit the typed pseudonymous checkpoint to the separate recovery copy and verify its
   read-back and integrity **before** reporting deletion/revocation complete. A failure
   disables the affected authentication path and every restore traffic class.
4. Purge identifying active-store fields and verifier/session rows within 24 hours. The
   checkpoint contains only the typed random immutable never-reused internal target
   reference, operation, target class, monotonic generation, timestamp, and payload-free
   result; never email, public key, role, IP address, verifier hash, bearer, or user
   content.
5. Retain the checkpoint while any enumerated backup can reintroduce the identity/device
   and through one successful restore verification after the last such window, then
   delete it under an audited rule.

Every restore purges/revokes **all** restored magic-link, worker-enrollment, session-
verifier, and session rows before accepting any authentication, callback, worker, or
viewer traffic, even when backed-up expiry/use state appears current. It also advances or
reconciles the recovery-protected monotonic auth-invalidation generation or signing/
verifier key version; the current version/root and verification secret material cannot
come from the application-data backup, and pre-restore key versions cannot remain in the
active verification set. Thus every stateless and stateful pre-restore credential remains
server-rejected even if plaintext persists in a mailbox/client. The
restore then replays account/device checkpoints, removes restored roles/invites/devices/
statistics and issuance authority in scope, and proves deleted targets cannot receive
new credentials. Fresh post-restore authentication and enrollment are required; no
restored bearer or admin session is grandfathered.

## Startup, restore, and disaster recovery

`CTRL-RESTORE-REPLAY` is a pre-traffic gate, not a background cleanup:

1. Isolate the new/restored environment from viewer, ingest, worker, scheduled-job, and
   callback traffic. Start every process with the local forced-off latch regardless of
   any restored setting.
2. Verify the integrity and freshness of the separate safety/deletion/revocation
   recovery copy. Missing, stale, rolled-back, conflicting, or unverifiable state ends
   the procedure with the environment isolated and off and every authentication and
   traffic class denied.
3. Purge or revoke every restored magic-link, worker-enrollment, session-verifier, and
   session row, irrespective of its backed-up expiry/use/revocation state. Advance or
   reconcile the recovery-protected monotonic auth-invalidation generation or non-
   restorable signing/verifier key version and ensure restored old key material cannot
   become current or remain in the active verification set. Reject sampled pre-restore
   stateful/stateless links, cookies, and tokens in a server-side negative verification
   before proceeding.
4. Load the current checkpoints. Replay room/session tombstones idempotently against
   restored Postgres data, indexes/caches, raw objects/versions, and managed exports;
   replay typed account/device deletion/revocation checkpoints against account, role,
   invite, device, statistics, token, verifier, and session rows. Verify that no deleted
   target is active, visible, authenticable, or able to receive newly issued authority.
5. Reconcile the application journal with the latest safety generation and canonical
   denylist recovery copy. A stale restored generation cannot overwrite the newer copy;
   any gap or integrity conflict leaves the environment off and creates a payload-free
   alert.
6. Verify provider-window inventory, audit integrity, source/platform/rights currency,
   incident remediation, applicable deletion results, and current owner approvals. Run
   the relevant tabletop using the restored environment while it remains isolated.
7. Only after all checks pass may a fresh, non-restored, separately audited admin
   recovery authentication request `CTRL-REENABLE-GATE`. Its credential and trust root
   cannot originate in the restored application backup; repository-owner governance
   grants no production credential. The new generation/journal/recovery-copy transition
   must succeed before authentication, viewer, worker, callback, or ingest traffic is
   admitted. Otherwise keep the environment offline/off and investigate.

Restoration tooling must not automatically swap traffic or credentials into the fork.
A provider's ability to restore old data is exactly why current deletion/revocation
checkpoints and authentication-invalidation state live outside the application-data
backup boundary, and stateful/stateless pre-restore credentials are rejected before any
replay or traffic.

## Re-enable gate

An incident disable has no automatic timeout. `CTRL-REENABLE-GATE` requires all of the
following:

- the root cause is identified and remediated, with credential/key rotation where
  relevant;
- the current acquisition channel, platform terms, rights evidence, purpose, public
  outputs, and any community-worker disclosure remain permitted;
- all affected deletion/revocation checkpoints have replayed successfully, every restored
  stateful/stateless credential is server-rejected, restored identity/device authority
  cannot issue a new credential, and no partial purge or unknown provider window is being
  misreported;
- the safety journal, recovery copy, generation, denylist, and audit are complete,
  current, and mutually consistent;
- the relevant tabletop has fresh successful evidence;
- every applicable Critical/High residual risk has an individual owner decision with
  date, scope, compensating controls, review date, and disable owner; and
- the repository owner has recorded approval for this production enable/remove decision,
  after which a fresh, non-restored, separately audited admin recovery authentication
  performs the technical transition.

Any failed or missing item leaves the global state disabled. Neither the repository
owner nor admin may waive a platform or rights-holder restriction.

## Payload-free audit contract

`CTRL-AUDIT-PAYLOAD-FREE` records only the minimum control evidence. The conceptual
fields below are stable content requirements, not a schema:

| Field | Allowed content |
| --- | --- |
| Event identity/time | Random audit event reference; occurrence and recorded timestamps. |
| Actor/control | Restricted pseudonymous actor reference, actor role, control ID, requested action, authorization result, and result code. |
| Target | Object class plus opaque room/session/export reference; identity deletion/revocation records only an opaque checkpoint-manifest reference and count, never its account/device target ID, event body, email, public key, bearer, or user-facing content. |
| Safety transition | Prior and resulting safety generation, previous/new effective posture, and stable reason code. |
| Incident/deletion | Opaque incident/manifest reference, deletion state, payload-free store counts, retry count, completion timestamp, and immutable `sla_breached` result where applicable. |
| Integrity | Key identifier/version, previous journal-link reference, and a keyed integrity digest of the canonical control or manifest record. |
| Failure | Stable component/control error code and success/failure/denied result, never an upstream response body or protected value. |
| Governance | Opaque owner-approval/risk-decision reference and review expiry where required. |

Never record an account/device checkpoint target, event/raw body, email, bearer secret,
cookie, playback locator, platform credential, audio representation, transcript, or a
digest of a low-entropy/raw value.
The keyed integrity digest covers the canonical metadata record, never deleted content.
Diagnostics must redact both secret keys and values. Audit access is restricted to an
admin/auditor, is append-only, and follows the 365-day lifecycle and documented
owner/expiry incident-hold exception in the lifecycle record.

## Required tabletop scenarios

These are paper/design acceptance tests for Issue #2. Later Issues must repeat them
against real controls and record exact commands, generation IDs, timestamps, injected
failures, and payload-free results.

### Tabletop 1: global disable during an active room

**Setup:** In an isolated test design, production-like ingest is enabled, one canonical
room is active, a playback locator is in backend memory, one worker lease is active, and
pending normalized publication exists.

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | An operator invokes global disable. | The local latch changes to off immediately; new starts, refreshes, reconnects, and assignments are denied without waiting for the ingest adapter. |
| 2 | Advance the safety generation and write the journal/recovery copy. | The new generation supersedes the old one. If either write is injected to fail, the system remains off, emits a payload-free alert, and no enable/remove succeeds. |
| 3 | Execute `CTRL-DISABLE-CLEANUP`. | The platform session terminates; the lease is revoked; late output is rejected; pending publication is hidden; the locator and all conforming audio buffers are cleared. |
| 4 | Attempt a platform reconnect and a worker frame from the revoked lease. | Both are denied under the current generation. No credentialed/alternate platform fallback or audio retry queue is created. |
| 5 | Inspect audit content. | The actor/control result, timestamps, object class, generation, result, and integrity metadata exist; no content, secret, locator, transcript, or audio appears. |

**Pass result:** Future disclosure and publication are stopped, recovery-copy failure
cannot fail open, and the record does not claim that an untrusted worker erased RAM.

### Tabletop 2: room/session takedown with one failed object deletion

**Setup:** The target has normalized rows, cache/index entries, one encrypted raw object,
a managed export, and a tombstone-capable recovery copy. Inject failure for deletion of
the raw object and advance simulated time beyond 24 hours before its successful retry.

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | An admin requests deletion for canonical room/session IDs. | The target enters `hidden` immediately; ingest/reconnect and every public/history/cache path are blocked before purge begins. |
| 2 | Purge all enumerated active stores with the raw-object failure injected. | Successful stores stay purged; the failed store records only an error code/count. The target stays `hidden`, retry is idempotent, and active completion is forbidden. |
| 3 | Retry the same manifest after the 24-hour deadline and verify all active stores. | The raw object is removed; the state becomes `active-purge-complete` with the original request time, a completion timestamp, and immutable `sla_breached=true`. |
| 4 | Evaluate exports and backups while their declared windows remain open. | Managed access is revoked and the target stays replay-protected, but `final-retention-window-satisfied` is withheld and retained copies are reported truthfully. |
| 5 | Expire/verify every enumerated window and run a post-window restore check. | Only then may the final state be recorded; the tombstone survives through the successful restore verification. No physical-erasure claim is made. |

**Pass result:** Visibility/ingest blocking is immediate, retries cannot resurrect or
duplicate data, partial/late deletion is truthful, and no unchecked store is called
complete.

### Tabletop 3: restore stale enablement, deleted data, and revoked identity

**Setup:** Restore an application-data backup whose generation is older, whose global
setting says enabled, and whose rows include a room/session plus an account/device deleted
after that backup. It also contains apparently unexpired magic-link, enrollment-token,
session-verifier/session rows, a stateless token signed by the old key version, and the
deleted subject's roles/invites/device statistics. The separate recovery copy contains
the newer forced-off generation, denylist, room/session tombstone, typed pseudonymous
account/device checkpoints, and newer auth-invalidation generation/key version.

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | Boot the restore in isolation. | Startup ignores backed-up enablement and latches off before any viewer, ingest, worker, callback, or scheduled-job traffic. |
| 2 | Verify and load the separate recovery copy. | The newer tombstone, identity/device checkpoints, safety generation, and auth-invalidation generation/key version are recognized; missing/tampered/conflicting-copy variants stop here and remain off. |
| 3 | Purge/revoke restored verifier/session rows, reconcile the protected auth generation/key version, and probe old links/cookies/stateless tokens. | Every stateful/stateless pre-restore credential is server-rejected regardless of backed-up expiry/use state; old verification key material cannot become current; fresh authentication and enrollment are required. |
| 4 | Replay room/session and typed account/device checkpoints, then verify deletion and issuance denial. | Content is purged/hidden; scoped account roles/invites/devices/statistics/tokens/sessions are purged or remain revoked; deleted authority can neither authenticate nor receive a new credential before safety reconciliation. |
| 5 | Reconcile safety generation and denylist. | The stale backed-up generation cannot overwrite the current copy. Gaps or mismatches remain off and produce a payload-free alert. |
| 6 | Evaluate `CTRL-REENABLE-GATE` using a fresh, non-restored, separately audited admin recovery authentication. | Restored admin sessions remain invalid. Traffic stays blocked until remediation, current rights/policy, audit, tabletop, provider-window, and owner approvals pass and the fresh recovery admin records a durable generation. |

**Pass result:** Stateful/stateless pre-restore credentials remain server-rejected and all
deletion/revocation checkpoints replay before safety reconciliation; every step precedes
traffic, and neither an old enabled value, restored admin session, nor deleted identity/
device authority becomes current.

### Tabletop 4: authenticated worker capable of retaining PCM

**Setup:** An invited worker authenticates successfully. Treat its host as malicious and
capable of copying any PCM it receives; authentication, signatures, allowlisting, and a
lease prove no more than identity/protocol state.

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | Attempt real-audio assignment without the explicit third-party rights record or owner acceptance of `RISK-WORKER-AUDIO-RETENTION`. | Assignment is denied; synthetic audio remains the default even though the worker authenticated. |
| 2 | Paper-test the separately gated real-PCM path. | Only an identified invited worker with the required rights and individual High-risk acceptance can receive one active lease; the budget is at most 30 seconds/960,000 canonical PCM bytes, standby workers receive no PCM, and no retry queue or platform/DB/archive/email/encryption/playback secret is sent. |
| 3 | Report suspected host retention/fabricated output. | An operator globally disables; the lease is revoked and late output rejected. An admin may revoke device identity. Backend locators/audio are cleared and pending publication hidden. |
| 4 | Assess deletion and recovery claims. | Revocation prevents future disclosure only. Audit states that malicious-host retention is unknown; it never claims remote erasure. The named High residual is reopened for owner review. |
| 5 | Attempt re-enable. | It remains denied until incident remediation, rights/processor review, current risk acceptance, disable-owner approval chain, and all ordinary re-enable gates pass. |

**Pass result:** A valid identity is never treated as trusted execution or proof of RAM
erasure, and real audio remains off without every explicit gate.

## Evidence handoff

Issue #2 supplies the stable decisions and paper expectations only. Issues #4, #7, #8,
#9, #11, #12, #13, #14, #15, #16, #17, and #19 must reference the applicable control IDs in
their own accepted artifacts and record executable verification. Production enablement
also requires the repository owner's final ADR approval and an individual decision for
every accepted Critical/High residual risk; a blanket approval is invalid.
