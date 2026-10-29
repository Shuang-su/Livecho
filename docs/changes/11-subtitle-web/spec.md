# Specification: Subtitle companion Web/PWA

This is a proposed local design for owner review. The requirement source map is in
[evidence](evidence.md). Numeric UI limits below are Livecho choices; they do not alter
the accepted [v1 protocol](../3-protocol-v1-contract/spec.md).

## Behavior

### Scope and display

The React/TypeScript/Vite application under `apps/web/` has a single room view and no
room-start action. A deployment-configured same-origin backend supplies the selected
opaque room ID; a route parameter may select only that configured room, never a URL or
an arbitrary public ingest target. The demonstration runs locally with synthetic
transcript/status fixtures from #9. It is labeled as a synthetic demonstration.
The first delivery uses #9's text-only `fixture_timeline` mode; no audio, decoder,
model or worker is started. Owner acceptance of the #11 artifacts permits fixture-only
UI implementation without model/worker/audio approval. Backend integration additionally
requires agreement with the accepted #9 contract. Actual worker partial emission and
MLX/host acceptance remain unproved, separate from UI fixture acceptance.

The view contains room/session status, connection state, current provisional text,
up to four recent final segments, a visible gap notice when needed, a display-delay
control and partial availability text. This short in-memory reading context is not a
history browser: no pagination, seek, download or persistence. A final is immutable
while retained but may leave the four-segment view. All content is selectable plain
text; no HTML/Markdown/link interpretation, remote image, embedded video or playback
control is allowed. Preserve accepted text exactly, including Unicode and line breaks.

Partial styling and a textual "Provisional" label distinguish it from final text.
Updates replace the same segment in place; finalization does not append a second copy.
Final-only mode states "Final subtitles only; partial unavailable". The initial #8
completed-segment path uses this mode; no benchmark early-partial result is shown as
observed runtime behavior. Fixture coverage may exercise v1 partial revisions without
claiming that the actual worker emits them. There is no partial-capability wire field;
the local demonstration configuration fixes this truthful label. Unknown future source
capabilities use "Partial availability unknown", never an inference from silence.

At 360 x 800 and 1280 x 800 CSS pixels the status, subtitles and delay control remain
usable without horizontal scrolling. Text wraps, supports 200% zoom and keyboard-only
operation, and does not rely on color alone. Connection/status and final subtitles use
polite live announcements; partial updates are not announced on every revision.
Long words and the maximum accepted 4,096-scalar text cannot cover or move controls
offscreen. The four final rows and one partial row use a maximum 131,072 UTF-8 text
bytes in total, with oldest final rows evicted first. Do not truncate accepted text;
if a whole accepted row cannot fit, clear the view and show the local overflow gap.

### Protocol acceptance before presentation

Connect to #9's same-origin `/api/viewer/ws` with `livecho.viewer.v1`, minor 0,
and a compatible client version. Consume only `ViewerReadyV1`, `TimelineEventV1`, and
the existing bounded ack/error responses. Import the generated types and validator
from the protocol package's browser-safe shared entry specified below. Reject binary
input, unknown fields, invalid JSON,
wrong binding, incompatible version and oversized frames before they affect display.
No frontend-only field is sent in a wire message and no backend error body is echoed.

The accepted source of truth is `(session_id, epoch)` from `ViewerReadyV1` and exact
`next_seq`. Use integer-safe uint64 decimal handling, never JavaScript Number arithmetic
for epoch/seq/revision. Apply the complete v1 sequence/revision validation and precedence,
including the 256-record sequence window and 4,096-identity revision state limit.
Display capacity does not permit evicting protocol state early. The revision key is the
v1 event identity; #9 must keep one stable event ID for each segment inside an epoch.
`segment_id` identifies its UI row within that binding, without making revision state
global across epochs. Immutable time bounds and final-object behavior remain v1 rules.

Accept a duplicate only under the v1 duplicate decision and produce no display effect.
Reject a conflict/gap without advancing the receive cursor or changing text. A higher
epoch timeline event is not authority to change epoch; obtain a new valid handshake.
Never insert guessed events or advance over a sequence gap. Keep the receive cursor
as the next accepted sequence, independently of when the accepted text is displayed.
At 4,096 revision identities, existing identities still accept valid updates and
duplicates under v1. Only a new 4,097th identity triggers `revision_capacity_exceeded`
without consuming sequence or altering state; then stop the view and obtain a fresh
no-cursor handshake with a visible gap. Never stop merely because capacity was reached
or reset counters in place. #27 owns future long-stream lifecycle changes.

### Session-only display delay

