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
| `CTRL-SAFETY-DEFAULT-OFF` | Production ingest and every startup/restore begin without serving activation; no durable value or old response recreates the non-restorable current-incarnation activation, and missing, stale, ambiguous, or conflicting state remains off. | Issues #4, #7, #16, and #19 |
| `CTRL-SAFETY-GENERATION` | One monotonic generation orders two orthogonal safety dimensions—the global enabled bit and canonical-room denylist—through non-effective `PREPARED` proposals and a conditionally advanced `COMMITTED` recovery head. Global enable promotes before its non-restorable current-incarnation activation; room removal keeps membership through preparation and requires a pre-promotion one-use permit whose consumption authorizes the conditional removal. | Issues #4, #7, #16, #17, and #19 |
| `CTRL-ROOM-DENYLIST` | Eligibility and every reconnect use the canonical platform room ID; a verified add/remove changes only that room entry, while ambiguity, stale/binding conflict, or transition write/read-back failure escalates to global disable. A failed final removal guard or lost/prior-incarnation permit cannot remove the durable entry. | Issues #7, #16, and #17 |
| `CTRL-DISABLE-CLEANUP` | Global disable cleans up every active/queued ingest scope; a successful canonical-room denylist add cleans up only that room and does not disturb unrelated rooms, without depending on the failing ingest path. | Issues #7, #8, #11, #14, #15, #16, #17, and #19 |
| `CTRL-RESTORE-REPLAY` | An offline restore rejects stateful/stateless pre-restore credentials, reconciles every intake-continuity epoch and authoritatively replays unresolved safety, room/session deletion, and account/device deletion or revocation controls to their required tombstone, checkpoint, or denial; it applies those results before reconciling current orthogonal global/denylist state and never restores serving activation. | Issues #4, #12, #13, #16, and #19 |
| `CTRL-IDENTITY-RESTORE-REVOCATION` | Account/device deletion or revocation intake is bound to a read-back-verified `open(E)` and its pending/high-watermark accounting before identity authority changes; typed pseudonymous checkpoints, durable invalid/unauthorized denials, and auth-invalidation state survive application backups, and every stateful/stateless pre-restore credential is server-rejected before authentication or traffic. | Issues #4, #12, #13, #16, #17, and #19 |
| `CTRL-REENABLE-GATE` | Only an admin may technically enable globally or remove one denylist entry, as separate exact-predecessor transitions, and only after current owner approval, safety/deletion/identity-control intake continuity, and every incident, rights, journal, recovery, and tabletop prerequisite passes. Durable global-enable commit alone never opens service; denylist removal cannot commit until its same-incarnation final guard has supplied the one-use promotion permit. | Issues #7, #16, #17, and #19 |
| `CTRL-AUDIT-PAYLOAD-FREE` | Every safety, incident, deletion, identity-control, and raw-access result is append-only and auditable without protected payload. | Issues #12, #13, #16, #17, and #19 |
| `CTRL-DELETION-FAIL-CLOSED` | A verified takedown selector is provisionally contained immediately, but acceptance, reportable `hidden`, and purge wait for commit/read-back of its durable `hidden` tombstone; the same append-only open/clean-close intake-continuity epoch also covers account/device checkpoint-or-denial outcomes and prevents any persistence-failed or crash-lost request from being mistaken for absence. | Issues #11, #12, #13, #16, and #17 |
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
  device deletion-or-revocation checkpoints and durable invalid/unauthorized denials; and
- integrity metadata and references to any required owner approval.

The journal stores the payload-free fields below, not platform responses, room content,
credentials, raw events, transcripts, or audio. A safety transition has one idempotency
identity, exact predecessor generation and head digest, one action—global disable,
global enable, denylist add for one canonical room, or denylist remove for one canonical
room—and the resulting complete orthogonal snapshot. The snapshot also retains latest
per-room add/remove provenance. A denylist-removal proposal leaves `R` in the current
snapshot throughout `PREPARED`; it cannot publish a snapshot without `R` until the same
live incarnation has passed the room-specific final guard and minted a single-use,
non-restorable removal permit. The one generation orders both dimensions; it does not
couple their effects. A stale,
duplicated, rolled-back, missing,
or conflicting generation cannot replace a newer decision. An empty restored database
is not evidence that generation zero is current.

The durable transition has two phases. `PREPARED` means the append-only proposal exists;
it is not current safety state and never permits serving. `COMMITTED` means a matching
journal proposal exists and a conditional compare-and-swap advanced the integrity-
protected recovery head from the exact predecessor to the result, after which both
records passed read-back. The recovery-head compare-and-swap is the durable-state
linearization point. A journal-only proposal, a head-only or mismatched record, a failed
conditional write, missing read-back, or an unknown result cannot activate a relaxation.
This is an idempotent single-writer protocol over the already required journal and
recovery copy; it does not claim an atomic transaction across process RAM and two stores.

Each process start creates a never-reused serving incarnation with no serving activation.
A `COMMITTED` global-enable decision is durable history and a necessary condition, not
permission to serve. Only the same still-live incarnation may, after exact read-back,
perform one short local compare-and-set that checks the committed head, its captured
applicable `G` and deletion-intake fence epochs, the matching continuity epoch, every
cleanup and governance gate, and then installs global activation. That activation is
deliberately not durable and cannot be reconstructed after restart.

Denylist removal uses the opposite safe ordering because its durable snapshot directly
controls later room eligibility. While `R` is still present in the current snapshot, the
same live incarnation performs one short local compare-and-set over the exact `PREPARED`
proposal, predecessor head, captured `G`/`Q[R]` and deletion-intake fence epochs,
continuity epoch, cleanup, and governance gates. Success atomically mints and consumes a
single-use, non-restorable `remove-permit(R, proposal, incarnation)` to issue exactly one
conditional recovery-head promotion, but does not yet unblock or start the room. That
promotion to `COMMITTED` atomically removes `R` and is the removal's
durable/effective linearization point. There is no fallible post-commit local effect.
Guard failure, process loss, or permit loss before the promotion request is issued leaves
`R` in the durable denylist. After dispatch, crash or an unknown result requires exact
journal/head reconciliation under global off: a matching `COMMITTED` head is the valid
permitted removal; an unchanged predecessor/`PREPARED` proposal still contains `R`; and
split or unverifiable state remains off. Any later tightening applies its safe local guard
immediately. If removal wins the recovery-head compare-and-swap, the tightening reloads
and replays against the promoted head; if a same-head tightening wins, removal promotion
fails without rebasing and `R` remains. A later deletion intake keeps its exact scoped
block while the permitted promotion outcome is reconciled. Verified promotion followed
by response loss is an idempotently successful removal, not an unapplied snapshot.

