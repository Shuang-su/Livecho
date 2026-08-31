# Railway rollout, rollback, and removal contract

## Current authority boundary

Issue #4 checks in an offline desired-state skeleton. It does not create, link, inspect,
plan, apply, deploy, migrate, alter, roll back, or delete anything in Railway. No provider
project, environment, service, database, Bucket, domain, token, variable, image, or
deployment is asserted to exist.

Every provider step below is a contract for a later owning Issue. It becomes eligible only
after that Issue has accepted artifacts, exact target approval, independent review, and
the evidence named in the relevant gate. Prose in this file is not execution authority.

The architecture and risk decisions remain blocking: ADR 0001 is still proposed with
repository-owner approval pending, the named platform/safety/persistence/residual-risk
gates are incomplete, and the High residual risks in the Alpha threat model are not
accepted. Production serving, production maintenance, persistence, raw archive, recovery,
email, authentication-dependent ingest, and real worker audio remain disabled. If any
prerequisite or provider result is unreadable or ambiguous, stop and retain the eight
false/fixture safety literals.

## Repository baseline

The program describes one logical `livecho` project per selected environment:

| Resource | Offline desired state |
| --- | --- |
| `web` | one `asia-southeast1-eqsg3a` replica; no variables; guarded start owned by Issue #11; `/healthz`, 30 seconds |
| `backend` | exactly one replica in that compute region; guarded start owned by Issue #9; `/healthz`, 30 seconds |
| `Postgres` | environment-local managed Postgres in `asia-southeast1-eqsg3a` |
| `Archive` | environment-local private Bucket in physical region `sin` |
| `maintenance` | one non-serving Singapore target; `NEVER` restart; 15-second replacement drain; zero baseline credentials |

The three code-service sources are unset. There is no domain, TCP proxy, cron schedule,
automatic deployment, pre-deploy command, provider identifier, or live apply path.
`backend` and `maintenance` receive exactly the eight safety literals from
[the reference/secret inventory](railway-secrets.md); `web` receives none. Production and
staging reserve six backend secret names without values. Preview/unclassified output does
not reserve them.

Permitted Issue #4 work is limited to repository checks: `make bootstrap`,
`make railway-check`, `make verify`, synthetic in-process graph rendering, source-tree
guards, and isolated Make-target tests. `make railway-migrate` returning `NO_MIGRATIONS`
means only that the canonical `db/migrations/` directory entry is absent.

## Separation of duties for later operations

- The repository owner approves the exact commit, environment, redacted plan, production
  gate, and destructive scope. That role implies no database or provider credential.
- The release/security owner approves image digest, signature/provenance, SBOM,
  dependency/license review, and credential-free build evidence.
- A non-destructive controller receives one new environment-scoped Project Token and may
  create, observe, stop, and reconcile exact deployment IDs for one bounded operation. It
  has no account/workspace token, database-owner secret, interactive Owner session, or
  service-instance deletion authority.
- A different, 2FA-authenticated Project Owner may perform one separately approved,
  interactive, dual-bound maintenance-instance deletion. Controller-token environment
  variables are unset; `--yes` is forbidden.
- The database owner creates and revokes one-use database roles and admissions, terminates
  sessions, and reconciles ownership/grants. Its credential never enters a service,
  controller, repository, or CI job.
- An independent reviewer checks immutable repository/provider inputs and redacted
  results, and does not patch the material being reviewed.

The controller token remains usable through required stop/reconciliation and is revoked
only after complete closure or an independently acknowledged terminal handoff.

## External CLI and disposable-copy gate

No Railway CLI is installed by this repository. A later provider session may use only the
external operator tool at exact version `@railway/cli@5.45.10`, after the owning Issue has
approved:

1. official release asset name and URL;
2. exact operating system and architecture;
3. archive SHA-256;
4. deterministic extraction procedure;
5. extracted executable SHA-256; and
6. provenance tying that asset to the approved release.

Obtain the asset in an access-restricted disposable directory. Verify the archive digest
before extraction and the executable digest after extraction. Before every authenticated
invocation, reverify the executable digest and parse an exact `5.45.10` version. `latest`,
`npx`, npm postinstall, a repository-cached binary, a missing digest, or a version parse
failure blocks the session.

