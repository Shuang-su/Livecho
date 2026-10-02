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
progress. It is callable only as a preparation backend, with no CLI registration or
network transport. Tests persist original notice text in temporary directories only.

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
filesystem promotion and final reads with ordinary text. They do not verify a real network
transport, model download, converted-asset writer or MLX cold loader. Cache locking assumes
cooperating cache clients in
a private operator directory, not protection against a hostile process with the same
operator privileges. Resource tests observe release callbacks;
they do not establish physical RAM erasure or no-paging on any host.

No model is selected. A synthetic complete report in tests exercises the fixed decision
rule only; it is never an inference allowlist or acceptance evidence. Issue #5 stays
open until the full matrix and owner-approved model-decision ADR exist. Downstream
Issues #6/#9 must not consume these test results as model measurements.
