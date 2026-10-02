# Implementation plan: Bounded memory audio

## Order of work

1. Obtain owner merge of these artifacts and record a fresh independent implementer
   exposure/assignment before runtime code. Use one Issue #8 implementation PR.
2. Define the closed synthetic source, segment handle, state/reason and reservation
   contracts. Implement ledger/ownership, input validation and terminal state changes
   before integrating any decoder or consumer.
3. Implement the integer VAD and exact sample-based segmenter with independent metadata
   expectations at every onset/silence/max-duration/context/EOF boundary. Generate all
   samples in process; do not add audio, hashes or recoverable fixture encodings.
4. Pin and approve the minimal FFmpeg build, license, executable digest and dependency
   inventory. Prove raw-format-only I/O, allocator/pipe limits, no-write/no-paging and
   crash behavior. If the accepted cap cannot be enforced, stop with the documented
   preflight failure; do not replace it with a sampled-memory claim.
5. Implement fixed no-shell invocation, parent watchdog, deadlines, descriptor ownership,
   exit monitoring and idempotent TERM/KILL/reap. Exercise abrupt parent death with an
   outer trusted test supervisor; no hardware/self-hosted untrusted PR execution.
6. Connect the source, decoder, ring and one borrowed segment using admission-before-
   allocation. Add pause/drop/terminal counters and bounded synthetic restart budget.
   Confirm no callback, timer, or retry can retain audio after its attempt closes.
7. Independently review the proposed overlap framing against accepted Issue #3 prose
   and validators. Prove all old fixtures unchanged and new metadata-only overlap
   cases accepted under the existing semantics. A conflict requires a protocol Issue;
   do not amend binary behavior in Issue #8 or silently remove overlap.
8. Add `make audio-check`, scoped synthetic tests and privacy/supervision checks to
   normal verification where the approved decoder is available. Distinguish pure
   deterministic checks from trusted host guarantees in evidence.
9. Record exact commands, test counts, byte/allocation inventory, timing outcomes,
   process cleanup and attempted-write evidence. Hand the local memory interface to
   Issue #9; keep Issue #7 and production/real-audio gates closed.

## Verification

Artifact commands: `git diff --check`, `make artifacts`, `make verify`, and changed-path
inspection. This PR creates only the four Issue #8 Markdown files.

Future implementation commands: `make bootstrap`, `make audio-check`, `make verify`,
`make protocol-check`, `git diff --check`. Record executable version/SHA verification
and the exact trusted host invocation in evidence; no undocumented local binary counts.

Verification matrix must include both formats; byte/sample boundaries; 30-second media
span; exact 960,000/16,777,216 ceilings; retained-view versus duplicate ownership;
500 ms consumer pause; 1-second handle expiry; 2-second stalls; retry exhaustion;
permission/source invalidation during retry; TERM-resistant decoder; SIGKILL parent;
watchdog failure; repeated teardown; and no stale child/handle after restart. Normal
EOF is distinct from malformed partial input and loss. Prove all no-state-change
protocol rejection cases remain unchanged.

Scan sandbox temp/cache/log/output directories, intercept attempted file/network/store
writes, and inspect database/object-store doubles after normal and fault-injected runs.
Use a sink that rejects before retaining or printing bytes; a negative privacy test
must not create the prohibited audio artifact it is meant to detect. Include supported
host paging/crash evidence; filesystem scans alone cannot prove the invariant.

## Rollout and rollback

No deployment or global-safety switch change. Only synthetic local integration is
eligible after owner acceptance. Failure closes admission, clears audio and reaps the
decoder; an earlier implementation can be restored only with the same caps/protocol.
There is no audio recovery or stored replay. Platform integration remains a later
accepted Issue and cannot bypass these preflight or rights gates.

## Open decisions

The proposed source formats, energy threshold, timing, memory partitions, retry budget,
ownership, and failure behavior are fixed for owner review. Exact FFmpeg build/digests,
host proof and independent protocol interpretation are evidence gates; missing evidence
blocks the affected runtime/integration. A new encoded input or conflicting protocol
interpretation requires an explicit artifact/protocol decision before code.