The backend also has one high-priority, ingest-independent local guard family: global
guard `G` and canonical-room guards `Q[R]`. A global disable atomically revokes current-
incarnation global activation, increments `G`, and sets its sticky local global-off latch;
a denylist add increments only `Q[R]`, sets its sticky target-room block, and invalidates
an unissued removal permit for that room. After promotion dispatch, `Q[R]` still blocks
locally while competing exact-head outcomes follow the reconciliation above. Neither
waits behind normal transition or durable I/O.
If a tightening's conditional commit loses to another successor, it reloads the newest
complete head and reapplies the same safe action idempotently; a relaxation never rebases
its approval automatically. If global activation or the room-removal permit compare-and-
set wins, a following global disable revokes globally, while a following `add(R)` blocks/
cleans only `R`. If an applicable guard or deletion-intake fence wins the pre-dispatch
local compare-and-set, only that relaxation fails; pending
`Q[R]` or intake does not revoke already installed unrelated activation. Classified
binding, ordering, durability, or containment ambiguity invokes a distinct global-disable
transition. A crash discards every activation and starts the next incarnation off, so a
previously committed relaxation or delayed response cannot reopen service while pending
state is reconciled.

Alpha has exactly one active serving authority process, which owns every active/queued
room and therefore applies this local guard family without a cross-process durability
dependency. A future multi-process deployment may not enable production until that guard
family is
synchronously visible to every active owner through an ingest-independent path. Failure
to enumerate an owner or obtain its applicable-guard acknowledgement immediately isolates/terminates
that owner at the deployment or egress boundary, keeps global off, and blocks relaxation.

Before a serving incarnation may accept deletion or account/device-control ingress or
install serving activation,
it commits and reads back an append-only `open(E)` serving/intake-continuity epoch in the
recovery boundary. The epoch remains open while that incarnation can receive safety
tightening, room/session deletion requests, or account/device deletion or revocation
controls. It may gain `clean-close(E)` evidence only after the same logical transition
authority atomically quiesces serving, safety-control, deletion, and identity-control
ingress; every accepted safety-control handler is drained and its outcome durably
reconciled; every deletion request seen in `E` is drained, with each valid request mapped
to its commit/read-back-verified `hidden` tombstone and each invalid request mapped to a
durable denial; and every account/device control seen in `E` is drained, with each valid
action mapped to its commit/read-back-verified typed pseudonymous checkpoint and each
invalid or unauthorized action mapped to a durable denial. The close is bound to the epoch
predecessor/high-watermark, commits and reads back while the ingress fence remains closed,
and cannot race a late control into the closing incarnation. If a safety, deletion, or
identity-control request linearizes first, close waits; if close linearizes first, the
request is rejected or bound to a new commit/read-back-verified epoch. Starting an
authenticated deletion request
atomically increments the local intake fence and sets `intake-pending` before it can race
a relaxation. Pending fences that relaxation and `clean-close(E)`; by itself it neither
revokes an already installed global activation nor denies traffic outside a verified
selector's provisional block. Observing a valid, exactly resolved selector installs that
room/session-scoped block under the same local authority before target-specific durability.
A durably denied invalid request clears pending without changing activation. Accepting an
authenticated account/device deletion or revocation control likewise binds it to the
current verified `open(E)` and atomically advances the epoch's pending/high-watermark
accounting before any target authority is stopped or any checkpoint is written. Ordinary
pending fences relaxation and `clean-close(E)` without revoking unrelated activation; a
valid action immediately stops the exact target's issuance/authority and clears pending
only after its typed checkpoint commits and reads back, while an invalid or unauthorized
action changes no target authority and clears pending only after durable denial. A failed
or ambiguous required intake, denial, tombstone, or identity-checkpoint commit/read-back,
or loss of proof that a selected deletion scope is contained, makes the guard sticky
`tainted`, atomically revokes serving activation, and keeps global off. If the recovery
boundary is then unavailable or the process crashes, the already durable unmatched
`open(E)` remains the recovery-visible blocker. The initiating client is not a recovery
authority. A later incarnation may clear the blocker only from exact authoritative replay
and reconciliation of safety, deletion, and identity-control handlers; if any accepted
action cannot be recovered, production remains off rather than guessing that none existed.

Issue #16 must maintain an encrypted, integrity-protected current recovery copy containing
enough of the latest safety/denylist state, journal integrity head, durable unresolved
room/session deletion intake, typed deletion manifests and dominance, typed pseudonymous
account/device checkpoints and durable control denials, append-only intake-continuity
epochs with predecessor/high-watermark evidence, and monotonic authentication-invalidation
generation or key version to detect stale application-data backups. A
checkpoint target is a random immutable never-reused internal reference, not an email,
role, public key, bearer, canonical room ID, or unkeyed digest of a low-entropy value.
These references remain linkable pseudonymous data, so access is narrowly authorized and
audited by opaque manifest reference/count. The copy and current verification key
material are stored separately from restorable application-data backups. It is a safety
dependency, not a general raw-data backup, and contains no direct identity field, event,
transcript, audio, bearer/verifier, playback locator, or other user content.

### Safe transition rules

- **Global disable:** an authorized operator/admin latches global off immediately and
  atomically revokes current-incarnation global activation, increments `G`, marks the
  current continuity epoch `safety-pending(global)`, closes local admission/
  publication gates, and issues termination, revocation,
  clearing, and hiding actions for every active or queued room before the first journal/
  recovery-copy await. Cleanup completion may proceed concurrently with durable I/O. The
  backend writes the exact-predecessor `PREPARED` decision without changing denylist
  membership, conditionally advances the recovery head to `COMMITTED`, and verifies both
  read-backs before acknowledgement and clearing `safety-pending(global)`. If another transition committed first, disable is
  reapplied to that complete head until it commits or remains unresolved/off. Any write,
  read-back, integrity, or cleanup failure keeps the local latch in force, alerts, retries,
  and blocks relaxation; the design does not claim erasure on an untrusted host.
- **Denylist add:** after exact canonical-room binding, an authorized operator/admin
  atomically increments `Q[R]`, invalidates an unissued removal permit for that room, marks the
  current continuity epoch `safety-pending(room:R)`, provisionally blocks it, and
  starts only its cleanup without revoking global activation or interrupting another
  room. If removal promotion was already dispatched, this block remains immediate while
  the exact-predecessor compare-and-swap winner is reconciled. The backend writes the
  exact-predecessor `PREPARED` add without changing the global enabled bit or any other
  entry, conditionally advances the recovery head to `COMMITTED`, and verifies both read-
  backs before acknowledgement and clearing `safety-pending(room:R)`. If another successor won, the same add is reapplied to
  the newest complete head. Once verified, the room remains denied and unrelated rooms
  retain their prior state and eligibility; nothing starts automatically. Ambiguous or
  changed binding, stale control state, or failed/ambiguous journal or recovery-head
  commit/read-back escalates to global disable rather than guessing a room-scoped success.
