# Bilibili public-ingest policy and production gate

This document is the normative platform-policy record for Issue #2. Terms such as
**must**, **must not**, and **may** have the meaning assigned in the Issue #2
specification. It records an operational risk decision, not a legal opinion.

## Current decision

`BILI-DEC-001` is **production OFF**.

As of 2026-08-24, Livecho has not selected an exact Bilibili acquisition channel or API
family and has not recorded platform permission, per-room rights-holder permission, an
approved third-party worker disclosure basis, a retention grant, or a public-output
grant. Public, free, anonymous viewing does not supply any of those permissions. The
repository owner's architecture approval or risk acceptance cannot replace permission
from Bilibili or the relevant rights holder.

Synthetic fixtures may be used by later protocol and worker Issues. No production
Bilibili media or event acquisition, persistence, worker disclosure, or publication is
authorized by this document.

## Authoritative source register

The register records the official pages reached on 2026-08-24 (Asia/Shanghai). A
"canonical URL" below means the stable operator-owned entry selected for this review.
The network-resolved URL, client-side redirect or aggregator, and selected content
page/segment are recorded separately so a future routing change becomes a review
trigger. Page-displayed dates identify the reviewed version but are not immutable
snapshots.

| ID | Canonical, entry, and resolved URL | Displayed title and version | Checked scope |
| --- | --- | --- | --- |
| `BILI-SRC-DEV` | Canonical and entry: <https://open.bilibili.com/agreement/developer-service>; resolved: same URL, HTTP 200, no redirect | 《哔哩哔哩开放平台开发者服务协议》; updated 2025-05-28, effective 2025-06-04 | Official Open Platform developer terms. Relevant only if the selected channel is actually an Open Platform service. The reviewed text describes developer/application onboarding, associated-UP authorization, purpose limitation, third-party processing controls, written-permission conditions, deletion, and shortest-necessary retention. It is not itself an approval of Livecho. |
| `BILI-SRC-OPEN-PRIV` | Canonical and entry: <https://open.bilibili.com/agreement/privacy-policy>; resolved: same URL, HTTP 200, no redirect | 《哔哩哔哩开放平台隐私政策》; updated 2025-05-28, effective 2025-06-04 | Open Platform SDK/API and developer/UP-user data processing. Applicable only with an approved Open Platform channel and its required relationships. |
| `BILI-SRC-LIVE` | Canonical and entry: <https://live.bilibili.com/p/html/live-app-help/index.html>; resolved: same URL, HTTP 200, no redirect | 《哔哩哔哩直播服务协议》; updated 2025-04-29, effective 2025-05-01 | General Bilibili Live rules for ordinary users and streamers, including mutable supplementary rules and the streamer's grant to Bilibili. That grant names Bilibili and its affiliates; this review found no downstream Livecho grant. |
| `BILI-SRC-USER` | Canonical and entry: <https://www.bilibili.com/blackboard/account-useragreement.html>; network-resolved: same URL, HTTP 200; client redirect/aggregator: <https://www.bilibili.com/blackboard/era/I1IzQXW4myXZIzBi.html>; selected China-mainland content: <https://www.bilibili.com/blackboard/activity-qKrC5olzgg.html> | 《哔哩哔哩弹幕网用户使用协议》; China-mainland version updated 2025-04-30, effective 2025-05-07 (the selected activity HTML title retains an older label) | General service terms incorporated by the live and Open Platform agreements. The aggregator also lists other jurisdictions; this record deliberately selects the China-mainland activity and does not substitute the newer Japan version. Entry, aggregator selection, title, and body-date changes all trigger review. |
| `BILI-SRC-PRIV` | Canonical and entry: <https://www.bilibili.com/blackboard/privacy-pc.html>; network-resolved: same URL, HTTP 200; current `privacy-pc` content segment: `99594` | 《哔哩哔哩隐私政策》; segment `99594`, updated 2026-02-12, effective 2026-02-19 | Current general website/app privacy policy and official privacy/customer-service routes. The stable entry's version list selected segment `99594` at review time; a different latest segment is an immediate review trigger. The retired 2024 `activity-yYWJeOsIDP` basic-function policy is not treated as current. |
| `BILI-SRC-DOCS` | Canonical and entry: <https://open.bilibili.com/doc>; resolved: same URL, HTTP 200, no redirect | 哔哩哔哩开放平台 documentation index; no displayed version/effective date captured | Official API-documentation entry point. No endpoint or API family has been selected from it, so it cannot establish channel applicability or permission. |

