# Intent: Public free Bilibili room resolution and ingest state machine

## Issue and owner

- GitHub Issue: [#7](https://github.com/Shuang-su/Livecho/issues/7)
- Human owner: @Shuang-su
- Stage/area/risk: `stage:m1`, `area:ingest`, `risk:high`

## Problem

Livecho cannot identify one operator-selected, free, unauthenticated Bilibili room and
drive a bounded OFFLINE→STARTING→LIVE→STALLED→RECONNECTING→ENDED state machine with
kill-switch and denylist stop paths. Without an accepted contract, any adapter risks
credential fallback, SSRF, playback-token persistence, or inventing an audio path that
bypasses Issue #8’s controlled interface and `audio_budget_unverified` gate.

## Desired outcome

Define a replaceable Bilibili **public-room adapter contract** that:

1. Resolves only an **operator/admin-selected** room to one canonical `room_id`, checks
   free/anonymous/live eligibility, and refuses login, payment, membership, geographic,
   DRM, rate-limit, and uncertain-rights cases by stopping safely.
2. Runs the Issue-named room state machine with exponential-backoff reconnects, hard
   caps, and payload-free status events; honors global kill switch and room denylist
   immediately for new starts and active sessions.
3. Keeps playback URLs and anonymous session tokens **in process memory only**—never in
   logs, databases, fixtures, worker messages, or disk.
4. Hands audio to Issue #8 **only** through that Issue’s verified controlled input
   interface after encoded-admission and rights gates; never hands a playback URL or
   arbitrary encoded stream into #8 as it exists today.
5. Ships **desensitized/synthetic fixtures** for parser, eligibility, reconnect, and
   error-state tests. Real network acquisition stays closed until the owner-selected
   acquisition channel (`BILI-ACQ-001`), rights record, and production decision
   (`BILI-DEC-001`) allow it.

Local #8/#9 synthetic caption loops do not require this Issue. Completing the adapter
does not authorize worker PCM distribution (#28) or production enablement.

## Non-goals

- Bypassing login, paywalls, membership, geographic restriction, DRM, or rate limits.
- Auto-discovery, historical crawl, public submission of rooms, or public start/stop.
- Cookie / login-state fallback (Issue #31 reviews voluntary credentialed acquisition
  separately; anonymous failure must not fall back to cookies).
- Danmaku / SC ingestion (#10), public accounts, long-live leasing, deployment/M2
  enablement, or community-worker media disclosure.
- Inventing an unbounded second audio pipeline, writing PCM/WAV/base64, or claiming
  live integration success from fixture greens.
- Selecting a Bilibili acquisition channel or fabricating platform/rights permission.

## Constraints and data impact

- Honor AGENTS.md and accepted Issue #2: modular monolith; production ingest default
  off; only operator-selected free anonymous streams; never send credentials, cookies,
  or signed playback URLs to community workers.
- Issue #8 remains binding: no playback-URL handoff; `audio_budget_unverified` cannot
  be bypassed; encoded formats need an owning admission definition before real media.
- Issue #9 local vertical stays synthetic/fixture; this Issue must not force platform
  access into that loop.
- Data classification: ephemeral playback locators/tokens in RAM; payload-free status
  and counters retained; desensitized metadata fixtures only—no live media, cookies,
  or recoverable encodings in the repository.

## Success signal

Reviewers can distinguish (a) green fixture/contract checks for parse/eligibility/
state/reconnect/denylist, (b) honest `blocked_evidence` / safe-stop when channel,
rights, kill switch, denylist, or #8 audio gates are missing or failed, and (c)
separately recorded trusted-host live probes that never run in untrusted CI. No draft
claims production or live integration pass.

## Human decision

- Status: Proposed; **documentation only**. Implementation is forbidden until this
  artifact PR’s intent/spec/plan are owner-merged (CONTRIBUTING / AGENTS).
- Approved by/date: Pending @Shuang-su review and merge.
- Channel/rights/production authorization: Pending separate owner records; these docs
  do not authorize network acquisition, media download, or production enablement.
