# ADR proposal: Public account entry and account-owned devices

- Status: **Proposed — pending repository-owner approval; not an effective override**.
- Date: 2026-10-05 Asia/Shanghai.
- Owning Issue: [#38](https://github.com/Shuang-su/Livecho/issues/38).
- Candidate successor scope: only the invitation/account/device authorization clauses
  listed below. No canonical ADR number or supersession is active yet.

## Context and recommendation

The user wants public Livecho accounts and self-service joining of their devices.
Current #12/#13/#17 and Issue #2 tie account entry, history and device enrollment to
invitation/admin controls. An explicit authority split permits open account entry
without making public signup a grant of historical data, platform rights or worker trust.

Recommend the [specification](spec.md): public email proof establishes a Livecho account;
normalized history remains independently granted; an active verified account can enroll
and revoke its own devices under bounded reservations. Device challenge authentication,
model/protocol acceptance, lease eligibility and real-audio rights/privacy gates are
separate. The existing modular monolith remains the sole online application authority.

Email magic links reuse an existing accepted authentication direction. A new social or
platform login must supply its own supported identity contract, scopes, binding, recovery,
revocation and rights evidence; the existence of a Livecho account implies none of them.

## Proposed permission matrix

All rows are proposals. Every permission also requires current source, safety, data and
recovery policy. Every still-active, verified account retains the own-account/device
baseline, including accounts labeled contributor, operator or admin. A role adds only
its explicitly named capabilities; it does not itself add a history grant. Deny other
permissions by default. Suspension/revocation still removes the affected authority.

| Actor/state | Proposed account/device/history permissions | Powers not created by this state |
| --- | --- | --- |
| Anonymous | Existing approved public live; request bounded email proof. | History, contribution/identity lookup, device enrollment, room control. |
| Verified active account without history grant | Own account/session controls; fresh-auth own-key enrollment; own devices/reservations/revocation and own aggregates. | Normalized history, another account's devices/stats, operator/admin powers. |
| Explicit viewer/history grant | Source-authorized normalized history in addition to the account's own baseline capabilities. | Raw access or new device/room/global authority. |
| Contributor label | Describes participation/own aggregates; does not automatically grant viewer. | Trusted-worker status, quota increases, public rankings, financial value. |
| Operator | Own-account/device baseline plus existing eligible-room control and emergency tightening actions. | Role administration, cross-account device administration, account takeover, relaxed platform restrictions. |
| Admin | Existing audited privileged controls plus subject-independent device/history-grant management. | Owner governance/risk bypass, untracked raw disclosure, new platform permission. |
| Worker device | Own current key challenge and, independently, only an admissible lease. | Browser account session, platform/database/email/archive credentials. |

## Exact amendment map

The following are current clauses, not edits performed by this PR. Canonical document
updates and follow-on artifacts must explicitly adopt only an owner-approved decision.
Historic accepted Issue #2 intent/spec/plan remain immutable records.

| Current source/clause | Proposed replacement or retained boundary | Follow-on owner |
| --- | --- | --- |
| #12 invited list; no public registration | Invitation no longer required for public email-verified account creation; existing magic-link/session security retained. | #12 |
| Issue #2 spec role matrix; threat model Invited viewer / Contributor inherits viewer | Verified account has own-account/device baseline; history grant remains independent; contributor does not imply history. | #12/#17 |
| #13 administrator-issued 24-hour enrollment token; contributor barred from issuance | Fresh-auth account issues a 10-minute, own-account/key-bound reservation within quotas; admin retains emergency controls. | #13 |
| Issue #2 admin-only device management; lifecycle DATA-WORKER-DEVICE | Subject may list/revoke its own devices; admin retains broader audited control; same deletion/recovery guarantees. | #13/#17 |
| #17 invited history and admin invitation screens | Account/no-history-grant/own-device states; remove invitation dependency only after approval; retain restricted historical data and existing privileged boundaries. | #17 |
| ADR 0001 `FLOW-ALLOW-002`; lifecycle `DATA-NORMALIZED-EVENT` invited-history wording | Explicit viewer/history grant replaces the invitation dependency; source/field publication, retention and deletion gates remain. | #12/#17 and canonical adoption |
| ADR 0001 FLOW-ALLOW-010 / Resend invited-address description; lifecycle account identity | Minimum verified-or-verifying contact address and one-time proof within bounded public flow; no general address publication. | #12 |
| ADR 0001 and threat model identified invited real-audio worker wording | Enrollment source may become self-service only after explicit amendment; real-audio disclosure risk/rights scope must be reviewed for that population, with no automatic acceptance. | #13 plus existing rights/risk governance |
| Bilibili public-ingest policy `BILI-RIGHT-WORKER` and its identified-invited-worker prerequisite | Retained. Self-service registration does not satisfy this current real-PCM prerequisite. Any future expansion to that worker population requires a separate explicit rights/policy amendment and risk decision. | Existing rights/risk governance; outside this public-account adoption |
| Issue #2 account/device checkpoints and restore, public anonymous ingest, worker no-secret flows | Retained; no amendment to their authority, ordering, scope or enablement prerequisites. | Existing owning Issues |

Canonical targets after approval are ADR 0001, the Alpha threat model's actors/entry
points/role/control/risk rows, and data-lifecycle account/device/counter and normalized
history-access provisions. The platform public-ingest policy and protocol remain
unchanged by this account/device adoption, including the retained real-PCM prerequisite
above. The operator-selected free anonymous acquisition limit remains unchanged even
if a later worker-population amendment is proposed. An audit/operations
cross-reference update may explain new issuance stops but cannot redefine global/room
safety or recovery sequencing. Exact adoption diff must be reviewed separately from this
proposed text; no existing authoritative file is modified here.

## Alternatives and consequences

- Retaining invitation for account/device entry contradicts the requested direction.
- Automatically granting all verified accounts viewer access removes an authorization
  barrier for restricted history. It is an explicit alternative, not the recommendation.
- Registration that waits for an admin invitation under a new name would not be
  self-service. Protocol/model/safety/rights checks remain legitimate independent gates.
- Public entry raises email cost, automated-account, device-churn and ownership-abuse
  exposure. The proposed low initial quotas bound issuance, not unique humans or the
  trustworthiness of workers. Shared networks may face limits and require operational
  review. These costs must be accepted or the proposed limits revised before enablement.
- A separate identity microservice is unnecessary for this change; existing authority,
  database and recovery boundaries suffice. No distributed limiter is required here.

## Owner decision register

| Decision | Recommendation | Owner alternatives / approval state |
| --- | --- | --- |
| PUB-ACCOUNT-001 | Public email-verified accounts with no invitation prerequisite; retain existing magic-link/session controls. | Pending owner adoption. Social/platform auth is a future separate contract. |
| HIST-GRANT-001 | Independent explicit viewer/history grant. | Owner may choose automatic viewer for every verified account only with an explicit authorization/source-risk amendment; currently pending. |
| DEVICE-SELF-001 | Verified active account may enroll/revoke only its own devices with key proof and independent task gates. | Pending owner adoption; this is not real-audio risk acceptance. |
| LIMIT-38-001 | Adopt the exact initial rolling limits, slot accounting and failure semantics in spec.md. | Owner may review different explicit values before approval; no implicit production capacity claim. |
| ADOPT-38-001 | Perform the bounded canonical amendments and approve owning artifacts before implementation/enablement. | Pending; new named/high residual decisions and operational evidence remain required. |

No approver/date is recorded yet. Drafting authorization is not decision approval, and
document approval is not a deployment, real-audio disclosure or platform authorization.
