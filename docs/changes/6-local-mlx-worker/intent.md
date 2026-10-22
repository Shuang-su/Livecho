# Intent: Run one gated local MLX worker

## Issue and owner

- GitHub Issue: [#6](https://github.com/Shuang-su/Livecho/issues/6).
- Human owner: @Shuang-su.
- Stage/area/risk: `stage:m1`, local worker, high audio/provenance risk.
- Current remote Issue body is unavailable; [evidence](evidence.md) records the gap.

## Problem

The accepted protocol and benchmark specification do not supply a runnable local worker
that admits only an approved model, enforces bounded audio ownership and returns final
transcripts through the existing worker contract. Installing MLX or a protocol mock is
not evidence that the full worker can safely transcribe speech.

## Desired outcome

Provide an operator-started local CLI worker for one synthetic session and one lease.
It verifies an already approved local inference manifest, negotiates v1, processes
bounded in-memory segments, and returns untrusted normalized final text for backend
validation. Contract-only tests remain available while model or host evidence is absent.

## Non-goals

- Model download/conversion, benchmark scoring/model selection, real audio, platform
  access, production enrollment, remote community execution or CUDA inference.
- Public account/device onboarding, multi-worker scheduling/failover, long-session
  lease renewal (#27), arbitrary commands, server download URLs or new wire fields.
- Runtime provisional-prefix audio delivery. The first #8 integration is final-only;
  partial unavailable is a reported limitation, never a fabricated measurement.

## Constraints and data impact

#2 audio/provenance controls, #3 protocol and #5/#8 evidence gates remain unchanged.
The model requires an actual complete #5 report and owner-approved model-decision ADR.
Host no-paging/no-crash and bounded-allocation proof are prerequisites, not inferred
from tests or the existence of an installed model. The execution registry stays closed
until separately authorized; these documents do not authorize download or execution.
Only payload-free metrics and synthetic text/metadata fixtures may be retained.

## Success signal

A trusted operator can distinguish a passing contract double from a verified real MLX
run, and a blocked run from a measured failure. The worker refuses unknown manifests,
non-synthetic leases and unsafe hosts before audio admission, and clears audio on every
normal/abnormal terminal path with no delayed transcript escaping cancellation.

## Human decision

- Status: Proposed; documentation only.
- Approved by/date: Pending @Shuang-su review and merge.
- Runtime/model/source approval: Pending separate evidence and explicit authorization.
