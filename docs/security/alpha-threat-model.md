# Alpha threat model

- Status: **Proposed — repository-owner ADR and residual-risk decisions pending**
- Date: 2026-08-24
- Scope: GitHub Issue #2 and the Alpha design in
  [ADR 0001](../architecture/adr/0001-alpha-modular-monolith.md)
- Review trigger: before any production enablement, at least every 90 days for the
  platform/rights boundary, and after any architecture, acquisition, policy, ownership,
  processor, authentication, key, dependency, or product-use change

## Current assurance state

This is a documentation-only threat model. A control described as “required” is a
requirement for a later Issue, not a statement that code, infrastructure, monitoring, or
an operational process exists. Runtime evidence must be attached to the owning Issue.

| Capability | Required state at this revision |
| --- | --- |
| Production ingest | **OFF** pending ADR approval, platform/rights evidence, safety and incident controls, and individual High/Critical decisions. |
| Community-worker input | Synthetic frames only. Production real PCM is **OFF** because `RISK-WORKER-AUDIO-RETENTION` is High and **NOT ACCEPTED**. |
| Production normalized/raw persistence | **OFF** pending Issue #16 controls, source-specific purpose/retention evidence, deletion/recovery evidence, and applicable risk decisions. |
| Managed raw export | **OFF** pending Issue #16. Untracked local plaintext export is prohibited. |
| Restarted/restored authentication and traffic | **OFF** until any orphaned serving-incarnation guard and prepared/ambiguous relaxation are reconciled, every restored stateful/stateless credential is rejected, deletion/revocation checkpoints replay, safety state reconciles, and a fresh non-restored admin recovery authentication plus current-incarnation activation passes. |
| Owner approval | **PENDING** for the ADR and for every individually listed Critical/High residual. No blanket approval is valid. |

## Method and decision semantics

The register covers confidentiality, integrity, availability, authorization, safety
control, data-lifecycle, platform, and software-supply threats across every trust
boundary. “Residual” means the expected severity only after every listed preventive,
detective, and response control has executable or operational evidence. It is not a
claim about the current repository.

| Residual | Meaning | Decision rule |
| --- | --- | --- |
| Critical | Catastrophic or system-wide harm remains plausible after controls. | Production is blocked until the repository owner individually accepts the named scope or the design removes it. |
| High | Serious confidentiality, integrity, rights, deletion, or safety harm remains plausible after controls. | Production is blocked until the repository owner individually accepts the named scope with compensating controls, review date, and disable owner. |
| Medium | Bounded harm remains and the planned controls can detect, contain, and recover it. | No exception is recorded here; all controls and evidence remain mandatory before the affected capability is enabled. |
| Low | Limited harm remains with routine detection and recovery. | Controls remain mandatory; no exception is implied. |

`NOT ACCEPTED` means no person or role has accepted the risk. The application `admin`
role cannot accept governance risk. Only the repository owner may do so, and approval of
the ADR or a pull request is not by itself an individual residual-risk acceptance.

## Assets

| Asset ID | Asset | Required protection |
| --- | --- | --- |
| `ASSET-SECRET` | Bilibili/platform, Postgres, Bucket/archive, Resend/email, encryption, deployment, and signing credentials; session/enrollment bearers; cookies; playback locators | Backend-only or intended one-time recipient; least privilege; redacted; never sent to browsers or workers except the intended auth bearer flow. |
| `ASSET-AUDIO` | PCM, encoded audio, audio base64, stream buffers, and audio-bearing derivatives | At most 30 seconds of monotonic media time in bounded RAM; zero persistence; clear on every stop/lease/session path. |
| `ASSET-PROTOCOL` | Worker identity, signature, version, manifest, lease, epoch, sequence, revision, frame, transcript, and health state | Authentic, current, session-bound, bounded, replay-resistant, and backend-authoritative. Wire details remain Issue #3. |
| `ASSET-SAFETY` | Orthogonal global enable state and canonical-room denylist under one monotonic safety generation, recovery-visible serving-incarnation continuity guard, prepared relaxation proposals, non-restorable current-incarnation activation capability, owner approvals, and emergency-disable result | Recovery records are integrity protected, rollback resistant, held outside application backups, and default off; the activation capability is intentionally process-local and non-restorable. A prepared relaxation is not current, a committed enabled snapshot alone cannot admit traffic, and an orphaned/unsealed continuity guard quarantines every traffic class. Global transitions affect all rooms while a successful room transition affects only its canonical target. |
| `ASSET-NORMALIZED` | Normalized events, transcript, room/session metadata, and authorized history | Restricted by default; field/source-purpose and publication controls; deletable by exactly one canonical-room-all-sessions or immutable-session-only selector. |
| `ASSET-RAW` | Sanitized raw business payloads, manifests, encryption metadata, and encrypted archive objects | High-risk, private Bucket only after Issue #16; no ordinary API path; authenticated encryption and admin-only managed access. |
| `ASSET-IDENTITY` | Invite/account email and role, worker device public key/status, minimal account/device state | Minimum necessary data; subject/admin or contributor-own access; revocable and deletable. |
| `ASSET-AUDIT` | Payload-free security, control, raw-access, and deletion audit records | Append-only and integrity protected; no secret/event/audio/transcript/direct identity fields; restricted pseudonymous actor or manifest references only where required for accountability. |
| `ASSET-DELETION` | Durable deletion intake with immutable original initiating-request time, exactly-one typed room-or-session `hidden` tombstones, unresolved admission blockers, typed pseudonymous account/device deletion/revocation checkpoints, active-purge state, backup-window state, and SLA-breach result | Exact-scope, idempotent, commit/read-back verified before acknowledgement or purge, and replayable before restored traffic; encrypted, narrowly authorized, access-audited, and protected against clock reset, crash, response loss, ambiguity, rollback, or omission. A pre-armed recovery-visible continuity guard preserves a coarse no-reopen fact if exact intake durability and both initiating-source/backend continuity are lost; it is not a tombstone, deletion state, SLA clock, or purge authority. |
| `ASSET-RIGHTS` | Current platform terms, acquisition channel, source/rights-holder permission, worker-disclosure basis, output-use decision, takedown contact | Authoritative, dated/versioned, reviewed at least every 90 days and on change; ambiguity disables the path. |
| `ASSET-BUILD` | Source, dependencies, lockfiles, CI results, artifacts, deployment identity, and maintainer authority | Reviewable provenance, least privilege, reproducibility, protected release path, and no prohibited AGPL/mixed/unclear copying. |
| `ASSET-AVAILABILITY` | Emergency disable path, serving-incarnation continuity, ingest, live publication, deletion execution, and recovery capability | Disable must work independently of ingest; failures fail closed; an unreconciled coarse quarantine may sacrifice availability but never becomes deletion evidence or mutates an unrelated room's durable scope. |

## Actors and entry points

| Actor ID | Actor and trust assumption |
| --- | --- |
| `ACT-PUBLIC` | Anonymous internet user, bot, or attacker; untrusted. |
| `ACT-ACCOUNT` | Invited viewer or contributor; authenticated identity does not make input or rendering trusted. |
| `ACT-WORKER` | Invited community-worker operator, compromised worker, malware, or modified client; untrusted for confidentiality, integrity, and availability. |
| `ACT-PLATFORM` | Bilibili endpoint, content owner, or changed platform behavior; external and mutable. |
| `ACT-PROVIDER` | Managed Postgres, Bucket, backup, email, or hosting provider and its failure modes. |
| `ACT-PRIVILEGED` | Operator, admin, maintainer, or compromised privileged account; actions still require least privilege, separation, and audit. |
| `ACT-SUPPLY` | Compromised dependency, build tool, CI action, package registry, model, dataset, or release artifact. |

