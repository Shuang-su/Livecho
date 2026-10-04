# Specification: Public accounts and self-service device boundaries

**Draft / proposed; pending repository-owner approval.** This is a proposed amendment,
not an effective override. Existing accepted invitation, role, history and ingest rules
remain in force until the explicit approval and adoption steps in [plan.md](plan.md).
No runtime capability is enabled by this document.

## Behavior

### AUTH-38-001: One site account, separate permission decisions

Livecho assigns an opaque immutable account identifier when email ownership is first
verified. The contact email is an authentication address, not a platform identity,
device identity or authorization role. Only the backend resolves their associations.
One address cannot concurrently create multiple active accounts. Issue #12 must define
one address-canonicalization contract shared by lookup, proof binding and abuse counters;
provider-specific dot/plus rewriting is excluded from this first phase.

The first phase removes invitation as a prerequisite to verified account creation. It
retains Resend magic links, verifier hashes, single use, a maximum 15-minute link life,
Secure/HttpOnly/SameSite=Lax session cookies, a maximum 30-day revocable session life and
server-side authorization from existing #12. Unverified requests are not active accounts.
Confirmation atomically validates proof purpose, address, expiry, unused state and account
status before creating/looking up the account and issuing its session. A race has one
account and one successful consumption; a reused link cannot issue another session.
Opening a link alone does not consume it or create a session; confirmation requires an
explicit protected action, whose exact web contract is owned by #12.

The service returns the same generic 202 shape for well-formed email requests whether
they can send, are suppressed by address limits, or refer to existing, new or suspended
accounts. An anonymous requester never receives the resolved account or delivery state.
Syntax rejection and request-volume rejection occur without revealing account membership.
No account is created, role granted, history granted or device admitted by requesting mail.

Successful public registration initially grants **no viewer history, operator or admin
authority**. A verified active account has the baseline ability to manage its own account
and the bounded device ownership actions below. A contributor label does not imply a
viewer/history grant; this explicitly changes the old contributor-inherits-viewer model.
No submitted role, owner identifier, capability claim or linked platform identifier can
grant authority. Existing elevated roles must never be recomputed from public signup.

Social login, platform login, account linking, changing the authentication address and
lost-email recovery require separate reviewed contracts before implementation. No platform
OAuth availability, entitlement or permission is assumed. None is necessary to deliver
the first public-email phase.

### AUTH-38-002: History remains independently authorized

The recommended default is a separately recorded viewer/history grant. Registration,
email proof, device ownership and contribution totals do not create this grant. An admin
may issue/revoke it through the existing audited role boundary; the requester cannot
self-select it. #17 must distinguish a signed-in account with no grant from an anonymous
viewer and from a history-authorized viewer without exposing restricted event metadata.

Even a grant permits only the normalized history allowed by current source, purpose,
field, retention and deletion policy. It never authorizes raw archives or erased/hidden
data. Anonymous viewers retain the existing approved normalized public-live subset.
The alternative of granting viewer to every verified account remains an explicit owner
decision in the ADR; it must not arise as an implementation default or UI convenience.

### DEV-38-001: Account-owned enrollment, independent device credentials

A verified, active account may create an enrollment reservation for itself without an
invitation or administrator-issued token. Issuance requires a current session and an
email authentication proof no older than 15 minutes. The reservation binds the immutable
account ID, intended device Ed25519 public key, purpose, expiry and one-time verifier.
The private key is generated/kept on the worker; the backend and browser need only its
public key and enrollment metadata. A browser session bearer is never given to the worker.

An enrollment secret is shown once to the initiating account flow, stored only as a
verifier hash and valid for **10 minutes** (a proposed tighter bound within #13's existing
24-hour maximum). It authorizes only that bound key's ownership registration. The worker
must additionally prove possession through the fresh non-replayable challenge contract
owned by #13. A token alone cannot authenticate another key or become a worker session.
This document does not define a new protocol field, token URL or executable command.

Consume the reservation, establish the owner/key/device association, and convert its
quota reservation to one registered device atomically. A replay or concurrent redemption
cannot consume two slots. A public key already bound to a different active account cannot
be moved, disclosed or rebound by this flow. Device transfer and key replacement are out
of this first phase; they need a separate ownership/recovery contract. The backend assigns
an immutable never-reused device ID. Unknown outcomes are reconciled by the same logical
operation identity, not retried as a second association.

The issuing account may cancel its own pending reservation. A lost once-only secret is
not redisplayed from storage: cancel the old reservation and issue a new bounded operation.
Cancellation/expiry cannot revive a consumed token. Denials disclose no other account's
device, email, enrollment secret or statistics. Admin emergency suspension/revocation
remains available without making admin invitation the normal registration prerequisite.

