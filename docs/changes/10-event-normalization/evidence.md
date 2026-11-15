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
