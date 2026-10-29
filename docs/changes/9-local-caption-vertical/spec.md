# Specification: Single-worker local caption vertical

This independently authored proposal preserves accepted [protocol](../3-protocol-v1-contract/spec.md),
[model decision](../5-mlx-benchmark/spec.md) and [audio](../8-memory-audio/spec.md)
contracts. #6/#11 proposals are coordinated interfaces, not accepted authority until
their own artifacts land. No external reference behavior is a requirement.

## Behavior

### Modes, authority and admission

Use one modular-monolith backend with local CLI controls and two explicitly labeled
modes: `fixture_timeline` and `synthetic_mlx`. The first emits independently authored
synthetic transcript/status metadata through the real viewer validation/publication
path without audio, decoder, worker inference or model loading. It is appropriate for
#11 UI checks but cannot pass the audio/ASR vertical. Never fall back from MLX to this
mode after failure, or label fixture text as recognized speech.

The first implementation phase enables only explicitly selected `fixture_timeline`.
After this Issue's artifacts are accepted, its admission requires existing v1 viewer
validation, fixed loopback configuration, a bounded text schedule and local
enable/stop/disable policy. It does not require #5 model evidence or manifest, #6
worker readiness, #8 audio integration, speech producer approval, host audio evidence
or the audio/MLX execution registry. It creates no worker, lease, PCM segment, decoder
or provider. `synthetic_mlx` stays closed; selecting it reports `blocked_evidence`
locally and never substitutes fixture output. Requirements below concerning source,
audio, worker, lease or model apply only to `synthetic_mlx`; viewer validation,
ordering, queue bounds, run-generation invalidation and publication closure apply to
both modes. No v1 field or meaning changes with mode selection.

`synthetic_mlx` requires an explicit trusted local operator start, one reviewed source
binding, one local worker and all prerequisite evidence. Refuse before source opening
unless #6/#8 integration is implemented from accepted artifacts; #5's actual complete
report, owner-approved model ADR and final inference manifest match; supported host,
decoder/provider memory and no-paging/no-crash evidence pass; and the local execution
registry is explicitly enabled for this exact reviewed run. No unfinished coordinator
task or model cache substitutes for these gates. Missing evidence gives `blocked_evidence`
in local payload-free diagnostics and no audio/MLX execution.

The source is freshly generated synthetic speech, with an immutable reviewed producer
implementation/configuration and text script, rights/provenance record and memory-only
output contract. It feeds only the fixed raw PCM formats accepted by #8; no file,
cached speech, network media, arbitrary URL, real human recording or platform session
is admitted. The exact approved producer record is a pre-run evidence gate, not an
implicit authorization to download TTS models or invoke an unreviewed generator.
Tones/noise may validate audio machinery but cannot count as speech-recognition evidence.

There is one configured opaque synthetic room and one immutable session at a time.
CLI start in either mode creates a new UUID session and backend epoch 1. Only
`synthetic_mlx` selects one exact approved
manifest and one compatible local worker. Worker enrollment and public account/device
registration are not part of this loopback demonstration. A lease lasts 90 seconds
at most; a demonstration accepts source media for at most 60 seconds and drains within
the remaining lease time. No lease renewal or indefinite session is introduced.

The local demonstration switch is separate from production ingest, which stays off.
Global emergency disable, scoped stop or deletion immediately closes local admission
and public visibility too. The synthetic switch cannot bypass safety disable/denylist
state or authorize a production/source capability. Unknown control state fails closed.

### Data path and bounded ownership

Order: approved synthetic source -> #8 decoder/VAD/segment handle -> backend v1 binary
sender -> one #6 worker -> validated final transcript -> normalized v1 timeline ->
viewer. Fixture order is authored text/status schedule -> backend validation ->
normalized v1 timeline -> viewer; it never fabricates worker messages or audio handoff
evidence. No browser or worker receives a source locator, account secret, raw event,
archive key or acquisition instruction. Backend and worker have independent audio
ledgers; all views/copies/transport internals stay within #2/#8 ceilings.

