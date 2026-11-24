# Intent: Worker gateway, heartbeat, and lease state machine

## Issue and owner

- GitHub Issue: [#14](https://github.com/Shuang-su/Livecho/issues/14)
- Human owner: @Shuang-su
- Stage/area/risk: `stage:m2`, `area:backend`, `type:feature`, `risk:high`

## Problem

An external worker still has no long-lived connection that is limited to the
versioned `livecho.worker.v1` subprotocol and guarded by authentication, a
5-second heartbeat, a 20-second lease, disconnect and expiry handling, and
epoch isolation. The closed Issue #3 contract defines the messages and the
ordering rules. The merged Issue #13 contract defines device proof, Hello
admission, and contribution updates. Neither contract mounts the worker
gateway. A process-local viewer socket from Issue #9 is not that gateway.

## Desired outcome

### This documentation merge

Lock the implementation contract for a later, separate pull request:

1. A worker opens an outbound WebSocket to `/api/worker/ws` and negotiates
   exactly `livecho.worker.v1`. Hello is admitted only by the existing #13
   `admit_hello` decision. A `LeaseV1` is sent only after that admission
   succeeds.
2. The lease lasts exactly 20 seconds. The worker heartbeat period is 5
   seconds. A heartbeat does not move `expires_at`. At `expires_at` the lease
   expires, and a later heartbeat, resume, or output is an expired renewal:
   it is rejected and does not change contribution counts.
3. The process holds at most one active audio lease, and a session holds at
   most one. A second connection does not receive a second lease. A valid
   resume of the same unexpired lease replaces the socket and keeps that
   lease.
4. JSON control frames and binary PCM frames keep the accepted size ceilings,
   and this contract adds hard per-connection rates. Inbound PCM is not
   retained. Outbound PCM is synthetic, in memory, and cleared on every
   terminal path.
5. Output whose epoch is not the active lease epoch is rejected and stays
   rejected. Disconnect, duplicate connections, expired renewal, out-of-order
   output, and process restart have state-machine tests. Restart drops leases
   and contribution memory together.
6. Backend messages are the existing closed models only. They have no shell,
   container, code, or arbitrary URL field.

Merging these documents does not mount the gateway on the public listener,
enroll a worker, enable production auth or mail, provision a secret, accept
live audio, or turn on production traffic.

### Explicitly deferred

- Choosing a best worker, ranking devices, and automatic failover. Those
  belong to Issue #15. This contract's decision, which #27 leaves to #14, is
  that `lease_replaced` and any successor lease for a session that already
  held one are not legal here.
- Durable contribution storage, database migrations, and restoring leases
  after a real host reboot. Issue #13's merged store is process memory, and
  Issues #4, #16, and #19 own a later durable store.
- Real ASR, live Bilibili ingest, community-worker real PCM, and CUDA
  inference. CUDA stays mock/contract-only.
- Protocol field or message-shape changes. Those belong to #27, #28, or a
  separate protocol issue. This contract uses the models already on `main`.
- The open-contribution loop, public leaderboard, and self-service enrollment
  discussed as research in Issue #31. The owner comment on #14 (2026-09-26,
  [comment](https://github.com/Shuang-su/Livecho/issues/14#issuecomment-5847331711))
  does not adopt that proposal.
- Wiring this gateway into the Issue #9 local vertical or the Issue #6 MLX
  runtime.

## Non-goals

- Selecting the best worker, scoring devices, or failing a session over to a
  different device.
- Issuing a second lease for a `session_id` that already held a lease in this
  process, including through `Minor1Session.replace_lease`.
- Implementing CUDA inference or inserting a CUDA manifest.
- Adding or renaming protocol fields, error codes, subprotocol strings, or
  binary-header layout. `epoch`, `seq`, and `revision` keep their accepted
  meanings.
- Reusing another project's message structure or adding a general-purpose
  control channel.
- Persisting PCM, writing audio fixtures, or sending real PCM to a community
  worker.
- Enabling `LIVECHO_EMAIL_ENABLED`, reading or writing `RESEND_API_KEY` or
  `LIVECHO_SESSION_SIGNING_KEY`, adding `db/migrations/`, or opening
  production traffic.
- A new enrollment scheme. Workers authenticate only through the merged #13
  challenge and Hello admission.
- Publishing viewer timeline events, selecting a Bilibili room, or accepting
  platform credentials on this socket.
- Points, cash, a public leaderboard, or counting a reconnect as task success.

## Constraints and data impact

- Depend on the contracts already at `cae5ccd951e1c761163d372dc83558c016ee96d5`.
  Issue #3 is closed. Issue #13's implementation is on `main` through PR #61
  even though that GitHub issue stays open. Issue #27's protocol
  implementation is on `main` through PR #58 even though that GitHub issue
  stays open. This contract must not wait for either open issue to be closed,
  and it must not replace either contract.
- Honor `CTRL-WORKER-PROTOCOL`, `CTRL-WORKER-REVOCATION`,
  `CTRL-WORKER-SYNTHETIC-ONLY`, `CTRL-AUDIO-RAM-ONLY`, and
  `CTRL-AUDIT-PAYLOAD-FREE` as already written.
- Data classification: ephemeral audio for PCM that exists only inside an
  active synthetic lease budget, plus identity metadata already stored by the
  #13 memory adapter (device id, public key, aggregate statistics). No PCM,
  transcript body, enrollment token, private key, cookie, or playback locator
  is written to disk, logs, or a new store.
- Alpha scope stays one operator-selected public free room, invite-only
  Apple Silicon/MLX workers, an anonymous public live page, synthetic audio
  for community workers, CUDA mock/contract-only, and production traffic off.
  `audio_origin` stays `synthetic`.
- The four states in the owner comment stay distinct: a healthy
  connection/heartbeat, a device that passed the applicable checks, a valid
  task lease, and an accepted result. Reconnect, restart, expired renewal,
  revocation, and result resend must leave those states and the contribution
  counters consistent with each other. Connection recovery is not task
  success and does not apply a contribution twice.
- App-facing product copy is zh-Hans-CN. These artifacts stay in the English
  used by the accepted change documents. This issue adds no screen copy.

## Success signal

A reviewer can trace each Issue #14 acceptance checkbox to a spec rule and a
later test. The diff of this pull request contains the four files in this
directory and no application, protocol, worker, CI, Railway, environment, or
migration file. The later implementation can show one active 20-second lease,
a 5-second heartbeat that does not extend it, permanent rejection of an old
epoch and of an expired renewal, and unchanged contribution counters across
reconnect and resend.

## Human decision

- Status: Proposed; documentation only. Gateway code is forbidden until the
  repository owner merges this directory's `intent.md`, `spec.md`, and
  `plan.md`.
- Approved by/date: Pending @Shuang-su review and merge.
- Production auth, live ingest, real ASR, community-worker real PCM, CUDA, and
  production traffic: not enabled here.
- Issue #31 research proposals: not adopted.
- Successor leases and automatic failover: not legal in this issue.
