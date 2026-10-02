# Specification: Bounded RAM audio and supervised FFmpeg

This proposed specification implements the owning Issue's synthetic path. It preserves
accepted Issues #2/#3 and does not enable Issue #7's platform capabilities. All numeric
choices below are local design decisions unless an accepted-artifact source is named.

## Behavior

### Controlled input and fixed decoder

Expose one backend-internal `MemoryAudioSource` contract with `open`, bounded `read`,
and idempotent `close`. `open` binds one opaque room, immutable session, attempt ID,
`origin=synthetic`, and exact source format. There is no URL, pathname, command,
container, arbitrary option, credential, or extensible metadata field. The source
provides freshly generated samples only; no input audio fixture or filesystem reader.

Initial source formats are PCM s16le at exactly 16,000 Hz mono or 48,000 Hz stereo.
The latter exercises decoding/downmix/resampling without admitting an encoded-media
parser. Each source read covers 20 ms: 320 mono samples/640 bytes, or 960 stereo
sample pairs/3,840 bytes. The read request is issued only after budget reservation.
The producer fills an owned bounded writable view; it cannot return an oversized
allocation first. Partial sample groups, NaN timing, zero/negative duration, missing
format, or unrecognized fields fail before admission. End of input is an explicit EOF,
not a zero-byte chunk pretending to be audio.

Each chunk has an exact next local `chunk_index`, integer start sample offset, sample
count, and immutable format. Offsets are contiguous inside an attempt; duplicates,
gaps, reordered chunks, format changes, and a producer advancing after a closed gate
terminate the attempt. Local indices are not protocol sequence numbers. Convert to
canonical PTS using integer rational sample counts; all allowed chunk durations land
on exact milliseconds. Output must contain exactly the expected resampled duration;
unexpected excess, unaccounted resampler tail, or invalid PTS is a failure.

Use one pinned, license-reviewed FFmpeg executable/build with only the required raw
PCM demux/decoder, downmix/resampler and raw PCM output capabilities. Its path is
trusted local configuration verified by executable SHA-256 and version at preflight;
the source and future workers cannot supply it. Invoke with a fixed argument array,
no shell, stdin `pipe:0`, stdout `pipe:1`, no video/subtitle/data mapping, and explicit
`pcm_s16le`, 16,000 Hz, one output channel. Disable interactive input, logging/report
files and statistics; stderr is discarded rather than retained as arbitrary decoder
diagnostics. Set a 4,096-byte pipe I/O block size. Raw PCM format/rate/channels must
be selected before input; no probing or auto-detection. Only `pipe` is allowed as an
I/O protocol. No `file`, `cache`, `async`, network, segment/HLS, or seekable output.

The source formats and fixed arguments are closed data, not a general decoder service.
Issue #7 cannot later hand a playback URL or arbitrary encoded stream to this interface.
Admitting encoded formats requires that owning artifact to define exact codecs,
duration evidence before retention, internal allocation limits, SSRF/rights controls,
and compatibility tests while retaining all caps. This is an explicit scope boundary,
not a promise that raw-PCM tests prove encoded-network safety.

### Canonical accounting and ownership

Canonical PCM is signed 16-bit little-endian, 16,000 samples/s, mono: 32,000 bytes/s.
Use one synchronized reservation ledger per room/session and a separate ledger for an
active worker lease. Validate metadata and reserve capacity before source read, pipe
write/read, allocation, copy, retained view, or consumer handoff. A borrowed view refers
to the same allocation and counts once physically; each copied allocation counts again.
Shared ownership delays release and cannot make bytes disappear from the ledger.

| Resource | Hard canonical byte reservation |
| --- | ---: |
| Primary ring (16 seconds maximum) | 512,000 |
| At most one handed-out segment, including left context (6 seconds) | 192,000 |
| Parent canonical read/assembly scratch | 32,000 |
| Canonical pipe/transport allowance attributed to session | 64,000 |
| VAD/pre-roll working PCM | 12,800 |
| Explicit retained context if copied rather than shared | 25,600 |
| Remaining reserve for measured canonical copies/internal state | 121,600 |
| Total backend room/session ceiling | 960,000 |

These are reservations, not permission to keep consumed data. Shrink/release immediately
after use. A 30-second ring plus copies is invalid; the lower 16-second primary ring
leaves room for the other required owners. Shared views cannot expand the allowed media
span. For every component, the union of retained audio intervals must fit within
`newest_end - oldest_start <= 30,000 ms`; unknown-duration input is never buffered.

