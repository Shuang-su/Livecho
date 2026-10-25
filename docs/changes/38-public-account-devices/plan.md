# Plan: Public-account and self-service-device architecture proposal

**Draft / proposed; pending repository-owner approval.** This plan is documentation
work followed by separately gated adoption and implementation. It starts no runtime.

The sequence below is the account/device proposal's sequence. The first subtitle loop
can proceed independently under its own approved artifacts and existing source/audio
gates; it does not wait for public accounts, new platform acquisition authorization or
rankings. Email first is a delivery stage, not a reduction of the identity roadmap.

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
   ownership tests. Retain Google/GitHub/Bilibili identity entry on #12's later roadmap;
   do not infer provider login support or platform acquisition rights from email design.
7. #13 then owns an approved self-service enrollment artifact and implementation: own
   account/key binding, current private-key proof, exact challenge/token contract,
   atomic reservations/slot limits, individual revocation, contribution authorization
   and recovery. Any worker wire change first needs the owning protocol artifact and
   compatibility evidence. The reviewed real-audio risk/rights scope remains a gate.
8. #17 owns approved account/no-history-grant/own-device interfaces alongside existing
   operator/admin surfaces. Prove cross-role/ownership denial, no raw-cache exposure,
   accessible states and safe destructive controls. Deliver personal device management
   and own contribution feedback before any voluntary public leaderboard. It cannot
   grant what #12/#13 deny.
9. Before enablement, record the actual deployment's limits, mail budget, abuse response,
   privacy/recovery evidence and any named residual-risk decisions. Inventory any existing
   identities/devices before defining a migration; never assume existing elevated roles
   can be discarded or that old invitation tokens may become public enrollment tokens.
10. Enable only the individually completed account/device capability under a bounded
    rollout. All ingest, model, real-audio, retention and source gates remain independent.

## Retained goals and follow-on decisions

| Goal / stage | Owning work | Required decision before implementation |
| --- | --- | --- |
| First account/device phase: public email accounts, self-service own devices and private own-contribution feedback | #12 accounts; #13 devices/aggregates; #17 interfaces | Owner adoption of #38 and each owning artifact, with the unchanged security, quota, history and revocation rules. |
| Later Google, GitHub and Bilibili identity entry | #12 identity contracts; #17 account interfaces | Supported provider mechanisms and evidence, binding/linking, recovery and revocation; no provider or OAuth capability is presumed. |
| Later voluntary public leaderboard, after personal device and contribution feedback | #13 contribution contract; #17 publication interface | Explicit opt-in, publication scope, privacy and withdrawal; no automatic publication, authority, financial value or quota increase. |
| Any future platform acquisition authorization outside the current anonymous channel | Existing rights/policy governance; a separate scoped Issue is required before expansion | Supported authorization and rights evidence plus explicit policy adoption. Site login, identity linking, self-service enrollment and this roadmap supply no such authorization. |

These rows retain product goals without creating an empty Issue, login/Cookie/OAuth
contract or implementation approval. Provider feasibility and the later leaderboard's
publication contract remain open; the first email/device phase does not depend on them.

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
| Reader treats email-first scope as removal of Google/GitHub/Bilibili identity entry | All three remain explicit later goals, owned by #12/#17, with provider contracts and approval still pending. |
| Reader treats a future provider login as platform permission or worker identity | Site identity, acquisition authorization and device key proof remain separate; no current anonymous-ingest or worker-rights rule changes. |
| Personal device/feedback delivery, voluntary leaderboard and first subtitle loop are sequenced | Own-device/feedback work precedes public ranking; the subtitle loop has no public-account, new platform-authorization or ranking prerequisite. |
| New email proof request; matching existing/suspended/nonexistent address | Same well-formed-request response; no role/history/device authority before valid proof. |
| Two confirmations of the same proof or two redemptions of the same enrollment race | One account/consumption/association; no duplicate session or quota slot from replay. |
| Verified account without viewer attempts history; contributor attempts another account's statistics | Denied without exposing restricted metadata; device activity grants neither permission. |
| Active verified operator enrolls/revokes own device, then targets another account's device | Own baseline action may pass its independent gates; cross-account administration is denied. Operator role alone supplies no history grant. |
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
Later provider identity and voluntary-publication contracts remain pending in the
owning work above. Authorization to revise this proposal approves none of those contracts
and does not approve deployment or amend current invitation or anonymous-ingest rules.