Borrow at most one #8 completed segment. Within its 1,000 ms lifetime, reserve all
transport storage, send frames no longer than one second with original PTS, release
the borrowed handle and retain no retry copy. If bounded transfer cannot finish in
time, fail the attempt and cancel the lease; a larger queue is not a remedy. The
segment's final frame alone sets `END_OF_SEGMENT`. Context retains the exact #8
sample ranges and header PTS, including the proposed 5000 -> 5200 boundary, only after
its required independent/executable compatibility evidence passes.

The backend remembers only bounded segment metadata for the one outstanding inference:
session/lease/epoch, input sequence interval, original start/end/new-start PTS and local
timing observations. It does not resend consumed PCM after timeout/disconnect or reset
the source clock. #8 backpressure and handle deadlines remain unchanged; a worker too
slow for that bounded pipeline produces a failed/blocked result rather than expanding
RAM or hiding lost media. No second segment is admitted to the worker while it is busy.

Every asynchronous source, transfer, provider and publish callback carries an internal
run generation. Under the same state owner, atomically revalidate that generation,
active lease/epoch, exact expected sequence, expiry and nonclosing/noncancelled state
before committing or publishing. A held completion from an expired/cancelled/restarted
run cannot consume input/output positions, reopen admission or affect a new session.
The #6 terminal candidate additionally requires confirmed actual audio release before
terminal commit/ack; a metadata counter reset is not proof of release.

Before accepting a transcript, validate the complete v1 envelope, lease, epoch, output
sequence/revision and immutable bounds against the outstanding segment metadata.
The first worker segment UUID must be fresh for this lease/epoch; bind it to that
metadata and reject reuse or unmatched bounds. V1 protocol validation alone does not
make worker text authoritative. The real first release accepts final-only revision 1;
partial data from a misconfigured real worker is rejected for this local mode, not
published as an achieved partial capability. Fixture mode may exercise valid partial
revisions with a stable immutable range and stable event ID for #11 testing.

Allocate one backend timeline event ID per accepted segment and keep it stable for
every fixture partial/final revision. Publication preserves validated text, language,
confidence and source start/end; no speculative correction or overlap-text stitcher
is added. Final context duplication, if any, is recorded as a limitation and cannot be
hidden in quality measurements. No later revision may mutate a finalized timeline
object. The backend supplies `LeaseV1.output_start_seq`; the worker alone advances the
single output allocator shared by heartbeat, stats and transcript messages. The backend
validates those worker sequences and never assigns or rewrites individual worker-output
positions. It separately owns and advances the viewer timeline sequence allocator.

### Local endpoints and permission boundary

Mount `GET /api/viewer/ws` for the exact `livecho.viewer.v1` handshake in both modes.
`GET /api/worker/ws` for `livecho.worker.v1` belongs only to later gated
`synthetic_mlx`; fixture-only implementation must not mount a worker endpoint.
WebSocket upgrade
paths are fixed; dynamic routing cannot become a source URL or worker command.
Bind only loopback. The browser uses the same origin, no wildcard cross-origin access;
the development origin is an explicit exact local allowlist. Reject browser Origin
requests on the worker endpoint. Admit only the single locally configured worker UUID
and manifest; this is a trusted-local test boundary, not production device authentication
or host attestation. Never expose these mounts on a public/network listener as part
of #9. An unexpected second worker receives no lease/audio and cannot replace authority.

There is no public HTTP start/stop/enable route. The local trusted CLI invokes backend
control through the fixed local runner; no arbitrary command execution is exposed.
All API responses use `Cache-Control: no-store`, and logs are payload-free. Static
shell hosting is #11's responsibility; backend routes do not cache transcript content.

### Viewer ordering, bounded fan-out and reconnect

At most 20 simultaneous viewer connections are admitted for the demonstration. A
21st is refused before creating a protocol domain. Each viewer has independent send
ownership capped at 32 event messages and 262,144 serialized bytes, including the
currently unsent application message. Count before enqueue; keep aggregate publication
queue storage at most 5,242,880 bytes across 20 viewers. These are normalized text,
never audio buffers. Remove body references immediately after successful delivery.

