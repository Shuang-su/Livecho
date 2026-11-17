# Specification: Long-session state lifecycle and resynchronization

This specification implements owning [Issue #27](https://github.com/Shuang-su/Livecho/issues/27)
on top of the accepted [protocol v1 contract](../3-protocol-v1-contract/spec.md).
Normative **must** and **must not** apply to the implementation PR that follows an
owner merge of this directory. #3 remains the authority for minor 0. This document
does not weaken a minor-0 rule.

## Behavior

### Version and negotiation

Major stays 1. Subprotocol strings stay `livecho.worker.v1` and `livecho.viewer.v1`.
Accepted minors become `[0, 1]`. Minimum worker and viewer versions stay `0.1.0`.

Handshake selection is the highest minor present in both the peer's `supported_minors`
and `[0, 1]`. An empty intersection is `unsupported_minor`. The selected minor is
written to `WorkerWelcomeV1.selected_minor` or `ViewerReadyV1.selected_minor` and is
the only minor that connection may send afterward.

| Offer | Worker capabilities | Selected minor |
| --- | --- | --- |
| `[0]` | exactly `asr.transcribe` and `protocol.binary-pcm` | 0 |
| `[0]` | any other set | `capability_required` |
| `[0, 1]` | exactly the two minor-0 capabilities | 0 |
| `[0, 1]` | exactly those two plus `protocol.epoch-rotation` | 1 |
| `[1]` | exactly the three capabilities above | 1 |
| `[1]` | any other set | `capability_required` |
| anything else that does not intersect `[0, 1]` | any | `unsupported_minor` |

Viewer negotiation uses the same minor intersection and has no capability list.
`WorkerHelloV1` and `ViewerSubscribeV1` are the only pre-selection envelopes. They
keep `protocol_minor: 0` and offer minor 1 through `supported_minors`. A hello or
subscribe whose `protocol_minor` is not 0 is rejected before selection.

After selection, the connection decodes and emits only the closed schema for that
minor. A minor-0 connection that then receives `protocol_minor: 1`, a minor-1-only
type, or capability `protocol.epoch-rotation` is `unsupported_minor` or
`capability_required` as applicable, with no state change. A minor-1 connection
that then receives `protocol_minor: 0` is `unsupported_minor`, including a lease,
transcript, timeline event, ack, or error built from a minor-0 class. Negotiation
is not an in-session downgrade. An established minor-1 session that loses the
capability match is closed; it is not rewritten to minor 0.

Existing minor-0 golden inputs keep their accept/reject codes. Advertising an extra
minor that the peer also supports may select 1 only under the table above. No current
accepted fixture sends that offer.

### Constants

| Name | Value | Applies |
| --- | --- | --- |
| `REVISION_DOMAIN_CAPACITY` | 4,096 identities | every active revision domain; no eviction inside the domain |
| `SEQUENCE_WINDOW_CAPACITY` | 256 | unchanged JSON and PCM windows |
| `ROTATION_TOMBSTONE_CAPACITY` | 8 per session | minor 1 only |
| `CANCELLATION_TOMBSTONE_CAPACITY` | 64 process-wide, 120 seconds | unchanged |
| Lease lifetime | `(0, 120]` seconds | unchanged; rotation does not extend it |
| Epoch arithmetic | start at 1; next is current + 1; no wrap | `epoch_exhausted` at `2^64 - 1` |

Logical ceilings, not process RSS, are the memory acceptance measure. An active
revision record stays the #3 136-byte logical record. A rotation tombstone stores
only integers and one reason literal: closed epoch, the exclusive next input,
output, and viewer sequences, `media_continue_ms`, `pcm_continue_pts`, and reason.
It stores no transcript text, segment id, PCM sample, content digest, credential,
or locator. Eight tombstones plus one active domain of at most 4,096 revision
records and two 256-record JSON windows is the per-session ceiling. PCM windows
store no records and no payload-derived bytes.

### Minor 0 retain rule

On minor 0 the #3 revision machine is unchanged:

- Identities 1 through 4,096 of a new domain are eligible at revision 1.
- An existing identity at size 4,096 still accepts a legal current-plus-one update
  and a duplicate no-op, and still rejects conflicts, stale revisions, gaps,
  immutable-field changes, and mutations of a final.
- A new identity at size 4,096 returns `revision_capacity_exceeded` and does not
  consume sequence or change object state.
- The implementation must not rotate the epoch, clear the domain, reset `seq` or
  `revision`, or emit `epoch_rotated`, `ViewerResyncV1`, or `EpochRotatedV1`.

#9 short sessions stay on minor 0. Ending a minor-0 session that can no longer
admit identities is a later consumer action through the existing cancellation and
session-teardown rules. This issue's state machine does not add an automatic
session-status side effect on minor 0.

### Minor 1 session machine

One session has one current epoch, one optional active lease, and these domains,
all bound to that epoch: worker PCM input window, worker output JSON window plus
revision domain, and viewer JSON window plus revision domain. Revision identity
remains `(message type, session_id, lease_id or zero UUID, epoch, object ID)`.

The machine also stores two session scalars, initially 0:

- `media_continue_ms`: maximum `end_ms` among accepted **final** transcripts in
  this session. A non-final does not advance it.
- `pcm_continue_pts`: end PTS of the last accepted PCM frame in this session,
  computed as `pts_ms + (sample_count * 1000 // 16000)`.

A different `session_id` is a different machine. It starts at epoch 1 with both
scalars at 0. Media time does not cross sessions. After a session is torn down,
messages for it are `binding_mismatch` and do not reopen the old epoch.

### Epoch transition

Only the backend may commit a transition. A worker or viewer field that asks for
rotation is `unknown_field` or `schema_invalid` and changes nothing.

Two triggers share one commit:

1. `revision_capacity`. A candidate whose revision preview would be
   `revision_capacity_exceeded` for a **new** identity. Updates, duplicates,
   conflicts, and other non-capacity decisions do not trigger it.
2. `lease_replaced`. An explicit backend request to issue a non-resumed lease
   for the same session. #14 and #15 decide when that request is legal. This
   spec defines the protocol effect only.

Commit is atomic. On failure, including `epoch_exhausted`, the candidate is not
applied, no sequence is consumed, no tombstone is written, and the current epoch
stays. On success:

1. Write a tombstone for the closing epoch from the pre-commit counters. If the
   session already holds 8 tombstones, drop the oldest first. A dropped epoch
   later yields `epoch_unknown`, not a replay.
2. Drop that epoch's revision maps and sequence records. Do not zero those
   counters while keeping the same identities. The tombstone freezes the
   exclusive next sequences.
3. Set the current epoch to `closed_epoch + 1`. Open empty domains. Do not copy
   revision records, partials, or message bodies forward.
4. If a lease was active, close it. The wire signal is `EpochRotatedV1`, not a
   new `LeaseCancelV1` reason. The minor-0 cancel reason enum stays closed.
   The existing cancellation tombstone may record the closure with reason
   `epoch_rotated` and still must not store transcript text or audio.
5. Return `epoch_rotated` for a capacity trigger (`retryable: true`, `expected`
   the opened epoch, `received` the closed epoch). Do not echo the candidate
   body. A `lease_replaced` trigger emits `EpochRotatedV1` without pretending
   the replacement was a rejected transcript.

`EpochRotatedV1` is backend to worker, type `worker.epoch_rotated`,
`protocol_minor: 1`. Fields are exactly: envelope, `session_id`, `lease_id` of
the closed lease or the zero UUID when no lease was active, `closed_epoch`,
`opened_epoch`, `media_continue_ms`, `pcm_continue_pts`, and `reason`
(`revision_capacity` or `lease_replaced`). It does not consume the worker output
sequence and carries no transcript.

The replacement `LeaseV1` is a new `lease_id`, `epoch` equal to `opened_epoch`,
lease `revision` `"1"`, `input_start_seq` `"1"`, `output_start_seq` `"1"`, the
same `session_id`, and `audio_origin: "synthetic"`. Lifetime stays inside
`(0, 120]` seconds. A lease for any other epoch, or with a start sequence other
than 1 immediately after this transition, is `epoch_unknown` or `schema_invalid`
and is not installed. `audio_origin` gains no new literal.

The triggering object is not rewritten onto the new epoch. The worker may send a
new `message_id` on the new lease. Reusing a `segment_id` is a new revision-1
identity because identity includes epoch. It does not mutate the retired object.
A replay that still carries the closed epoch is `epoch_stale` while the tombstone
exists, and `epoch_unknown` after that tombstone is evicted. Either result leaves
the active domain unchanged.

### Media time

Within one session, transcript time and PCM PTS survive epoch transitions.

- An accepted final sets `media_continue_ms` to `max(media_continue_ms, end_ms)`.
- The next transcript, on any later epoch of that session, must have
  `start_ms >= media_continue_ms`. A smaller `start_ms` is
  `media_time_regressed`, retryable false, with no state change.
- `start_ms > media_continue_ms` is a gap. The protocol must not insert filler
  text.
- PCM on a minor-1 lease uses header minor byte 1. Header minor 0 on that lease
  is `binary_header_invalid`. Minor 0 still requires header minor byte 0.
- The next accepted frame's `pts_ms` must be `>= pcm_continue_pts`. A lower value
  is `audio_pts_invalid`. The scalar advances only after acceptance. Tests pass
  header integers only. They must not allocate a retained payload, write payload
  bytes, or hash them.
- Non-final captions abandoned by a transition do not move `media_continue_ms`.
  Their later arrival on the closed epoch is `epoch_stale` and is not displayed
  as a final of the new epoch.

A new session does not inherit either scalar. Clients must clear captions on a
session change and on an epoch transition. Those two events are different:
session change resets media time; epoch transition continues it and reports a gap.

### Viewer cursors

Minor 0 cursor results stay on `ViewerReadyV1` and `ProtocolErrorV1` code
`resync_required`. Minor 0 must not send `ViewerResyncV1`.

Minor 1 uses one message, `ViewerResyncV1`, type `viewer.resync`,
`protocol_minor: 1`. Fields are exactly: envelope, `session_id`, `room_id`,
`epoch` (the epoch to use now), `next_seq`, `media_continue_ms`, `reason`
(`epoch_rotated`, `cursor_expired`, or `cursor_unknown`), and `gap: true`.
The message contains no transcript, partial, or event body. It does not consume
a timeline sequence.

| Cursor | Result |
| --- | --- |
| Same session, current epoch, `next_seq` equal to the live expected sequence | `ViewerReadyV1` with resume succeeded. No `ViewerResyncV1`. No gap. No body replay. |
| Same session, current epoch, any other `next_seq` | `ViewerResyncV1` reason `cursor_expired`, `next_seq` at the live expected sequence, `gap: true`. |
| Same session, epoch present in a rotation tombstone | `ViewerResyncV1` reason `epoch_rotated`, current epoch and its expected sequence, `gap: true`. Data messages on that closed epoch are `epoch_stale`. |
| Same session, any other epoch | `ViewerResyncV1` reason `cursor_unknown`, current cursor, `gap: true`. Data messages are `epoch_unknown`. |
| Different session | `binding_mismatch`. Do not attach the caller to the other session. |

On a successful transition every connected minor-1 viewer is sent
`ViewerResyncV1` with reason `epoch_rotated`, the opened epoch, `next_seq` `"1"`,
and the session `media_continue_ms`. The client clears provisional text and must
not treat the new sequence as a retransmission of retired events. An exact later
resume still does not announce a gap.

Inside the active epoch, duplicate finals stay `revision_duplicate` or
`object_final` under the #3 precedence. Old-epoch output, duplicate and
conflicting messages, and out-of-order messages cannot commit into the current
domain. Sequence precedence remains: transport and binding and epoch, then the
sequence window, then revision. A sequence rejection does not evaluate revision
and does not rotate.

### Stable codes

Add these codes only to the minor-1 `ProtocolErrorV1` schema. The minor-0 error
schema keeps the #3 code list and must reject these three. Minor-0 machines must
not emit them. They are legal on minor 1:

| Code | Retryable | When |
| --- | --- | --- |
| `epoch_rotated` | true | capacity trigger rejected the candidate and committed a new epoch |
| `epoch_exhausted` | false | the current epoch is `2^64 - 1`, so no successor exists |
| `media_time_regressed` | false | transcript `start_ms` is below the session floor |

`resync_required`, `epoch_stale`, `epoch_unknown`, `revision_capacity_exceeded`,
`object_final`, and `audio_pts_invalid` keep their #3 meanings.

## Interfaces and compatibility

### Schema deltas

Minor-0 envelope classes keep `protocol_minor: Literal[0]`. Do not widen that
literal. Minor 1 is a second closed schema for each post-selection message:
the same fields, bounds, and validators, with `protocol_minor: Literal[1]`.
The decoder for a connection uses only the schema of the minor it selected.
The replacement lease, ordinary transcripts, timeline events, acknowledgements,
and errors on a minor-1 connection are those twins, not the minor-0 classes.

Pre-selection requests stay on the minor-0 classes:

| Request | Rule |
| --- | --- |
| `WorkerHelloV1` | `protocol_minor: 0`. Capability literal gains `protocol.epoch-rotation` so an offer can be parsed. The offer table still requires an exact set. Nested `WorkerResumeV1` is unchanged. |
| `ViewerSubscribeV1` | `protocol_minor: 0`. No new field. `supported_minors` carries the offer. Nested `ViewerCursorV1` is unchanged. |

Post-selection twins, one minor-0 class and one minor-1 class each:

| Message | Minor-1 difference from the minor-0 class |
| --- | --- |
| `WorkerWelcomeV1` | `protocol_minor: 1`, `selected_minor: 1`, `accepted_capabilities` exactly the original two plus `protocol.epoch-rotation` |
| `ViewerReadyV1` | `protocol_minor: 1`, `selected_minor: 1` |
| `LeaseV1` | `protocol_minor: 1`. `audio_origin` stays `synthetic`. The post-rotation lease uses this twin. |
| `LeaseCancelV1` | `protocol_minor: 1`. `reason` enum is identical to minor 0. |
| `HeartbeatV1`, `WorkerStatsV1`, `TranscriptSegmentV1` | `protocol_minor: 1`. Field rules otherwise identical. |
| `TimelineEventV1` | `protocol_minor: 1`. Payload branches stay transcript and session status. Rotation is not a payload and must not be stuffed into transcript text or `reason_code`. |
| `ProtocolAckV1` | `protocol_minor: 1`. Outcome enum unchanged. |
| `ProtocolErrorV1` | `protocol_minor: 1`. Code enum is the #3 list plus `epoch_rotated`, `epoch_exhausted`, and `media_time_regressed`. |

Minor 1 only, with no minor-0 class:

| Message | Rule |
| --- | --- |
| `EpochRotatedV1`, `ViewerResyncV1` | `protocol_minor: 1`, fields as specified above, no extra fields |

The minor-0 welcome still has `selected_minor: 0` and exactly the original two
capabilities. The minor-0 error schema does not list the three new codes.
Nested payload, manifest, and audio-format objects stay shared; they do not
carry `protocol_minor`.

Generation stays single-source from the Pydantic models through the existing
generator. The generator must emit both closed schemas. Hand-edited schema or
TypeScript is not allowed. `make protocol-check` must pass. Every pre-existing
golden case keeps its decision and stable code. New cases use ids prefixed
`long-session-` and live in the existing accepted and rejected corpora and
manifest. One new accepted case must show a minor-1 `LeaseV1`, transcript,
timeline event, ack, and error. One new rejected case must show each of those
payloads with `protocol_minor: 0` on a connection that selected 1.

### Compatibility matrix

| Surface | Major | Accepted minors | Minimum client |
| --- | --- | --- | --- |
| Worker | 1 | 0, 1 | `0.1.0` |
| Viewer | 1 | 0, 1 | `0.1.0` |

A minor-0 peer never receives minor-1 messages. After selection, a minor-1 peer
that sends a minor-0 envelope is rejected. The hello and subscribe that offered
minor 1 remain `protocol_minor: 0`. Rollback removes minor 1 from the matrix together
with the new models, codes, schema, types, and fixtures. Sessions that were on
minor 1 fail closed with `unsupported_minor` after rollback. Rollback must not
revive a retired epoch or reset a minor-0 counter.

### Consumers

#15 must use this transition for same-session failover and must not clear an
active domain or reuse an epoch to survive the 4,096 ceiling. A peer that
negotiated only minor 0 stops on `revision_capacity_exceeded` through existing
cancellation. #19 may claim long-session operation only by citing the
implementation evidence of this issue. This implementation PR must not edit
those issues, the #30 index, `services/backend`, `apps/web`, or worker runtimes.

### Package ownership

Implementation is confined to `packages/protocol/**` and `tests/protocol/**`,
plus this issue's `evidence.md`. The focused test module is
`tests/protocol/test_long_session.py`. TypeScript coverage goes through the
existing protocol package tests and golden runner.

## Failure modes and disable path

- Malformed minor-1 messages follow #3 transport rejection and change nothing.
- `epoch_exhausted` leaves the full domain in place. The candidate is not
  admitted. The backend must stop admitting new identities; it must not wrap.
- A crashed commit must not leave a tombstone without a new epoch, or a new
  epoch without having dropped the old maps. Implementations should stage the
  successor and publish it with one assignment.
- Disable minor 1 by negotiating only minor 0. Minor 0 endpoints and the #9
  fixture path stay available.
- No production listener, lease issuer, or audio source is enabled by merging
  or implementing this issue.

## Security, privacy, and data lifecycle

- Backend authority alone chooses epochs, leases, and cursors. Worker text and
  viewer cursors stay untrusted.
- Tombstones and cancellation records stay in process memory. They are not
  written to Postgres, Bucket, logs, or fixtures.
- Diagnostics may include the stable code, minor, epoch integers, and sequence
  integers. They must not include transcript text, the rejected payload, PCM
  bytes, or a digest computed from those bodies.
- Synthetic golden text, when a transcript model requires text, is a fixed
  public placeholder. Binary cases stay metadata-only, matching #3.
- Hostile workers can still keep PCM they already received. This issue adds no
  disclosure and does not accept that residual risk. Real community PCM remains
  closed under the existing #2 gates.

## Acceptance criteria

- [ ] Minor 0 goldens and the 4,096 / 4,097 capacity cases keep today's codes,
      and minor 0 never emits the new messages or rotates.
- [ ] Minor 1 accepts identities 4,095 and 4,096, rejects the new 4,097th
      identity with `epoch_rotated` without storing it, and repeats that
      crossing on three successive epochs. Active revision records after each
      commit equal only the new epoch's later admissions. Tombstones stay ≤ 8.
- [ ] An existing-identity update or duplicate at size 4,096 does not rotate.
      A duplicate final stays idempotent. A final cannot be revised. Closed-epoch
      and out-of-order messages leave the active domain unchanged.
- [ ] Exact cursors resume without a gap claim. Expired cursors, tombstoned
      epochs, and unknown epochs resync with `gap: true` and no body replay.
- [ ] Transcript and PCM time continue across an epoch and reset across a
      session. Regression is `media_time_regressed` or `audio_pts_invalid`.
      A gap does not create filler text.
- [ ] A minor-1 connection accepts `LeaseV1`, transcript, timeline, ack, and
      error twins with `protocol_minor: 1`, and rejects those payloads when
      `protocol_minor` is 0. Minor-0 schemas still reject `protocol_minor: 1`.
- [ ] `epoch_exhausted` does not wrap. Header minor bytes follow the negotiated
      minor. `audio_origin` and `LeaseCancelV1.reason` are unchanged.
- [ ] Schema, TypeScript, and fixtures are generated or corpus-checked from the
      Python source. Python and TypeScript agree on every new and old case.
- [ ] The diff does not touch backend services, the web app, workers, ingest,
      or audio fixtures. Evidence lists commands, identity counts, and logical
      ceilings, and records that #15 and #19 are consumers rather than edited
      here.