Review owner: `@Shuang-su`. Evidence preparer: Issue #2 documentation author. Last
checked: 2026-08-24. Scheduled review due: 2026-11-22. The current review is incomplete,
so that future date does not create a temporary authorization window.

## Acquisition channel and applicable agreement

`BILI-ACQ-001` is **unselected**. Before any real network request, the enablement record
must identify all of the following without a wildcard or an undocumented fallback:

- official product name and channel owner;
- exact API family and documented entry point, authentication mode, application ID, and
  required Bilibili/UP-account relationship;
- permitted room-identity, live-status, event, and transient-media operations;
- current rate and concurrency limits, schema/version identifiers, and error semantics;
- every incorporated agreement, policy, product rule, and separately negotiated term;
- allowed host and redirect set for SSRF protection; and
- the platform contact and revocation/takedown procedure for that channel.

Livecho must not use a reverse-engineered private endpoint, browser-session extraction,
cookie, account credential, signed URL supplied by an operator, alternate scraper, or
an undocumented endpoint as a fallback. If the chosen official channel requires a
developer account, associated UP account, application approval, or written agreement,
those artifacts must exist before the channel is eligible. The general agreements in
`BILI-SRC-*` do not decide which specialized agreement applies.

## Permission and purpose record

Each production candidate must have a per-room record keyed by canonical `room_id`.
Permission for one row does not imply permission for another row.

| ID and action | Evidence required | Current state |
| --- | --- | --- |
| `BILI-RIGHT-ACQUIRE`: automated acquisition of live metadata, events, and transient media | Exact channel approval plus platform and rights-holder permission covering Livecho's named purpose | Missing; blocked |
| `BILI-RIGHT-TRANSFORM`: decode at the trusted backend and transform at most 30 seconds of audio in RAM into captions | Permission for transient processing and speech-to-text; data classes and processor locations named | Missing; blocked |
| `BILI-RIGHT-WORKER`: disclose bounded PCM to an identified invited community worker | Express third-party-processing/disclosure permission, worker terms, territory, deletion duty, and owner acceptance of `RISK-WORKER-AUDIO-RETENTION` | Missing; synthetic-only |
| `BILI-RIGHT-NORMALIZED`: retain normalized danmaku, SC, status, transcript, or room/session metadata | Per-field purpose, data-subject/right-holder basis, retention/review rule, deletion trigger, Issue #16 controls | Missing; persistence blocked |
| `BILI-RIGHT-RAW`: retain sanitized encrypted business payloads | Every normalized-data gate plus explicit raw-purpose permission and Issue #16 archive/export/deletion controls | Missing; persistence blocked |
| `BILI-RIGHT-PUBLISH`: expose captions or any normalized live/history/statistics surface | Each output field, audience, latency, duration, attribution, moderation, and redistribution/derivative permission | Missing; publication blocked |

The record must include the evidence issuer, recipient, scope, issue date, expiry or
revocation terms, evidence location, reviewer, review date, and any stricter retention
or deletion rule. A statement by the repository owner is governance evidence only. It
is never entered in a platform- or rights-holder-evidence field.

## Eligibility and deny rules

A room is eligible for consideration only when an operator/admin selected it, aliases
and URLs resolved to one unambiguous canonical Bilibili `room_id`, it is currently live,
and it is freely viewable without authentication, payment, membership, geographic
restriction, or DRM restriction. Eligibility must be reevaluated before initial start
and every reconnect; a prior success is not cached permission. Livecho must not bypass
or work around any such restriction.