| Entry ID | Entry point |
| --- | --- |
| `ENTRY-BROWSER` | Public/viewer/admin HTTP, realtime, rendering, auth, and control surfaces. |
| `ENTRY-BILIBILI` | Canonical-room resolution, redirects, playback connection, metadata, danmaku, SC, status, and business events. |
| `ENTRY-WORKER` | Enrollment, authentication, lease, control/PCM frames, heartbeat, transcript, health, timeout, and disconnect paths. |
| `ENTRY-AUTH-EMAIL` | Invite creation, Resend request/delivery, magic link, session cookie, worker enrollment token, and device registration. |
| `ENTRY-DATA` | Postgres, private Bucket, caches, indexes, replicas, object versions, managed exports, and audit interfaces. |
| `ENTRY-DELETION-RESTORE` | Serving-incarnation continuity guard, durable deletion intake, typed room/session selector parsing and authoritative resolution, tombstone admission/acknowledgement, crash and response-loss retry, takedown, deletion retry, identity/device revocation, bearer invalidation, `PREPARED`/`COMMITTED` relaxation, current-incarnation activation, checkpoint replay, application backup, restart/restore, and re-enable process. |
| `ENTRY-MAINTENANCE` | Issue #4 migration/deletion/recovery job, runbook, temporary credential, and mutual-exclusion mechanism. |
| `ENTRY-CI-DEPLOY` | Source review, dependency resolution, CI, artifact publication, secret injection, deployment, model, and dataset intake. |

## Minimum role matrix

Authorization defaults to deny. This matrix is a design requirement for Issues #12,
#13, and #17, not an assertion that the roles are implemented.

| Actor/role | Permitted actions after the owning Issue lands | Explicitly prohibited |
| --- | --- | --- |
| Anonymous viewer | Read only an approved normalized public live surface. | History/statistics, ingest, worker registration, raw/identity/secrets, and control state. |
| Invited viewer | Anonymous-viewer access plus authorized normalized history after Issues #12/#17. | Worker/statistics management, room control, raw access, and global/denylist/role control. |
| Contributor | Invited-viewer access plus that contributor's own aggregate statistics after Issues #13/#17. | Device administration or registration-token issuance, room control, raw access, global enablement, denylist removal, and role administration. |
| Operator | Select, start, and stop an eligible room; add a canonical room to the denylist; invoke global emergency disable. | Global re-enable, denylist removal, raw export, deletion completion, and role/key/device administration. |
| Admin | Operator actions plus role/invite/device control, deletion requests, separately audited managed raw export, audited denylist removal, and technical re-enable after governance gates pass. | Bypassing owner risk/policy approval, exposing raw through ordinary APIs, overriding platform restrictions, or claiming external plaintext erasure. |
| Repository owner | Human governance approval for ADRs, source/rights basis, production global enablement, and each Critical/High residual. | This is not an application role and grants no implicit production credential, raw-data, database, Bucket, or deployment access. |

An operator/admin disable or denylist-add is always allowed to reduce exposure. A less
privileged or stale decision cannot override a newer safety generation. Admin technical
re-enable and denylist removal require a recorded repository-owner governance decision.

## Required control catalog

Every item below is **planned/required**, not implemented by Issue #2.

| Control ID | Requirement | Later evidence owners / integration dependencies |
| --- | --- | --- |
| `CTRL-AUTHZ-DENY-BY-DEFAULT` | Authenticate where required and authorize every object/action against the minimum role matrix; repository-owner governance remains out of band. | Issues #12, #13, #16, #17 |
| `CTRL-DATA-RESTRICTED-DEFAULT` | Treat every class as restricted unless a current per-source/per-field record approves purpose, audience, retention/review, and deletion trigger. | Issues #10, #12, #13, #16, #17 |
| `CTRL-SECRET-CONTAINMENT` | Least-privilege, backend-only service secrets; in-memory playback locators; redaction; rotation/revocation; no worker/browser/store leakage. | Issues #4, #7, #12, #16, #19 |
| `CTRL-SAFETY-DEFAULT-OFF` | Start every process and restore globally disabled with no reusable activation capability, ignoring backed-up enable state. Before any traffic, durably open/read back a serving-incarnation continuity guard bound to the current generation and one live authority. Only that authority's non-restorable capability may admit traffic; a missing, unsealed-orphaned, ambiguous, or unsealable guard quarantines authentication, viewer/history/publication, ingest, worker, export, persistence, callback, and maintenance traffic until authoritative replay proves continuity. | Issues #4, #7, #16, #19 |
| `CTRL-SAFETY-GENERATION` | One monotonic generation orders an append-only journal and integrity-protected recovery snapshot containing an orthogonal global enable bit and complete canonical-room denylist. Enable/remove first writes and reads back a predecessor-bound `PREPARED` proposal under an opaque proposal identity; preparation is not current and does not advance the generation or authorize traffic/recovery. Only successful conditional promotion to `COMMITTED` advances the one generation. A `COMMITTED` enabled snapshot still requires the same live incarnation's non-restorable activation capability, minted only by the final local check-and-effect. An ingest-independent guard family separates global `G` from room `Q[R]`: global disable increments `G`, revokes global activation, and starts all-room cleanup, while pending or committed `add(R)` increments only `Q[R]`, blocks/cleans `R`, invalidates only its removal, and preserves unrelated-room activation. Scope-labelled pending entries prevent clean sealing but do not themselves widen runtime effect. A failed/ambiguous add invokes a distinct global-disable transition; after process loss, an unsealed/orphaned continuity guard globally quarantines recovery. A generation change reloads/re-evaluates state; it does not itself imply global cleanup. | Issues #4, #7, #16, #17, #19 |
| `CTRL-ROOM-DENYLIST` | Resolve aliases/URLs and active-resource bindings to canonical room ID before eligibility. A pending-in-deadline or successfully committed add blocks/cleans only the matching room and preserves unrelated rooms; add failure/ambiguity explicitly escalates through global disable. Global enable preserves the list and removing one room does not enable global ingest. Ordinary offline/ended live status is transient: stop or reject only that start/reconnect, without adding the room, advancing the generation, or requiring owner-gated removal. | Issues #7, #16, #17 |
| `CTRL-DISABLE-CLEANUP` | Apply cleanup at the verified effective scope: Alpha uses one active serving authority process, and global disable first revokes its live activation capability, closes its gates, and starts every active/queued-room cleanup before any journal/recovery-copy await, so slow, hung, or failed durable I/O cannot extend disclosure; a pending or successful denylist add rejects/stops only matching-room starts/reconnects, platform session, lease, conforming audio/locator RAM, and pending publication, with unrelated-room noninterference until a classified add failure invokes separate global disable. Future multi-owner guard/ack uncertainty isolates the owner and fails globally. | Issues #7, #8, #11, #14, #15, #16, #17, #19 |
| `CTRL-RESTORE-REPLAY` | Reject restored stateful/stateless credentials; reject every prepared/ambiguous relaxation and any committed enable lacking a freshly reconciled current-incarnation activation capability; quarantine an orphaned/unsealed serving guard; reconcile every continuity failure against authoritative ingress replay, admitting each unresolved valid deletion intake to a verified replayable tombstone and reproducing durable denial for each invalid request; replay current deletion/revocation checkpoints; and reconcile the complete global/denylist snapshot before accepting any authentication, viewer/history/publication, ingest, worker, export, persistence, callback, or maintenance traffic. | Issues #4, #12, #13, #16, #19 |
| `CTRL-IDENTITY-RESTORE-REVOCATION` | Keep typed pseudonymous account/device checkpoints and an auth-invalidation generation/key version outside application backups; reject every pre-restore credential and prevent deleted authority from being reissued before traffic. | Issues #4, #12, #13, #16, #19 |
| `CTRL-REENABLE-GATE` | Admin technical global re-enable or exact-room removal only after remediation, current evidence, tabletop, recorded owner approval, authoritative replay of every unresolved deletion intake/continuity hazard, successful reconciliation or clean sealing of any prior serving-incarnation guard, and rejection of every prepared/split/ambiguous relaxation. Enable preserves the denylist, removal never enables global ingest, neither starts a room automatically, and neither admits traffic without the fresh current incarnation's non-restorable activation capability. | Issues #7, #16, #17, #19; repository owner decision |
| `CTRL-AUDIT-PAYLOAD-FREE` | Append actor/action/result/time/object class/generation/integrity metadata without event, email, secret, locator, audio, transcript, or unsafe digest. | Issues #12, #13, #16, #17, #19 |
| `CTRL-WORKER-SYNTHETIC-ONLY` | Send only synthetic frames unless the separate real-PCM rights and High-risk gates pass. | Issues #8, #9, #14, #15; repository owner decision |
| `CTRL-WORKER-PROTOCOL` | Accept only bounded versioned ASR messages and allowlisted manifests; verify identity/signature/version/lease/epoch/size/rate/timeout; no arbitrary execution/download fields. | Issues #3, #13, #14, #15 |
| `CTRL-WORKER-REVOCATION` | Reject invalid or late output, revoke the lease/device as appropriate, quarantine results, and prevent reconnect after disable/denylist. | Issues #13, #14, #15 |
| `CTRL-AUDIO-RAM-ONLY` | Enforce media-time, 960,000-byte room/session and lease, one-room/one-lease, 16,777,216-byte process ceilings; no retry queue or persistent/log/crash/fixture path; clear on every terminal path. | Issues #3, #8, #14, #15 |
| `CTRL-PLATFORM-FAIL-CLOSED` | Only operator/admin-selected, canonical, free, anonymous, current-live, unrestricted, rate-compliant acquisition; stop on ambiguity/change/restriction with no fallback. A normal offline/ended result denies only the current attempt and is never persisted as a denylist decision; room/global safety changes require their separate policy, rights, or incident trigger. | Issues #7, #10, #19 |
| `CTRL-PLATFORM-RIGHTS-REVIEW` | Record exact official source/version, channel/applicable agreement, purpose, rights for worker disclosure/retention/output, takedown contact, and 90-day/change review. | Policy owner and repository owner before Issue #7 production use |
| `CTRL-SSRF-RESOLUTION` | Allowlist scheme/host/port and acquisition family; canonicalize and revalidate every redirect/DNS target; block private/link-local/metadata networks; bound requests. | Issues #7, #19 |
| `CTRL-EVENT-VALIDATION` | Bound and validate schema, size, credential/audio fields, canonical session, and publication fields before normalization or temporary raw handling. | Issues #3, #7, #10 |
| `CTRL-RAW-BOUNDARY` | Reject/remove credentials, locators, excess identity, and all audio before compressed authenticated encryption in the private Bucket; fail without spill. | Issues #10 and #16 |
| `CTRL-RAW-EXPORT` | Admin-only per-access authorization/audit, 15-minute capability, encrypted managed object at most 24 hours, deletion revocation, no untracked plaintext. | Issues #16, #17 |
| `CTRL-DELETION-STATE` | Require exactly one selector and immediate provisional containment; atomically retain selector, idempotency identity, and immutable original initiating-request time in durable intake, then make the existing `hidden` tombstone reuse that triple and pass independent recovery-boundary commit/read-back before accepting/acknowledging the request, reporting `hidden`, or starting purge. Room scope covers all child sessions, session scope only its target, room tombstones dominate, and exact-scope cascade retains the three truthful states plus immutable late-SLA evidence. | Issue #16 |
| `CTRL-BACKUP-EVIDENCE` | Enumerate and evidence every cache, replica, object version, export, and backup window. Keep the current recovery-visible serving guard and every unresolved safety proposal/result outside application backups until reconciled; retain admitted room/session tombstones, unresolved admission blockers, identity/device checkpoints, and independent auth-invalidation state through every applicable window and one verified post-window restore. Never claim physical erasure or persist a process-local activation capability. | Issues #4, #12, #13, #16, #19 |
| `CTRL-DELETION-FAIL-CLOSED` | Before verified admission, containment is provisional and no deletion state/success is reported or purge started. A pending valid request blocks only its exact room/session scope, and a pending invalid selector starts no guessed purge; neither pending state revokes global activation. Verified tombstone admission continues only that exact-scope block, so sibling/unrelated serving needs no global re-enable. Durable invalid denial clears pending. Failed, timed-out, response-unknown, or unreadable intake/tombstone/denial persistence, or inability to install or prove the selected scope's containment/ownership, marks the epoch `tainted`, revokes global activation, and prevents clean sealing. Initiating-source loss plus backend crash then leaves an orphaned guard that globally quarantines recovery until authoritative replay replays the observed request: a valid request must recover/admit its exact selector/idempotency/time triple, while an invalid request must reproduce a durable denial. If the applicable proof cannot be recovered, quarantine persists. The guard is not `hidden`, a fourth deletion state, an SLA clock, or purge authority. After admission, a failed store stays scoped `hidden` while isolation remains proven; loss of that proof escalates globally, and unchecked completion is never reported. Volatile containment, an audit row, or an empty store is not a tombstone. | Issues #11, #16, #17 |
| `CTRL-RENDER-UNTRUSTED` | Treat normalized text/URLs as data, contextually escape, constrain links, and apply a restrictive browser policy; never render raw markup. | Issues #10, #11, #17 |
| `CTRL-AUTH-EXPIRY` | Enforce single-use and maximum bearer lifetimes, verifier-only storage, revocation, active-row purge, and server rejection of every pre-restore auth/enrollment credential without claiming client/email plaintext erasure. | Issues #12, #13 |
| `CTRL-AUTH-KEY-LIFECYCLE` | Use single-use bounded bearers, verifier hashes, revocable sessions/devices, key separation/rotation, and a recovery-protected monotonic auth-invalidation generation or key version whose current secret material is never restored and whose pre-restore versions never remain in the active verification set. | Issues #4, #12, #13, #16, #19 |
| `CTRL-MAINTENANCE-EXCLUSIVE` | Approved operation-specific runbook, mutual exclusion with serving authority, narrower temporary credentials, no serving/external flow, fail closed. | Issues #4, #16, #19 |
| `CTRL-SUPPLY-CHAIN` | Pinned/reviewed dependencies and actions, locked builds, provenance, protected release identity, secret isolation, model/dataset license gate, and clean-room license policy. | Issues #1, #4, #18, #19 and independent-implementation policy |
| `CTRL-INCIDENT-DISABLE` | Operator/admin can invoke an ingest-independent global disable; rotate/revoke, preserve payload-free evidence, purge where required, and require remediation/tabletop/owner review before re-enable. | Issues #17, #19 and incident runbook |

