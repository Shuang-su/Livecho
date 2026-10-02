# Specification: M3 Ultra MLX benchmark and model decision

Normative requirements below are proposed Livecho decisions. Vendor facts are limited
to the primary source register in `evidence.md`; vendor benchmark claims are not local
measurements. Artifact approval must precede implementation and the first scored run.

## Behavior

### Candidates, provenance, and acquisition

The only candidates are `Qwen/Qwen3-ASR-1.7B` and `Qwen/Qwen3-ASR-0.6B`, converted
for local MLX inference using affine 8-bit groups of 64. Quantize supported linear
and embedding weight matrices; retain unsupported tensors in their original dtype and
record the exact tensor-name/dtype/quantization map. No calibration audio is permitted.
Both candidates must use the same reviewed conversion and provider implementation.
An unclassified tensor, missing conversion rule, or incompatible architecture blocks
that candidate before scoring; it does not silently substitute a different model.

A reviewed preparation manifest authorizes only acquisition and local conversion. It
contains the canonical repository, full immutable source revision, every source asset's
path/size/SHA-256, source and conversion licenses/notices/use scope, tokenizer/config
provenance, conversion implementation revision and dependency lock digest, quantization
map, and owner/reviewer/date. It contains no invented converted-asset digest. After
source verification, conversion may load source weights solely to convert them in the
model-only cache; no inference or audio is allowed under this preparation authority.
Compute the resulting asset digests and obtain owner/reviewer approval of a separate
final inference manifest that includes the preparation-manifest digest, converted-asset
path/size/SHA-256 and notices. Only that complete final manifest may be allowlisted for
inference. Code, weights, tokenizer, converter, and test-source rights are separate
approvals. No placeholder digest is allowlisted.
The protocol-facing projection remains exactly the Issue #3 `ModelManifestRefV1`
tuple; its SHA-256 identifies canonical JSON of the complete local manifest excluding
that self-digest. There is no protocol URL, path, execution field, or download command.

Use two explicit operator-selected source modes, `huggingface` and `modelscope`, each
mapping the canonical model to an approved first-party repository and immutable
revision. Record mirror-to-canonical asset digest equality; missing parity blocks that
mirror. Never fall back automatically between hosts. Fixed repository/file allowlists
exclude executable remote code, datasets, samples, and audio. Local loaders use
verified files with network and remote-code loading disabled.

Model download is a separate explicit preparation action. Its cache is outside Git,
contains model assets only, supports resumable partial transfers, and exposes only
asset label, bytes/total, percent, retry count, and outcome. Verify length and SHA-256
before atomic promotion; a changed revision invalidates a partial transfer. Bound an
attempt by a 60-second no-progress timeout, three attempts, and 1/2-second delays;
HTTP authentication/permission or integrity failure stops immediately. Never log
headers, tokens, signed URLs, arbitrary server text, or local user paths. An interrupted
model preparation may resume later; an audio input may not.

Qwen's official cards identify transformers/vLLM interfaces, not verified MLX
compatibility. The implementation must supply an independently authored in-process
MLX adapter and exact dependency/provenance evidence; it cannot treat the cards or a
community model label as proof. Do not add a third-party adapter without a reviewed
artifact amendment covering its exact version, license, interfaces, and exposure.

### Corpus and repeatability

Freeze a text-and-metadata corpus manifest before scoring. It has 60 distinct
12-second scripts, 12 per primary stratum: clean Mandarin, Chinese proper names,
numbers/units/dates, Chinese-English code switching, and continuous speech without a
500 ms pause. Each script has at least 30 normalized reference characters and explicit
target-span annotations for names/numbers/English. Use at least three consenting adult
speakers, balanced across strata. Every base rendition also has a paired noise condition:
deterministic in-memory generated broadband noise at 10 dB SNR relative to the speech
RMS (silence excluded by reference timing). Noise seed/algorithm and reference time
annotations are non-audio metadata. They must not encode speech or an audio waveform.

