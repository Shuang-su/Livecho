# Implementation plan: Long-session state lifecycle and resynchronization

## Order of work

1. **This pull request is documentation only.** Merge `intent.md`, `spec.md`, and
   `plan.md` before any protocol code. The diff for this pull request is the four
   files in `docs/changes/27-long-session-state/`. Do not close #27.
2. After owner merge, open a separate `issue/27-long-session-state-impl` branch
   from that main commit. Record implementer exposure in `evidence.md` before
   editing Python.
3. Extend the Pydantic source only as the spec's schema section allows. Keep
   every minor-0 `protocol_minor` literal at 0. Add a closed minor-1 twin for
   each post-selection message in that section, including `LeaseV1`,
   `TranscriptSegmentV1`, `TimelineEventV1`, `ProtocolAckV1`, and
   `ProtocolErrorV1`. Add `EpochRotatedV1` and `ViewerResyncV1` as minor-1-only
   messages. Leave `LeaseCancelV1.reason`, `audio_origin`, and timeline payload
   shapes unchanged on both twins.
4. Extend negotiation to the spec's offer table. Keep today's results for every
   existing hello and subscribe fixture.
5. Add a minor-1 session machine beside the existing minor-0 machines. Minor 0
   `RevisionDomain` and sequence windows stay free of tombstones and rotation.
   The minor-1 commit is atomic and covers both `revision_capacity` and
   `lease_replaced`. Stage the successor epoch and publish it in one assignment
   so a failed commit cannot leave a tombstone without a new epoch.
6. Implement media-floor checks and header-minor checks. PCM tests pass integers
   only and must not retain payload bytes.
7. Regenerate schema, TypeScript, and compatibility JSON with the existing
   generator. Add `long-session-` golden cases to the shared manifest. Run both
   language runners.
8. Add `tests/protocol/test_long_session.py` for the 4,095 / 4,096 / 4,097
   counts, three crossings, duplicate-final and old-epoch isolation, cursor
   table, session-versus-epoch media time, tombstone eviction at 8, and
   `epoch_exhausted` without wrapping. Assert record counts and logical ceilings,
   not process RSS.
9. Confirm `git diff` does not touch `services/`, `apps/`, `workers/`, ingest, or
   the #30 index. Append implementation commands to this issue's `evidence.md`
   only. Do not rewrite the merged intent, spec, or plan.
10. Open one implementation pull request. #15, #19, and the #30 navigation update
    stay in their own later changes. #9 remains minor 0.

## Verification

**This artifact pull request:**

- `make artifacts`
- `git diff --check`
- `LIVECHO_HEAD_REF=issue/27-long-session-state make verify`
- Local Markdown link check for the four new files
- `git diff --name-only origin/main` lists only those four files

**Later implementation pull request:**

- `make protocol-generate`
- `git diff --exit-code` is empty after a second generate
- `make protocol-check`
- `uv run pytest -q tests/protocol/test_long_session.py tests/protocol`
- `pnpm --filter @livecho/protocol test`
- `make verify`
- `git diff --check`
- A scan of the diff for audio fixtures, base64 payloads, WAV, credentials, and
  paths outside `packages/protocol`, `tests/protocol`, and this evidence file

Skipped hardware, live ingest, and real-audio checks stay recorded as not run.
They are not passes.

## Rollout and rollback

No service, flag, or deployment changes in either pull request. Minor 1 is
absent until a later consumer negotiates it. Rollback of the implementation
reverts the Pydantic source and every generated artifact together. Minor-0
fixtures must still match. A rolled-back reader rejects minor 1 instead of
downgrading an open session or restoring a retired epoch.

## Open decisions

None. Identity ceilings, negotiation, tombstone contents, media floors, cursor
reasons, new codes, and the implementation path list are fixed above. A change
to any of them needs a new owner-reviewed artifact before code that depends on
the change.
