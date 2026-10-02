# Implementation plan: M3 Ultra MLX benchmark

## Order of work

1. Owner reviews and merges this documentation-only artifact. Before implementation,
   record a fresh implementer exposure/assignment and isolated reviewer under the
   independent-implementation policy. Start a separate Issue #5 implementation PR.
2. Implement the closed manifest, report, timing, metric, and decision contracts with
   synthetic text/metadata tests. Unknown fields, missing cells, nonfinite measurements,
   zero denominators, and incomplete/failed runs must not produce qualification.
3. Pin/review the MLX and acquisition dependencies; implement the independent local
   provider adapter, conversion map, model-only cache, progress and bounded resumption.
   Test preparation against metadata-only transfer doubles. No CI model/audio download.
4. Implement bounded in-memory acquisition/preprocessing and synchronous ownership
   accounting. Prove negative paths before running real audio: stalls, cancellations,
   overflow, dump/cache attempt, provider failure, and repeated teardown.
5. Implement instrumented cold/warm runner, partial/overlap scoring, complete reports,
   exact machine inventory allowlist, and tests at all threshold boundaries. Keep
   public/runtime routes and worker protocol untouched.
6. Obtain exact source/model/converter/mirror approval and protected-host no-paging/no-
   dump evidence. Freeze the corpus/settings before scoring. Missing evidence records
   `blocked_evidence`; do not fabricate values or substitute a community checkpoint.
7. On the reviewed commit, manually prepare models, preflight, and run the full matrix
   on the trusted M3 Ultra. Retain only approved text/metadata and metrics. Record exact
   commands, versions, pass/fail counts, invalidated runs, and no-persistence evidence.
8. Write the measured model-decision ADR with the fixed rule; obtain owner approval
   before any consumer adopts a manifest. Both-model failure keeps the vertical blocked.

## Verification

Artifact phase: `git diff --check`, `make artifacts`, and `make verify`; inspect the
changed-path list for exactly this Issue's four Markdown files. Record actual commands
and outcomes in `evidence.md`.

Implementation phase: `make bootstrap`, `make asr-benchmark-check`, `make verify`,
`git diff --check`. Manually record the exact reviewed-manifest arguments to
`uv run python -m tools.asr_benchmark prepare-models`, `preflight`, and `run`.
Those commands do not exist in the artifact phase and are not claimed as executed.

Exercise every decision branch and threshold equality/just-outside case, text metric
goldens, missing partial behavior, cold/warm separation, model mirror mismatch, and
nonfinite data. Scan temp/log/cache/fixture/output paths and database/storage doubles;
observe attempted writes as well as residual files. Test all audio ownership releases.
Hardware results must include all windows/strata/repetitions, not selected averages.

## Rollout and rollback

No deployment, feature enablement, protocol change, or migration. The harness remains
manual and local. Revoke a manifest on provenance/privacy failure and invalidate its
dependent decision; do not automatically switch models or retain audio for diagnosis.
Consumers remain blocked until the replacement report and ADR are owner-approved.

## Open decisions

None delegated to implementation: candidates, formats, corpus shape, metrics, thresholds,
selection, and failures are fixed here for owner review. Exact asset hashes, source
rights, compatible independent adapter evidence, trusted-host guarantees, measurements,
and final model ADR are named evidence/approval gates; all are currently pending.