All representations, including source-format PCM, decoder/resampler working state,
kernel pipes, Python copies, conversion features and transport buffers, also count
toward each process's 16,777,216 audio-byte ceiling. Conservatively attribute a shared
kernel pipe's full configured capacity to both endpoints. No process may exclude its
child's buffers from the child's own accounting. The parent ledger reserves at most
4 MiB for noncanonical audio, and a decoder allocation inventory must bound its total
audio state at most 8 MiB; neither changes the 960,000 canonical or 30-second limits.
Unused headroom is not a second audio queue. Model memory is outside Issue #8.

Before enabling audio, pin the FFmpeg build and record an audited allocation upper
bound for this exact raw-input/resampler/output configuration, pipe capacities, runtime
buffer sizes, and every copy. Combine preallocated/reserved buffers with a hard failure
on any unaccounted allocation. RSS sampling or `-blocksize` alone is not a hard bound
on decoder internals. If the platform/build cannot enforce or prove that inventory,
preflight fails with `audio_budget_unverified`; do not weaken the invariant or claim
observed low RSS is proof. There are no standby PCM recipients or multiple active rooms.

### VAD and segmentation

The first deterministic VAD is a locally authored energy detector, not a downloaded
model: evaluate consecutive 20 ms/320-sample canonical frames. A frame is speech when
`sum(sample^2) >= 320 * 32768^2 / 10000` (-40 dBFS RMS). Accumulate with an integer
type that cannot overflow. Exactly three consecutive speech frames trigger onset;
include up to 200 ms of pre-roll, limited to the current attempt. Isolated shorter
bursts are discarded as `below_onset`. Leading/trailing silence is measured and cleared,
never accumulated to fill a ring. This VAD's synthetic correctness is not a claim of
human-speech/noise accuracy; an algorithm change needs its own artifact evidence.

On every silence/EOF closure, reset VAD onset/pre-roll state and clamp subsequent
pre-roll start to at least the last emitted segment's end. Samples already handed out
cannot enter later pre-roll. A rapid onset after a short last frame may have less than
200 ms pre-roll. Only the explicit max-duration context rule below may retain earlier
samples; it does not permit ordinary pre-roll to rewind a prior wire header.

After onset, close on 25 consecutive nonspeech frames (500 ms), explicit EOF, or
6,000 ms of total segment samples, whichever comes first. The total includes pre-roll,
silence, and any left context. Keep trailing silence through its 500 ms close point.
Speech returning before 500 ms resets the silence counter. Boundary equality closes
at that exact sample; it does not wait for an extra frame. No segment exceeds 96,000
samples/192,000 bytes. A partial frame at EOF is malformed input, never zero-padded.
At clean EOF, emit a shorter already-open segment only if it has new speech; no onset
means no segment. All remaining scratch/pre-roll is then cleared.

For continuous speech cut by the 6-second cap, retain exactly the last 800 ms/12,800
samples as left context for the next segment, charged to the same session budget. The
next segment has at most 5,200 ms of new audio. Its `start_pts` includes context,
`new_start_pts` equals the previous `end_pts`, and `end_pts` remains on the original
media clock. Do not carry context across silence closure, EOF, attempt failure, source
replacement, cancellation, disablement, or session end. Context without new speech is
never emitted as a standalone segment. Overlap is not counted as newly processed time.

### Segment interface and protocol boundary

Return one `SegmentHandle` at a time with immutable room/session/attempt binding,
local segment index, `start_pts`, `new_start_pts`, `end_pts`, canonical sample count,
`left_context_samples`, close reason (`silence`, `max_duration`, `eof`), format, and
a bounded read-only owned memory view. A handle expires 1,000 ms after handoff unless
released sooner; consumer access after release/cancel/expiry is rejected and cannot
resurrect its backing storage. Consumer copies require explicit ledger reservations.
No retained list of segments, hidden callback queue, or background audio retry exists.

This is a completed-segment interface; it promises final-segment delivery, not partial
text during collection. A provider benchmark with incremental prefix access has a
different scope. Issue #9 may use this interface for its first final-caption path and
must report actual/unavailable partial timings. It cannot present a benchmark's early
partial result as this pipeline's behavior. Any incremental runtime view or transport
requires an explicit owner-merged artifact addressing ownership and immutable transcript
ranges before implementation; no protocol field or PTS workaround is implied here.

