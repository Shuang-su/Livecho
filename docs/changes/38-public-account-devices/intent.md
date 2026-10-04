# Intent: Public Livecho accounts and self-service device boundaries

## Issue and owner

- GitHub Issue: [#38](https://github.com/Shuang-su/Livecho/issues/38).
- Human owner: @Shuang-su.
- Stage/area/risk: M2 architecture and identity; high authorization/privacy risk.
- Status: **Draft / proposed — pending repository-owner approval**.

## Problem

The current architecture and Issues #12/#13/#17 require invited accounts and
administrator-issued device enrollment. The user's 2026-10-05 direction is to remove
invitation as the account/device entry requirement and offer one Livecho account with
self-service joining of that account's devices. Simply deleting invitation checks would
also expand history access and device authority without a reviewed decision.

## Desired outcome

Propose an explicit amendment separating email-verified account ownership, normalized
history authorization, ownership of a worker device, device authentication, task
eligibility and platform acquisition permission. Public email verification is the first
phase. Social/platform login is a future separate contract, not a claimed integration.

A verified account may register and revoke only its own devices within published bounds.
Independent history authorization is the recommended default. Operator/admin powers,
platform selection, protocol/model admission and real-audio disclosure gates stay
separate. No new infrastructure or second application authority is needed.

## Non-goals

- Product code, schema/API/protocol changes, deployments, live registration or migration.
- Immediate replacement of accepted documents or invitation/role behavior by this draft.
- Platform OAuth or credential acquisition, a changed anonymous-ingest policy, public
  room submissions, public contribution rankings or financial rewards.
- New ASR/subtitle behavior, model download/transfer or real-audio worker enablement.

## Constraints and data impact

- Backend remains the sole authority. Workers receive no platform credentials, cookies,
  signed playback locators, archive keys, email credentials or browser session bearer.
- Existing account/device revocation, deletion, recovery and payload-free audit rules
  remain required; a verified email does not establish a trusted worker or content rights.
- This proposal processes no personal data. Future data remain restricted: verified
  contact address, opaque account/device identity, ownership, authorization state and
  own aggregate statistics. Proposed short-lived abuse counters are specified separately.
- Numeric limits are conservative local product proposals, not vendor policy or measured
  capacity. Approval and later executable evidence are prerequisites to enablement.

## Success signal

A reviewer can identify every permission granted and withheld, trace each invitation
clause to its proposed replacement and owning follow-on Issue, and test races, limits,
revocation and recovery without inferring new history or platform permissions.

## Human decision

- Status: Proposed; drafting authorized, architecture decisions not yet approved.
- Approved by/date: Pending. See the decision register in [the ADR draft](adr-proposal.md).
- Creating this Issue or merging documentation alone is not production authorization.
