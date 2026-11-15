# Specification: Local MLX worker CLI (fixture + gated real)

This specification implements owning [Issue #6](https://github.com/Shuang-su/Livecho/issues/6)
using accepted [protocol](../3-protocol-v1-contract/spec.md),
[benchmark](../5-mlx-benchmark/spec.md), [audio](../8-memory-audio/spec.md), and
[local caption](../9-local-caption-vertical/spec.md) contracts. Closed draft PR #40 is
prior art only—not approved scope. Where #40 proposed `check`/`preflight`/`run` and a
final-only-only product, this artifact follows the Issue CLI and separates fixture
partial/final truth from real-provider capability.

## Behavior

### CLI surface and installation

Package lives under `workers/mlx/`. The operator installs with `uv tool` or `uvx` so the
entry point is available on Apple Silicon and on Linux CI for fixture/doctor checks.
There is **no** automatic run on install or import.

Closed command set (exactly these names; no silent rename to `check`/`preflight`):

| Command | Purpose | Audio / MLX |
| --- | --- | --- |
| `enroll` | Write/update closed local configuration: reviewed loopback backend endpoint id, local worker UUID, approved final-manifest id, trusted host-evidence id. Does **not** create public accounts, community devices, or cloud enrollment. | None |
| `doctor` | Diagnose install, platform, config completeness, presence of required evidence artifacts and (when present) local asset digests. Never downloads, converts, or infers. Exit codes distinguish ok / invalid config / evidence blocked. | None |
| `benchmark` | Read and validate linkage to the **existing** #5 report and owner model-decision ADR; optionally invoke the blocked #5 CLI which itself exits `blocked_evidence` until gates pass. Does **not** score CER/RTF, select a model, or invent ADR content. | None in CI; trusted-host measurement remains #5's gate |
| `run` | Manual only. Requires doctor-equivalent gates **plus** a separately enabled local execution registry. Opens one synthetic lease path. | Fixture doubles: no real audio/MLX. Real path: only after all evidence gates |

Exit codes are stable and payload-free: success, invalid configuration, evidence blocked,
protocol failure, runtime failure. Stack traces must not include transcript text, audio,
or absolute local model paths in retained logs.

Local configuration accepts only closed keys. Arbitrary endpoint URLs, executable paths,
shell/container instructions, download URLs, and free-form metadata from protocol input
are rejected. The operator starts the process; the backend never commands process create.

### Capability truth: fixture partials vs real providers

Protocol v1 already supports `TranscriptSegmentV1` with `is_final` false/true and
immutable range rules. Issue #6 requires fixture transcription to produce **legal
partial and final** events. Accepted #9 states fixture mode may exercise valid partial
revisions, while the first real `synthetic_mlx` release accepts **final-only** revision 1
and rejects unexpected real partials as misconfiguration—not as achieved partial support.

Therefore:

1. **Fixture/contract provider** (default for `make worker-check` / Linux CI): emits at
   least one in-place partial revision then a final revision for a synthetic segment,
   with stable `segment_id`, stable immutable `start_ms`/`end_ms`, NFC text ≤ 4,096
   scalars, and exact-next output `seq`. Old revision rejection and final immutability
   must match #3 validators. Fixture text is **not** speech recognition evidence.
2. **Real MLX provider** (trusted host only): may ship **final-only** until independent
   evidence proves provisional prefixes for the approved adapter. It must advertise
   `partial_unavailable` in doctor/run diagnostics and must **never** invent intermediate
   text, empty fillers, or prefix-latency claims. Fabricating partials to “satisfy” the
   Issue checkbox is forbidden.
3. Promoting a real provider from final-only to partial-capable requires recorded #5-style
   measurements and an owner-visible evidence update; it is not implied by fixture greens.

### Preparation and model allowlist

The allowlisted manifest must be the exact complete final inference manifest approved
under #5, with verified immutable source/converted assets, licenses, and digests. Require
the actual benchmark report and owner-approved **model-decision ADR** before real `run`.
Neither “prefer 1.7B”, “fallback 0.6B”, nor “an MLX file exists on disk” is approval.
Preparation-only receipts, placeholder hashes, incomplete reports, and unapproved local
files fail doctor/`run` closed. Local model loading (when eventually authorized) is
network-disabled and remote-code-disabled. No automatic fallback model, source host,
provider implementation, or dtype is permitted.

### State, handshake, and authority

States: `stopped`, `enrolling`, `diagnosing`, `connecting`, `ready`, `receiving`,
`transcribing`, `stopping`, `failed`. One owner serializes lease/input/output; callbacks
carry an internal run generation that is not wire `epoch`. Admission starts closed and
opens only after successful local gates, exact `livecho.worker.v1` negotiation,
compatible `WorkerWelcomeV1`, and a matching synthetic `LeaseV1` (`audio_origin:
"synthetic"`). Failed doctor/gates never advertise ASR-ready status or acquire audio.

Hello advertises exactly `asr.transcribe` and `protocol.binary-pcm` plus the selected
approved `ModelManifestRefV1`. Backend-issued lease/room/session/epoch, input/output
start sequences, expiry, and allowlisted manifest must match. Only one lease and one
active segment. No worker-issued epoch, lease extension, credential transport, or server
model installation. Validate every JSON/binary frame with v1 bounds/ordering/revision
before use; rejected input changes neither counters, transcript state, nor audio
ownership. Duplicate PCM sequences are discarded unread under accepted replay rules.

Worker-output heartbeat, stats, and transcript share one exact-next sequence allocator.
Heartbeats every 2 s while leased use `ready`/`busy`/`draining`/`error` and cannot be
starved by inference. Stats: one fresh stats id per lease, revision one, emitted at
normal completion only if the lease is still active; omit after cancel/expiry.

This initial worker never resumes after disconnect or process restart. It clears audio
and exits; a later operator start omits resume and needs a fresh lease/epoch. No
automatic reconnect or replay buffer. #14/#15 own remote worker lifecycle later.

### Segment intake and transcript construction

Accept only s16le/16 kHz/mono binary messages ≤ 1 s with the existing 56-byte header.
Assemble at most 6,000 ms / 192,000 canonical bytes for one segment. Contiguous original
sample positions inside a segment; a following segment's first PTS may include the #8
800 ms left context only when that framing passes unchanged v1 nondecreasing-header
tests. Never repair missing frames, rebase PTS, pad samples, or renumber sequences.
Only the terminal input frame sets `END_OF_SEGMENT`.

The worker assigns one local segment UUID; the backend treats it as untrusted and binds
it. Output time range is exactly first input PTS through terminal end (including accepted
overlap). Normalize provider text to NFC; reject disallowed content or > 4,096 scalars
instead of truncating. Language/confidence omitted unless the approved adapter supplies
valid values—no invented confidence.

Fixture path: emit partial then final as above. Real final-only path: one
`TranscriptSegmentV1` with `revision: "1"` and `is_final: true`, or no transcript for an
empty result. The worker does not stitch or rewrite accepted finals for overlap; #9 may
record duplication as a measurement limitation.

### End-of-segment inference and ownership gate

Keep the terminal frame as an uncommitted validated candidate while the complete segment
is processed in one bounded end-of-segment transaction. The provider sees only reserved
memory views. Before any terminal commit/ack, the same state owner atomically revalidates
run generation, active lease/epoch, expected input position, unexpired lease, and
absence of cancellation/closing. **Every segment audio allocation must be proved released
before that commit**—a protocol counter reset is not RAM proof. Failed recheck or release
aborts with no sequence/PTS commit or output and keeps admission closed. An old
completion cannot resurrect cleared state or reopen a restarted generation. Timeout or
cancel during processing aborts without publishing. Never acknowledge terminal acceptance
then retain the segment as a background job.

This transaction is an integration interpretation, not permission to alter v1. Before
real inference, independent review against #3/#8 prose plus executable tests must prove
old goldens unchanged, no rejected-frame side effects, terminal clearing, and cancel
races. If a provider needs audio after terminal acceptance, or accepted interpretation
disallows the transaction, inference stays blocked pending an owner-merged decision.

### Resource and cancellation bounds

Independent hard limits: 960,000 canonical PCM bytes across receive/assembly/provider
copies; 16,777,216 all-audio bytes process-wide including features and device transfers;
≤ 30 s retained media span; ≤ 6 s per segment. Reserve before allocation/copy/transport.
Borrowed views count once but cannot extend owner lifetime invisibly. Opaque or unbounded
provider state blocks real `run`. Model weights are not audio; input-derived features are.

No new segment queues while transcribing. Provider call max 10 s or remaining lease time.
Control cancellation invalidates output and closes admission immediately; all audio must
be released within 1 s. Approved provider/host must prove cooperative cancellation or a
fixed locally supervised termination path; inability blocks audio admission. Cleanup
timeouts are never reported as successful erasure.

Expiry, valid `LeaseCancelV1`, disconnect, malformed input, sequence conflict/gap, budget
failure, provider failure, operator interrupt, and teardown all close admission,
invalidate pending output, release audio, and close the connection. A transcript staged
before cancellation is still suppressed. Cleanup is idempotent. Fatal native/provider
conditions leave the worker unavailable—no automatic model switch or audio retry.

## Interfaces and compatibility

- Code (future implementation PR only): `workers/mlx/`, `tests/worker/`,
  `make worker-check` (fixture/contract; must not skip-as-pass real gates), and a
  separately documented trusted-host invocation recorded in evidence when run.
- Wire models remain in the existing protocol package **unchanged**. No new `epoch` /
  `seq` / `revision` semantics.
- CUDA remains mock/contract-only. Loopback transport is a local demo integration, not
  #13/#14 community trust.
- This documentation PR adds **only** the four Markdown files under
  `docs/changes/6-local-mlx-worker/`.

## Failure modes and disable path

| Condition | Outcome |
| --- | --- |
| Missing enroll config / invalid keys | `enroll`/`doctor`/`run` fail closed; no ready advertise |
| Missing #5 report, ADR, host evidence, or empty execution registry | `doctor`/`benchmark`/`run` report evidence blocked; no audio/MLX |
| Non-Apple Silicon attempting real MLX | Explicit refusal before load |
| Unknown model / digest mismatch / non-synthetic lease | Refuse before audio admission |
| Protocol violation / cancel / expiry during inference | Suppress output; clear audio; close |
| Real provider without proven partials emitting partials | Rejected by local #9 policy; not claimed as capability |

## Security, privacy, and data lifecycle

Audio must not enter disk, temp/RAM disk, logs, fixtures, hashes, traces, telemetry,
cache, queues, dumps, or swap. Host/process proof against paging/crash persistence plus
attempted-write interception are required before real `run`; an empty folder is not
proof. Retain only payload-free stable errors/counters and approved synthetic
text/metadata verification results. Never persist transcript content in worker logs or
model prompts. Never receive platform credentials/locators, archive keys, raw events, or
download URLs. Conforming-host cleanup does not prove a hostile host erased PCM.

## Acceptance criteria

- [ ] CLI names are `enroll`, `doctor`, `benchmark`, `run`; installable via `uv tool` /
  `uvx` documentation in the implementation PR; no silent rename to `check`/`preflight`.
- [ ] `doctor` and fixture `worker-check` run without model/audio; missing manifest, ADR,
  report, host evidence, or execution authorization blocks before inference/audio.
- [ ] Fixture path produces legal partial then final events with immutable ranges, exact
  seq/revision behavior, and honest “not speech recognition” labeling.
- [ ] Real path remains final-only (or proven partial later) without fabricating partials;
  unknown models, unknown job types, and non-Apple-Silicon MLX starts refuse explicitly.
- [ ] Handshake/allowlist/lease/epoch/sequence/revision cases retain accepted v1 outcomes;
  duplicates have no second inference effect.
- [ ] Independent terminal/overlap review and unchanged golden fixtures precede real
  inference; allocations stay charged until actual release.
- [ ] Cancel/expiry/disconnect/restart prevent late output; process exit clears audio;
  logs contain no raw audio representation.
- [ ] Manual trusted-host MLX evidence is separate from doubles, uses owner-approved #5
  decision and #8 host/source evidence, and never claims CUDA or production readiness.
