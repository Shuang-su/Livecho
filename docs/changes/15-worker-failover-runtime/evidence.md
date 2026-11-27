# Evidence: Minor-1 scheduling runtime proposal

## Artifact approval and exposure

- Proposed. Owner merge and implementation evidence pending.
- Base `63783a514002cfbfa43f6ac9ef3962a8975ebd50`, branch
  `codex/issue-15-failover-artifacts`. This publication follows explicit
  owner authorization to open and merge the documentation PR after review
  and CI pass.
- 2026-11-27: Codex documented the application integration from the user's
  request, Livecho's own #13/#14/#27 contracts, the current #15 issue and
  its owner confirmation. Claude Code Opus 5.5 independently analyzed the #27
  protocol-runtime connection from first-party source fragments. This
  requirements assignment does not itself appoint a future app implementer.
  Reference-project expression, code, fixtures and assets were not inputs.

## Existing gates

- [PR #62](https://github.com/Shuang-su/Livecho/pull/62) merged the gateway
  documentation and its proof-binding revision at `63783a5`. The gateway
  implementation and this consumer implementation are separate changes.
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