Each approved source record names publisher/speaker consent evidence, immutable
non-audio source item/version, permitted transient processing/reference-text/result
retention, expiry/revocation, and reviewer. A source must deliver a reproducible
rendition into a bounded memory stream without HTTP/dataset/media cache, temporary
file, downloader, or audio digest. A licensed upstream service may retain its own
recording; Livecho may not copy it to local storage. A live re-reading can be reported
as exploratory but is not identical-source repeatability evidence. Missing qualified
sources blocks the scored benchmark; synthetic tones test machinery, not CER.

Run clean and paired-noise conditions separately for every script, model and window
in `{1, 2, 4, 6}` seconds. Three independent process repetitions per model/window
are mandatory, in fixed alternating model order per repetition. The source order is
sorted script ID. Reacquire the same approved rendition for each pass; never keep a
corpus in RAM past 30 seconds. Scored decoding is batch size 1, deterministic greedy
decoding, no prior transcript prompt, no external language model, no forced aligner,
and no language hint. Record all effective settings and the provider's bounded output
token limit (512 per segment); hitting that limit is a failed sample, not success.

### Timing and output semantics

Use one process monotonic clock, expressed in integer nanoseconds. Replay in real time
from source PTS; reject missing/non-monotonic timing. Instrument these observations:

| Symbol | Exact observation |
| --- | --- |
| `t0` | First sample of the segment's new, non-overlap speech becomes eligible at the harness input |
| `te` | Last new speech sample becomes eligible, from the approved reference annotation |
| `tc` | Segment closes after its chosen window, silence policy, or EOF |
| `ti_first` | First provisional provider call begins after that call's input preparation, potentially before segment closure |
| `ti_final` | Final provider call begins after `tc` and its own input preparation |
| `tp` | First nonempty normalized readable provisional text is delivered by the adapter |
| `tf` | Complete final text is delivered after MLX evaluation/synchronization |

Record start/end times for input preparation and synchronized execution of every
provisional and final call. Report segmentation wait `tc - te`, per-call preparation
duration, final queue wait from `tc` until final preparation starts, first-readable
partial `tp - t0`, provider-first-text `tp - ti_first`, provider-final
`tf - ti_final`, and speech-end-to-final `tf - te`. Continuous forced splits have
`te = tc`. Provisional inference is eligible each time another 250 ms of new audio
arrives within the selected window, with no concurrent calls. If the provider is busy,
coalesce missed ticks into one latest eligible prefix after it becomes idle; do not
queue snapshots. Count missed opportunities and evaluated prefixes in the report.
At `tc`, abandon any unstarted provisional prefix and prioritize final preparation
after any already-running call completes. Its wait remains measured. A provider
that only returns final text must report partial unavailable and fails the partial
gate; it must never relabel final as partial. Intermediate text and all revisions
are evaluated in RAM and discarded after metrics are computed.

Per-segment RTF is the sum of every call's preparation and synchronized execution
durations divided by that segment's newly consumed non-overlap audio duration. These
are disjoint execution intervals, never `tf - ti_first`, which includes replay waits.
Include every provisional and final call and preprocessing, exclude source
replay waits, network, download, and model load. Report per-call RTF too, with overlap
duration explicitly identified; overlap cannot inflate the decision denominator.
Measure complete provider work by forcing lazy evaluation and synchronizing before
closing timers. Report queued wait separately, even when zero.

Cold means a new process loading verified cached weights with no model instance or
warmup; record load start to ready, first inference, and first-final from process start.
Do not claim OS page-cache coldness or flush host caches. Warm means the same loaded
process after three unscored synthetic warmups at that window shape, whose audio is
immediately released. Cold and warm samples are never pooled. Each repetition scores
all scripts; its first scored script additionally supplies the cold observation before
warmup. Keep the per-observation metric rows, count, and nearest-rank p50/p95
(`sorted[ceil(p*n)-1]`) per model/window/condition/repetition. The RTF/segmentation/
partial/final populations contain one row per scored segment; preparation population
contains every scored call. A sample missing a required partial fails instead of
being omitted. Pooled aggregates may be additional summaries but cannot replace the
required per-repetition gates. Three cold samples
imply a p95 equal to their maximum, not a high-confidence tail estimate.

