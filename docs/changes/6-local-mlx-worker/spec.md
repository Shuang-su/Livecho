# Specification: Single local MLX worker

This proposal uses accepted Livecho [protocol](../3-protocol-v1-contract/spec.md),
[benchmark](../5-mlx-benchmark/spec.md) and [audio](../8-memory-audio/spec.md) contracts.
No unmerged #9/#11 proposal is normative authority. Local limits are proposed choices
unless their accepted source is cited.

## Behavior

### Entry points and closed preparation boundary

Add `workers/mlx/` with a locally invoked Python CLI containing `check`, `preflight`
and `run`. `check` uses synthetic text/metadata doubles and creates no audio or MLX
execution. `preflight` checks the selected reviewed local configuration and existing
model assets; it never downloads, converts or infers. `run` is manual, requires all
preflight gates and a separately enabled local execution registry, and does not inherit
permission from a successful `check`. There is no automatic run on installation/import.

Local configuration has closed keys for a reviewed backend endpoint identifier, one
local worker UUID, an approved final manifest identifier and a trusted host-evidence
record identifier. The endpoint registry resolves only a loopback backend for this
Issue; arbitrary endpoint URLs, executable paths, flags, code, shell or container
instructions are not accepted from protocol input. The operator launches the worker;
the backend cannot command process creation. Exit codes distinguish success, invalid
configuration, evidence blocked, protocol failure and runtime failure with stable
payload-free reason codes; no stack trace includes content or local paths.

The allowlisted manifest must be the exact complete final inference manifest approved
under #5, with verified immutable source/converted assets, licenses and digests. Require
the actual benchmark report and owner-approved model-decision ADR before adopting it.
Neither 1.7B preference, 0.6B fallback nor an installed MLX checkpoint supplies approval.
Preparation-only receipts, placeholder hashes, incomplete reports and unapproved local
files fail preflight. Local model loading is network-disabled and remote-code-disabled.
No automatic fallback model, source host, provider implementation or dtype is permitted.

### State, handshake and authority

States are stopped, checking, connecting, ready, receiving, transcribing, stopping and
failed. One owner serializes lease/input/output state; callbacks carry an internal run
generation that cannot be mistaken for a wire epoch. Admission starts closed and opens
only after successful local preflight, exact `livecho.worker.v1` negotiation, compatible
`WorkerWelcomeV1` and a matching synthetic `LeaseV1`. Failed checks never advertise an
ASR-ready worker or acquire audio. Initial worker version is protocol-compatible 0.1.0.

The hello advertises exactly `asr.transcribe` and `protocol.binary-pcm`, and the selected
approved `ModelManifestRefV1`. The backend-issued lease/room/session/epoch, exact input
and output start sequences, immutable expiration and allowlisted manifest must match.
Only one lease and one segment may be active. No worker-issued epoch, lease extension,
credential transport or server model installation exists. Validate every JSON and binary
frame with v1 bounds/ordering/revision rules before use; rejected input changes neither
counters, transcript state nor audio ownership. A duplicate PCM sequence is discarded
unread under the accepted arithmetic replay rule and never re-transcribed.

All worker-output heartbeat, stats and transcript messages use one exact-next sequence
allocator. A valid heartbeat is sent every 2 seconds during an active lease and uses
`ready`, `busy`, `draining` or `error`; native inference cannot starve the control loop.
Heartbeat content is bounded accepted metadata, never host inventory or diagnostics.
Stats use one fresh stats ID per lease and revision one. To avoid changing a stats
window's immutable end, emit this single final stats object at normal work completion
only if the lease is still active; omit periodic stats. Its start/end and cumulative
counters describe that completed observation window. No stats are emitted after
cancellation/expiry.

This initial worker never resumes a lease after disconnect or process restart. It
clears audio and exits; any later operator restart omits the resume object and requires
a fresh backend-issued lease/epoch. There is no automatic reconnect/replay buffer.
#14/#15 own future remote worker lifecycle and scheduling.

### Segment intake and final output

Accept only s16le/16 kHz/mono messages of at most one second and the existing 56-byte
header. Assemble at most 6,000 ms / 192,000 canonical bytes for one segment. Inside a
segment require contiguous original sample positions; the first PTS of a following
segment may include the specific #8 800 ms context when its approved framing passes
the unchanged v1 nondecreasing-header test. Never repair a missing frame, rebase PTS,
pad samples or renumber sequence positions. The final input frame alone sets the
existing `END_OF_SEGMENT` bit. No independent segment-control message is introduced.

The worker assigns one segment UUID locally for its output; the backend treats it as
untrusted and binds it to the received segment. Output range is exactly the first input
sample PTS through the terminal frame's end, including accepted overlap. First release
is final-only: one `TranscriptSegmentV1` with `revision: "1"` and `is_final: true`,
or no transcript for an empty result. Never fabricate filler text, emit empty text,
reinterpret final as partial or claim prefix latency. Normalize provider output to NFC
before constructing the wire message; reject disallowed content or more than 4,096
scalars instead of silently truncating. Language/confidence are omitted unless the
approved adapter supplies valid values; no invented confidence is allowed.

