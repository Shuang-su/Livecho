# Intent: Define protocol v1 and cross-language compatibility

## Issue and owner

- GitHub Issue: #3
- Human owner: @Shuang-su
- Stage/area/risk: `stage:m0`, `area:protocol`, `type:feature`, `risk:high`

## Problem

The backend, browser, and community worker do not yet share an executable wire contract.
Without a single source for message shapes, ordering, retries, and version negotiation,
the Python and TypeScript implementations can accept different data, reconnects can
silently duplicate or reorder results, and later workers can accidentally receive
secrets or unbounded payloads.

## Desired outcome

Define protocol major version 1 from strict Python Pydantic models and generate the
corresponding JSON Schemas and TypeScript types deterministically. The contract will:

- define `TimelineEventV1`, `TranscriptSegmentV1`, `WorkerHelloV1`, `LeaseV1`,
  `HeartbeatV1`, and `WorkerStatsV1` plus the bounded handshake/error messages needed to
  exercise them;
- separate `livecho.worker.v1` and `livecho.viewer.v1` JSON control messages from a
  fixed, bounded binary PCM message;
- make `epoch`, `seq`, and `revision` ordering, duplicate, reconnect, and rejection
  behavior executable in both languages;
- run the same synthetic golden cases through Python and TypeScript validators; and
- fail CI when committed schemas, types, compatibility data, or fixtures drift from the
  authoritative models.

## Non-goals

- Connecting to Bilibili, another live source, or a real ASR model.
- Implementing worker enrollment, authentication, scheduling, failover, persistence,
  database state, public history, or deployment.
- Enabling production PCM or deciding the rights and residual-risk gate for disclosure
  of real audio to a community worker.
- Defining raw Bilibili payloads, normalized danmaku or super-chat fields, long-term
  timeline storage, or browser presentation. Those remain with Issues #10, #11, and
  #16; protocol v1.0 initially carries only synthetic transcript and session-status
  timeline payloads.
- Adding arbitrary commands, shell/container/code execution, model download locations,
  or extensible telemetry dictionaries.

## Constraints and data impact

- Python Pydantic is the only hand-edited schema source. Generated JSON Schema and
  TypeScript files are committed and must reproduce byte-for-byte from pinned tools.
- The backend remains the sole authority for session identity, leases, version
  selection, `epoch`, expected `seq`, and accepted `revision`.
- Workers are untrusted. Messages are closed, bounded, versioned, and limited to
  allowlisted model-manifest identifiers and digests. No platform/database/archive/email
  credential, playback locator, server-provided URL, arbitrary path, code, or command is
  permitted.
- Audio remains ephemeral RAM-only data. No PCM, encoded audio, audio base64, stream
  bytes, WAV, recoverable audio derivative, or audio digest may enter a source file,
  fixture, snapshot, log, queue, database, cache, or object store. Binary codec tests
  construct bounded synthetic sample bytes in memory and discard them in the test.
- JSON fixtures contain only synthetic UUIDs, timestamps, room/session identifiers, and
  text. They contain no real platform payload, account identity, secret, or production
  export.
- The Issue #2 ceilings remain upper bounds: at most 30 seconds and 960,000 bytes of
  canonical s16le/16 kHz/mono audio for each backend session and active lease, one active
  room/lease in Alpha, and 16,777,216 audio bytes process-wide. Protocol v1 deliberately
  imposes a lower one-second/32,000-byte limit per binary message.
- Changes to `epoch`, `seq`, `revision`, message meaning, or the binary layout require a
  later protocol Issue, regenerated artifacts, new golden cases, and explicit backward-
  compatibility evidence.
- Data classification: synthetic protocol metadata and restricted normalized synthetic
  transcript/event text; ephemeral in-memory synthetic audio only during codec tests.

## Success signal

`make verify` regenerates protocol artifacts without a diff and proves that Python and
TypeScript make the same accept/reject decision and return the same stable Livecho error
code for every golden case. Focused state-machine tests demonstrate duplicates,
conflicts, gaps, stale/unknown epochs, revision rules, reconnect resume/refusal, version
negotiation, and the binary boundary without writing audio anywhere.

## Human decision

- Status: Proposed
- Approved by/date: Pending
