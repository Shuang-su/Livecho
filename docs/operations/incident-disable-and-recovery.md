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
| `CTRL-SAFETY-GENERATION` | One monotonic generation orders two orthogonal safety dimensions—the global enabled bit and canonical-room denylist—without making a transition in one implicitly mutate the other; every transition uses the append-only journal and integrity-protected recovery copy outside restorable application-data backups. | Issues #4, #7, #16, #17, and #19 |
| `CTRL-ROOM-DENYLIST` | Eligibility and every reconnect use the canonical platform room ID; a verified add/remove changes only that room entry, while ambiguity, stale/binding conflict, or transition write/read-back failure escalates to global disable. | Issues #7, #16, and #17 |
| `CTRL-DISABLE-CLEANUP` | Global disable cleans up every active/queued ingest scope; a successful canonical-room denylist add cleans up only that room and does not disturb unrelated rooms, without depending on the failing ingest path. | Issues #7, #8, #11, #14, #15, #16, #17, and #19 |
| `CTRL-RESTORE-REPLAY` | An offline restore rejects stateful/stateless pre-restore credentials, reconciles unresolved deletion intake, replays every pending `hidden` tombstone and deletion/revocation checkpoint, and only then reconciles current orthogonal global/denylist state before admitting traffic. | Issues #4, #12, #13, #16, and #19 |
| `CTRL-IDENTITY-RESTORE-REVOCATION` | Typed pseudonymous account/device checkpoints and auth-invalidation state survive application backups; every stateful/stateless pre-restore credential is server-rejected before authentication or traffic. | Issues #4, #12, #13, #16, and #19 |
| `CTRL-REENABLE-GATE` | Only an admin may technically enable globally or remove one denylist entry, as separate transitions, and only after current owner approval and every incident, rights, deletion, journal, recovery, and tabletop prerequisite passes. | Issues #7, #16, #17, and #19 |
| `CTRL-AUDIT-PAYLOAD-FREE` | Every safety, incident, deletion, and raw-access result is append-only and auditable without protected payload. | Issues #12, #13, #16, #17, and #19 |
| `CTRL-DELETION-FAIL-CLOSED` | A verified takedown selector is provisionally contained immediately, but acceptance, reportable `hidden`, and purge wait for commit/read-back of its durable `hidden` tombstone; invalid/ambiguous or persistence-failed scope never starts guessed destructive purge or reports success. | Issues #11, #16, and #17 |
| `CTRL-WORKER-SYNTHETIC-ONLY` | Community workers receive synthetic audio unless the explicit rights and named High-residual gates for real PCM have passed. | Issues #8, #9, #14, and #15 |

`CTRL-AUDIO-RAM-ONLY`, `CTRL-BACKUP-EVIDENCE`, `CTRL-RESTORE-REPLAY`,
`CTRL-IDENTITY-RESTORE-REVOCATION`, `CTRL-AUDIT-PAYLOAD-FREE`, and
`CTRL-DELETION-FAIL-CLOSED` use the stable data classes, control definitions, and
three-state typed room-or-session deletion model in
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
- the global ingest decision and canonical room-ID denylist as orthogonal dimensions,
  neither inferred from nor implicitly changed by the other;
- an append-only sequence of disable, enable, add, and remove decisions;
- durable unresolved room/session deletion-intake blockers plus the current typed
  room-or-session deletion manifests, including room-over-session dominance, and account/
  device revocation checkpoints; and
- integrity metadata and references to any required owner approval.

The journal stores the payload-free fields below, not platform responses, room content,
credentials, raw events, transcripts, or audio. A safety transition is bound to its
predecessor generation and names exactly one action: global disable, global enable,
denylist add for one canonical room, or denylist remove for one canonical room. The one
generation orders both dimensions; it does not couple their effects. A stale, duplicated,
rolled-back, missing, or conflicting generation cannot replace a newer decision. An empty
restored database is not evidence that generation zero is current.

The backend also has one high-priority, ingest-independent pending-tightening fence. A
global disable atomically sets its sticky local global-off latch, and a denylist add sets
its sticky target-room block, without waiting behind a normal transition or its durable
I/O. Durable transitions still serialize against one predecessor and at most one
successor may commit. Every in-flight or later enable/remove must recheck the fence and
transition epoch immediately before durable commit **and** before any local relaxation;
the final fence check and local effect/latch change are one atomic compare-and-set under
that same logical transition authority. If relaxation linearizes first, a following
tightening immediately latches/blocks and cleans; if tightening linearizes first, the
relaxation fails without a reopen window or clearing the latch/block. Unfinished cleanup
or ambiguous ordering also resolves globally off. A crash before tightening durability
restarts default-off rather than honoring a backed-up or late-arriving relaxation.

