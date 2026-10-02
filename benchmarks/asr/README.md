# Local ASR benchmark

The Issue #5 contracts, text metrics, matrix evaluator, scheduling and transfer control
planes live in `tools/asr_benchmark`. Run `make asr-benchmark-check` for deterministic
text/metadata tests. No audio, weight, source rendition, or approved manifest ships here.

The local final manifest projects to the unchanged protocol tuple: provider `mlx`,
the lowercase canonical model basename, its immutable source revision, and SHA-256 of
the complete canonical local inference manifest. This helper does not allowlist a model.
Report serialization verifies a separately reviewed frozen run identity before writing
to an already-open text sink; changed corpus/settings/machine/provenance requires a new
run identity. The POSIX model-only cache uses private directory descriptors, nonblocking
per-asset locks, fixed identity-derived names, actual file offsets, metadata checkpoints,
bounded SHA-256 reads and mutation-checked atomic promotion. Context cancellation or an
integrity failure invalidates the partial; deliberate normal close preserves resumable
progress. The download coordinator preserves cancellation progress only with an explicit
checkpoint matching actual length, identity and started-attempt count. Tests persist
original notice text in temporary directories only.

The internal preparation transport derives HTTPS requests from immutable manifest assets
on the fixed Hugging Face authority. It verifies TLS and accepts only exact-length,
identity-encoded initial responses or exact suffix Range responses. Redirects and the
unverified ModelScope endpoint remain blocked; there is no source fallback or credential,
proxy, arbitrary URL or header integration. Three attempts and fixed 1/2-second delays
share a 60-second no-progress deadline across connect, headers and body within each
attempt. Authentication, integrity, unsupported responses and server cooldowns terminate.
Cancellation revokes IO before releasing the cache entry. Complete interrupted files can
be locally verified/promoted without a request beyond EOF, including after attempt three.
Synchronous cache fsync/hash work is bounded in chunk size but cannot be preempted by the
async network deadline. This transport has no CLI registration or live-network evidence.

`prepare_sources` now acquires a complete preparation-only source collection. It first
verifies existing files under their selected mirror identities and downloads only truly
missing physical assets. Corruption, unsafe files, permission and lock failures terminate;
they never trigger replacement downloads. Matching content aliases share a locked reader.
All files must verify before a read-only mapping is borrowed, and the context revokes all
readers on exit. The caller retains ownership of the cache. Downloader success metadata
alone cannot establish that files exist or are valid. A cooperating client that completes
an asset after the missing probe is handled by another locked actual-file verification.
ModelScope acquisition is still blocked; a complete, verified cache bound to that
explicit mirror may be read locally without requesting its unverified endpoint. This
collection neither approves an inference manifest nor invokes conversion or inference.

`conversion_session` adds a preparation-only lifecycle around an injected cooperative
backend. Exact converter/lock pins and fresh unloaded state precede acquisition; only
successful admission transfers backend cleanup to the session. The eager decoder consumes
the complete verified source mapping with local-only/no-remote-code arguments, evaluates
and synchronizes, then releases all readers. Named tensor records and every description
must match the exhaustive map before quantization starts. The existing dispatcher retains
unsupported tensors and uses the fixed affine 8-bit/group-64 call for classified weights.
Results are borrowed through a checked mapping; exiting clears that mapping and closes the
backend. Cancellation/error paths also clear this layer's containers and temporary token
references, including when its traceback survives. This is a cooperative interface: pin
self-reports are not revision proof, escaped raw tensor references cannot be revoked,
third-party frames cannot be erased, and synchronous compute has no hard deadline here.
No actual tensor decoder, MLX backend, serializer, inference manifest or registry is added.

`ConversionStaging` now provides a separate model-only storage boundary for a future
reviewed serializer. A closed preparation/converter/lock-bound output plan declares every
path/kind and per-file/total byte limit, within internal ceilings of 256 outputs, 64 GiB
per file and 128 GiB total. These limits concern model storage, not audio. Bounded sinks
write private staging files; held-inode checks and actual size/SHA verification precede
publication under the existing canonical final-cache keys. Same-content aliases share
physical files while counting separately toward declared logical output limits. Existing
assets are verified and preserved. A preparation-scoped writer lock coordinates receipt
transactions; existing per-asset locks coordinate content access.

