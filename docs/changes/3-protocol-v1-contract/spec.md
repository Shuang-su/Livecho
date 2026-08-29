# Specification: Protocol v1 and cross-language compatibility

Normative terms such as **must**, **must not**, and **may** apply to the Issue #3
implementation. A later change cannot weaken them without a repository-owner-approved
protocol Issue and compatibility evidence.

## Behavior

### Transport and canonical values

The worker WebSocket must negotiate the exact subprotocol `livecho.worker.v1`; the
viewer WebSocket must negotiate `livecho.viewer.v1`. A missing or different major
subprotocol is rejected before an application message is accepted. Version 1.0 selects
minor `0`; there is no silent fallback to another major or minor.

JSON control input is one UTF-8 JSON object per WebSocket text message, with a maximum
encoded size of 65,536 bytes. The parser must reject invalid UTF-8, duplicate object
keys, non-object roots, non-finite numbers, unknown fields, invalid enum values, and data
outside schema bounds. JSON schemas are closed recursively. The selected subprotocol is
also repeated in the top-level `protocol` literal and every control message carries
`protocol_minor: 0`, a lowercase canonical UUIDv4 `message_id`, an exact `type`
discriminator, and a canonical UTC timestamp with exactly millisecond precision and a
`Z` suffix.

Wire fields with schema format `uint64-decimal`, including `epoch`, `seq`, `revision`,
cursors, and cumulative counters, are canonical decimal strings in the inclusive range
0 through 18,446,744,073,709,551,615. Only `"0"` may start with zero. This avoids loss
of precision in JavaScript. Durations and bounded per-message counts that cannot exceed
2,147,483,647 remain JSON integers. UUIDs are lowercase hyphenated strings. Opaque
backend-issued room identifiers are 1-128 lowercase ASCII characters matching
`[a-z0-9][a-z0-9._:-]*`; they are never URLs or playback locators.

### Authoritative and supporting models

The authoritative Python package must export the following strict Pydantic models. All
string lengths, numeric ranges, enum values, and collection counts below are schema
bounds, not advisory limits.

| Model | Direction and required payload |
| --- | --- |
| `WorkerHelloV1` | Worker to backend before any lease: envelope; `worker_id` UUIDv4; SemVer `worker_version` up to 64 characters; unique `supported_minors` containing 1-16 integers from 0-255; unique `capabilities` containing 1-16 known capability literals; 0-16 `ModelManifestRefV1` values; and optional `WorkerResumeV1`. Outside that closed resume object it contains no session, locator, path, arbitrary metadata, or secret. |
| `LeaseV1` | Backend to worker: envelope; `lease_id`, `session_id`, `room_id`; `epoch` starting at `"1"`; lease `revision` starting at `"1"`; canonical `issued_at`/`expires_at`; `input_start_seq` and `output_start_seq`; exactly one allowlisted model manifest; fixed `AudioFormatV1`; and `audio_origin: "synthetic"`. Expiry is after issue time and no more than 120 seconds later. |
| `HeartbeatV1` | Worker to backend for an active lease: envelope; lease/session binding; `epoch`; stream `seq`; worker state `ready`, `busy`, `draining`, or `error`; optional last accepted input/output sequences; `audio_buffer_bytes` from 0-960,000; and `observed_at`. It has no free-form metrics map or diagnostic body. |
| `WorkerStatsV1` | Worker to backend for an active lease: envelope; lease/session binding; `epoch`; stream `seq`; stats object `revision`; bounded cumulative `processed_audio_ms`, `segments_accepted`, and `segments_rejected`; `realtime_factor` from 0 through 100 with at most six decimal places; and `window_started_at`/`window_ended_at`. It has no host inventory, command output, transcript body, or extensible map. |
| `TranscriptSegmentV1` | Worker to backend: envelope; lease/session binding; `segment_id`; `epoch`; stream `seq`; segment `revision`; `start_ms` and `end_ms` with `0 <= start_ms < end_ms` and a maximum 30,000 ms span; normalized UTF-8 `text` of 1-4,096 Unicode scalar values; optional BCP-47 `language`; optional confidence from 0 through 1 with at most six decimal places; and `is_final`. It contains no audio representation or raw platform identity. |
| `TimelineEventV1` | Backend to viewer: envelope; `event_id`, `session_id`, `room_id`; `epoch`; viewer-stream `seq`; event `revision`; `occurred_at`; and a closed discriminated payload. V1.0 payloads are `TranscriptTimelinePayloadV1`, containing exactly `segment_id`, `start_ms`, `end_ms`, `text`, optional `language`, optional `confidence`, and `is_final`, or `SessionStatusTimelinePayloadV1`, containing only `status` (`starting`, `live`, `stopping`, `stopped`, or `failed`) and an optional 1-64-character conservative-ASCII stable `reason_code`. No raw platform payload or arbitrary object is permitted. |