Alpha has exactly one active serving authority process, which owns every active/queued
room and therefore applies this fence without a cross-process durability dependency. A
future multi-process deployment may not enable production until the same fence is
synchronously visible to every active owner through an ingest-independent path. Failure
to enumerate an owner or obtain its fence acknowledgement immediately isolates/terminates
that owner at the deployment or egress boundary, keeps global off, and blocks relaxation.

Issue #16 must maintain an encrypted, integrity-protected current recovery copy containing
enough of the latest safety/denylist state, journal integrity head, durable unresolved
room/session deletion intake, typed deletion manifests and dominance, typed pseudonymous
account/device checkpoints, and monotonic authentication-
invalidation generation or key version to detect stale application-data backups. A
checkpoint target is a random immutable never-reused internal reference, not an email,
role, public key, bearer, canonical room ID, or unkeyed digest of a low-entropy value.
These references remain linkable pseudonymous data, so access is narrowly authorized and
audited by opaque manifest reference/count. The copy and current verification key
material are stored separately from restorable application-data backups. It is a safety
dependency, not a general raw-data backup, and contains no direct identity field, event,
transcript, audio, bearer/verifier, playback locator, or other user content.

### Safe transition rules

- **Global disable:** an authorized operator/admin latches global off immediately and
  closes local admission/publication gates and issues termination, revocation, clearing,
  and hiding actions for every active or queued room before the first journal/recovery-
  copy await. Cleanup completion may proceed concurrently with durable transition I/O; a
  slow, hung, failed, or ambiguous write/read-back never delays, cancels, or reorders
  those local actions. The backend allocates the next generation, appends the global-
  disable decision without changing denylist membership, advances the recovery copy, and
  verifies read-back. If any durable write/read-back or integrity/freshness check fails,
  the local global-off latch remains in force while cleanup continues/retries
  independently. Any cleanup failure alerts and blocks every relaxation; the design does
  not claim erasure on an untrusted host.
- **Denylist add:** after exact canonical-room binding, an authorized operator/admin
  provisionally blocks and cleans up only that room. The backend allocates the next shared
  generation, appends `add` for that canonical room without changing the global enabled
  bit or any other room entry, advances the recovery copy, and verifies read-back. Once
  verified, the room remains denied and unrelated rooms retain their prior state and
  eligibility; nothing starts automatically. Ambiguous or changed binding, stale control
  state, or failed/ambiguous journal or recovery-copy write/read-back escalates to global
  disable rather than guessing a room-scoped success.
- **Global enable:** only an admin may request this transition, with current recorded
  owner approval and all `CTRL-REENABLE-GATE` evidence. Its new generation changes only
  the global enabled bit and preserves the complete denylist; every denied room remains
  denied. Journal/recovery-copy write and read-back must reconcile before enablement takes
  effect, and the pending-tightening fence/epoch must be clear at pre-commit and at the
  atomic final check-and-effect. A concurrent/newer tightening, unfinished cleanup, or
  partial/ambiguous result is failure and leaves global ingest disabled.
- **Denylist remove:** only an admin may request removal of one exactly bound canonical
  room, with current owner approval and all applicable `CTRL-REENABLE-GATE` evidence. Its
  new generation removes only that entry and preserves the global enabled bit and all
  other entries. Removal neither globally enables ingest nor starts the room. It must
  also pass the pre-commit check and atomic final fence/epoch check-and-effect. Binding,
  freshness, concurrent/newer tightening, unfinished cleanup, write/read-back, or
  integrity uncertainty escalates to global disable.
- **Canonical identity:** aliases and URLs resolve to one canonical Bilibili room ID
  before selection, eligibility, or denylist comparison. Resolution failure, ambiguity,
  stale state, or an unavailable configuration store is a denial, never a fallback.
- **Ongoing checks:** the effective global generation, global enabled bit, and canonical
  denylist are checked before each start and reconnect. A generation change requires
  re-evaluation; it is not itself a cleanup instruction. A resulting global-off state
  invokes global cleanup, a resulting denylist match invokes cleanup only for that room,
  and an unrelated verified change preserves unaffected operation subject to ordinary
  eligibility checks.

No safety operation may silently decrement/rebase a generation, truncate history,
reconstruct an enabled value from an application backup, or treat journal/recovery-copy
unavailability as permission to continue. No implementation may derive the global bit
from an empty/non-empty denylist, clear the denylist on global enable, or treat removal of
one room as global enablement.

## Immediate disable and denylist procedure