Issue #9 must reuse `t0`, `te`, `tc`, `tp`, and `tf` semantics and separately add
backend transport, worker transport, publication, and browser-render observations.
These results are provider/local-pipeline measurements and never end-to-end latency.

Provisional-prefix access is a benchmark-only local adapter interface. The separate
Issue #8 draft hands out completed segments and therefore cannot supply a partial at
1,500 ms during an uninterrupted 6-second segment. A qualified model here does not
qualify that completed-segment path for early partials. Issue #9 must measure actual
behavior and report partial unavailable or its actual later observation; it cannot
inherit this benchmark's partial latency. Introducing incremental runtime audio delivery
or provisional publication requires an owner-merged owning artifact specifying memory
ownership, framing and immutable transcript ranges before implementation. This Issue
neither adds that interface to #8 nor changes Issue #3 to supply it.

### Quality definitions and fixed decision thresholds

Normalize references/hypotheses with Unicode NFC, ASCII Latin lowercase, and removal
of Unicode whitespace and punctuation categories. Preserve digits, Han characters,
symbols, script variants, and number wording; no phonetic/fuzzy/name alias mapping.
CER is `(substitutions + deletions + insertions) / reference_characters`, using
Levenshtein alignment on Unicode scalars. Resolve equal-cost alignments by match,
substitution, deletion, then insertion. Report micro CER plus per-stratum CER;
empty-reference silence is reported as inserted-character count per minute, not CER.
Target-span exact accuracy is the fraction of annotated name/number/English spans
matched exactly after the same normalization.

For 4/6-second continuous-speech runs, additionally use 800 ms retained left context.
The next segment's new content begins at the prior segment end; context does not reset
the source clock. The harness uses a bounded transcript stitcher: choose the longest
exact normalized suffix/prefix match of at most 32 characters, otherwise concatenate.
Score the stitched stream against the complete reference. At every boundary, annotate
the reference characters in the 800 ms shared interval. Boundary duplicate rate is
alignment insertions matching characters from that interval divided by those reference
characters; boundary omission rate is alignment deletions in that interval divided by
the same denominator. Retain counts and denominators; a zero denominator is N/A and
does not silently pass coverage.

Partial rewrite frequency is changed prior partials / successive partial pairs for
one segment, excluding pure suffix extension. Rewrite severity is the sum of
`old_length - longest_common_prefix(old,new)` divided by the sum of old lengths.
Report finalization changes separately; an empty/withdrawn partial is a rewrite.

All following limits are Livecho's proposed Alpha acceptance gates, not vendor facts:

| Gate | Required result in each warm repetition |
| --- | --- |
| Clean CER | <= 10% micro and <= 15% for every primary stratum |
| Noise CER | <= 20% micro and <= 25% for every primary stratum |
| Target spans | >= 90% exact clean; >= 80% exact noise for each span class |
| Continuous boundary quality | Duplicate <= 1%; omission <= 2% in both 4/6-second overlap runs |
| Partial stability | Rewrite frequency <= 25%; severity <= 10% for each condition |
| RTF | p95 <= 0.70, no failed or timed-out sample, for every 1/2/4/6-second window |
| Segment/preparation | p95 segmentation wait <= 600 ms; input preparation <= 100 ms |
| Partial | p95 `tp - t0` <= 1,500 ms; `tp - ti_first` <= 750 ms |
| Final | p95 `tf - ti_final` <= min(2,000 ms, 700 ms * window_seconds); `tf - te` <= 2,600 ms |
| Cold and memory | Every cached cold load <= 30 seconds; incremental peak physical footprint <= 8 GiB; no swap/page-out attributable to audio |
| Privacy | All audio/time/byte/teardown/persistence gates pass, including failure paths |

CER, target-span and partial-stability gates apply to the production candidate point of a
6-second maximum segment, 500 ms silence, 800 ms overlap. Other windows must still
report full quality, including failures, to expose tradeoffs; their quality does not
replace that operating point. The separate continuous boundary duplicate/omission
gate explicitly applies to both 4- and 6-second overlap runs. Timing/RTF gates apply
to every window as stated.
Include 60 seconds of pure in-memory silence per repetition; allow zero nonempty final
outputs and zero hallucinated partials. Never exclude a failed sample from counts.

