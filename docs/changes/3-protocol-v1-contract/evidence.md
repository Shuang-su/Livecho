# Evidence: Protocol v1 and cross-language compatibility

## Artifact approval

- Artifact PR: #23
- Artifact merge: `77fb21b` on `main`
- Approved by/date: @Shuang-su / 2026-08-30 (delegated merge after repository checks and
  review gates pass)

## Implementation approval

- Implementation branch: `codex/issue-3-protocol-v1-implementation`, based on
  `77fb21b`
- Implementation PR: #24
- Authorized by/date: @Shuang-su / 2026-08-30 (continue implementation and merge after
  repository checks and review gates pass)

## Automated verification

| Command | Result | Date/commit |
| --- | --- | --- |
| `make bootstrap` | Passed; uv checked the frozen environment and pnpm 11.21.0 reported the frozen workspace already up to date. | 2026-08-30 / staged artifact tree |
| `make verify` | Passed after the two exact-head P2 corrections; Ruff check/format, workspace lint, mypy, typecheck, 40 pytest tests, pnpm tests, artifact gate, and build all succeeded. | 2026-08-30 / corrected artifact tree |
| GitHub Actions `verify` | Passed in 43 seconds on the material contract head after all P1/P2 corrections. | 2026-08-30 / `3d9ffdf` / run `33269409446` |
| `make artifacts` | Passed: `change artifacts: ok`. | 2026-08-30 / staged artifact tree |
| `git diff --check && git diff --cached --check` | Passed with no whitespace errors. | 2026-08-30 / staged artifact tree |
| `git diff --cached --name-only` | Passed; exactly the four required files under `docs/changes/3-protocol-v1-contract/` were listed. | 2026-08-30 / staged artifact tree |

## Implementation verification

| Command | Result | Date/commit |
| --- | --- | --- |
| `make bootstrap` | Passed; uv verified the frozen Python environment and pnpm 11.21.0 verified the frozen two-workspace install and supply-chain policy. | 2026-08-30 / `4662d41` |
| `make protocol-generate` | Passed; rewrote the complete generated tree transactionally from the Pydantic source and pinned generator. | 2026-08-30 / `9373d55` |
| `git diff --exit-code -- packages/protocol/schema packages/protocol/src/generated packages/protocol/fixtures` | Passed after regeneration; generated Schema, TypeScript, compatibility, and fixture bytes match the committed output. | 2026-08-30 / `9373d55` |
| `make protocol-check` | Passed: `protocol generated artifacts: ok`; the checker compared all expected paths and bytes from a temporary generation. | 2026-08-30 / `9373d55` |
| `uv run pytest -q tests/protocol/test_binary.py tests/protocol/test_state.py tests/protocol/test_golden.py` | Passed: 34 focused binary, runtime, and golden-corpus tests, including equal/stale creation, sequence exhaustion, end-of-segment release, idle expiry, higher-epoch replacement, and bounded cancellation state. | 2026-08-30 / `3061ef9` |
| `uv run pytest -q tests/protocol/test_state.py tests/protocol/test_golden.py` | Passed: 30 focused runtime and golden-corpus tests, including transactional invalid replacement with no live-state retirement or active-entry leak. | 2026-08-30 / `a175430` |
| `uv run pytest -q tests/protocol/test_state.py tests/protocol/test_golden.py` | Passed: 31 focused runtime and golden-corpus tests, including a negotiated-manifest mismatch that preserves the current runtime and active count. | 2026-08-30 / `56158c1` |
| `uv run pytest -q tests/protocol/test_models.py tests/protocol/test_golden.py` | Passed: 36 focused model/parser and golden-corpus tests, including integral-fraction protocol-minor version precedence. | 2026-08-30 / `47f4588` |
| `uv run pytest -q tests/protocol/test_binary.py tests/protocol/test_golden.py` | Passed: 10 focused codec and cross-language corpus tests, including all three binary uint64 overflow boundaries. | 2026-08-30 / `8b843fb` |
| `uv run pytest -q tests/protocol` | Passed: 67 protocol tests. | 2026-08-30 / `56158c1` |
| `pnpm --filter @livecho/protocol typecheck` | Passed with TypeScript strict mode; also rerun by `make verify`. | 2026-08-30 / `9373d55` |
| `pnpm --filter @livecho/protocol test` | Passed: one Vitest file and 124 tests, comprising 123 generated parity cases plus the corpus integrity assertion; also rerun by `make verify`. | 2026-08-30 / `9373d55` |
| `make verify` | Passed; Ruff, workspace lint, mypy, TypeScript checks, 107 pytest tests, 124 Vitest tests, artifact lifecycle, protocol drift, and build all succeeded. | 2026-08-30 / `9373d55` |
| `git diff --check && git diff --cached --check` | Passed with no whitespace errors. | 2026-08-30 / `9373d55` |