`Currently live` is a per-attempt, transient eligibility fact, not a durable safety
decision. If a selected room is ordinarily offline at the initial check or reconnect, or
an otherwise eligible broadcast ends normally, Livecho rejects or stops only that bound
attempt and performs ordinary session/lease/audio/locator/publication teardown. It does
not prepare or commit a safety transition, advance the safety generation, change the
global bit or denylist, or require an owner-gated denylist removal. A later broadcast may
be considered only after every eligibility and rights gate is evaluated again.

Any of the following also denies the attempted action and is an immediate stop/review
trigger:

- the global switch is off, the room is denied, safety state is missing/stale, or a
  canonical room ID cannot be established;
- any `BILI-RIGHT-*` record needed by the attempted action is missing, expired,
  revoked, ambiguous, or narrower than that action;
- the source review is older than 90 days, a registered source cannot be reached, a
  title/version/date changes, or incorporated rules cannot be enumerated;
- the platform, room owner, acquisition channel, application relationship, product
  purpose, processor set, output audience, or data fields change;
- a response requires login, cookie, token, payment, or membership; indicates any
  geographic or DRM restriction; redirects outside the allowlist; or requires a
  rate-limit workaround;
- endpoint, schema, field, signature, rate-limit, or error behavior differs from the
  approved channel record;
- a platform/right-holder complaint, takedown, restriction, ownership dispute, or
  inability to reach the registered contact occurs; or
- sanitization, worker, audit, retention, deletion, or recovery controls required for
  the selected action are unavailable.

There is no public room submission, automatic discovery, historical crawl,
credentialed fallback, or "best effort" continuation. An eligibility or prerequisite
failure is not by itself a denylist mutation. Missing, expired, stale, or incomplete
prerequisites keep the attempted action off and require review, but do not automatically
create a durable room entry. An authorized operator/admin may separately invoke
`add(R)` only for a verified policy, rights, takedown, restriction, or safety incident
whose affected scope is one exactly bound canonical room. From acceptance of that
tightening through its commit/read-back, only `R` is provisionally blocked and cleaned;
the global activation and unrelated eligible rooms remain unchanged. A successfully
committed addition persists that same room-only result. Canonicalization or active-
resource binding ambiguity, unknown or platform-wide incident scope, or a failed/stale/
conflicting safety-journal or recovery-copy commit/read-back invokes global forced-off
rather than guessing or claiming a scoped transition succeeded.
Every global forced-off path closes local authority gates and issues cleanup for all
active/queued rooms before any safety-journal or recovery-copy await; slow, hung, or
failed durability cannot extend playback, business-event intake, worker disclosure, or
pending publication.
A global-enable or room-removal transition in durable `PREPARED` phase is only a proposal;
even a matching `COMMITTED` journal/recovery-head result is durable history, not serving
authority. Each boot starts without activation and globally off. Only a non-restorable
current-incarnation activation may apply the exact committed head, after its final local
compare-and-set proves the same incarnation, a matching intake-continuity `open(E)`, no
applicable pending/tainted intake or unfinished cleanup, and unchanged global guards for
global enable or unchanged `R`-scoped guards for `remove(R)`. An unrelated room-local
add or deletion intake does not revoke global activation or block unaffected rooms.
A delayed proposal, commit, response, or prior-incarnation activation cannot clear a
newer local global/room block. Global disable revokes current global activation before its
durability work; `add(R)` instead installs/revokes only `R`'s scoped block/removal effect
and leaves unrelated active rooms under the existing global activation. If a new intake
or tightening applicable to the relaxation's global or exact-room scope linearizes before
final activation/effect, that relaxation fails without opening the affected path.
Runtime enforcement belongs to Issue #7; until it exists and is verified, all real
acquisition stays off.