- **Global enable:** only an admin may request this transition, with current recorded
  owner approval and all `CTRL-REENABLE-GATE` evidence. The proposal captures the exact
  recovery head, current incarnation, global guard `G`, deletion-intake fence epoch, and
  matching `open(E)`. Its `PREPARED` and conditionally `COMMITTED` generation sets only
  the global bit and preserves the complete denylist. It never rebases automatically.
  After both durable records read back, the same incarnation performs the final local
  compare-and-set over the exact committed head, captured applicable guards, continuity guard,
  cleanup, and governance gates, then installs non-restorable global activation. A
  concurrent/newer applicable guard or intake, unfinished applicable cleanup, stale head, prior-
  incarnation record, or partial/ambiguous result prevents activation. An intake-pending
  state that wins this final check denies the new relaxation; it does not revoke an
  activation that was already installed. Even if its durable bit is already enabled, a
  later incarnation requires a fresh committed transition and final activation; the old
  result is never replayed into service.
- **Denylist remove:** only an admin may request removal of one exactly bound canonical
  room, with current owner approval and all applicable `CTRL-REENABLE-GATE` evidence. Like
  global enable, it captures one exact predecessor/incarnation/`G`/`Q[R]`/continuity tuple,
  never rebases, and keeps that entry in the current snapshot while writing/reading back
  `PREPARED`. The same incarnation must then pass the final local guard compare-and-set
  and atomically mint/consume a single-use removal permit while `R` is still denied. That
  is the only path allowed to issue conditional promotion of the exact proposal; `COMMITTED` then
  removes only that entry while preserving the global bit and every other entry. Removal neither
  globally enables ingest nor starts the room. A concurrent/newer add or intake,
  unfinished applicable cleanup, or prior-incarnation use prevents permit mint/consumption
  without treating pending alone as a global disable; `R` therefore cannot
  disappear from the durable snapshot after a failed final guard. Binding, freshness,
  write/read-back,
  or integrity uncertainty instead escalates to global disable. A committed removal from
  the permitted promotion is a durably successful owner-approved decision; response loss
  retries that same result. Crash or guard failure before promotion dispatch leaves the room
  denied and requires a fresh owner-approved removal. Crash or uncertainty after dispatch
  keeps the environment globally off until the exact journal/head proves a matching
  `COMMITTED` removal or an unchanged predecessor/`PREPARED` state; split or unknown state
  remains off.
- **Canonical identity:** aliases and URLs resolve to one canonical Bilibili room ID
  before selection, eligibility, or denylist comparison. Resolution failure, ambiguity,
  stale state, or an unavailable configuration store is a denial, never a fallback.
- **Ongoing checks:** the current-incarnation activation, effective global generation,
  global enabled bit, canonical denylist, and applicable local `G`/`Q[R]`/intake guards are checked
  before each start and reconnect. A pending deletion intake fences relaxation and close,
  while its verified selector block denies only that target; it does not make the global
  bit or existing activation false for unrelated scope. A tainted/unaccounted intake does.
  A generation change requires re-evaluation; it is not itself a cleanup instruction or
  activation. A resulting global-off or missing-activation state denies service, a global
  disable invokes global cleanup, a resulting denylist match invokes cleanup only for
  that room, and an unrelated verified room change preserves unaffected active operation
  subject to ordinary eligibility checks.

No safety operation may silently decrement/rebase a generation, truncate history,
reconstruct an enabled value from an application backup, or treat journal/recovery-copy
unavailability as permission to continue. No implementation may derive the global bit
from an empty/non-empty denylist, clear the denylist on global enable, or treat removal of
one room as global enablement. No implementation may treat `PREPARED`, `COMMITTED`, a
prior-incarnation activation, or a control response as interchangeable states.

## Immediate disable and denylist procedure

The safety path must remain usable when the platform adapter or normal ingest state
machine is failing. On any security, rights/platform, credential, raw-access, worker,
deletion, control-integrity, or unknown-severity incident whose safe containment scope is
global or a canonical room:

1. An operator/admin explicitly selects global disable or denylist add for one resolved
   canonical room. If room resolution/binding is ambiguous, conflicting, or stale, apply
   global disable rather than guessing an ID.
2. Apply the provisional local effect immediately. Global disable rejects every new room
   start, reconnect, refresh, and worker assignment, including queued requests, **and
   atomically revokes current-incarnation activation, increments `G`,
   closes its local admission, publication, lease, and late-output authority gates, and
   issues cleanup for every active or queued room before awaiting any journal or recovery-
   copy I/O**. The single Alpha serving authority owns all such resources; its cleanup
   executor is independent of the failing ingest path and durable-I/O executor. Steps 4–7
   are the actions issued here; they progress before or concurrently with step 3 rather
   than being gated by their numbering. An exactly bound
   canonical-room denylist add increments only `Q[R]`, invalidates any unissued removal
   permit, and rejects only the target room's starts, reconnects, refreshes, and assignments.
   If promotion was already dispatched, the block remains while the competing exact-head
   result is reconciled. It also begins target-room cleanup immediately, while unrelated rooms retain their prior
   state and are not started automatically.
3. With the applicable cleanup already in progress, append the exact-predecessor
   `PREPARED` proposal, conditionally advance the recovery head to `COMMITTED`, and verify
   both read-backs before acknowledgement. A tightening that loses the predecessor race
   is reapplied to the newest complete head; it is not discarded with the stale proposal.
   Slow or hung durable I/O cannot postpone cleanup. A global-disable write failure cannot
   undo its local latch, stop cleanup, or reactivate a resource. A room-add write/read-
   back, integrity, freshness, or binding failure escalates the local posture to global
   off, immediately expands cleanup to every active or queued room without another
   durability await, and raises a payload-free security alert; it is never reported as a
   successful room-only transition.
4. Complete the already-started cleanup at the effective scope. Global disable, including
   escalation from a failed room-add transition, covers every active or queued room. A
   successfully verified denylist add finishes cleanup only for the canonical target room
   and proves non-target room state was not changed. Terminate each in-scope Bilibili platform
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
   durable-admission barrier below before reporting `hidden`. A structurally invalid
   request with no credible affected target is durably denied without changing global
   activation. When a credible hazard identifies the room but session scope conflicts,
   deny that room; when such a hazard has no safely bounded scope, remain globally off and
   escalate. Never guess destructive scope.
