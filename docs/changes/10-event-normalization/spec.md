# Specification: Internal offline event normalization (first slice)

This specification implements owning [Issue #10](https://github.com/Shuang-su/Livecho/issues/10)
using accepted [architecture/risk](../2-architecture-risk-boundaries/spec.md),
[protocol v1](../3-protocol-v1-contract/spec.md), [Bilibili ingest](../7-bilibili-room-ingest/spec.md),
and [subtitle web](../11-subtitle-web/spec.md). Owner comment on Issue #10 (2026-09-26)
and Issue #31 (D5/D6, E2/E4) inform dedup/privacy notes only. Closed drafts are not
accepted scope. Issue #29 (viewer danmaku/SC display) and Issue #16 (raw archive) are
out of the first slice.

## Phasing (normative)

| Slice | In scope | Out of scope |
| --- | --- | --- |
| **First implementation (after this docs merge)** | Internal offline normalize/dedup against synthetic fixtures; closed in-process records; feature flag for any future live adapter remains **off** | Protocol edits, codegen, `TimelineEventV1` / WS publication, #29 UI, #16 archive, live network |
| **Deferred** | Viewer wire danmaku/SC (e.g. hypothetical `protocol_minor = 1`), public allowlist publication, durable sanitized raw | Not selected by merging these docs |

**Danmaku/SC are not representable on accepted protocol minor 0.** The first slice must
not pretend wire delivery (including via transcript `text` or status `reason_code`).

### Deferred protocol note (non-authorizing)

A future owner-approved protocol artifact may propose closed `TimelineEventV1` payload
branches and a minor bump. That work needs separate intent/spec/plan, goldens, and
backward-compatibility evidence. **This documentation merge does not choose or approve
that extension.** Until then, normalized records stay process-internal.

## First-slice behavior

### Synthetic fixture input (desensitized)

Fixtures are **visibly synthetic**. They are not claimed to match live Bilibili wire
schemas. Upstream field names and nesting remain **uncertain** until an owner-selected
acquisition channel documents them; adapters map real shapes later under #7 gates.

Each fixture item is a JSON object with **exactly** these top-level keys (extra keys →
`schema_invalid`):

| Key | Type | Rule |
| --- | --- | --- |
| `fixture_class` | string | One of `danmaku`, `superchat`, `status`, `transcript_companion` |
| `source_event_id` | string | 1–128 chars; conservative ASCII `[A-Za-z0-9._:-]` |
| `source_ts` | string | RFC 3339 UTC with `Z` (same discipline as protocol timestamps) |
| `body` | object | Class-specific closed map below |

**Sensitive keys anywhere in the object** (case-insensitive name match) cause hard
reject `sensitive_field_refused` before normalize: `cookie`, `cookies`, `authorization`,
`auth_token`, `sessdata`, `bili_jct`, `signed_url`, `playback_url`, `pcm`, `wav`,
`audio`, `base64`, `password`. Nested objects/arrays are not walked for open content—
any nested `object`/`array` value under `body` is `schema_invalid` (flat body only).

#### `body` allowlists by class

**`danmaku`** — required: `text` (NFC string, 1–512 Unicode scalars). Optional:
`sender_display` (NFC, 1–64). No other keys.

**`superchat`** — required: `text` (NFC, 1–512). Optional: `sender_display` (1–64),
`amount_display` (1–32 NFC display string), `currency_code` (3–8 ASCII `[A-Z]`). No
other keys. Amounts are display strings only—not money objects or processor payloads.

**`status`** — required: `status` in
`starting` \| `live` \| `stopping` \| `stopped` \| `failed`. Optional: `reason_code`
(1–64 conservative ASCII). No other keys. Aligns with existing session-status vocabulary
for internal tests only—not a wire publisher.

**`transcript_companion`** — required: `text` (NFC, 1–4096), `start_ms` / `end_ms`
(ints, `0 <= start_ms < end_ms <= start_ms + 30000`). Optional: `is_final` (bool).
Used only to exercise shared identity/dedup alongside chat fixtures; **must not** be
emitted on viewer APIs by this module.

### Normalized output record (in-process only)

Successful normalize yields a closed dict (or StrictModel in implementation) with
**exactly**:

| Field | Rule |
| --- | --- |
| `schema_version` | Literal `1` |
| `class` | Same as `fixture_class` |
| `source_event_id` | Echo validated id |
| `source_ts` | Echo validated source time |
| `received_ts` | Backend observe time (injectable clock in tests) |
| `room_id` | Operator-supplied synthetic room id for the batch (1–64 conservative ASCII) |
| `session_id` | Synthetic session UUID string for the batch |
| `payload` | Closed projection: only the allowlisted `body` fields that validated |

No viewer `seq`, no `event_id` wire envelope, no protocol `revision` assignment in this
slice (those belong to a future publisher bound to #3). Dedup and ordering use
`(room_id, session_id, source_event_id)` as the source-event key (Issue #31: distinct
from worker transcript revision domains).

### Dedup, ordering, queues, backpressure

| Control | Cap / rule |
| --- | --- |
| Batch input size | ≤ 256 fixture items per `normalize_batch` call |
| Single item JSON size | ≤ 8 KiB UTF-8 |
| Dedup map entries | ≤ 4,096 distinct source-event keys per session; insert beyond → drop with `dedup_capacity` alert |
| Output queue | ≤ 256 normalized records retained for the test harness; overflow → drop oldest with `queue_overflow` counter (never disk) |
| Duplicate `source_event_id` in same room/session | Second+ → `duplicate_suppressed`; no second normalized emit |
| Reorder | Items processed in call order; late duplicate still suppressed; no invented gap fillers |
| Unparseable / wrong class / bad NFC / oversize text | `schema_invalid` or `text_invalid`; payload-free alert only |

Reconnect-style fixtures are simulated by re-feeding the same synthetic ids after a
cleared or retained dedup map as the test specifies—no network.

### Alerts and logging

Alerts are payload-free: `{ "reason": <stable code>, "counters": {...} }` only. Never
log `text`, `sender_display`, raw fixture bodies, or secrets. Stable reasons include:
`schema_invalid`, `sensitive_field_refused`, `text_invalid`, `duplicate_suppressed`,
`dedup_capacity`, `queue_overflow`, `batch_too_large`, `live_adapter_disabled`,
`wire_publish_disabled`, `archive_disabled`.

### Feature flags (default closed)

| Flag | Default | First-slice behavior |
| --- | --- | --- |
| Live chat adapter | off | Any live/network entry returns `live_adapter_disabled` |
| Wire / Timeline publish | off | Any publish attempt returns `wire_publish_disabled` |
| Raw archive | off | Any persist attempt returns `archive_disabled` |

Fixtures may call normalize without flipping these flags.

### Privacy and data lifecycle

- No durable chat or personal text. Process exit clears maps/queues.
- No cookies, signed URLs, or audio in fixtures or outputs.
- Ordinary APIs and browsers are not consumers of this module in the first slice.
- Kill switch / denylist from #2/#7 are not required to unit-test pure normalize, but
  any future live adapter must honor them before calling normalize.

### Goldens / tests required for first implementation PR

Desensitized fixtures + deterministic tests must cover at least:

1. Happy path each class → exact allowlisted output fields.
2. Extra top-level / body key → reject.
3. Sensitive key name → `sensitive_field_refused`.
4. Oversize text / batch / item bytes → reject or cap alert.
5. Duplicate source id → single emit + `duplicate_suppressed`.
6. Reorder + re-feed reconnect simulation → no double emit when dedup retained.
7. Nested object in body → `schema_invalid`.
8. Import/normalize path opens **no sockets**; no file writes of chat text.
9. Attempts to “publish” or “archive” hit disabled reasons.
10. Document in evidence that fixtures are synthetic and upstream shape is uncertain.

`make events-check` (name may match implementation) runs these tests and prints that
live chat, wire publish, protocol extension, and raw archive remain pending.

## Interfaces and compatibility

- **This docs PR:** only the four Markdown files under
  `docs/changes/10-event-normalization/`.
- **First code PR:** internal module under the backend monolith (path named then),
  fixture corpus, tests, `make events-check`. **No** changes to
  `packages/protocol` models, goldens, or codegen.
- Accepted v1 wire semantics unchanged. #11 remains caption/status only.

## Failure modes

| Condition | Outcome |
| --- | --- |
| Invalid fixture / sensitive field | Reject; alert; no normalized emit |
| Duplicate source id | Suppress; counter |
| Live/wire/archive entry points | Disabled reasons; no side effects |
| Protocol publish attempted | Forbidden in first slice |

## Security, privacy, and data lifecycle

Internal normalized records are restricted test/memory artifacts. Raw business payloads
are not archived. Logs stay payload-free. Audio forbidden.

## Acceptance criteria

### First slice (docs + subsequent impl)

- [ ] Internal normalize-only contracts above are implementable without protocol edits.
- [ ] Closed input/output allowlists, caps, dedup, backpressure, and reject reasons are
  specified; synthetic fixture uncertainty recorded.
- [ ] No Timeline/WS publication, #29 UI, #16 archive, or live network in first slice.
- [ ] Docs merge does **not** select `protocol_minor = 1` or any wire extension.

### Deferred (separate owner/protocol work)

- [ ] Closed wire danmaku/SC payloads, minor negotiation, goldens, BC evidence.
- [ ] Public projection allowlist for #29; #16 sanitized-raw enablement; live chat under
  #7 rights/channel gates.