## Worker disclosure and audio boundary

Synthetic frames are the default for community workers. Real PCM may go only to an
identified invited worker after `BILI-RIGHT-WORKER` is complete and the repository
owner individually accepts the named High residual risk. Authentication and protocol
signatures do not prove the worker erased audio.

Every conforming component must hold audio only in bounded RAM under the Issue #2
30-second media-time and aggregate-byte ceilings. No audio retry queue exists: a retry
may reference only frames still inside the existing ring/in-flight budget. Audio,
encoded audio, base64, stream buffers, crash dumps, telemetry, logs, fixtures,
databases, and objects must never persist. Disable, deny, timeout, disconnect, lease
revocation, or teardown clears conforming RAM and stops future disclosure; it does not
claim erasure from a malicious host. Playback locators and credentials remain
backend-memory-only and are never disclosed to workers.

## Retention and publication gates

`BILI-DATA-001` applies the following order; the strictest applicable rule wins:

1. audio and playback secrets follow their zero-persistence/active-use-only rules;
2. a source, written permission, rights-holder instruction, law, or takedown may impose
   a shorter period or prohibit storage entirely;
3. no normalized field may persist until its purpose, audience, review cadence,
   deletion trigger, and source-specific retention decision are approved; and
4. no raw business payload may persist until those decisions and all Issue #16
   sanitization, encryption, access, audit, export, deletion, backup, and restore gates
   are implemented and evidenced.

There is no platform-independent default TTL that creates permission. Missing or stale
evidence stops new acquisition, persistence, and publication. A takedown or revocation
immediately hides output and blocks ingest, then invokes the room/session deletion
workflow. Existing data is not retained merely because the 90-day source review had
not yet expired.

Each takedown record must determine its verified scope before destructive purge. A
complaint or channel/rights revocation verified to cover the whole room uses
`room(canonical_room_id)` and covers room metadata plus every session. A request that
authoritatively identifies one immutable session uses `session(immutable_session_id)` and
must not affect siblings or shared room state. If complaint scope is ambiguous or affected
sessions cannot be separated reliably, block the widest safely identified exposure (deny
the known room, otherwise global off), escalate, and do not guess a destructive selector.

## Takedown contacts and response

- Livecho takedown governance owner: repository owner `@Shuang-su`. The operational
  global-disable owners are the operator and admin roles defined by the incident runbook;
  the repository-owner role has no implied production credentials. Sensitive reports use
  the repository's private GitHub Security Advisory intake; reports must not place
  credentials, signed URLs, identifiers, event payloads, or audio in a public issue.
- Bilibili service contact currently recorded from current segment `99594` of
  `BILI-SRC-PRIV`:
  `help@bilibili.com`. This is a platform customer-service route, not evidence of
  permission and not a substitute for the channel-specific contact.
- Per-room rights-holder/authorized representative: **not recorded**. A direct contact,
  authority description, and acknowledgement path are mandatory in each room record.

The missing per-room and channel-specific contacts are production blockers. On a credible
session-scoped complaint, an operator/admin stops/hides/blocks that session and its lease,
audio, locators, and pending/public output. On verified room scope, the operator/admin
may invoke `add(R)` and stops all that room's active paths. If session scope is ambiguous
but the canonical room is verified, block that room without guessing a destructive
selector; if no exact room can be bound or scope may be platform-wide, remain globally off
as defined above. The report remains an unresolved takedown intake
until its exact selector has a verified durable deletion record; a payload-free audit
entry alone is not that record. Before accepting any report, the sole current serving
authority must commit and read back a target-free intake-continuity `open(E)` in the
independent recovery boundary. If it cannot, the intake endpoint remains closed and the
system globally off. An admin may start idempotent deletion only after exact scope
resolution, with exactly one typed selector: canonical `room_id` for room metadata and all
current/historical/pending/late/restored sessions, or immutable `session_id` for only the
session resolved through the backend's authoritative parent-room index. The caller does
not have to provide—and cannot override—the session's parent room. None, both,
conflicting, missing, non-unique, or ambiguous targets start no destructive purge.