One slow viewer cannot hold a shared publication lock or block another viewer. At
either per-viewer cap or a 500 ms send deadline, remove that viewer from fan-out,
clear its queue and close its socket. If a bounded error can be sent without waiting,
use the existing `resync_required`; otherwise socket closure is sufficient. No new
wire code, retry store or replay database is introduced. Browser reconnect makes the
gap visible under #11. Terminal status/disable never waits behind transcript queues.
Under the same state owner, remove the viewer from ordinary fan-out and inspect its
fully transmitted prefix before discarding queued bodies. A terminal timeline event
may be sent only if its sequence is exactly the next position after that prefix, no
earlier event is queued or partially in flight, and sending it requires no wait behind
old text. Otherwise clear queued text and immediately close/abort the transport;
#11 hides content on disconnection. Never send a terminal event across a discarded
position, renumber it, finish flushing old text to reach it, or assume the browser will
bypass sequence validation for a status. If a write is partially in flight, cancel it
and abort the transport rather than append another frame. A failed terminal send also
closes the connection. For example, dropping queued sequences 10/11 cannot make
terminal sequence 12 valid for a viewer expecting 10; that viewer must be closed.

Backend viewer ordering uses a session/epoch timeline position and each admitted
connection's existing v1 sequence/revision state. Retain the required 256 JSON identity
records and at most 4,096 revision identities per active domain; body queue limits do
not change these protocol windows. At capacity existing updates/duplicates stay valid;
only a new identity receives `revision_capacity_exceeded` without state change.

Reconnect resumes only if cursor session/epoch/next_seq exactly matches the current
session timeline's next position and still-live corresponding revision state. A
disconnected domain's old next position is insufficient after the timeline advances. The
backend retains disconnected viewer protocol metadata for at most 10 seconds, within
the 20-domain total limit; new connections may be refused while reserved domains are
full. A reconnect may reclaim the matching domain, with no body replay claim. A cursor
that cannot identify one consistent matching domain is refused; the protocol has no
viewer connection ID to invent. Each retained domain has the same protocol state only
when its accepted event prefix is identical. A matching cursor may reuse that identical
state without treating it as viewer identity or authentication.

The 256-record window is duplicate detection, not a promise of replaying 256 event
bodies. There is no retained event-body history after successful sends. If any missing
events cannot be served, emit `resync_required`; the viewer subscribes without a cursor
and receives current session/epoch/next_seq with `cursor_resumed: false` and a visible
gap. A successful zero-loss resume keeps exact next positions; neither side silently
skips a gap. A fresh subscription receives a newly sequenced current session status,
not a fabricated historical transcript snapshot. Allocate that status on the shared
timeline and fan it out to every currently admitted viewer, so sending it to the new
viewer cannot create an unexplained gap for existing viewers. Its ready cursor is the
position immediately preceding that newly issued status. Fresh admission is also
subject to the fixture boundary below; it is not safe to join midway through revisions
of an unknown mutable object. Session/epoch replacement clears old domains, partials
and queues. #27 owns any broader lifecycle/replay design.

### Fixture partials and compatible fresh admission

The real final-only path creates each transcript event at revision 1, so a fresh viewer
may join at any current-position boundary. Fixture mode may have at most one mutable
transcript event at a time. A fresh/no-cursor subscription, including one after refused
resume, is admitted only when no mutable event is open. It must receive `ViewerReadyV1`
and the newly sequenced status atomically under the publication owner before the next
mutable event's revision 1 can be issued. Every later event identity it receives starts
at revision 1; the backend cannot deliver a previously unseen revision 2 or higher.

While a fixture partial is open, do not issue a fresh ready cursor or create a new
revision domain. Reject the subscribe using existing `resync_required` with
`retryable: true` and close; the client retries through its bounded reconnect policy.
Do not queue subscriptions or retain/replay partial bodies for them. An exact resumed
cursor whose retained domain already accepted that partial may resume under the normal
rules, provided all current-position and state checks pass.

