# Specification: Architecture, trust, data, and platform boundaries

Normative terms such as **must**, **must not**, and **may** apply to all later Livecho
Issues unless a repository-owner-approved ADR explicitly supersedes this decision.

## Behavior

### Architecture and allowed flows

The Alpha system must be a modular monolith. One backend deployment is authoritative
for authentication, room/session state, event ordering, worker leases, persistence,
kill-switch and denylist state, deletion manifests, and audit. Modules may have explicit
interfaces, but must not introduce a broker, peer-to-peer control plane, or separately
authoritative online service without a later accepted ADR and measured need. The Issue
#4 maintenance component is a trusted, non-serving, single-purpose job: it runs mutually
exclusively under an approved migration/deletion/recovery runbook with narrower
credentials and never becomes another application authority. The ADR must draw it.

The architecture decision record must draw these zones and flows:

| Zone | Trust decision | Allowed flow |
| --- | --- | --- |
| Browser | Public input and rendered content are untrusted. | Sends bounded viewer/auth/control requests to the backend; anonymously receives only the approved normalized live subset and, after authorization, permitted account/history state. Ordinary browser/API/cache paths never receive raw payloads. |
| Backend | Sole application authority and secret-bearing boundary. | Validates every crossing, owns sessions and leases, and mediates all external and managed-service access. |
| Bilibili | External, mutable, and untrusted platform boundary. | Through an approved acquisition channel, the backend adapter may request only an operator-selected, free, anonymous, currently live room and receive transient playback bytes/metadata plus scoped real-time danmaku, SC, status, and business payloads. Size/schema/credential/audio-field validation occurs before normalization or temporary raw handling. |
| Community worker | Untrusted for confidentiality, integrity, and availability even after device authentication. | Synthetic frames are the default. Production PCM requires the explicit rights/risk gate below; a conforming worker receives only bounded versioned ASR control/PCM frames and an allowlisted manifest and returns untrusted transcript/health frames. |
| Postgres | Managed processor with least-privilege backend access. | Stores restricted normalized events, minimal identity/device state, manifests, an append-only safety-control journal, and payload-free audit records after their owning Issues land. |
| Private Bucket | Managed high-risk processor isolated from ordinary APIs. | Stores only credential/audio-stripped, compressed, authenticated-encrypted raw business payloads/manifests after Issue #16 and an integrity-protected safety/deletion recovery copy kept separate from application-data backups. |
| Resend | External email processor. | Receives only the minimum invited address and one-time-link content required by Issue #12. |

The diagram must also show prohibited flows: ordinary browser-to-Bucket/raw,
browser-to-worker, worker-to-Bilibili/Postgres/Bucket/Resend, raw payload-to-public API,
playback locator or credential-to-worker, and audio-to-any persistent store. A worker
must never receive arbitrary OS/shell commands, an execution field, code, a container,
a download URL, or a non-allowlisted model. Versioned allowlisted ASR control messages
such as lease, heartbeat, cancel, and bounded frame metadata are not arbitrary commands.

Device authentication, signatures, version checks, and leases prove identity/protocol
state only; they do not prove the host runs an unmodified client or erased RAM. Before
the final owner decision, community workers receive synthetic audio only. Production
real PCM may be assigned only to an identified invited worker after the rights record
explicitly permits acquisition, transient transformation, and disclosure to that
third-party processor, and after the owner individually accepts
`RISK-WORKER-AUDIO-RETENTION` with scope, compensating controls, review date, and disable
owner. Every conforming Livecho worker implementation must remain zero-persistence and
clear audio RAM; malicious host copying remains a named High residual, never a claim of
technical erasure.

### Actors and permissions

Authorization defaults to deny. Documentation must preserve this minimum matrix:

| Actor | Permitted actions | Explicitly prohibited |
| --- | --- | --- |
| Anonymous viewer | Read only an approved normalized public live surface. | History/statistics, ingest, worker registration, raw/identity/secrets, or control state. |
| Invited viewer | Anonymous-viewer access plus authorized normalized history after Issues #12/#17. | Worker/statistics management, room control, raw access, global/denylist/role control. |
| Contributor | Invited-viewer access plus that contributor's own aggregate statistics after Issues #13/#17. | Device administration or registration-token issuance, room control, raw access, global enablement, denylist removal, role administration. |
| Operator | Select, start, and stop eligible rooms, add a room to the denylist, and invoke the global emergency disable. | Global re-enable, denylist removal, raw export, deletion completion, role/key/device administration. |
| Admin | Operator actions plus role/invite/device control, deletion requests, separately audited managed raw export, audited denylist removal, and technical re-enable after governance preconditions pass. | Bypassing owner risk/policy approval, exposing raw data to ordinary APIs, overriding a platform restriction. |
| Repository owner | Human governance approval for ADRs, source/rights basis, production global enablement, and residual risk. | This is not an application role and grants no implicit production credential access. |

### Kill switch and room denylist

- Production ingest must be globally disabled by default. A repository-owner decision
  may authorize enablement only after the approved ADR, current platform/rights review,
  incident procedure, deletion controls required for enabled persistence, and residual
  risks are recorded.
- An operator or admin may atomically disable global ingest or add a canonical room ID
  to the denylist. Only an admin may technically re-enable ingest or remove a denylist
  entry, and only with recorded owner approval for the triggering policy/risk review.
- Disable/enable and denylist add/remove operations use a monotonic safety generation and
  append-only journal. The current integrity-protected recovery copy is stored outside
  restorable application-data backups. A stale generation cannot overwrite a newer
  safety decision. If the journal/recovery-copy write is unavailable, emergency disable
  acts locally immediately and the system remains globally disabled; no unaudited
  enable/remove operation may succeed.
- Room aliases and URLs must resolve to a canonical platform room ID before eligibility
  or denylist checks. Failure, ambiguity, stale control state, or an unavailable
  configuration store is a denial, never a fallback.
- Disablement or a new denylist match must reject new starts/reconnects, terminate the
  active platform session, revoke any worker lease, stop using and clear local playback
  locators (request upstream revocation only where supported), clear audio buffers, hide
  pending publication, and append a payload-free audit event. The disable path must not
  depend on the failing ingest path.
- Every process start and every restore ignores any backed-up `enabled` value and begins
  globally disabled. Before an admin can re-enable, the system must reconcile the latest
  available safety generation, denylist journal, deletion tombstones, and owner approval
  against the separate recovery copy. Missing, stale, rolled-back, or conflicting state
  leaves ingest disabled.

### Public Bilibili eligibility

Only an operator/admin-selected room that is free, unauthenticated, not geographically
or DRM restricted, within documented rate limits, and currently live may be considered.
There is no public submission, auto-discovery, historical crawl, credentialed fallback,
or workaround. A field/schema change, login/cookie demand, payment/membership gate,
geographic/DRM restriction, rate-limit response, uncertain policy, or missing current
rights basis must stop the session and require review.

Public availability is not a redistribution grant. Before global production enablement,
the repository owner must approve a record containing the relevant official platform
terms/policies and version or effective date, the exact acquisition channel/API family
and applicable agreement, the project's permitted purpose and data use, and the rights
or written-license evidence for acquisition, transient transformation, disclosure to an
invited community worker, retention, and each public output. Owner approval cannot
substitute for platform or rights-holder permission. If an applicable term requires
written consent and that evidence is absent, the path stays off. The record must also
name a rights-holder/takedown contact and be rechecked at least every 90 days and whenever
an upstream behavior, policy, ownership, acquisition channel, or product use changes.

## Interfaces and compatibility

This Issue adds documentation only. Its implementation pull request must create:

- `docs/architecture/adr/0001-alpha-modular-monolith.md`;
- `docs/security/alpha-threat-model.md`;
- `docs/security/data-lifecycle-and-deletion.md`;
- `docs/policy/bilibili-public-ingest.md`;
- `docs/policy/independent-implementation.md`;
- `docs/operations/incident-disable-and-recovery.md`; and
- discoverable links from `README.md` and `SECURITY.md`.