`railway link` writes metadata below `.railway`, so link/status/verbose-plan work must
never run in the ordinary checkout. For each future session:

1. create a restricted disposable copy of one reviewed commit;
2. prove it is clean and that `.railway` contains only its four reviewed files, with no
   link state, `.env`, generated file, cache, or alternate IaC language;
3. link and select one exact target only inside that copy;
4. immediately reduce status/plan output to an allowlisted, value-free summary;
5. retain no raw output, URL, variable, identifier, link metadata, or plan file; and
6. destroy the disposable copy after projecting evidence.

Never request values, include variables, enable shell tracing around credentials, or dump
the process environment.

## Environment creation and staging-first provider gate

All actions in this section are future manual actions.

1. Start with an empty staging environment; do not clone production data or values.
2. Through the verified external executable and disposable copy, run
   `railway status --json`, then `railway config plan --verbose`, then status again; prove
   the selected logical target did not change and treat the verbose plan as read-only.
3. Retain only versions, logical resource counts, intended regions, source/domain
   categories, and logical add/change/remove categories.
4. Reject unexpected deletion, source, domain, scale, region, environment, variable,
   reference, or topology changes.
5. Obtain a separate owner approval for one future interactive `railway config apply` of
   the reviewed plan. A plan is never apply approval, and no unattended confirmation is
   permitted.
6. After apply, issue staging-only values and keep every safety literal false/fixture.
7. Run the no-schema guard while serving remains off.
8. Keep automatic PR environments disabled until an Owner selects staging as the sole PR
   base and separate provider metadata proves the selection and sealed-value exclusions.

Synthetic `pr-*` rendering demonstrates repository policy only. Railway's PR feature
copies its configured base and does not automatically run the classifier.

A plan alone cannot prove provider state. Independent metadata must show:

- distinct production/staging service instances, Postgres, Bucket, network scope, and
  values;
- Singapore compute placement for web/backend/maintenance/Postgres and Bucket region
  `sin`;
- intended domain/TCP/cron absence;
- no GitHub source or automatic production deploy;
- staging as the only PR base and every non-copyable value sealed;
- staging literals still false/fixture; and
- no preview source build, copied persistent secret, or cross-environment reference.

Production requires a new plan, current independent owner decision, applicable ADR/risk
approvals, and separately issued values. Staging success does not authorize production.

## Immutable-image requirements

### Backend

Railway variables and managed references are visible during builds. Before any backend
code reaches any persistent or preview target that has such values current or staged, its
owning Issue must create an exact-commit OCI image in a protected build with no provider or
runtime credential. Record and review the content digest, signature/provenance, SBOM,
dependencies, licenses, and verification result.

Configure only that digest. Active and staged provider state must have no GitHub/source
upload, Railway source build, pre-deploy command, package-install step, image auto-update,
or build-time value path. Bind every resulting deployment ID to the exact environment,
service, commit, and digest; reconcile all IDs. One reviewed backend deployment must pass
`/healthz` within the 30-second cutover gate before traffic can be separately approved.

### Maintenance

Before even a sealing canary, a later operation Issue must build a zero-credential
maintenance image with a fixed exec-form `ENTRYPOINT` and empty `CMD`. It records the same
digest/provenance/SBOM/dependency/license evidence. The Issue must remove Issue #4's custom
maintenance build and start commands from IaC, then prove those overrides and any source,
pre-deploy, install, argument override, or auto-update are absent in active and staged
provider state. A custom Railway start command would override the image entrypoint and is
a hard stop.

Configuring the image can itself create deployments. Pre-arm the set-reconciliation gate
before that change. Every new ID is bound to the exact target and digest; each started
instance emits only `maintenance-uri: absent`; at least one completes that probe; and all
new IDs are stopped/cancelled/reconciled before a canary value is eligible.

## Database-operation contract

Issue #4 creates no schema, role, lock, or admission. The first schema Issue must replace
the no-schema Make guard in the same change that creates `db/migrations/`, use that as the
only migration root, and supply an idempotent migration tool. A second root, startup
migration, or provider pre-deploy migration is invalid.

### Mutual exclusion

