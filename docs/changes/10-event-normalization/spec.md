# Specification: Danmaku / SC / status event normalization

This specification implements owning [Issue #10](https://github.com/Shuang-su/Livecho/issues/10)
using accepted [architecture/risk](../2-architecture-risk-boundaries/spec.md),
[protocol v1](../3-protocol-v1-contract/spec.md), [Bilibili ingest](../7-bilibili-room-ingest/spec.md),
and [subtitle web](../11-subtitle-web/spec.md) boundaries. Owner comment on Issue #10
(2026-09-26) and Issue #31 (D5/D6, E2/E4) require explicit dedup/statistics contracts
without treating same-site data as independent verification. Closed drafts are not
accepted scope. Issue #29 owns public viewer display of danmaku/SC and is out of this
PR’s product surface.

## Behavior

### Representability gate (protocol)

Accepted `TimelineEventV1` today admits only:

- `TranscriptTimelinePayloadV1`
- `SessionStatusTimelinePayloadV1`

**Danmaku and superchat are not representable on protocol minor 0.** This Issue must
not pretend delivery by smuggling platform JSON into `text`, status `reason_code`, or
extra fields. Implementation is split:

| Phase | Content | Authorization |
| --- | --- | --- |
| This documentation PR | Closed normalized payload contracts, privacy/dedup rules, flags, and test plan | Docs merge only |
| Later implementation PR(s) | Python source models → JSON Schema/TS; goldens; normalize/dedup engine; feature flag | After this artifact merges; protocol change requires goldens + BC evidence |
| Raw durable archive | Encrypted private Bucket / admin export | Issue #16 + rights gates only |
| Viewer danmaku/SC UI | Rendering | Issue #29 |

### Recommended protocol extension (owner decision)

**Recommendation:** introduce viewer **`protocol_minor = 1`** that extends the
`TimelineEventV1.payload` closed union with exactly two new StrictModel branches
(names illustrative until implementation locks identifiers):

1. **`DanmakuTimelinePayloadV1`** — closed fields only, for example:
   - `kind: "danmaku"` (or equivalent discriminant compatible with existing branch
     selection rules)
   - `source_event_id` (bounded NFC/ASCII identity from upstream after validation)
   - `source_ts` / binding to envelope `occurred_at` rules as defined in goldens
   - `text` (NFC, 1–512 scalars unless owner revises)
   - optional `sender_display` (NFC, bounded; never account cookies or auth ids)
   - no nested maps, HTML, URLs-as-actions, or binary

2. **`SuperChatTimelinePayloadV1`** — closed fields only, for example:
   - `kind: "superchat"`
   - `source_event_id`, timestamps as above
   - `text` (NFC, bounded)
   - optional `amount_display` / `currency_code` as **display strings** from an
     allowlist (not opaque money objects)
   - optional `sender_display`
   - no payment-processor secrets, QR payloads, or raw platform blobs

`SessionStatusTimelinePayloadV1` remains the status branch (already on minor 0).
Transcript remains unchanged. **Do not change** the meaning of `epoch`, stream `seq`,
or object `revision`. Immutable projections for new payloads must pin identity + time
bounds analogous to transcript (`event_id`, `occurred_at`, segment-like keys) and be
golden-tested.

**Old clients (minor 0):** negotiate minor 0; backend **must not** emit danmaku/SC
payloads on that connection. Unknown/unsupported payload shapes are rejected at the
publisher with stable codes—never coerced into transcript text.

If the owner prefers to keep minor 0 and only document internal normalize structs
without wire publication until a later protocol Issue, that is an acceptable alternate;
wire publication still cannot proceed without an accepted protocol change. This
artifact’s default recommendation is the minor-1 path above so #29 has a clear wire
target.

### Four event classes and identities

Every normalized event (transcript, danmaku, SC, status) carries:

| Field | Rule |
| --- | --- |
| Logical type | Closed discriminant (`transcript` / `danmaku` / `superchat` / `session_status`) |
| Source timestamp | Upstream or synthetic fixture time; validated bounds |
| Received timestamp | Backend observe time; never secret-bearing |
| Viewer `seq` | Exact-next allocator per session/epoch (existing #3 rules) |
| Source event identity | Stable key for dedup (platform id after validation, or fixture id) |
| `event_id` / `revision` | Existing TimelineEventV1 rules; finals/immutability per payload class |

Dedup keys are **source-event identity scoped to room/session/epoch**, distinct from
worker transcript segment revision domains (owner #31 note). Worker-result dedup and
source-event dedup are separately tested.

### Ordering, reconnect, and queues

- One owner serializes normalize → publish for a session.
- Bounded in-memory queues only; overflow drops with counters + payload-free alerts,
  never disk spill.
- Reconnect / upstream duplicate / reorder fixtures must prove: no double publish for
  the same source identity; late duplicates acknowledged without state corruption;
  gaps surface as status/alerts without inventing filler events.
- Backend restart clears ephemeral normalize buffers; durable resume of raw chat is
  not claimed until #16.

### Normalization vs raw

| Layer | Contents | Retention in this Issue |
| --- | --- | --- |
| Upstream fixture/raw candidate | Desensitized synthetic platform-like JSON | Test fixtures only; no live capture |
| Sanitized raw (future) | Credential/locator/audio-stripped business JSON | **Blocked** until #16; in-memory optional for tests that immediately discard |
| Normalized projection | Closed allowlist fields only | In-memory / future restricted DB under #16 purpose gates |
| Public/ordinary API | Allowlisted normalized subset | Never raw; #29 consumes normalized wire after protocol enablement |

Before any retention candidate, reject or clear: cookies, auth tokens, signed playback
URLs, audio/PCM/WAV/base64, and unknown nested blobs. Malicious text is kept as text
only (no HTML/Markdown execution). Field missing / unknown extra field / schema invalid
→ reject normalize with stable reason; do not partially publish open objects.

### Unparseable upstream shapes

New or undecodable platform messages produce **payload-free structured alerts**
(reason code + counters). They must not enter `TimelineEventV1`, logs as raw bodies,
or synthetic “best effort” text.

### Feature flag and live acquisition

Platform chat adapter is behind a feature flag default **off**. Live Bilibili danmaku
sockets remain gated by Issue #7 channel/rights/production decisions
(`BILI-ACQ-001` / `BILI-DEC-001`). This Issue’s CI path is fixture-only: no real network,
no cookies, no paid/member/private content. Completing normalize tests does not enable
ingest or production.

### Public projection allowlist

Public/ordinary projection is an **explicit allowlist** per payload class (final field
list locked in the implementation PR goldens). Tests must cover: missing required
field, unknown extra field, duplicate/reorder, malicious text, and sensitive-payload
refusal. #29 may only render allowlisted normalized fields.

### Statistics note (Issue #31)

Short-window or site-derived counts are not independent verification. Effective zeros,
missing observations, unsupported fields, and disconnects must remain distinguishable
in counters/alerts. This Issue does not ship public statistics surfaces.

## Interfaces and compatibility

- Documentation (this PR only): four Markdown files under
  `docs/changes/10-event-normalization/`.
- Future code: backend normalize module, desensitized fixtures, `make` check target,
  protocol model/golden updates under the chosen minor, Python/TS parity.
- Wire: no silent extension of minor 0. Epoch/seq/revision semantics unchanged unless
  a separate protocol Issue + BC evidence says otherwise (not expected here).

## Failure modes and disable path

| Condition | Outcome |
| --- | --- |
| Feature flag off / channel rights missing | No live chat; fixtures may still unit-test normalize |
| Payload not in closed schema | Reject; alert; no publish |
| Sensitive fields present | Strip/reject before any retention candidate |
| Duplicate source identity | No second publish; stable ack/counter |
| Minor 0 viewer subscribed | Danmaku/SC not emitted |
| #16 not ready | No DB/Bucket raw archive |

## Security, privacy, and data lifecycle

Chat text and platform identifiers are sensitive. Raw business payloads are high-risk.
Ordinary APIs and browsers never receive raw. Logs are payload-free. Audio remains
forbidden in this path. Kill switch / denylist from #2/#7 stop new acquisition and
clear ephemeral buffers without depending on the chat parse path.

## Acceptance criteria

- [ ] Four event classes defined with type, source/received time, seq, and source
  identity; transcript remains compatible.
- [ ] Closed danmaku/SC normalized payloads specified; no arbitrary raw objects on
  `TimelineEventV1`.
- [ ] Protocol extension path explicit (recommended minor 1) with negotiation, old
  client behavior, and unchanged epoch/seq/revision meaning.
- [ ] Fixture tests planned for reconnect duplicate, reorder, unknown fields, malicious
  text, and sensitive-field refusal.
- [ ] Raw vs normalized separation; cookies/tokens/signed URLs/audio cleared or rejected.
- [ ] Unparseable events → payload-free alerts only.
- [ ] Adapter feature flag default off; no live CI chat; no implicit #16 archive ON.
- [ ] #29 UI and production enablement remain out of scope; no auto-close of #10 on
  docs merge alone.