The ADR must include a Mermaid trust/data-flow diagram whose source renders in GitHub.
It must include the Issue #4 maintenance job, safety recovery boundary, and separate
admin-export boundary in addition to the required zones. Supporting documents must use
stable threat, data-class, control, and decision identifiers so later Issues can cite
them. No runtime API, schema, CLI, UI, configuration, generated code, or protocol
compatibility field changes in this Issue. Wire formats remain reserved for Issue #3.

## Failure modes and disable path

- Missing/stale kill-switch or denylist state, uncertain canonical room identity, or
  policy/rights ambiguity fails closed before start and before every reconnect.
- Safety-journal write failure, control rollback/tampering, or an unauthorized re-enable
  acts as a global disable and a security alert; a restore never inherits enabled state.
- An invalid worker identity, signature, version, manifest, frame, epoch, size, rate, or
  timeout revokes the lease; late output is rejected and never becomes authoritative.
- Worker authentication/allowlisting does not prove code integrity or PCM erasure. Any
  real-audio use remains gated by the explicit third-party rights decision and named
  residual risk, and revocation limits future disclosure rather than claiming to erase a
  malicious host's copy.
- A platform response requiring credentials/payment or indicating a restriction stops
  ingest. There is no alternate scraper or endpoint fallback.
- Raw sanitization, encryption, key, audit, manifest, or storage failure prevents raw
  archival. It must not spill raw data into Postgres, logs, queues, or temporary files.
- Raw export authorization expiry can stop future access but cannot revoke plaintext
  already disclosed outside the managed boundary. Untracked local plaintext export is
  disabled by default and requires a separately accepted High residual if introduced.
- A deletion request first blocks ingest and public visibility. Any partial purge keeps
  the room/session blocked, records only payload-free failure metadata, and retries
  idempotently. It is never reported complete while an active store remains unchecked.
- A restore or disaster-recovery environment remains globally disabled and closed to
  traffic until the current safety/denylist state and deletion manifest have been
  replayed and their audit result is successful.
- For a security/platform incident, operator/admin global disablement is the immediate
  rollback. Re-enable requires cause remediation, current policy/rights confirmation,
  deletion replay where relevant, tabletop evidence, and recorded owner approval.

## Security, privacy, and data lifecycle

### Required data rules