The safety path must remain usable when the platform adapter or normal ingest state
machine is failing. On any security, rights/platform, credential, raw-access, worker,
deletion, control-integrity, or unknown-severity incident:

1. An operator/admin explicitly selects global disable or denylist add for one resolved
   canonical room. If room resolution/binding is ambiguous, conflicting, or stale, apply
   global disable rather than guessing an ID.
2. Apply the provisional local effect immediately. Global disable rejects every new room
   start, reconnect, refresh, and worker assignment, including queued requests, **and
   closes its local admission, publication, lease, and late-output authority gates and
   issues cleanup for every active or queued room before awaiting any journal or recovery-
   copy I/O**. The single Alpha serving authority owns all such resources; its cleanup
   executor is independent of the failing ingest path and durable-I/O executor. Steps 4–7
   are the actions issued here; they progress before or concurrently with step 3 rather
   than being gated by their numbering. An exactly bound
   canonical-room denylist add rejects only the
   target room's starts, reconnects, refreshes, and assignments; it also begins target-
   room cleanup immediately, while unrelated rooms retain their prior state and are not
   started automatically.
3. With the applicable cleanup already in progress, apply the corresponding next-
   generation journal/recovery-copy transition and verify read-back. Slow or hung durable
   I/O cannot postpone global cleanup. A global-disable write failure cannot undo its
   local latch, stop cleanup, or reactivate a resource. A room-add write/read-back,
   integrity, freshness, or binding failure escalates the local posture to global off,
   immediately expands cleanup to every active or queued room without another durability
   await, and raises a payload-free security alert; it is never reported as a successful
   room-only transition.
4. Complete the already-started cleanup at the effective scope. Global disable, including
   escalation from a failed room-add transition, covers every active or queued room. A successfully
   verified denylist add finishes cleanup only for the canonical target room and proves
   non-target room state was not changed. Terminate each in-scope Bilibili platform
   session and stop its playback bytes and business events. There is no alternate
   endpoint, credentialed fallback, or scraper.
5. Revoke each in-scope worker lease, reject late output, and send only the bounded
   versioned cancellation/control message allowed by the ASR protocol. Never send a
   shell command, execution field, code, container, or download URL.
6. Stop using and clear in-scope local playback locators/credentials. Request upstream
   revocation only if the platform supports it. Clear all in-scope conforming backend/
   worker audio buffers under `CTRL-AUDIO-RAM-ONLY`; revocation limits future disclosure
   and does not claim erasure on a malicious host.
7. Hide in-scope pending publication. If this is a takedown or deletion event, apply
   selector-scoped provisional containment only after exact target resolution and use the
   durable-admission barrier below before reporting `hidden`. When the room is known but
   session scope conflicts, deny the room; when no scope is safely identifiable, remain
   globally off and escalate. Never guess destructive scope.
8. Append a `CTRL-AUDIT-PAYLOAD-FREE` result for each attempted control and notify the
   incident owner through an approved non-payload channel.

The effective result is safe only when every in-scope start/reconnect is denied, platform
session and lease authority are closed, transient backend state is cleared, and pending
publication is hidden. A successful add of room `R` leaves the global enabled bit and
every non-`R` denylist/room state unchanged; a generation change only causes those rooms
to re-evaluate current state. Audit, binding, or recovery-copy failure is itself an
incident and escalates to global off rather than waiting on the failing ingest path.

## Takedown and partial deletion procedure

An admin deletion request supplies exactly one typed selector:
`room(canonical_room_id)` deletes room-level metadata and every current, historical,
pending, late-discovered, or restored session for that room, while
`session(immutable_session_id)` deletes only the uniquely resolved session and its
derivatives. The caller does not supply an authoritative parent room for session scope;
the backend resolves it from its authoritative index. The request must never require
both. None, both, an ambiguous room alias, a conflicting caller hint/store mapping, or a
missing/non-unique session resolution is denied rather than guessed. Block the known room
when safely identified, otherwise remain globally off, escalate, and begin no destructive
purge. An operator may first stop/denylist the room but may not declare deletion complete.

1. Immediately apply provisional containment for the verified selector while durable
   admission is pending. A room selector blocks the room's new start/reconnect/write/
   publication, all session visibility, leases, audio/locators, exports, and persistence.
   A session selector blocks only that session's visibility and descendants and stops its
   ingest, lease, audio, locator, and export paths when active; sibling sessions and shared
   room-level state remain available. This immediate effect is not a fourth deletion state
   and is not yet an accepted or reportable `hidden` result.