8. Append a `CTRL-AUDIT-PAYLOAD-FREE` result for each attempted control, distinguishing
   `PREPARED`, `COMMITTED`, global activation/revocation, and room-removal permit outcome
   without treating a response as state, and notify the incident owner through an approved
   non-payload channel.

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
missing/non-unique session resolution is denied rather than guessed and does not, merely
by being invalid, change global activation. If independent credible takedown evidence
still identifies a bounded exposure, block the known room; if such a hazard cannot be
safely bounded, revoke global activation and escalate. Begin no destructive purge. An
operator may first stop/denylist the room but may not declare deletion complete.
Deletion ingress is unavailable until the current incarnation's `open(E)` has committed
and read back. At the authenticated intake boundary, every request atomically increments
the local deletion-intake fence and sets `intake-pending` before it can race a relaxation.
Pending fences global enable's final activation and a clean epoch close. Before room-removal
promotion dispatch it prevents the permit; after dispatch the selector-scoped block or taint
applies immediately while the exact durable outcome reconciles. It does not
revoke existing global activation or deny non-target traffic. An invalid request clears
pending only after its payload-free denial is durable; it never creates a tombstone,
authorizes purge, or requires re-enable after that successful denial.

1. Immediately apply provisional containment for the verified selector while durable
   admission is pending. A room selector blocks the room's new start/reconnect/write/
   publication, all session visibility, leases, audio/locators, exports, and persistence.
   A session selector blocks only that session's visibility and descendants and stops its
   ingest, lease, audio, locator, and export paths when active; sibling sessions and shared
   room-level state remain available under the existing global activation. The valid-
   selector observation and scoped block are one local linearization step, so a concurrent
   relaxation cannot open the target between them. This immediate effect is not a fourth
   deletion state and is not yet an accepted or reportable `hidden` result.
2. Keep the initiating takedown/incident intake open with the exact selector. Before its
   first durability attempt, assign one immutable authenticated initiating-request time.
   Atomically write/read back that time with selector and idempotency identity in the
   independent recovery boundary so all three survive until admission. It is only an
   unresolved blocker, not a deletion state, tombstone, or purge authorization. If intake
   durability itself fails, return no success, mark the current local guard sticky
   `tainted`, atomically revoke global activation, retain the selector/time triple while
   the process can do so, and keep global off. A client retry is useful but is not recovery
   evidence: `open(E)` cannot receive a clean close until exact authoritative replay
   resolves this request. Then commit the existing typed, payload-free `hidden` tombstone
   to that boundary and verify read-back **before** accepting or
   acknowledging the request, reporting `hidden`, or starting destructive purge. A
   volatile block, audit event, intake record, or empty application store is not a
   substitute. If tombstone commit/read-back fails, times out, or has an ambiguous result,
   return no success, start no purge, make/keep the continuity guard tainted, atomically
   revoke global activation, keep global off, and leave the durable intake unresolved for
   idempotent retry. The tombstone must reuse the intake's original time; a missing/
   mismatched time fails admission. If a
   commit succeeded but its response was lost, retry reuses the same tombstone, original
   request time, and manifest identity. Only verified tombstone admission resolves this
   request for continuity accounting and clears pending. On the ordinary success path it
   neither revokes nor installs global activation, so unrelated scope needs no re-enable.
3. Enumerate and idempotently purge every active store named by Issue #16: normalized
   rows, indexes, caches, replicas, manifests, raw objects/versions, managed exports, and
   derived/shared projections. Room scope re-enumerates every child session/path on each
   retry/replay; session scope includes only the resolved session and recomputes shared
   projections without deleting or hiding siblings/shared room state.
4. A room tombstone dominates its child-session tombstones. A later session request cannot
   narrow/overwrite the room block; an earlier session manifest may be linked into the
   room manifest without resetting evidence or reviving data. Retries keep selector kind,
   opaque target, original request time, and manifest identity.
5. A failed, ambiguous, or unchecked store/child keeps the safe block. An ordinary failure
   inside a still-proven exact scope remains scoped and does not revoke global activation;
   loss of proof that containment covers the target or that ownership is bounded escalates
   globally. Record only a stable error code/count, then retry idempotently. Room scope
   cannot complete until every child is enumerated/empty; session scope cannot complete
   until its descendants are empty and siblings/shared room state are proven preserved.
   Never guess-delete an uncertain owner.
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
time, and the unmatched `open(E)` plus unresolved record block re-enable. A crash before
intake durability also produces no acknowledgement, but does not depend on the initiating
source surviving: the already committed unmatched `open(E)` proves continuity was not
cleanly closed. The next incarnation remains off until exact authoritative replay
recovers and admits the request; if that is impossible, it remains off indefinitely. A
crash after tombstone commit but before response is recovered by the idempotent retry and
existing tombstone. Every restart/restore reconciles every intake-continuity epoch and
unresolved request before safety reconciliation: a valid intake must obtain or reuse a
verified `hidden` tombstone, while an invalid request must obtain durable denial.
Recovery of the application store, an empty application tombstone view, or a stale/late
client response never closes an epoch or proves that no target exists.

## Account/device deletion or revocation and restored credential procedure

`CTRL-IDENTITY-RESTORE-REVOCATION` applies when an admin deletes or revokes an account or
device:

1. Through the same logical authority that owns `open(E)`, accept the authenticated request
   into authoritative replay order and atomically bind it to the current verified epoch by
   advancing its pending/high-watermark accounting **before** changing account/device
   authority or attempting a checkpoint. Validate authorization, a typed operation
   (`deleted` or `revoked`), and exact scope. An invalid or unauthorized action changes no
   authority and may clear pending only after its durable denial commits and reads back.
2. For a valid action, stop new authentication, token/session issuance, enrollment, and
   worker assignment for the exact target immediately. Account deletion revokes and
   cascades through roles, invites, devices, aggregate statistics, tokens, verifiers, and
   sessions. Device deletion affects only that device, its enrollment/session state, and
   device-scoped statistics unless the account is also targeted. A permanent deletion may
   never be downgraded to a reversible revocation, and a lower generation may never replace
   either operation.
3. Commit the typed pseudonymous checkpoint to the separate recovery copy and verify its
   read-back and integrity **before** reporting deletion/revocation complete or clearing
   pending. A failed or ambiguous intake, checkpoint, or denial leaves the exact target
   authority stopped where applicable, taints the continuity epoch, revokes serving
   activation, and keeps every restore traffic class globally off. A crash before the
   verified outcome leaves unmatched `open(E)` as a cross-restart blocker; only exact
   authoritative replay may reconstruct the checkpoint or denial and clear it.
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
   callback traffic. Create a new never-reused serving incarnation with no activation and
   the local forced-off latch, regardless of any restored setting.
2. Verify the integrity and freshness of the separate safety/deletion/revocation
   recovery copy, including the independently recorded global enabled bit, complete
   canonical-room denylist, every `PREPARED` proposal and `COMMITTED` head, each intake-
   continuity epoch and predecessor/high-watermark, every pending `hidden` tombstone, and
   every identity checkpoint or denial. Failure to establish the copy's authenticity,
   integrity, freshness, or single non-rolled-back authority ends the activation attempt:
   do not replay or clean-close from that copy, keep every authentication and traffic class
   isolated/off, alert, repair or recover an authoritative copy, and retry. By contrast, a
   verified copy that exposes an unmatched prior `open(E)`, stale/cross-epoch close,
   unresolved safety handler, valid deletion without a tombstone, invalid deletion without
   denial, valid identity action without a checkpoint, or invalid/unauthorized identity
   action without denial is a recovery blocker, not proof that the copy is untrustworthy.
   Reject the stale close, preserve isolation, and continue the following offline replay;
   an empty restored application store proves none of those actions absent.
