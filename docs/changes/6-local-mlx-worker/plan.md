# Implementation plan: Local MLX worker

## Order of work

1. **This PR (docs only):** Owner-merge intent/spec/plan. No `workers/mlx/` product code
   in the artifact PR. Closed draft #40 remains historical prior art only.
2. After merge, open a **separate** `issue/6-...` implementation PR. Register a fresh
   independent implementer/reviewer assignment in that PR's evidence before runtime code.
3. Implement closed local configuration and `enroll` / `doctor` / `benchmark` entry points
   with empty execution registry. Missing #5 ADR/report or #8 host evidence fails closed;
   no loader or download becomes enabled because contracts can run.
4. Implement one-owner state/sequence handling on accepted protocol doubles. Author
   synthetic metadata cases for negotiation, lease lifetime, duplicate/conflict/gap,
   cancellation, and **fixture partial→final** output suppression/acceptance before any
   real provider.
5. Complete independent end-of-segment/overlap interpretation review against #3/#8/#9.
   Prove terminal acceptance, actual resource clearing (not counter-only), and unchanged
   goldens with a bounded provider double. Conflicts block inference and need their
   owning decision—do not patch protocol meaning.
6. Implement reservation-before-allocation, bounded segment assembly, heartbeat
   responsiveness, transcript construction (fixture partial/final; real final-only until
   proven), and idempotent teardown. Hold provider completions across
   expiry/cancel/disconnect/restart in metadata tests; prove atomic precommit revalidation
   and actual release before terminal ack.
7. Integrate only the independently authored #5 MLX provider, approved final manifest,
   actual report/model ADR, and trusted host evidence. Prove CPU/device audio allocations,
   paging/crash exclusions, and bounded cancellation. Missing evidence leaves `run`
   blocked. This artifact authorizes none of those downloads or executions.
8. With separate run authorization on a trusted Apple Silicon host, record exact
   invocations, revisions, timings, reservation peaks, terminal cleanup, and negative
   sink tests. Do not substitute sine waves or scripted fixture text for speech-recognition
   evidence. Keep CUDA, community deployment, and public enrollment closed.

## Verification

**Artifact PR (this batch):**

- `make artifacts`
- `git diff --check`
- `make verify`
- Local Markdown link check for `docs/changes/6-local-mlx-worker/**`
- Changed-path inspection: exactly four Issue #6 Markdown files

**Future implementation PR:**

- `make worker-check` — fixture/contract only; must print that real MLX/host acceptance
  remains pending; skipped real gates are failures, not passes
- `make protocol-check`, `make verify`, `git diff --check`
- Trusted-host matrix (manual): Apple Silicon doctor; approved manifest digest; synthetic
  lease only; 6 s / 960,000 / 16,777,216 bounds; cancel/expiry races; no write attempts;
  paging/crash evidence cross-check with #8
- No untrusted self-hosted hardware CI

## Rollout and rollback

Local manual operation only after approval/evidence gates. On failure close admission,
cancel the lease, clear audio, close the connection, and keep execution disabled.
Rollback restores the last reviewed worker/configuration without relaxing protocol or
resource limits. No audio recovery or automatic replacement model.

## Open decisions

None that block **documentation** merge of the Issue-aligned CLI and partial/final truth
table above. The following remain **implementation blockers** (not silent implementer
choices):

1. Exact #5 model-decision ADR identity and complete final inference manifest digests.
2. #8 approved FFmpeg/host inventories clearing `audio_budget_unverified`.
3. Whether/when a real MLX adapter earns partial-capable status (default: final-only +
   `partial_unavailable` until measured).
4. Separate local execution-registry enablement for real `run` (default closed).

Recommendation for the owner: merge this artifact as the Issue-aligned contract; keep
real partials and model selection as evidence-gated follow-ons rather than reopening the
#40 `check`/`preflight` rename.