2. Keep the initiating takedown/incident intake open with the exact selector. Before its
   first durability attempt, assign one immutable authenticated initiating-request time.
   Atomically write/read back that time with selector and idempotency identity in the
   independent recovery boundary so all three survive until admission. It is only an
   unresolved blocker, not a deletion state, tombstone, or purge authorization. If intake
   durability itself fails, return no success and require the initiating source to retain
   and retry the same selector, identity, and original time while global off remains in
   force. Then commit the existing typed, payload-free
   `hidden` tombstone to that boundary and verify read-back **before** accepting or
   acknowledging the request, reporting `hidden`, or starting destructive purge. A
   volatile block, audit event, intake record, or empty application store is not a
   substitute. If tombstone commit/read-back fails, times out, or has an ambiguous result,
   return no success, start no purge, keep global off, and leave the durable intake
   unresolved for idempotent retry. The tombstone must reuse the intake's original time;
   a missing/mismatched time fails admission. If a commit succeeded but its response was
   lost, retry reuses the same tombstone, original request time, and manifest identity.
3. Enumerate and idempotently purge every active store named by Issue #16: normalized
   rows, indexes, caches, replicas, manifests, raw objects/versions, managed exports, and
   derived/shared projections. Room scope re-enumerates every child session/path on each
   retry/replay; session scope includes only the resolved session and recomputes shared
   projections without deleting or hiding siblings/shared room state.
4. A room tombstone dominates its child-session tombstones. A later session request cannot
   narrow/overwrite the room block; an earlier session manifest may be linked into the
   room manifest without resetting evidence or reviving data. Retries keep selector kind,
   opaque target, original request time, and manifest identity.
5. A failed, ambiguous, or unchecked store/child keeps the safe block. Record only a stable
   error code/count, then retry idempotently. Room scope cannot complete until every child
   is enumerated/empty; session scope cannot complete until its descendants are empty and
   siblings/shared room state are proven preserved. Never guess-delete an uncertain owner.
6. When the selector-specific proof passes, record the immutable completion timestamp. If
   more than 24 hours elapsed from the original request, transition truthfully to
   `active-purge-complete` with `sla_breached=true` and retain the incident result.
7. Do not report `final-retention-window-satisfied` until every managed export and every
   enumerated provider backup/object-version window has expired or supplied verifiable
   purge evidence. Retain the tombstone through at least one successful restore
   verification after the last window.

The states prove the documented control boundary, not physical-media erasure. Unknown
provider windows or untracked plaintext prevent final satisfaction and, under
`CTRL-BACKUP-EVIDENCE`, block production persistence.

A crash after durable intake but before verified tombstone admission produces no success
acknowledgement; the intake retains selector, idempotency identity, and immutable original
time, startup remains forced off, and the same triple is retried before re-enable. A crash
before intake durability also produces no acknowledgement and requires the initiating
source to retain/retry that same triple. A crash after tombstone
commit but before response is recovered by the idempotent retry and existing tombstone.
Every restart/restore reconciles unresolved intake and replays a pending `hidden`
tombstone before safety reconciliation. Recovery of the application store or an empty
application tombstone view never clears an unresolved intake or proves that no target
exists.

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
   recovery copy, including the independently recorded global enabled bit, complete
   canonical-room denylist, and every pending `hidden` tombstone. Missing, stale, rolled-
   back, conflicting, or unverifiable state—or an unresolved deletion intake without a
   verified tombstone—ends the procedure with the environment isolated and off and every
   authentication and traffic class denied. An empty restored application store is not
   proof that no pending target or safety decision exists.
3. Purge or revoke every restored magic-link, worker-enrollment, session-verifier, and
   session row, irrespective of its backed-up expiry/use/revocation state. Advance or
   reconcile the recovery-protected monotonic auth-invalidation generation or non-
   restorable signing/verifier key version and ensure restored old key material cannot
   become current or remain in the active verification set. Reject sampled pre-restore
   stateful/stateless links, cookies, and tokens in a server-side negative verification
   before proceeding.
4. Load the current checkpoints. Replay every pending `hidden` tombstone before any
   completion claim: typed room tombstones cover every restored session for their
   canonical room and typed session tombstones cover only their uniquely resolved session,
   across Postgres data, indexes/caches, raw objects/versions, managed exports, and shared
   projections. Room tombstones retain dominance over child-session manifests; missing/
   conflicting parent mapping or tombstone admission uncertainty leaves the environment
   isolated/off and starts no guessed purge;
   replay typed account/device deletion/revocation checkpoints against account, role,
   invite, device, statistics, token, verifier, and session rows. Verify that no deleted
   target is active, visible, authenticable, or able to receive newly issued authority.