## Threat register

### Secrets, authorization, and data boundaries

| ID | Asset | Actor | Entry point | Preconditions | Preventive controls | Detection | Response | Control owner / dependency | Residual | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `THREAT-SECRET-DISCLOSURE` | `ASSET-SECRET` | `ACT-PUBLIC`, `ACT-WORKER`, `ACT-PRIVILEGED`, or `ACT-SUPPLY` | Any entry; especially logs/errors, `ENTRY-WORKER`, `ENTRY-AUTH-EMAIL`, `ENTRY-CI-DEPLOY` | A platform/email/archive/database credential, key, cookie, bearer, or playback locator crosses the wrong boundary or a privileged boundary is compromised. | `CTRL-SECRET-CONTAINMENT`, `CTRL-AUTH-KEY-LIFECYCLE`; diagram no-flows; never send service secrets/locators to browser or worker. | Secret scanning; redaction tests; provider/key access alerts; anomalous authentication/use; payload-free access audit. | Global/room disable as scoped; close platform session; revoke/rotate/invalidate; remove exposed managed objects; investigate and notify under the incident runbook. | Security and operations owners; Issues #4/#7/#12/#16/#19 | **High**: a recipient may retain a disclosed secret or use it before revocation. | **NOT ACCEPTED**; applicable production path OFF; see decision register. |
| `THREAT-RAW-IDENTITY-PRIVESC` | `ASSET-RAW`, `ASSET-IDENTITY`, `ASSET-NORMALIZED` | `ACT-PUBLIC`, `ACT-ACCOUNT`, compromised `ACT-PRIVILEGED` | `ENTRY-BROWSER`, `ENTRY-DATA` | Missing object/action authorization, confused role, direct store route, cache key mix-up, or admin action without separate audit. | `CTRL-AUTHZ-DENY-BY-DEFAULT`, `CTRL-DATA-RESTRICTED-DEFAULT`, `CTRL-RAW-BOUNDARY`, `CTRL-RAW-EXPORT`; ordinary APIs expose no raw data. | Denial/allow decision audit; authorization matrix tests; cross-role/object probes; raw-access alerts and reconciliation. | Deny and hide; revoke session/role; global disable or persistence/export disable; purge unauthorized cache/export; incident review. | Identity/API/data owners; Issues #12/#16/#17 | **High**: raw or identity disclosure cannot be revoked after receipt. | **NOT ACCEPTED**; persistence/export OFF; see decision register. |
| `THREAT-BROWSER-XSS` | `ASSET-NORMALIZED`, `ASSET-IDENTITY`, `ASSET-SECRET` | `ACT-PLATFORM`, `ACT-PUBLIC`, `ACT-WORKER` supplying hostile content | `ENTRY-BROWSER` through event/transcript/history rendering | Untrusted text, URL, or metadata is interpreted as active markup/script or escapes its render context. | `CTRL-RENDER-UNTRUSTED`, `CTRL-EVENT-VALIDATION`; normalized fields only; no raw markup/API response. | Unit/E2E hostile corpus; browser policy violation reports; output encoding review. | Stop/hide affected publication; revoke session if exposed; patch renderer/policy; invalidate affected caches; assess credential exposure. | Web and event owners; Issues #10/#11/#17 | Medium | **CONTROL REQUIRED**; public UI remains unavailable until evidenced. |
| `THREAT-RAW-ARCHIVE-SPILL` | `ASSET-RAW`, `ASSET-SECRET`, `ASSET-AUDIO` | Malformed `ACT-PLATFORM` input, coding error, or compromised `ACT-PRIVILEGED` | `ENTRY-BILIBILI`, `ENTRY-DATA` | Sanitization, audio/credential rejection, compression, encryption, key access, audit, manifest, or storage fails and fallback writes raw elsewhere. | `CTRL-EVENT-VALIDATION`, `CTRL-RAW-BOUNDARY`; fail without archival; no temp/log/queue/Postgres fallback. | Negative-path tests; archive manifest/audit reconciliation; forbidden-path scanners; encryption and object-policy alerts. | Stop raw archival and new persistence; keep normalized publication only if separately safe; quarantine/delete spill; rotate exposed secrets; incident disable if scope uncertain. | Data/security owners; Issues #10/#16/#19 | **High**: an unintended persistent copy may survive discovery. | **NOT ACCEPTED**; production raw persistence OFF; see decision register. |
| `RISK-RAW-PLAINTEXT-EXPORT` | `ASSET-RAW` | Authorized or compromised `ACT-PRIVILEGED` | `ENTRY-DATA` managed export or a proposed local download | Plaintext is disclosed outside the managed encrypted/audited boundary. | `CTRL-RAW-EXPORT`; default prohibition on untracked local plaintext; bounded managed object only. | Per-access audit; object expiry/deletion reconciliation; destination inventory if a future exception is proposed. | Revoke future access and object; delete managed copy; disable export; incident/takedown process. Do not claim remote erasure of received plaintext. | Data/security owner and admin disable owner; Issues #16/#17 | **High** if the capability is introduced. | **NOT ACCEPTED**; local plaintext export prohibited; see decision register. |

