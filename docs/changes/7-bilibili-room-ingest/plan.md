# Implementation plan: Bilibili public room ingest

## Order of work

1. **This PR (docs only):** Owner-merge intent/spec/plan. No adapter product code, no
   live sockets, no fixture corpus that embeds secrets. Closed historical drafts (if
   any) remain prior art only.
2. After merge, open a **separate** `issue/7-...` implementation PR. Register a fresh
   independent implementer/reviewer note in that PR’s evidence before runtime code.
3. Implement closed registries (acquisition channel empty, rights empty, production
   ingest off) and operator-only start/stop authorization hooks consistent with Issue
   #2 actors. Missing channel/rights/kill-switch clearance fails closed.
4. Implement canonical room-id resolution and eligibility refusal against **synthetic**
   metadata fixtures (offline, live-free, login-required, paywalled, geo/DRM-like,
   rate-limited, schema-invalid). No live Bilibili calls in CI.
5. Implement the OFFLINE→STARTING→LIVE→STALLED→RECONNECTING→ENDED owner-serialized
   state machine with exponential backoff, attempt/time ceilings, payload-free status
   events, and mandatory locator clearing on reconnect/stop/disable/denylist.
6. Wire kill-switch and denylist stop paths so disable does not depend on the ingest
   network path; prove new starts and reconnects are rejected under disable.
7. Define SSRF allowlist validation against synthetic URLs; reject private, file, and
   off-allowlist redirects. Keep redaction helpers for diagnostics.
8. Audio: **do not** open an encoded path until an owner-accepted #8 extension names
   codecs, budgets, and compatibility tests. Keep handoff blocked with
   `audio_budget_unverified` / encoded-admission missing. Never pass playback URLs into
   #8. Do not loosen #8 registries.
9. Only after channel (`BILI-ACQ-001`), rights, safety enablement, and #8 admission
   evidence exist on a trusted host, record exact manual probe commands separately—
   never as a substitute for fixture greens, never in untrusted CI.

## Verification

**Artifact PR (this batch):**

- `make artifacts`
- `git diff --check`
- `make verify`
- Local Markdown link check for `docs/changes/7-bilibili-room-ingest/**`
- Changed-path inspection: exactly four Issue #7 Markdown files

**Future implementation PR:**

- `make ingest-check` — fixture/contract only; must print that real network/channel/
  rights/audio acceptance remains pending; skipped real gates are failures
- `make verify`, `git diff --check`
- Trusted-host matrix (manual, owner-gated): selected channel only; free anonymous
  room; kill switch/denylist; locator non-persistence; #8 budget clearance; no worker
  locator leakage
- No untrusted self-hosted live ingest CI

## Rollout and rollback

Production remains off (`BILI-DEC-001`). On failure close the attempt, clear locators
and audio, keep global ingest disabled unless an audited admin re-enable with owner
preconditions has already landed (out of this Issue’s enablement scope). Rollback
restores the last reviewed adapter/config without relaxing eligibility, SSRF, or
persistence rules.

## Open decisions

None that block **documentation** merge of the Issue-aligned anonymous free path and
#8 handoff boundary. The following remain **implementation / production blockers**
(not silent implementer choices):

1. Exact official acquisition channel identity, host allowlist, and rate-limit document
   (`BILI-ACQ-001` today: unselected).
2. Per-room rights evidence for acquire/transform (and later worker/publish) rows.
3. Whether encoded media admission into #8 is a follow-on artifact after channel
   selection, or folded into the first #7 implementation PR once channel evidence
   exists. **Recommendation:** keep the first implementation PR fixture/metadata/state
   only; open a follow-on artifact for encoded→#8 admission after the channel is
   selected, so #8’s raw-PCM invariant is not weakened under pressure.
4. Production global enablement and #28 worker PCM disclosure remain separately owned.

Recommendation for the owner: merge this artifact as the Issue-aligned contract; keep
live sockets and encoded audio blocked until channel/rights/#8 admission evidence is
explicit.