5. Reconcile the application journal with the latest shared safety generation, global
   enabled bit, and complete canonical denylist recovery copy. Preserve the two dimensions
   independently: global enable never clears a room entry and removal of one room never
   implies global enable. A generation change triggers re-evaluation only; its resulting
   global/room decisions determine cleanup. A stale restored generation cannot overwrite
   the newer copy; any gap, binding mismatch, or integrity conflict leaves the environment
   globally off and creates a payload-free alert.
6. Verify provider-window inventory, audit integrity, source/platform/rights currency,
   incident remediation, applicable deletion results, and current owner approvals. Every
   failed, timed-out, response-lost, or otherwise ambiguous deletion intake must reconcile
   to its verified durable tombstone and replay result; neither an audit event nor an empty
   application store closes it. Run the relevant tabletop using the restored environment
   while it remains isolated.
7. Only after all checks pass may a fresh, non-restored, separately audited admin
   recovery authentication request a global-enable or one-room denylist-removal transition
   under `CTRL-REENABLE-GATE`. Its credential and trust root cannot originate in the
   restored application backup; repository-owner governance grants no production
   credential. The requested action's generation/journal/recovery-copy write and read-back
   must succeed before its effect is recognized, and its pending-tightening fence/epoch
   must still match in the atomic final check-and-effect. Global enable preserves every
   denylist entry, and removing one entry neither enables globally nor starts that room.
   Otherwise keep the environment offline/off and investigate. No authentication, viewer, worker,
   callback, or ingest traffic is admitted without the separately verified global-enable
   result and every other pre-traffic gate.

Restoration tooling must not automatically swap traffic or credentials into the fork.
A provider's ability to restore old data is exactly why current deletion/revocation
checkpoints and authentication-invalidation state live outside the application-data
backup boundary, and stateful/stateless pre-restore credentials are rejected before any
replay or traffic.

## Re-enable gate

An incident disable has no automatic timeout. Global enable and one-room denylist removal
are separate relaxation actions under one generation: neither implies the other, and each
requires all of the following under `CTRL-REENABLE-GATE`:

- the root cause is identified and remediated, with credential/key rotation where
  relevant;
- the current acquisition channel, platform terms, rights evidence, purpose, public
  outputs, and any community-worker disclosure remain permitted;
- all affected deletion/revocation checkpoints, including pending `hidden` tombstones,
  have replayed successfully; every failed, timed-out, response-lost, or ambiguous deletion
  intake has reconciled to a committed/read-back tombstone; every restored stateful/
  stateless credential is server-rejected; restored identity/device authority cannot issue
  a new credential; and no partial purge or unknown provider window is being misreported;
- the safety journal, recovery copy, shared generation, independently evaluated global
  enabled bit, complete canonical-room denylist, and audit are current and mutually
  consistent; neither a recovered/empty application store nor a generation change alone
  proves that a relaxation is safe;
- no pending/newer local tightening fence, cleanup failure/retry, ambiguous transition,
  or late response from an in-flight relaxation exists; the relaxation rechecks its
  captured fence/epoch immediately before commit, then atomically performs the final
  fence/epoch check and local effect under the same logical transition authority;
- the relevant tabletop has fresh successful evidence;
- every applicable Critical/High residual risk has an individual owner decision with
  date, scope, compensating controls, review date, and disable owner; and
- the repository owner has recorded approval for the exact global-enable or named-room-
  removal decision, after which a fresh, non-restored, separately audited admin recovery
  authentication performs only that technical transition.

Any failed or missing item leaves the global state disabled. Neither the repository
owner nor admin may waive a platform or rights-holder restriction. A successful global
enable preserves every denylist entry; a successful removal preserves the global bit and
all other entries and does not start the removed room.

## Payload-free audit contract

`CTRL-AUDIT-PAYLOAD-FREE` records only the minimum control evidence. The conceptual
fields below are stable content requirements, not a schema:

