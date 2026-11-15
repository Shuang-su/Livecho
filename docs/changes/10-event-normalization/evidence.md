# Evidence: Event normalization artifacts

## Artifact approval

- Artifact PR: [#52](https://github.com/Shuang-su/Livecho/pull/52) (documentation draft)
- Approved by/date: Pending @Shuang-su review and merge
- Base: `main` at `d3dae9f9472df274aba6bf3151b9b513b8a63456`. Owning Issue #10 reread
  2026-11-15; revised same day after parent feedback on unresolved protocol choice.
- Branch: `issue/10-event-normalization`

## Revision note (2026-11-15)

Parent inspected head `2e07618` and required the immediate first implementation slice to
be unambiguously **internal / offline / normalize-only**, without treating docs merge as
selection of viewer `protocol_minor = 1`. All four artifacts were revised accordingly:
minor-1 / Timeline publication moved to **deferred**; concrete fixture allowlists, caps,
dedup, backpressure, and reject reasons specified for the first slice. This is a
**sequencing** clarification under accepted v1—not protocol approval.

## Prior art (not approval)

No prior merged `docs/changes/10-*`. Accepted #3: v1.0 timeline is transcript +
session-status only. Issue #10 / #31 comments are governance context only. Closed
drafts not copied blindly.

## Scope reconciliation

| Topic | Issue #10 | Accepted deps | This artifact (revised) |
| --- | --- | --- | --- |
| First code slice | Normalize + privacy/dedup | #3 closed wire; #11 caption/status | Internal offline normalize only |
| Wire danmaku/SC | Eventual closed payloads | Not on minor 0 | **Deferred**; docs merge does not select minor 1 |
| Raw archive | Strip secrets; #16 durable | #2/#16 | Blocked; `archive_disabled` |
| UI | Not this Issue | #29 display | Out of scope |
| Live chat | Feature flag; fixtures | #7 OFF | Synthetic fixtures; adapter off |

## Requirements-author exposure and provenance

- Author: Cursor Auto (cloud agent), 2026-11-15 (initial + revision).
- Inputs: AGENTS.md, CONTRIBUTING.md, Issue #10 (+ comment), #2/#3/#7/#11 artifacts,
  parent instruction to prefer internal-first sequencing.
- No live chat, accounts, downloads, paid APIs, user-machine access, or fabricated
  protocol/rights approval. Fixtures remain synthetic; upstream shape uncertainty
  recorded in spec.

## Automated verification

| Exact command | Result | Date/tree |
| --- | --- | --- |
| `make artifacts` | Exit 0; `change artifacts: ok` | 2026-11-15 / revision on `issue/10-event-normalization` |
| `git diff --check` | Exit 0; no whitespace errors | 2026-11-15 |
| `make verify` | Exit 0; Ruff/mypy/TypeScript ok; `910 passed, 1 deselected`; protocol 262 + Railway 63 + web 51 Vitest; artifact/protocol checks and build ok | 2026-11-15 |
| Local Markdown link check | Relative refs to #2/#3/#7/#11 specs; 0 broken | 2026-11-15 |
| `git diff --cached --name-only` | Exactly four files under `docs/changes/10-event-normalization/` | 2026-11-15 |

## Manual or hardware evidence

None.

## Review findings (critical review of revision)

- **Protocol choice:** Removed “default recommend minor 1 for first impl”; deferred
  wire extension so merge cannot be read as minor selection.
- **Implementability:** First slice now has explicit input/output allowlists, byte/count
  caps, dedup key, queue policy, and stable reject reasons.
- **Honesty:** Synthetic fixtures + source-shape uncertainty called out; no invented
  live Bilibili schema.
- **Boundaries:** No Timeline/WS/#29/#16/live network in first slice; #11 unchanged.

## Deviations

Branch `issue/10-event-normalization`. Docs only. No product/protocol code.

## Release and rollback evidence

Not deployed. No live chat, protocol minor, or raw archive gate enabled.

## 2026-11-15 — First implementation (internal/offline/normalize-only)

Implementer: Cursor Auto (cloud agent). Parent squash-merged docs PR #52 as
`6ec9ad18c4d7c7dc80b4fcb3e5a9ae167ddc12f5`. Branch:
`issue/10-event-normalization-impl` from that `main`. Accepted intent/spec/plan were
**not** rewritten; this section appends implementer evidence only.

### What landed (CI-safe only)

- `services/backend/src/livecho_backend/events/` — closed fixture allowlists, NFC/
  type/range validation, sensitive-key refusal, in-process normalize/dedup engine,
  bounded output queue, closed feature flags (`live_adapter_disabled` /
  `wire_publish_disabled` / `archive_disabled`)
- Desensitized synthetic fixtures under `events/fixtures/` (visibly labeled; **not**
  claimed as live Bilibili wire schemas)
- `tests/events/` + `make events-check`
- **No** `packages/protocol` edits, Timeline/WS publication, #29 UI, #16 archive,
  live upstream traffic, cookies/accounts, audio/MLX, or raw chat persistence

### Caps recorded

| Cap | Value |
| --- | ---: |
| Batch items / `normalize_batch` | 256 |
| Single item JSON UTF-8 | 8 KiB |
| Dedup map entries / session | 4,096 |
| Output queue retention | 256 |

### Critical-review findings and fixes

- Extra body keys with present `text` previously risked mis-labeling as
  `text_invalid`; validators now classify allowlist/type failures as
  `schema_invalid` and NFC/length failures as `text_invalid` (regression covered).
- Dedup insert deferred until after closed output-record construction so a
  defensive key mismatch cannot poison the map.
- Dedup identity documented as `(room_id, session_id, source_event_id)` with
  per-engine storage of `source_event_id` only.
- Queue overflow drops oldest, increments `queue_overflow`, retains newest;
  capacity fill tests tolerate concurrent overflow alerts.
- Alerts remain `{reason, counters}` only; regressions assert chat text/sender
  never appear in alert JSON.
- Import/normalize path opens no sockets; write-mode `open` refused during
  normalize; fixtures scanned for URL/cookie/token substrings.
- Bool-as-int for `start_ms`/`end_ms` rejected; transcript window capped at
  30_000 ms; non-NFC text rejected.

### Commands and results

| Exact command | Result | Date/tree |
| --- | --- | --- |
| `make events-check` | Exit 0; 23 passed; pending-gates banner printed | 2026-11-15 / `issue/10-event-normalization-impl` |
| `make protocol-check` | Exit 0; `protocol generated artifacts: ok` | 2026-11-15 |
| `git diff --check` | Exit 0; no whitespace errors | 2026-11-15 |
| `make verify` | Exit 0; Ruff/mypy/TypeScript ok; `933 passed, 1 deselected`; protocol 262 + Railway 63 + web 51 Vitest; artifact/protocol checks and build ok | 2026-11-15 |
| `git diff origin/main -- packages/protocol` | Empty (byte-for-byte unchanged) | 2026-11-15 |

### Unresolved wire/live gates (not claimed done)

- Live chat adapter / `BILI-ACQ-001` selection and rights
- Viewer protocol minor / closed `TimelineEventV1` danmaku/SC wire payloads
- Timeline/WS publication and Issue #29 display
- Issue #16 raw archive enablement
- Real upstream schema compatibility (fixtures remain synthetic)
