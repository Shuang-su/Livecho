# Requirements and evidence index

Reviewed 2026-10-03 (Asia/Shanghai) against repository baseline
`93d8b0a4b3e147ce0b7df903f118060117d56f0a`. Maintenance owner:
[Issue #30](https://github.com/Shuang-su/Livecho/issues/30). Audit and historical
snapshots: [implementation evidence](changes/30-requirements-evidence-index/evidence.md).
Current direct planning edges: [roadmap](roadmap.md).

This is secondary navigation, not a normative decision. Accepted Issue artifacts define
approved contracts. Supporting records retain their own approval state; an ADR merge
does not approve its pending decisions or individually accept a risk. GitHub state,
paper review, deterministic tests, runtime measurements, hardware results, provider
observations, external permission and owner decisions are distinct facts. A newer text
or closed Issue does not supersede an accepted requirement.

## How to read a record

Each row is one record, completed by its linked evidence profile. The row gives an ID,
summary, exactly one primary file/section, implementation/evidence owners, capability
and stage. The profile supplies source/governance state, implemented scope and revision,
dated evidence category/result/limits, and missing-decision/evidence blocker. Profiles
are shared prose, not combined readiness scores. Owners in the tables are implementation/
evidence owners; definition ownership is stated for each table. #30 owns navigation only.
Issue numbers resolve through the [direct dependency table](roadmap.md#direct-dependency-snapshot).

Stage codes: **O** repository/offline contract; **L** local synthetic caption path;
**H** trusted hardware; **R** platform or real input; **D** distributed/identity/persistence;
**P** provider staging/production. A scope condition activates only the named capability
gate. Universal audio, secret, distrust and compatibility boundaries apply wherever the
relevant data or interface exists, including L. Production rights/provider/risk decisions
are not new prerequisites for an unrelated short synthetic demonstration.

Evidence results are passed, failed, pending, missing or not applicable with a reason.
Historical passes remain historical. No runtime, hardware or provider verification was
performed by this documentation change. Restricted operational evidence must use an
authorized opaque reference, never an embedded payload or credential.

## Evidence profiles

<a id="foundation"></a>
**F — accepted foundation.** Definition #1, [approval][e1-approval] and [evidence][e1],
[merged PR #20](https://github.com/Shuang-su/Livecho/pull/20), merge `f57780e`.
Offline evidence passed: `make bootstrap`, `make verify`, 40 pytest tests and lifecycle
regressions, 2026-08-24 PR tree. Repository lifecycle checks exist; human merge authority
is a process requirement, not inferred from a test. Runtime/hardware/provider evidence
is not applicable to these repository checks. No missing capability gate is introduced.

<a id="design"></a>
**D — required design, runtime not established.** Definition #2 accepted
[artifact/spec][s2] and [approval record][e2]; supporting records merged through
[PR #22](https://github.com/Shuang-su/Livecho/pull/22), `0331db6`.
Their constraints apply, but the ADR and threat record explicitly remain **Proposed**;
[ADR decisions][adr-status] and [individual risk decisions][risk-decisions] are pending.
Document/paper evidence passed: #2 `make verify`, source/control/link audit and paper
review, 2026-08-24 final documentation tree. This establishes no runtime enforcement.
For each row, runtime evidence is **missing** unless a separately linked O profile names
its narrow implemented part. The row's owners must supply the source's executable
acceptance evidence before enabling its capability. Required owner decisions remain
pending only at their stated scope. Hardware/provider evidence is missing where that
capability needs it, otherwise not applicable; this profile does not turn every D row
into a production gate for local work.

<a id="protocol"></a>
**V — accepted protocol, offline implementation.** Definition #3;
[artifact approval][e3-artifact], [implementation approval][e3-approval] and
[exact checks][e3]; artifact PR #23 and
[implementation PR #24](https://github.com/Shuang-su/Livecho/pull/24),
merge `982fc37`. Offline contract verification **passed** at `978673b`,
2026-08-30: `make verify` (107 pytest, 128 protocol Vitest), `make protocol-check`,
focused transactional rejection tests; subsequent boundary fixes retain dated evidence
in the same record. Pydantic source and generated Schema/TypeScript/golden corpus exist.
Runtime integration is **missing**, not inferred from validator success. Owning runtime
Issues supply it; #27 long-session and #28 real-input gaps are separate records below.
Hardware/provider evidence is not applicable to the pure protocol result.

<a id="railway"></a>
**W — accepted offline Railway contract.** Definition #4,
[artifact approval][e4-approval] and [implementation evidence][e4], artifact PR #25 and
[implementation PR #26](https://github.com/Shuang-su/Livecho/pull/26),
merge `67fc6ed`. Offline verification **passed**, 2026-08-31,
`46f886e`: `make verify`, `make railway-check`, 63 focused Vitest cases and
independent constant/mutation checks. Desired-state rendering and fail-closed command
guards exist. Provider resources, maintenance runtime, canary, deployment and restore
evidence are **missing**. The row's owning implementation/operation must satisfy the
linked contract in the exact environment before live use; O work has no provider-token
prerequisite. Hardware evidence is not applicable.

<a id="policy"></a>
**B — dated platform record, permission missing.** Definition #2;
[policy decision][b-current] and [source register][b-sources] record the 2026-08-24
review. These merged local records report historical official sources; #30 neither
revisits external pages nor grants a legal conclusion. Channel selection is unselected;
each rights row lacks issuer/scope/expiry evidence. Runtime and current permission are
**missing**, owner production-enable decision **pending**, production **OFF**.
The platform/policy owner and repository owner must complete [review/enablement][b-review],
including at-least-90-day/change review, exact channel and reachable contacts.
Each separate right requires its own platform/right-holder evidence; owner approval
cannot replace it. These R/P conditions do not block purely synthetic L work.

<a id="license"></a>
**I — accepted independent-source requirement.** Definition #2;
[policy][lic-current], [#2 evidence][e2], merged documentation `0331db6`.
Document constraint/paper review is the evidence category; copying remains prohibited
under the current decision. Later authors need fresh exposure/assignment, independent
review, exact approved notice mapping for any future MIT copy, and separate dependency/
model/dataset approval. Evidence is **missing until the owning implementation records
it**; the blocker applies before its corresponding authorship, merge or artifact use,
not only production. No blanket eligibility or legal conclusion is inferred here.

<a id="pending"></a>
**N — planned capability.** The linked Issue defines planning ownership, not accepted
implementation requirements. At this baseline implementation/runtime evidence is
**not established**. Its own accepted artifacts, implementation and scoped verification
must precede a claim of availability; no new dependency is invented. #5/#8 are the
explicit exceptions with accepted specifications linked below; their runtime evidence
still remains missing. H/P evidence and owner approvals are required only where the
owning source says so.

## Repository lifecycle and architecture

Definition owners are #1 for F and #2 for D. Detailed role and trust restrictions remain
in [minimum role matrix][roles], [trust zones][zones], and accepted [#2 spec][s2].

| ID and requirement | Primary definition | Evidence owners; capability/stage | Profile |
| --- | --- | --- | --- |
| IDX-ARTIFACT-LIFECYCLE — owner merges artifacts before implementation | [Change lifecycle](../CONTRIBUTING.md#change-lifecycle) | #1; every implementation/O | [F](#foundation) |
| IDX-ARTIFACT-DURABILITY — preserve accepted intent/spec/plan and exact evidence | [Versioned records](changes/README.md) | #1; repository changes/O | [F](#foundation) |
| IDX-ROLE-MATRIX — deny-by-default distinct viewer/contributor/operator/admin/owner authority | [Minimum roles][roles] | #12/#13/#17; identity/action authorization/D,R,P | [D](#design) |
| DEC-ARCH-001 — single authoritative modular-monolith backend | [One online authority][dec-arch] | #3/#7/#8/#10/#12–#16/#19 per [follow-on obligations][follow]; online application/L,D,R,P | [D](#design) |
| DEC-MAINT-001 — mutually exclusive, non-serving maintenance | [Maintenance exception][dec-maint] | #4/#16/#19; maintenance/D,P | [D](#design), [W](#railway) |
| DEC-SAFETY-001 — current safety/intake continuity outranks restored data | [Safety authority][dec-safety] | #4/#7/#12/#13/#16/#17/#19; safety/recovery/D,R,P | [D](#design) |
| DEC-WORKER-001 — hostile-capable workers, synthetic default | [Worker trust][dec-worker] | #3/#8/#9/#13/#14/#15; worker input/L,D,R,P | [D](#design), [V](#protocol) |
| DEC-DATA-001 — mediated restricted persistence | [Data authority][dec-data] | #10/#12/#13/#16/#17; persistence/D,P | [D](#design) |
| DEC-EXPORT-001 — separately managed encrypted admin export | [Export boundary][dec-export] | #16/#17; raw export/D,P | [D](#design) |
| GATE-ADR-OWNER — final ADR approval | [Production gate record][gates] | repository owner; production/P | [D](#design) |
| GATE-PLATFORM-RIGHTS — current exact channel and purpose rights | [Production gate record][gates] | policy/repository owner; platform/R,P | [B](#policy) |
| GATE-SAFETY-RUNTIME — executable safety and restore controls | [Production gate record][gates] | #4/#7/#12/#13/#16/#17/#19; production auth/ingest/P | [D](#design) |
| GATE-PERSISTENCE — complete data/deletion/recovery evidence | [Production gate record][gates] | #16; persistence/export/D,P | [D](#design) |
| GATE-WORKER-PCM — disclosure rights and individual retention-risk decision | [Production gate record][gates] | policy/repository owner, #8/#13/#14/#15; real community PCM/R,P | [D](#design), [B](#policy) |
| GATE-RESIDUAL-RISK — individual Critical/High decisions | [Production gate record][gates] | repository owner; each named production capability/P | [D](#design) |

## Allowed and prohibited flows

Definition #2, primary ADR registries; endpoint meaning is supported by the
[flow diagram][diagram]. Each flow retains its source's full condition and failure
posture. Evidence ownership below follows [assigned capability obligations][follow];
it is not an authorization to implement a new interface. Every row uses [D](#design):
runtime evidence missing, blocked only when attempting the named flow. [V](#protocol)
proves bounded message validation only; [W](#railway) proves offline guards only.

| ID and requirement | Primary definition | Evidence owners; capability/stage | Profile |
| --- | --- | --- | --- |
| FLOW-ALLOW-001 — Bounded authorized browser requests | [Allowed registry][allow] | #12/#17; browser request/L,D | [D](#design) |
| FLOW-ALLOW-002 — Approved normalized live subset or authorized history | [Allowed registry][allow] | #11/#12/#16/#17; publication/history/L,D,R | [D](#design) |
| FLOW-ALLOW-003 — Action-authorized admin request, no implicit governance | [Allowed registry][allow] | #12/#17; admin/D | [D](#design) |
| FLOW-ALLOW-004 — Selected canonical eligible current-live acquisition | [Allowed registry][allow] | #7; platform/R | [D](#design) |
| FLOW-ALLOW-005 — Eligible transient media/events, validate before handling | [Allowed registry][allow] | #7/#10; platform input/R | [D](#design) |
| FLOW-ALLOW-006 — Bounded versioned synthetic frames; real PCM separately gated | [Allowed registry][allow] | #3/#8/#14/#15; worker input/L,D,R | [D](#design) |
| FLOW-ALLOW-007 — Validate untrusted transcript and health | [Allowed registry][allow] | #3/#13/#14/#15; worker output/L,D | [D](#design) |
| FLOW-ALLOW-008 — Restricted normalized/minimal identity/control/audit to Postgres | [Allowed registry][allow] | #12/#13/#16; persistence/D | [D](#design) |
| FLOW-ALLOW-009 — Sanitized compressed authenticated-encrypted raw to Bucket | [Allowed registry][allow] | #10/#16; archive/D,R | [D](#design) |
| FLOW-ALLOW-010 — Minimum invited address and one-time link to Resend | [Allowed registry][allow] | #12; email identity/D | [D](#design) |
| FLOW-ALLOW-011 — Protected ordered safety/deletion/revocation recovery copy | [Allowed registry][allow] | #4/#12/#13/#16/#19; recovery/D,P | [D](#design) |
| FLOW-ALLOW-012 — Application backup to offline maintenance restore | [Allowed registry][allow] | #4/#16/#19; restore/P | [D](#design) |
| FLOW-ALLOW-013 — Recovery copy to isolated replay/credential invalidation | [Allowed registry][allow] | #4/#12/#13/#16/#19; restore/P | [D](#design) |
| FLOW-ALLOW-014 — Exclusive maintenance to Postgres | [Allowed registry][allow] | #4/#16/#19; maintenance/P | [D](#design) |
| FLOW-ALLOW-015 — Exclusive maintenance to Bucket | [Allowed registry][allow] | #4/#16/#19; maintenance/P | [D](#design) |
| FLOW-ALLOW-016 — Reconciled maintenance update to recovery copy | [Allowed registry][allow] | #4/#16/#19; recovery/P | [D](#design) |
| FLOW-ALLOW-017 — Managed gate creates bounded encrypted export | [Allowed registry][allow] | #16; export/D,P | [D](#design) |
| FLOW-ALLOW-018 — Backend authorizes and audits export gate | [Allowed registry][allow] | #16/#17; export/D,P | [D](#design) |
| FLOW-ALLOW-019 — Encrypted Bucket source through managed gate | [Allowed registry][allow] | #16; export/D,P | [D](#design) |
| FLOW-ALLOW-020 — Audited bounded retrieval by admin | [Allowed registry][allow] | #16/#17; export/D,P | [D](#design) |
| FLOW-DENY-001 — No ordinary browser raw/Bucket access | [No-flow registry][deny] | #16/#17; browser/storage/D | [D](#design) |
| FLOW-DENY-002 — No browser-to-worker channel | [No-flow registry][deny] | #3/#14; worker transport/L,D | [D](#design) |
| FLOW-DENY-003 — No worker-to-platform path | [No-flow registry][deny] | #7/#14; worker isolation/L,D,R | [D](#design) |
| FLOW-DENY-004 — No worker-to-Postgres path | [No-flow registry][deny] | #14/#16; worker isolation/L,D | [D](#design) |
| FLOW-DENY-005 — No worker-to-Bucket path | [No-flow registry][deny] | #14/#16; worker isolation/L,D | [D](#design) |
| FLOW-DENY-006 — No worker-to-Resend path | [No-flow registry][deny] | #12/#14; worker isolation/L,D | [D](#design) |
| FLOW-DENY-007 — No backend credentials, locators or keys to workers | [No-flow registry][deny] | #3/#7/#13/#14; secret isolation/L,D,R | [D](#design) |
| FLOW-DENY-008 — No audio to Postgres | [No-flow registry][deny] | #8/#16; audio/O,L,D,R | [D](#design) |
| FLOW-DENY-009 — No audio to Bucket | [No-flow registry][deny] | #8/#16; audio/O,L,D,R | [D](#design) |
| FLOW-DENY-010 — No raw to ordinary API/cache/public surface | [No-flow registry][deny] | #16/#17; raw/D,R | [D](#design) |
| FLOW-DENY-011 — Application backup cannot overwrite current recovery authority | [No-flow registry][deny] | #4/#16/#19; restore/D,P | [D](#design) |
| FLOW-DENY-012 — No serving interface to maintenance job | [No-flow registry][deny] | #4/#19; maintenance/P | [D](#design) |
| FLOW-DENY-013 — No maintenance-to-platform path | [No-flow registry][deny] | #4/#7/#19; maintenance/P | [D](#design) |
| FLOW-DENY-014 — No maintenance-to-worker path | [No-flow registry][deny] | #4/#14/#19; maintenance/P | [D](#design) |
| FLOW-DENY-015 — No maintenance-to-email path | [No-flow registry][deny] | #4/#12/#19; maintenance/P | [D](#design) |
| FLOW-DENY-016 — No audio to application backup | [No-flow registry][deny] | #8/#16/#19; audio/O,L,D,R,P | [D](#design) |
| FLOW-DENY-017 — No audio to recovery copy | [No-flow registry][deny] | #8/#16/#19; audio/O,L,D,R,P | [D](#design) |
| FLOW-DENY-018 — No audio to managed export | [No-flow registry][deny] | #8/#16; audio/O,L,D,R | [D](#design) |

## Controls

Definition #2. The threat model's [required control catalog][controls] enumerates all
thirty controls and their evidence owners. The [incident registry][i-controls] explicitly
assigns six shared control definitions to the [lifecycle registry][l-controls]; those
rows use that primary pointer below. Their detailed [audio limits][audio],
[identity/recovery rules][identity], [deletion sequence][delete-sequence],
[lifecycle matrix][data-matrix] and [backup/provider evidence][provider] remain supporting
definitions. The remaining catalog entries retain their primary catalog pointer;
matching lifecycle and incident entries support them without creating precedence.
[Required response invariants][responses] and [runbook evidence handoff][handoff] retain
all failure/race/tabletop obligations. A short summary never narrows that source text.
Where #3 or #4 is listed, only the relevant [V](#protocol)/[W](#railway) offline subset
exists; complete live control remains unestablished under D.

| ID and requirement | Primary definition | Evidence owners; capability/stage | Profile |
| --- | --- | --- | --- |
| CTRL-AUTHZ-DENY-BY-DEFAULT — Object/action authorization; owner governance stays out of band | [Control catalog][controls] | #12/#13/#16/#17; authorization/D | [D](#design) |
| CTRL-DATA-RESTRICTED-DEFAULT — Per-source/per-field purpose, audience, retention and deletion | [Control catalog][controls] | #10/#12/#13/#16/#17; data/D,R | [D](#design) |
| CTRL-SECRET-CONTAINMENT — Least-privilege backend secrets, RAM locators, redaction and rotation | [Control catalog][controls] | #4/#7/#12/#16/#19; secrets/L,D,R,P | [D](#design) |
| CTRL-SAFETY-DEFAULT-OFF — No restored activation; verified continuity before traffic | [Control catalog][controls] | #4/#7/#16/#19; startup/recovery/D,R,P | [D](#design) |
| CTRL-SAFETY-GENERATION — Orthogonal global/room state, exact-head transitions and guards | [Control catalog][controls] | #4/#7/#16/#17/#19; safety/D,R,P | [D](#design) |
| CTRL-ROOM-DENYLIST — Canonical exact-room scope; transient offline is not denylisting | [Control catalog][controls] | #7/#16/#17; eligibility/safety/R,D | [D](#design) |
| CTRL-DISABLE-CLEANUP — Global cleanup before durability; room cleanup preserves unrelated rooms | [Control catalog][controls] | #7/#8/#11/#14/#15/#16/#17/#19; stop paths/L,D,R,P | [D](#design) |
| CTRL-RESTORE-REPLAY — Isolated replay, old credential rejection, fresh activation | [Lifecycle registry][l-controls] | #4/#12/#13/#16/#19; restore/D,P | [D](#design) |
| CTRL-IDENTITY-RESTORE-REVOCATION — Pending before effects, typed checkpoint or durable denial | [Lifecycle registry][l-controls] | #4/#12/#13/#16/#17/#19; identity deletion/revocation/D,P | [D](#design) |
| CTRL-REENABLE-GATE — Admin execution after exact scoped owner decision and evidence | [Control catalog][controls] | #7/#16/#17/#19; relaxation/R,D,P | [D](#design) |
| CTRL-AUDIT-PAYLOAD-FREE — Append control metadata without protected payloads | [Lifecycle registry][l-controls] | #12/#13/#16/#17/#19; audit/D,P | [D](#design) |
| CTRL-WORKER-SYNTHETIC-ONLY — Synthetic until separate rights and High-risk gates pass | [Control catalog][controls] | #8/#9/#14/#15; worker input/L,D,R | [D](#design) |
| CTRL-WORKER-PROTOCOL — Bounded versioned ASR, identity and allowlisted manifests | [Control catalog][controls] | #3/#13/#14/#15; worker protocol/O,L,D | [D](#design) |
| CTRL-WORKER-REVOCATION — Reject late/invalid output; revoke and quarantine | [Control catalog][controls] | #13/#14/#15; worker lifecycle/D | [D](#design) |
| CTRL-AUDIO-RAM-ONLY — 30 s media, 960,000 canonical bytes, 16 MiB all-audio and cleanup | [Lifecycle registry][l-controls] | #3/#8/#14/#15; all audio/O,L,D,R | [D](#design) |
| CTRL-PLATFORM-FAIL-CLOSED — Selected free anonymous unrestricted current-live input only | [Control catalog][controls] | #7/#10/#19; platform/R,P | [D](#design) |
| CTRL-PLATFORM-RIGHTS-REVIEW — Exact source/channel/purpose/disclosure and current review | [Control catalog][controls] | policy/repository owner before #7 production; platform/R,P | [D](#design) |
| CTRL-SSRF-RESOLUTION — Allowlisted channel and every redirect/DNS destination | [Control catalog][controls] | #7/#19; resolver/R,P | [D](#design) |
| CTRL-EVENT-VALIDATION — Bound schema/size, credentials/audio and session/publication fields | [Control catalog][controls] | #3/#7/#10; untrusted events/O,L,R | [D](#design) |
| CTRL-RAW-BOUNDARY — Sanitize, compress, encrypt; no ordinary API or spill | [Control catalog][controls] | #10/#16; raw archive/D,R | [D](#design) |
| CTRL-RAW-EXPORT — Admin audit, 15-minute capability, 24-hour encrypted object | [Control catalog][controls] | #16/#17; raw export/D,P | [D](#design) |
| CTRL-DELETION-STATE — One typed selector, immutable intake time, verified hidden admission | [Control catalog][controls] | #16; deletion/D,P | [D](#design) |
| CTRL-BACKUP-EVIDENCE — Enumerated copies/windows and provider evidence | [Lifecycle registry][l-controls] | #4/#12/#13/#16/#19; backup/restore/D,P | [D](#design) |
| CTRL-DELETION-FAIL-CLOSED — Exact containment, continuity, no guessed admission/purge | [Lifecycle registry][l-controls] | #11/#12/#13/#16/#17; deletion/identity/D,P | [D](#design) |
| CTRL-RENDER-UNTRUSTED — Escape data, constrain URLs and content policy | [Control catalog][controls] | #10/#11/#17; rendering/L,D,R | [D](#design) |
| CTRL-AUTH-EXPIRY — Single-use bounded bearer lifetime and verifier-only storage | [Control catalog][controls] | #12/#13; authentication/D | [D](#design) |
| CTRL-AUTH-KEY-LIFECYCLE — Revocable identity, key separation, rotation and restore rejection | [Control catalog][controls] | #4/#12/#13/#16/#19; identity/secrets/D,P | [D](#design) |
| CTRL-MAINTENANCE-EXCLUSIVE — Approved non-serving operation with narrow temporary authority | [Control catalog][controls] | #4/#16/#19; maintenance/P | [D](#design) |
| CTRL-SUPPLY-CHAIN — Pinned reviewed dependencies, manifests and release provenance | [Control catalog][controls] | #1/#4/#18/#19; build/artifact use/O,L,H,D,P | [D](#design) |
| CTRL-INCIDENT-DISABLE — Ingest-independent disable, response and reviewed re-enable | [Control catalog][controls] | #17/#19; incident/R,D,P | [D](#design) |


## Threats and individual residual decisions

Definition #2, primary [threat register][threats]. Each row's detection, response and
named human disable owner remain in that exact source row. All thirteen High residuals
are individually **NOT ACCEPTED** in the supporting [decision register][risk-decisions];
only the repository owner can change that state with the named scope, controls, review
date and disable owner. Medium rows still require controls. Risk severity assumes those
controls exist; it does not describe a passed implementation. No Critical row is listed.
No risk acceptance is required here merely to write offline/local code.

| ID and requirement | Primary definition | Evidence owners; capability/stage; residual | Profile |
| --- | --- | --- | --- |
| THREAT-SECRET-DISCLOSURE — Secret disclosure | [Threat register][threats] | #4/#7/#12/#16/#19; secrets/R,D,P; High | [D](#design) |
| THREAT-RAW-IDENTITY-PRIVESC — Raw/identity privilege escalation | [Threat register][threats] | #12/#16/#17; data access/D,P; High | [D](#design) |
| THREAT-BROWSER-XSS — Untrusted rendered data | [Threat register][threats] | #10/#11/#17; Web/L,D,R; Medium | [D](#design) |
| THREAT-RAW-ARCHIVE-SPILL — Raw spill on validation/encryption/storage failure | [Threat register][threats] | #10/#16/#19; archive/D,R,P; High | [D](#design) |
| RISK-RAW-PLAINTEXT-EXPORT — Recipient plaintext cannot be recalled | [Threat register][threats] | #16/#17; plaintext export/D,P; High; prohibited | [D](#design) |
| THREAT-WORKER-EXFILTRATION — Worker crosses secret/service boundary | [Threat register][threats] | #13/#14/#15; worker/L,D; Medium | [D](#design) |
| RISK-WORKER-AUDIO-RETENTION — Hostile worker retains disclosed PCM | [Threat register][threats] | #8/#13/#14/#15; real community PCM/R,P; High; synthetic only | [D](#design) |
| THREAT-WORKER-FABRICATED-OUTPUT — Forged transcript/health is not authoritative | [Threat register][threats] | #3/#9/#13/#14/#15; worker output/L,D; Medium | [D](#design) |
| THREAT-WORKER-RESOURCE-ABUSE — Worker exhausts resources or safety cleanup | [Threat register][threats] | #13/#14/#15/#19; worker/D,P; Medium | [D](#design) |
| THREAT-WORKER-CONTROL-INJECTION — No shell/code/container/download-command control | [Threat register][threats] | #3/#6/#13/#14/#18; worker interface/O,L,D; Medium | [D](#design) |
| THREAT-PROTOCOL-REPLAY-FORGERY — Replay, forgery and compatibility-field misuse | [Threat register][threats] | #3/#13/#14/#15; protocol/O,L,D; Medium | [D](#design) |
| THREAT-DELETION-INCOMPLETE — Lost admission/time, wrong scope, missed copies/authority | [Threat register][threats] | #12/#13/#16/#17; deletion/D,P; High | [D](#design) |
| THREAT-RESTORE-RESURRECTION — Restore revives data, credentials or activation | [Threat register][threats] | #4/#12/#13/#16/#19; restore/D,P; High | [D](#design) |
| THREAT-SAFETY-ROLLBACK — Stale safety, lost control or wrong cleanup scope | [Threat register][threats] | #7/#16/#17/#19; safety/R,D,P; High | [D](#design) |
| THREAT-AUDIT-JOURNAL-FAILURE — Unavailable/ambiguous/payload-bearing audit or recovery writes | [Threat register][threats] | #16/#17/#19; audit/recovery/D,P; Medium | [D](#design) |
| THREAT-PLATFORM-CHANGE — Changed policy/rights/schema versus ordinary offline status | [Threat register][threats] | #7/#10/#19; platform/R,P; High | [D](#design) |
| THREAT-SSRF-REDIRECT — Untrusted resolution reaches privileged destinations | [Threat register][threats] | #7/#19; resolver/R,P; High | [D](#design) |
| THREAT-MAINTAINER-TAKEOVER — Privileged maintenance/release misuse | [Threat register][threats] | #1/#4/#16/#19; maintenance/release/O,P; High | [D](#design) |
| THREAT-AUTH-KEY-COMPROMISE — Stolen/replayed/restored identity or key | [Threat register][threats] | #4/#12/#13/#16/#17/#19; identity/key/D,P; High | [D](#design) |
| THREAT-SUPPLY-CHAIN-COMPROMISE — Unreviewed/tampered source, dependency, model or release | [Threat register][threats] | #1/#4/#18/#19; supply chain/O,H,P; High | [D](#design) |


## Data lifecycle and recovery

Definition #2. Each class has exactly one primary [normative lifecycle row][data-matrix].
Owners follow the source's [implementation/evidence assignment][data-owners] and shared
control registries. Supporting [audio invariants][audio], [identity restore][identity],
[deletion state machine][deletion] and [provider evidence][provider] retain all detailed
limits. Active purge's 24-hour rule does not imply final backup/export erasure.
`hidden`, `active-purge-complete`, and `final-retention-window-satisfied` are distinct;
unverified admission never authorizes purge. No physical-media erasure is claimed.

| ID and requirement | Primary definition | Evidence owners; capability/stage | Profile |
| --- | --- | --- | --- |
| DATA-AUDIO-EPHEMERAL — Audio RAM only; immediate scoped cleanup | [Lifecycle matrix][data-matrix] | #3/#8/#14/#15; audio/O,L,D,R | [D](#design) |
| DATA-PLAYBACK-SECRET — Backend memory only during active connect/refresh | [Lifecycle matrix][data-matrix] | #7; locator/R | [D](#design) |
| DATA-NORMALIZED-EVENT — Restricted source-specific fields; no default retention grant | [Lifecycle matrix][data-matrix] | #10/#16/#17; timeline/history/D,R | [D](#design) |
| DATA-RAW-BUSINESS — Sanitized compressed AES-256-GCM private archive | [Lifecycle matrix][data-matrix] | #10/#16; raw/D,R | [D](#design) |
| DATA-ACCOUNT-IDENTITY — Minimum invited identity; deletion/revocation checkpoint | [Lifecycle matrix][data-matrix] | #12; account/D | [D](#design) |
| DATA-AUTH-BEARER — 15-minute magic link, 24-hour enrollment, 30-day session maxima | [Lifecycle matrix][data-matrix] | #12/#13; authentication/D | [D](#design) |
| DATA-WORKER-DEVICE — Minimum device identity and contributor-own aggregates | [Lifecycle matrix][data-matrix] | #13; device/statistics/D | [D](#design) |
| DATA-AUDIT — Payload-free restricted audit; 365-day rule and scoped incident hold | [Lifecycle matrix][data-matrix] | #12/#13/#16/#17/#19; audit/D | [D](#design) |
| DATA-DELETION-TOMBSTONE — Typed room/session hidden tombstone; intake is not admission | [Lifecycle matrix][data-matrix] | #16; deletion/D,P | [D](#design) |
| DATA-IDENTITY-REVOCATION-CHECKPOINT — Protected typed pseudonymous target outcome and restore replay | [Lifecycle matrix][data-matrix] | #4/#12/#13/#16/#17/#19; identity recovery/D,P | [D](#design) |
| DATA-MANAGED-RAW-EXPORT — 15-minute access, 24-hour encrypted managed object | [Lifecycle matrix][data-matrix] | #16/#17; export/D,P | [D](#design) |
| DATA-DERIVED-COPY — Enumerated caches/versions/backups; exact replay before traffic | [Lifecycle matrix][data-matrix] | #4/#12/#13/#16/#19; derived copies/restore/D,P | [D](#design) |
| IDX-DELETION-SCOPE — room-all-sessions versus exact immutable session; dominance | [Deletion state machine][deletion] | #16; deletion/D,P | [D](#design) |
| IDX-DELETION-ADMISSION — immutable request time; hidden commit/read-back before acceptance/purge | [Required deletion sequence][delete-sequence] | #16; deletion/D,P | [D](#design) |
| IDX-IDENTITY-INTAKE — pending before validation/effects; checkpoint or durable denial | [Identity revocation][identity] | #12/#13/#16; identity/D,P | [D](#design) |
| IDX-RECOVERY-CONTINUITY — isolated replay, apply, reconcile, old close, new open, fresh activation | [Startup/restore][restore] | #4/#12/#13/#16/#19; recovery/D,P | [D](#design) |
| IDX-SAFETY-SCOPES — global G and room Q, local effects before durable awaits | [Durable safety state][safety-state] | #7/#16/#17/#19; safety/R,D,P | [D](#design) |
| IDX-RELAXATION — global commit before activation; room permit before promotion | [Safe transition rules][transitions] | #7/#16/#17/#19; re-enable/R,D,P | [D](#design) |
| IDX-AUDIT-FIELDS — no protected payload or target identity in control audit | [Payload-free audit][audit-fields] | #12/#13/#16/#17/#19; audit/D,P | [D](#design) |
| IDX-TABLETOPS — disable, scoped denylist, deletion, stale restore, hostile worker | [Required tabletops][tabletops] | #4/#7/#8/#12/#13/#14/#15/#16/#17/#19 per [handoff][handoff]; operational acceptance/R,D,P | [D](#design) |


## Platform and independent implementation

Platform definition #2; policy/evidence owners are the platform-policy and repository
owners plus #7 acquisition, #10 normalization, #16 retention/deletion and #17 controls
as applicable. The six permission records are independent; all are missing, not waived.
Historical source records establish only what was reviewed then. Rights records must
name issuer, recipient, purpose, scope, issue/review/expiry dates and revocation terms.

| ID and requirement | Primary definition | Evidence owners; capability/stage | Profile |
| --- | --- | --- | --- |
| BILI-DEC-001 — production OFF | [Current decision][b-current] | policy/repository owner; ingest/R,P | [B](#policy) |
| BILI-ACQ-001 — exact acquisition channel unselected | [Channel record][b-channel] | policy/repository owner, #7; acquisition/R | [B](#policy) |
| BILI-DATA-001 — strictest source/rights retention; no implicit TTL | [Retention/publication][b-data] | #10/#16/#17, policy owner; data/R,D | [B](#policy) |
| BILI-SRC-DEV — dated Open Platform developer terms | [Source register][b-sources] | policy owner; channel applicability/R | [B](#policy) |
| BILI-SRC-OPEN-PRIV — dated Open Platform privacy policy | [Source register][b-sources] | policy owner; channel/data/R | [B](#policy) |
| BILI-SRC-LIVE — dated live-service agreement | [Source register][b-sources] | policy owner; live source/R | [B](#policy) |
| BILI-SRC-USER — dated selected mainland user agreement | [Source register][b-sources] | policy owner; service terms/R | [B](#policy) |
| BILI-SRC-PRIV — dated privacy entry/content segment | [Source register][b-sources] | policy owner; privacy/R | [B](#policy) |
| BILI-SRC-DOCS — official documentation entry, no selected API | [Source register][b-sources] | policy owner, #7; channel/R | [B](#policy) |
| BILI-RIGHT-ACQUIRE — automated media/event acquisition | [Permission record][b-rights] | policy/rights holders, #7; acquisition/R | [B](#policy) |
| BILI-RIGHT-TRANSFORM — transient decode and ASR processing | [Permission record][b-rights] | policy/rights holders, #7/#8; transformation/R | [B](#policy) |
| BILI-RIGHT-WORKER — identified third-party worker disclosure | [Permission record][b-rights] | policy/rights holders, repository owner, #14/#15; real worker PCM/R | [B](#policy) |
| BILI-RIGHT-NORMALIZED — source/field normalized retention | [Permission record][b-rights] | policy/rights holders, #10/#16; persistence/R,D | [B](#policy) |
| BILI-RIGHT-RAW — additional raw-purpose retention | [Permission record][b-rights] | policy/rights holders, #10/#16; raw/R,D | [B](#policy) |
| BILI-RIGHT-PUBLISH — each field/audience/output purpose | [Permission record][b-rights] | policy/rights holders, #11/#17; publication/R,D | [B](#policy) |
| IDX-PLATFORM-ELIGIBILITY — free, anonymous, unrestricted, current live and rate-compliant | [Eligibility/deny rules][b-eligibility] | #7; resolver/R | [B](#policy) |
| IDX-TAKEDOWN-CONTACT — exact contacts, verified scope and response | [Takedown contacts][b-takedown] | policy owner, #7/#16/#17; takedown/R,D | [B](#policy) |
| IDX-PLATFORM-REVIEW — 90-day/change-triggered review and scoped enable record | [Review/enablement][b-review] | policy/repository owner; production/R,P | [B](#policy) |
| LIC-DEC-001 — no reference-only copying; MIT candidates not yet approved | [Current license decision][lic-current] | each implementer/reviewer; source intake/O,L,H,D,P | [I](#license) |
| LIC-REQ-001 — only accepted local requirements and primary vendor/standards inputs | [Independent requirements][lic-requirements] | requirements/implementation authors; authorship/O,L,H,D,P | [I](#license) |
| LIC-EXP-ISSUE2 — recorded exposure and corresponding author exclusion | [Exposure/exclusion][lic-exposure] | assignment owner/independent reviewer; authorship/O,L,H,D,P | [I](#license) |
| IDX-EXPOSURE-ASSIGNMENT — fresh author declaration and assignment before code | [Exposure/exclusion][lic-exposure] | each author/assigner/reviewer; authorship/O,L,H,D,P | [I](#license) |
| IDX-ISOLATED-REVIEW — separate reviewer; quarantine suspected similarity | [Reviewer separation][lic-review] | independent reviewer; implementation merge/O,L,H,D,P | [I](#license) |
| IDX-MIT-NOTICES — exact approved blob-to-destination notice mapping | [Notice mapping][lic-notices] | owner/reviewer; any proposed copy/O,L,H,D,P | [I](#license) |
| IDX-MODEL-PROVENANCE — weights/data/tokenizer/output terms separately approved | [Models/datasets][lic-models] | artifact/owner reviewer; model/data intake/H,D | [I](#license) |
| IDX-PROVENANCE-PR — seven evidence requirements before merge/release | [PR gate][lic-pr] | implementation author and isolated reviewer; release/O,L,H,D,P | [I](#license) |

## Protocol and current delivery scope

Definition #3 for V rows; each later Issue owns its own N record. Supporting source is
[Pydantic protocol package](../packages/protocol/python/livecho_protocol/),
[generated schema](../packages/protocol/schema/protocol-v1.schema.json),
[TypeScript validator](../packages/protocol/src/validator.ts), and
[metadata-only golden manifest](../packages/protocol/fixtures/manifest.json).
Generated output is not a second normative authority.

| ID and requirement | Primary definition | Evidence owners; capability/stage | Profile |
| --- | --- | --- | --- |
| IDX-PROTOCOL-CANONICAL — transport/parser/size/canonical values | [Transport/canonical values][p-canonical] | #3; message validation/O,L,D | [V](#protocol) |
| IDX-PROTOCOL-MODELS — closed versioned model and manifest contract | [Authoritative models][p-models] | #3; synthetic protocol/O,L,D | [V](#protocol) |
| IDX-PROTOCOL-PCM — exact header/size/PTS/budget/end-of-segment | [Binary PCM][p-pcm] | #3, runtime #8/#14; audio framing/O,L,D | [V](#protocol) |
| IDX-PROTOCOL-EPOCH — backend-authoritative non-resumed replacement | [Ordering/reconnect][p-order] | #3, runtime #9/#14/#15; lease lifecycle/O,L,D | [V](#protocol) |
| IDX-PROTOCOL-SEQ — exact-next order, duplicate/conflict/exhaustion | [Ordering/reconnect][p-order] | #3, runtime #9/#14; sequence/O,L,D | [V](#protocol) |
| IDX-PROTOCOL-REVISION — immutable identity/ranges, monotonic revisions/final | [Ordering/reconnect][p-order] | #3, runtime #9/#11/#14; transcript state/O,L,D | [V](#protocol) |
| IDX-PROTOCOL-BOUNDS — bounded object/replay state, expiry and resync | [Ordering/reconnect][p-order] | #3/#27; state lifecycle/O,L,D | [V](#protocol) |
| IDX-PROTOCOL-REJECTION — stable precedence and no rejected-state mutation | [Stable rejection][p-rejection] | #3; protocol failures/O,L,D | [V](#protocol) |
| IDX-PROTOCOL-GENERATION — one source, deterministic generated parity | [Generation/fixtures][p-generation] | #3; compatibility/O | [V](#protocol) |
| IDX-PROTOCOL-VERSION — protocol Issue and golden compatibility evidence | [Version policy][p-version] | #3 and future protocol owner; protocol edits/O,L,D,R | [V](#protocol) |
| IDX-ASR-BENCHMARK — reproducible approved benchmark/hardware evidence | [Accepted #5 spec](changes/5-mlx-benchmark/spec.md) | #5; benchmark/O,H | [N](#pending); artifact PR #33 merged, runtime/hardware missing |
| IDX-MEMORY-AUDIO — synthetic source, ownership, VAD and supervised decoder | [Accepted #8 spec](changes/8-memory-audio/spec.md) | #8; bounded audio/O,L | [N](#pending); artifact PR #34 merged, decoder/allocation/host evidence missing |
| IDX-LOCAL-WORKER — synthetic single-worker MLX path | [Issue #6](https://github.com/Shuang-su/Livecho/issues/6) | #6; worker/L,H | [N](#pending) |
| IDX-LOCAL-CAPTION — short synthetic end-to-end path | [Issue #9](https://github.com/Shuang-su/Livecho/issues/9) | #9; integration/L | [N](#pending); no #7/#27/#28/#29/#30 dependency |
| IDX-CAPTION-WEB — first caption/session-status page | [Issue #11](https://github.com/Shuang-su/Livecho/issues/11) | #11; companion Web/L | [N](#pending); event delivery belongs to #29 |
| IDX-LONG-SESSION — capacity/lifecycle/resynchronization extension | [Issue #27](https://github.com/Shuang-su/Livecho/issues/27) | #27, supplies #15/#19; long sessions/D,P | [N](#pending); not a short #9 gate |
| IDX-REAL-NEGOTIATION — real-input origin and capability extension | [Issue #28](https://github.com/Shuang-su/Livecho/issues/28) | #28, supplies #19; real input/R,P | [N](#pending); existing #6/#9 remain synthetic |
| IDX-EVENT-WEB — independent danmaku/Super Chat display | [Issue #29](https://github.com/Shuang-su/Livecho/issues/29) | #29 after #10/#11; event Web/R | [N](#pending) |
| IDX-INVITED-IDENTITY — invite-only email and role authorization | [Issue #12](https://github.com/Shuang-su/Livecho/issues/12) | #12; identity/D | [N](#pending) |
| IDX-WORKER-IDENTITY-STATS — invited device identity and contributor-own statistics | [Issue #13](https://github.com/Shuang-su/Livecho/issues/13) | #13; worker identity/statistics/D | [N](#pending) |
| IDX-PERSISTENT-HISTORY — normalized timeline, encrypted raw and complete deletion | [Issue #16](https://github.com/Shuang-su/Livecho/issues/16) | #16; persistence/history/D | [N](#pending) |
| IDX-INVITED-CONSOLE — authorized history/statistics and operator/admin controls | [Issue #17](https://github.com/Shuang-su/Livecho/issues/17) | #17; console/D | [N](#pending) |
| IDX-CUDA-MOCK — mock/cross-provider contract only | [Issue #18](https://github.com/Shuang-su/Livecho/issues/18) | #18; contract/O,D | [N](#pending); real CUDA hardware not established |
| IDX-ALPHA-ACCEPTANCE — exact deployed environment and complete acceptance evidence | [Issue #19](https://github.com/Shuang-su/Livecho/issues/19) | #19; final Alpha/P | [N](#pending), [W](#railway) |


## Deployment and secret gates

Definition #4, accepted [specification][s4]. The operations and secrets records are the
detailed future procedures assigned by that contract. Each record has [W](#railway):
offline scope passed, live/provider evidence missing, and no provider operation
authorized by this index. The owning later operation must supply its accepted artifact,
exact target approval and required independent evidence before that operation.

| ID and requirement | Primary definition | Evidence owners; capability/stage | Profile |
| --- | --- | --- | --- |
| IDX-RAILWAY-SOURCE — one reviewed IaC source and locked toolchain | [Source/toolchain][w-source] | #4; offline graph/O | [W](#railway) |
| IDX-RAILWAY-ENV — exact environment classification, false/fixture defaults | [Environment defaults][w-env] | #4/#19; O, provider isolation/P | [W](#railway) |
| IDX-RAILWAY-TOPOLOGY — fixed resources, placement and single backend replica | [Topology][w-topology] | #4/#19; desired graph/O, actual resources/P | [W](#railway) |
| IDX-RAILWAY-COMMANDS — guarded start/health/no-migration entry points | [Command contracts][w-commands] | #4, runtime #9/#11; command guards/O, serving/P | [W](#railway) |
| IDX-RAILWAY-CLI — exact external binary provenance and disposable copy | [External CLI gate][w-cli] | later operation owner/reviewer, #19; provider control/P | [W](#railway) |
| IDX-RAILWAY-STAGING — independent environments and staging-first observed proof | [Environment creation][w-staging] | #19/repository owner; rollout/P | [W](#railway) |
| IDX-RAILWAY-IMAGE — exact immutable backend/maintenance images without credential-bearing builds | [Immutable images][w-images] | release/security owner, #9/#19 and maintenance owner; release/P | [W](#railway) |
| IDX-MAINT-EXCLUSION — session locks and serving/maintenance mutual exclusion | [Mutual exclusion][w-exclusive] | #4 contract, first schema/operation owner, #16/#19; maintenance/P | [W](#railway) |
| IDX-MAINT-ADMISSION — durable one-use non-rewindable operation admission | [Durable admission][w-admission] | first operation owner, #16/#19; maintenance/recovery/P | [W](#railway) |
| IDX-MAINT-ROLE — one-use narrow temporary role and session revocation | [Temporary role][w-role] | database/security and operation owner; maintenance/P | [W](#railway) |
| IDX-MAINT-DISPATCH — fixed dispatcher and bounded supervisor | [Dispatcher/supervisor][w-dispatch] | operation owner, #19; maintenance/P | [W](#railway) |
| IDX-MAINT-DEPLOYMENTS — reconcile exact deployment-ID set/deltas | [Deployment reconciliation][w-deployments] | operation controller/reviewer; maintenance/P | [W](#railway) |
| IDX-MAINT-CANARY — per-environment sealed carrier deletion/recreation and absence proof | [Sealing canary][w-canary] | project owner, database owner, independent reviewer; maintenance/P | [W](#railway) |
| IDX-MAINT-OPERATION — approved target, sole trigger and full terminal cleanup | [One real operation][w-operation] | operation/database/project owners and reviewer; maintenance/P | [W](#railway) |
| IDX-ROLLOUT-HEALTH — staged deployment order and observed health cutover | [Deployment/health][w-health] | #9/#11/#19; serving/P | [W](#railway) |
| IDX-ROLLBACK — explicit disable and exact reviewed rollback | [Rollback/disable][w-rollback] | #19/repository owner; rollout/P | [W](#railway) |
| IDX-PROVIDER-DESTRUCTION — exact restore/deletion scope, provider evidence limits | [Restore/destruction][w-destroy] | #16/#19/database/project owners; destruction/recovery/P | [W](#railway) |
| IDX-SECRET-LITERALS — eight complete default-off/fixture literals | [Safety literals][secret-literals] | #4, each later consumer; config/O,P | [W](#railway) |
| IDX-SECRET-REFERENCES — backend-only managed references; placement not inferred | [Managed references][secret-refs] | database/data/operations/security; credentialed backend/P | [W](#railway) |
| IDX-SECRET-SLOTS — six names only, independent values/sealing/rotation | [Persistent slots][secret-slots] | auth/worker/data/operations/security per source; secrets/P | [W](#railway) |
| IDX-SECRET-MAINT — no baseline maintenance URI; temporary authority fully retired | [Temporary authority][secret-maint] | database/security/operation owners; maintenance/P | [W](#railway) |
| IDX-SECRET-OPERATORS — separate controller, 2FA owner, release and database authority | [External credentials][secret-operators] | source's named owners; operator controls/P | [W](#railway) |
| IDX-SECRET-PROHIBITED — no platform secrets, audio, worker secrets or cross-environment reuse | [Prohibited credentials][secret-prohibited] | every consumer/security owner; secrets/O,L,D,R,P | [W](#railway), [D](#design) |
| IDX-SECRET-LOCAL — bounded in-memory substitutes and no-send mail | [Local behavior][secret-local] | each owning runtime Issue; synthetic local/L | [W](#railway) |
| IDX-SECRET-EVIDENCE — value-free scoped provisioning/revocation review | [Review record][secret-evidence] | provisioning/rotation/emergency owners and reviewer; secrets/P | [W](#railway) |

## Authority and discrepancy register

No contradictory normative definition was identified in this index review. This does not
approve source decisions or claim runtime validation. The primary pointers reflect source
responsibilities: ADR decisions/flows, threat/control catalog, the six explicitly
lifecycle-owned controls, lifecycle classes, platform policy, independent-source policy,
accepted protocol and deployment contracts. Repeated control IDs retain their supporting
lifecycle/incident/catalog references, with unchanged owners;
the index creates no new normative precedence between those documents.

| Observation | Exact sources | Treatment and resolution owner |
| --- | --- | --- |
| Accepted #2 artifacts coexist with proposed ADR and unaccepted High risks | [#2 evidence][e2], [ADR approval][adr-status], [risk decisions][risk-decisions] | Intentional authority distinction; retain pending production decisions. Repository owner must decide each scope, not #30. |
| Artifact-era #30/#5/#8 evidence still says pending although artifact PRs merged | [#30 approval update](changes/30-requirements-evidence-index/evidence.md#implementation-approval-and-author-assignment), PRs [#32](https://github.com/Shuang-su/Livecho/pull/32), [#33](https://github.com/Shuang-su/Livecho/pull/33), [#34](https://github.com/Shuang-su/Livecho/pull/34) | Historical artifact text is preserved; merge metadata establishes accepted artifact availability, never runtime readiness. Implementation evidence owners record scoped follow-up. |
| #31 title gained a proposal prefix | [Dated roadmap snapshot](roadmap.md#direct-dependency-snapshot), [accepted #30 stages](changes/30-requirements-evidence-index/spec.md#stages-and-dependencies) | Metadata-only drift; no body consulted or requirement adopted. Separate owner-reviewed change needed for any new scope. |

Unresolved authority rows: **0**. If a later review identifies ambiguity or conflict,
mark the affected row `authority unresolved`, retain all candidate pointers and exact
wording difference here, name the affected capability and definition owner, and require a
separate owner-reviewed normative decision. Do not choose the convenient source. An
accurately documented unresolved row need not block this index or unrelated capabilities.

## Maintenance

Review affected records, README and roadmap when an owning Issue changes implementation,
evidence, approval, dependencies or source status. Preserve dated historical passes and
their limits; missing or changed-environment proof remains missing. Use normal PR review;
there is no automatic promotion, approval, automation or new #9/#11 gate. The index
does not reopen completed #1–#4 or adopt the pending #31 proposal.

[e1]: changes/1-repository-foundation/evidence.md#automated-verification
[e1-approval]: changes/1-repository-foundation/evidence.md#artifact-approval
[e3-artifact]: changes/3-protocol-v1-contract/evidence.md#artifact-approval
[e3-approval]: changes/3-protocol-v1-contract/evidence.md#implementation-approval
[e4-approval]: changes/4-railway-deployment-skeleton/evidence.md#artifact-approval
[e2]: changes/2-architecture-risk-boundaries/evidence.md#artifact-approval
[e3]: changes/3-protocol-v1-contract/evidence.md#implementation-verification
[e4]: changes/4-railway-deployment-skeleton/evidence.md#implementation-automated-verification
[s2]: changes/2-architecture-risk-boundaries/spec.md
[s4]: changes/4-railway-deployment-skeleton/spec.md
[adr-status]: architecture/adr/0001-alpha-modular-monolith.md#assurance-and-approval-state
[risk-decisions]: security/alpha-threat-model.md#critical-and-high-residual-risk-decision-register
[roles]: security/alpha-threat-model.md#minimum-role-matrix
[zones]: architecture/adr/0001-alpha-modular-monolith.md#trust-decisions-by-zone
[dec-arch]: architecture/adr/0001-alpha-modular-monolith.md#dec-arch-001-one-online-authority
[dec-maint]: architecture/adr/0001-alpha-modular-monolith.md#dec-maint-001-constrained-issue-4-maintenance-exception
[dec-safety]: architecture/adr/0001-alpha-modular-monolith.md#dec-safety-001-safety-state-outranks-restored-application-state
[dec-worker]: architecture/adr/0001-alpha-modular-monolith.md#dec-worker-001-community-workers-are-hostile-capable-processors
[dec-data]: architecture/adr/0001-alpha-modular-monolith.md#dec-data-001-mediated-restricted-persistence
[dec-export]: architecture/adr/0001-alpha-modular-monolith.md#dec-export-001-separate-managed-admin-export-boundary
[follow]: architecture/adr/0001-alpha-modular-monolith.md#follow-on-obligations
[gates]: architecture/adr/0001-alpha-modular-monolith.md#production-gates-and-decision-record
[diagram]: architecture/adr/0001-alpha-modular-monolith.md#trust-and-data-flow-diagram
[allow]: architecture/adr/0001-alpha-modular-monolith.md#allowed-flow-registry
[deny]: architecture/adr/0001-alpha-modular-monolith.md#no-flow-registry
[controls]: security/alpha-threat-model.md#required-control-catalog
[l-controls]: security/data-lifecycle-and-deletion.md#control-registry
[i-controls]: operations/incident-disable-and-recovery.md#control-registry-and-implementation-ownership
[responses]: security/alpha-threat-model.md#required-response-invariants
[handoff]: operations/incident-disable-and-recovery.md#evidence-handoff
[threats]: security/alpha-threat-model.md#threat-register
[data-matrix]: security/data-lifecycle-and-deletion.md#normative-lifecycle-matrix
[data-owners]: security/data-lifecycle-and-deletion.md#implementation-ownership-and-acceptance-evidence
[audio]: security/data-lifecycle-and-deletion.md#audio-budget-and-teardown-invariants
[identity]: security/data-lifecycle-and-deletion.md#identity-revocation-and-restore-rollback
[deletion]: security/data-lifecycle-and-deletion.md#roomsession-deletion-state-machine
[provider]: security/data-lifecycle-and-deletion.md#current-railway-provider-evidence-and-production-gate
[delete-sequence]: security/data-lifecycle-and-deletion.md#required-deletion-sequence
[restore]: operations/incident-disable-and-recovery.md#startup-restore-and-disaster-recovery
[safety-state]: operations/incident-disable-and-recovery.md#durable-safety-state
[transitions]: operations/incident-disable-and-recovery.md#safe-transition-rules
[audit-fields]: operations/incident-disable-and-recovery.md#payload-free-audit-contract
[tabletops]: operations/incident-disable-and-recovery.md#required-tabletop-scenarios
[b-current]: policy/bilibili-public-ingest.md#current-decision
[b-sources]: policy/bilibili-public-ingest.md#authoritative-source-register
[b-channel]: policy/bilibili-public-ingest.md#acquisition-channel-and-applicable-agreement
[b-data]: policy/bilibili-public-ingest.md#retention-and-publication-gates
[b-rights]: policy/bilibili-public-ingest.md#permission-and-purpose-record
[b-eligibility]: policy/bilibili-public-ingest.md#eligibility-and-deny-rules
[b-takedown]: policy/bilibili-public-ingest.md#takedown-contacts-and-response
[b-review]: policy/bilibili-public-ingest.md#review-and-enablement-record
[lic-current]: policy/independent-implementation.md#current-decision
[lic-requirements]: policy/independent-implementation.md#independently-written-requirements
[lic-exposure]: policy/independent-implementation.md#author-exposure-and-exclusion
[lic-review]: policy/independent-implementation.md#reviewer-separation-and-similarity-response
[lic-notices]: policy/independent-implementation.md#mit-notice-mapping
[lic-models]: policy/independent-implementation.md#models-datasets-and-generated-material
[lic-pr]: policy/independent-implementation.md#pull-request-gate
[p-canonical]: changes/3-protocol-v1-contract/spec.md#transport-and-canonical-values
[p-models]: changes/3-protocol-v1-contract/spec.md#authoritative-and-supporting-models
[p-pcm]: changes/3-protocol-v1-contract/spec.md#binary-pcm-message-boundary
[p-order]: changes/3-protocol-v1-contract/spec.md#ordering-idempotency-and-reconnect
[p-rejection]: changes/3-protocol-v1-contract/spec.md#stable-rejection-contract
[p-generation]: changes/3-protocol-v1-contract/spec.md#source-generation-and-shared-fixtures
[p-version]: changes/3-protocol-v1-contract/spec.md#version-policy
[w-source]: changes/4-railway-deployment-skeleton/spec.md#source-of-truth-and-toolchain
[w-env]: changes/4-railway-deployment-skeleton/spec.md#environment-classification-and-defaults
[w-topology]: changes/4-railway-deployment-skeleton/spec.md#project-topology-and-placement
[w-commands]: changes/4-railway-deployment-skeleton/spec.md#service-command-contracts
[w-cli]: operations/railway-deployment.md#external-cli-and-disposable-copy-gate
[w-staging]: operations/railway-deployment.md#environment-creation-and-staging-first-provider-gate
[w-images]: operations/railway-deployment.md#immutable-image-requirements
[w-exclusive]: operations/railway-deployment.md#mutual-exclusion
[w-admission]: operations/railway-deployment.md#durable-one-use-admission
[w-role]: operations/railway-deployment.md#temporary-role
[w-dispatch]: operations/railway-deployment.md#fixed-dispatcher-and-bounded-supervisor
[w-deployments]: operations/railway-deployment.md#deployment-id-set-reconciliation
[w-canary]: operations/railway-deployment.md#per-environment-sealing-canary
[w-operation]: operations/railway-deployment.md#one-future-real-operation
[w-health]: operations/railway-deployment.md#deployment-order-and-health-cutover
[w-rollback]: operations/railway-deployment.md#rollback-and-disable
[w-destroy]: operations/railway-deployment.md#restore-and-permanent-destruction
[secret-literals]: operations/railway-secrets.md#non-secret-safety-literals
[secret-refs]: operations/railway-secrets.md#managed-references-for-backend
[secret-slots]: operations/railway-secrets.md#persistent-backend-slots
[secret-maint]: operations/railway-secrets.md#temporary-maintenance-database-authority
[secret-operators]: operations/railway-secrets.md#external-operator-and-automation-credentials
[secret-prohibited]: operations/railway-secrets.md#credentials-that-must-not-exist
[secret-local]: operations/railway-secrets.md#safe-local-behavior
[secret-evidence]: operations/railway-secrets.md#value-free-review-record
