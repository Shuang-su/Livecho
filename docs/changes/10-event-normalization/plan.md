# Implementation plan: Event normalization (danmaku / SC / status)

## Order of work

1. **This PR (docs only):** Owner-merge intent/spec/plan. No protocol model edits, no
   live sockets, no raw archive enablement, no #29 UI.
2. After merge, open a **separate** `issue/10-...` implementation PR (or a stacked
   protocol-minor PR if the owner wants models first). Record implementer notes in
   evidence before runtime code.
3. Lock closed Pydantic models for danmaku/SC payloads + TimelineEventV1 union update
   under the owner-accepted minor. Run codegen; add shared goldens for accept/reject
   and stable error codes with Python/TS parity.
4. Document negotiation: minor 0 clients never receive danmaku/SC; publisher filters by
   selected minor. Prove epoch/seq/revision semantics unchanged via existing goldens.
5. Implement in-memory normalize/dedup engine against **desensitized fixtures** only:
   duplicates, reorder, unknown fields, malicious text, sensitive-field strip/reject,
   unparseable → alert.
6. Keep feature flag default off. Do not call live Bilibili. Do not open #16 persistence
   paths or invent rights rows.
7. Leave #29 display and public statistics to their owning Issues. If wire publication
   waits on minor selection, keep normalize unit-tested behind an internal API until
   goldens land.

## Verification

**Artifact PR (this batch):**

- `make artifacts`
- `git diff --check`
- `make verify`
- Local Markdown link check for `docs/changes/10-event-normalization/**`
- Changed-path inspection: exactly four Issue #10 Markdown files

**Future implementation PR:**

- Protocol goldens + `make protocol-check` after model changes
- Dedicated fixture normalize check (e.g. `make events-check`) printing that live
  chat/raw archive remain pending; skipped real gates are failures
- `make verify`
- No untrusted live danmaku CI

## Rollout and rollback

Feature flag off by default. On failure disable the adapter flag, clear ephemeral
queues, and keep raw archive OFF. Rollback restores last reviewed models/flag without
relaxing allowlists. Protocol minor rollback keeps minor 0-only publication.

## Open decisions

None that block **documentation** merge of the closed-payload + privacy contract. These
remain **implementation blockers** (not silent choices):

1. Exact viewer `protocol_minor` for danmaku/SC wire publication (recommendation:
   minor 1; alternate: internal-only normalize until a later protocol Issue).
2. Final allowlisted field names/bounds for danmaku/SC public projection (locked in
   goldens at implementation time).
3. Issue #16 timing for any durable sanitized-raw retention.
4. Issue #31 statistics semantics beyond the distinguishability note above.

Recommendation for the owner: merge this artifact so implementation can add models +
fixture normalize without waiting on #29 UI or #16 archive; keep live chat and raw
persistence closed.
