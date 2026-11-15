# Intent: Internal offline normalization of danmaku / SC / status fixtures

## Issue and owner

- GitHub Issue: [#10](https://github.com/Shuang-su/Livecho/issues/10)
- Human owner: @Shuang-su
- Stage/area/risk: `stage:m1`, `area:events` / `area:protocol`, `risk:high`

## Problem

Aside from captions, ordinary danmaku, superchat (SC), and live-room status lack a
shared identity, dedup key, closed normalized shape, and a safe boundary that keeps
raw business fields out of ordinary APIs. Accepted protocol v1.0 `TimelineEventV1`
carries only transcript and session-status payloads. Extending that wire now would be
speculative. An **internal** normalize/dedup engine against desensitized fixtures can
still land without changing protocol, WebSocket publication, #29 UI, or #16 archive.

## Desired outcome

### Immediate first implementation slice (authorized after this docs merge)

An **internal, offline, normalize-only** backend module that:

1. Accepts **visibly synthetic / desensitized** fixture envelopes (not claimed live
   Bilibili schemas) for four logical classes: danmaku, superchat, status, and
   transcript-shaped companion rows used only for shared identity/dedup tests.
2. Emits closed **in-process** normalized records with stable type, source timestamp,
   received timestamp, and source-event identity; applies size/count caps, dedup,
   bounded queues, and payload-free rejection/alerts.
3. Never publishes to `TimelineEventV1`, viewer WebSocket, ordinary HTTP, logs as chat
   bodies, databases, or Bucket.
4. Never opens network sockets; never enables live chat, cookies/accounts, or raw
   personal/chat persistence.
5. Keeps #11 caption/status-only; does not implement #29 display.

### Explicitly deferred (not selected by merging these docs)

- Viewer `protocol_minor = 1` (or any) wire extension of `TimelineEventV1` for
  danmaku/SC — requires a **separate** owner decision and protocol artifact with
  goldens/BC evidence.
- Timeline/WS publication, schema/codegen changes, #29 UI, #16 raw archive ON,
  live Bilibili chat acquisition, production enablement.

Merging this documentation is a **conservative sequencing** choice for an internal
fixture path under current accepted v1. It is **not** approval of a new protocol
minor, rights grant, or production feature.

## Non-goals

- Protocol model edits, JSON Schema/TS codegen, or minor bumps in the first slice.
- Timeline/WebSocket/public API publication of danmaku/SC.
- #29 viewer display; #16 durable raw archive; #7 live chat sockets.
- Live network, cookies/accounts, paid/member/private content, or inventing exact
  upstream Bilibili message schemas as “truth.”
- Silent `epoch` / `seq` / `revision` changes or stuffing chat into transcript `text`.

## Constraints and data impact

- Honor AGENTS.md and accepted #2/#3/#7/#11: closed wire remains unchanged; public
  surfaces stay normalized-only when later enabled; ingest/chat live paths stay gated.
- Fixtures are synthetic stand-ins; **source shape uncertainty is recorded**—fields are
  representative for testing privacy/dedup, not reverse-engineered live contracts.
- Data classification: in-memory normalized test records only; no durable chat/person
  text; diagnostics payload-free.

## Success signal

(a) Green offline normalize/dedup/reject fixture checks; (b) honest closed gates for
live chat / wire publish / raw archive; (c) no claim that docs merge selected a
protocol minor or enabled #29/#16. Wire publication remains a separate future decision.

## Human decision

- Status: Proposed; **documentation only**. Implementation forbidden until owner-merge.
- Approved by/date: Pending @Shuang-su review and merge.
- Protocol-minor / wire publication / #16 / live chat: **not decided here**; deferred.
