# Intent: Demonstrate one local caption vertical

## Issue and owner

- GitHub Issue: [#9](https://github.com/Shuang-su/Livecho/issues/9).
- Human owner: @Shuang-su.
- Stage/area/risk: `stage:m1`, backend orchestration, high audio/privacy risk.
- Remote Issue reread on 2026-10-25; [evidence](evidence.md) records publication
  reconciliation and remaining approval/acceptance limits.

## Problem

Separate audio, worker and protocol contracts do not prove a complete caption path.
The backend needs one bounded local orchestration flow that can show the actual state
and measured limitations without making platform access, accounts or devices prerequisites.

## Desired outcome

The first implementation phase is only `fixture_timeline`: manually started synthetic
text/status on the validated viewer path. It needs accepted #9 artifacts and the
existing viewer protocol, not a model manifest, worker, audio integration or host audio
evidence. It cannot close Issue #9's real ASR criteria.

A separately gated later phase would provide one synthetic memory speech session, one approved local MLX
worker and a normalized subtitle/status viewer endpoint. A separate text-only fixture
mode supports deterministic Web/PWA development while real model/audio execution is
blocked. Its success is explicitly a fixture success, never a working ASR claim.

The short local path uses existing #8 completed segments and supports final-only text.
It measures actual stage timings and reports partial unavailable. #7 public-platform
input, #10/#29 danmaku/SC, public accounts/devices and #27 long-session lifecycle are
separate work and do not block a short synthetic demonstration.

## Non-goals

- Real source acquisition, model preparation/selection, production or community
  worker deployment, persistence/history/raw archives, multi-worker scheduling.
- New audio transport, interim-prefix protocol, custom lifecycle fields, lease renewal,
  silent sequence/PTS repair, public start controls or new account/device flows.
- Treating test doubles, host inventory or artifact merge as actual MLX/host evidence.

## Constraints and data impact

All accepted #2/#3/#5/#8 constraints remain authoritative where applicable. Fixture
execution opens no audio source and loads no model. For `synthetic_mlx`, audio stays
bounded and ephemeral. The selected model needs a complete actual report and owner-approved ADR;
the exact host/source/decoder/provider evidence and separate execution authorization
must pass before any real run. The execution registry remains closed in this batch.
Only approved synthetic normalized text/status and payload-free observations may be
retained in verification reports. Public/production publication remains disabled.

## Success signal

A reviewer can trace source admission, segment handoff, one worker response, backend
validation and viewer receipt; stop/disable/error clears both audio and publication.
The report distinguishes text-only fixture, contract double, blocked real run and
measured MLX result, including missing partials, gaps and component-specific failures.

## Human decision

- Status: Proposed; documentation only.
- Approved by/date: Pending @Shuang-su review and merge.
- Runtime/model/source/host/production approval: Pending separate evidence.