### DEV-38-002: Ownership is not task or real-audio admission

An account may list and revoke only its own registered devices, cancel its own pending
reservations and see only its own existing aggregate contribution metrics. Those metrics
remain online duration, processed duration, success rate, RTF and recent health; no
rankings, transferable points, payments or proof of trusted output are introduced.

Registration establishes ownership. Fresh challenge authentication establishes only
current possession of the registered key. Separately, an admissible Hello requires the
existing protocol and allowlisted backend/model/revision/SHA. A lease additionally
requires the existing scheduler, room/session, safety, privacy and model/source gates.
Each decision is server-authoritative and defaults to deny on missing evidence.

Self-registration does not enable production real PCM. The existing synthetic-only
default, independent real-audio rights basis, named worker-retention risk decision and
executable ownership/privacy evidence remain prerequisites. Replacing the word invited
must not silently accept the risk for a larger worker population. Platform acquisition
remains limited to the currently approved operator-selected, free, anonymous channel;
an account, device or contribution cannot supply platform acquisition authority.

## Proposed quotas and exact admission semantics

These are **local product choices pending owner approval**, intended to bound initial
email cost and account/device churn without assuming platform limits or measured load.
All rolling windows are trailing intervals `(now - window, now]`, using backend time.
An event exactly one window old no longer counts; equality at the limit denies the next
counted request or issuance. Clock rollback, missing counters or ambiguous reservation results
fail closed for the affected issuance. Limits combine with AND; none is bypassed by a
more permissive limit. No Redis, broker, new service or distributed authority is proposed.

| Operation/dimension | Proposed initial limit | Rationale and outcome |
| --- | --- | --- |
| Proof-request admission per trusted network key | 30 in rolling 60 seconds | Bounds parsing/lookup pressure; excess returns a generic 429 before account lookup. |
| Proof-request admission globally | 300 in rolling 60 seconds | Bounds aggregate admission; same account-independent 429 behavior. |
| Email dispatch per canonical address | 60-second minimum interval, 5 in rolling hour, 10 in rolling 24 hours | Allows retries while bounding repeated mail to one person; suppressed requests retain generic 202. |
| Email dispatch per trusted network key | 20 in rolling hour | Bounds one caller/network; shared networks can experience suppression, which conveys no account existence. |
| Email dispatch globally | 20 in rolling hour and 100 in rolling 24 hours | Explicit initial cost envelope; no claim of production demand/capacity sufficiency. |
| Enrollment issuance per verified account | 5 distinct reservations in rolling 24 hours | Bounds cancel/reissue churn; cancellation, expiry and delivery uncertainty do not refund this count. |
| Pending enrollment reservations per account | At most 2, each expiring after 10 minutes | Bounds abandoned requests. |
| Registered non-revoked devices plus pending reservations per account | At most 3 total | Reserves future capacity; offline/paused devices still count. Redemption moves a slot, not adds one. |

Request-admission counters count every request reaching the proof-request endpoint,
including malformed requests, repeated operation IDs and logged-in reauthentication.
Email/enrollment issuance counters instead count reserved distinct logical operations.
An operation identity cannot be reused with a different bound address, purpose, account
or public key; conflict creates no new dispatch, reservation or authority.

A trusted network key derives from the peer address obtained at the configured trusted
ingress, never an arbitrary client forwarding header. Counters use short-lived keyed,
pseudonymous lookup values, not plain email/IP fields or unkeyed low-entropy hashes.
Their only purpose is issuance admission; they are not account identities or audit keys.
Key rotation must preserve all still-live windows rather than resetting limits.

Reserve all applicable quota dimensions atomically before accepting an issuance or
calling the email provider. A provider failure or unknown delivery still consumes its
reserved dispatch; repeated use of the same operation ID does not create a second mail
or refund capacity. #12 must bind provider idempotency to the same logical dispatch,
without a persistent plaintext-token outbox. It must not promise exactly-once external
delivery. Fresh operation IDs remain subject to every quota. Provider restrictions can
further reduce sending; local settings cannot waive them.

Likewise #13 serializes slot reservation/redemption/revocation so parallel requests do
not exceed three combined slots. Expired reservations release only pending slots, not
their 24-hour issuance count. A revoking device keeps its slot until the required durable
revocation outcome is verified. There is no automatic quota increase from contributions,
account age, capability claims or admin invitation. Quota changes require reviewed local
configuration and audit; the implementation must not silently raise limits to make tests
or registration succeed.