One atomic unapproved-receipt rename is the complete-set publication point, followed by
directory fsync before success. Individual asset renames do not commit a set. A failed
attempt may leave immutable assets without a receipt; future attempts may rehash/reuse
them. Cleanup touches only the current transaction's staging, and does not collect unknown
crash-abandoned stages. After receipt rename, errors preserve the visible set; reopening
rehashes current bytes but does not repair a failed directory fsync. An identical commit
retry revalidates the prior complete set and fsyncs again; conflicts or damaged prior
sets stop. Injected failure tests are not power-loss/filesystem durability proof.

The receipt contains actual output metadata only, without Approval or inference rights.
It cannot enter the final loader as an inference manifest. Independently approved final
manifests can reference these compatible content keys and still verify the complete set.
No real serializer, model-format validation or quantization-quality proof is supplied
here. Storage accepts only model bytes
from a separately reviewed cooperative caller; it is not an audio or arbitrary-file API.

`prepare_converted_artifacts` now connects these boundaries through an injected
cooperative serializer. Strict preparation/plan/cache identity, converter/serializer pins
and exact fresh states are checked before I/O or ownership transfer. Once admitted, both
backend roles close exactly once even if storage construction or inner conversion
admission fails; a shared backend instance is deduplicated by identity. Existing local
source files must actually verify, and a fixed denying transport prevents a missing-file
download bypass. The serializer receives only borrowed converted values, allowlisted
auxiliary tokenizer/config/notice inputs with `size`/`read_at`, and sequential
`write_output(label, chunks)`. These facades expose no commit, close, path, fd or network
operation. They expire before serializer cleanup; observed errors/cancellation/pin changes
remain terminal even if the backend catches them. After reader, serializer and converter
cleanup succeeds, the bridge alone commits the unapproved receipt. A late failure after
publication preserves the stored set while withholding a successful return. No concrete
serialization format, backend pin provenance, hostile-code sandbox, raw-reference erasure,
hard synchronous deadline, inference approval or executable registry is provided.

The final-cache reader separately binds the final inference manifest to preparation,
checks every converted asset before exposing any handle, and shares a locked reader for
equal-content path aliases. Bounded read-at access checks the held inode and mutation
metadata before and after reading; no public raw descriptor or local path is supplied.
The local load boundary checks injected backend pins/unloaded state, requests local-only
and no remote code, synchronizes, and closes all readers before returning load timestamps.
Those timestamps do not establish a new process or form a scored `Cold` observation.
The guard and eager backend are injected contracts; neither has a real registered backend.

Manual entry points accept a reviewed identifier, never a path or URL:

```sh
uv run python -m tools.asr_benchmark prepare-models --manifest pending --source huggingface
uv run python -m tools.asr_benchmark preflight --manifest pending
uv run python -m tools.asr_benchmark run --manifest pending
```

All currently return exit 2 and a closed `blocked_evidence` record. `pending` is an
unapproved identifier, not a manifest. Nothing is downloaded or loaded. There is no
runtime registration API that can turn a caller-supplied approval flag into authority.

Still required before execution: reviewed immutable source/conversion/inference and
mirror records, exact reviewed MLX dependencies, the independently authored Qwen forward
pass/converter and allocation inventory, a bounded source/preprocessing implementation,
the qualified 60-script consenting-speaker corpus, protected-host evidence preventing
paging/dumps, real-time runner/watchdog integration, and real M3 Ultra measurements.
The model conversion dispatcher calls only the reviewed backend's affine 8-bit/group-64
operation, evaluation and synchronization; no actual MLX backend is installed.
Transfer-control tests simulate lengths/digests/outcomes; cache tests exercise local
filesystem promotion and final reads with ordinary text. HTTP/control tests inject streams
and responses without opening sockets. They do not establish live endpoint/CDN support,
model downloads, a real model serializer or an MLX cold loader. Storage tests write only
original notice text. Cache locking assumes
cooperating cache clients in
a private operator directory, not protection against a hostile process with the same
operator privileges. Resource tests observe release callbacks;
they do not establish physical RAM erasure or no-paging on any host.

No model is selected. A synthetic complete report in tests exercises the fixed decision
rule only; it is never an inference allowlist or acceptance evidence. Issue #5 stays
open until the full matrix and owner-approved model-decision ADR exist. Downstream
Issues #6/#9 must not consume these test results as model measurements.
