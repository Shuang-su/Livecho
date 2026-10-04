# Plan: Public-account and self-service-device architecture proposal

**Draft / proposed; pending repository-owner approval.** This plan is documentation
work followed by separately gated adoption and implementation. It starts no runtime.

## Order of work

1. Commit the actual author exposure/assignment and separate reviewer before drafting.
   Read only allowed local requirements and the original #12/#13/#17 bodies. Stop the
   affected assignment on a new prohibited exposure; do not import research comments.
2. Draft intent/spec and the supplementary ADR inside this Issue's artifact directory.
   Trace account entry, history authorization, device ownership/authentication, task
   eligibility and platform acquisition separately. Record all local numeric choices.
3. Perform independent requirements/security/privacy review on the exact documentation
   commit. Resolve ambiguities in role inheritance, same-address account creation,
   ownership, quotas, shared-network handling, revocation and restore. Do not claim
   runtime correctness, capacity measurements or legal clearance from document review.
4. Open a draft documentation PR for #38 after that review. The owner decides each ADR
   row, especially history access and numeric limits; unselected alternatives do not
   become defaults. Record approver/date/scope. Do not merge without owner authorization.
5. After approval, publish a separately reviewed canonical supplementary ADR and exact
   amendment diff for the targets in adr-proposal.md. Explicitly reference the approved
   #38 artifact. Do not rewrite accepted Issue #2 intent/spec/plan or silently replace its
   history. Update ongoing Issue descriptions/artifact plans for #12/#13/#17 accordingly.
6. #12 first owns an approved public-email account/session/history-grant artifact and
   implementation: canonicalization, proof confirmation, exact endpoints, request/email
   admission and idempotency, suspension/deletion/restore, zero self-elevation and the
   ownership tests. Do not infer platform login support from the email design.
7. #13 then owns an approved self-service enrollment artifact and implementation: own
   account/key binding, current private-key proof, exact challenge/token contract,
   atomic reservations/slot limits, individual revocation, contribution authorization
   and recovery. Any worker wire change first needs the owning protocol artifact and
   compatibility evidence. The reviewed real-audio risk/rights scope remains a gate.
8. #17 owns approved account/no-history-grant/own-device interfaces alongside existing
   operator/admin surfaces. Prove cross-role/ownership denial, no raw-cache exposure,
   accessible states and safe destructive controls. It cannot grant what #12/#13 deny.
9. Before enablement, record the actual deployment's limits, mail budget, abuse response,
   privacy/recovery evidence and any named residual-risk decisions. Inventory any existing
   identities/devices before defining a migration; never assume existing elevated roles
   can be discarded or that old invitation tokens may become public enrollment tokens.
10. Enable only the individually completed account/device capability under a bounded
    rollout. All ingest, model, real-audio, retention and source gates remain independent.

## Verification

For this document-only proposal:

- `uv run python tools/check_change_artifacts.py`
- `git diff --check`
- `git diff --name-only origin/main...HEAD` and the worktree status: only this Issue's
  four artifacts and supplementary ADR draft may differ.
- Resolve relative Markdown links and compare the amendment map with current local
  architecture and #12/#13/#17 original bodies.
- Independent exact-commit review and scenario table below, recording actual outcomes
  in evidence.md. No redundant full product test run is required for text-only changes.

| Documentation scenario | Required unambiguous outcome |
| --- | --- |
| New email proof request; matching existing/suspended/nonexistent address | Same well-formed-request response; no role/history/device authority before valid proof. |
| Two confirmations of the same proof or two redemptions of the same enrollment race | One account/consumption/association; no duplicate session or quota slot from replay. |
| Verified account without viewer attempts history; contributor attempts another account's statistics | Denied without exposing restricted metadata; device activity grants neither permission. |
| Three occupied slots; concurrent reserve/expire/revoke/redemption | At most three registered non-revoked devices plus pending reservations; no early revocation refund. |
| Mail failure/unknown delivery, repeated operation identity, changed operation identity | Original reserved cost remains; same operation sends no duplicate; new operation observes every limit. |
| Limit equality/window edge; counter unavailable or clock rolled back | Exact boundary semantics; affected issuance fails closed without account enumeration. |
| Own revocation/account deletion and invalid cross-account request during restore | Existing exact-scope target stop/checkpoint or durable denial/recovery ordering retained. |
| Valid self-enrolled device but absent real-audio/source/manifest evidence | Device ownership exists; the corresponding lease/audio/ingest remains denied. |
| Public signup stopped while existing owner revokes a device | No new issuance; authorized scoped revocation remains available subject to existing recovery safety. |

Later implementation Issues must run their required bootstrap/full deterministic checks
and executable positive/negative/competition tests. This document does not count these
future obligations as passed or authorize a real account/email/worker/platform test.

## Rollout and rollback

This PR has no deployment, migration, feature flag or changed running permissions.
An owner-approved adoption still requires canonical amendments, owning artifacts and
implementation evidence. Future rollback disables new issuance, invalidates pending
material and preserves existing revocation/deletion/history boundaries; it never infers
invitations or revives old credentials. Any proposal correction remains reviewable here.

## Open decisions

The ADR register is pending owner review. Recommended history behavior is independent
grant; numeric limits are explicit proposals, not placeholders. Any different history
choice or limit set must be recorded before adoption. Endpoint, canonicalization,
challenge and migration details belong to the named owning artifacts and must be fixed
there before code; they are not licenses for an implementer to improvise new authority.