## Interfaces and compatibility

This draft defines capability boundaries and acceptance cases, not endpoint/schema
definitions. #12 owns registration, proof, session, role/history-grant and email/admission
contracts; #13 owns own-device enrollment/ownership/challenge/revocation and contribution
contracts; #17 owns account, no-history-access, own-device and existing privileged screens.
Each needs owner-merged artifacts before its implementation. Anonymous live remains
compatible; no existing public or worker protocol is changed by this proposal.

If #13 requires any change to existing worker protocol compatibility fields or messages,
it must first obtain the owning protocol artifact and golden/backward-compatibility
evidence. This architecture cannot authorize such a change by implication.

## Failure modes and disable path

- Email/provider outage, throttling or uncertain delivery produces no account or session
  without valid proof, no secret log and no automatic alternate delivery provider.
- Missing/invalid/expired/reused proof, suspended account, wrong owner/key, stale challenge
  or malformed capability fails without granting new authority or mutating another target.
- A later revocation/deletion invalidates pending account proofs, enrollment authority,
  sessions and related device authority through the existing scoped control boundary.
  Device-only action affects that device; account action cascades to all its devices.
- Existing pre-armed intake continuity, pending-before-effect, typed checkpoint/durable
  denial, read-back, restore quarantine and pre-restore credential rejection requirements
  apply unchanged. An unavailable recovery/control boundary cannot be bypassed by signup.
- A dedicated signup/enrollment issuance stop can stop new public acquisition while
  preserving authorized existing sessions and revocation paths. It cannot enable ingest,
  relax the global/room safety controls, create recovery authority or block emergency
  revocation. A system-wide safety incident still follows the existing incident runbook.
- Rollback stops new issuance and expires/revokes pending material. It cannot retroactively
  invent invitations, expand history rights or erase existing device/account obligations.

## Security, privacy, and data lifecycle

Existing subject/admin access, minimum account email/role/revocation state, device public
key/status/capabilities and own aggregates remain restricted. Proposed quota counters hold
only the necessary pseudonymous key, purpose, bounded operation identity and timing/count
state; retain no longer than their last live 24-hour window and then purge. Enforce the
existing account/device deletion SLA for any linked active-store record. Email dispatch
metadata/proof retention must follow #12's bounded contract, not become a contact archive.

Audit retains only existing allowed payload-free actor/control/result metadata, never
emails, IPs, public keys, bearer/verifier values, quota lookup keys, content or their
low-entropy hashes. Device private keys stay local; server revocation prevents future
acceptance but does not claim remote deletion of keys or already disclosed PCM.

Deletion never restores an old identity. A later independently permitted signup by the
same email may create a fresh account ID, but inherits no old roles, history grant,
devices or credentials. This is not a promise of identifying or blocking every human
who creates another account. Account suspension and abuse response retain their own
explicit data basis; neither can invent an indefinite undeclared identity denylist.

## Acceptance criteria

- [ ] Draft/approval/adoption/enablement states are explicit and current rules unchanged.
- [ ] Public proof redemption needs no invitation, yet duplicate/replayed/concurrent
  confirmations yield no duplicate account/session or self-granted role.
- [ ] Registered/no-grant, viewer-granted, own contributor, operator and admin cases have
  positive and cross-role/cross-account negative authorization tables in #12/#13/#17.
- [ ] Registration or contribution does not reveal normalized history or raw data; grant
  revocation, source restriction and room/session deletion independently deny access.
- [ ] Every quota tests just below/at/above the limit and exact window expiry, concurrency,
  idempotent retries, provider failure, clock rollback and counter-unavailability cases.
- [ ] Three combined slots cannot become four through concurrent issue/redeem/expire/
  revoke; cancelled requests do not reset daily issuance counts.
- [ ] Wrong-key, wrong-owner, token replay/expiry, public-key conflict and unknown commit
  outcomes grant no duplicate ownership; cancelled or lost secrets cannot be redisplayed.
- [ ] An enrolled device still fails task admission when authentication, manifest, lease,
  rights, privacy or safety evidence is missing; it receives no platform credential.
- [ ] Account/device revocation and deletion test exact cascade, durable-denial failures,
  stopped authority and stale-backup/new-authority resurrection negatives.
- [ ] Signup/enrollment stop does not disable authorized revocation or silently change
  public live, history authorization or platform eligibility.
- [ ] Owner records the ADR decisions and specific residual-risk treatment; later owning
  artifacts and executable evidence precede any capability enablement.