3. Fence the old incarnation/authority and authoritatively replay every accepted safety,
   room/session deletion, and account/device deletion or revocation control in each
   unmatched epoch through its exact predecessor/high-watermark. Reconcile each safety
   handler to its durable outcome; recover every valid deletion to its exact selector,
   idempotency identity, original time, and verified `hidden` tombstone, and every invalid
   deletion to durable denial; recover every valid identity action to its exact typed
   pseudonymous checkpoint and every invalid or unauthorized identity action to durable
   denial. If authoritative replay, exact binding, or completeness cannot be proved, keep
   the epoch unmatched and the environment isolated/off; do not guess, clean-close, open a
   successor epoch, or attempt activation.
4. Apply every replayed or already current result. Replay every pending `hidden` tombstone before any
   completion claim: typed room tombstones cover every restored session for their
   canonical room and typed session tombstones cover only their uniquely resolved session,
   across Postgres data, indexes/caches, raw objects/versions, managed exports, and shared
   projections. Room tombstones retain dominance over child-session manifests; missing/
   conflicting parent mapping or tombstone admission uncertainty leaves the environment
   isolated/off and starts no guessed purge;
   replay typed account/device deletion/revocation checkpoints against account, role,
   invite, device, statistics, token, verifier, and session rows. Purge or revoke every
   restored magic-link, worker-enrollment, session-verifier, and session row irrespective
   of backed-up expiry/use/revocation state; advance or reconcile the recovery-protected
   auth-invalidation generation or non-restorable signing/verifier key version, keep old
   key material outside the active verification set, and negatively probe sampled pre-
   restore stateful/stateless credentials. Verify that no deleted target is active,
   visible, authenticable, or able to receive newly issued authority.
5. Reconcile the application journal with the latest shared safety generation, global
   enabled bit, and complete canonical denylist recovery copy. Preserve the two dimensions
   independently: global enable never clears a room entry and removal of one room never
   implies global enable. A generation change triggers re-evaluation only; its resulting
   global/room decisions determine cleanup. A stale restored generation cannot overwrite
   the newer copy. A journal-only global-enable proposal is abandoned without activation;
   an unpromoted room-removal proposal still has its room in the current denylist because
   prior-incarnation permits are invalid; an exact prepared tightening is replayed against
   the current complete head. Any head/journal gap, binding mismatch, or integrity conflict leaves the environment globally
   off and creates a payload-free alert.
6. Verify provider-window inventory, audit integrity, source/platform/rights currency,
   incident remediation, applicable deletion and identity-control results, and current owner approvals. Every
   failed, timed-out, response-lost, or otherwise ambiguous valid deletion intake must
   reconcile to its verified durable tombstone and replay result; every invalid request
   must reproduce durable denial. Every valid account/device action must reconcile to its
   verified checkpoint and applied issuance denial, and every invalid or unauthorized
   identity action to durable denial. Neither an audit event nor an empty application store
   closes any path. Only after old authority is fenced, authoritative replay is complete
   through each exact high-watermark, all safety outcomes are durable, and every applicable
   tombstone, checkpoint, denial, and safety result has reconciled may the old epoch's
   `clean-close(E)` commit and read back against its predecessor/high-watermark. A failed,
   stale,
   cross-epoch, or ambiguous close remains unmatched/off and is retried; even a zero-event
   epoch needs authoritative zero-event proof. After every old epoch is cleanly sealed,
   commit/read back a fresh `open(E)` for the new incarnation before accepting deletion or
   identity-control ingress or attempting activation. Run the relevant tabletop using the
   restored environment while it remains isolated.
7. Only after all checks pass may a fresh, non-restored, separately audited admin
   recovery authentication request a global-enable or one-room denylist-removal transition
   under `CTRL-REENABLE-GATE`. Its credential and trust root cannot originate in the
   restored application backup; repository-owner governance grants no production
   credential. For global enable, the request must advance from `PREPARED` to the
   conditionally `COMMITTED` recovery head, pass both read-backs, and only then may the
   same incarnation verify the exact head, guards, matching `open(E)`, and remaining gates
   while installing non-restorable activation. For room removal, `PREPARED` leaves the
   entry present; the same incarnation must atomically validate those gates and consume a
   one-use permit in the conditional promotion that removes the entry. Global enable
   preserves every denylist entry, and removing one entry neither enables globally nor
   starts that room. Otherwise keep the environment offline/off and investigate. No
   authentication, viewer, worker, callback, or ingest traffic is admitted from a prior-
   incarnation record, delayed response, durable bit alone, missing global activation, or
   a lost/prior-incarnation room-removal permit.

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
- all affected room/session tombstones and account/device deletion/revocation checkpoints
  have replayed successfully; every failed, timed-out, response-lost, or ambiguous valid
  deletion intake has reconciled to a committed/read-back tombstone and every invalid
  request to durable denial; every valid account/device action has reconciled to a verified
  typed checkpoint and applied issuance denial, every invalid or unauthorized identity
  action to durable denial, and no such action remains pending; every restored stateful/
  stateless credential is server-rejected; restored identity/device authority cannot issue
  a new credential; and no partial purge or unknown provider window is being misreported;
- every prior serving/intake-continuity epoch is cleanly closed from exact authoritative
  safety, deletion, and identity-control replay through its predecessor/high-watermark;
  the current incarnation's `open(E)` is committed/
  read back; no safety-pending transition exists; and
  its local intake fence has no pending or tainted request. An unmatched epoch is never
  cleared from an empty store, audit row, client disappearance, or owner waiver;
- the safety journal, recovery copy, shared generation, independently evaluated global
  enabled bit, complete canonical-room denylist, latest per-room add/remove provenance,
  and audit are current and mutually consistent; a room removal remains `PREPARED` with
  its entry present until the same live incarnation's one-use permit authorizes conditional
  promotion; neither a recovered/empty application store nor a generation change alone
  proves that a relaxation is safe;
- no pending/newer applicable `G`/`Q[R]` guard, cleanup failure/retry, ambiguous transition,
  or late response from an in-flight relaxation exists; the relaxation captures one exact
  predecessor and never rebases. Global enable reaches `COMMITTED` by conditional recovery-
  head update and matching read-backs before the same incarnation's final activation;
  room removal instead uses one atomic local check to mint/consume its non-restorable
  permit and issue the conditional promotion that removes the room;
