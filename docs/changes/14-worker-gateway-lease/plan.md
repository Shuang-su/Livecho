# Implementation plan: Worker gateway, heartbeat, and lease state machine

## Order of work

1. **This pull request is documentation only.** Merge `intent.md`, `spec.md`,
   and `plan.md` before any gateway code. The diff is the four files in
   `docs/changes/14-worker-gateway-lease/`. Do not complete Issue #14 in this
   pull request. Do not edit protocol, worker, backend, web, CI, Railway,
   `.env.example`, or `db/migrations/` here.
2. After owner merge, open a separate implementation branch from that `main`
   commit. The branch name must match `issue/14-` plus a lowercase kebab slug,
   as this branch `issue/14-worker-gateway-lease` does, so the artifact check
   can read issue 14. Append a fresh implementer exposure record to
   `evidence.md` before editing Python. The requirements-author record in this
   file is not that record.
3. Add `WorkerIdentityService.device_usable` as a read of the existing memory
   adapter and account lookup. Test unknown, revoked, and inactive-account
   devices. Do not change `admit_hello`, enrollment routes, or statistic
   formulas.
4. Add `livecho_backend.worker_gateway` and `create_worker_gateway_app` with
   the `/api/worker/ws` route, injectable clock, and injectable ids. Do not
   register that route on `create_local_vertical_app` or
   `create_worker_identity_app`. Assert both existing apps still lack it.
5. Implement upgrade checks, Hello through `admit_hello`, Welcome, and
   `arm_grant` lease issuance through `LeaseRuntimeCoordinator.create`. Use a
   20-second `expires_at`. Do not call `Minor1Session.replace_lease` and do
   not construct `EpochRotatedV1`.
6. Implement `expire_due`, heartbeat health, resume through
   `decide_worker_resume`, disconnect PCM release, duplicate-connection
   refusal, revocation cancel, and `restart()` against a new identity
   service. Call `record_stats`, `record_health`, and `note_online` only in
   the cases the spec table allows.
7. Enforce the size and rate table, including `submit_synthetic_pcm`. Generate
   any PCM bytes inside the test process and release them. Do not add an
   audio fixture.
8. Keep `LIVECHO_EMAIL_ENABLED=false` and `LIVECHO_PERSISTENCE_ENABLED=false`.
   Do not read `RESEND_API_KEY` or `LIVECHO_SESSION_SIGNING_KEY`. Do not add a
   secret name or a migration.
9. Confirm `git diff` does not touch `packages/protocol/`, `workers/mlx/`,
   `apps/web/`, CI workflows, Railway config, `.env.example`, or
   `db/migrations/`. Append implementation commands to this issue's
   `evidence.md` only. Do not rewrite the merged intent, spec, or plan.
10. Open one implementation pull request for #14 only after that evidence is
    recorded. Per `CONTRIBUTING.md`, that later pull request is the one that
    completes the issue. #15 and #18 stay in their own changes.

## Verification

**This artifact pull request:**

- `LIVECHO_HEAD_REF=issue/14-worker-gateway-lease uv run python tools/check_change_artifacts.py`
- `LIVECHO_HEAD_REF=issue/14-worker-gateway-lease make artifacts`
- `git diff --check`
- Local Markdown link check for the four new files
- `git diff --name-only origin/main` lists only those four files
- `make verify` from this branch, because `CONTRIBUTING.md` uses that entry
  point for the deterministic check and this change is documentation only

**Later implementation pull request:**

- `uv run pytest -q tests/worker_gateway`
- A test that Hello before a successful #13 verify sends neither Welcome nor
  Lease, and that a header `livecho-device-id` different from `worker_id`
  sends no lease
- A test that `expires_at - issued_at` is exactly 20 seconds, that
  `heartbeat_healthy` is false at 5 seconds without a heartbeat, and that
  `lease_valid` is still true at that instant
- A test that a heartbeat at or after `expires_at` returns `lease_expired`,
  leaves `record_stats` aggregates unchanged, and is rejected again on resend
- A test that a second authenticated device receives no lease while the first
  lease remains, and that a matching `decide_worker_resume` keeps the same
  `lease_id` and epoch without a second `record_stats` call
- A test that disconnect drops buffered PCM to zero, closes one online
  interval, and does not set `result_accepted`