### Model decision and failures

Decision states are `blocked_evidence`, `neither_qualifies`, `qualified_1_7b`, or
`qualified_0_6b`. Missing source/model/hardware/privacy evidence gives blocked; it is
not a measured fail. If 1.7B passes all gates select its qualified recommendation even
if 0.6B is faster. If 1.7B has a complete measured failure and 0.6B passes all gates,
recommend 0.6B. Otherwise no model is selected. A partial matrix cannot promote the
other model. Any threshold, corpus, adapter, dtype, quantization, decoding, or machine
change requires a new frozen run set; no post-hoc gate relaxation is permitted.

The owner must approve the final measurement report and a model-decision ADR before
Issues #6/#9 consume a selected manifest. In particular, a 0.6B fallback records the
1.7B failed gates, both full matrices, and quality/latency tradeoff in that ADR. The
current architecture ADR has no accepted model selection; this artifact does not
pretend otherwise. CUDA stays mock/contract-only regardless of these measurements.

Input stall of 2 seconds, provider call exceeding 10 seconds, invalid timing, budget
reservation failure, model digest failure, or cancellation terminates the sample,
clears audio, and records only a stable reason/count. No audio replay/retry queue.
Partial or interrupted runs remain incomplete and are never eligible for selection.

## Interfaces and compatibility

The implementation introduces an offline Python benchmark module under
`tools/asr_benchmark/`, text/metadata corpus manifests under `benchmarks/asr/`, and
`make asr-benchmark-check` for deterministic synthetic contract tests. Manual commands
are `uv run python -m tools.asr_benchmark prepare-models`, `preflight`, and `run`;
each uses a reviewed local manifest identifier, never arbitrary shell/options/URLs.
`run` writes only the allowlisted metrics report. It never downloads assets implicitly.
Provider adapter calls are local `load`, `transcribe(memory_view, timing)`, and `close`;
bounded text updates carry monotonic observations. No production CLI or protocol change.

## Security, privacy, and data lifecycle

The trusted operator records chip, CPU/GPU core counts, physical RAM, OS build,
power mode, thermal status, Python/MLX/provider/converter versions, lock/manifest and
code revisions, model cache state, and measurement method. No serial, hostname,
username, device UUID, environment dump, credential, or arbitrary profiler capture.
Run only a reviewed exact commit manually; untrusted PR/self-hosted triggers are absent.

Audio and recoverable features/copies count toward 30 seconds of monotonic media time,
960,000 canonical PCM bytes for the local active input, and 16,777,216 audio-bearing
bytes per process. Model-only parameters are not audio; input/features/decoder state
that can represent audio are. Record a complete allocation inventory and reserve
before allocation; an opaque provider that cannot bound its audio state is blocked.
The 8 GiB total footprint gate never enlarges the audio ceiling. Disable core dumps,
audio tracing, tensor dumps, profiler snapshots, and media cache. A host unable to
prevent audio paging/crash persistence may run text-only tests but no audio benchmark.
Encryption or RAM-disk storage is not an exception. Release on consumption/cancel/error
and teardown, with failure injection and write-sink observation. Do not claim hostile
host erasure or infer no persistence merely from an empty working directory.

## Acceptance criteria

- [ ] Approved immutable manifests prove both models, conversion, mirrors, and licenses.
- [ ] Preparation progress/resume/digest failures are tested without fetching models in CI.
- [ ] All sources have rights/repeatability evidence; fixtures contain text/metadata only.
- [ ] Cold/warm complete matrices, three repetitions, machine record, quality and timing
  definitions, and memory/persistence evidence satisfy every owning Issue criterion.
- [ ] Deterministic tests cover normalization, alignment ties, percentile boundaries,
  overlap counts, partial rewrites, missing cells, and all decision branches.
- [ ] Owner-approved model ADR records qualified 1.7B, justified qualified 0.6B, or blocked.
- [ ] No audio/model bytes, production interface, protocol change, or CUDA claim is added.
