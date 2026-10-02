# Intent: Measure and select the local MLX ASR candidate

## Issue and owner

- GitHub Issue: [#5](https://github.com/Shuang-su/Livecho/issues/5)
- Human owner: @Shuang-su
- Stage/area/risk: `stage:m1`, ASR benchmark, high audio/provenance risk

## Problem

Livecho has no trusted M3 Ultra measurements of Qwen3-ASR 0.6B or 1.7B in
8-bit MLX form. Model size, vendor throughput, and a successful dependency install
cannot establish Chinese caption quality, latency, memory use, or safe audio handling.

## Desired outcome

A local, manually invoked harness compares both candidates under the same frozen
corpus, preprocessing, timing boundaries, and acceptance rule. It reports cold and
warm results for 1/2/4/6-second windows, selects 1.7B only when all gates pass, and
otherwise proposes the qualified 0.6B fallback or explicitly reports blocked.
Issues #6 and #9 consume the measurement definitions and approved decision record.

## Non-goals

- Production worker, browser, transport, deployment, Bilibili access, or publication.
- Real audio through a synthetic `LeaseV1`; Issue #28 owns a later real-audio protocol.
- Audio files, audio downloads/cache, audio hashes, weights committed to Git, CUDA
  execution, automatic hardware CI, or an unreviewed third-party model loader.
- Claiming measurements, model approval, or rights evidence in this artifact PR.

## Constraints and data impact

Accepted Issue #2 audio/provenance controls and Issue #3 protocol remain unchanged.
Licensed human speech is non-synthetic even when public. It is eligible only for a
separately approved local benchmark source; it never becomes worker-protocol input.
Only model assets have a persistent, explicitly separated cache. All audio and
recoverable audio derivatives remain within the accepted RAM/media-time ceilings.
Persisted results contain licensed reference text, non-audio source metadata, machine
configuration without identifying serials, and payload-free measurements.

## Success signal

An owner can reproduce the comparison on a trusted M3 Ultra and distinguish a measured
pass, a measured failure, and missing evidence. A passing report includes every cell,
three independent repetitions, fixed thresholds, model provenance, and privacy checks.

## Human decision

- Status: Proposed; documentation review only.
- Approved by/date: Pending repository-owner review and merge.
- Hardware/model/source approval: Pending; no model is selected by this PR.