Issue #9 remains responsible for binding a synthetic active `LeaseV1`, the manifest,
epoch and exact-next wire sequence through the accepted validators. This module never
assigns an epoch or rewinds/resets a sequence to hide a loss. Keep immutable segment
ranges for subsequent transcript revisions; they cannot grow between partial/final.
Local handles do not authorize unknown fields in any wire model.

The proposed v1 integration emits each completed segment as up to one-second binary
messages with original PTS, exact sample counts and only the final message carrying
`END_OF_SEGMENT`. A forced 6-second segment emits six full one-second messages.
For a segment starting at 0, their header PTS values are 0/1000/2000/3000/4000/5000;
the next segment's 800 ms context begins at 5200, so header starts stay nondecreasing
without changing the samples' media positions. Never split the final forced segment
into 20 ms wire frames and then send an earlier context PTS. Short terminal/silence
segments do not carry context forward. Context is retained only at the backend after
handoff; the worker still clears its segment PCM on the accepted end flag.

This framing must pass independent specification review and executable golden/validator
compatibility tests before Issue #9 treats overlap delivery as supported. Test original
PTS, every frame size, the context interval, worker/session aggregate copies, terminal
clearing and stable errors. If the accepted protocol interpretation disallows this
overlap, block that integration and require an owner-merged protocol Issue; do not
rely on a validator omission, rebase PTS, drop required overlap silently, or change
`epoch`/`seq`/`revision`. Issue #8's local segmentation contract can be verified alone.

### State, overload, and reconnect

States are `idle`, `starting`, `running`, `backpressured`, `retry_wait`, `stopping`,
`stopped`, and `failed`. One owner serializes source, ledger, handle and child-process
transitions. Admission closes synchronously before any teardown await. A generation
token internal to the attempt invalidates every pending read/callback; it is not wire
`epoch` or durable safety generation.

| Trigger | Required transition and outcome |
| --- | --- |
| Start with valid synthetic binding and verified budgets | `idle -> starting`; reserve and spawn one decoder; first canonical output within 2 seconds, then `running` |
| Consumer has a handle, or free canonical reserve below next complete frame | Enter `backpressured`; stop requesting source reads, pause pipe admission, permit no new audio allocation |
| Consumer releases and reservation succeeds within 500 ms | Resume `running`; same source offsets, no dropped/renumbered frame |
| Backpressure persists for 500 ms, media window would exceed 30 seconds, or handle expires | Fail attempt with `consumer_slow`/`audio_budget_exceeded`; clear all audio, count lost unique media intervals, no segment reported successful |
| Producer sends despite pause, metadata invalid, or unaccounted allocation | Terminal `failed`; no automatic retry |
| No source progress for 2 seconds outside permitted pause | Abort attempt as `input_stalled`; eligible only for bounded synthetic reconnect below |
| FFmpeg nonzero exit, pipe error, or start timeout | Abort attempt as `decoder_exit`/`decoder_pipe`/`decoder_start_timeout`; eligible only for bounded synthetic reconnect |
| Clean EOF | Close an already-open valid segment, wait at most the 1-second consumer deadline, then `stopping -> stopped`; no reconnect |
| Cancel, disable, matching denylist, lease/session end, or backend shutdown | Immediate gate close, invalidate handles, clear data, terminate/reap; no final segment/publication/retry |

Every attempt failure first terminates/reaps its decoder and releases all its audio.
Only a synthetic source factory explicitly declaring restartability may receive two
automatic reconnect attempts per session, after 250 ms and 1,000 ms. Recheck admission
and cancellation before and after each delay. The budget never resets after a successful
period; exhaustion is terminal. Reconnect starts a fresh attempt/source offset and tells
Issue #9 that continuity is broken before any new PCM. A caller must create a fresh
non-resumed lease with a higher backend-issued epoch, or a new session, before sending
it to a worker. The module cannot silently resume a lost worker sequence.

There is no live-source network retry in this Issue. Issue #7 must own later eligibility,
rights, disable-state and source reacquisition checks, with no cached signed URL. Normal
offline/ended state is not a denylist mutation. Scope-bound stop affects only the bound
session; an unknown safety scope is returned to the backend's global safety owner.

### Teardown and parent death