Default added delay is 0 ms. The user may choose 0 through 5,000 ms inclusive in
100 ms steps. This is extra time after validated receipt, not a signed PTS correction.
It cannot show text before it exists or remove inference/transport delay. The label
states that the page does not observe an external player's clock or guarantee sync.

Assign each accepted display mutation a local monotonic `received_at`. Its due time is
`received_at + selected_delay`; source PTS, `start_ms`, `end_ms`, `occurred_at`, text,
event identity, epoch, seq and revision are never rewritten. A delay change recomputes
due times for pending mutations only; already displayed finals stay visible and are
not replayed. If lowering delay makes several mutations due, process them in accepted
sequence order in the next render turn. Increasing delay never hides a displayed final.

The pending presentation queue is memory-only and bounded by both 128 accepted text
mutations and 262,144 bytes of their validated serialized JSON, counted before enqueue.
Status/control handling and protocol metadata have separate ownership and are never
blocked by this queue. Intermediate partial revisions may be coalesced for presentation
only after all have passed protocol validation; retain the latest due revision for
each row, and never show a partial after its final. Coalescing cannot advance the
receive cursor on a rejected event or postpone safety-state processing.

On either queue limit, stop admitting display mutations, clear pending and displayed
text, mark a visible subtitle gap and close the affected viewer connection. Reconnect
through the normal current-cursor procedure; no saved event-body retry queue, disk
spill or unlimited browser task queue is permitted. Foreground restoration also drains
only a bounded queue; if suspension caused overflow, show a gap rather than a burst
of stale subtitles. A delay selection is erased on room/session/epoch change, fresh
resync, page reload or unmount; a same-binding resumed connection may retain the value.

### Connection, resumption and gaps

Connection UI states are connecting, connected, reconnecting, offline and incompatible.
They are browser-local, never invented server enum values. An offline signal or closed
connection immediately clears pending/current text and labels the connection state;
do not leave a stale caption looking live. Retain only the memory cursor and protocol
metadata needed for a possible same-binding resume. If accepted but undisplayed text
was cleared, state explicitly that some subtitles were not displayed, even when cursor
resume succeeds. Already accepted sequence positions cannot be rolled back to recover
discarded presentation data.

While online, retry connection at 250/1,000/2,000/4,000/8,000 ms, at most five retries
per outage; after exhaustion offer an explicit Retry control. Offline suspends timers.
Coming online may begin one such bounded retry cycle. Session stop/disable, incompatible
protocol and unmount cancel timers. Manual Retry does not start a room or enable ingest.

The subscribe cursor is exactly `session_id`, `epoch`, `next_seq` from validated memory
state; no localStorage or history request reconstructs it. `cursor_resumed: true` must
match the same session/epoch and expected next sequence before retaining that state.
`resync_required`, a refused cursor, new session or epoch clears protocol and display
state and obtains a fresh `ViewerReadyV1` using a subscribe without a cursor. Display
"Subtitle gap; continuing from the current position" before the new text. No historical
replay, missing-event count or loss duration is invented. The gap notice remains until
the viewer dismisses it or leaves the view; dismissal never changes protocol state.

An ordinary no-cursor first connection is current-only without a historical continuity
claim. Resume is possible only where #9 can satisfy the accepted v1 cursor contract;
this UI does not require a server event-body replay store. If the server has progressed
beyond what it can resume, the result is explicitly a gap and fresh position.

### Session status and visibility precedence

Only the five v1 session statuses are accepted. Map `starting` to waiting/starting,
`live` to live, `stopping` to stopping, `stopped` to stopped and `failed` to failed.
The #9 closed public reason mapping must distinguish `no_compatible_worker`,
`ingest_disabled`, `policy_disable` and `session_deleted` when applicable. Unknown safe
reason codes render a generic status, not arbitrary server text or an inferred cause.
"No compatible worker" is shown only for an explicit mapped reason; a silent stream
is not sufficient evidence. Connection status and session status remain separate.
In `fixture_timeline`, #9 may publish `live` with no reason without a worker;
the synthetic-demonstration label remains visible. The worker-wait deadline belongs
to `synthetic_mlx`, not to this text-only mode. Fixed failure reasons
`worker_failed`, `source_failed` and `protocol_failed` render safe local labels;
unknown reasons use the generic failed/status label.

