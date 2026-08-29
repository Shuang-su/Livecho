# Evidence: Protocol v1 and cross-language compatibility

## Artifact approval

- Artifact PR: #23
- Approved by/date: @Shuang-su / 2026-08-30 (delegated merge after repository checks and
  review gates pass)

## Automated verification

| Command | Result | Date/commit |
| --- | --- | --- |
| `make bootstrap` | Passed; uv checked the frozen environment and pnpm 11.21.0 reported the frozen workspace already up to date. | 2026-08-30 / staged artifact tree |
| `make verify` | Passed; Ruff check/format, workspace lint, mypy, typecheck, 40 pytest tests, pnpm tests, artifact gate, and build all succeeded. | 2026-08-30 / staged artifact tree |
| `make artifacts` | Passed: `change artifacts: ok`. | 2026-08-30 / staged artifact tree |
| `git diff --check && git diff --cached --check` | Passed with no whitespace errors. | 2026-08-30 / staged artifact tree |
| `git diff --cached --name-only` | Passed; exactly the four required files under `docs/changes/3-protocol-v1-contract/` were listed. | 2026-08-30 / staged artifact tree |

## Manual or hardware evidence

No hardware, live source, model, deployment, real audio, or real platform/account data
is required or permitted for this artifact-only change. A manual trace covered the six
Issue models, supporting handshake/outcome/error models, both subprotocols, the fixed
binary header, ordering/reconnect outcomes, stable rejection codes, deterministic
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
  with a no-eviction 4,096-identity/425,984-logical-byte ceiling per active domain,
  `revision_capacity_exceeded`, and capacity/update/cleanup boundary requirements.
- Security/data review found no permitted field for a credential, playback/download URL,
  arbitrary path/command/code/container, raw platform payload, or extensible metadata.
  The documents expressly prohibit audio fixtures, encodings, digests, persistence, and
  logging; only bounded in-memory synthetic codec bytes are planned.
- Repository-owner merge authorization is recorded above. External PR review remains
  pending. Implementation and generated files wait for the artifact PR to merge.

## Deviations

None.

## Release and rollback evidence

Not deployed. This artifact-only change has no runtime rollback.