| Field | Allowed content |
| --- | --- |
| Event identity/time | Random audit event reference; occurrence and recorded timestamps. |
| Actor/control | Restricted pseudonymous actor reference, actor role, control ID, requested action, authorization result, and result code. |
| Target | For a denylist action, an opaque reference bound to the exactly verified canonical room; for deletion, exactly one typed room/session selector kind and opaque target/export reference. Identity deletion/revocation records only an opaque checkpoint-manifest reference and count, never its account/device target ID, event body, email, public key, bearer, or user-facing content. |
| Safety transition | Explicit action kind (global disable, global enable, denylist add, or denylist remove); prior and resulting shared generation; prior/result global bit; affected room's prior/result membership where applicable; proof the orthogonal dimension and non-target entries were preserved; stable reason code. |
| Incident/deletion | Opaque incident/manifest reference, immutable original initiating-request time, provisional-containment result, durable intake/tombstone commit/read-back and acknowledgement result, deletion state when admitted, payload-free store counts, retry count, completion timestamp, and immutable `sla_breached` result where applicable. |
| Integrity | Key identifier/version, previous journal-link reference, and a keyed integrity digest of the canonical control or manifest record. |
| Failure | Stable component/control error code, canonical-binding/freshness/write/read-back stage, escalation scope, and success/failure/denied/ambiguous result, never an upstream response body or protected value. |
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
| 1 | An operator invokes global disable while the durable safety store is deliberately slow. | The local latch changes to off immediately; new starts, refreshes, reconnects, and assignments are denied; local admission/publication gates close; and every active/queued room receives its termination/revocation/clear/hide actions before the first journal/recovery-copy await. |
| 2 | Hold the journal/recovery-copy operation pending and inspect the active room; repeat with an injected timeout/failure and a hypothetical future-owner fence-ack failure. | Without waiting for durable I/O, the single Alpha authority reaches every locally controlled result: the platform connection is locally closed, playback bytes/business events stop, the lease is revoked, late output is rejected, pending publication is hidden, and the locator plus all conforming audio buffers are cleared. A hung or failed write cannot pause cleanup or reactivate any resource. A separately failing cleanup action alerts, retries while off, and blocks relaxation; an unacknowledged future owner is isolated/terminated and keeps global off. |
| 3 | Reset to a separately approved globally-off predecessor, begin a valid `global-enable(g→g+1)`, and in separate race subcases inject global disable immediately before and immediately after its atomic final check-and-effect. | If disable linearizes first, enable fails its atomic fence/epoch comparison and never reopens. If enable linearizes first, disable immediately latches off and starts all-room cleanup; in both orders the final state is off, no late response clears the latch, and reconciliation uses the newest complete snapshot. |
| 4 | Let the first disable transition commit/read back; observe the failed subcase. | The committed action changes only the global bit, advances from its predecessor, and preserves the denylist. The failed subcase remains locally off with cleanup independently completed or retrying under alert, and permits no enable/remove until reconciliation. |
| 5 | In separate attempts, crash after local latch/authority closure but before journal commit; after journal commit but before recovery-copy commit/read-back; and after both read back but before the caller receives a response. | Every restart begins default-off with old leases/output rejected. An exact committed disable is reused; a split/unknown result remains off and reconciles from the newest complete snapshot without dropping the denylist. Retry/late response never clears the latch or repeats an unsafe local effect. |
| 6 | Attempt a platform reconnect and a worker frame from the revoked lease. | Both are denied under the current generation. No credentialed/alternate platform fallback or audio retry queue is created. |
| 7 | Inspect audit content. | The explicit global-disable action, prior/result global bit, preserved denylist, generation, result, and integrity metadata exist; no content, secret, locator, transcript, or audio appears. |

**Pass result:** Future disclosure and publication are stopped, recovery-copy failure
cannot fail open, slow or unavailable durability cannot defer active cleanup, and the
record does not claim that an untrusted worker erased RAM.

### Tabletop 1B: canonical-room denylist add without global side effects

**Setup:** In an isolated test design, the global bit is enabled, canonical room `A` is
active with one platform session and lease, and unrelated canonical room `B` is eligible
but inactive. Neither room is denied. Capture both rooms' state and the current generation.

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | While `A` is active, an operator adds exactly resolved unrelated room `B` to the denylist, advances the shared generation, updates the journal/recovery copy, and verifies read-back. | Only membership of `B` changes. `B` starts/reconnects are denied, but `A`'s platform session, lease, audio/locator RAM, and pending publication are untouched. The global bit remains enabled and `B` is not started. |
| 2 | Reset the isolated case, make `A` active again, and add exactly resolved room `A`. | Before or concurrently with durability, `A` is provisionally blocked and only `A`'s platform session, lease, late output, locator/audio, and pending publication are stopped/cleared. Commit/read-back decides whether scoped success may be reported; `A` reconnect is denied and unrelated `B` remains otherwise unchanged. |
| 3 | Inspect both transition audits and re-evaluate unaffected rooms. | Each audit proves the explicit action, canonical binding, prior/result global bit and target membership, preserved non-target state, generation, and integrity result. A generation change alone triggers re-evaluation, not cleanup or automatic start. |
| 4 | Separately inject alias ambiguity, changed room binding, stale safety state, and journal/recovery-copy write or read-back failure. | No room-scoped success is reported. Each variant escalates to local global off, immediately issues all-room cleanup without another durability await, emits a payload-free failure-stage/escalation audit, and blocks every relaxation pending reconciliation. |
| 5 | Race global disable and `add(B)` from the same predecessor in both commit orders; also lose the response after a verified `add(B)` and retry it. | At most one successor commits. If add wins, disable still latches/cleans globally and reconciles from the newer snapshot while preserving `B`; if disable wins, stale add cannot overwrite off or drop entries. Response-loss retry reuses the verified add rather than reopening `B`; unverifiable scope never reports room success and escalates globally. |
| 6 | Globally disable, then perform a separately approved global-enable transition while `B` remains denied; in a separate global-off subcase, perform an approved `remove(B)`. Reset another subcase with `A` initially denied, then race a valid `remove(A)` and newer `add(A)` on both sides of their atomic final check-and-effect. | Global enable does not remove `B`. Removing `B` does not enable globally, alter another entry, or start `B`. If removal linearizes first, the following add blocks/cleans `A`; if add linearizes first, removal fails without reopening `A` or clearing its block. The two dimensions and tightening precedence remain intact. |

