# Implementation plan: Protocol v1 and cross-language compatibility

## Order of work

1. Merge this artifact-only change with no runtime, dependency, schema, fixture, or
   generated-code changes. Start implementation from the resulting `main` commit on a
   separate Issue #3 branch.
2. Add pinned Pydantic v2 and protocol workspace dependencies, create the Python and
   TypeScript package layout specified above, and add root `protocol-generate` and
   `protocol-check` Make targets. Keep every existing workspace script contract green.
3. Implement the strict Pydantic scalar/envelope/supporting models, six required public
   models, closed CAS-based `LeaseCancelV1`, compatibility matrix, stable codes, and
   semantic invariants. Unit-test model boundaries before generating downstream files.
4. Implement the 56-byte binary header encode/decode and boundary validation. Tests must
   construct only minimal synthetic sample bytes in memory, must not print/snapshot/write
   them, and must assert cleanup and unchanged budget on rejection.
5. Implement pure bounded in-memory ordering state machines for epoch authority,
   directional sequences, revisions, terminal objects, cancellation tombstones, and
   reconnect decisions. Test every transition, duplicate/conflict distinction, gap,
   the exact 256-record per-domain FIFO boundary, tombstone expiry/capacity,
   cross-binding rejection, and no-state-change failure path without implementing
   scheduling or persistence.
6. Implement deterministic draft-2020-12 JSON Schema, compatibility JSON, and TypeScript
   generation. Normalize ordering/line endings/IDs, reject nondeterministic metadata,
   generate atomically, and add a temporary-directory drift comparison that detects
   changed, missing, and extra files.
7. Add the accepted/rejected synthetic JSON golden corpus and raw duplicate-key cases.
   Run it through the Python validators and TypeScript Ajv plus semantic validators;
   compare decision and stable code, not dependency-specific diagnostic strings. Keep
   binary cases metadata-only and add a repository scan proving that no audio fixture or
   obvious encoded-audio form was added.
8. Export the generated TypeScript contract from the protocol workspace, implement all
   required `lint`, `typecheck`, `test`, and `build` scripts, and wire protocol drift and
   parity into `make verify`/CI. Do not mount endpoints or enable any production path.
9. Update only this Issue's `evidence.md` with exact commands, commit, generation/parity
   case counts, diff review, and deviations. Review the complete diff for secrets,
   locators, arbitrary execution/download surfaces, real platform data, audio artifacts,
   and scope belonging to later Issues before opening the implementation PR.
10. Open one implementation PR that closes Issue #3. Resolve every deterministic check
    and review finding, obtain the required owner/risk decision, and merge only when the
    accepted artifacts, implementation, generated output, and evidence agree.

## Verification

- `make bootstrap`
- `make protocol-generate`
- `git diff --exit-code -- packages/protocol/schema packages/protocol/src/generated`
- `make protocol-check`
- `uv run pytest -q tests/protocol`
- `pnpm --filter @livecho/protocol test`
- `make verify`
- `git diff --check`
- `git diff --name-only origin/main...HEAD`
- Golden parity report: one row per case, with identical Python/TypeScript decision and
  stable code; record accepted/rejected totals in `evidence.md`.
- Generated-file-set negative tests: mutation, deletion, and unexpected extra file each
  cause the drift checker to fail.
- Protocol transition trace: every Issue #3 ordering/reconnect rule has at least one
  accept/no-op case and one rejection case proving state and budget are unchanged.
- Data/surface review: `rg` and diff inspection find no audio/WAV/base64 fixture,
  platform credential/locator/raw payload, arbitrary command/code/container/download
  field, or real account/platform identifier.
- Manual review of the generated JSON Schema and TypeScript public surface against the
  six required model names, both subprotocols, binary table, compatibility matrix, and
  minimum-version strategy.

## Rollout and rollback

Issue #3 is a contract/package change only. It does not deploy an endpoint, connect a
stream or model, issue a real lease, persist data, or enable production audio. Later
Issues import the versioned package only after their own accepted artifacts and gates.

Rollback reverts the Pydantic source, compatibility matrix, schemas, TypeScript types,
fixtures, dependencies, and verification wiring in one atomic repository change. Do not
hand-edit or partially roll back generated output. Any consumer that has advertised a
now-removed version must be disabled until its reader/writer set again matches the
committed matrix; there is no downgrade fallback.

## Open decisions

None. A request to add a message kind, payload field, binary flag, compatibility
exception, real-data fixture, or production behavior outside this specification requires
an artifact update or a later owning Issue before implementation.