Close source/segment admission first, invalidate pending tasks/handles, cancel reads and
timers, close pipe descriptors, clear every owned audio allocation, terminate the decoder
process group, wait at most 500 ms, then kill and reap within a further 500 ms. Retrying
cleanup is safe and cannot reopen a source, buffer, lease, or process. A reap failure is
`decoder_reap_failed`; keep admission closed and block every replacement process until
the old identity is proved dead. Clear ownership even when a consumer is uncooperative.

Use an independently supervised per-session watchdog with a parent-liveness pipe and
the recorded child process-group identity. It owns no audio and has no serving authority.
EOF on the liveness pipe, backend abrupt exit, or loss of the parent requires the same
bounded TERM/KILL/reap sequence. Ensure close-on-exec and no inherited copies keep the
liveness pipe falsely open. Decoder stdin/stdout also close on parent death; test both
mechanisms rather than assuming signal handling runs after SIGKILL. Watchdog death
must close source admission through its monitored exit and trigger parent cleanup.
PID reuse cannot target a later process: bind supervision to the created child handle
and process lifetime, not a stale PID read from disk. No PID/audio recovery file exists.

Backend restart starts with no resumed audio state, no surviving child, and no accepted
handle. It does not claim to recover dropped media from storage. Abrupt decoder/parent/
watchdog termination, repeated cleanup, and all pairwise cancellation/retry races must
be tested under a trusted local supervisor before acceptance.

## Interfaces and compatibility

Implementation belongs under `services/backend/src/livecho_backend/audio/` and focused
tests under `tests/audio/`. Introduce `make audio-check` for deterministic memory-source,
segmenter, budget, supervision, and no-persistence checks. The Make target must use
synthetic in-memory generation only, with an explicit skip/fail distinction for a
missing approved FFmpeg build; required decoder acceptance never reports a skip as pass.
No HTTP/WebSocket endpoint, remote process control, new database, deployment setting,
generated protocol edit, or source/model download is added by this Issue.

## Security, privacy, and data lifecycle

No audio may enter files, temp directories, RAM disks, swap, dumps, caches, fixtures,
snapshots, logs, traces, databases, queues, object stores or hashes. Disable process
core dumps, decoder reports and payload logging. A supported host must prove audio
allocations cannot page or enter crash collection; inability to do so fails audio
preflight. An encrypted swap or filesystem is still persistence. Host/process-level
evidence is needed in addition to application writer interception.

Allowlisted metrics are current/peak canonical and all-audio reserved bytes, retained
media span, pause/stall duration, decoder/retry/reap outcomes, and dropped unique media
milliseconds by stable reason. Drop duration is the union of discarded new-audio
intervals, never overlap counted twice; unknown duration is reported separately as
`unmeasurable_input`, not zero. Exclude routine trimmed silence from failed speech but
report its count separately. Session metric labels are ephemeral attempt IDs in memory;
retained aggregate metrics omit room/session identifiers, media bodies and local paths.
Detailed exception/FFmpeg stderr output is never retained.

No public source or real community PCM is enabled. Worker erasure remains a conforming
implementation claim, not evidence that a hostile host erased disclosed data.

## Acceptance criteria

- [ ] Controlled synthetic input converts both exact formats with sample-accurate PTS.
- [ ] Silence at 480/500/520 ms, exact 6-second splits, 800 ms context, EOF and onset
  boundaries have independently computed expected metadata and RAM-only sample checks.
- [ ] Ledger tests reject before allocation at all byte/media limits and count every
  copied/view/pipe/decoder owner; opaque internals fail preflight.
- [ ] Independent overlap/protocol review and unchanged v1 fixtures precede integration.
- [ ] A short silence-closed final frame followed by rapid onset cannot reuse pre-roll
  before its emitted end or move the next wire header PTS backward.
- [ ] Slow/hostile producers/consumers, stalls, budget exhaustion, failures and every
  retry/cancel race are bounded and report actual loss without sequence/PTS repair.
- [ ] EOF/cancel/timeout/disconnect/disable/denylist/session end and parent restart/SIGKILL
  all invalidate handles, clear audio and prove no surviving decoder/watchdog.
- [ ] Attempted-write interception and temp/log/database/storage/cache scans pass for
  normal and failure runs; no audio test artifact or digest is retained.
- [ ] `make verify`, `make audio-check`, approved FFmpeg inventory and host evidence pass;
  missing runtime/hardware evidence is explicitly pending, never claimed by this PR.