Every future backend opens a dedicated connection and obtains
`pg_try_advisory_lock_shared(1279874629, 4)` before enabling traffic. It may retry the
non-blocking call with bounded backoff to a monotonic 30-second deadline and holds that
session continuously. False at deadline, SQL/transport error, unknown result, connection
loss, or lock loss closes traffic and the connection.

Migration, deletion, restore, and recovery each use a dedicated connection and obtain
`pg_try_advisory_lock(1279874629, 4)` under the same non-blocking monotonic deadline before
operation-specific database I/O. They hold it through the whole operation and abort on
error or uncertainty. A blocking advisory lock plus external timeout is not a substitute.
All serving instances must also be down, but that observation does not replace the lock.

### Durable one-use admission

The lock prevents concurrency, not later replay. Before a real carrier, the database owner
creates a uniqueness-constrained admission record bound to the globally unique temporary
role, exact environment/database/schema/operation, reviewed image and manifest digests,
and an opaque recovery-protected target reference (or keyed integrity digest of its
canonical control record). An unkeyed digest of a low-entropy room, session, identity, or
deleted content is forbidden.

The normal state begins `PENDING`. After acquiring the exclusive lock and before business
I/O, the role may invoke only a fixed claim primitive that atomically commits
`PENDING -> CLAIMED` for `current_user` and every binding. Exactly one row must return.
Zero or multiple rows, mismatch, non-PENDING state, unreadable state, serialization error,
or commit uncertainty fails closed. `CLAIMED` never becomes `PENDING` again. A crash or
ambiguous result consumes the admission; a new operation needs a new approval, role,
password, and record.

The first schema bootstrap creates the ledger and an already-claimed bootstrap record in
one transaction before any other schema/data effect. Restore/recovery that can rewind the
ledger requires an equivalent one-use authority outside the recovery set under a newly
accepted ADR; absent that proof, recovery is prohibited.

### Temporary role

For each operation, create a never-reused globally unique `NOINHERIT` login, valid no
longer than 60 minutes, with only the exact database/schema/table/function privileges in
the manifest and no superuser, create-role, create-database, replication, or bypass-RLS.
The first schema Issue also establishes one environment-local stable `NOLOGIN` schema
owner that is never a service credential. Persistent objects belong to that stable role.
Only an approved DDL migration may receive non-admin `SET ROLE` membership; deletion,
restore, and recovery receive none unless their own manifest proves the need.

Only this role's URI may be staged as the provider-sealed
`LIVECHO_MAINTENANCE_DATABASE_URL`, and only after that environment's canary lifecycle has
passed. The URI is absent from baseline and may be created/edited/sealed only through the
pre-rehearsed single-variable dashboard flow. No CLI/API/Raw Editor sealed-URI write is
authorized.

## Fixed dispatcher and bounded supervisor

The immutable entrypoint chooses behavior from the literal maintenance flag and membership
(never values) of exactly `LIVECHO_MAINTENANCE_SEAL_CANARY` and
`LIVECHO_MAINTENANCE_DATABASE_URL`. It accepts no argument, selector, mode variable, start
override, or alternate dispatch path.

| Flag / canary / URI | Required result |
| --- | --- |
| false / present / absent | output only `canary: present`, then exit |
| false / absent / absent | output only `maintenance-uri: absent`, then exit |
| true / absent / present | arm the supervisor, then run the single approved operation |
| every other state | payload-free failure before reading either value |

The owning Issue tests the entire flag/membership matrix, traps secret access on probe
paths, and rejects arguments/overrides. Probe output contains no target, environment,
dynamic key, or value.

Before the child can connect, the supervisor arms a monotonic 45-minute deadline, then
emits exactly `maintenance-supervisor: armed`. It owns the child and descendants in one
process group. On deadline, `TERM`, `INT`, or internal exit, it sends `TERM`, waits at most
10 seconds, sends `KILL` to survivors, reaps, and exits nonzero. Descendants may not
daemonize or escape the group. Tests must cover completion, timeout, external TERM,
TERM-ignoring child, grandchild, marker ordering, and absence of survivors.

The provider replacement drain is exactly 15 seconds, exceeding the 10-second reap
window. Restart policy `NEVER`, role expiry, and provider stop are not substitutes for the
internal supervisor or database revocation.

## Deployment-ID set reconciliation