### Community worker and protocol

| ID | Asset | Actor | Entry point | Preconditions | Preventive controls | Detection | Response | Control owner / dependency | Residual | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `THREAT-WORKER-EXFILTRATION` | `ASSET-PROTOCOL`, synthetic/test data, and any future least-data input | `ACT-WORKER` or host malware | `ENTRY-WORKER` | An authenticated worker can inspect any data legitimately delivered to its host. | `CTRL-WORKER-SYNTHETIC-ONLY`, `CTRL-WORKER-PROTOCOL`, no service secrets, least-data fields, identified invited device. | Lease/device audit; volume/rate anomalies; unexpected output/health behavior. Host-local copying is not reliably observable. | Revoke lease/device; block reconnect; rotate anything unexpectedly disclosed; quarantine output; incident review. | Worker gateway/scheduler owners; Issues #13/#14/#15 | Medium for synthetic/control-only production state; real audio is the separate High risk below. | **CONTROL REQUIRED**; synthetic only. |
| `RISK-WORKER-AUDIO-RETENTION` | `ASSET-AUDIO` and associated rights/confidentiality | Malicious/compromised `ACT-WORKER` or host operator | `ENTRY-WORKER` real-PCM assignment | The backend deliberately discloses real PCM to a third-party host; authentication cannot prove unmodified code or RAM erasure. | `CTRL-WORKER-SYNTHETIC-ONLY`, `CTRL-AUDIO-RAM-ONLY`, `CTRL-WORKER-PROTOCOL`, identified invited worker, explicit third-party processing rights, least duration/data, one active lease. | Backend lease/frame audit and protocol anomalies can bound disclosure, but **cannot detect or prove host-side copying/erasure**. | Stop assignments; revoke lease/device; clear conforming sender/worker RAM; global or room disable; rights-holder/incident response. Never claim deletion of a hostile copy. | Worker/security owner; Issues #8/#13/#14/#15; repository owner is sole risk decision maker | **High** even after conforming controls. | **NOT ACCEPTED**. Production real PCM to community workers remains **OFF**; synthetic-only gate stays in force. |
| `THREAT-WORKER-FABRICATED-OUTPUT` | `ASSET-PROTOCOL`, `ASSET-NORMALIZED` integrity | Malicious/compromised `ACT-WORKER` | `ENTRY-WORKER` transcript/health return | Worker holds or forges an apparently valid lease and returns invented, altered, late, or cross-session output. | Backend remains authoritative; `CTRL-WORKER-PROTOCOL`, `CTRL-WORKER-REVOCATION`; bind output to session/lease/version/epoch/sequence and validate schema/size/time. | Duplicate/late/cross-session counters; transcript/health plausibility and timing checks; sampled comparison where lawful; device error-rate trends. | Reject/quarantine output; revoke lease/device; hide affected publication; reprocess only from audio still inside the existing RAM budget; no audio retry queue. | Protocol/worker/event owners; Issues #3/#9/#13/#14/#15 | Medium | **CONTROL REQUIRED**; worker output never becomes authoritative without validation. |
| `THREAT-WORKER-RESOURCE-ABUSE` | `ASSET-AVAILABILITY`, `ASSET-PROTOCOL` | `ACT-WORKER` or bot using enrollment/worker surface | `ENTRY-WORKER` registration, heartbeat, frames, output, reconnect | Missing quotas/timeouts or a valid device intentionally consumes connections, memory, CPU, bandwidth, or scheduler capacity to cause denial of service. | `CTRL-WORKER-PROTOCOL`, bounded frames/rates/timeouts, one active Alpha lease, enrollment controls, `CTRL-WORKER-REVOCATION`. | Per-device and global rate/memory/RTF/timeout metrics; connection and scheduler saturation alerts. | Drop/revoke/throttle device; reject reconnect; shed nonessential work; global disable if resource pressure threatens safety cleanup. | Worker/operations owners; Issues #13/#14/#15/#19 | Medium | **CONTROL REQUIRED**; availability does not justify relaxing safety bounds. |
| `THREAT-WORKER-CONTROL-INJECTION` | `ASSET-BUILD`, backend/worker host integrity, `ASSET-SECRET` | Compromised backend/account or malicious protocol peer | `ENTRY-WORKER` control message/model selection | Protocol accepts arbitrary command, shell, code, container, download URL, or non-allowlisted model field. | `CTRL-WORKER-PROTOCOL`; closed versioned schema; allowlisted manifest supplied by identifier/digest only; no general execution/download capability. | Unknown-field/version/manifest rejection tests; protocol audit; executable/network behavior alerts in trusted test environments. | Reject message; revoke lease/device; disable worker path; rotate affected keys; investigate host compromise. | Protocol/worker/security owners; Issues #3/#6/#13/#14/#18 | Medium after strict closed-schema controls. | **CONTROL REQUIRED**; arbitrary execution capability is prohibited. |
| `THREAT-PROTOCOL-REPLAY-FORGERY` | `ASSET-PROTOCOL`, ordering and publication integrity | `ACT-PUBLIC`, `ACT-WORKER`, network attacker, stale client | `ENTRY-WORKER` | Captured/forged message, stale epoch, duplicate sequence, version downgrade, expired lease, or cross-session binding is accepted. | `CTRL-WORKER-PROTOCOL`; signed/authenticated identity; explicit version allowlist; lease/session/epoch/sequence/revision binding; expiry and duplicate rejection. | Replay/duplicate/stale/downgrade counters; signature/version failures; cross-session invariant tests and golden fixtures. | Reject with no authoritative state change; revoke on suspicious repetition; hide affected output; incident review. | Protocol owner; Issues #3/#13/#14/#15 | Medium | **CONTROL REQUIRED**; compatibility fields change only through a protocol Issue and golden evidence. |

### Deletion, safety, platform, and privileged operations