- A test that `seq` ahead of the next expected value returns `seq_gap` and
  does not call `record_stats`
- A test that `restart()` rejects the previous lease id against a new identity
  service whose statistics are empty, and that the test directory gained no
  audio file
- A test that a lower epoch is `epoch_stale` on first use and on resend
- A test that the 11th inbound text frame in one timestamp window and a text
  frame of 65,537 bytes close the socket, and that the third inbound binary
  frame is not retained
- A test that `submit_synthetic_pcm` refuses the 51st frame or the frame that
  would pass 32,000 payload bytes in the rolling second
- A test that constructing each outbound model with an extra `shell`,
  `container`, `code`, `url`, or `uri` field raises, and that the gateway
  module does not reference `EpochRotatedV1`
- A test that `create_local_vertical_app` still serves `/health` and
  `/api/viewer/ws` and does not mount `/api/worker/ws`
- `make verify`
- `git diff --check`
- A scan of the diff for `RESEND_API_KEY=` values, session-key values, audio
  fixtures, `db/migrations/`, and edits under `packages/protocol/` or
  `workers/mlx/`

Skipped live ingest, real ASR, CUDA, Resend, Railway provisioning, and
production-auth checks stay recorded as not run. They are not passes.

## Rollout and rollback

No flag, secret, or deployment changes in either pull request. The gateway
application stays unmounted by the local viewer app, the worker-identity app,
and Railway start commands. Public live viewing stays anonymous.
Community-worker audio stays synthetic. Rollback of the implementation reverts
the gateway package, `device_usable`, and the new tests. Rollback of this
documentation pull request deletes the four new Markdown files and leaves
runtime behavior unchanged.

A later owner who stores leases or contribution counters in Postgres must
replace the Issue #4 no-schema guard in that same change and must satisfy the
existing restore rules. That store is not authorized here. `restart()` in this
contract drops both together and restores neither.

## Open decisions

None. Any unresolved product or interface decision blocks implementation.

## Fixed bounds

The issue body requires a 5-second heartbeat, a 20-second non-renewal expiry,
one active lease, hard frame size and rate limits, the named state-machine
cases, and server messages without shell, container, code, or arbitrary URL
fields. It does not state every rate or the resume and restart mechanics.
The following values are this spec's contract. Owner merge of this directory
accepts them.

| Bound | Value | Why this value |
| --- | --- | --- |
| Lease lifetime | 20 seconds exactly | The issue's non-renewal expiry. It is inside the accepted `(0, 120]` lease window. `expires_at` stays immutable. |
| Heartbeat lateness | 5 seconds | The issue's heartbeat period. Lateness clears `heartbeat_healthy` only. |
| First Hello deadline | 5 seconds | The same period, applied to a socket that has not yet sent Hello. |
| Session successor lease | not issued | #27 asks #14 when `lease_replaced` is legal. Non-goals exclude failover and indefinite renewal, so it is not legal here. |
| Inbound text rate | 10 frames per rolling second | Above the 0.2 Hz heartbeat, still a hard flood cap. Size stays 65,536 from #3. |
| Inbound binary rate | 2 frames per rolling second | The worker does not upload PCM. Two frames is enough to observe the cap; the body is not retained. Size stays 32,056 from #3. |
| Outbound PCM rate | 50 frames and 32,000 payload bytes per rolling second | Canonical realtime rate of 16 kHz s16le mono. Budgets stay 960,000 and 16,777,216 from #2 and #3. |
| Outbound control rate | 10 frames per rolling second | Matches the inbound text cap. |
| Active leases | one per process, and one per `session_id` for the life of the process | The issue's single active lease plus the alpha one-lease audio rule. |
| Start sequences | `"0"` on minor 0, `"1"` on minor 1 | The accepted golden lease shapes already on `main`. |
| Wire `retryable` | true only for `resync_required` and `epoch_rotated` | `epoch_rotated` is already specified as retryable. This gateway does not emit it. |
| Device header | `livecho-device-id` | The #13 requirement that the gateway, not the Hello body alone, supply `device_id`. |

A different lifetime, a successor-lease policy, a new protocol field, a
persistent PCM path, or an Issue #31 enrollment or leaderboard change
requires a new owner-merged artifact before code that depends on it.