The generated corpus contains 123 unique cases: 40 accepted and 83 rejected. Every
`StableCode` value occurs as an expected result. All 18 public Pydantic models have an
accepted case; the remaining cases cover parser/version/capability/manifest failures,
JSON and record-free PCM sequence boundaries, revision precedence/capacity/immutability,
all four final-object outcomes, cancellation CAS/tombstones, reconnect, RFC 8785
representation variants, and metadata-only binary/PTS/budget boundaries.

Generated output contains 21 Schema/compatibility files, one TypeScript contract, and
124 fixture files including the manifest. Negative drift tests independently prove that
a changed file, a missing file, and an unexpected extra file each fail comparison.

## Manual or hardware evidence

No hardware, live source, model, deployment, real audio, or real platform/account data
is required or permitted for this contract implementation. A manual trace covered the
six Issue models, supporting handshake/outcome/error models, both subprotocols, the
fixed binary header, ordering/reconnect outcomes, stable rejection codes, deterministic
generation, shared golden cases, minimum versions, and the Issue #2 audio ceilings.

## Review findings

- Scope review found exactly four new documentation files in
  `docs/changes/3-protocol-v1-contract/`; no runtime, dependency, fixture, schema, or
  generated file is present.
- Pre-PR protocol review found and resolved three ambiguities: worker resume state is now
  a closed `WorkerResumeV1`; viewer client/minor negotiation is explicit; and binary
  duplicate handling discards bytes without audio hashing. It also separates successful
  duplicate no-ops into `ProtocolAckV1` and defines the three allowed golden input forms.
- A second interface trace resolved the missing bounded cancellation control required by
  the accepted architecture: `LeaseCancelV1` now has exact bindings, fixed reasons,
  idempotency, terminal behavior, and no arbitrary instruction text.
- Codex review P1 found that cancellation reused the ordinary lease `revision` field
  while ordinary updates require current plus one. Resolved by defining
  `expected_revision` as a non-advancing CAS guard and pinning initial close, identical
  replay, changed replay, stale/gapped CAS, and already-closed outcomes.
- Final-head Codex review P1 found that clearing all deduplication state on close made
  cancellation replay outcomes indistinguishable. Resolved by retaining one bounded,
  120-second, in-memory terminal cancellation tombstone containing only bindings,
  message/reason/CAS metadata, and a canonical JSON digest while immediately clearing
  PCM and ordinary deduplication state.
- Final-head Codex review P2 found that the ordinary JSON deduplication window lacked a
  shared capacity and eviction rule. Resolved with an exact 256-record per-domain FIFO
  window of fixed logical records and explicit 255/256 boundary, duplicate, conflict,
  eviction, and cleanup test requirements.
- Follow-up Codex review P2 found no defined PCM replay boundary. Resolved with an exact
  256-position arithmetic window derived only from `next_expected_seq`; it stores no
  frame record, payload, or audio-derived digest and pins the 255/256 boundary outcomes.
- Follow-up Codex review P2 found that “canonical JSON” was unspecified. Resolved by
  requiring RFC 8785 JCS plus SHA-256 in both languages, strict pre-canonicalization
  validation, NFC text, and raw representation-variant parity cases.
- Follow-up Codex review P2 found that whole-message replay identity made
  `revision_duplicate` ambiguous or unreachable. Resolved with a transmission-field-free
  JCS revision projection and fixed sequence-before-revision precedence, including both
  replay forms and changed-content outcomes.
- Follow-up Codex review P2 found unbounded retained per-object revision state. Resolved
  with a no-eviction 4,096-identity/557,056-logical-byte ceiling per active domain,
  `revision_capacity_exceeded`, and capacity/update/cleanup boundary requirements.
- Exact-head Codex review P2 found that the bounded revision record could not enforce
  immutable time ranges from its complete projection digest alone. Resolved by adding a
  closed per-type immutable-field projection and second 32-byte digest to each bounded
  record, plus immutable-preserving/update-at-capacity and unchanged-state rejection
  requirements.