| ID | Asset | Actor | Entry point | Preconditions | Preventive controls | Detection | Response | Control owner / dependency | Residual | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `THREAT-DELETION-INCOMPLETE` | `ASSET-DELETION`, `ASSET-NORMALIZED`, `ASSET-RAW`, `ASSET-IDENTITY` | `ACT-PROVIDER`, coding error, or `ACT-PRIVILEGED` | `ENTRY-DATA`, `ENTRY-DELETION-RESTORE` | A request is acknowledged, `hidden` reported, or purge started before tombstone commit/read-back; ordinary pending or a durable invalid denial incorrectly revokes unrelated serving; admission/denial or scoped-containment failure does not taint/revoke globally; recovery demands a valid selector triple for an invalid request; durable intake omits/resets the original request time; exact intake persistence fails and the initiating source plus backend then crash without a recovery-visible continuity blocker; a pre/post-commit crash or lost response loses/duplicates admission; an audit row, volatile block, coarse guard, or empty store is mistaken for a tombstone; a selector is invalid/conflicting; room/session scope or dominance is wrong; a cascade fails; or late success erases the SLA breach. | `CTRL-DELETION-STATE`, `CTRL-DELETION-FAIL-CLOSED`, `CTRL-SAFETY-DEFAULT-OFF`, `CTRL-IDENTITY-RESTORE-REVOCATION`, `CTRL-BACKUP-EVIDENCE`, `CTRL-ROOM-DENYLIST`; pre-armed serving-incarnation continuity guard, explicit pending-versus-tainted intake states, sticky backend ownership after failed accounting/admission, atomic durable valid-intake triple, durable invalid denial, verified `hidden` admission barrier, authoritative selector, room dominance, exact-scope cascade, and checkpoint read-back. | Valid session/room and invalid-selector pending probes verify unrelated activation is unchanged; intake/tombstone/denial write, timeout, unknown-result, read-back, and scoped-containment/ownership-proof failures verify atomic taint plus global revoke; valid-triple and invalid-denial authoritative replay; immutable-clock comparison; source-loss/backend-crash and orphaned-guard recovery; pre/post-commit crash and response-loss retry; audit/coarse-guard/empty-store negatives; selector, room-all-child, sibling non-deletion, dominance, store, identity, retry, and SLA reconciliation. | While admission is pending, keep only exact-scope provisional containment, or no guessed containment for an invalid selector; report no success/state and start no purge without disturbing unrelated serving. Durable invalid denial clears pending. Verified admission preserves the exact-scope block without global re-enable. Failed/ambiguous accounting/admission or loss of containment proof atomically taints the epoch and revokes global activation; the live backend retries rather than relying solely on its source. If both continuities are lost, refuse every data surface and relaxation until authoritative replay either recovers and admits the valid request's same triple or reproduces the invalid request's durable denial. Absent applicable proof, quarantine persists without inventing `hidden`, a clock, or purge scope. After admission retry/re-enumerate exactly, never report unchecked completion, and preserve dominance and late-SLA evidence. | Identity/data/privacy/operations owners; Issues #12/#13/#16 | **High**: lost admission/time, wrong scope, provider failure, an omitted authority row, or an unknown copy may expose retained data, hide lateness, or delete unrelated data. | **NOT ACCEPTED**; production auth/persistence OFF; see decision register. |
| `THREAT-RESTORE-RESURRECTION` | `ASSET-DELETION`, `ASSET-SAFETY`, `ASSET-IDENTITY`, `ASSET-SECRET`, all persisted data | `ACT-PROVIDER`, mistaken `ACT-PRIVILEGED`, stale backup | `ENTRY-DELETION-RESTORE`, `ENTRY-MAINTENANCE` | Restart/restore treats an empty application store/audit as proof, trusts a prepared/ambiguous relaxation or committed enabled snapshot without a fresh current-incarnation activation capability, seals or ignores an orphaned continuity guard, opens with unresolved or exact-intake-lost deletion scope, fails room/session or account/device replay, loses room dominance, accepts a conflicting parent map or pre-restore credential/key, or uses stale safety scope or an unbounded backup/object window. | `CTRL-SAFETY-DEFAULT-OFF`, `CTRL-RESTORE-REPLAY`, `CTRL-DELETION-STATE`, `CTRL-IDENTITY-RESTORE-REVOCATION`, `CTRL-AUTH-KEY-LIFECYCLE`, `CTRL-BACKUP-EVIDENCE`, `CTRL-MAINTENANCE-EXCLUSIVE`; process-bound non-restorable activation, continuity-guard quarantine, durable admission, and provider-window evidence. | Orphaned/unsealed-guard and exact-intake-loss restart negatives; prepared, post-promotion/pre-activation, and committed-without-capability crash probes; unresolved-intake and missing-tombstone restore negatives; pre/post-commit crash and response-loss replay; offline credential/new-authority rejection; room/session/sibling/dominance reconciliation; auth and safety-snapshot generation comparison; post-window verification. | Keep every traffic class isolated/off; discard or reconcile prepared/split relaxation and never reuse a prior incarnation's capability; require authoritative ingress continuity before sealing an orphaned guard; reconcile every exact intake to a commit/read-back-verified tombstone before replay; start no guessed purge; reject restored credentials, advance protected auth state, replay exact-scope cascades/checkpoints, and require fresh non-restored audited recovery-admin auth. | Identity/data/operations owners; Issues #4/#12/#13/#16/#19 | **High**: an omitted/unadmitted/wrong-scope target, orphaned authority epoch, stale enabled snapshot, or accepted pre-restore credential can republish data, delete unrelated data, or recreate authority. | **NOT ACCEPTED**; auth/persistence/recovery production paths OFF; see decision register. |
| `THREAT-SAFETY-ROLLBACK` | `ASSET-SAFETY`, `ASSET-AVAILABILITY` | Compromised/mistaken `ACT-PRIVILEGED`, stale backup, storage failure | `ENTRY-BROWSER` admin control, `ENTRY-DATA`, `ENTRY-DELETION-RESTORE` | A newer global/room decision is overwritten; global cleanup waits behind slow/hung durable I/O; generic tightening state lets pending `add(R)` revoke unrelated activation; a failed add never invokes global disable; a relaxation is made recovery-current before its final guard check, or a committed enabled snapshot is treated as sufficient after that check fails; tightening exists only in volatile state when the process crashes; a delayed enable/remove response clears a newer `G`/`Q[R]`; multiple active owners do not share/acknowledge the guards; a crash, split journal/recovery commit, or lost response drops scope/state; clean-close races a late safety action; enable drops denylist entries or removal enables global ingest; canonical/resource binding is ambiguous; state is stale/lost; or relaxation lacks owner approval. | `CTRL-SAFETY-DEFAULT-OFF`, `CTRL-SAFETY-GENERATION`, `CTRL-ROOM-DENYLIST`, `CTRL-DISABLE-CLEANUP`, `CTRL-REENABLE-GATE`; one active Alpha serving authority, pre-armed continuity guard, process-bound non-restorable activation capability, non-current predecessor-bound prepared relaxation, future-owner isolation on guard uncertainty, distinct high-priority `G` and `Q[R]`, pre-durability scope-correct cleanup, one-generation orthogonal snapshot, predecessor binding, and explicit add-failure escalation. | Hold exact `add(B)` pending within deadline while `A` remains active and prove `G`/`A` resources unchanged; then inject timeout/unknown/read-back failure and prove a separately identified global-disable first changes `G` and starts all-room cleanup. Also test active-owner guard acknowledgement; prepared/current/capability inspection; both linearization orders for relaxation versus tightening and disable versus add; final-guard failure after candidate durability followed by tightening-write failure/crash; clean-close races; pre-/mid-/post-promotion and activation crash/response loss; orphaned-guard recovery; generation mismatch; global-enable/room-remove noninterference; stale/concurrent operation and binding/integrity alerts. | Apply exact scope without awaiting durability: global disable increments `G`, revokes global activation, and starts all-room cleanup; pending/committed `add(R)` increments only `Q[R]`, blocks/cleans `R`, and preserves unrelated activation. Add timeout/unknown/binding or commit/read-back failure retains the safe room block where exact and invokes a separate global-disable transition; only that action changes `G` and expands cleanup. A prepared relaxation is never current, and a committed candidate without the same live incarnation's final capability admits no traffic. Process loss globally quarantines recovery under the orphaned guard. Isolate/terminate an unacknowledged future owner and reconcile split/unknown state without dropping the denylist. | Safety/security/operations owners; Issues #7/#16/#17/#19 | **High**: delayed cleanup, stale relaxation, uncoordinated authority, lost/split state, control compromise, or wrong scope can expose denied content or cause broad availability loss. | **NOT ACCEPTED**; production ingest OFF; see decision register. |
| `THREAT-AUDIT-JOURNAL-FAILURE` | `ASSET-AUDIT`, `ASSET-SAFETY` | `ACT-PROVIDER`, disk/quota failure, coding error, `ACT-PRIVILEGED` | Any control/raw/deletion action, especially `ENTRY-DATA` | Append or recovery-copy write/read-back is unavailable, reordered, rolled back, ambiguous, or contains prohibited payload. | `CTRL-SAFETY-GENERATION`, `CTRL-DELETION-STATE`, `CTRL-AUDIT-PAYLOAD-FREE`; emergency disable works locally; no unverified deletion admission, enable, denylist removal, or raw export may succeed. | Write/read-back failure, sequence gap, integrity mismatch, payload-schema rejection, provider alert. | Disable locally and remain off; deny deletion acknowledgement/purge, relaxation, and export; preserve safe payload-free diagnostics that are not treated as tombstones; repair/reconcile and obtain re-enable approval. | Security/operations/data owners; Issues #16/#17/#19 | Medium if fail-closed behavior is independently evidenced. | **CONTROL REQUIRED**; audit unavailability never fails open, and audit is never deletion admission. |
| `THREAT-PLATFORM-CHANGE` | `ASSET-RIGHTS`, `ASSET-AVAILABILITY`, event integrity | `ACT-PLATFORM`, content/rightsholder change, stale project review | `ENTRY-BILIBILI` and policy/rights review | Interface/schema, terms, rights, ownership, restriction, acquisition channel, rate limit, or product use changes after approval or cannot be proven current; or ordinary offline/ended status is mistaken for a durable room-safety decision. | `CTRL-PLATFORM-FAIL-CLOSED`, `CTRL-PLATFORM-RIGHTS-REVIEW`, `CTRL-EVENT-VALIDATION`, `CTRL-ROOM-DENYLIST`; no credentialed/scraper/alternate fallback and explicit transient-live versus policy/rights/safety classification. | Runtime schema/restriction/rate signals; offline/end/reconnect lifecycle tests that assert no denylist or generation mutation; scheduled 90-day review; change-triggered review; owner/takedown reports. | For ordinary offline/end, stop only that session/start/reconnect and clear transient resources; do not denylist or require governance removal. For a verified room/platform policy, rights, or safety incident, stop publication/persistence and invoke the applicable room/global control; takedown/delete as required and re-review exact purpose/rights. | Platform/policy owner and operator disable owner; Issues #7/#10/#19; repository owner decision | **High**: a change may create rights or compliance exposure before detection, while false durable denial can unnecessarily suppress later lawful broadcasts. | **NOT ACCEPTED**; production ingest OFF; see decision register. |
| `THREAT-SSRF-REDIRECT` | `ASSET-SECRET`, backend network/data authority | `ACT-PUBLIC`, `ACT-PLATFORM`, DNS/redirect attacker | `ENTRY-BILIBILI` room/URL resolution and connect/refresh | User-controlled alias/URL, redirect, DNS rebinding, or alternate scheme reaches private, link-local, metadata, arbitrary-port, or credential-bearing destination. | `CTRL-SSRF-RESOLUTION`, `CTRL-PLATFORM-FAIL-CLOSED`; operator-selected canonical room ID; fixed approved acquisition family; no arbitrary URL fetch. | Denied-target/redirect/DNS audit; egress policy alerts; resolver unit/integration tests; unexpected destination telemetry without secret values. | Abort resolution/session; clear locator; disable room/global path; rotate possibly exposed credentials; investigate network access. | Ingest/security/operations owners; Issues #7/#19 | **High**: successful SSRF can reach privileged metadata or internal services. | **NOT ACCEPTED**; production resolver OFF; see decision register. |
| `THREAT-MAINTAINER-TAKEOVER` | `ASSET-SAFETY`, `ASSET-DELETION`, `ASSET-RAW`, `ASSET-BUILD` | Malicious/compromised `ACT-PRIVILEGED` maintainer | `ENTRY-MAINTENANCE`, source/review administration | Broad or durable credentials, bypassed mutual exclusion/review, or an Issue #4 job becomes a serving/second authority. | `CTRL-MAINTENANCE-EXCLUSIVE`, `CTRL-AUTH-KEY-LIFECYCLE`, branch/review protection, narrow expiring credentials, no external/serving flow. | Runbook approval and lock audit; concurrent-authority alert; credential-use anomaly; protected-branch/release audit. | Stop job and serving traffic; global disable; revoke/rotate; restore/reconcile safety and deletion state; independent incident review. | Repository, security, and operations owners; Issues #1/#4/#16/#19 | **High**: a privileged maintainer may alter code, safety, deletion, or archive state. | **NOT ACCEPTED**; maintenance/production deployment OFF; see decision register. |
| `THREAT-AUTH-KEY-COMPROMISE` | `ASSET-SECRET`, `ASSET-IDENTITY`, `ASSET-SAFETY`, `ASSET-RAW` | `ACT-PUBLIC`, `ACT-ACCOUNT`, `ACT-PRIVILEGED`, provider attacker | `ENTRY-AUTH-EMAIL`, admin controls, key/service interfaces, `ENTRY-DELETION-RESTORE` | Magic/enrollment/session bearer, device/admin identity, signing/encryption key, or provider credential is stolen, replayed, overprivileged, not revocable, or revived from a stale backup. | `CTRL-AUTH-EXPIRY`, `CTRL-IDENTITY-RESTORE-REVOCATION`, `CTRL-AUTH-KEY-LIFECYCLE`, `CTRL-AUTHZ-DENY-BY-DEFAULT`, `CTRL-SECRET-CONTAINMENT`; bounded bearer lifetimes, verifier hashes only, recovery-protected auth generation/key version, and no current verification key material in application backups. | Failed/reused/expired/pre-restore-token audit; impossible or anomalous admin/device actions; key/provider alerts; session/device inventory and auth/checkpoint generation reconciliation. | Revoke sessions/devices/tokens; purge restored verifier/session rows; rotate or advance protected key/generation state; global disable; stop raw access/export; require fresh non-restored audited recovery-admin auth and owner re-enable review. | Identity/security/operations owners; Issues #4/#12/#13/#16/#17/#19 | **High**: privileged use before detection may disclose or alter protected state. | **NOT ACCEPTED**; auth-dependent production paths OFF; see decision register. |
| `THREAT-SUPPLY-CHAIN-COMPROMISE` | `ASSET-BUILD`, every runtime asset reachable by released code/model | `ACT-SUPPLY` or compromised `ACT-PRIVILEGED` | `ENTRY-CI-DEPLOY` | Malicious/unpinned dependency/action/tool/model/dataset, tampered artifact, leaked CI secret, or prohibited copied code reaches a release. | `CTRL-SUPPLY-CHAIN`; lockfiles, review and protected release identity, provenance, secret isolation, allowlisted manifests, independent license/provenance policy. | Deterministic verify; dependency/provenance/license scans; artifact digest/signature comparison; CI and release audit; runtime anomaly alerts. | Stop release/deploy; global disable if deployed; revoke/rotate; rebuild from reviewed sources; quarantine artifact/model; incident and license review. | Repository/security/release owners; Issues #1/#4/#18/#19 | **High**: trusted build output can subvert every runtime boundary. | **NOT ACCEPTED**; production deployment OFF; see decision register. |

