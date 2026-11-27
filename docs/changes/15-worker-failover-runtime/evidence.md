# Evidence: Minor-1 scheduling runtime proposal

## Artifact approval and exposure

- Proposed. Owner merge and implementation evidence pending.
- Base `cae5ccd951e1c761163d372dc83558c016ee96d5`, branch
  `codex/issue-15-long-session-runtime`.
- 2026-11-27: Codex documented the application integration from the user's
  request, Livecho's own #13/#14/#27 contracts, the current #15 issue and
  its owner confirmation. Claude Code Opus 5.5 independently analyzed the #27
  protocol-runtime connection from first-party source fragments. This
  requirements assignment does not itself appoint a future app implementer.
  Reference-project expression, code, fixtures and assets were not inputs.

## Existing gates

- [PR #62](https://github.com/Shuang-su/Livecho/pull/62) is the gateway
  documentation PR. Its local proof-binding revision is `8370848`.
- [Issue #27](https://github.com/Shuang-su/Livecho/issues/27) explicitly
  reserves gateway, scheduler, worker and viewer integration for their
  owning changes. The protocol adapter being validated locally only
  prepares that handoff.
- Current gateway drafts use one 20-second lease and no healthy successor.
  The app needs an approved handoff policy and measured gap behavior before
  long-running operational acceptance.

## Verification

Local artifact check, staged whitespace check and relative-link validation
are recorded with this documentation checkpoint. No socket, device,
three-worker, hardware, or production result is asserted by this draft.
