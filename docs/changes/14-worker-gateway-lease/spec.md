# Specification: Worker gateway, heartbeat, and lease state machine

Normative terms **must**, **must not**, and **may** apply to the later Issue #14
implementation. This document does not enable that implementation.

Accepted contracts this spec uses without rewriting:

- `livecho.worker.v1` messages, the 65,536-byte JSON ceiling, the 32,056-byte
  PCM frame ceiling, lease lifetime `(0, 120]` seconds, and epoch/sequence
  rules in [the #3 spec](../3-protocol-v1-contract/spec.md)
- Hello admission, `record_stats`, `record_health`, and `note_online` in
  [the #13 spec](../13-worker-invite-identity/spec.md), as implemented in
  `livecho_backend.worker_identity` on this commit
- Epoch isolation and the rule that #14 decides when `lease_replaced` is legal
  in [the #27 spec](../27-long-session-state/spec.md). This issue's decision is
  that it is not legal here
- The worker path constant and the ban on mounting that path from the fixture
  vertical in [the #9 spec](../9-local-caption-vertical/spec.md)
- `decide_worker_resume` and `LeaseRuntimeCoordinator` already in
  `livecho_protocol`
- `CTRL-WORKER-PROTOCOL`, `CTRL-WORKER-REVOCATION`, `CTRL-WORKER-SYNTHETIC-ONLY`,
  `CTRL-AUDIO-RAM-ONLY`, and `DATA-AUDIO-EPHEMERAL` in
  [the threat model](../../security/alpha-threat-model.md) and
  [the data lifecycle](../../security/data-lifecycle-and-deletion.md)

The owner comment on Issue #14 (2026-09-26,
[comment](https://github.com/Shuang-su/Livecho/issues/14#issuecomment-5847331711))
is in scope as a consistency constraint. It does not add a product direction.
Issue #31 is a research proposal only. This contract does not add an open
contribution loop, a public leaderboard, self-service enrollment, points, or
a new message family.

Issue #13's GitHub issue may stay open. The gateway calls the merged #13
functions. It does not invent a second enrollment path and does not add a
database migration. Issue #27's GitHub issue may stay open. The gateway uses
the epoch checks already in the protocol package and does not edit
`packages/protocol/`.

## Behavior

### Four predicates

These are process-memory observations. They are not wire fields and they are
not synonyms.

| Predicate | True only when |
| --- | --- |
| `heartbeat_healthy(connection_id)` | That socket is open, it holds the active lease, and either the lease age is strictly under 5 seconds or the gateway accepted a heartbeat for that lease at gateway time `t` with `now - t` strictly under 5 seconds. |
| `device_checked(connection_id)` | `admit_hello` returned accepted for that connection and `device_usable` is still true. |
| `lease_valid(connection_id)` | That connection holds the process's single active lease, `now` is strictly before `expires_at`, and the lease is not cancelled. |
| `result_accepted(message_id)` | The gateway recorded one `accepted` protocol decision for that worker message id. |

A WebSocket that has not completed Hello is none of the first three.
`device_checked` does not imply `lease_valid`. `heartbeat_healthy` does not
imply `result_accepted`. Welcome, lease issuance, heartbeat acceptance,
resume, and socket replacement must not record `result_accepted`. Only an
`accepted` decision for `worker.transcript` or `worker.stats` records it.
`worker.heartbeat` never records it.

### Actors and authority

| Actor | How it is established |
| --- | --- |
| Worker | Outbound WebSocket. No account cookie. Device proof is the existing #13 Hello admission. |
| Grant source | In-process `arm_grant` used by tests and, later, Issue #15. Not an HTTP route and not a worker message. |
| Backend | Issues welcome, lease, cancel, ack, and error from the existing models. Assigns lease id, connection id, epoch, and start sequences. |

The worker cannot create a grant, choose an epoch, extend `expires_at`, or
name a shell, container, code, or URL field. Unknown JSON fields fail closed
under the existing parser.

### Gateway process

`create_worker_gateway_app` builds a FastAPI app whose only WebSocket route is
`/api/worker/ws`, the existing `WORKER_ENDPOINT_PATH`. The app is not mounted
by `create_local_vertical_app`, `create_worker_identity_app`, or a Railway
start command. It reads no environment variable and sets no
`livecho_session` cookie.

The upgrade must offer the exact subprotocol `livecho.worker.v1`. Any other
offer closes with WebSocket code `1002` and sends no application message. An
`Origin` header closes with `1008` before the subprotocol is accepted. A
missing or non-UUID `livecho-device-id` header closes with `1008` and does
not call `admit_hello`. The header value is the lowercase hyphenated device
id the gateway will pass into `admit_hello`. It is the connection binding #13
already required. It is not a new credential, not a cookie, and not a
protocol field.

Clocks and ids are injectable. Timestamps use the existing millisecond `Z`
form from `livecho_backend.worker_identity.clock`. Tests call `expire_due()`
after moving the clock. They must not sleep for the 5-second or 20-second
bounds. The socket handler also calls `expire_due()` before each inbound
frame and when a 5-second idle wait ends.

### Hello and lease admission

The first application frame must be one UTF-8 text frame of at most 65,536
bytes carrying `WorkerHelloV1` with `protocol_minor` 0, and it must arrive
before the socket has been open for 5 seconds of gateway time. Any other
first frame, a late first frame, or an oversize frame produces no lease. An
oversize text frame uses `control_frame_too_large`. The gateway then closes
the socket.

On a well-formed Hello the gateway calls `admit_hello(hello, device_id)` with
the header device id. It must not substitute `hello.worker_id` when the
header differs. A decision that is not accepted sends a pre-selection
`ProtocolErrorV1` (`protocol_minor` 0). If `HelloDecision.protocol_code` is
already a minor-0 `ProtocolErrorV1` code, that code is used. The #13 results
`rejected`, `device_revoked`, and `signature_invalid` are not protocol codes,
so those three use `schema_invalid`. The #13 audit row is whatever
`admit_hello` already wrote. The public `message` is the wire code and
nothing else. The socket then closes. No Welcome and no Lease are sent. The
failed call still consumes the admission exactly as #13 already specifies.
After Welcome, later errors use the selected minor's error model.

An accepted decision sends `WorkerWelcomeV1` or `WorkerWelcomeV1Minor1` for
the `selected_minor` `admit_hello` returned. Minor 0 lists exactly
`asr.transcribe` and `protocol.binary-pcm`. Minor 1 lists exactly those two
plus `protocol.epoch-rotation`. `minimum_worker_version` stays `0.1.0`.
`accepted_manifests` are the Hello manifests, which #13 already required to
be on the admin allowlist. Welcome does not issue a lease by itself.

A lease is sent only when all of the following hold:

1. `device_checked` is true.
2. `arm_grant` has one pending grant whose manifest is one of the Hello
   manifests.
3. This process has no active lease, and this `session_id` has never held a
   lease in this process.
4. Exactly one connection is in `hello_accepted` for that grant. Zero waiters
   leaves the grant pending. Two or more waiters void the grant, send no
   lease, and close the extra sockets. The void is permanent for that
   `session_id` in this process. The gateway does not pick a survivor and
   does not rank devices.

The lease object is a `LeaseV1` or `LeaseV1Minor1` matching `selected_minor`:

| Field | Value |
| --- | --- |
| `lease_id` | New lowercase UUIDv4 |
| `session_id`, `room_id` | The grant |
| `epoch` | `"1"` |
| `revision` | `"1"` |
| `issued_at` | Gateway now |
| `expires_at` | `issued_at` plus 20 seconds |
| `input_start_seq`, `output_start_seq` | `"0"` on minor 0, `"1"` on minor 1 |
| `model_manifest` | The grant's one allowlisted manifest |
| `audio_format` | `pcm_s16le`, 16,000 Hz, 1 channel |
| `audio_origin` | `synthetic` |

Installation goes through `LeaseRuntimeCoordinator.create`. The gateway must
refuse before `create` when that call would make a second active lease. It
must not call `Minor1Session.replace_lease`, must not increment the epoch,
and must not emit `EpochRotatedV1` or `ViewerResyncV1`.

`arm_grant(session_id, room_id, manifest) -> bool` stores at most one pending
grant. It returns false, and changes nothing, when a grant is already
pending, when any lease is active, or when that `session_id` already held a
lease in this process. Repeating the identical pending tuple returns true and
does not create a second grant. There is no HTTP route for it.

### Heartbeat, expiry, and expired renewal

Heartbeat is `HeartbeatV1` or `HeartbeatV1Minor1` on the worker-output
sequence. The gateway does not invent a second sequence for it, and it does
not send heartbeats.

The worker is expected to send one heartbeat every 5 seconds of gateway time
after `issued_at`. The first 5 seconds are not late. At exactly 5 seconds
after issue, or at exactly 5 seconds after the last accepted heartbeat,
`heartbeat_healthy` becomes false. That transition does not expire the lease,
does not cancel it, and does not change contribution counters.

The lease expires when gateway `now` is at or after `expires_at`. Expiry uses
`LeaseRuntimeState`'s existing rule (`now < expires_at` still valid). A
heartbeat does not change `expires_at`, `issued_at`, `epoch`, or the lease id.
This 20-second object is the whole renewal term. A successor lease is not
issued.

A heartbeat, resume, transcript, stats message, or PCM submit at or after
`expires_at` is an expired renewal attempt. The runtime returns
`lease_expired`. The gateway sends that code, records no `result_accepted`,
and does not call `record_stats`, `record_health`, or `note_online` for the
attempt. A second attempt is rejected the same way. PCM buffered for that
lease is already cleared by the runtime expiry path and must stay cleared.

Natural expiry does not require a successful `LeaseCancelV1`: once the runtime
is terminal, `cancel` also returns `lease_expired`. The gateway sends one
`ProtocolErrorV1` with `lease_expired` and does not pretend a cancel was
accepted.

### Epoch isolation

The active lease epoch is `"1"` for the life of that lease. The gateway
passes worker output and outbound PCM through the existing runtime so that:

- a lower epoch returns `epoch_stale`;
- a higher epoch returns `epoch_unknown`;
- either result leaves sequence, revision, audio budget, and contribution
  counters unchanged.

The same message presented again is rejected again. The gateway must not
accept it after expiry, after resume, or after `expire_due()`. It must not
reuse the epoch for a later lease of the same `session_id`, because this
process will not issue that later lease at all.

`revision_capacity_exceeded` stays a non-rotating rejection from the existing
runtime. This issue must not translate it into `replace_lease` or
`epoch_rotated`. Doing so would fork the #27 commit inside the gateway.
Minor-1 tombstone eviction therefore does not run on this path. The permanent
rejection this issue owes is the runtime's `epoch_stale`, `epoch_unknown`, and
`lease_expired` results, plus the refusal to reopen the session.

### Resume, disconnect, and duplicate connections

`WorkerHelloV1.resume` is evaluated only after `admit_hello` accepts, and only
through `decide_worker_resume` against the live cursor of the active lease:
`connection_id`, `lease_id`, `session_id`, `epoch`, `next_input_seq`,
`next_output_seq`, and `expires_at`. The gateway fills that cursor from the
installed runtime. It does not accept a worker-supplied epoch as authority.

| Situation | Result |
| --- | --- |
| Resume matches the unexpired lease of this same device | `resume_succeeded` true. The previous socket is closed. The same lease, epoch, and sequences remain. No new lease, no `result_accepted`, no `record_stats`. |
| Resume does not match, and a lease is already active | Error from `decide_worker_resume`, second socket closed, existing lease untouched. |
| No lease is active and exactly one waiter remains | A new lease may be issued under the admission rules above. |
| A second device Hellos while a lease is active | That connection may be `device_checked` and must not become `lease_valid`. It is closed. Epoch and counters stay as they were. |

Disconnect of the leased socket releases that lease's PCM immediately, closes
the online interval once, and leaves the lease active until `expires_at` so a
matching resume can still succeed. Disconnect does not call `record_stats` and
does not record `result_accepted`. There is no audio retry queue and no replay
of the released PCM. Sequences are not rewound.

The online interval starts when `admit_hello` accepts, not when the TCP
connection opens. It closes on disconnect, expiry, revoke, or cancel. Resume
starts a new interval at the resume instant. `note_online` is called once per
closed interval with those two gateway times. The gap while the socket is down
is not passed to `note_online`. Two intervals must not cover the same instant:
the first is closed at the disconnect time before the next one starts.

### Revocation

Before Welcome side effects beyond the #13 decision, before lease issue, before
each heartbeat, stats, or transcript side effect, before renewal-attempt
handling, and before `submit_synthetic_pcm`, the gateway calls
`device_usable(device_id)`. The method is a new read on the existing #13
service. It returns true only when the device exists, its status is active,
and its account is still an active contributor. It writes no audit row and no
statistic.

A false result while a lease is active sends `LeaseCancelV1` with reason
`policy_disable` and `expected_revision` equal to the current lease revision,
then closes the socket. The in-flight frame is not applied. PCM is cleared.
`note_online` runs once for the open interval. Later `record_stats`,
`record_health`, and `note_online` calls fail closed through the existing #13
rules and leave aggregates unchanged. Account role and status stay whatever
#13 revocation already left them.

### Contribution consistency

The gateway is the only caller of the #13 update functions on this path, and
only after a protocol decision:

| Event | `record_stats` | `record_health` | `note_online` | `result_accepted` |
| --- | --- | --- | --- | --- |
| Hello accepted | no | no | interval opens; not closed yet | no |
| Lease issued or Welcome sent | no | no | no extra call | no |
| Heartbeat `accepted` | no | once, state from the frame, time is gateway now | no | no |
| Stats `accepted` | once, the cumulative fields from that frame | no | no | yes, for that message id |
| Transcript `accepted` | no | no | no | yes, for that message id |
| `seq_duplicate`, `revision_duplicate`, or any rejection | no | no | no | no |
| Resume succeeded | no | no | previous interval already closed at disconnect | no |
| Expired renewal attempt | no | no | no | no |
| Revocation or `policy_disable` | no for the rejected frame | no for the rejected frame | close the open interval once | no |
| Process restart | the new service starts empty | the new service starts empty | the new service starts empty | the new service has none |

`record_health` receives the gateway clock, not the worker's `observed_at`, so
a forged timestamp cannot move `recent_health`. The worker field is still
schema-validated. `record_stats` is not called for a duplicate, so a resent
result cannot add processed time or success twice. A lower cumulative counter
keeps the previous aggregate through the existing #13 rule. The gateway must
not reset those aggregates on resume, expiry, or restart of a socket.

Danmaku volume, points, cash, and leaderboard fields are not parameters.

### Restart

`restart()` on the gateway tears down every session it issued through the
public `LeaseRuntimeCoordinator.session_teardown`, drops its grants, sockets,
and predicate maps, and is then pointed at a new `WorkerIdentityService`. It
must not read or write a file, database, or queue. After `restart()`:

- the previous lease id is unknown and its output is rejected;
- the new identity service's statistics are the empty initial values;
- a replayed stats or transcript frame does not change those values;
- a new Hello requires a new #13 admission on the new service.

Leases and contribution counters therefore disappear together. The gateway
must not persist one of them without the other. This models a process restart
of the in-memory adapters. It is not a durable recovery drill.

### Frame size and rate

Size limits are the accepted protocol limits. Rate limits are gateway limits.
Both are hard. Counts use the gateway clock and a rolling one-second window:
a frame at `t` shares the window with frames at times strictly greater than
`t - 1s` and less than or equal to `t`.

| Path | Size | Rate | Over the limit |
| --- | --- | --- | --- |
| Inbound text | 65,536 bytes | 10 frames | Size uses `control_frame_too_large` and closes. The 11th frame in the window closes with WebSocket code `1008`. If a lease is active it is cancelled with `protocol_violation` first. The excess body is not parsed for side effects and is not stored. |
| Inbound binary | 32,056 bytes | 2 frames | Size uses `binary_frame_too_large` and closes. A smaller inbound binary frame is not worker audio: the gateway does not call `accept_pcm` on it, does not retain the payload, and answers `binary_header_invalid`. The third binary frame in the window is not read into a retained buffer; the socket closes with `1008` and an active lease is cancelled with `protocol_violation`. |
| Outbound PCM | 32,056 bytes, and the existing 960,000-byte lease budget and 16,777,216-byte process budget | 50 frames and 32,000 payload bytes | `submit_synthetic_pcm` refuses before send. Refused bytes are not queued. |
| Outbound control | 65,536 bytes | 10 frames | The gateway stops sending and closes with `1008` rather than emit an 11th control frame. |

32,000 payload bytes in one second is the canonical realtime rate of
16 kHz, 16-bit, mono PCM. Fifty frames of 20 ms fit that rate. The gateway
must not burst the 30-second lease budget inside one second.

`submit_synthetic_pcm(lease_id, frame)` is the only outbound PCM entry. It
sends only when `lease_valid` is true for that lease, `device_usable` is true,
`audio_origin` is `synthetic`, the rate and budgets accept the frame, and
`LeaseRuntimeState.accept_pcm` returns `accepted`. The payload stays in that
runtime budget until `consume_pcm`, disconnect, expiry, cancel, revoke, or
teardown. Tests may build a frame in memory. They must not write it to disk,
a fixture, a log, or a snapshot.

### Outbound allowlist

Every backend application message is one of these existing models, chosen for
the connection's selected minor after Welcome:

- `WorkerWelcomeV1` or `WorkerWelcomeV1Minor1`
- `LeaseV1` or `LeaseV1Minor1`
- `LeaseCancelV1` or `LeaseCancelV1Minor1`
- `ProtocolAckV1` or `ProtocolAckV1Minor1`
- `ProtocolErrorV1` or `ProtocolErrorV1Minor1`

`EpochRotatedV1` and `ViewerResyncV1` are not sent. Cancel reasons are only
the existing literals. This issue uses `lease_expired` only as the runtime's
error code for natural expiry, and `policy_disable` or `protocol_violation`
as `LeaseCancelV1.reason` when the gateway itself closes a live lease.
`expected_revision` is the runtime's current lease revision. The initial lease
revision is `"1"`.

An ack is sent for `accepted`, `seq_duplicate`, `revision_duplicate`, and
`cancel_duplicate`. Every other stable code is an error. `message` is the
code string. `retryable` is true only for `resync_required` and
`epoch_rotated`. This gateway does not emit `epoch_rotated`. `expected` and
`received` are null unless the existing decision already carries those
integers. Error and ack bodies must not echo the rejected payload, transcript
text, or PCM.

Adding a key named `shell`, `container`, `code`, `url`, `uri`, `command`,
`path`, or `download` to any outbound model must fail validation. Tests cover
that rejection on the model classes the gateway uses. Encoded outbound objects
contain only that model's fields.

Out-of-order worker output is not buffered. A `seq` above the next expected
value returns `seq_gap` from the runtime, does not advance the sequence, and
does not call `record_stats`. A later frame with the missing sequence is
evaluated normally. The gateway must not insert the skipped frame afterward.

### `device_usable`

`WorkerIdentityService.device_usable(device_id: str) -> bool` reads the
existing memory adapter and account lookup. Unknown, revoked, and
non-active-contributor devices return false. The method must not change
enrollment, challenge, allowlist, or statistic behavior, and it must not add a
route, a column, or a migration.

## Interfaces and compatibility

The later implementation may add:

- `services/backend/src/livecho_backend/worker_gateway/`
- `tests/worker_gateway/`
- `create_worker_gateway_app`
- `arm_grant`, `expire_due`, `restart`, `submit_synthetic_pcm`
- the four predicate methods
- `WorkerIdentityService.device_usable`

It must import #13 and the protocol package rather than copy a second
admission or epoch machine. It must not modify `packages/protocol/`,
`workers/mlx/`, `apps/web/`, `db/migrations/`, `.env.example`, CI workflows,
or Railway config. It must not register `/api/worker/ws` on the local vertical
app or the worker-identity app. `LIVECHO_EMAIL_ENABLED` and
`LIVECHO_PERSISTENCE_ENABLED` stay false. No new secret name is added.

No change to `epoch`, `seq`, or `revision` meaning is in scope. A new control
message, a signature field on Hello, or a server-provided download URL is a
protocol or threat-model change and is out of scope.

JSON control parsing stays the #3 parser: UTF-8, one object, no duplicate
keys, closed schemas. The gateway must not keep a rejected body after the
error is sent.

## Failure modes and disable path

| Condition | Outcome |
| --- | --- |
| Wrong subprotocol or browser `Origin` | Close `1002` or `1008`. No Hello call. No lease. |
| Hello before a live #13 admission | No Welcome, no lease, admission rules unchanged. |
| Header device id mismatches `worker_id` | `admit_hello` applies the existing mismatch result. No lease. |
| Two authenticated waiters and no lease yet | Grant void. No lease. No device ranking. |
| Second device while a lease is active | No second lease. First lease and epoch stay. |
| Heartbeat 5 seconds late | `heartbeat_healthy` false. Lease stays until `expires_at`. Counters unchanged. |
| `now >= expires_at` | `lease_expired`. Further attempts rejected. PCM stays clear. Counters unchanged. |
| Old or unknown epoch | `epoch_stale` or `epoch_unknown`. Still rejected on resend. |
| Out-of-order `seq` | `seq_gap` or the existing conflict code. No buffer. No stat write. |
| Inbound frame over size or rate | Close, and cancel with `protocol_violation` when a lease is active. No retained PCM. |
| `device_usable` false | `policy_disable`, PCM cleared, aggregates unchanged. |
| `restart()` | New empty identity service. Old lease rejected. No file restored. |
| Coordinator would open a second lease | Refuse before `create`. |

To stop the gateway, stop constructing `create_worker_gateway_app` and stop
mounting it. This issue has no production flag to turn on and no production
deployment to roll back. Clearing the in-memory objects drops leases and PCM
together.

## Security, privacy, and data lifecycle

- Trust boundary: the worker is untrusted. Authentication is the #13
  admission. A valid device is not a lease, and a lease is not an accepted
  result.
- The socket carries ephemeral synthetic PCM and worker metadata. PCM must not
  be written to disk, database, queue, log, fixture, or object storage. Release
  it on consume, disconnect, expiry, cancel, revoke, disable, and teardown.
  The implementation must not claim that a hostile host erased its copy.
- Community-worker audio stays synthetic. `submit_synthetic_pcm` is not a
  real-PCM grant. `RISK-WORKER-AUDIO-RETENTION` stays not accepted.
- Logs, when present, may contain the stable code, device id, lease id,
  session id, and epoch integers. They must not contain PCM, transcript text,
  tokens, signatures, public keys, cookies, or URLs.
- The worker receives no Bilibili credential, cookie, playback URL, archive
  key, shell, container, code, or download URL. `FLOW-DENY` paths from the
  worker to Postgres, Bucket, Resend, and the platform stay closed because
  this gateway does not open them.
- `restart()` must not snapshot contribution counters or leases to survive the
  process. A later durable store is a different issue.
- Tests generate PCM only in process memory and discard it at teardown.

## Acceptance criteria

- [ ] Hello and a lease are sent only after `admit_hello` accepts. A missing
      admission, a device-id mismatch, a revoked device, and a Hello that
      fails negotiation produce no lease.
- [ ] An active lease has `expires_at` exactly 20 seconds after `issued_at`.
      `heartbeat_healthy` is false at 5 seconds without an accepted heartbeat,
      while `lease_valid` remains true until `expires_at`. A heartbeat does
      not move `expires_at`. At and after `expires_at`, output and heartbeat
      are `lease_expired` and contribution counters are unchanged.
- [ ] The process has at most one active lease. A second connection, including
      a second authenticated device, does not receive one. A matching resume
      keeps the same lease and does not record a result or a second stats
      update.
- [ ] Inbound text over 65,536 bytes and inbound binary over 32,056 bytes are
      rejected and not retained. The 11th inbound text frame and the 3rd
      inbound binary frame in one rolling second close the socket. Outbound
      PCM stops at 50 frames or 32,000 payload bytes in that window and never
      exceeds the existing lease and process budgets.
- [ ] State-machine tests cover disconnect, duplicate connections, expired
      renewal, out-of-order output, and `restart()`. Old-epoch output is
      rejected on first presentation and on resend, with no contribution
      change.
- [ ] Encoded server messages are instances of the allowlisted models. Adding
      `shell`, `container`, `code`, `url`, or `uri` fails validation. The
      gateway does not send `EpochRotatedV1`.
- [ ] Reconnect, `restart()`, expired renewal, revocation, and result resend
      leave the four predicates and the five #13 statistics consistent with
      the table above. Connection recovery does not set `result_accepted` and
      does not apply `record_stats` twice.
- [ ] The implementation diff does not edit `packages/protocol/`,
      `db/migrations/`, `.env.example`, CI, or Railway config, and it does not
      enable production auth, mail, secrets, live ingest, real ASR, real
      community-worker PCM, or CUDA.
