# Intent: Bound and supervise the in-memory audio pipeline

## Issue and owner

- GitHub Issue: [#8](https://github.com/Shuang-su/Livecho/issues/8)
- Human owner: @Shuang-su
- Stage/area/risk: `stage:m1`, audio ingest, high privacy/resource risk

## Problem

Livecho has protocol metadata validation but no executable FFmpeg supervision, bounded
PCM ownership, silence/continuous-speech segmentation, or proof that terminal paths
leave neither audio buffers nor a decoder process behind.

## Desired outcome

Provide a controlled synthetic memory source independent of Bilibili, convert through
a supervised FFmpeg process into s16le/16 kHz/mono PCM, and deliver bounded memory
segments with 500 ms silence closure, a 6-second maximum, and 800 ms continuous-speech
context. Issue #9 can use the interface directly. Issue #7 later integrates only after
the required source/channel/policy controls and this pipeline's verification pass.

## Non-goals

- Real stream access, live platform URLs, encoded-media network protocols, public output,
  distributed scheduling, model inference, or audio persistence in any representation.
- Replacing Issue #3 ordering, binary framing, `epoch`, `seq`, or `revision` semantics.
- Authorizing a real-audio lease or claiming deletion on an untrusted worker host.

## Constraints and data impact

Issue #2's 30-second media-time limit, 960,000-byte canonical room/session and separate
active-lease ceilings, 16,777,216-byte process ceiling, and single-room/single-lease
Alpha limit are mandatory. Every audio-bearing copy and internal buffer counts.
Only synthetic input is eligible in this implementation. Persisted diagnostics contain
bounded counters and stable reasons; no audio, waveform, digest, input body, or locator.

## Success signal

Deterministic tests prove exact segmentation/timing, admission before allocation,
bounded overload and restart behavior, protocol compatibility, no writes to audio sinks,
and idempotent cleanup on every normal, abnormal, and abrupt parent-exit path.

## Human decision

- Status: Proposed; documentation review only.
- Approved by/date: Pending @Shuang-su review and merge.
- Runtime/FFmpeg build/privacy evidence: Pending implementation and trusted validation.