- Exact-head Codex review P2 found conflicting outcomes for changed content at the
  current revision of an already-final object. Resolved with an explicit internal
  precedence: identical current content is `revision_duplicate`, lower is
  `revision_stale`, and changed current content or any higher revision is
  `object_final`; all four cases are required golden cases.
- Security/data review found no permitted field for a credential, playback/download URL,
  arbitrary path/command/code/container, raw platform payload, or extensible metadata.
  The documents expressly prohibit audio fixtures, encodings, digests, persistence, and
  logging; only bounded in-memory synthetic codec bytes are planned.
- Repository-owner merge authorization is recorded above. Codex completed its review of
  material contract head `3d9ffdf` with no remaining major finding; every P1/P2 review
  thread is resolved. Cursor Bugbot is optional and remained pending, so it is not a
  merge gate. The artifact PR subsequently merged as `77fb21b` before implementation
  began on the separate branch recorded above.
- Implementation review confirmed that every public and nested model is recursively
  closed and bounded, the manifest is an identifier/digest-only equality claim, and the
  TypeScript Ajv layer enforces the generated schema plus the same semantic constraints
  as Python.
- Ordering review confirmed exact sequence-before-revision precedence, the 256-record
  JSON FIFO, the record-free 256-position PCM window, the 4,096-identity revision
  ceiling, immutable projections, final-object precedence, unchanged rejected state,
  and cleanup into a terminal lease state.
- Cancellation review confirmed a successful CAS close clears PCM bytes and ordinary
  sequence/revision state immediately, retains only a bounded metadata tombstone, and
  makes all later lease input/output return `lease_closed`.
- Generation review confirmed pinned Python/Node dependencies, stable IDs/order/LF
  output without timestamps or machine paths, rollback-capable directory replacement,
  and changed/missing/extra drift detection in `make verify`.
- Data/surface tests found no fixture audio file or binary payload and no public Schema
  field for a URL/URI, playback locator, credential/cookie, arbitrary command/code path,
  container/environment/options, raw platform payload, PCM/audio bytes, or audio base64.
  Binary tests allocate only minimal synthetic byte arrays in memory and never print,
  snapshot, or persist them.
- Implementation-head Codex review P1 found that `LeaseV1` revisions have no `seq` and
  therefore could not use the sequenced stream state. Resolved with a dedicated
  non-sequenced lease revision domain that handles duplicate/gap/immutable decisions
  and updates the cancellation CAS revision after an accepted lease revision.
- Implementation-head Codex review P1 found that the composed lease runtime did not
  enforce `expires_at`. Resolved with one deadline gate before PCM, output, lease-update,
  and cancellation decisions; expiry atomically clears all three ordinary state domains,
  removes the active cancellation entry, and remains terminal as `lease_expired`.
- Corrected-head Codex review P2 found that per-runtime cancellation registries violated
  the 64-tombstone process ceiling. Resolved with one module process-scoped registry,
  coordinator-created runtimes, cross-coordinator capacity tests, and authoritative
  `lease_closed` after oldest-entry eviction.
- Corrected-head Codex review P2 found that idle tombstones were pruned only by a later
  cancellation. Resolved with a coordinator `prune(now)` scheduling entry point and an
  exact 120-second idle-prune test that requires no new cancellation.
- Corrected-head Codex review P2 found that JavaScript accepted timestamp year `0000`
  while Python rejected it. Resolved in the TypeScript canonical timestamp format and a
  shared year-zero golden case.
- Corrected-head Codex review P2 found that acknowledgement positions were not tied to
  their outcomes. Resolved in Python and TypeScript with exact sequence/cancellation
  positions, required revision plus optional sequence for revision duplicates, and
  eight accepted/rejected shared Ack combinations.
- Final-head Codex review P1 found that session teardown removed cancellation metadata
  without closing live lease runtimes. Resolved with process-scoped session/runtime
  tracking, atomic clearing of PCM, output, and lease-revision domains, terminal
  `lease_closed` decisions, and a cross-coordinator teardown regression test.
- Final-head Codex review P2 found that the shared Ack/Error envelope models classified
  unsupported major versions as `schema_invalid`. Resolved with an explicit two-protocol
  v1 allowlist in Python and TypeScript plus shared worker-Ack and viewer-Error v2 golden
  cases that both require `unknown_major`.