- the relevant tabletop has fresh successful evidence;
- every applicable Critical/High residual risk has an individual owner decision with
  date, scope, compensating controls, review date, and disable owner; and
- the repository owner has recorded approval for the exact global-enable or named-room-
  removal decision, after which a fresh, non-restored, separately audited admin recovery
  authentication performs only that technical transition.

Any failed or missing global item leaves the global state disabled; a failed or missing
room-removal item leaves that canonical room in the denylist and cannot widen service. Neither the repository
owner nor admin may waive a platform or rights-holder restriction. A successful global
enable preserves every denylist entry; a successful removal preserves the global bit and
all other entries and does not start the removed room. Every process restart requires a
fresh committed global-enable transition and current-incarnation activation even if the
durable bit says enabled. A room-removal proposal that lost its permit or never promoted
must be freshly owner-approved and retried; global activation, reconciliation, or an old/
late response never removes its still-durable entry.

## Payload-free audit contract

`CTRL-AUDIT-PAYLOAD-FREE` records only the minimum control evidence. The conceptual
fields below are stable content requirements, not a schema:

| Field | Allowed content |
| --- | --- |
| Event identity/time | Random audit event reference; occurrence and recorded timestamps. |
| Actor/control | Restricted pseudonymous actor reference, actor role, control ID, requested action, authorization result, and result code. |
| Target | For a denylist action, an opaque reference bound to the exactly verified canonical room; for deletion, exactly one typed room/session selector kind and opaque target/export reference. Identity deletion/revocation records only an opaque checkpoint-manifest reference and count, never its account/device target ID, event body, email, public key, bearer, or user-facing content. |
| Safety transition | Explicit action kind and scope; transition identity; `PREPARED`/`COMMITTED` outcome; prior/result generation and head digest; prior/result global bit; affected-room membership, latest add/remove provenance, and preserved orthogonal/non-target state; serving incarnation plus captured/final `G`/`Q[R]` guard result; non-restorable global activation or single-use room-removal permit installed/consumed/denied/superseded result; stable reason code. |
| Incident/deletion/identity control | Opaque incident/manifest reference, intake-continuity epoch plus predecessor/high-watermark and open/clean-close/pending/tainted result, immutable original initiating-request time, provisional-containment result, durable intake/tombstone or identity-checkpoint/denial commit/read-back and acknowledgement result, deletion state when admitted, payload-free store counts, retry count, completion timestamp, and immutable `sla_breached` result where applicable. |
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
| 3 | Reset to an approved globally-off predecessor, write a `PREPARED` global enable, conditionally commit/read back its recovery head, and inject global disable before and after both that durable CAS and the final current-incarnation activation CAS. | If disable commits first, enable's exact-predecessor CAS fails and is not rebased. If enable commits first but disable wins the local fence, committed enable never activates and disable reapplies to the newest head. If enable activates first, disable immediately revokes activation and cleans. Every order ends off; durable commit and local serving effect are not falsely described as atomic. |
| 4 | Let the winning disable transition commit/read back; observe the losing or superseded enable and delay its response. | Disable changes only the global bit and preserves the denylist. The enable remains prepared-only or committed-but-not-activated; its late response cannot install activation. Cleanup completes/retries while every further relaxation waits for reconciliation. |
| 5 | Separately crash after enable prepare; after enable recovery-head commit but before read-back/final activation; after disable's local latch but before its durable commit; after split journal/recovery writes; and after commit/activation but before either response. Also race `clean-close(E)` against global disable and `add(B)` in both orders, including failed tightening durability followed by process exit. | Every restart creates a new incarnation with no activation and rejects old leases/output. Prepared/split/unknown state remains off. An exact committed tightening is reused or replayed; a committed global enable from the dead incarnation is durable history only and requires a fresh transition/activation. If tightening is accepted first, close waits for its durable reconciliation; if close wins the atomic ingress fence, the action is rejected or bound to a new verified epoch. No late action, retry, or response crosses a closed epoch, clears a latch/block, or activates an old result. |
| 6 | Attempt a platform reconnect and a worker frame from the revoked lease. | Both are denied under the current generation. No credentialed/alternate platform fallback or audio retry queue is created. |
| 7 | Inspect audit content. | The explicit global-disable action, prior/result global bit, preserved denylist, generation, result, and integrity metadata exist; no content, secret, locator, transcript, or audio appears. |

**Pass result:** Future disclosure and publication are stopped, recovery-copy failure
cannot fail open, slow or unavailable durability cannot defer active cleanup, and the
record does not claim RAM/durable atomicity or that an untrusted worker erased RAM. A
committed global enable without current-incarnation activation never serves; room-removal
ordering is exercised separately in Tabletop 1B.

### Tabletop 1B: canonical-room denylist add without global side effects

**Setup:** In an isolated test design, the global bit is enabled, canonical room `A` is
active with one platform session and lease, and unrelated canonical room `B` is eligible
but inactive. Neither room is denied. Capture both rooms' state and the current generation.

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | While `A` is active, an operator starts an exactly resolved `add(B)`, holds its durable I/O pending within the control deadline, then advances the shared generation and verifies the journal/recovery read-back. | From pending through committed state, only `Q[B]` and then membership of `B` change. `B` starts/reconnects are denied and the epoch cannot cleanly close, but `A`'s global activation, platform session, lease, audio/locator RAM, and pending publication are untouched. The global bit remains enabled and `B` is not started. |
| 2 | Reset the isolated case, make `A` active again, and add exactly resolved room `A`. | Before or concurrently with durability, `A` is provisionally blocked and only `A`'s platform session, lease, late output, locator/audio, and pending publication are stopped/cleared. Commit/read-back decides whether scoped success may be reported; `A` reconnect is denied and unrelated `B` remains otherwise unchanged. |
| 3 | Inspect both transition audits and re-evaluate unaffected rooms. | Each audit proves the explicit action, canonical binding, prior/result global bit and target membership, preserved non-target state, generation, and integrity result. A generation change alone triggers re-evaluation, not cleanup or automatic start. |
| 4 | Separately inject alias ambiguity, changed room binding, stale safety state, and journal/recovery-copy write or read-back failure. | No room-scoped success is reported. Each variant escalates to local global off, immediately issues all-room cleanup without another durability await, emits a payload-free failure-stage/escalation audit, and blocks every relaxation pending reconciliation. |
| 5 | Race global disable and `add(B)` from the same predecessor in both durable-CAS orders; also lose the response after a verified `add(B)` and retry it. | At most one successor commits for that predecessor, but the losing tightening is not lost: it latches first, reloads the winner's complete snapshot, and commits its same safe action at the next generation. Response-loss retry reuses the verified add; unverifiable scope never reports room success and escalates globally. |
| 6 | Globally disable, then commit/activate global enable while `B` remains denied; separately prepare `remove(B)` while off. Reset with `A` denied and race `remove(A)` against `add(A)`, global disable, and deletion intake before/after the atomic permit mint/consumption and promotion dispatch. Force the final guard to fail; crash before dispatch; crash after dispatch with the result unknown; perform fresh global enable only after reconciliation; and lose the response after a verified permitted promotion. | Global enable does not remove `B`; remove does not enable/start it. Failed guard, lost/prior-incarnation permit, or crash before dispatch leaves the room byte-for-byte present. After dispatch, all safe guards apply immediately: if removal wins the recovery-head compare-and-swap, a safety tightening reloads/replays against that head and deletion keeps its selector block; if a same-head tightening wins, removal fails without rebasing and `R` remains. An unknown/split result remains globally off until exact read-back proves either permitted `COMMITTED` removal or unchanged membership, so fresh global enable cannot guess. Verified-promotion response loss reuses the durably successful removal. Unrelated rooms retain their prior active state unless failure escalates globally. |
| 7 | With no denylist entry, test initial offline, normal broadcast end, and reconnect still offline; then make the room live and re-run all gates. Separately test a missing/stale prerequisite and an authorized exact-room policy/rights/safety incident. | Ordinary offline/end stops or rejects only the attempt/current session and performs normal teardown; journal, generation, global bit, and denylist remain byte-for-byte unchanged, and the later live attempt needs no removal approval. A missing/stale prerequisite denies the action and triggers review without automatic add. Only the explicit verified incident enters this `add(R)` procedure; unknown/platform-wide scope invokes global disable without guessing an entry. |