**Pass result:** A successful `add(B)` leaves active unrelated `A` untouched, while a
successful `add(A)` contains only `A`; both preserve the global bit. Uncertainty escalates
globally, and a generation change by itself causes re-evaluation rather than cleanup.

### Tabletop 2: room-or-session takedown with one failed object deletion

**Setup:** Run room and session subcases through a durable takedown/incident intake and a
tombstone-capable independent recovery copy. Room `R` initially has sessions `S1`/`S2`,
and a stale backup later reveals `S3`; another room is unrelated. The session subcase
selects `S1` while `S2` shares room-level projections. Each selected scope has normalized
rows, cache/index entries, an encrypted raw object, and a managed export. Inject primary
safety-store unavailability, recovery-copy commit/read-back failures, crashes on both
sides of verified commit, and one selected raw-object deletion failure; advance simulated
time beyond 24 hours before the raw-object retry succeeds.

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | An admin submits exactly one typed selector; separately test room/session plus none, both, ambiguous, unknown, and conflicting parent-hint/index inputs. | A verified room scope immediately provisionally contains `R`; verified session scope derives `S1`'s parent from the authoritative index and provisionally contains only `S1`. Neither is yet accepted/reportable `hidden`. Invalid scope starts no tombstone or purge; a known room is denied, otherwise global off/escalation applies. |
| 2 | With the primary application/safety store unavailable, assign the immutable original initiating-request time and atomically write/read back it with selector/idempotency in the durable intake; then commit/read back the typed `hidden` tombstone in the independent recovery copy. | The unresolved intake retains the same selector/idempotency/time triple across the admission barrier but is not a deletion state or purge authority. The tombstone must reuse that time. After tombstone read-back, and only then, the request is accepted, `hidden` is reportable, and purge may begin; the application-store outage keeps global off until later reconciliation. Audit/intake alone is not admission. |
| 3 | In separate attempts, fail intake durability, fail/time out tombstone commit/read-back after durable intake, and crash before verified tombstone commit. Restart with an empty application tombstone view and attempt re-enable. | No success, reportable `hidden`, or destructive purge occurs. Failed intake durability requires the initiating source to retry the original triple; an already durable intake remains unresolved with that triple. Restart begins off, resubmits it without resetting the SLA clock, and rejects re-enable. Empty application state cannot prove that no target exists. |
| 4 | Let recovery-copy commit succeed, lose its response, and crash before acknowledgement; retry the same intake after restart. | Retry discovers and verifies the same tombstone, manifest identity, selector, and original request time. It neither creates a duplicate nor loses/resets the target or SLA clock. |
| 5 | Purge all enumerated active stores with the raw-object failure injected. | Room scope covers room metadata plus `S1`/`S2`; session scope covers only `S1` and recomputes shared projections without exposing `S1` or deleting/hiding `S2`. Successful stores stay purged; the failed store records only an error code/count; completion is forbidden. |
| 6 | Retry the same manifest after the 24-hour deadline and verify all active stores. | The raw object is removed; the state becomes `active-purge-complete` with the original request time, a completion timestamp, and immutable `sla_breached=true`. |
| 7 | Evaluate exports and backups while their declared windows remain open. | Managed access is revoked and the target stays replay-protected, but `final-retention-window-satisfied` is withheld and retained copies are reported truthfully. |
| 8 | Restore the stale backup containing late `S3`; test both `session(S1)` then `room(R)` and `room(R)` then a later `session(S1)` request; expire/verify every window. | Pending `hidden` replay precedes safety reconciliation and room replay discovers/purges `S3`. In both orders the room tombstone remains dominant: the child manifest links without narrowing/overwriting the room block, resetting evidence, or reviving `R` metadata/`S1`/`S2`/`S3`. A standalone session tombstone affects only its session. Mapping conflicts stay isolated/off; final state waits for post-window verification. |

