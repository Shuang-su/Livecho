# Intent: Read a live subtitle companion page

## Issue and owner

- GitHub Issue: [#11](https://github.com/Shuang-su/Livecho/issues/11).
- Human owner: @Shuang-su.
- Stage/area/risk: `stage:m1`, browser/PWA, normalized-content visibility risk.
- Source limitation: the authorized 2026-09-26 Issue snapshot was read; current remote
  text and comments are unavailable, as recorded in [evidence](evidence.md).

## Problem

There is no browser surface for a single session's current subtitles and connection
state. A viewer needs to distinguish provisional text, confirmed text, absence of a
worker, a disconnected view and an unrecoverable gap without mistaking them for history.

## Desired outcome

Provide a responsive React/Vite PWA showing one operator-selected room's normalized
subtitles and session state. It consumes Issue #9's local synthetic timeline through
the existing viewer protocol. Public account enrollment, device self-service, platform
ingest and long-stream lifecycle extensions do not block this short local demonstration.

Keep the page independent of an external video player. An explicit, session-only
display delay helps a viewer align text manually; it cannot predict unavailable text
or measure synchronization with another player. Final-only input is a supported first
demonstration, with partial availability described honestly.

## Non-goals

- Danmaku/SC (#10/#29), history, search, export, statistics, worker management,
  public start/stop controls, accounts/devices, native Mac applications or deployment.
- Embedded players, playback control, automatic video synchronization, translation,
  model selection, new audio delivery or changes to v1 identities/cursors.
- Offline transcript replay, transcript persistence, long-session completion claims
  (#27), real-platform input or any production visibility enablement.

## Constraints and data impact

Only approved normalized transcript/status events may reach the page. Render text as
untrusted text, never markup. The browser connects only to the backend and receives no
audio, worker identity, source locator, raw event, credential or model manifest.
All timeline state, cursor and delay settings are session memory; the PWA may cache
only a fixed static application shell. Existing Issues #2/#3/#5/#8 remain authoritative.

## Success signal

Desktop and mobile users can read the same ordered synthetic timeline, adjust bounded
display delay, see gaps and status changes immediately, and reconnect without duplicate
effects. A 20-viewer fast/slow test proves isolation and bounded client queues.

## Human decision

- Status: Proposed; documentation review only.
- Approved by/date: Pending @Shuang-su review and merge.
- Model/host/source/production approval: Not supplied or implied by these artifacts.
