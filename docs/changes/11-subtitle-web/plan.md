# Implementation plan: Subtitle companion Web/PWA

## Order of work

1. Obtain owner merge of this artifact, reread the current remote Issue,
   and record a fresh independent implementation assignment. Before backend
   integration, require accepted #9 endpoint and public-reason contracts; fixture-only
   UI work may proceed after this artifact is accepted without model, worker, audio,
   platform or trusted-host execution approval. Keep those execution paths disabled.
2. Create `apps/web/` with the repository's pinned React/TypeScript/Vite toolchain and
   types. Refactor only the shared protocol package's environment adapters/schema
   packaging to expose the browser-safe entry defined in the spec; preserve the Node
   API, one validation implementation and all existing golden outcomes. Add focused
   browser/Node parity and bundle checks, plus unit/E2E scripts and
   `make web-check`; retain Node 22/pnpm 11 and existing workspace conventions.
3. Implement the pure connection/protocol reducer first. Test integer-safe identities,
   sequence/revision precedence, full-capacity existing updates/duplicates versus new
   identity rejection, exact cursor resume, fresh resync and terminal clearing
   using independently authored synthetic text/metadata, with no audio fixture.
4. Implement the bounded presentation scheduler with a controlled monotonic test clock.
   Separate receive/protocol state from due display mutations; verify delay changes,
   queue byte/count boundaries, partial coalescing and immediate visibility precedence.
5. Build the responsive room/status/subtitle view and accessible delay control. Add
   plain-text adversarial rendering and longest-text checks, mobile/desktop images,
   keyboard, zoom and live-announcement tests using synthetic content only.
6. Add the static shell manifest and narrowly allowlisted service worker. Intercept
   every browser persistence surface in tests; prove offline reload never restores
   timeline text or cursor, and denied cache/storage writes fail before retention.
7. Integrate #9's accepted text-only `fixture_timeline` mode at `/api/viewer/ws`
   and test 20 clients, fast/slow
   isolation, retry exhaustion, stop/disable/delete at maximum delay, socket closure,
   old epoch callbacks and fresh resync. No public account or device registration gate
   is introduced. #7 and #27 remain separate capability boundaries.
8. Record exact commits, commands, test counts, queue peaks, fixture rates, browser
   versions, screenshots and gap outcomes. Independently review protocol/privacy and
   visual behavior before asking the owner to accept the implementation.

## Verification

This documentation batch runs `git diff --check`, `make artifacts`, staged-path
inspection and local Markdown-link validation. It does not run unrelated runtime,
model/audio, deployment or full-suite tests. Exact outcomes belong in [evidence](evidence.md).

Future implementation must add and run `make web-check`,
`pnpm --filter @livecho/web test`, `pnpm --filter @livecho/web test:e2e`,
`make protocol-check`, `make verify` and `git diff --check`. Those new web targets do
not exist yet and are not claimed as executed. E2E uses local synthetic timeline
fixtures from accepted contracts, never platform content or a downloaded model.

The 20-client run records accepted seq/revision outcomes, per-client queue peak,
overflow/resync counts and client-observed receive-to-render times. It proves UI and
fan-out behavior only. MLX/decoder/source/host latency is pending separate trusted
acceptance; no absolute worker-to-browser latency is inferred from unrelated clocks.

## Rollout and rollback

Run the static shell and backend locally only after their own implementation gates.
Keep production ingest, source publication and execution registries unchanged. Failure
closes the viewer and clears its memory; disable the web route for rollback. No database
migration, content export or retained transcript restoration is needed.

## Open decisions

The view, delay range, queue limits, reconnect budget and retention behavior are fixed
proposals for owner review. Agreement with #9's accepted endpoint/reason mapping is an
integration gate, not implementer discretion to invent wire fields. Remote Issue
freshness, owner merge, runtime tests, model adoption and host evidence remain separate
acceptance records: model/host evidence does not block fixture-only UI implementation
or synthetic validation. Actual ASR partial/MLX acceptance stays incomplete until
separately demonstrated. A protocol conflict requires its own accepted protocol Issue.