**Pass result:** Both typed selectors enforce their exact scope; provisional containment
is immediate but the three-state machine admits only a committed/read-back `hidden`
tombstone; failures, ambiguous responses, both crash windows, restart, restore, and early
re-enable cannot lose a target or fail open. Invalid/composite inputs cause no guessed
deletion, room retries/restores discover all room sessions and dominate narrower child
tombstones, session deletion preserves siblings/shared state, and partial/late deletion is
truthful.

### Tabletop 3: restore stale enablement, deleted data, and revoked identity

**Setup:** Restore an application-data backup whose generation is older, whose global
setting says enabled, whose denylist is stale, and whose rows include both a room-wide
tombstone target (with a late restored child session), an exact-session tombstone target
with a preserved sibling, and an account/device deleted after that backup. It also
contains apparently unexpired magic-link, enrollment-token, session-verifier/session
rows, a stateless token signed by the old key version, and the deleted subject's roles/
invites/device statistics. The separate recovery copy contains the newer forced-off
global bit and complete denylist under one generation, a durable unresolved deletion
intake plus pending `hidden` typed room/session tombstones with dominance, typed
pseudonymous account/device checkpoints, and newer auth-invalidation generation/key
version.

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | Boot the restore in isolation. | Startup ignores backed-up enablement and latches off before any viewer, ingest, worker, callback, or scheduled-job traffic. |
| 2 | Verify and load the separate recovery copy. | The unresolved intake, pending `hidden` tombstones, identity/device checkpoints, orthogonal global-bit/complete-denylist snapshot, safety generation, and auth-invalidation generation/key version are recognized. Missing/tampered/conflicting-copy or empty-application-store-as-proof variants stop here and remain off. |
| 3 | Purge/revoke restored verifier/session rows, reconcile the protected auth generation/key version, and probe old links/cookies/stateless tokens. | Every stateful/stateless pre-restore credential is server-rejected regardless of backed-up expiry/use state; old verification key material cannot become current; fresh authentication and enrollment are required. |
| 4 | Reconcile the unresolved intake to a commit/read-back-verified tombstone; replay typed room/session and account/device checkpoints; then verify exact scope and issuance denial. | No purge precedes admission. Room replay purges every restored child; session replay removes only its target and preserves the sibling; room dominance holds. Scoped account authority is purged/revoked and cannot authenticate or receive a new credential before safety reconciliation. |
| 5 | Reconcile the shared safety generation, global enabled bit, and complete denylist. | The stale backed-up generation/global bit/denylist cannot overwrite the current copy. Global enable cannot clear a room entry, exact-room removal cannot enable globally, and generation change alone only re-evaluates. Gaps, binding conflicts, or mismatches remain globally off and produce a payload-free alert. |
| 6 | Attempt `CTRL-REENABLE-GATE` before intake/tombstone reconciliation, then evaluate it after reconciliation using a fresh, non-restored, separately audited admin recovery authentication. | The early attempt is denied even if the application store is healthy/empty. Restored admin sessions remain invalid. Traffic stays blocked until durable intake/tombstone replay, remediation, current rights/policy, audit, tabletop, provider-window, and owner approvals pass and the fresh recovery admin records the exact durable global-enable transition without clearing the denylist. |

**Pass result:** Stateful/stateless pre-restore credentials remain server-rejected,
unresolved intake and pending `hidden` tombstones reconcile/replay before orthogonal
safety-state reconciliation, and every step precedes traffic. Neither empty application
state, an old enabled value/denylist, a restored admin session, nor deleted identity/device
authority becomes current.

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

For the new failure boundaries, Issue #7 owns global-versus-room transition scope,
canonical binding, cleanup, and noninterference; Issue #11 owns immediate provisional
visibility containment; Issue #16 owns recovery-boundary intake/tombstone commit and
read-back, idempotency, purge, and fault injection; Issue #17 owns admin request/
acknowledgement, unresolved-intake retry, status, and relaxation blocking; and Issues
#4/#19 own crash/restart/restore and pre-traffic replay drills. Their evidence must cover
intake-write failure, tombstone commit/read-back failure, both crash windows, lost
response, empty application state, room-add ambiguity/staleness/write failure, and early
re-enable without defining Issue #2 runtime schema or wire fields.
