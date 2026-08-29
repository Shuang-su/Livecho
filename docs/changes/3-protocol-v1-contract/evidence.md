# Evidence: Protocol v1 and cross-language compatibility

## Artifact approval

- Artifact PR: Pending
- Approved by/date: Pending

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
- Security/data review found no permitted field for a credential, playback/download URL,
  arbitrary path/command/code/container, raw platform payload, or extensible metadata.
  The documents expressly prohibit audio fixtures, encodings, digests, persistence, and
  logging; only bounded in-memory synthetic codec bytes are planned.
- Repository-owner approval and external PR review remain pending. Implementation and
  generated files wait for the artifact PR to merge.

## Deviations

None.

## Release and rollback evidence

Not deployed. This artifact-only change has no runtime rollback.
