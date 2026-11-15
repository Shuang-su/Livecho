# Intent: Normalize danmaku, superchat, and live status onto the shared timeline

## Issue and owner

- GitHub Issue: [#10](https://github.com/Shuang-su/Livecho/issues/10)
- Human owner: @Shuang-su
- Stage/area/risk: `stage:m1`, `area:events` / `area:protocol`, `risk:high`

## Problem

Aside from captions, ordinary danmaku, superchat (SC), and live-room status lack a
shared timeline identity, dedup key, closed normalized shape, and a safe boundary for
raw business payloads. Accepted protocol v1.0 `TimelineEventV1` carries only
`TranscriptTimelinePayloadV1` and `SessionStatusTimelinePayloadV1`. Treating platform
objects as free-form JSON on that wire would violate Issue #3’s closed-payload rule and
leak high-risk fields into ordinary APIs.

## Desired outcome

Define and later implement **backend event normalization** that:

1. Captures four event classes on one ordered timeline with transcript: **danmaku**,
   **superchat**, **status**, and existing **transcript**—each with stable `type`,
   source timestamp, received timestamp, viewer `seq`, and source-event identity.
2. Publishes only **closed, allowlisted normalized payloads** on `TimelineEventV1`
   after an explicit protocol extension (not arbitrary raw objects).
3. Keeps sanitized raw business payloads **separate** from normalized projections;
   strips cookies, auth tokens, signed URLs, and any audio/base64 before any retention
   candidate; never exposes raw payloads on ordinary/public APIs.
4. Handles reconnect duplicates, upstream repeats, and reordering with fixture tests;
   unparseable new upstream shapes yield payload-free structured alerts only.
5. Gates the platform adapter behind a feature flag defaulting **off**; no live
   Bilibili chat acquisition in CI or by default.

Issue #11’s first web surface stays caption/status only. Issue #29 owns danmaku/SC
**viewer display** and depends on this Issue plus #11. Issue #16 owns durable raw
archive enablement; this Issue must not silently turn on Postgres/Bucket persistence.

## Non-goals

- Long-term Bucket archival or production raw enablement (#16).
- Exposing raw payloads on ordinary/public APIs or browser caches.
- Issue #29 UI, accounts/devices, M2, long-live leasing, or deployment switches.
- Live Bilibili network chat, cookies/accounts, paid/member/private content, or
  claiming live integration from fixture greens.
- Silent `epoch` / `seq` / `revision` semantic changes, or inventing protocol fields
  only in UI code.
- Broadening #7 into credentialed acquisition or production ingest ON.

## Constraints and data impact

- Honor AGENTS.md and accepted #2/#3: closed wire models; payload-free errors; raw
  archives encrypted/admin-only/deletable when #16 eventually enables them; public
  surfaces get normalized data only.
- Protocol v1.0 cannot represent danmaku/SC today. This Issue’s implementation must
  land via an **explicit protocol extension** (recommended: viewer `protocol_minor`
  bump) with shared goldens and Python/TypeScript parity—not by stuffing unknown maps
  into existing payloads.
- Data classification: normalized chat/status are restricted; sanitized raw business
  payloads are high-risk; credentials/locators/audio must never be retained. Fixture
  corpora are desensitized synthetic metadata/text only.

## Success signal

Reviewers can distinguish (a) green fixture normalize/dedup/reject tests, (b) honest
`blocked_evidence` / feature-flag-off when live acquisition or raw persistence gates
are missing, and (c) a separately documented protocol-minor enablement with goldens.
No draft claims live chat pass, raw archive ON, or #29 UI completion.

## Human decision

- Status: Proposed; **documentation only**. Implementation is forbidden until this
  artifact PR’s intent/spec/plan are owner-merged (CONTRIBUTING / AGENTS).
- Approved by/date: Pending @Shuang-su review and merge.
- Protocol-minor selection, public allowlist finalization, and #16 raw enablement:
  Pending separate owner decisions; these docs do not authorize production persistence
  or live platform chat.