The worker handshake additionally exports `WorkerResumeV1`, containing exactly the
previous `connection_id`, `lease_id`, `session_id`, `epoch`, `next_input_seq`, and
`next_output_seq`, and `WorkerWelcomeV1`, which selects minor 0, returns a backend-issued
`connection_id`, states `minimum_worker_version`, reports whether resume succeeded, and
lists the accepted capability/manifest identifiers. The viewer handshake exports
`ViewerSubscribeV1`, with SemVer `client_version`, `supported_minors`, a room ID, and an
optional `ViewerCursorV1`, and `ViewerReadyV1`, with the selected minor, minimum client
version, current session/epoch, next viewer sequence, and whether the cursor resumed.

`ProtocolAckV1` is available on both subprotocols and contains only the envelope,
`outcome` (`accepted`, `seq_duplicate`, or `revision_duplicate`), and the applicable
message identity/sequence/revision. `ProtocolErrorV1` contains only the envelope, stable
rejection `code`, bounded public `message`, `retryable`, and optional
`expected`/`received` uint64 decimal values. Neither response may echo an invalid
payload, transcript, secret, locator, or audio.

`ModelManifestRefV1` is a closed tuple-like object containing only `provider`,
`model_id`, `revision`, and a lowercase 64-character SHA-256 digest. Each textual field
is 1-128 characters from a conservative ASCII allowlist. It has no URL, URI, filesystem
path, command, environment, or options field. `AudioFormatV1` is exactly
`encoding: "pcm_s16le"`, `sample_rate_hz: 16000`, `channels: 1`.

The backend-to-worker control set also exports `LeaseCancelV1`, containing only the
envelope, `lease_id`, `session_id`, `epoch`, the exact current lease `revision`, and one
reason literal: `operator_stop`, `lease_expired`, `worker_replaced`, `policy_disable`,
`protocol_violation`, or `session_end`. It is idempotent by message ID and bound lease
revision, immediately prevents later PCM/output acceptance for that lease, and contains
no arbitrary instruction or reason text. Repeating the identical cancellation is an
accepted no-op; changing the reason under the same identity/revision is a conflict.

Known worker capability literals in minor 0 are `asr.transcribe` and
`protocol.binary-pcm`. A worker must advertise both. The backend intersects only known
values and must reject an unknown or missing required capability rather than treating it
as an extension. Manifest acceptance is equality on the complete allowlisted reference,
including digest; the protocol never instructs a worker where or how to obtain a model.

### Binary PCM message boundary

After an active synthetic `LeaseV1`, PCM is carried in one WebSocket binary message with
a fixed 56-byte header followed immediately by the payload. Header integers are unsigned
network-byte-order values; the payload is signed 16-bit little-endian mono PCM.

| Offset | Size | Field | Rule |
| --- | --- | --- | --- |
| 0 | 4 | magic | ASCII `LPCM` |
| 4 | 1 | major | `1` |
| 5 | 1 | minor | negotiated `0` |
| 6 | 1 | flags | bit 0 is `END_OF_SEGMENT`; all other bits are zero |
| 7 | 1 | header length | `56` |
| 8 | 16 | lease ID | UUID bytes in network order |
| 24 | 8 | epoch | uint64, at least 1 |
| 32 | 8 | seq | uint64 |
| 40 | 8 | PTS milliseconds | uint64, monotonic within the lease |
| 48 | 4 | sample count | 1-16,000 |
| 52 | 4 | payload length | 2-32,000 and exactly `sample_count * 2` |