**Pass result:** A pending or successful `add(B)` leaves active unrelated `A` untouched,
while a successful `add(A)` contains only `A`; both preserve the global bit. A classified
failure invokes separate global disable, and a generation change by itself causes re-
evaluation rather than cleanup. Transient offline/end and missing prerequisites never
silently become durable denylist decisions.

### Tabletop 2: room-or-session takedown with one failed object deletion

**Setup:** Commit/read back `open(E)` before deletion ingress, then run room and session
subcases through a durable takedown/incident intake and a tombstone-capable independent
recovery copy. Room `R` initially has sessions `S1`/`S2`,
and a stale backup later reveals `S3`; another room is unrelated. The session subcase
selects `S1` while `S2` shares room-level projections. Each selected scope has normalized
rows, cache/index entries, an encrypted raw object, and a managed export. Inject primary
safety-store unavailability, recovery-copy commit/read-back failures, crashes on both
sides of verified commit, and one selected raw-object deletion failure; advance simulated
time beyond 24 hours before the raw-object retry succeeds.

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | With current-incarnation activation installed, submit room/session plus none, both, ambiguous, unknown, and conflicting parent-hint/index inputs. Separately reset globally off and race the same cases against global enable. | In the active case, valid intake installs only its verified selector block, and a session request leaves `S2` plus unrelated scope available; durable invalid denial clears pending without changing activation or starting tombstone/purge. In the race, intake first fences out enable's final CAS without revoking any prior activation; enable first installs activation, after which intake blocks only its target. Only credible unbounded hazard or failed scoped containment escalates globally. |
| 2 | With the primary application/safety store unavailable, assign the immutable original initiating-request time and atomically write/read back it with selector/idempotency in the durable intake; then commit/read back the typed `hidden` tombstone in the independent recovery copy. | The unresolved intake retains the same selector/idempotency/time triple across the admission barrier but is not a deletion state or purge authority. The tombstone must reuse that time. After tombstone read-back, and only then, the request is accepted, `hidden` is reportable, and purge may begin; the application-store outage keeps global off until later reconciliation. Audit/intake alone is not admission. |
| 3 | In separate attempts, fail `open(E)` commit/read-back; after a verified open, fail exact-intake durability, invalid-request denial durability, scoped-containment proof, or tombstone commit/read-back after durable intake; and crash before verified tombstone commit. Let the initiating client disappear, restart with an empty application view, and attempt re-enable. | A failed/ambiguous open never exposes deletion ingress. Each later accounting/admission or isolation failure produces no success, reportable `hidden`, purge, or clean close; it taints the live guard, revokes global activation, and expands cleanup globally. After crash, unmatched `open(E)` remains recovery-visible even when the target record is absent, so the new incarnation stays off without relying on client retry. Exact authoritative replay must recover/admit or durably deny the request; absent it, production remains off. |
| 4 | Let recovery-copy tombstone commit succeed, lose its response, and crash before acknowledgement; retry the same intake after restart. Then quiesce ingress and race a late authenticated request against `clean-close(E)` in both orders, including close write/read-back failure. | Retry discovers and verifies the same tombstone, identity, selector, and original time. It neither duplicates/resets the target nor installs serving activation. If the request linearizes first, close waits for durable denial or verified tombstone reconciliation; if quiescence wins, the request is rejected or waits for a new verified epoch. Failed, stale, cross-epoch, or ambiguous close remains unmatched, and a new epoch opens before any later ingress/activation. |
| 5 | Purge all enumerated active stores with the raw-object failure injected. | Room scope covers room metadata plus `S1`/`S2`; session scope covers only `S1` and recomputes shared projections without exposing `S1` or deleting/hiding `S2`. Successful stores stay purged; the failed store records only an error code/count; completion is forbidden. Because target isolation remains proven, the failure stays scoped and unrelated activation is not revoked. |
| 6 | Retry the same manifest after the 24-hour deadline and verify all active stores. | The raw object is removed; the state becomes `active-purge-complete` with the original request time, a completion timestamp, and immutable `sla_breached=true`. |
| 7 | Evaluate exports and backups while their declared windows remain open. | Managed access is revoked and the target stays replay-protected, but `final-retention-window-satisfied` is withheld and retained copies are reported truthfully. |
| 8 | Restore the stale backup containing late `S3`; test both `session(S1)` then `room(R)` and `room(R)` then a later `session(S1)` request; expire/verify every window. | Pending `hidden` replay precedes safety reconciliation and room replay discovers/purges `S3`. In both orders the room tombstone remains dominant: the child manifest links without narrowing/overwriting the room block, resetting evidence, or reviving `R` metadata/`S1`/`S2`/`S3`. A standalone session tombstone affects only its session. Mapping conflicts stay isolated/off; final state waits for post-window verification. |

**Pass result:** Both typed selectors enforce their exact scope; ordinary valid intake and
durably denied invalid intake preserve existing non-target activation, while admission/
accounting or isolation failure alone taints and revokes it. Provisional containment is
immediate but the three-state machine admits only a committed/read-back `hidden`
tombstone; failures, ambiguous responses, both crash windows, restart, restore, and early
re-enable cannot fail open. An unmatched continuity epoch preserves an off-state blocker
even when a pre-durable target cannot be recovered; it never invents a deletion state or
relies on the client. Invalid/composite inputs cause no guessed deletion, room retries/
restores discover all room sessions and dominate narrower child tombstones, session
deletion preserves siblings/shared state, and scoped partial/late deletion is truthful.