Process status immediately after validation, with zero display delay. `stopping`,
`stopped`, `failed`, `ingest_disabled`, `policy_disable` or `session_deleted` clears
all queued/displayed transcripts and blocks further transcript presentation for that
binding. Terminal or blocked content cannot reappear because a queued timer fires or
a delayed partial arrives. Reopening requires a fresh authorized handshake; the page
cannot perform that authorization. A status message or socket close must be tested
while the display delay is at its maximum. A browser that is disconnected cannot learn
a later server decision, so connection loss itself hides text immediately; this is not
a claim that the backend can recall text already seen by a viewer.

## Interfaces and compatibility

#11 owns `apps/web/`, its static PWA shell, frontend checks and the minimum browser-safe
packaging refactor in `packages/protocol/`. The current validator imports `node:buffer`,
`node:crypto` and `node:fs` and reads schemas at runtime, so its existing root entry
cannot be imported directly in a browser bundle. Add a shared browser entry with
build-bundled generated schemas and browser-compatible byte/hash adapters; keep the
existing Node entry/API working. Reuse one strict parser, JCS projection and ordering/
revision implementation rather than creating a second frontend validator. Preserve
validation order even if browser hashing is asynchronous by serializing acceptance in
the same bounded input path; no message may overtake an earlier candidate. Browser and
Node runners must retain every existing golden outcome and exact schema bytes. This
packaging work is part of #11 implementation, not a new approval or runtime gate, and
does not authorize protocol semantics/schema/fixture changes. #9 owns the backend
endpoint, publication policy, concurrency and status-reason mapping. Before integration
the two owner-merged artifacts must agree on the same-origin route and the reason
mapping. This draft does not treat an unmerged #9 proposal as accepted authority.
It adds no protocol model, status enum, timestamp meaning, schema or generated fixture.
An incompatible requirement blocks integration until its separate protocol Issue lands.
Model adoption, trusted-host execution and actual ASR evidence gate their own real
capabilities; they do not gate text-only fixture UI work or its synthetic E2E checks.

## Security, privacy, and data lifecycle

Only the shell's versioned local HTML/CSS/JS/icons may enter a Service Worker cache,
using an explicit build-produced allowlist. Exclude APIs, WebSockets, responses carrying
transcript/event/session data and all unknown URLs. No background sync, transcript
notification, IndexedDB, localStorage, sessionStorage, filesystem, service-worker message
queue or offline content cache may store timeline data or cursor. Application API
responses use `Cache-Control: no-store`; no event data appears in URLs or analytics.
On offline launch, show the shell with "Offline; subtitles unavailable", with no old
session text. Service-worker update/activation removes obsolete shell caches only.

Logs, error tracking and test artifacts contain only public-safe synthetic fixtures or
payload-free codes/counts. Never log received frames, DOM transcript snapshots from
real sessions, raw platform payloads, worker identities, tokens, locators or audio.
For later real output, #2 source/rights/visibility gates remain mandatory; anonymous
rendering permission is never inferred from a working synthetic demo. No app feature
can read raw archives or connect to a worker.

## Acceptance criteria

- [ ] Mobile/desktop and 200% zoom visual/E2E checks cover the maximum accepted text,
  keyboard delay control, readable statuses and distinct partial/final presentation.
- [ ] Revision replacement, final immutability, duplicate no-ops, exact-next cursor,
  rejected gaps/conflicts and old/unknown epochs follow unchanged v1 golden outcomes.
- [ ] At 4,096 identities an existing valid update/duplicate still succeeds; only a new
  4,097th identity rejects and triggers the visible fresh-resync path without state change.
- [ ] Browser and Node shared validation agree on every existing golden result; the
  production browser bundle has no Node built-ins or runtime filesystem/schema read.
- [ ] Same-binding resume, refused/out-of-window cursor, new epoch/session and cleared
  undisplayed text each show the correct continuity/gap claim and clear old partials.
- [ ] Delay 0/5,000 ms, step/range validation, increase/decrease, coalescing, foreground
  restore and exact queue boundaries preserve every source and protocol identity.
- [ ] Stop/disable/delete/failure and disconnect hide text ahead of delay timers.
- [ ] Twenty simulated viewers run the same synthetic timeline for 60 seconds: 18 fast,
  one consuming once per second and one deliberately stalled; fast viewers do not wait
  for the slow pair, all queues stay bounded and overflow uses visible resync.
- [ ] Offline shell reload contains no previous timeline data in DOM or any browser
  storage; API/network/cache/storage interception detects attempted content writes.
- [ ] Public messages contain only normalized allowed transcript/status fields; no
  raw payload, worker identity, locator, secret, model reference or audio reaches UI.
- [ ] Final-only demo labels partial unavailable, distinguishes UI fixture checks from
  real MLX evidence, and adds no production, source, model or account enablement.