The complete application message is at most 32,056 bytes. The lease ID, epoch, expected
input sequence, audio format, and current in-memory budget must match the active lease
before payload use. Invalid magic/version/header length/flags/size, an expired or wrong
lease, a stale or unknown epoch, non-monotonic PTS, a sequence gap/conflict, or a budget
overflow rejects the whole message without buffering it. One message covers at most one
second, the active aggregate still cannot exceed the Issue #2 30-second/960,000-byte
lease and session ceilings, and no retry queue is created.

Repository fixtures must never contain this payload, a hex/base64 encoding of it, a
WAV, an audio digest, or a recoverable derivative. Codec and boundary tests create the
minimum required synthetic byte arrays in process memory, do not print them, do not
snapshot them, and release them at test teardown.

### Ordering, idempotency, and reconnect

The backend assigns an `epoch` beginning at `"1"` for a session. Replacing the worker
authority or issuing a non-resumed lease increments the epoch. A client cannot create or
advance it. Messages for a lower epoch are `epoch_stale`; messages for a higher,
unissued epoch are `epoch_unknown`. Neither changes state.

Sequence domains are independent for `(session_id, lease_id, epoch, direction)` on the
worker connection and `(session_id, epoch, viewer stream)` on the viewer connection.
Worker input PCM starts at `LeaseV1.input_start_seq`; `HeartbeatV1`, `WorkerStatsV1`, and
`TranscriptSegmentV1` share the worker-output sequence beginning at
`LeaseV1.output_start_seq`; viewer timeline delivery begins at the `ViewerReadyV1`
sequence. In each domain:

1. The receiver accepts only the exact next expected `seq` and then increments it.
2. A lower JSON `seq` is an idempotent no-op only when its message identity and canonical
   content digest match the previously accepted value in the current bounded in-memory
   deduplication window. It yields `seq_duplicate` without reapplying side effects. A
   lower binary PCM `seq` in the current window is always discarded unread as the same
   no-op; audio bytes are neither compared nor hashed.
3. Reusing a sequence with different identity or content is `seq_conflict`.
4. A higher sequence is `seq_gap`; the receiver does not buffer, skip, or advance.
5. JSON deduplication digests remain in memory only, are never logged or persisted, and
   must never be computed for or from PCM payload bytes. A sequence older than the
   bounded current window yields `resync_required`; no historical or audio retry store
   is created.

Revision domains are per stable lease, transcript segment, stats window, or timeline
event identity within one session/epoch. A new object starts at revision `"1"`. The
receiver accepts only current revision plus one; an exact canonical retransmission of
the current revision is a no-op; a changed value at the current revision is
`revision_conflict`; a lower value is `revision_stale`; and a jump is `revision_gap`.
An `is_final: true` transcript cannot be revised. A revision cannot move an object to a
different session, lease, epoch, time range, or identity.

`LeaseCancelV1` closes the named lease at its exact current revision without consuming
the PCM input sequence. It is checked before any later input/output message, and closed
lease traffic returns `lease_closed` while expiry returns `lease_expired`. Cancellation
clears bounded PCM/deduplication state; a cancellation cannot be undone or converted
into a different reason by replay.

`WorkerHelloV1` and `ViewerSubscribeV1` may include a reconnect cursor. Resume succeeds
only when the named connection/session, exact lease where applicable, epoch, and next
sequence still match live in-memory authoritative state and the lease is unexpired. The
backend replies with the same epoch and expected next sequences. Otherwise it emits
`resync_required` or the more specific lease/epoch error. It never silently resets a
sequence or downgrades a version. A new worker lease uses a higher epoch; a viewer whose
cursor can no longer be served starts from a newly returned current cursor without any
claim of historical replay.

### Stable rejection contract

Python and TypeScript validators compare stable Livecho codes rather than library error
text. Minor 0 defines at least:

`malformed_json`, `duplicate_key`, `unknown_field`, `schema_invalid`,
`control_frame_too_large`, `unknown_major`, `unsupported_minor`,
`worker_version_too_old`, `capability_required`, `manifest_not_allowed`,
`lease_unknown`, `lease_expired`, `lease_closed`, `binding_mismatch`, `epoch_stale`, `epoch_unknown`,
`seq_duplicate`, `seq_conflict`, `seq_gap`, `revision_duplicate`,
`revision_conflict`, `revision_stale`, `revision_gap`, `object_final`,
`resync_required`, `binary_header_invalid`, `binary_frame_too_large`,
`audio_pts_invalid`, and `audio_budget_exceeded`.

`seq_duplicate` and `revision_duplicate` describe successful `ProtocolAckV1` no-op
outcomes; every other listed code is a `ProtocolErrorV1` rejection. Tests must prove no
rejected message advances a counter,
changes a revision, consumes audio budget, or emits a timeline event. Protocol errors
are bounded and safe to return; detailed parser/validator diagnostics remain internal
and payload-free.

## Interfaces and compatibility

### Source, generation, and shared fixtures

The implementation uses this layout:

- `packages/protocol/python/livecho_protocol/`: hand-edited strict Pydantic models,
  semantic validators, ordering state machines, binary header codec, compatibility
  matrix, and stable error codes;
- `packages/protocol/schema/`: committed generated JSON Schemas and compatibility JSON;
- `packages/protocol/src/generated/`: committed generated TypeScript types;
- `packages/protocol/src/`: TypeScript semantic validation and golden runner;
- `packages/protocol/fixtures/accepted/` and `rejected/`: shared synthetic JSON cases;
- `tests/protocol/`: Python model, ordering, binary boundary, and generation tests; and
- `tools/protocol_codegen.py`: the only generation entry point.

The root Python environment adds pinned Pydantic v2. The protocol workspace adds pinned
TypeScript, Ajv 2020, and JSON-Schema-to-TypeScript dependencies and implements the
required `lint`, `typecheck`, `test`, and `build` scripts. Python creates draft 2020-12
JSON Schema. TypeScript validates the `wire` member of each fixture with the matching
generated schema plus explicit semantic checks. Both runners load the same manifest and
compare the expected accept/reject result and stable code.

Generated output has sorted object keys, stable schema/model ordering, LF endings, one
terminal newline, fixed `$id` values, and no timestamp, machine path, random value, or
tool-version banner. `make protocol-generate` rewrites all generated output atomically.
`make protocol-check` generates into a temporary directory and byte-compares the full
expected file set, including detecting missing and extra generated files. `make verify`
must call the drift check. Generated files are never manually edited.

Golden cases use a closed wrapper containing `case_id`, `model`, `expect`, `code`, and
exactly one input member: `wire` for a parsed object, `raw_text` for parser cases such as
duplicate keys, or `binary_header` for metadata-only binary boundary cases. Accepted
cases cover every model, `LeaseCancelV1`, and both timeline payloads. Rejected cases
cover every stable failure family, boundaries immediately below/at/above limits,
duplicate JSON keys through raw-text cases, cross-session/lease binding, version and
minimum-worker negotiation, stale/unknown epoch, duplicate/conflicting/gapped sequence
and revision, final-object mutation, reconnect resume/refusal, manifest/capability
policy, and binary-header metadata. Binary metadata cases contain header field values
only, never payload bytes. Case IDs and expected codes are unique and deterministically
ordered.

### Version policy

The committed compatibility matrix for launch is:

| Surface | Major | Accepted minor | Minimum client |
| --- | --- | --- | --- |
| Worker | 1 | 0 | worker `0.1.0` |
| Viewer | 1 | 0 | protocol client `0.1.0` |

Worker/client versions are valid SemVer without build metadata for negotiation.
Pre-release versions compare by SemVer rules and are below the corresponding release.
Patch releases are accepted only when the major/minor protocol and required capabilities
remain compatible; application version never overrides protocol negotiation.

A future minor under major 1 may add optional fields with defaults, a capability-gated
message/payload kind, or a new stable error code. Negotiation selects one exact minor,
and the receiver validates the closed schema for that minor; an older minor does not
accept unknown newer fields. A minor must not remove or rename a field, make an optional
field required, change a type/bound/meaning, weaken validation, alter ordering or
idempotency, change the binary header, or expose a new data class without its owning
Issue and risk review.