| Data class | Location and lifetime | Access and deletion rule |
| --- | --- | --- |
| PCM, encoded audio, audio base64, stream buffers, and audio-bearing derivatives | Conforming backend/worker/decoder RAM only. Every representation covers at most 30 seconds of monotonic PTS/media time; missing, conflicting, or non-monotonic duration metadata is rejected from any retained buffer. Each s16le/16k/mono backend room/session and active worker lease separately has a hard aggregate 960,000-byte ceiling across rings, in-flight copies, and overlap. Alpha permits one active room and one active audio lease; standby workers receive no PCM until promotion. Every process has a 16,777,216-byte ceiling across all audio-bearing buffers, including decoder/transport internals. There is no audio retry queue: a retry may reference only data still inside the existing ring/in-flight budget. Issue #3/#8 may impose lower limits. Never disk, temp, database, queue, log, telemetry, crash dump, fixture, cache, or object storage. | Evict consumed frames immediately and clear on segment/session/lease completion, cancellation, timeout, disconnect, disable, denylist, and teardown. Conforming workers must clear RAM; hostile-host retention remains `RISK-WORKER-AUDIO-RETENTION`, not a deletion guarantee. Transcripts are restricted normalized events, not audio, and must not embed a recoverable audio representation. |
| Playback URL/token/cookie or upstream credential | Trusted backend ingest memory only for the active connect/refresh operation; never persisted or sent to a worker/browser. | Stop use, close the session, and clear the local reference on use, refresh, stop, disable, or error; request upstream revocation only where supported. Redact keys and values from every diagnostic. |
| Normalized event and room/session metadata | Restricted by default. Production Postgres persistence is disabled until Issue #16 controls and a current per-source/per-field purpose, publication decision, retention/review rule, and deletion trigger are approved. There is no platform-independent default TTL; a source-specific shorter/stricter rule wins and missing/expired evidence disables new persistence and publication. | Anonymous APIs expose only the approved live subset; invited history is separately authorized. Delete by canonical room/session: hide and block immediately, then purge active stores within 24 hours. |
| Sanitized raw business payload | Production persistence is disabled until the normalized-data gates plus Issue #16 sanitization/encryption controls pass. Then it may exist only in the private Bucket after credential, locator, excess identity, and all audio representations are rejected/removed and the payload is compressed and AES-256-GCM encrypted with separate keys. No platform-independent TTL overrides a source-specific rule. | Admin-only managed export with per-access audit; never ordinary/public API or browser cache. Delete room/session objects and versions within 24 hours. New persistence stops when source evidence is missing/expired. |
| Invite/account identity | Disabled until Issue #12. Then only the invited email, role, and minimum revocation/account state while the account remains active. | Subject/admin only. Revoke access immediately; on approved account deletion, purge identifying active-store fields within 24 hours and retain only the payload-free security/tombstone record below. |
| Authentication/enrollment bearer secret | Magic link: maximum 15 minutes and single-use. Worker enrollment token: maximum 24 hours and single-use. Database stores only a verifier hash and expiry/use state. Session cookie: maximum 30 days and individually revocable. Plaintext exists only in the intended Resend email or initiating client flow, never database/log/telemetry/URL analytics. | Expiry/use/revocation immediately prevents future acceptance. A previously delivered email may retain inert plaintext, but it cannot become valid again. Account/device deletion revokes related tokens/sessions immediately and purges active verifier/session rows within 24 hours. |
| Device identity and aggregate worker statistics | Disabled until Issue #13. Then only device public key, status, allowlisted capabilities, online/processed duration, success rate, RTF, and recent health while registered. | Contributor sees own aggregate statistics; admin manages devices. Revoke immediately; device/account deletion purges identifying active-store fields within 24 hours. |
| Security/control/raw-access audit | Append-only actor/control result, timestamps, object class, safety generation, and integrity metadata for 365 days. No event body, email, secret, playback locator, audio, transcript, or digest of a low-entropy/raw value. | Restricted admin/auditor access; after 365 days purge active audit rows within 24 hours unless a documented incident hold with owner and expiry applies. Integrity digests cover canonical manifest/control records using a keyed construction, never deleted content. |
| Deletion tombstone | Opaque room/session target, deletion state, safety generation, timestamps, and payload-free counts only. | Retain while any live/history data or backup can reintroduce the target, and at least through one successful post-backup-window restore verification. It is available to every restore and contains no raw/identity content. |
| Managed raw export | Disabled until Issue #16. Access capability maximum 15 minutes; encrypted managed export object maximum 24 hours. Default Alpha forbids untracked local plaintext copies. | Per-access admin audit; delete/revoke the managed object within 24 hours or immediately on room/session deletion. Authorization revocation does not claim erasure of already disclosed plaintext; allowing such disclosure requires a named High residual and bounded destination. |
| Cache, index, replica, object version, or backup | No independent source of truth. Active copies follow the 24-hour purge SLA. | Restore stays disabled/offline until current safety/denylist and deletion records replay. The implementation document must name/evidence each provider's maximum backup window; inability to bound/replay it blocks production persistence. |

Deletion is keyed by canonical `room_id` and immutable `session_id`, is idempotent, and
cascades through normalized rows, indexes, caches, manifests, raw objects/versions, and
managed exports. It exposes three distinct states: `hidden` immediately blocks public
visibility and ingest; `active-purge-complete` means every enumerated active store was
purged, with a completion timestamp; and `final-retention-window-satisfied` requires
`active-purge-complete`, managed export expiry, and expiration of every enumerated
provider-declared backup/object-version window or verifiable provider purge evidence.
Active purge has a 24-hour SLA, but a late successful retry still transitions to
`active-purge-complete` with an immutable `sla_breached=true` incident/audit result. This
final state proves the documented control/contract boundary, not physical media erasure.
A replay-protected but still retained backup is reported as such, never as final
satisfaction. Any unknown/untracked plaintext copy prevents the final state. Backups may
remain immutable only while inaccessible to application traffic and every restore
replays current tombstones before opening. Audit counts/keyed manifest digests and
failures never contain or hash raw/identity/transcript content.