The fixture schedule must finalize its sole mutable object within 1,000 ms of revision
1, then leave at least 2,000 ms with no mutable object before starting another. This
is a locally fixed test-stream restriction, not a wire timing rule or a real-ASR
promise. New final-only revision-1 objects and safe status events may still publish
during that admission interval. If a fixture misses its planned final deadline, fail
that fixture session and close affected viewers; do not fabricate final text or leave
a permanently closed admission window. No historical revision body store is introduced.

For example, A receives E revision 1 partial. B's fresh subscribe before E final is
refused. A may receive E revision 2 final; B subsequently joins after that final with a
fresh current cursor and receives no E revisions. B can then accept the next new
event at revision 1. The same rule applies when B must fresh-resync between E partial
and final. Do not reset E's revision, change E's identity, skip its sequence for an
already admitted viewer, or claim that B received the omitted subtitle.

### Session status and lifecycle

Use only v1 session statuses and the following local public reason mapping. Each new
status event has a fresh event ID and revision 1, preserving v1 immutable identities.

| Situation | Status | Optional reason code |
| --- | --- | --- |
| Fixture start admitted, before schedule activation | `starting` | omitted |
| Approved MLX start admitted, waiting for worker | `starting` | `no_compatible_worker` if no compatible worker is currently available |
| Local synthetic source and compatible worker ready, or fixture timeline active | `live` | omitted |
| Operator normal stop / clean EOF final drain completed | `stopping` | omitted |
| All work cleared after normal stop/EOF | `stopped` | omitted |
| Local ingest switch closed before/while running | `stopped` | `ingest_disabled` |
| Emergency/global policy disable | `stopped` | `policy_disable` |
| Session hidden/deleted | `stopped` | `session_deleted` |
| Source/worker/protocol/budget runtime failure | `failed` | one fixed payload-free reason such as `worker_failed`, `source_failed` or `protocol_failed` |

No raw exception, worker UUID or source detail enters `reason_code`. Unknown internal
failures map to generic `failed` with no reason. A missing worker cannot be called live;
this worker rule applies only to `synthetic_mlx`. Fixture readiness is the validated
text schedule and publication path; it becomes `live` without a worker. Schedule
completion emits `stopping` then `stopped`, subject to the exact-next send rule.
Stop/disable/deletion/failure invalidates its schedule and pending text immediately,
including held callbacks, with no lease cancellation or audio cleanup claim.
For `synthetic_mlx`, after 5 seconds without a compatible worker, fail the start and close source admission.
No source/audio opens while waiting for that worker. After all evidence gates pass,
initial worker connect/hello/welcome is bounded by the same 5-second start deadline.

On EOF, the final segment may drain while status remains live for at most the remaining
worker deadline and lease time. Publish an accepted final before emitting `stopping`;
once stopping is emitted no new transcript may become visible. Operator stop, disable,
deletion or failure instead closes publication/audio immediately with no final drain.
Cancellation clears every pending segment, protocol queue and source handle; revoke the
lease using existing `LeaseCancelV1`. Send current status before closure only where
the exact-next clear-send condition above holds; otherwise close/abort immediately.
Disconnection itself causes #11 to hide stale text.

Worker loss always cancels this local session. No transparent worker replacement or
automatic fresh-epoch continuation is attempted. #8 source retry similarly invalidates
continuity: its caller must cancel the active lease/session before any retry PCM can
flow, and this first vertical requires a new explicit start. It never resumes an old
input sequence, ignores a loss callback or inherits an earlier successful epoch.

## Timing and evidence

Reuse #5 meanings for `t0`, `te`, `tc`, `tp` and `tf`; first real release records
`tp = unavailable` with a reason, never substitutes final time. Record backend handle
receipt, first/last frame send completion, worker first/last receipt, provider start/end,
backend validated-transcript receipt and per-viewer enqueue/send completion. Report
segmentation wait, handle transfer, worker preparation/inference, backend validation/
publication and viewer backpressure separately. New-audio duration excludes overlap.

