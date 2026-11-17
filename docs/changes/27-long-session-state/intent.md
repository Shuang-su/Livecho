# Intent: Long-session state lifecycle and resynchronization

## Issue and owner

- GitHub Issue: [#27](https://github.com/Shuang-su/Livecho/issues/27)
- Human owner: @Shuang-su
- Stage/area/risk: `stage:m2`, `area:protocol`, `type:feature`, `risk:high`

## Problem

Accepted protocol v1 keeps at most 4,096 revision identities in an active domain and
does not evict them. A new identity at that ceiling returns `revision_capacity_exceeded`
and leaves sequence and object state unchanged. That rule is the correct short-session
bound. It does not define a legal long-session continuation, how media time survives an
epoch change, or how a client tells a real gap from a replay. A short fixture run cannot
stand in for that contract. Resetting `seq` or `revision` inside the active domain, or
reusing an epoch, would hide the ceiling instead of defining it.

## Desired outcome

### This documentation merge

Lock one implementation contract for a later, separate pull request:

1. Minor 0 behavior, fixtures, and generated minor-0 results stay as accepted in #3.
   At 4,096 identities the active domain retains them. A new identity is
   `revision_capacity_exceeded`. Nothing rotates, clears, or renumbers that domain.
2. Minor 1, negotiated explicitly, adds backend-authored epoch rotation when a new
   identity would exceed 4,096, and the same continuity rules when the backend issues
   a non-resumed replacement lease. The closed epoch is retired to a bounded tombstone.
   The new epoch is `closed_epoch + 1`. New sequence domains start at the new lease's
   start sequences. Old counters are frozen, not zeroed in place.
3. Transcript `start_ms` / `end_ms` and PCM PTS continue across epochs of the same
   session. A new `session_id` starts a new media timeline. Clients observe an explicit
   gap and receive no replayed bodies for retired epochs or expired cursors.
4. Python and TypeScript accept and reject the same synthetic cases, including
   identities 4,095, 4,096, and 4,097 and three accelerated crossings, with a logical
   memory ceiling. No audio bytes are stored.

### Explicitly deferred

- Wiring rotation into the #9 local vertical, #6 worker runtime, #11 PWA, #14 gateway,
  or #15 scheduler. Those consumers must import this contract only after their own
  accepted artifacts. #9 stays on minor 0.
- Real audio origin, live ingest, danmaku/SC publication, CUDA, accounts, and
  persistence. #28 owns any non-synthetic `audio_origin`.
- Editing the #30 index or the GitHub text of #15 and #19 in the implementation PR.
  Those issues consume this contract in their own later changes.

Merging these documents authorizes that protocol implementation. It does not enable a
long-running production session, a real lease, or a new audio path.

## Non-goals

- Clearing the active revision map, resetting its `seq` or `revision`, or reusing its
  epoch in order to admit identity 4,097.
- Audio persistence, history replay storage, multi-room fan-out, or a distributed store.
- Describing the 256-sequence window or the 8 rotation tombstones as a lossless replay
  guarantee.
- A new protocol major, a new WebSocket subprotocol string, or a change to minor 0
  field meanings.
- Lease lifetimes above the accepted 120-second maximum, or indefinite lease renewal.

## Constraints and data impact

- Honor accepted #2 boundaries and the #3 version policy. `epoch`, `seq`, and
  `revision` change only inside the new minor, with old-client behavior and a rollback
  boundary stated in the spec.
- Workers remain hostile-capable. Rotation is a backend decision. A worker or viewer
  message cannot request it.
- Data classification: in-memory synthetic protocol metadata and scalar PTS/media
  cursors. No PCM payload, transcript body, digest of transcript text, credential, or
  locator in tombstones, logs, or fixtures.
- #15 failover and #19 Alpha acceptance are future consumers. They must not invent a
  second rotation rule.

## Success signal

After the later implementation PR: minor-0 goldens keep their codes; minor-1 tests
cross the 4,096 ceiling three times without growing past the logical ceilings; a
regressed media time is rejected; a resumed exact cursor does not announce a gap; a
stale cursor and a retired epoch do, without body replay. This documentation merge
succeeds when the spec, plan, and evidence contain those rules and no product code.

## Human decision

- Status: Proposed; documentation only. Implementation is forbidden until the
  repository owner merges this directory's `intent.md`, `spec.md`, and `plan.md`.
- Approved by/date: Pending @Shuang-su review and merge.
- Production long-session operation, real audio, and provider deployment: not decided
  here.