An exactly resolved valid request installs only its selector-scoped provisional
containment while admission is pending. A deterministically invalid request is rejected
and durably accounted for without changing global activation, the denylist, or unrelated
room/session service. Neither normal valid intake nor a completed invalid-request denial
is a global tightening. Intake persistence/read-back failure or uncertainty, loss of proof
that an exactly identified target remains contained and owned at that scope, an
independently credible exposure that cannot be safely bounded, or an otherwise tainted
continuity guard instead invokes global forced-off and blocks every relaxation until
authoritative reconciliation.

For a valid selector, immediate local containment precedes a commit/read-back barrier:
the typed payload-free `hidden` tombstone must be durably admitted to the independent
recovery boundary before Livecho acknowledges the deletion request, reports `hidden` as
an accepted state, or begins destructive purge. A timeout, lost response, or unavailable
or uncertain commit keeps the takedown intake open, returns no success, taints the current-
incarnation intake guard, forbids a clean epoch close, and escalates to global forced-off.
The initiating source may retry the same selector, idempotency identity, and
original time, but Livecho does not depend on that source remaining available. A clean
`clean-close(E)` is permitted only after one atomic authority fence quiesces serving,
safety-control, and deletion ingress; every accepted safety-control handler drains and its
outcome is durably reconciled; late reports are rejected; deletion handlers drain; and
every valid report maps to its
verified tombstone with no safety/intake pending or taint. A safety/deletion action that
linearizes first blocks close until reconciliation; one that arrives after close must be
rejected or bound to a new verified epoch.
If the source disappears or the process crashes before target-specific
durability, unmatched `open(E)` survives restart and blocks all traffic and relaxation;
because it contains no target, it authorizes no guessed purge. Without exact authoritative
replay the system remains off indefinitely. Neither a process restart, a recovered but
empty application store, an audit record, a durable relaxation proposal/commit, nor a
prior-incarnation activation closes that epoch or permits re-enable. An operator escalates
the safely blocked scope to an admin and cannot declare or initiate deletion. Room
tombstones dominate child-session manifests; session deletion preserves siblings/shared
room state. Partial deletion remains hidden and denied. Recovery may not serve traffic
until every continuity epoch and exact-scope deletion manifest, every unresolved intake,
the exact committed safety head, and a fresh current-incarnation activation reconcile
successfully.

## Review and enablement record

The source/rights review must run at least every 90 days and immediately on any trigger
listed above. It must compare canonical, entry, and resolved URLs; visible title and
dates; incorporated documents; exact channel docs; permissions; room ownership;
processing/output purpose; worker set; retention; contacts; and prior takedowns.

Production may be considered only when one signed record proves all of the following:

- every `BILI-SRC-*` and exact channel source is current and internally consistent;
- `BILI-ACQ-001` and every required `BILI-RIGHT-*` row is complete;
- the room, rights holder, platform/channel, Livecho takedown, and disable contacts are
  reachable and tested without disclosing sensitive data;
- Issues #7, #16, and #17 provide the runtime, persistence, two-phase relaxation,
  current-incarnation activation, and intake-continuity controls required by the chosen
  scope, and the incident/deletion tabletops pass, including first-intake-write failure,
  source loss, crash/restart, unmatched epoch, and late relaxation cases;
- every Critical/High residual has a separate, scoped owner decision; and
- `@Shuang-su` records a dated production-enable approval whose review date has not
  expired.

An admin may technically prepare and commit an enable transition only after those
governance prerequisites pass. Serving remains off until the same incarnation freshly
commits that exact-head transition and installs its non-restorable activation under
unchanged tightening/intake guards, all prior continuity epochs reconciled, and its
current verified `open(E)`. Any missing item, including written permission required by an
applicable term, leaves `BILI-DEC-001` at **production OFF**.
