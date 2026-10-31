# Implementation plan: Local MLX worker

## Order of work

1. Reconcile the current Issue body once available and obtain owner merge of these
   artifacts. Register a fresh independent implementation author/reviewer before code.
2. Add the closed local configuration, evidence/manifest checks and text-only `check`
   path. Missing evidence fails closed; no loader, execution registry or download path
   becomes enabled merely because contracts can run.
3. Implement one-owner state/sequence handling using the accepted protocol. Author
   synthetic metadata cases for negotiation, lease lifetime, duplicate/conflict/gap,
   cancellation and output suppression before connecting any real provider.
4. Complete independent end-of-segment/overlap interpretation review. Prove terminal
   acceptance, actual resource clearing and all old golden outcomes with a bounded
   provider double. A conflict blocks inference and requires its owning decision;
   do not patch protocol meaning or treat metadata counters as cleared RAM.
5. Implement reservation-before-allocation, bounded segment assembly, output sequencing,
   heartbeat responsiveness, final-only transcript construction and idempotent teardown.
   Hold provider completions across expiry/cancel/disconnect/restart in metadata tests;
   prove atomic precommit revalidation and actual release before any terminal ack, with
   no old-generation sequence/PTS mutation or reopening.
   Test with in-process generated synthetic samples only when host audio preflight is
   authorized; text-only tests remain separate and cannot claim these runs passed.
6. Integrate only the independently authored and reviewed #5 MLX provider, approved final
   manifest, actual report/model ADR and trusted host evidence. Prove all CPU/device
   audio allocations, paging/crash exclusions and bounded cancellation. Missing evidence
   leaves `run` blocked. This artifact authorizes none of these downloads or executions.
7. With separate run authorization, record a trusted manual synthetic speech test from
   #9, exact invocation/revisions, outputs and timings, reservation peaks, terminal
   cleanup and negative sink tests. Do not substitute sine waves or scripted text for
   evidence of speech recognition. Keep CUDA and community deployment closed.

## Verification

Artifact batch: `make artifacts`, `git diff --check`, `git diff --cached --check`,
changed-path inspection and local Markdown link checks, with exact results in
[evidence](evidence.md). No unrelated full runtime suite or model/audio run is required
for this documentation-only proposal.

Future implementation adds `make worker-check` and runs `make protocol-check`,
`make verify` and `git diff --check`. The new worker target must report text-only,
synthetic-audio and manually gated MLX outcomes separately; skipped gates are not passes.
Trusted audio checks cover 6-second/960,000-byte/16,777,216-byte boundaries, every copy,
terminal-before-clear races, no write attempts, host paging/crash guarantees and
provider cancellation deadlines. No untrusted self-hosted hardware CI is added.

## Rollout and rollback

Local manual operation only after approval/evidence gates. On failure close admission,
cancel the lease, clear audio, close the connection and keep execution disabled.
Rollback restores the last reviewed worker/configuration without relaxing protocol or
resource limits. There is no audio recovery or automatic replacement model.

## Open decisions

CLI scope, final-only behavior, resource/cancellation limits and no-resume policy are
fixed proposals. Exact #5 model approval, supported host evidence and independent
terminal/overlap compatibility are named blockers before inference integration. The
current remote Issue text and artifact approval are also pending; no implementer is
authorized to resolve these gaps by weakening accepted constraints.