A new major is required for any incompatible required-field/type/semantic change, any
change to `epoch`/`seq`/`revision` meaning, JSON numeric encoding, the binary header or
PCM encoding, subprotocol identity, trust boundary, or removal of a previously accepted
case. Every protocol change updates authoritative models, compatibility data, schemas,
types, and golden cases atomically and includes evidence that every still-supported old
fixture retains its result. There is no silent downgrade.

## Failure modes and disable path

- Handshake version, client-version, capability, or manifest mismatch closes the
  application session before a lease or timeline cursor is issued.
- Malformed, oversized, unknown-field, or semantically invalid JSON is rejected as one
  message; its body is not reflected or logged and state is unchanged.
- Invalid binary metadata or budget state rejects the whole message before payload use.
  The receiver does not retain the message for retry.
- Expiry, disconnect, cancellation, stale epoch, sequence conflict, or repeated policy
  violations invalidate or revoke the affected lease according to later gateway Issues;
  Issue #3 supplies `LeaseCancelV1`, the deterministic close decision, and stable code
  but does not implement worker scheduling.
- The protocol can be disabled by not mounting its WebSocket endpoints. No deployment
  or production path is enabled by this Issue.
- Generation drift, missing fixtures, cross-language disagreement, or an unpinned
  generator dependency fails `make verify` and blocks merge.
- Rollback reverts the authoritative source and all generated artifacts together. A
  deployed reader must not advertise a minor or major whose complete validator and
  compatibility matrix are absent.

## Security, privacy, and data lifecycle

- Browser and worker messages are untrusted. Validate size and UTF-8/JSON structure
  before model validation, then validate negotiated version, identity/binding, manifest,
  epoch, ordering, revision, and current resource budget before side effects.
- The backend alone issues UUIDs for sessions/leases/connections, selects versions,
  maintains counters, and turns accepted worker output into a viewer event. Worker text
  never becomes authoritative merely because it is schema-valid.
- No message has a URL, URI, filesystem path, command, code, container, environment,
  arbitrary options, raw payload, credential, cookie, signed playback locator, archive
  key, or extensible metadata field. Unknown fields fail closed.
- Model references are identifier/digest claims compared to a backend allowlist. The
  protocol does not download, execute, or attest a model or worker host.
- JSON fixtures and diagnostics use synthetic, public-safe values. Validator logs contain
  only protocol/minor, message type when safely decoded, stable code, bounded identifiers,
  and timing; never transcript/event bodies, invalid input, low-entropy content digests,
  credentials, raw payloads, or audio.
- PCM exists only in bounded process memory for an active synthetic lease or an in-memory
  codec test. It is evicted on consumption, end-of-segment, expiry, cancellation,
  disconnect, disablement, and teardown. The protocol creates no persistence, queue,
  dump, snapshot, fixture, telemetry, or retry copy.
- This contract does not claim that an untrusted host erased RAM. Real-audio assignment
  remains disabled pending the Issue #2 rights record and individually accepted
  `RISK-WORKER-AUDIO-RETENTION` decision.

## Acceptance criteria

- [ ] `livecho.worker.v1` and `livecho.viewer.v1` strict JSON control models and the
  56-byte binary PCM boundary are generated, documented, and tested without any audio
  fixture or persistence.
- [ ] Focused executable tests cover epoch authority, exact-next sequencing, idempotent
  duplicate versus conflict, out-of-order rejection without buffering, revision rules,
  final-object behavior, reconnect resume/refusal, and unchanged state on rejection.
- [ ] `make protocol-generate` is deterministic, `make protocol-check` detects changed,
  missing, and extra generated output, and `make verify` enforces drift.
- [ ] Python and TypeScript run the identical accepted/rejected golden corpus and agree
  on decision and stable Livecho code for every case.
- [ ] The committed compatibility matrix and tests enforce exact minor selection, no
  downgrade, major/minor change rules, and minimum worker/client version `0.1.0`.
- [ ] Models and tests prove closed bounds and prohibit secrets, locators, arbitrary
  execution/download fields, raw platform payloads, and persistent or fixture audio.
- [ ] `make bootstrap`, `make verify`, and `git diff --check` pass, and Issue #3 evidence
  records exact commands/results without claiming live, model, deployment, or hardware
  validation.