### Threat model and clean-room controls

The threat model must record asset, actor, entry point, precondition, mitigation,
detection, response, residual severity, and owner for at least:

- platform/email/archive/database credential or playback-locator disclosure;
- malicious or compromised worker exfiltration, fabricated output, resource abuse, or
  denial of service;
- replay, forgery, stale epoch, duplicate, downgrade, and cross-session confusion;
- raw-payload or identity privilege escalation and browser rendering/XSS;
- incomplete deletion, stale caches/exports, and backup restore resurrection;
- safety-control rollback/tampering, lost denylist state, unauthorized re-enable, and
  audit-journal write failure;
- Bilibili interface, terms, rights, ownership, or rate-limit change;
- SSRF and redirect abuse in platform resolution; and
- maintainer/auth/key/supply-chain compromise.

Critical or High residual risk blocks production unless the repository owner explicitly
accepts that named residual risk with a date, scope, compensating control, review date,
and disable owner. A blanket approval is invalid.

Every external reference must record its canonical URL, immutable revision or captured
version, repository path/package, nearest governing license at that revision, material
consulted, and decision. Mixed repositories are reference-only by default until each
path is proven otherwise. AGPL, mixed-license, or unclear material is reference-only: do
not copy, translate, port, adapt, or derive source, tests, fixtures, schemas,
configuration, comments, documentation text, or assets. Before implementation, authors
record prior exposure and do not inspect prohibited material. An author with material
prior exposure may not implement the corresponding behavior/module unless an independent
license/legal review records that the exposure was limited to unprotectable facts or
public requirements; implementers receive only independently written requirements. A
separate reviewer may perform post-implementation similarity review without relaying
protected expression.
Any approved MIT copying must preserve its copyright and permission notice and map the
source revision/path to the destination path; attribution is not optional. This Issue
itself copies none. Model weights and datasets require separate license approval.

## Acceptance criteria

- [ ] The ADR and Mermaid diagram cover browser, backend, Bilibili, community worker,
  Postgres, private Bucket, and Resend, including all named trust/no-flow boundaries.
- [ ] The role matrix, global-default-off switch, denylist precedence, immediate stop,
  durable safety generation, restore-forced-off behavior, fail-closed lookup, and
  owner-controlled re-enable rules are independently traceable.
- [ ] The threat model covers every required Issue threat plus SSRF, untrusted rendering,
  worker abuse, auth/key/supply-chain compromise, with owned residual risk.
- [ ] The lifecycle matrix covers every data class, location, access, retention/deletion
  bounds and triggers, three deletion states, audit content, export/backup behavior, and
  production prerequisite.
- [ ] The approved documents define the 30-second media-time window, 960,000-byte
  canonical-PCM session/lease ceiling, fixed process/concurrency cap, prohibited
  persistent/logging/crash paths, malicious-worker gate, and backend-only playback
  credentials; they assign executable enforcement evidence to Issues #3, #8, #14, and
  #15 without claiming runtime enforcement in this documentation-only Issue.
- [ ] A room/session takedown tabletop proves immediate visibility/ingest blocking,
  idempotent active-store purge, partial-failure handling, and deletion replay before
  restored traffic.
- [ ] The Bilibili policy records current authoritative sources, version/date, eligible
  room rules, acquisition channel/applicable terms, permission evidence, review triggers,
  worker disclosure, takedown path, and owner-approved rights basis without equating
  public viewing with redistribution permission.
- [ ] The independent-implementation policy pins path-level upstream revisions/licenses,
  prohibits copying AGPL/mixed/unclear material, preserves mandatory MIT notices, and
  records separated author exposure and reviewer provenance attestations.
- [ ] `README.md` and `SECURITY.md` link the approved records; no runtime/deployment
  resource is changed; deterministic repository checks pass.
- [ ] @Shuang-su explicitly approves the final ADR and each accepted Critical/High
  residual risk before production enablement.
