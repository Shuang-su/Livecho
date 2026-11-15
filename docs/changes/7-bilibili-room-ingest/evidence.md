# Evidence: Bilibili public room ingest artifacts

## Artifact approval

- Artifact PR: Pending (this documentation draft)
- Approved by/date: Pending @Shuang-su review and merge
- Base: `main` at `19907996d5cf9cd499155842ce0ce44ca63e3191` (includes squash-merged #6
  Linux-safe worker). Owning Issue #7 reread 2026-11-15.
- Branch: `issue/7-bilibili-room-ingest`

## Prior art (not approval)

No merged `docs/changes/7-*` tree existed on `main` at documentation start. Repository
search found no accepted Issue #7 implementation PR. Issue #7 owner comment
(2026-09-26) and Issue #31 are **governance context only**—not a selected cookie
channel and not authorization to implement credentialed fallback. Accepted Issue #2
policy `docs/policy/bilibili-public-ingest.md` (`BILI-DEC-001` OFF, `BILI-ACQ-001`
unselected) remains binding. Closed drafts elsewhere, if any, are not copied blindly.

## Scope reconciliation (Issue vs dependencies)

| Topic | Issue #7 / owner comment | Accepted deps | This artifact |
| --- | --- | --- | --- |
| Access model | Operator-selected free anonymous; no bypass | #2 public eligibility; policy OFF | Same; cookie fallback deferred to #31 |
| State machine | OFFLINE→STARTING→LIVE→STALLED→RECONNECTING→ENDED | #2 kill switch/denylist | Issue states + #2 stop semantics |
| Audio | Use #8 controlled interface; local #8/#9 need not wait | #8 forbids playback-URL handoff; budget gate | Fixture/metadata first; encoded→#8 needs follow-on admission |
| Live CI | Desensitized fixtures; stop if rights unclear | Policy: no production acquisition | No live sockets in artifact or default CI path |
| Worker PCM | Needs #28 + rights; adapter ≠ enablement | #2 worker disclosure High residual | Explicitly out of grant |

## Requirements-author exposure and provenance

- Author: Cursor Auto (cloud agent), 2026-11-15.
- Livecho inputs: AGENTS.md, CONTRIBUTING.md, owning Issue #7 (+ owner comment),
  change templates and artifact checker, accepted Issue #2/#3/#8/#9 intent/spec,
  `docs/policy/bilibili-public-ingest.md`, Issue #8 handoff prose forbidding playback
  URL injection into the current raw-PCM interface.
- No live Bilibili fetch, account signup/change, media/model download, paid API use,
  user-machine access, or fabricated rights/channel approval was performed for this
  documentation batch.

## Automated verification

| Exact command | Result | Date/tree |
| --- | --- | --- |
| `make artifacts` | Exit 0; `change artifacts: ok` | 2026-11-15 / docs worktree on `1990799` |
| `git diff --check` | Exit 0; no whitespace errors | 2026-11-15 |
| `make verify` | Exit 0; Ruff/mypy/TypeScript ok; `892 passed, 1 deselected`; protocol 262 + Railway 63 + web 51 Vitest; artifact/protocol checks and build ok | 2026-11-15 |
| Local Markdown link check | 5 relative/absolute refs inspected; 0 broken; `docs/policy/bilibili-public-ingest.md` present | 2026-11-15 |
| `git diff --cached --name-only` | Exactly four files under `docs/changes/7-bilibili-room-ingest/` | 2026-11-15 |

## Manual or hardware evidence

None. No live room probe, playback URL acquisition, or audio decode is claimed.

## Review findings (critical review before return)

- **Anonymous-only:** Issue comment forbids cookie fallback on anonymous failure—
  retained; #31 stays separate.
- **#8 boundary:** Spec refuses playback-URL handoff and requires a follow-on encoded
  admission rather than weakening `audio_budget_unverified`.
- **Production OFF:** Does not invent `BILI-ACQ-001` selection or rights rows.
- **Owner ambiguity (recommendation):** Prefer fixture/state implementation first;
  select the official acquisition channel and #8 encoded-admission in explicit later
  artifacts rather than bundling unproven network media into the first code PR.

## Deviations

Uses branch `issue/7-bilibili-room-ingest` (repository-accepted `issue/<n>-<slug>` form).
Directory slug `7-bilibili-room-ingest` matches Issue area. No product code, protocol
edit, or production enablement.

## Release and rollback evidence

Not deployed. No production ingest, channel, or worker disclosure gate is enabled.
