# Implementation plan: Event normalization

## Order of work

1. **This PR (docs only):** Owner-merge intent/spec/plan with the first slice locked as
   **internal / offline / normalize-only**. No protocol edits, codegen, live sockets,
   #29 UI, or #16 archive. Viewer `protocol_minor = 1` remains **deferred**—docs merge
   does not select it.
2. After merge, open a **separate** `issue/10-...` implementation PR for the first slice
   only. Record implementer notes in evidence before runtime code.
3. Implement the closed fixture → normalized-record engine, dedup map, bounded queue,
   sensitive-field refusal, and payload-free alerts exactly as spec’d. Add desensitized
   synthetic fixtures labeled as non-live schemas.
4. Add `make events-check` (or equivalent) that runs fixture tests and prints that live
   chat, wire publish, protocol extension, and raw archive remain pending. Skipped real
   gates are failures, not passes.
5. **Do not** modify `packages/protocol`, Timeline publishers, viewer WS, or web UI.
6. **Deferred follow-ons** (each needs its own owner-accepted artifact when ready):
   protocol minor / closed `TimelineEventV1` danmaku/SC branches + goldens/BC; wire
   publisher filtered by negotiated minor; #29 display; #16 archive; live adapter under
   #7 channel/rights.

## Verification

**Artifact PR (this batch):**

- `make artifacts`
- `git diff --check`
- `make verify`
- Local Markdown link check for `docs/changes/10-event-normalization/**`
- Changed-path inspection: exactly four Issue #10 Markdown files

**First implementation PR (future):**

- `make events-check` — fixture/contract only
- `make protocol-check` must still pass with **unchanged** protocol artifacts
- `make verify`, `git diff --check`
- No untrusted live danmaku CI

## Rollout and rollback

First slice has no production surface. On failure clear in-memory maps/queues; keep all
live/wire/archive flags off. Rollback removes the internal module without touching
protocol or #11.

## Open decisions

None that block **documentation** merge of the internal-first sequencing. Remaining
**owner-only** items (not chosen by this PR):

1. Whether/when to authorize a viewer protocol minor and closed wire danmaku/SC
   payloads (deferred; needs separate protocol artifact).
2. Final public projection field list for #29 after wire exists.
3. Issue #16 timing for durable sanitized-raw retention.
4. Exact live upstream message schemas once `BILI-ACQ-001` is selected (#7)—fixtures
   stay synthetic until then.

Recommendation: merge this artifact to unlock the internal normalize implementation;
keep protocol extension and live/archive/UI as explicit later decisions.