Railway may create multiple deployments for a source/image/service change. Initial image,
canary, real-operation, and zero-credential recreation phases all use this invariant:

1. freeze unrelated IaC, source, image, variable, service, domain, scale, and environment
   changes;
2. record a restricted pre-action inventory and a digest of redacted active/staged state;
3. pre-arm a bounded observation window before the sole trigger;
4. capture a trigger-returned ID, but identify the complete nonempty new-ID set;
5. bind every member to exact environment, service, image digest, and operation/cleanup
   generation;
6. require the phase-specific probe/result for each started ID and an explicit terminal
   state for any ID stopped before start;
7. stop/cancel/reconcile every member by immutable ID, with no second trigger; and
8. continue inventory/read-back until the provider settles and no unrelated revision or
   unowned deployment remains.

An empty, incomplete, mismatched, enlarged, or unsettled set fails the phase. A mutable
latest-deployment command is never used. Exact IDs remain only in provider-native or
restricted retention-bounded operation records; ordinary evidence holds a redacted result
and opaque audit reference.

## Per-environment sealing canary

The following future rehearsal runs independently in staging and production; one result
does not transfer to another environment.

Prerequisites are: exact approved maintenance digest, fixed entrypoint/empty CMD, no
custom/source/build/start/pre-deploy/install override in active or staged state, successful
initial `maintenance-uri: absent` reconciliation, maintenance false, both maintenance-only
keys absent, no maintenance domain/TCP/cron/health credential, and separate controller and
interactive Owner authentication.

### Presence probe

1. In the single-variable dashboard UI, create a one-time non-credential canary under
   `LIVECHO_MAINTENANCE_SEAL_CANARY` and apply `Seal`.
2. Retain only target/key/sealed/staged metadata. Never copy the value to CLI/API, output,
   screenshots, logs, or evidence.
3. Confirm the write did not create an unowned deployment.
4. Let the pre-armed controller make the only deploy request and bind the complete new-ID
   set.
5. Require at least one `canary: present` probe and reconcile every ID.

### Removal, exact instance deletion, and recreation

Deployment removal does not make a historical variable carrier unreachable. After the
probe:

1. remove the canary through the same proven dashboard flow and enumerate all carriers;
2. snapshot sibling maintenance instances, proving maintenance false, both keys absent,
   and no operation/cleanup;
3. have the Project Owner declare a bounded project-wide maintenance freeze, enumerate
   every mutator/automation path, obtain acknowledgements, and retain a redacted logical
   snapshot/revision marker;
4. freshly resolve the exact `(environmentId, serviceId)` for only the target environment's
   maintenance instance;
5. in a separate 2FA Owner session with token variables unset, interactively review and
   perform only `serviceDelete(environmentId, serviceId)`; never use `--yes`, project-level
   deletion, environment deletion, or database/Bucket deletion;
6. prove that exact instance absent and require every prior carrier's restart/redeploy/
   rollback action to return an authenticated typed non-actionable result; network/auth/
   unknown errors are not proof;
7. prove siblings unchanged;
8. approve a redacted plan whose only change recreates that instance from the
   zero-credential image baseline;
9. pre-arm set reconciliation, apply only that recreation under separate approval, bind
   every member of the nonempty new-ID delta, obtain at least one
   `maintenance-uri: absent` probe, and stop/reconcile every ID; and
10. read back active/staged key absence, repeat old-carrier non-actionability checks, prove
    siblings unchanged, then end the freeze.

The freeze is a governance/read-back gate, not a linearizable lease. Missing acknowledgement,
revision drift, broader plan, copied key, cross-environment change, actionable old carrier,
empty deployment delta, or absent probe blocks any real URI.

## One future real operation

No real operation is eligible while the maintenance ADR or applicable High-risk decision
is pending. A later accepted operation follows this order.

### Preflight and target

1. Bind one environment/database/schema/operation, owners, image/manifest, and opaque
   recovery-protected target reference.
2. Deletion accepts only `canonical-room-all-sessions` or `immutable-session-only`. A
   mutable alias, multi-target batch, volatile selector, or audit row is invalid.
3. Destructive purge additionally requires a recovery-protected `hidden` tombstone whose
   commit and read-back are both verified.
4. Stop serving and prove serving, ingest, persistence, raw archive, email, real worker
   audio, and maintenance remain false/fixture.