- Exact-head Codex review P2 found that errors from the nonmatching timeline payload
  union branch could turn a known invalid value into `unknown_field`. Resolved by
  selecting the transcript or session-status branch before classification in both
  languages and pinning an empty known transcript text as `schema_invalid`.
- Exact-head Codex review P2 found that the metadata-only PCM golden evaluator skipped
  lower-sequence replay decisions. Resolved with the full input-start/next-expected
  256-position arithmetic window in both evaluators and a shared case where
  `seq_duplicate` takes precedence over simultaneous invalid PTS and budget state.
- Follow-up Codex review P2 found that Python 3.12 timestamp formatting omitted leading
  zeros for years 0001 through 0999. Resolved with explicit fixed-width component
  formatting and an accepted shared year-0001 case; year 0000 remains rejected.
- Follow-up Codex review P2 found that coordinator-created runtimes defaulted the process
  PCM usage to zero. Resolved with one process-scoped logical byte budget updated on
  accept, consume, cancellation, expiry, and session teardown, plus an 18-runtime exact
  boundary test that reuses one synthetic in-memory frame and proves final cleanup.
- Subsequent Codex review P2 found that a partial timeline payload containing known
  transcript fields but missing `segment_id` could still inherit extra-field errors from
  the status branch. Resolved by selecting unambiguous partial branches and classifying
  `unknown_field` only for keys outside the union of all timeline payload fields in both
  languages; known partial and mixed payloads are `schema_invalid`.
- Subsequent Codex review P2 found that TypeScript reported a duplicate key before a
  later JSON syntax error while Python reported malformed JSON. Resolved by completing
  native JSON syntax parsing before the duplicate-key scan and pinning the combined
  malformed-plus-duplicate input as `malformed_json` in the shared corpus.
- Later Codex review P2 found that multiple leases in one session could exceed the
  session PCM ceiling. Resolved with a process-scoped ledger that tracks both session and
  process logical bytes and releases them on consume, cancellation, expiry, and teardown;
  separate session and process boundary regressions use one reusable synthetic frame.
- Later Codex review P2 found that version prechecks ran on closed nested models and on
  malformed or missing envelope fields. Resolved by limiting negotiation decisions to
  envelope models with present, correctly typed protocol and minor fields; four shared
  cases pin nested extra-field and malformed-envelope results.
- Later Codex review P2 found JavaScript safe-integer collapse in semantic ordering
  evaluators. Resolved by using `bigint` for sequence, epoch, revision, PCM position, and
  binary uint64 comparisons, with five shared cases above `2^53` including an accepted
  next revision.
- Later Codex review P1 found that a cancellation for lease B passed to runtime A could
  close B in the shared registry while clearing A. Resolved by validating lease, session,
  and epoch against the addressed runtime before touching the registry; a two-runtime
  regression proves neither runtime is incorrectly closed.
- Later Codex review P2 found Python could surface a nested duplicate before a later outer
  syntax error. Resolved by completing a bounded syntax parse before the duplicate-aware
  parse and pinning a nested-duplicate-plus-malformed document as `malformed_json`.
- Exact-head Codex review P2 found runtime revision capacity was checked after the
  initial-revision rule. Resolved by making capacity authoritative for every new identity
  at 4,096 records and pinning the combined capacity-plus-gap input.
- Exact-head Codex review P2 found the metadata-only binary evaluator accepted epoch zero
  structurally. Resolved with the same positive-epoch check as the executable codec and a
  shared epoch-zero case requiring `binary_header_invalid`.
- Exact-head Codex review P2 found JSON Schema and strict Pydantic disagreed on integral
  fractional spellings such as `0.0`. Resolved by normalizing only finite integral JSON
  floats to integers in Python while rejecting booleans, strings, and nonintegral floats;
  three raw-text shared cases pin the aligned behavior.
- Final exact-head Codex review P1 found that coordinator pruning removed only expired
  cancellation tombstones, leaving an idle expired runtime's PCM and session/process
  budget live until another lease entry point ran. Resolved by having the scheduler
  prune every tracked runtime at the exact lease deadline and by a no-follow-up-message
  regression that proves PCM, active cancellation state, and both budgets are cleared.
