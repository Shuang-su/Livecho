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
| `make bootstrap` | Passed; uv verified the frozen Python environment and pnpm 11.21.0 verified the frozen two-workspace install and supply-chain policy. | 2026-08-30 / `2457dbc` |
| `make protocol-generate` | Passed; rewrote the complete generated tree transactionally from the Pydantic source and pinned generator. | 2026-08-30 / `2457dbc` |
| `git diff --exit-code -- packages/protocol/schema packages/protocol/src/generated packages/protocol/fixtures` | Passed after regeneration; generated Schema, TypeScript, compatibility, and fixture bytes match the committed output. | 2026-08-30 / `2457dbc` |
| `make protocol-check` | Passed: `protocol generated artifacts: ok`; the checker compared all expected paths and bytes from a temporary generation. | 2026-08-30 / `2457dbc` |
| `uv run pytest -q tests/protocol` | Passed: 36 protocol tests. | 2026-08-30 / `2457dbc` |
| `pnpm --filter @livecho/protocol typecheck` | Passed with TypeScript strict mode. | 2026-08-30 / `2457dbc` |
| `pnpm --filter @livecho/protocol test` | Passed: one Vitest file and 72 tests, comprising 71 generated parity cases plus the corpus integrity assertion. | 2026-08-30 / `2457dbc` |
| `make verify` | Passed; Ruff, workspace lint, mypy, TypeScript checks, 76 pytest tests, 72 Vitest tests, artifact lifecycle, protocol drift, and build all succeeded. | 2026-08-30 / `2457dbc` |
| `git diff --check && git diff --cached --check` | Passed with no whitespace errors. | 2026-08-30 / `2457dbc` |

The generated corpus contains 71 unique cases: 30 accepted and 41 rejected. Every
`StableCode` value occurs as an expected result. All 18 public Pydantic models have an
accepted case; the remaining cases cover parser/version/capability/manifest failures,
JSON and record-free PCM sequence boundaries, revision precedence/capacity/immutability,
all four final-object outcomes, cancellation CAS/tombstones, reconnect, RFC 8785
representation variants, and metadata-only binary/PTS/budget boundaries.

Generated output contains 21 Schema/compatibility files, one TypeScript contract, and
72 fixture files including the manifest. Negative drift tests independently prove that
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

## Deviations

None.

## Release and rollback evidence

Not deployed or wired to production runtime paths. Before downstream integration, the
complete rollback is a normal revert of the implementation commit; generated outputs
are recreated from the reverted Pydantic source and pinned toolchain.