5. Verify image/entrypoint/empty CMD/15-second drain and all override absences.
6. Create the temporary role and durable admission without recording URI/password.
7. authenticate a fresh environment-scoped controller token and read its scope back;
8. establish the project-wide freeze and sibling quiescence;
9. snapshot redacted active/staged state, provider revision marker, and deployment set; and
10. pre-arm the controller with a two-minute deploy-to-ID/marker deadline, internal
    45-minute duration, and marker-plus-46-minute provider fallback.

No unrelated mutation is allowed until zero-credential recreation settles. Recompute the
logical digest and inventory after every permitted provider action.

### Stage without an unowned deploy

Through the proven dashboard path, create/edit/seal only the temporary URI and retain only
sealed key metadata. Confirm no deployment. Then stage only
`LIVECHO_MAINTENANCE_ENABLED=true` for that target using documented no-deploy semantics
for this non-secret flag. Read back the eight-literal allowlist and sealed-key metadata
without values. An unexpected variable, deployment, or revision fails before admission.

### Sole trigger and watchdogs

The controller performs one deploy request, binds the returned ID and complete new-ID set,
and requires the dispatcher state true/absent/present. The entrypoint arms its 45-minute
timer and emits `maintenance-supervisor: armed`; the controller must observe and bind the
marker within two minutes of the request, then schedules the external fallback for 46
minutes after that marker.

The child obtains the exclusive lock and consumes exactly one matching `PENDING`
admission before business I/O. Later carriers fail admission and are stopped. Commit
uncertainty is never retried. At the fallback deadline, use the Railway Public API to stop
each exact ID; `railway down` is prohibited because it selects mutable latest state.

Missing/mismatched/late ID or marker, provider supervision loss, or unconfirmed stop is an
incident. Independently set the role `NOLOGIN`, terminate its sessions, stop all known
exact IDs, keep traffic off, and do not start another operation. A hard provider stop does
not prove the supervisor's signal handler completed.

### Cleanup on success, failure, timeout, or unknown result

Every outcome uses the same closure sequence:

1. concurrently restore maintenance false with no-deploy semantics and set the role
   `NOLOGIN`;
2. stop/cancel every observed exact carrier and maintain reconciliation through terminal
   status or explicit handoff;
3. terminate every session for the role;
4. record an authoritative terminal admission when possible, but never reopen `CLAIMED` or
   an uncertain record;
5. compare ownership/grants with the manifest, move only expected persistent objects to
   the stable `NOLOGIN` owner, remove residual grants, and drop the role;
6. after database revocation, remove the URI through the proven dashboard path;
7. prove all URI-window deployments stopped and test old-carrier actions for typed
   non-actionability;
8. perform only the exact dual-bound maintenance-instance deletion under the 2FA
   Owner/project-wide-freeze procedure;
9. approve and apply only zero-credential recreation under a new cleanup generation;
10. reconcile the nonempty new-ID set, obtain `maintenance-uri: absent`, prove active and
    staged canary/URI absence, and repeat old-carrier checks;
11. prove siblings unchanged; and
12. revoke the controller token after full reconciliation or acknowledged terminal
    handoff, then end the freeze.

Provider deletion is carrier cleanup, never the revocation authority or emergency stop.
Unknown ownership, grants, sessions, role drop, key removal, carrier status, or sibling
state keeps traffic and further maintenance disabled. No provider-audit or backup-erasure
claim is made.

## Deployment order and health cutover

A future staging rollout, after all applicable approvals, proceeds in this dependency
order: prove environment isolation/placement and safety metadata; establish managed
resources without traffic; complete the maintenance image and canary lifecycle; run an
approved schema migration under the exclusive fence while serving is down; configure the
exact backend image and reconcile IDs; prove one backend `/healthz`; prove the backend
holds the shared advisory lock; deploy web under Issue #11 and prove `/healthz`; then seek
a distinct traffic-cutover approval.

Future web/backend processes listen on Railway's injected `PORT`. `/healthz` contains only
bounded status—not configuration, secret, raw event, identity, transcript, locator, or
audio. Health checks gate cutover, not continuous monitoring; Issue #19 owns external
monitoring. A healthy route cannot override a false safety flag or failed authority gate.