Only subtract times proven to share a clock domain; record the clock-domain identity
and comparison method without machine identity. Otherwise present per-process intervals
and mark cross-process one-way latency unavailable. #11 measures browser receipt-to-
render on its own monotonic clock, including chosen display delay separately. A trusted
external observer may record source-start-to-visible-render with observation overhead
and uncertainty disclosed; do not subtract unrelated browser/worker clocks.

For each authorized real run record segment count, empty/failed/missing results,
observed p50/p95 with sample counts, final latency, partial-unavailable, budget peaks,
cleanup outcomes and actual gaps. Small-run p95 is descriptive, not production tail
evidence. A first local path has no new latency qualification threshold that supersedes
#5's model gates. Fixture fan-out timing is never labeled MLX or end-to-end ASR latency.

## Interfaces and compatibility

Implementation owns `services/backend/src/livecho_backend/local_vertical/`, local
runner wiring, focused `tests/local_vertical/` and `make local-vertical-check`.
The accepted #6 CLI/terminal ownership must agree before later worker integration;
#11 viewer/browser contracts must agree before browser integration. Neither #6 nor
audio/host/model evidence blocks fixture-only backend implementation or text-only
viewer checks after #9 artifact acceptance. Exact endpoints/reason mapping above are
this Issue's proposal to be accepted, not authorization granted by another draft.
No schemas, generated types, v1 meanings, database or deployment settings change.

## Security, privacy, and data lifecycle

All audio representations obey #2/#8 bounds and no-persistence rules, including pipes,
socket buffers, device transfers, features, logs, dumps and paging. No audio digest,
temporary file or source recording is used for test evidence. Source credentials and
platform/raw data are absent. Only approved synthetic text and normalized status may
reach the local browser; real/public output remains restricted by existing policy.
Write-sink interception rejects before retaining sensitive bytes. Audit/metrics contain
only fixed reasons, counters and permitted synthetic-run metadata. No public account or
device information is collected, stored or displayed.

## Acceptance criteria

- [ ] Fixture start/live/completion/stop/disable/deletion work without a manifest,
  worker endpoint/process, audio source, decoder/provider or audio registry admission;
  a closed MLX request never starts fixtures.
- [ ] Fixture completion is reported only for the text phase. Actual synthetic MLX,
  audio ownership and real partial/latency criteria remain uncompleted.
- [ ] Text-only fixture checks, audio contract doubles and actual MLX runs are visibly
  distinct; missing model ADR/report, host/source evidence or registry keeps real run off.
- [ ] One approved synthetic memory speech stream reaches one worker and validated
  final-only timeline without platform/account/device prerequisites or audio persistence.
- [ ] Source/handle/lease budgets and terminal/overlap compatibility are independently
  evidenced; no queue, retry, timing repair or partial claim bypasses #3/#8.
- [ ] All invalid/malicious worker outputs leave ordering and public state unchanged;
  final content, segment range and event identity remain stable after publication.
- [ ] Twenty fixture viewers run for 60 seconds with 18 fast, one slow at 1 Hz and one
  stalled; per-viewer/aggregate peaks stay bounded and fast clients continue in order.
- [ ] Exact zero-loss resume, lost-event/fresh resync, metadata expiry, 20-domain limit,
  new session/epoch and 4,096-existing/4,097-new revision cases retain v1 outcomes.
- [ ] Fresh and fresh-resync attempts between fixture partial/final are refused until
  the bounded admission interval; an eligible existing-domain resume succeeds without
  an unknown-object revision gap, body replay, revised identity or skipped sequence.
- [ ] Terminal status sends only at an exact-next clear send boundary; queued 10/11
  followed by terminal 12, a partially written frame and send failure all close the
  viewer without flushing/reordering text or bypassing validation.
- [ ] Operator stop, disable, deletion, EOF drain, worker loss, source retry and expiry
  clear audio and pending publication with no late transcript or stale viewer partial.
- [ ] Evidence separates all clock domains, actual/unavailable partials, fixture versus
  MLX measurements and local verification versus owner/host/production acceptance.
