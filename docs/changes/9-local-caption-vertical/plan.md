# Implementation plan: Local caption vertical

## Order of work

1. Reconcile current Issue text when available, obtain owner artifact merge, and record
   independent implementer/reviewer exposure before code. #5 coordinator completion
   is not a prerequisite for writing or reviewing this proposal.
2. Implement the closed mode/start configuration and evidence gates, with production
   and actual execution off. Add metadata-only `fixture_timeline` and protocol/status
   reducers first. A blocked `synthetic_mlx` request must not silently start fixtures.
3. Add the fixed loopback viewer route, same-origin restrictions, current status
   mapping, 20-domain bound, independent fan-out queues and explicit fresh-resync path.
   Test ordering and saturation with synthetic text only, without model/worker audio.
4. Once #6/#8 implementations and their relevant accepted contracts are ready, connect
   one bounded segment handle to the existing binary sender and one local worker.
   Validate the complete ownership inventory, terminal/overlap compatibility, deadlines
   and output metadata before any authorized audio test. Do not amend old protocol
   fixtures or use a provider double as actual inference proof.
5. Connect trusted start/stop/disable/delete to atomic admission closure, publication
   suppression, existing lease cancellation and #8 cleanup. Test every race with source
   retry, worker loss, final arrival and viewer backpressure; invalidation precedes await.
6. Add stage observations, per-clock interval calculation and reports that explicitly
   mark missing partial and cross-clock values. Test counts/percentiles with metadata
   cases. Separate fixture traffic and measured audio paths in output and evidence.
7. Integrate #11's accepted page using `/api/viewer/ws` and the exact reason mapping.
   Run 20 fast/slow fixture clients for 60 seconds; test fresh/current cursor outcomes,
   drop/close, final-only labels and clear-on-terminal at maximum presentation delay.
8. Only with separate execution authorization, approved producer/host/decoder/provider,
   actual #5 report/model ADR and final manifest, run the short synthetic-speech MLX
   demonstration. Record exact commands/revisions, actual timing/quality/cleanup results
   and missing evidence; no downloads or runs are authorized by this artifact PR.

## Verification

For these documents: `make artifacts`, `git diff --check`, staged whitespace/changed
path inspection and local Markdown link check; exact results go in [evidence](evidence.md).
Do not run unrelated full runtime/model/hardware tests for this proposal.

Future implementation adds `make local-vertical-check` and runs `make protocol-check`,
`make verify` and `git diff --check`. Include exact v1 boundary/no-state-change results,
queue bytes/counts and send deadlines, simultaneous cancellation, clean-EOF last final,
source-retry refusal, no-worker start timeout, disconnected-domain expiry and capacity.
New target names here are planned, not evidence of existing commands or passing tests.

Authorized audio checks additionally prove each #8 ownership/persistence/host requirement,
actual approved speech-to-final text and cleanup. Store no PCM/encoded/audio-derived
fixture or dump. A skipped/blocked model or host check remains a failed acceptance gate,
not a passing vertical. Trusted hardware tests are manual and never untrusted CI jobs.

## Rollout and rollback

Local only, with fixture mode and actual inference clearly selected and gated.
Production resources, public listeners, account/device controls and source policies
stay unchanged. Rollback closes endpoints and admission, cancels/clears the local
session and starts no replacement. There is no persisted audio/transcript recovery.

## Open decisions

Endpoints, mode split, local limits, status mapping, reconnect behavior and short-session
scope are fixed proposals. Current remote Issue reconciliation, owner acceptance,
terminal/overlap compatibility and exact source/model/host evidence remain explicit
integration/run gates. Missing evidence never permits a fallback implementation or an
unapproved change to `epoch`, `seq`, `revision`, PTS or the accepted audio interfaces.
