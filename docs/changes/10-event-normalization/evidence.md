# Evidence: Event normalization artifacts

## Artifact approval

- Artifact PR: Pending (this documentation draft)
- Approved by/date: Pending @Shuang-su review and merge
- Base: `main` at `d3dae9f9472df274aba6bf3151b9b513b8a63456` (includes squash-merged #7
  fixture ingest). Owning Issue #10 reread 2026-11-15.
- Branch: `issue/10-event-normalization`

## Prior art (not approval)

No merged `docs/changes/10-*` tree existed on `main` at documentation start. Accepted
Issue #3 states v1.0 timeline payloads are transcript + session-status only; danmaku/SC
fields were explicitly deferred. Issue #10 owner comment (2026-09-26) and Issue #31 are
governance context for dedup/statistics—not authorization to ship live chat, raw
archive, or silent protocol maps. Closed drafts elsewhere are not copied blindly.

## Scope reconciliation

| Topic | Issue #10 | Accepted deps | This artifact |
| --- | --- | --- | --- |
| Wire shape | Closed normalized danmaku/SC on timeline | #3: no arbitrary objects; v1.0 lacks danmaku/SC | Explicit protocol extension (recommend minor 1); defer if owner chooses internal-only |
| Four events | danmaku, SC, status, transcript | Transcript/status exist | Add danmaku/SC contracts; keep status/transcript |
| Raw archive | Strip secrets; #16 for durable | #2/#16 gates | No implicit DB/Bucket ON |
| UI | Not this Issue | #11 caption/status; #29 danmaku UI | Out of scope |
| Live chat | Feature flag; fixtures | #7 channel/rights OFF | Fixture-only CI |

## Requirements-author exposure and provenance

- Author: Cursor Auto (cloud agent), 2026-11-15.
- Livecho inputs: AGENTS.md, CONTRIBUTING.md, Issue #10 (+ owner comment), Issue #3
  protocol models/spec, Issue #2 data classes, Issue #7/#11 boundaries, Issue #31
  dedup/statistics notes as context only.
- No live Bilibili chat, account signup, media/model download, paid API, user-machine
  access, or fabricated protocol/rights approval was performed.

## Automated verification

| Exact command | Result | Date/tree |
| --- | --- | --- |
| `make artifacts` | Exit 0; `change artifacts: ok` | 2026-11-15 / docs worktree on `d3dae9f` |
| `git diff --check` | Exit 0; no whitespace errors | 2026-11-15 |
| `make verify` | Exit 0; Ruff/mypy/TypeScript ok; `910 passed, 1 deselected`; protocol 262 + Railway 63 + web 51 Vitest; artifact/protocol checks and build ok | 2026-11-15 |
| Local Markdown link check | 5 relative/absolute refs inspected; 0 broken | 2026-11-15 |
| `git diff --cached --name-only` | Exactly four files under `docs/changes/10-event-normalization/` | 2026-11-15 |

## Manual or hardware evidence

None. No live chat capture or raw archive enablement is claimed.

## Review findings (critical review before return)

- **Representability:** Honest deferral—danmaku/SC cannot ride minor 0 without a
  protocol Issue; recommended minor 1 rather than fake delivery via transcript `text`.
- **Privacy:** Raw vs normalized separation; secrets/audio rejected; ordinary APIs
  allowlist-only; unparseable → payload-free alerts.
- **Dedup:** Source-event vs worker-result domains called out per owner #31 note.
- **Owner ambiguity (recommendation):** Merge docs now; choose minor 1 (or internal
  normalize-only) explicitly at implementation; keep #16/#29/#7 live gates closed.

## Deviations

Uses branch `issue/10-event-normalization`. Directory slug matches area. No product
code, protocol edit, or production enablement.

## Release and rollback evidence

Not deployed. No live chat, protocol minor bump, or raw archive gate is enabled.