## Critical and High residual-risk decision register

All entries below are individual decisions. None is accepted. “Disable owner” identifies
who must stop future exposure; it does not grant that person authority to accept the
risk. Before any acceptance, the repository owner must fill in an approver, decision
date, exact bounded scope, verified compensating controls, next review date, and any
expiry. An empty or collective statement is invalid.

| Risk ID | Exact gated scope | Residual | Required compensating controls before a decision | Disable owner | Current owner decision |
| --- | --- | --- | --- | --- | --- |
| `THREAT-SECRET-DISCLOSURE` | Production use of platform/email/database/archive/deployment credentials and transient locators. | High | `CTRL-SECRET-CONTAINMENT`, `CTRL-AUTH-KEY-LIFECYCLE`, tested rotation/revocation and incident disable. | Operator/admin for ingest; security/operations for affected service | **NOT ACCEPTED — approver/date/review date PENDING; path OFF** |
| `THREAT-RAW-IDENTITY-PRIVESC` | Production identity/history/raw persistence and managed raw access. | High | `CTRL-AUTHZ-DENY-BY-DEFAULT`, `CTRL-RAW-BOUNDARY`, `CTRL-RAW-EXPORT`, cross-role/object tests and audit. | Admin plus data/security owner | **NOT ACCEPTED — approver/date/review date PENDING; persistence/export OFF** |
| `THREAT-RAW-ARCHIVE-SPILL` | Production temporary raw handling and private-Bucket archival. | High | `CTRL-EVENT-VALIDATION`, `CTRL-RAW-BOUNDARY`, forbidden-path and encryption-failure evidence. | Operator/admin and data owner | **NOT ACCEPTED — approver/date/review date PENDING; raw persistence OFF** |
| `RISK-RAW-PLAINTEXT-EXPORT` | Any future plaintext disclosure outside the managed encrypted export boundary. | High | A separately approved bounded destination, legal/rights basis, access/audit/deletion controls, and incident procedure; `CTRL-RAW-EXPORT` alone cannot erase recipient copies. | Admin and data/security owner | **NOT ACCEPTED — capability prohibited** |
| `RISK-WORKER-AUDIO-RETENTION` | Real production PCM disclosed to an identified invited community worker. | High | Explicit third-party-processing rights; `CTRL-WORKER-SYNTHETIC-ONLY`, `CTRL-AUDIO-RAM-ONLY`, `CTRL-WORKER-PROTOCOL`, least-data/lease/revocation evidence; scope and expiry. | Operator/admin and worker security owner | **NOT ACCEPTED — real PCM OFF; synthetic only** |
| `THREAT-DELETION-INCOMPLETE` | Production normalized/raw/identity persistence and managed exports subject to room/session/account/device deletion. | High | `CTRL-DELETION-STATE`, `CTRL-DELETION-FAIL-CLOSED`, `CTRL-SAFETY-DEFAULT-OFF`, `CTRL-IDENTITY-RESTORE-REVOCATION`, `CTRL-BACKUP-EVIDENCE`, provider inventory/window evidence, admission commit/read-back, exact-intake-failure plus source/backend-crash continuity-guard tests, invalid-selector, room-all-child, session-sibling, dominance, cascade/read-back, and partial-failure tests. | Admin and identity/data/privacy owner | **NOT ACCEPTED — approver/date/review date PENDING; auth/persistence OFF** |
| `THREAT-RESTORE-RESURRECTION` | Restoring any production data backup or object-version state, including unresolved/admitted or exact-intake-lost deletion scope, orphaned serving-incarnation state, identity, and stateful/stateless credential state. | High | `CTRL-SAFETY-DEFAULT-OFF`, `CTRL-RESTORE-REPLAY`, `CTRL-DELETION-STATE`, `CTRL-IDENTITY-RESTORE-REVOCATION`, `CTRL-AUTH-KEY-LIFECYCLE`, `CTRL-BACKUP-EVIDENCE`, continuity-guard quarantine, unresolved-intake blocking, prepared/ambiguous-relaxation rejection, current-incarnation activation proof, verified-admission replay, exact-scope/dominance restore, credential rejection, and deleted-authority issuance probes. | Identity/operations/data owner | **NOT ACCEPTED — approver/date/review date PENDING; auth/recovery path OFF** |
| `THREAT-SAFETY-ROLLBACK` | Production global enablement, room-scoped denylist transitions, and restored safety state. | High | `CTRL-SAFETY-DEFAULT-OFF`, `CTRL-SAFETY-GENERATION`, `CTRL-ROOM-DENYLIST`, `CTRL-DISABLE-CLEANUP`, `CTRL-RESTORE-REPLAY`, `CTRL-REENABLE-GATE`, independent recovery copy, prepared/promotion/final-fence/current-incarnation crash tests, orphaned-guard quarantine, exact-scope/noninterference/concurrency tests, and rollback/unauthorized-reenable tabletop. | Operator/admin for immediate disable; safety owner | **NOT ACCEPTED — approver/date/review date PENDING; ingest OFF** |
| `THREAT-PLATFORM-CHANGE` | Production Bilibili acquisition, transformation, worker disclosure, retention, and public output. | High | `CTRL-PLATFORM-FAIL-CLOSED`, `CTRL-PLATFORM-RIGHTS-REVIEW`, exact source/rights evidence, 90-day/change review, takedown process. | Operator/admin and platform-policy owner | **NOT ACCEPTED — approver/date/review date PENDING; ingest OFF** |
| `THREAT-SSRF-REDIRECT` | Production room resolution and playback/event connection. | High | `CTRL-SSRF-RESOLUTION`, network egress policy, redirect/DNS tests and incident rotation procedure. | Operator/admin and ingest/security owner | **NOT ACCEPTED — approver/date/review date PENDING; resolver OFF** |
| `THREAT-MAINTAINER-TAKEOVER` | Issue #4 production migration/deletion/recovery operations and release authority. | High | `CTRL-MAINTENANCE-EXCLUSIVE`, `CTRL-AUTH-KEY-LIFECYCLE`, protected review/release and recovery evidence. | Operations/security owner | **NOT ACCEPTED — approver/date/review date PENDING; production maintenance OFF** |
| `THREAT-AUTH-KEY-COMPROMISE` | Production invite/session/device/admin/service identity and encryption/signing keys. | High | `CTRL-AUTH-EXPIRY`, `CTRL-IDENTITY-RESTORE-REVOCATION`, `CTRL-AUTH-KEY-LIFECYCLE`, `CTRL-AUTHZ-DENY-BY-DEFAULT`, stateful/stateless restore rejection, rotation tests, and alerts. | Admin plus security/operations owner | **NOT ACCEPTED — approver/date/review date PENDING; auth-dependent paths OFF** |
| `THREAT-SUPPLY-CHAIN-COMPROMISE` | Production artifact, dependency, CI action, model, dataset, and deployment release path. | High | `CTRL-SUPPLY-CHAIN`, protected release provenance, deterministic verification, rollback/rotation incident evidence. | Repository/security/release owner | **NOT ACCEPTED — approver/date/review date PENDING; production deployment OFF** |