Postgres checks retain no URI. A Bucket write/read/delete probe may use only a separately
approved synthetic non-audio object after the data/security Issue defines deletion
evidence. Raw archive remains off.

## Rollback and disable

If desired state has never been applied, repository rollback is a normal revert. Once a
later apply exists, first generate a redacted plan from the reviewed reverted commit and
reject unintended deletion. Omission from IaC is not safe destruction evidence.

Application rollback first closes safety gates, then binds one retained deployment by
exact environment/service ID and reviewed image digest. Reconcile every provider-created
ID and reread active/staged variables and sources. Railway image/variable rollback does
not reverse an application schema. Never run a destructive down migration. Partial,
incompatible, or unknown schema state stays offline for approved recovery.

Emergency disable is non-destructive: close the relevant feature/global/ingest gates;
stop exact immutable deployment IDs; for maintenance concurrently apply `NOLOGIN`, end
exact-role sessions, and stop every carrier; retain only payload-free outcome evidence;
and keep the environment off until provider/database reconciliation. Do not delete a
service, Postgres, Bucket, environment, or project as an emergency shortcut. Restart
policy, health failure, expiry, deployment `Remove`, and an unconfirmed stop are incomplete
disable mechanisms.

## Restore and permanent destruction

A restore can resurrect temporary roles and admission records. The recovered environment
admits neither traffic nor maintenance until the owner enumerates the role ledger and the
one-use authority outside the recovery set; irreversibly cancels every affected
nonterminal/unknown admission; applies `NOLOGIN`, terminates sessions, reconciles exact
ownership/grants, and drops every present role; proves URI absence; and proves the
admission authority was not rewound. Missing or inconsistent evidence keeps the
environment offline.

Permanent resource destruction is outside Issue #4, CI, rollback, and emergency disable.
A later owner must disable all capabilities, identify one exact scope, satisfy backup,
retention, deletion, audit, and rights obligations, review a redacted destructive plan,
obtain exact owner approval and interactive confirmation, and verify final provider and
deletion evidence. Production project/service/Postgres/Bucket/backup/data destruction
requires then-current Issue #16 and #19 evidence and is never automated.

The only special deletion described here is the stateless maintenance-instance carrier
cleanup after authoritative role revocation. It still requires the per-environment canary,
exact dual IDs, independent Owner/2FA, project-wide freeze, sibling non-interference,
recreation-only plan, nonempty reconciliation set, absence probe, and prior-carrier
non-actionability. It is not project-level service deletion and does not erase audit or
backup history.

## Evidence rules and universal stop conditions

Ordinary evidence may retain repository versions, logical names/counts, redacted
region/source/domain/sealing/status categories, approved image/CLI digest statements,
SBOM/license outcomes, digests of redacted logical snapshots, payload-free dispatcher
markers, timestamps, reviewers, approvals, terminal categories, and opaque references to
restricted audit records.

It must not retain provider IDs, link state, raw status/plan output, URLs, variable values,
resolved references, connection URIs, tokens, passwords, cookies, signing/encryption keys,
signed locators, environment dumps, raw events, identities, transcripts, production data,
deleted target material, PCM, encoded audio, audio base64, stream buffers, audio digests,
or recoverable audio derivatives.

Stop immediately for a missing ADR/risk approval; CLI digest/version mismatch; dirty or
unreadable disposable copy; target drift; unexpected plan removal/source/domain/region/
scale/value change; wrong PR base or unsealed/copied value; image/provenance mismatch;
provider build/install/pre-deploy/autoupdate path; missing or lost lock/admission/role/
dispatcher/supervisor binding; empty or unsettled deployment set; value-bearing probe;
actionable prior carrier; sibling drift; incomplete recreation; uncertain database
ownership/session/role cleanup; or any credential, identifier, payload, locator, or audio
in ordinary output.

The fail-closed terminal state keeps serving and maintenance false, ingest disabled and in
fixture mode, persistence/archive/email/real-worker-audio false, identifiable deployments
stopped, temporary database authority `NOLOGIN` with sessions terminated, no new operation
admitted, and reconciliation assigned to the named owners. Nothing here permits bypassing
login, paywalls, geographic limits, DRM, platform safeguards, or rate limits.