The accepted final text is not stitched or rewritten by the worker. #9 may record
overlap duplication in measurements but cannot silently change finalized wire content
or immutable ranges. Any publication deduplication beyond v1 identity semantics needs
an explicit owning artifact decision before implementation.

### End-of-segment inference and ownership gate

Keep the terminal frame as an uncommitted, validated candidate while the complete
segment is processed in one bounded end-of-segment transaction. The provider sees only
reserved memory views. The final acceptance transition commits the exact expected
input position and clears every segment audio allocation; only validated text remains
eligible for output after rechecking lease/epoch/expiry/cancellation. A timeout or
cancel during processing aborts the candidate and clears audio without publishing.
Never acknowledge terminal acceptance then retain that segment as a background job.

This transaction is a proposed integration interpretation, not permission to alter v1.
Before real inference integration, an independent reviewer must confirm it against
#3/#8 prose and existing validator decisions, then executable tests must prove every
old golden result unchanged, no rejected frame side effect, terminal clearing and
correct cancellation races. `PcmLeaseState` currently clears its counted bytes when
accepting the terminal frame; that reset is not evidence that a provider freed RAM.
The worker maintains actual reservation/ownership until clear, never infers free bytes
from that counter. If a provider requires audio after accepted terminal completion,
or the accepted interpretation disallows the transaction, inference stays blocked and
a separate owner-merged protocol/artifact decision is required. A validator omission
or mock success cannot authorize the integration.

### Resource and cancellation bounds

The worker's independent hard limits are 960,000 canonical PCM bytes across receive,
assembly, provider inputs and copies; 16,777,216 all-audio bytes process-wide including
features and device transfers; and at most 30 seconds of retained media span. The lower
6-second segment cap also applies. Reserve before allocation/copy/transport admission;
borrowed views count once but cannot extend owner lifetime invisibly. Include all socket,
runtime, MLX/device and provider-internal buffers in the audited inventory. Model weights
are not audio; input-derived features/state are. Opaque or unbounded state blocks run.

No new segment may queue while transcribing. Apply transport backpressure within the
same accounted budget; a sender that continues beyond available reservation is rejected
and the lease closes. A provider call has a 10-second maximum, or remaining lease time
if shorter. Control cancellation must invalidate output and close new admission
immediately; all audio must be released within 1 second. The approved provider/host
must prove bounded cooperative cancellation or a fixed locally supervised process
termination path; inability to prove either blocks audio admission. A local supervisor
must use the recorded child lifetime/handle, never a server-supplied PID or command.
No cleanup timeout may be reported as successful erasure.

Expiry, valid `LeaseCancelV1`, disconnect, malformed input, sequence conflict/gap,
budget failure, provider failure, operator interruption and process teardown all close
admission, invalidate pending output, release audio and model-owned views, and close the
connection. A final transcript staged before cancellation is still suppressed. Repeated
cleanup is idempotent. A fatal native/provider condition leaves the worker unavailable;
there is no automatic model switch or retry using copied audio.

## Interfaces and compatibility

Implementation adds `workers/mlx/`, focused `tests/worker/` and `make worker-check` for
deterministic text/metadata contracts. Exact manual invocations and local config IDs
are recorded only when implemented and reviewed; no run command is executed by this
artifact. All wire models remain in the existing protocol package, unchanged. CUDA
remains mock/contract-only. The loopback transport is a limited local demo integration,
not a substitute for #13/#14 authentication or community-host trust controls.

## Security, privacy, and data lifecycle

Audio cannot enter disk, temp/RAM disk, logs, fixtures, hashes, traces, telemetry, cache,
queues, dumps or swap. Host/process proof against paging/crash persistence and attempted
write interception are both required before `run`; an empty output folder is insufficient.
Retain only payload-free stable errors/counters and approved synthetic text/metadata
verification results. Never persist transcript content in worker logs or model prompts.
Never receive platform credentials/locators, archive keys, raw events or download URLs.
Conforming-host cleanup does not prove a hostile community host erased disclosed PCM.

## Acceptance criteria

- [ ] `check` runs without model/audio; missing manifest, ADR/report, host evidence or
  execution authorization reports blocked before model inference/audio admission.
- [ ] Exact handshake/allowlist, lease/epoch/binding, expiry and sequence/revision cases
  retain accepted v1 outcomes; duplicates have no second inference/output effect.
- [ ] One synthetic segment produces final-only normalized text with exact source
  bounds, or explicitly no text; output counts and partial-unavailable are truthful.
- [ ] Independent terminal/overlap review and executable unchanged-fixture evidence
  precede actual inference; all real allocations remain charged until release.
- [ ] Slow provider/input, overflow, cancellation, expiry, disconnect, native failure
  and teardown prevent late output and satisfy bounded cleanup without persistence.
- [ ] Manual real MLX evidence is separate from doubles, uses owner-approved #5 model
  decision and host/source evidence, and records measured outcomes without CUDA claims.