Repository-owner decision fields for each row:

- Approver: **PENDING**
- Decision date: **PENDING**
- Accepted exact scope and expiry: **PENDING**
- Verified compensating-control evidence: **PENDING**
- Next review date: **PENDING**

These fields must be completed separately for each accepted ID. In particular, neither
merging this document nor enabling a synthetic worker test accepts
`RISK-WORKER-AUDIO-RETENTION`.

## Required response invariants

The later incident and recovery implementation must preserve these invariants:

1. Emergency global disable is available to operator/admin independently of the failing
   ingest path, immediately revokes the current incarnation's non-restorable activation
   capability, rejects every room, closes its local authority gates, and issues all
   active/queued cleanup before any journal/recovery-copy await. Slow, hung, or failed
   durable I/O cannot defer that cleanup. Alpha has one active serving authority;
   any future owner that cannot synchronously acknowledge an applicable guard is isolated/
   terminated and keeps the deployment globally off. A pending-in-deadline or successfully
   committed `denylist-add(R)` sets
   only `Q[R]` and rejects/stops canonical room `R`; an unrelated active room's platform
   session, lease, audio/locator RAM, pending publication, and global activation remain
   untouched. A classified add failure invokes a separately identified global-disable
   action, and only that action sets `G`, revokes globally, and expands cleanup. Both paths
   write only payload-free audit data where available.