- Final exact-head Codex review P1 found that creating a higher-epoch non-resumed lease
  left lower-epoch runtimes authoritative. Resolved by atomically closing and removing
  every superseded runtime before registering the replacement, clearing PCM, output,
  lease-revision, cancellation, and budget state; a runtime regression and shared
  `epoch.non_resumed_replacement_clears_state` golden transition pin the behavior.
- Final exact-head Codex review P2 found that Pydantic numeric literals treated booleans
  as equal integers while JSON Schema and Ajv rejected them. Resolved by applying the
  boolean-rejecting JSON-integer normalizer to protocol/selected minor, sample-rate, and
  channel literals; four shared raw-text cases pin each boolean rejection in Python and
  TypeScript.
- Final exact-head Codex review P1 found that creating an older epoch after epoch 2 left
  the stale runtime able to accept its own PCM/output. Resolved with a process-scoped,
  session-lifetime epoch watermark checked before construction; stale creation remains
  rejected even after the current runtime expires, and a shared transition pins
  `epoch_stale`.
- Final exact-head Codex review P2 found that an accepted `END_OF_SEGMENT` frame left its
  logical PCM and aggregate session/process accounting charged. Resolved by clearing the
  lease PCM count on the accepted transition and applying its negative delta to both
  ledgers while retaining sequence/PTS ordering; direct and coordinator regressions plus
  an accepted binary flag case cover the boundary.
- Final exact-head Codex review P2 found that the separate authoritative `closed` lease
  dictionary grew without the 64-entry tombstone bound. Resolved by removing that map:
  the bounded tombstone owns replay classification, while the addressed runtime owns
  durable terminal `lease_closed` authority after tombstone expiry or eviction. Capacity,
  expiry, and session teardown tests pin the split.
- Final exact-head Codex review P2 found that an epoch above uint64 passed the encoder's
  lower-bound-only predicate and escaped as `struct.error`. Resolved with one shared
  uint64 maximum in the executable codec and explicit epoch/sequence/PTS lower/upper
  structural checks in both metadata evaluators; three shared overflow cases require
  `binary_header_invalid` before ordering or epoch comparison.
- Final exact-head Codex review P1 found that equal-epoch construction could register a
  second authoritative runtime. Resolved by rejecting it before construction with
  `resync_required`, leaving the exact live runtime untouched for the existing resume
  path; invalid same-session multi-runtime tests were replaced with authority-conforming
  lease/session/process scenarios and a shared equal-epoch transition.
- Final exact-head Codex review P2 found that accepting sequence uint64 maximum would
  increment the next cursor outside the wire domain. Resolved by returning
  `resync_required` before commit while retaining the maximum cursor, with commit guards
  and shared JSON, record-free PCM, and binary-metadata exhaustion cases in both runners.
- Final exact-head Codex review P1 found that a schema-valid higher-epoch lease with
  initial revision 2 retired the current runtime before failing and leaked an active
  cancellation entry. Resolved by making candidate construction side-effect-free,
  returning the initial revision decision before any retirement, then activating only
  after successful validation; a shared revision-gap transition and runtime regression
  prove the prior PCM/output/authority state remains intact and the active count unchanged.
- Final exact-head Codex review P1 found that `LeaseV1.model_manifest` had only shape
  validation after the worker handshake. Resolved by requiring each coordinator to hold
  the negotiated complete manifest-key set and rejecting a lease reference/digest before
  any epoch or runtime mutation; Python and TypeScript shared decisions also compare the
  complete reference, and a mismatch regression proves the existing runtime, PCM, and
  active-lease count remain unchanged.
- Final exact-head Codex review P2 found that Python version prechecks skipped JSON
  Schema integer spellings such as `protocol_minor: 1.0`, producing `schema_invalid`
  where TypeScript returned the negotiated version error. Resolved by normalizing only
  finite integral minor values before the precheck; two raw-text shared cases pin
  `unsupported_minor` and unknown-major precedence in both languages.
- Final exact-head Codex review P2 found that TypeScript handshake decisions did not
  require `supported_minors` to contain minor 0, while Python negotiation did. Resolved
  by applying the same check before version/capability/manifest decisions for worker and
  viewer handshakes; two shared cases pin `unsupported_minor` in both languages.

## Deviations

None.

## Release and rollback evidence

Not deployed or wired to production runtime paths. Before downstream integration, the
complete rollback is a normal revert of the implementation commit; generated outputs
are recreated from the reverted Pydantic source and pinned toolchain.
