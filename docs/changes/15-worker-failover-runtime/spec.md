# Specification: Synthetic minor-1 scheduling integration

## Eligibility and ownership

- One backend event-loop owner serializes the source/session, worker lease
  transitions, viewer publication and teardown. Gate the scheduling path on
  the accepted #14 upgrade proof and Hello. Recheck live device/account
  status and allowed manifests before issuing a lease or accepting results.
- One primary and at most two standbys. A standby can prepare the approved
  model but receives PCM only after promotion under its own active lease.
  Filter out inactive, incompatible, unverified, or already stale workers.
- Rank eligible workers by server-confirmed warm readiness, measured capacity
  against the fixed model, benchmark/observed real-time factor, recent accepted
  result reliability, and canonical device id as a final tie-break. Worker
  declarations are hints until supported by server observations. In the
  synthetic test environment, injected observations are labelled; they do not
  qualify a real model or a community device for live audio.

## Same-session transition

Use the `Minor1SessionRuntime` protocol owner. The initial and successor
leases use the accepted minor-1 twin. A same-lease reconnect can resume only
under #14's proof and exact resume rules, while a same-session non-resumed
lease calls the #27 `lease_replaced` transition. A capacity rejection consumes
no candidate sequence and uses the runtime's `revision_capacity` transition.

1. Under the session owner, fence the outgoing lease against source admission,
   stop its PCM producer, and drop pending old-epoch sends. On the protocol
   transition, the runtime releases old lease accounting, freezes cursor
   metadata and publishes the successor epoch. There is no await inside the
   protocol commit.
2. After commit, use the emitted `EpochRotatedV1` for the old minor-1 worker
   when still reachable and enqueue `ViewerResyncV1` ahead of new timeline
   events for every minor-1 viewer. Neither notice contains body replay.
   Clear old browser text, pending display delay and transient partials before
   accepting the first event in the new epoch. Close a blocked connection
   under its normal bounds rather than delay other viewers. Late old-epoch
   frames cannot enter the successor ordering state or contribution counters.
3. Only then install the selected worker's new `LeaseV1Minor1` with a new
   lease id, the same session, the opened epoch and both start sequences at 1.
   When no compatible standby is ready, keep the session without an active
   PCM lease and surface the gap. Retry selection from fresh eligibility.

The first synthetic failover slice resumes from the live source position.
It discards expired audio and does not transfer PCM from the outgoing lease.
If later measurements justify carrying still-valid context, define that
extension under the accepted #8 RAM/byte and #27 PTS constraints before
changing this choice. Maintain media continuity and report dropped duration.

For an exact eligible viewer cursor, emit the selected-minor Ready at the live
next sequence without a gap. For an expired, tombstoned or unknown cursor,
use the runtime's resync reason and current cursor. Never attach a cursor
from another session. Minor-0 viewers and workers must never receive the
minor-1 notices. A minor-0 session follows its existing cancellation path
at capacity.

## Lease lifetime and acceptance

The #14 initial lease lasts 20 seconds. Keep its expiry immutable. A
successor uses the #27 new-lease transition rather than extending an old
lease. Before claiming sustained operation, accept the normal healthy-lease
handoff policy and measure its viewer gap cost. A failure-recovery test does
not prove satisfactory steady-state handoff.

- Exercise a real loopback synthetic chain with three connections, a slow
  viewer, a valid resumable cursor and a cursor outside the retained boundary.
- Inject primary disconnect/expiry, no backup, all slow, cold model and
  repeated failures. Latest valid heartbeat to first accepted successor final
  is at most 60 seconds in the qualified failover case. Record each stage,
  dropped duration and recovery lag. No standby gets pre-promotion PCM.
- Exercise both revision domains at 4,095, 4,096, 4,097 and multiple rotations.
  Check one active lease, no replay bodies, original minor-0 decisions, stale
  and evicted epoch outcomes, idempotent final acceptance, and immediate
  clearing on terminal changes.
- Log metadata and counts only. No stored PCM, caption contents, private
  credentials or proof headers enter diagnostics or evidence.