### Tabletop 3: restore stale enablement, deleted data, and revoked identity

**Setup:** Restore an application-data backup whose generation is older, whose global
setting says enabled, whose denylist is stale, and whose rows include both a room-wide
tombstone target (with a late restored child session), an exact-session tombstone target
with a preserved sibling, and an account/device deleted after that backup. It also
contains apparently unexpired magic-link, enrollment-token, session-verifier/session
rows, a stateless token signed by the old key version, and the deleted subject's roles/
invites/device statistics. In the old incarnation, also accept a valid account/device
action, stop its authority, and crash before its checkpoint; accept an invalid or
unauthorized identity action whose durable denial fails. The separate recovery copy
contains the newer forced-off global bit and complete denylist under one generation, a
durable unresolved valid deletion intake plus pending `hidden` typed room/session
tombstones with dominance, existing typed pseudonymous account/device checkpoints, a prior
unmatched intake-continuity epoch, and newer auth-invalidation generation/key version.
Authoritative ingress replay contains the unresolved identity actions and an invalid
deletion request whose denial previously failed.

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | Boot the restore in isolation. | Startup creates a new never-reused incarnation without activation, ignores backed-up enablement, and stays off before any viewer, ingest, worker, callback, or scheduled-job traffic. |
| 2 | Verify and load the separate recovery copy; separately inject a missing, tampered, rolled-back, or conflicting copy. | A copy whose authority/integrity/freshness cannot be proved terminates that activation attempt without replay, close, or traffic and remains isolated/off for repair. With the trusted copy, prepared/committed state, the unmatched epoch, unresolved controls, pending tombstones, existing identity checkpoints, orthogonal snapshot, and auth state are recognized. The unmatched epoch is a blocker that preserves quarantine and drives the next offline replay; it does not terminate reconciliation, and empty application state proves nothing absent. |
| 3 | Fence the old owner and replay the trusted epoch's authoritative safety, deletion, and identity-control ingress through its exact high-watermark, including the crash-before-checkpoint and failed-denial cases. | Each accepted safety handler reaches a durable outcome; the valid deletion recovers its exact selector/idempotency/original-time tombstone and the invalid deletion its denial; the valid identity action recovers its typed checkpoint and the invalid/unauthorized action its durable denial. Missing/incomplete replay remains isolated/off, leaves the epoch unmatched, and performs no guessed close or activation. |
| 4 | Apply the reconciled tombstones and account/device checkpoints; purge/revoke restored verifier/session rows, reconcile the protected auth generation/key version, and probe old credentials and exact scopes. | No purge precedes valid deletion admission, and no target is invented for an invalid request. Room replay purges every restored child; session replay preserves its sibling; room dominance holds. Every stateful/stateless pre-restore credential is server-rejected, old key material cannot become current, and scoped deleted/revoked account/device authority cannot authenticate or receive new authority before safety reconciliation. |
| 5 | Reconcile prepared/committed safety outcomes, shared generation, global bit, and complete denylist while every old continuity epoch remains quarantined. | Stale backup state cannot overwrite the current head. Prepared global enable never serves; unpromoted room removal still has its entry, and no prior-incarnation permit is reusable; prepared tightening replays. Global enable cannot clear a room entry, removal cannot enable globally, and generation alone creates no activation. Any unmatched epoch, gap, binding conflict, or mismatch remains off for the explicit close step. |
| 6 | Attempt `CTRL-REENABLE-GATE` early; then, after replay/application/safety reconciliation, clean-close the old epoch, open a new epoch, and evaluate a fresh activation using a non-restored audited recovery admin. Inject stale/cross-epoch/failed close and a claimed zero-event epoch without authoritative proof. | Every early or faulty-close attempt is denied and the old epoch remains unmatched/off. Only exact high-watermark completeness, including every checkpoint and denial, permits verified `clean-close(E)` for the old epoch; even zero events require authoritative proof. Only after every old epoch is sealed may a fresh `open(E)` commit/read back, followed by a fresh exact-head global enable and separate current-incarnation activation. No close, replay, old commit/response, restored admin session, or global bit activates traffic or clears the denylist. |

**Pass result:** Stateful/stateless pre-restore credentials remain server-rejected. A bad
recovery copy aborts activation, while a trusted unmatched epoch preserves quarantine and
continues authoritative offline replay. Safety, deletion, and identity-control outcomes
reconcile; tombstones/checkpoints apply before orthogonal safety reconciliation; old epochs
clean-close only from exact high-watermark proof; and a new epoch plus fresh activation
follow in that order before traffic. Neither empty application state, an old enabled value/
denylist or committed relaxation, a restored admin session, nor deleted identity/device
authority becomes current-incarnation serving authority.

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
canonical binding, exact-predecessor relaxation, tightening reapplication, local
current-incarnation activation/revocation, cleanup, and noninterference; Issue #11 owns
immediate room/session-scoped provisional visibility containment, sibling/non-target
noninterference, and escalation when that containment cannot be proven; Issue #16 owns
prepared journal records,
conditional committed recovery-head updates, pre-promotion one-use room-removal permits,
append-only open/clean-close safety/deletion/identity-control intake-continuity and exact
high-watermark evidence, recovery-boundary intake/tombstone/checkpoint/denial commit/read-
back, idempotency, purge, and fault injection; Issues #12/#13 own exact account/device
cascade, target-authority stop, restored-credential rejection, and typed-checkpoint replay;
Issue #17 owns admin request/acknowledgement, pending-before-effect semantics, durable
invalid/unauthorized denial without target mutation, tainted failure revocation, unresolved-
intake replay/status, late-response non-authority, and relaxation blocking;
and Issues #4/#19 own new-incarnation default-off, clean shutdown, crash/restart/restore,
and pre-traffic replay drills. Their evidence must cover successful session/room admission
and durable invalid denial preserving non-target activation; identity pending/high-
watermark before authority stop/checkpoint, valid checkpoint and invalid/unauthorized
denial, crash before checkpoint, and checkpoint/denial failure; intake/denial/tombstone
write failure revoking activation; lost scoped-containment proof, client loss, bad-copy
activation abort versus trusted-unmatched offline replay, unmatched/stale/cross-epoch close,
prepare/commit/read-back split, global-enable crash before and after local
activation, room-removal final-guard/permit failure, crash before dispatch, crash after
dispatch with unknown outcome, both exact-head CAS winners, old/late
responses, empty application state, room-add ambiguity/staleness/write failure, both
enable/disable and remove/add/intake orders, fresh global enable after a failed removal,
and early re-enable without defining Issue #2 runtime schema or wire fields.
