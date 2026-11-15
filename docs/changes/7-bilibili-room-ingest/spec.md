# Specification: Public free Bilibili room ingest adapter

This specification implements owning [Issue #7](https://github.com/Shuang-su/Livecho/issues/7)
using accepted [architecture/risk](../2-architecture-risk-boundaries/spec.md),
[protocol](../3-protocol-v1-contract/spec.md), [memory audio](../8-memory-audio/spec.md),
[local caption](../9-local-caption-vertical/spec.md), and the normative policy
`docs/policy/bilibili-public-ingest.md`. Owner comment on Issue #7 (2026-09-26) keeps
this path **anonymous free public only**; voluntary credentialed acquisition is Issue
#31 and must not be a silent fallback. No closed draft is treated as accepted scope.

## Behavior

### Operators, rooms, and eligibility

Only an **operator or admin** may start or stop one room ingest attempt. Anonymous
viewers and invited viewers have no room-control actions. There is no public create-
ingest API, no auto-discovery, and no historical crawl.

Input is an operator-supplied selector that must resolve to exactly one canonical
Bilibili `room_id` before any eligibility or denylist check. Ambiguous aliases, failed
resolution, or missing configuration are denials. A room is eligible for consideration
only when all of the following hold on the **current** attempt:

- operator/admin selected it;
- free and viewable without authentication, payment, or membership;
- not geographically or DRM restricted;
- within documented rate limits for the selected acquisition channel;
- currently live;
- a current rights/acquisition basis exists for the selected channel (see gates).

Login demand, payment/membership gate, geographic/DRM restriction, rate-limit response,
schema/field uncertainty, or missing rights basis **stops** the attempt safely. Prior
success is not cached permission; eligibility is reevaluated before start and every
reconnect.

### Acquisition channel and production gates

`BILI-ACQ-001` remains **unselected** and `BILI-DEC-001` remains **production OFF**
until the repository owner records an exact official channel, allowlisted hosts, rate
limits, and rights evidence per `docs/policy/bilibili-public-ingest.md`. This Issue’s
implementation may land **fixture/contract** code and closed registries, but must not
open live sockets to Bilibili or any third party by default, on import, or in CI.

Real network resolution and media acquisition require, without silent fallback:

1. owner-selected acquisition channel identity and host allowlist;
2. non-empty, reviewed rights evidence for the attempted room/action;
3. global ingest enablement permitted by the safety journal (still default off);
4. room not on the denylist;
5. for any audio path: Issue #8 preflight clearing `audio_budget_unverified` for the
   exact build/host, plus an **encoded-admission** extension (below) if input is not
   already #8 raw PCM.

Missing any gate fails closed with a stable reason such as
`acquisition_channel_unselected`, `rights_basis_missing`, `ingest_disabled`,
`room_denied`, or `audio_budget_unverified`. Skipped real gates are test failures, not
passes.

### State machine

One owner serializes state for the active room attempt. States are exactly:

`OFFLINE` → `STARTING` → `LIVE` → `STALLED` → `RECONNECTING` → `ENDED`

plus terminal/safe-stop paths that may jump to `ENDED` (or remain `OFFLINE`) on
eligibility failure, kill switch, denylist match, operator stop, protocol/policy stop,
or fatal adapter error. Transitions emit **payload-free** status events (reason codes
and counters only). Playback locators/tokens are never fields on those events.

| Condition | Transition / action |
| --- | --- |
| Operator start, gates pass | `OFFLINE` → `STARTING` → `LIVE` when anonymous public play is confirmed |
| Input silence / no media progress beyond bound | `LIVE` → `STALLED` |
| Recoverable stall within retry budget | `STALLED` → `RECONNECTING` → `LIVE` or `ENDED` |
| Operator stop, kill switch, denylist, rights/login/paywall/DRM/geo fail | stop → clear locators/audio → `ENDED` |
| Normal offline / broadcast end | stop bound attempt → `ENDED` without safety-generation advance |

Reconnect uses exponential backoff with a hard attempt ceiling and total wall-time
ceiling (exact numeric caps recorded in the implementation evidence; defaults must be
finite and small enough for operator demos, e.g. ≤ 8 attempts and ≤ 120 s total unless
an owner-accepted plan revises them). Exhausted retries end the attempt. Every
reconnect clears prior playback locators and must not reuse a stale signed URL.

### Kill switch and denylist

Global kill switch and room denylist semantics remain those of accepted Issue #2:
operator/admin may disable globally or denylist a canonical room; disable rejects new
starts/reconnects, terminates the active platform session, clears local playback
locators and audio, hides pending publication, and appends a payload-free audit event.
The disable path must not depend on the failing ingest path. Process start begins
globally disabled; backed-up `enabled` values are ignored.

### SSRF-safe URL handling

Any URL constructed or followed for resolution/play (when a channel is later selected)
must be constrained to an owner-recorded allowlist of hosts, schemes (`https` only
unless the channel record explicitly requires another), redirect hop limits, and
maximum response sizes. Literal operator-pasted signed playback URLs, `file://`,
link-local, metadata, or private-network targets are rejected. Redirects outside the
allowlist abort. Fixture tests cover reject cases with synthetic URLs; CI must not
contact real hosts.

### Secrets, logging, and persistence

Playback URLs, anonymous session tokens, cookies, and account credentials:

- exist only in process memory for the active attempt;
- are never written to disk, databases, queues, logs, traces, fixtures, hashes of
  secrets, worker protocol messages, or object storage;
- are cleared on stop, disable, denylist match, reconnect replacement, and process exit.

Diagnostics retain only stable reason codes, counters, redacted hostnames (no query
strings), and synthetic fixture identifiers. Absolute local paths in retained logs are
redacted to basename where needed.

### Audio ownership handoff to Issue #8

Accepted Issue #8 states that #7 **must not** hand a playback URL or arbitrary encoded
stream into the current raw-PCM pipe interface. Therefore:

1. **Fixture/contract path (default for CI):** no audio bytes. Status and metadata
   doubles only.
2. **Real media path (future, gated):** the adapter may feed #8 only after an owning
   artifact defines exact codecs, duration evidence before retention, internal
   allocation limits, SSRF/rights controls, and compatibility tests that extend #8’s
   admission inventory. Until that admission lands and `audio_budget_unverified` is
   cleared for the exact FFmpeg/host build, real media stays blocked.
3. No second unbounded ring, disk spool, or duplicate VAD pipeline. Connection
   replacement must not retain old playback addresses or old audio buffers; teardown
   aligns with #8 cancel/disable clearing and backpressure.

Assigning real PCM toward a community worker additionally requires Issue #28 protocol
support and independent rights evidence. Completing this adapter is not that grant.
Local #8/#9 loops do not depend on this Issue.

### Fixture and test surface

Implementation (separate PR after this artifact merges) must provide:

- Desensitized JSON/metadata fixtures covering field churn, offline/live/paywalled/
  login-required/geo/DRM-like error shapes, and denylist/kill-switch stops—**no live
  capture**, no cookies, no real playback URLs with secrets.
- Deterministic unit tests for canonical room resolution, eligibility refusal, state
  transitions, backoff ceilings, locator clearing on reconnect/stop, and redaction.
- A `make` target such as `ingest-check` that runs fixture/contract tests and prints
  that real network/channel/rights acceptance remains pending. Skipping real gates as
  “pass” is forbidden.

No untrusted CI job may perform live Bilibili requests.

## Interfaces and compatibility

- Code (future implementation PR only): adapter module under the backend modular
  monolith (exact path named in that PR), `tests/ingest/` (or equivalent), fixture
  corpus, and `make ingest-check`.
- Wire protocol remains v1 unchanged. No new `epoch` / `seq` / `revision` semantics.
- This documentation PR adds **only** the four Markdown files under
  `docs/changes/7-bilibili-room-ingest/`.

## Failure modes and disable path

| Condition | Outcome |
| --- | --- |
| Non-operator actor attempts start/stop | Denied; no state change |
| Ambiguous room selector / denylist / kill switch | Deny or stop; clear locators/audio |
| Anonymous parse fails; login/paywall/geo/DRM/rate-limit | Safe stop; no credential fallback |
| Channel unselected / rights missing / production OFF | `blocked_evidence` (or equivalent); no sockets |
| #8 budget unverified / encoded admission missing | No audio admission |
| Stall beyond retry budget | `ENDED`; locators cleared |
| Reconnect | New eligibility; never reuse stale playback locator |

## Security, privacy, and data lifecycle

Treat Bilibili as an untrusted mutable boundary. Validate size/schema before any
normalization. Never persist raw platform payloads in this Issue’s scope. Never send
playback locators or credentials to workers. Audio remains ephemeral per AGENTS.md and
Issue #8. Public availability is not a redistribution grant.

## Acceptance criteria

- [ ] Only operator/admin can start or stop one room; public cannot create ingest tasks.
- [ ] Anonymous failure, paywall/login, geo/DRM, and rate-limit cases stop safely without
  credential fallback or access bypass.
- [ ] Global kill switch and room denylist immediately block new acquisition and tear
  down the active attempt with locator/audio clear.
- [ ] Retries use exponential backoff, hard caps, and payload-free status events.
- [ ] Playback URLs/anonymous tokens stay in memory and never appear in logs, DBs,
  fixtures, or worker messages.
- [ ] Desensitized fixtures cover upstream field changes and error states; CI claims no
  live integration pass.
- [ ] Adapter audio path uses only Issue #8’s verified controlled interface after
  encoded-admission and budget clearance; no parallel unbounded buffer.
- [ ] Platform stall/reconnect clearing stays consistent with #8 cleanup/backpressure;
  connection replacement drops old locators and audio.
- [ ] Completing the adapter does not authorize production enablement, #28 worker PCM
  disclosure, or Issue #10 danmaku scope.