2. One generation orders an orthogonal global-enable bit and complete denylist. Global
   enable preserves the denylist, exact-room removal does not enable global ingest, and
   generation change alone causes reload/re-evaluation rather than cleanup. A relaxation
   first persists and reads back a predecessor-bound `PREPARED` proposal under a separate
   opaque identity; preparation neither advances the generation nor becomes current or
   recovery-effective. Only conditional promotion to `COMMITTED` advances the one
   generation. Even a `COMMITTED` enabled snapshot cannot admit traffic without the same
   live serving incarnation's non-restorable capability minted by the atomic final local
   guard check-and-effect. Global disable increments `G` and preempts slow relaxation I/O
   by revoking that capability; `add(R)` increments only `Q[R]`, preempts only the matching
   room-removal effect, and keeps unrelated rooms' global activation. Every scope-labelled
   pending handler prevents clean sealing, but pending alone does not widen runtime scope.
   A prepared, split, ambiguous, post-promotion/pre-activation, or guard-failed relaxation
   stays non-effective; after process loss an unsealed/orphaned continuity guard prevents
   a committed candidate from reopening. Canonical/resource ambiguity, stale/conflicting
   state, journal/recovery failure, unknown rights scope, or unauthorized relaxation
   invokes an explicit global-disable action. Ordinary offline/ended status is not such an
   action: it only stops the current session/start/reconnect and mutates neither generation
   nor denylist.
3. A deletion request first enters `intake-pending` and validates exactly one authoritative
   room-or-session selector. Pending valid intake establishes only exact-scope provisional
   containment; pending invalid intake starts no guessed purge. Neither pending state
   revokes global activation. The valid path atomically retains selector, idempotency, and
   immutable original initiating-request time in durable intake, then makes the existing
   `hidden` tombstone reuse that triple and commit/read back at the independent recovery
   boundary. Before that barrier, no request is accepted/acknowledged, no deletion state is
   reported, and no purge begins. Verified admission preserves only its exact-scope block;
   durable invalid denial clears pending, and neither requires a global re-enable. A
   failed, timed-out, response-unknown, or unreadable admission/denial, or inability to
   install or prove exact-scope containment/ownership, instead atomically marks the epoch
   `tainted`, revokes global activation, and prevents clean sealing. Loss
   of source and backend then leaves recovery globally quarantined until authoritative
   replay replays the observed request: a valid request must recover/admit its exact triple,
   while an invalid request must reproduce a durable denial. Absent the applicable proof,
   quarantine persists without inventing `hidden`, a fourth state, a later clock, or
   destructive scope. The initiating source is
   not the sole replay owner; audit, volatile block, coarse guard, or empty store is not a
   substitute.
4. After verified admission, room scope blocks and re-enumerates every child session;
   session scope removes only its target/derivatives and preserves siblings/shared state;
   room tombstones dominate child manifests. Partial purge never reports completion,
   retries idempotently, and preserves immutable late-SLA evidence.
5. Every restart/restore has no reusable activation capability and remains offline and
   globally quarantined while a prior serving guard is unsealed/orphaned, any exact intake
   continuity is unproven, or any relaxation is prepared/split/ambiguous. Before a fresh
   capability may be minted, authoritative ingress continuity must reconcile; every
   unresolved exact deletion intake/admission must become a verified replayed tombstone;
   every restored stateful credential row must be purged/revoked; protected auth state
   must reject every stateless pre-restore credential; typed room/session and account/
   device checkpoints must replay with exact-scope/dominance proofs; and the complete
   safety snapshot must reconcile. A backup, `COMMITTED` enabled snapshot alone, empty
   application store, or audit row cannot replace recovery evidence, restore a prior
   capability/current key material, or recreate deleted authority.
6. Worker revocation limits only future disclosure. It never asserts that a malicious
   host erased PCM. Raw-export revocation likewise never asserts erasure of plaintext
   already disclosed outside the managed boundary.
7. Re-enable or exact-room denylist removal requires cause remediation, current platform/
   rights evidence, authoritative replay of every deletion intake and serving-incarnation
   continuity hazard, rejection of every prepared/split/ambiguous relaxation, successful
   tabletop evidence, recorded repository-owner approval, and fresh non-restored
   separately audited admin recovery authentication. It uses the prepared/promotion/final-
   capability protocol above. Global enable retains the denylist; room removal does not
   enable global ingest; neither starts a room automatically. Availability pressure,
   restored admin sessions, an empty store, and an enabled snapshot without the fresh
   current-incarnation capability are not exceptions.

## Review and evidence checklist

Before the repository owner can approve this threat model for production use, reviewers
must attach evidence that:

- every threat row maps to executable tests, operational checks, or a deliberately
  disabled capability in its owning Issue;
- every Critical/High row has its own complete decision record, rather than a blanket
  approval;
- the role matrix has positive and negative authorization tests;
- synthetic-only worker behavior is the default and real community PCM cannot be
  selected while `RISK-WORKER-AUDIO-RETENTION` is not accepted;
- secret redaction, protocol rejection, no-audio-persistence, raw archival failure, and
  platform fail-closed have negative evidence appropriate to their Issue; platform tests
  separately prove that ordinary offline/end stops only the current attempt and changes
  neither denylist nor safety generation;
- deletion tests prove the recovery-visible serving guard is durably open before traffic;
  hold valid exact-session, valid room, and invalid-selector requests in `intake-pending`
  and prove unrelated/global activation is unchanged; admit the valid tombstone or durably
  deny the invalid selector and prove no global re-enable is required; then inject exact-
  intake write/read-back failure, invalid-denial write/read-back failure, and scoped-
  containment/ownership proof loss, each followed by initiating-source loss and backend
  crash; prove failure atomically changes pending to `tainted`, revokes global
  activation, gives the live backend a sticky retry, and makes clean sealing impossible;
  prove restart detects the orphaned guard and every data surface/relaxation remains
  quarantined, and loss of authoritative replay creates no false `hidden`, later clock,
  or guessed purge; inject tombstone commit/read-back failure, pre-commit crash, post-
  commit/pre-response crash, and response loss; prove no acknowledgement/report/purge
  precedes the barrier; prove durable intake atomically retains selector/idempotency/
  original time and retry/tombstone reuse the unchanged triple; reject audit, coarse
  guard, volatile containment, or an empty store as admission evidence; and preserve only
  the existing three deletion states;
- safety tests distinguish global `G` from matching and unrelated-room `Q[R]`; hold
  `add(B)` pending within its deadline while `A` is active and prove only B is blocked/
  cleaned, the continuity epoch cannot close, and A's activation/session/lease/audio/
  locator/publication remain unchanged; then classify timeout, unknown result, binding,
  or write/read-back failure and prove a separate global-disable action changes `G` and
  starts all-room cleanup before any further durability await; prove global-disable local
  authority closure and cleanup precede every durable-I/O await; prove a
  relaxation's predecessor-bound `PREPARED` proposal is not current/recovery-effective,
  only promotion to `COMMITTED` advances the single generation, and `COMMITTED`
  enablement cannot admit traffic without a non-restorable capability for the same live
  incarnation; inject
  disable versus enable and add versus remove before preparation, after preparation,
  around promotion, and on both sides of the final local check-and-effect; specifically
  commit the enabled candidate, make the final fence fail, fail tightening durability,
  then crash, and prove the orphaned guard plus lost capability prevents restart reopen;
  inject latch-before-journal, split journal/recovery, post-read-back response-loss, and
  same-predecessor disable/add crash/retry cases without losing the complete denylist;
  prove only an atomic serving/safety/deletion-ingress quiescence fence plus authoritative
  reconciliation can cleanly seal a serving guard; race close against disable/add in both
  orders and inject tightening durability failure plus process exit; prove the late action
  is either included before close or rejected/bound to a new verified epoch, while timeout,
  empty state, audit, or ordinary approval cannot seal;
  prove Alpha has one active serving authority and that a future unenumerated or
  non-acknowledging owner is isolated/terminated rather than allowed to continue egress;
  prove unrelated-room noninterference, verify enable preserves all entries and exact-
  room removal never enables global ingest, reject stale/concurrent generation updates,
  and make canonical/resource-binding or journal/recovery ambiguity invoke the explicit
  global-disable path rather than widening a generic pending guard;
- invalid room/session selector rejection, room-all-child and session-sibling exact-scope
  proofs, room-tombstone dominance, deletion partial failure, stateful/stateless pre-
  restore credential rejection, account/device cascade and new-authority denial,
  identity/device checkpoint replay, and fresh recovery-admin paths have negative tests
  or tabletop evidence appropriate to their Issue;
- monitoring and audit examples contain no audio, event body, transcript, email, secret,
  playback locator, or unsafe low-entropy/raw digest; and
- the review identifies exact code/config/runbook revisions without claiming provider,
  worker-host, backup-media, or external plaintext erasure beyond the documented control
  boundary.

Repository-owner threat-model approval: **PENDING**

Approver/date: **PENDING**

Approved revision: **PENDING**
