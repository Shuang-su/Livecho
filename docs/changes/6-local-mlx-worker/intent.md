# Intent: Local MLX worker CLI with fixture and gated real paths

## Issue and owner

- GitHub Issue: [#6](https://github.com/Shuang-su/Livecho/issues/6)
- Human owner: @Shuang-su
- Stage/area/risk: `stage:m1`, `area:worker`, medium operational / high audio risk

## Problem

Apple Silicon contributors lack an installable, diagnosable worker CLI that is constrained
to allowlisted models, speaks accepted protocol v1, and can prove fixture transcription
without claiming real MLX/hardware acceptance. Installing MLX, a mock, or a protocol
double is not evidence that speech was recognized safely.

## Desired outcome

Deliver a Python worker under `workers/mlx/` installable with `uv tool` / `uvx`, exposing
exactly the Issue-named commands: `enroll`, `doctor`, `benchmark`, and `run`.

- **Fixture/contract path (Linux/CI-safe):** text and metadata doubles exercise
  handshake, lease lifetime, sequence/revision rules, and legal **partial then final**
  transcript events with stable immutable ranges. No audio, model load, or MLX inference.
- **Real MLX path (trusted Apple Silicon only):** after #5 report + owner model-decision
  ADR, #8 host/audio evidence, and a separately enabled local execution registry, process
  one synthetic in-RAM lease/segment through the approved provider. Real providers that
  cannot prove provisional prefixes must report **partial unavailable** and emit
  **final-only** revision 1; they must never fabricate partial text or prefix latency.

Together with #8 and #9 this enables the first local caption loop once those gates pass.
#9 already treats fixture partials as UI/protocol exercise and rejects unexpected real
partials for the first `synthetic_mlx` release.

## Non-goals

- Real cloud lease, community signup/device onboarding, multi-worker scheduling, or
  long-session lease renewal (#27 / #14 / #15).
- CUDA inference, remote shell, arbitrary server code, or server-provided download URLs.
- Model download/conversion, benchmark scoring that selects a model, or inventing a
  model-decision ADR.
- Real platform ingest, public accounts, production enablement, or deployment switches.
- Claiming fixture partials are model partials, or claiming final-only MLX as partial
  support.

## Constraints and data impact

- Honor AGENTS.md: ephemeral audio only; workers accept only versioned ASR protocol and
  allowlisted manifests; CUDA remains mock/contract-only until later evidence.
- #2 ceilings (30 s media, 960,000 canonical bytes, 16,777,216 process audio bytes),
  #3 wire semantics (`epoch` / `seq` / `revision` / `is_final`), #5 model ADR and report,
  and #8 `audio_budget_unverified` until approved FFmpeg/host inventories remain binding.
- Data classification: ephemeral synthetic audio in RAM only; retained diagnostics are
  payload-free stable reasons/counters; synthetic text/metadata fixtures only—no PCM,
  WAV, digests of audio, or recoverable encodings.

## Success signal

Operators and CI can distinguish (a) green fixture/contract checks, (b) honest
`blocked_evidence` / doctor failures when model/host/execution gates are missing, and
(c) separately recorded trusted-host MLX measurements. Unknown models, non-Apple-Silicon
MLX starts, non-synthetic leases, and unsafe hosts are refused before audio admission.
Every terminal path clears audio with no delayed transcript after cancel/expiry.

## Human decision

- Status: Proposed; **documentation only**. Implementation is forbidden until this
  artifact PR's intent/spec/plan are owner-merged (CONTRIBUTING / AGENTS).
- Approved by/date: Pending @Shuang-su review and merge.
- Runtime/model/host/execution authorization: Pending separate evidence; these docs do
  not authorize download, inference, or production.
