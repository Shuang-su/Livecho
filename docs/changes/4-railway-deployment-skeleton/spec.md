# Specification: Fail-closed Railway deployment skeleton

Normative terms such as **must**, **must not**, and **may** apply to the Issue #4
implementation. Later Issues may replace guarded service entry points or add a gated
capability, but they must not silently weaken environment isolation or a safety default.

## Behavior

### Source of truth and toolchain

The repository must contain exactly one Railway IaC authoring file at
`.railway/railway.ts`. It must import the generally available TypeScript DSL from
`railway/iac`, export one `defineRailway` program, and return one `project("livecho", ...)
definition. No `railway.json`, `railway.toml`, second authoring language, named partial,
generated provider ID, CLI link file, state file, or decrypted provider export is
permitted. Before any allowlist check, traversal, or import, `lstat` must prove that the
`.railway` root itself is a real directory and not a symlink. Offline tests must then use
two checks: `git ls-files --cached --others
--exclude-standard .railway` must equal the reviewed source/config/test allowlist, and
every allowlisted entry must exist as a regular, non-symlink file. A physical tree walk
must inspect every other entry, including ignored files and symlinks. It may prune
`.railway/node_modules/**` only when `lstat` confirms that the `node_modules` root itself
is a real directory rather than a symlink; any other type at that path fails verification.
Outside that verified dependency subtree, any entry not on the allowlist—including CLI
link metadata, state, generated support, cache, or a second authoring file—fails
verification. The scan must not confuse expected links inside the verified pnpm
`node_modules` directory with provider metadata.

The `.railway` directory must be a pnpm workspace named
`@livecho/railway-config`. It must pin, without ranges:

| Dependency | Required version | Purpose |
| --- | --- | --- |
| `railway` | `3.11.0` | TypeScript IaC DSL and types |
| `typescript` | `7.0.2` | Offline static checking, aligned with the repository |
| `vitest` | `4.1.11` | Offline desired-state contract tests |
| `@types/node` | `26.4.0` | Node APIs used by offline repository-contract tests |

`@railway/cli` must not be a repository dependency or package script. Its npm package's
postinstall downloads a platform binary outside the npm tarball integrity boundary, while
pnpm blocks that build unless explicitly allowlisted. Issue #4 adds neither an install
allowlist nor an unaudited executable download. A later provider operation requires the
exact external operator tool `@railway/cli@5.45.10`, but its owning rollout Issue must
first record the exact official release asset name/URL/platform, archive SHA-256,
deterministic extraction procedure, extracted-executable SHA-256, and provenance approval.
Each operation session must verify the archive digest before extracting into an access-
restricted disposable directory, then verify the executable digest after extraction.
Before every authenticated invocation it must reverify that executable digest and parse
an exact `5.45.10` version. `latest`, `npx`, an unverified postinstall binary, and a
repository-cached binary are prohibited.

The workspace must expose `lint`, `typecheck`, `test`, and `build` scripts so the
existing recursive root commands and `make verify` execute it. `lint`, `typecheck`, and
`build` may all use deterministic TypeScript no-emit checking; none may authenticate,
call Railway, read a local `.env`, or mutate provider state. `test` must evaluate the
exported program entirely in process with synthetic context objects.

The implementation is locked to the exact `railway@3.11.0` declarations and emitted
graph shape. That version exposes database `region`, service `preDeploy`, nested deploy
restart policy and `drainingSeconds`, and generic `ref(resource, output)` APIs even where Railway's prose
reference does not yet commit to every field. Exact structural tests and a later live
plan are therefore compatibility gates; an SDK upgrade must not infer that these
undocumented pinned-package surfaces remain unchanged.

The implementation must add a `make railway-check` convenience target that runs only the
offline `.railway` workspace checks. There must be no `apply`, deploy, environment-create,
or environment-delete target in `Makefile`, CI, package scripts, or GitHub workflows.

### Environment classification and defaults

The program must classify an exact context name of `production` as production, an exact
name of `staging` as staging, and every other value—including `pr-*`, an arbitrary name,
an empty string, or a missing value—as preview/unclassified. Classification must be pure
and deterministic; it must not read process environment variables.

All classes must render these eight literal safety settings on both backend and
maintenance; web receives none of them:

| Variable | Required value | Meaning |
| --- | --- | --- |
| `LIVECHO_GLOBAL_SERVING_ENABLED` | `false` | No serving authority may open traffic |
| `LIVECHO_INGEST_ENABLED` | `false` | Acquisition kill switch is off |
| `LIVECHO_INGEST_MODE` | `fixture` | Only synthetic fixture behavior is eligible |
| `LIVECHO_PERSISTENCE_ENABLED` | `false` | Ordinary database writes are disabled |
| `LIVECHO_RAW_ARCHIVE_ENABLED` | `false` | Raw archive writes are disabled |
| `LIVECHO_EMAIL_ENABLED` | `false` | No Resend/email flow |
| `LIVECHO_REAL_WORKER_AUDIO_ENABLED` | `false` | No real PCM disclosure to a worker |
| `LIVECHO_MAINTENANCE_ENABLED` | `false` | Offline operation cannot start by default |

The selected class and Railway environment name are policy inputs only and must not be
rendered as service variables. An absent name must normalize internally to a stable
`unclassified-preview` class. No class in Issue #4 may render a true safety flag. A future
change that enables any one of these flags requires its owning Issue, accepted artifact,
and independent gate evidence; changing production alone is not a shortcut.

Production and staging must render all and only the six named `preserve()` slots in the
fixed inventory below. Preview/unclassified output must omit all such slots. It must not
use `ctx.shared` for a secret and must not place a literal secret, token, password, key,
cookie, signed URL, or credential-shaped test value in the graph.

Evaluating a synthetic `pr-*` context proves only the repository's render policy when an
operator explicitly runs the IaC program against such a selected environment. Railway's
automatic PR-environment feature instead copies the configured base environment and does
not automatically run this classifier. The live safety gate must therefore prove that
staging is the PR base, staging remains false/fixture, and every value that must not copy
is provider-sealed. No test may present `pr-*` rendering as evidence of those provider
settings.

### Project topology and placement

Each environment graph must contain exactly these five resources and no queue, cache,
worker, second backend, volume, always-on maintenance process, or distributed service:

| Resource | IaC kind | Required placement and authority |
| --- | --- | --- |
| `web` | `service` | One replica in `asia-southeast1-eqsg3a`; no secret or direct database/Bucket access |
| `backend` | `service` | Exactly one replica in `asia-southeast1-eqsg3a`; sole future online application authority |
| `Postgres` | `postgres` | `postgres("Postgres", { region: "asia-southeast1-eqsg3a" })`; environment-local managed database |
| `Archive` | `bucket` | Private Railway Bucket with immutable physical region `sin` |
| `maintenance` | `service` | At most one manually started Singapore job; never a serving authority |

Service placement must use the canonical compute identifier mapping
`{ "asia-southeast1-eqsg3a": 1 }`; a bare replica count does not prove Singapore.
Postgres must pass the same canonical identifier through the pinned helper's `region`
option, and tests must assert its normalized single-replica region structure. Bucket
placement must use `sin`, not the compute identifier and not the S3 API's `REGION=auto`
value. The checked-in desired state still does not prove the provider's actual placement;
a redacted provider plan plus live metadata check remains a mandatory later rollout gate.

Railway environments provide the resource isolation boundary. The file is evaluated
against the selected environment, so identical logical resource names must resolve to
different production, staging, and PR resource instances. Source must not contain a
project ID, environment ID, database ID, Bucket ID, hostname, password, or access key.

The baseline must leave every service source unset. In particular, production must not
have a GitHub source or automatic deployment. Creating the empty deployment targets is a
later explicit `config apply`; supplying a reviewed deployable artifact is a separate later
manual action and must satisfy the credential-bearing image gate below. PR
environment enablement and base selection are also later Railway project settings, not
IaC helpers. Automatic PR creation copies the selected base environment; it is safe only
after staging's provider state and sealed-variable exclusions pass the runbook gate.

### Service command contracts

Issue #4 defines commands but does not implement product runtimes. The exact graph is:

| Target | Build command | Start command | Health contract |
| --- | --- | --- | --- |
| `web` | `make bootstrap && make build` | `make railway-start-web` | `GET /healthz`, HTTP 200 before cutover, 30-second Railway timeout |
| `backend` | `make bootstrap && make build` | `make railway-start-backend` | `GET /healthz`, HTTP 200 before cutover, 30-second Railway timeout |
| `maintenance` | `make bootstrap && make build` | `make railway-run-maintenance` | None; it is a bounded one-shot job, not HTTP-serving |
| `Postgres` | Railway-managed | Railway-managed | Provider state and connection checks, not an application route |
| `Archive` | Railway-managed | Railway-managed | Provider state, private credential resolution, and explicit later write/read/delete probe |

The three start Make targets must exist in Issue #4 and fail non-zero with a short,
secret-free explanation. The web and backend guards identify Issues #11 and #9 as their
respective owners. The maintenance guard says that no approved operation is installed.
They must not open a socket, write data, invoke a platform, acquire a credential, or
silently return success. Their later replacement is implementation work for the owning
Issue and requires its own tests.

The web and backend health paths are forward contracts only. Their guards make an
accidental deployment fail before becoming active. Once implemented, each process must
listen on Railway's injected `PORT`; `/healthz` must return only bounded status metadata
and no secret, configuration dump, raw event, identity, transcript, locator, or audio.
Railway's deploy health check is a cutover gate, not continuous monitoring; Issue #19
owns external runtime monitoring.

`web` must receive no database, Bucket, email, archive, signing, platform, or maintenance
credential. A later server-side web proxy may receive only the backend private hostname
under its own Issue. The browser bundle must never receive a private hostname or secret.

`backend` must receive all and only the selected-environment managed-resource references
for `DATABASE_URL` and the private Bucket outputs `BUCKET`, `ENDPOINT`, `REGION`,
`ACCESS_KEY_ID`, and `SECRET_ACCESS_KEY`. `DATABASE_URL` must use the typed Postgres
reference. Each Bucket output must use the pinned SDK's structured
`ref(Archive, output)` form and logical resource address; no reference may inline a
resolved value. Apart from these six references, the eight literal safety settings and
the six persistent-only preserved slots, no backend variable is permitted. The literal
disable flags remain authoritative, so the presence of an unused resource credential does
not enable a write.

Railway exposes service variables and references to both build and runtime. The listed
backend build command is therefore only a repository build contract while the skeleton has
no source; it is not approved as a Railway build once any database/Bucket reference or
secret slot is current or staged. Before any backend code or source reaches Railway in a
persistent or preview environment, its owning Issue must build and review an immutable OCI
image for the exact accepted commit in a protected, credential-free release job, record its
digest, signature/provenance, SBOM, dependency/license review, and verification result, and
configure Railway to pull that exact digest. The provider state must have no GitHub source,
Railway source build, pre-deploy command, package-install hook, or image auto-update. A
source upload/link or provider build while any managed-resource reference or secret slot is
current or staged is prohibited even when every feature flag is false. This gate applies
equally to production, staging, and every PR-derived environment; a preview may not trade
secret isolation for automatic source builds.
The tabled backend start command and `/healthz`/30-second health check remain Railway
runtime contracts for that reviewed image; only the credential-bearing build moves to the
protected release job.

### Maintenance and migration boundary

The `maintenance` target must have no domain, TCP proxy, cron schedule, health path,
GitHub source, automatic update, or restart loop. Its pinned graph must normalize to
`deploy.restartPolicyType="NEVER"` and `deploy.drainingSeconds=15`. The 15-second provider
replacement grace exceeds the entrypoint's bounded 10-second child reap window. In Issue #4
it receives no `DATABASE_URL`, no
`LIVECHO_MAINTENANCE_DATABASE_URL`, no `preserve()` slot, no resource reference, and no
Archive, Resend, Bilibili/platform, worker, session-signing, or serving credential. The
baseline `LIVECHO_MAINTENANCE_ENABLED=false` guard must remain literal.

The pinned TypeScript SDK does expose a service pre-deploy command, and Railway runs one
in a separate container with the application's environment variables. Issue #4 still
chooses the separate maintenance target because an ordinary backend pre-deploy would
inherit backend credentials and does not itself prove the ADR-required serving/operation
mutual exclusion or credentials narrower along the accepted environment, database,
schema, operation, object-manifest, lifetime, and external-authority dimensions.
Environment creation and PR-base
selection remain separate provider operations; no deprecated `railway.json` or
dashboard-only pre-deploy setting may substitute for the checked-in contract.

`make railway-migrate` must exist as a deterministic no-schema guard. In Issue #4 it must
lexically inspect each repository-relative ancestor of the canonical migration root before
the root itself: if `db` exists, it must be a real non-symlink directory; any other entry
kind fails without traversal. Only then may an `lstat`-equivalent check of
`db/migrations/` return `NO_MIGRATIONS` when that final entry is absent. Every existing
final-entry kind must fail: regular file, empty or non-empty directory, valid symlink,
dangling symlink, socket, FIFO, or device. All future migration material must live under
that single root;
migration files elsewhere are invalid rather than an alternative that bypasses the guard.
The deployment runbook orders this command in a separate maintenance phase before backend
deployment. The first Issue that introduces a schema must replace the guard in the same
change with an idempotent migration tool and the fence below.

Every future backend process must acquire and continuously hold the Postgres session-level
shared advisory lock `pg_try_advisory_lock_shared(1279874629, 4)` on a dedicated
connection before enabling serving. It may retry the non-blocking call with bounded
backoff to a monotonic 30-second deadline; a false result at the deadline, SQL/transport
error, unknown result, connection close, or lock loss must close that dedicated connection,
close traffic, and leave global serving disabled. Every migration, deletion, restore, or
recovery operation must acquire the matching non-blocking exclusive advisory lock
`pg_try_advisory_lock(1279874629, 4)` on its dedicated connection under the same monotonic
deadline before its first operation-specific database read or write, hold that session for
the entire operation, and abort/close it immediately on timeout, error, or uncertainty. A blocking
`pg_advisory_lock` plus timeout is not an allowed substitute. The exclusive lock excludes
both the serving backend and every other maintenance operation; a manual service-down
check is additional evidence, not the authority fence. Mutual exclusion does not provide
replay protection: a replacement can acquire the lock after the first process releases it.

Before any real operation deployment, the database owner must create a durable one-use
admission record bound by a uniqueness constraint to the globally unique temporary role and
the exact environment, database, schema, operation, reviewed image/manifest digest, and
an exact opaque recovery-protected target reference or keyed integrity digest of its
canonical manifest/control record. An unkeyed digest of a room, session, identity, or
deleted content is prohibited. The reviewed image and admission record together determine
the operation and target; no Railway argument, mode, or selector supplies either. The normal
record starts `PENDING` and the operation role may invoke only the fixed claim primitive,
not read or mutate the ledger directly. After acquiring the exclusive advisory lock and
before any business-data read or write, the child must commit one atomic conditional
transition from `PENDING` to `CLAIMED` for `current_user` and every exact binding, requiring
exactly one returned row. Zero or multiple rows, a binding mismatch, an unreadable state,
any state other than `PENDING`, or an uncertain commit fails closed before business I/O.
`CLAIMED` may later gain a terminal outcome for audit, but it can never return to `PENDING`.
A crash or ambiguous result consumes the admission and requires offline reconciliation plus
a newly approved operation, role, password, and admission; it is never automatically
retried. Thus a provider replacement, redeploy, or rollback may later obtain the exclusive
lock but cannot replay the operation.

The first schema Issue must create the protected admission ledger and claim primitive. Its
one allowed bootstrap must create the ledger and an already-`CLAIMED` bootstrap record in
the same transaction before any other schema/data effect; every bootstrap action must be
transaction-safe so rollback exposes no partial business change. If that cannot be proved,
the ledger needs a separately accepted earlier bootstrap and every real URI remains
prohibited. The ledger and claim primitive are outside every ordinary operation manifest.
An operation, such as restore or recovery, that can rewind or replace that ledger must use
an equivalently durable one-use admission authority outside its mutation/recovery set and
prove the same atomic bindings and irreversible consumption. Adding an external authority
requires its own accepted ADR; without that proof the operation remains prohibited.

For each approved future operation, an authorized database owner must create a new
operation-specific Postgres role whose globally unique name is bound to that environment
and operation, is not the backend role, and is never reused after drop. Its password is
also one-use. The role has only the required
database/schema/table/function privileges, has `VALID UNTIL` no later than 60 minutes,
and has no superuser, create-role, create-database, replication, or bypass-RLS capability.
The first schema Issue must also establish one environment-local stable `NOLOGIN` schema
owner that is never a service credential; all persistent migration objects must be
created after changing to that stable owner, never owned by the temporary login role. The
temporary login is `NOINHERIT` and, only for a migration whose reviewed manifest requires
DDL, may receive non-admin `SET ROLE` membership in that schema owner. Deletion, restore,
and recovery roles receive no such membership unless their own accepted operation manifest
proves it necessary. The ADR's required “narrower than backend” property means one exact
environment/database/schema, one allowlisted operation and object manifest, no unrelated
data or external authority, and the bounded lifetime here; it does not falsely claim that
migration DDL is a subset of backend DML.
Only its connection URI may be written as the provider-sealed service variable
`LIVECHO_MAINTENANCE_DATABASE_URL`, after exact environment and operation review. Railway's
published contract establishes single-variable dashboard creation/editing followed by the
three-dot `Seal` action, and says variable changes are staged; it does not establish a
complete CLI/API sealed-variable create/update/delete lifecycle. Issue #4 therefore
authorizes no CLI/API or Raw Editor write for this URI. Separately for each target Railway
environment, before its first real value is ever written, the owning schema/operation Issue
must rehearse the exact single-variable dashboard surface on that environment's maintenance
service. No staging result transfers to production or another environment.

Railway service variables are available to both builds and runtime. Before even the canary
deployment, the owning Issue must produce and review an immutable maintenance OCI image
without either variable, record its exact content digest and provenance, and configure the
target to pull that digest while removing the Issue #4 custom build and start commands from
desired state. Both active and staged provider state must show no custom start-command
override, source build, pre-deploy hook, package installation, or other user code before the
reviewed image entrypoint. Provider metadata must match the approved digest. The Issue #4
source-build/start guards are not operation-image commands; removing them is an explicit
infrastructure compatibility change in that accepted Issue before a canary or real URI.
A digest mismatch, retained override, or any build-time credential exposure blocks the
operation. Because first configuring that image source also
starts a deployment, the controller must pre-arm a bounded inventory window and apply the
same set-bound reconciliation rules defined below: every new ID is bound to the exact
environment/service/digest, every started ID reports `maintenance-uri: absent` while both
keys are absent and the flag is false, at least one ID completes that probe, and every ID is
stop/cancel/reconciled. The canary write is prohibited until that initial delta is settled.

That image must expose one reviewed fixed dispatcher as its exec-form immutable `ENTRYPOINT`
with an empty `CMD`; no deploy
call, CLI argument, dedicated mode/selector variable, start-command mutation, or other
caller-supplied override may choose its mode. Before any secret-value read or application-
external I/O, the dispatcher uses only the literal non-secret maintenance flag and
membership—not values—of exactly
`LIVECHO_MAINTENANCE_SEAL_CANARY` and `LIVECHO_MAINTENANCE_DATABASE_URL`. Its closed state
machine is:

| Exact state | Only permitted behavior |
| --- | --- |
| flag false; canary present; URI absent | emit only `canary: present` and exit |
| flag false; canary absent; URI absent | emit only `maintenance-uri: absent` and exit |
| flag true; canary absent; URI present | arm the supervisor, then enter the accepted operation path that may read the URI, acquire the exclusive lock, and consume its one-use admission before business I/O |
| every other state, missing/invalid flag, argument, or override | emit a stable payload-free error and fail closed before reading either value |

The owning Issue must unit-test the complete flag/key-membership matrix, reject every
argument/override, and use value-access traps proving that both probe branches never read or
render either value. Tests must also prove output contains no dynamic key or environment
name and that only the accepted operation branch can reach a URI value access.

With the maintenance flag false and the real URI absent, the rehearsal creates the canary
key through the single-variable dashboard with a one-time random non-credential value,
applies `Seal`, and verifies the sealed badge plus staged-without-deploy state. A
short-deadline instance of the exact-ID controller must be the sole deploy caller, bind and
verify the canary carrier deployment's immutable ID, let the fixed dispatcher obtain a
`canary: present` result, then stop and reconcile that exact deployment. The fixed key name
may remain in the restricted
provider audit trail; its value must never enter source, CLI/API input, process output, CI,
logs, or evidence. Ordinary evidence retains only fixed logical labels, redacted boolean
outcomes, and opaque provider-audit references.

The rehearsal must then remove the canary through the exact dashboard flow and exercise the
proposed carrier cleanup. Railway's deployment `Remove`, a `REMOVED` status, or expiry of
image retention is insufficient because documented rollback and redeploy actions can restore
historical custom variables. The only cleanup surface accepted by this artifact is the
pinned CLI/API `serviceDelete(environmentId, serviceId)` mutation, with both opaque IDs
resolved from and checked against the exact logical target immediately before a separately
approved destructive call. The cleanup operator must record every canary-carrier deployment
ID, the pre-delete `(environmentId, serviceId)` binding, and any provider instance/
incarnation marker in restricted state. It must delete only that environment's maintenance
instance, prove that exact tuple has no instance before recreation, and verify every carrier
deployment is not found or rejects restart, redeploy, and rollback. The project-level
service ID may remain stable and is not itself claimed erased.
Provider-native audit entries may remain queryable; this does not claim physical erasure
from provider backups.

Carrier action rejection must be tested from the authenticated cleanup-Owner session that
is authorized to perform those actions; a `401`/`403`, network error, timeout, or unknown
failure is not deletion evidence. Only an explicit provider not-found/deleted/non-actionable
result for the exact carrier ID qualifies. The canary makes this safe to rehearse. For a
real URI, no action probe may run until the one-use database role has been dropped. If an
action is unexpectedly accepted, the controller must bind and stop the resulting deployment,
leave serving disabled, and treat cleanup as failed.

The controller must receive a fresh Project Token bound to that exact Railway environment,
read back only its project/environment claims, and hold no account/workspace API token or
interactive owner session. Railway documents Project Tokens as environment-scoped and
deployment-only; the token must not have service-instance deletion authority. It remains
usable only through the bounded operation and its required stop, carrier cleanup, and
absence reconciliation. A child result, watchdog firing, or operation deadline triggers
stop/`NOLOGIN` but is not itself a token-lifecycle endpoint while cleanup is active. The
token is revoked immediately after reconciliation completes or after the independent
operator/database-owner channel acknowledges an explicit terminal cleanup handoff; every
overall success, failure, or incident record must include that revocation outcome. Any
broader or unreadable token class prohibits the first URI write.
The destructive call belongs to a separately authenticated Project Owner in an interactive
session with token environment variables unset, enforced two-factor authentication, and no
credential handoff to the controller. Railway Editors are insufficient because they cannot
delete services. The Owner uses the verified pinned CLI with its target confirmation and is
never automated or passed `--yes`. The cleanup credential and opaque IDs remain outside
source, CI, and ordinary evidence.

Before any such call, the Project Owner must declare a bounded project-wide maintenance
change freeze, enumerate every environment and authorized mutator/automation path, record
their acknowledgements, and keep maintenance globally disabled. Every sibling maintenance
instance must have no current or staged canary/URI, a false maintenance flag, and no active
operation or cleanup. The Owner captures a redacted logical configuration/activity snapshot
and any provider revision marker, then rereads them immediately before confirmation and
after deletion/recreation. Missing metadata, an unacknowledged mutator, or any unexpected
revision/snapshot change blocks or fails cleanup and leaves maintenance globally disabled.
This is an explicit governance/readback gate, not a linearizable distributed lease; Issue #4
adds no coordination service. The freeze ends only after exact-target recreation and the
absence probe plus post-recreation carrier-action checks finish, otherwise reconciliation
remains open.

The canary rehearsal must snapshot every other environment's maintenance instance before
the call and prove each is unchanged afterward. It must then review a redacted IaC plan
whose only change is recreation of the deleted target environment's maintenance instance.
Before apply, the controller records the restricted deployment inventory and pre-arms a
bounded reconciliation window for the nonempty delta of provider-triggered recreation
deployments. Under separate owner
approval, the Owner applies only that plan and distinguishes the recreated instance from the
deleted incarnation by recording a new cleanup generation and any new provider instance
marker. The recreated target must have the maintenance flag false, no canary or real URI,
no GitHub source/build or autodeploy, and the approved image digest. Because creating an
image-backed service starts a Railway deployment even though the image skips a provider
build, the controller repeatedly diffs the inventory through the provider-settled final
readback. It binds every new immutable deployment ID to that environment/service, cleanup
generation, and image digest, proves active/staged state has no canary/URI or database role,
and stop/cancel/reconciles every ID. Each ID that starts must let the fixed dispatcher report
`maintenance-uri: absent`; an ID stopped before start must have an explicit terminal state,
and at least one bound ID must complete the absence probe. That nonempty bound delta is the
post-removal absence proof; no second trigger or selector channel is allowed. An empty delta,
unbound/mismatched/unreadable ID, unsettled queue at the bounded deadline, or started ID
without the exact probe result fails cleanup and sends every observed exact ID through the
incident stop path. Before ending the change
freeze, the authenticated cleanup-Owner session must repeat the typed
restart, redeploy, and rollback checks for every pre-delete carrier ID and prove each remains
explicitly not-found/deleted/non-actionable after recreation.

Any unexplained or extra deployment, dual-ID target mismatch, cross-environment change, actionable
carrier, unexpected probe result, retained current key, broader recreation plan, or
unconfirmed cleanup prohibits the first real URI write. Only after the complete per-
environment proof may that environment receive its first real URI; without it every real
maintenance operation there is prohibited. Project/environment deletion and a service
delete without both environment and service bindings are prohibited.

Creates, true/false updates, and resets of the non-secret
`LIVECHO_MAINTENANCE_ENABLED` flag must target the exact environment/service and use
documented no-deploy semantics (`--skip-deploys` for CLI writes or API
`skipDeploys: true`). After any canary, URI, or flag staging action the operator may read
back only staged key names, target metadata, sealed state, and a dedicated projection of the
eight allowlisted non-secret safety literals. That projection accepts only their specified
`fixture`/`true`/`false` values and may be retained to prove the maintenance flag and sibling
baselines. Every sealed value, managed-resource reference, resolved credential, and other
variable value remains unreadable and unretained. Any unexpected safety key/literal fails
closed, and the operator must confirm that no unowned deployment was triggered. The
external controller below remains the sole operation deploy caller. The future maintenance entrypoint must
itself be the wall-clock supervisor. It
must arm a monotonic 45-minute deadline, emit the exact payload-free
`maintenance-supervisor: armed` marker, and only then allow an operation child in its own
process group to open the database. At the deadline the supervisor sends that process group `TERM`,
waits at most 10 seconds, sends `KILL` if any child remains, reaps the child, and exits
non-zero; process termination closes the child's dedicated lock/database connection. The
supervisor must also catch `TERM`, `INT`, and every internal exit request and run that same
idempotent bounded process-group `TERM`/`KILL`/reap sequence before it exits; it must never
drop a signal by exiting first. The reviewed operation child and descendants must not
daemonize, call `setsid`, change process group, or otherwise escape supervision. The owning
Issue must test a normal child, deadline expiry, supervisor `TERM`, a child that ignores
`TERM`, and a same-group grandchild, proving marker-after-arm/before-child ordering, bounded
reap, and no surviving descendant.
Immediately before the real URI is written, the operator must freeze that exact maintenance
instance: it retains only the approved immutable image with no GitHub source/build or
autodeploy. From that freeze until the replacement baseline is reconciled, every IaC plan/
apply, source/image/autoupdate, service-setting, domain/TCP/cron/scale, environment sync/
copy, restart/redeploy/rollback, and variable mutation is prohibited. Before database
revocation, the only exceptions are the one exact reviewed, target-bound dashboard URI
create/edit, `Seal`, and staged write; the exact reviewed maintenance flag true/false writes;
and the controller's one operation deployment plus stop/cancel/remove of its exact IDs.
After revocation, final URI removal, the specified dual-bound instance deletion, the
recreation-only apply, and the absence probe are additionally allowed.
The controller records a deterministic digest of the redacted active and staged logical
configuration, any provider-exposed revision marker, and a restricted deployment inventory
before the URI write and after every allowed provider action. Every
deployment created while the URI is staged or current is a carrier, including any
unexpected provider-initiated replacement; each carrier ID must be bound, stopped, and
reconciled. Only the first child whose exact database admission transition succeeds may
perform the operation. Every later carrier must receive an admission denial even if it
eventually acquires the exclusive lock; discovery of such a carrier also triggers exact-ID
stop and `NOLOGIN`, never a retry. Missing or unreadable critical active/staged state, any unexplained ID,
unexpected snapshot-digest/revision change, drift, or unowned commit triggers the fail-
closed stop/`NOLOGIN` response.
Before triggering the deployment, the operator must also pre-arm an independent kill-after
controller as a second-layer fallback with the exact environment, maintenance service,
two-minute startup/binding deadline from the deploy request, 45-minute internal duration,
and 46-minute post-observed-start provider delay, then read those values back. That
controller must be the sole provider
deploy caller for the operation. It captures the new immutable deployment ID returned by
that call, immediately verifies the ID belongs to the pre-armed environment/service, and
retains the binding only in access-restricted volatile state. It must observe the exact
armed marker within the two-minute startup deadline, then arm the provider timestamp at 46
minutes after that observation. The marker is emitted only after the internal timer is
armed, so this second deadline is later than the 45-minute timer plus its 10-second reap
window even when image pull or queue time is nonzero. This external layer still does not
claim that ID binding finishes before the child starts; the entrypoint supervisor remains
the only wall-clock authority inside the deployment. A missing, late, mismatched, or
unreadable binding/marker triggers the same fail-closed exact-ID cancel/stop, `NOLOGIN`, and
session-termination response below.
At the observed-marker-plus-46-minute provider deadline the controller must use Railway's
Public API stop operation for that exact deployment ID; `railway down` is prohibited because it targets the mutable latest
successful deployment. The exact ID may exist only in Railway's provider-native audit
trail or an access-restricted, retention-bounded admin operation record used for stop and
cleanup verification; ordinary/repository evidence retains only a redacted outcome and an
opaque audit reference. It must not enter source, CI artifacts, public/application logs,
or ordinary evidence. The controller's scoped operator credential is never recorded.
Railway documents `drainingSeconds` for replacement teardown but does not promise that an
exact-ID Public API stop honors that grace. The 46-minute fallback therefore runs only after
the observed supervisor arm plus its 45-minute deadline and 10-second reap window, and a hard provider kill
remains acceptable only alongside independent database `NOLOGIN` and exact-role session
termination; evidence must not claim that the supervisor handler completed after a provider
stop unless its own bounded-reap result was observed.
Controller supervision loss or an unconfirmed provider stop is an abnormal, not a
successful immediate stop: through an independent operator/database-owner channel,
attempt the same exact-ID provider stop, set the role `NOLOGIN`, and terminate its exact-
role sessions. Any unreachable or unconfirmed step leaves traffic disabled, prohibits any
new maintenance deployment, and leaves cleanup/reconciliation pending. `NEVER` restart
policy and `VALID UNTIL` are not execution timeouts. After success, failure, either watchdog
firing, or ambiguous completion, the owner must immediately restore
`LIVECHO_MAINTENANCE_ENABLED=false` and set the role `NOLOGIN`; neither action waits for
the other. The owner must then stop/confirm stopped the maintenance deployment, terminate
every remaining session for that exact role, and verify in the exact database that it owns
no persistent object. Any unexpected ownership blocks serving and must first be reconciled
against the approved migration/object manifest. Only an exact expected object with the
approved stable destination may be reassigned; unknown or extra ownership remains offline
for a separately approved recovery and must never be blindly reassigned. After ownership
is clear, `DROP OWNED` revokes residual grants, then the temporary role is dropped. That
confirmed `NOLOGIN`, session termination, ownership cleanup, and drop of a never-reused role
is the credential-revocation authority; provider deletion is carrier cleanup and must not
be used as the emergency stop. Only after revocation may the sealed variable be removed
through the pre-proved dashboard flow and the frozen instance be deleted through the exact
dual-bound `serviceDelete` sequence. The cleanup operator must enumerate every deployment
created during the URI window, prove each stopped, and verify after deletion that every
carrier rejects restart, redeploy, and rollback. It must also prove every other environment
instance unchanged.

A separately approved redacted IaC plan may then recreate only the deleted maintenance
instance from the zero-credential immutable-image baseline. Before apply, the controller
records the restricted deployment inventory and pre-arms a bounded reconciliation window
for the nonempty delta of provider-triggered recreation deployments. The Owner applies only
that plan, binds the recreation to a new cleanup generation and any available provider
instance marker, and does not require the project-level service ID to change. The controller
repeatedly diffs the inventory through the provider-settled final readback, binds every new
immutable deployment ID to that environment/service, cleanup generation, and image digest,
proves active/staged state has no URI/canary and no usable database role, and stop/cancel/
reconciles every ID. Each ID that starts must let the fixed dispatcher report
`maintenance-uri: absent`; an ID stopped before start must have an explicit terminal state,
and at least one bound ID must complete the absence probe. That nonempty bound delta is the
post-removal absence proof; no second trigger or selector channel is allowed. An empty delta,
unbound/mismatched/unreadable ID, unsettled queue at the bounded deadline, or started ID
without the exact probe result fails cleanup and sends every observed exact ID through the
incident stop path. After current active/staged state is also proved to lack the URI, the
authenticated cleanup-Owner session must repeat the typed restart, redeploy, and rollback
checks for every pre-delete carrier ID and prove each remains explicitly not-found/deleted/
non-actionable after recreation. Cleanup is complete only after those checks and the cross-environment/
recreation evidence pass. No
step claims provider-audit or backup erasure. The dropped role names and passwords are never
reissued, so retained provider copies alone have no authority against the current database
where the drops were verified. A database restore may resurrect one-use roles and admission
rows captured in its recovery window; every restore therefore remains globally off and
prohibits traffic or maintenance until an owner enumerates both the environment's
maintenance-role ledger and the recovery-safe admission authority. The owner must prove
every admission that may fall in that window terminal and irreversibly cancel every
restored `PENDING`, `CLAIMED`, unknown, or inconsistent entry; none may be reused. The owner
must then prove every recorded role absent or complete the full database-side cleanup for
each present role. That cleanup immediately sets the role
`NOLOGIN`, terminates every exact-role session, inventories its ownership and grants against
the approved operation manifest, reassigns only exact expected objects to the stable
`NOLOGIN` schema owner, and leaves unknown/extra ownership offline for separate recovery.
Only after ownership is clear may it run `DROP OWNED`/residual-grant revocation and drop the
role. Expiry alone is not sufficient. A missing role/admission ledger, admission authority
inside the rewound recovery set, or unbounded/uncertain recovery window also remains off. A
retained URI plus any restored or uncertain role/admission is an
incident. Any later successful carrier restart/redeploy/rollback is also an incident. A
failed provider cleanup leaves the already
dropped database role unusable but keeps serving disabled and the incident open.
`VALID UNTIL` alone is not session revocation. The credential
used by the database owner to issue or
revoke that role is never a service, repository, or CI variable.

For an approved future offline operation, the runbook must require all serving targets
down; every serving, ingest, persistence, raw-archive, email, and real-worker-audio flag
still false/fixture; an exact environment selection; a recorded operation and owner; the
operation-specific sealed role; the reviewed image's entrypoint-supervisor contract; and
the external controller pre-armed as above. Only an accepted owning Issue and that exact
runbook may then stage `LIVECHO_MAINTENANCE_ENABLED=true` temporarily, using a provider
variable write with `--skip-deploys` semantics so that the controller remains the sole
deploy caller. It then triggers the one-shot deployment; the entrypoint arms its monotonic
deadline before the child can open the database, and the child must acquire the exclusive
lock before its first database read or write. Every completion, failure, watchdog action,
or unknown result starts the false/`NOLOGIN` cleanup above before any serving restart. A
failure or unknown result leaves traffic disabled, prohibits any new maintenance
deployment, and requires offline reconciliation. Maintenance never becomes a second
authority and never talks to Bilibili, a worker, Resend, or a browser.

A deletion operation must name and verify exactly one target form:
`canonical-room-all-sessions` for one canonical room or `immutable-session-only` for one
immutable session. An alias, mutable/volatile selection, multi-target batch, empty store,
audit row, or unacknowledged request is not admission evidence. Destructive purge may
start only from a recovery-protected `hidden` tombstone whose commit and read-back have
both been verified; every other state fails closed under the same operation fence.

### Secret inventory and local substitutes

The implementation must include `docs/operations/railway-secrets.md`. It records names
and metadata only—never values—and distinguishes provider-generated references from
future application secrets and CI/operator credentials.

The future application secret inventory is fixed for this skeleton:

| Variable | Scope/consumer | State in Issue #4 | Rotation owner |
| --- | --- | --- | --- |
| `LIVECHO_SESSION_SIGNING_KEY` | production or staging backend only | Reserved sealed slot; no value | Auth/security owner |
| `LIVECHO_WORKER_TOKEN_SIGNING_KEY` | production or staging backend only | Reserved sealed slot; no value | Worker/security owner |
| `LIVECHO_ARCHIVE_ENCRYPTION_KEY` | production or staging backend only | Reserved sealed slot; no value; archive off | Data/security owner |
| `LIVECHO_RECOVERY_INTEGRITY_KEY` | production or staging backend only | Reserved sealed slot; no value; recovery off | Operations/security owner |
| `LIVECHO_AUDIT_INTEGRITY_KEY` | production or staging backend only | Reserved sealed slot; no value; audit persistence off | Data/security owner |
| `RESEND_API_KEY` | production or staging backend only | Reserved sealed slot; no value; email off | Auth/operations owner |

These slots use `preserve()` only in persistent-environment graph output. `preserve()`
means keep an already provider-managed value; it is not evidence of sealing. Before a
later owning Issue sets a value, Railway must mark it sealed and environment-local, its
consumer must reject absence without logging, and live evidence must record only the
variable name, sealed state, scope, creation/rotation time, and reviewer.

`LIVECHO_MAINTENANCE_DATABASE_URL` is not a reserved or preserved application-secret
slot. It must be absent from every baseline graph and is permitted only as the temporary,
provider-sealed operation credential defined above. Its inventory record is created for
that operation, names the one-use database role and expiry without recording the URI, and
closes only after role revocation/drop, exact-environment carrier deletion, zero-credential
instance recreation, current active/staged absence, and the absence probe are verified.
Closure does not claim provider-audit or backup erasure.

The inventory must also cover Railway project/deploy tokens, backend Postgres credentials,
temporary maintenance roles, and the five private Bucket credential outputs. For every
entry it records least-privilege consumer, environment scope, provisioning owner,
rotation/revocation trigger, emergency owner, and the fact that a suspected disclosure
causes immediate revoke/replace plus affected deployment review. Production and staging
values are issued independently. Provider/database-owner credentials used to create the
temporary role and CI/deploy tokens are never service variables. Bilibili account
credentials, cookies, signed playback URLs, worker download credentials, and archive
keys sent to workers are explicitly nonexistent rather than reserved.

The root `.env.example` must contain all and only the eight safety settings in the table
above: `LIVECHO_INGEST_MODE=fixture` and the other seven values exactly `false`. It must
contain no class variable, comment assignment, placeholder password, key, token, URL with
embedded credentials, database credential, Bucket credential, or production-shaped value.
The operations document defines these safe local substitutes:

- database and archive adapters disabled by default; a later owning Issue may use an
  isolated loopback fixture service or bounded in-memory fake, never production data;
- mail as an in-memory/no-send sink;
- signing/integrity material generated ephemerally per local process when a later test
  requires it, never committed, logged, snapshotted, or written to disk; and
- ingest as synthetic fixture input only, with no account credential or playback URL.

No local substitute may persist audio or raw unencrypted data.

## Interfaces and compatibility

The implementation adds the following repository interfaces:

- `.railway/railway.ts`: sole desired-state program plus exported non-secret policy
  constants used by tests;
- `.railway/package.json`, `.railway/tsconfig.json`, and `.railway/railway.test.ts`:
  pinned offline validation workspace;
- `make railway-check`, `make railway-start-web`, `make railway-start-backend`,
  `make railway-run-maintenance`, and `make railway-migrate`;
- `.env.example`: safe local disable values only;
- `docs/operations/railway-deployment.md`: environment setup, plan/apply gate, separate
  migration phase, deploy, rollback, and destruction runbook; and
- `docs/operations/railway-secrets.md`: secret/reference ownership and rotation inventory.

There is no public API, wire protocol, schema, database, UI, or persisted-data change.
The existing protocol `epoch`, `seq`, and `revision` meanings are untouched. Removing or
renaming a service, resource, variable, environment class, command, or safety switch is
a reviewed infrastructure compatibility change because Railway IaC omission can be
destructive.

### Offline and live verification boundary

Offline CI must prove source-level desired state but must not claim provider state. Tests
must evaluate at least `production`, `staging`, `pr-123`, an arbitrary name, an empty
name, and a missing name. They must assert:

- one project and exactly the five named resources;
- no duplicate backend, one canonical Singapore replica for each code service, and the
  exact normalized Singapore region structure from
  `postgres("Postgres", { region: "asia-southeast1-eqsg3a" })`;
- Bucket region `sin`, the exact typed Postgres reference, all and only the five structured
  `ref(Archive, output)` Bucket references, and no hard-coded provider identifier or
  resolved credential;
- exact build/start/health contracts and fail-closed Make targets;
- production has no source or auto-deploy path;
- preview/unclassified has no `preserve()` secret slot and every safety value is
  false/fixture;
- backend and maintenance each have all and only the exact eight safety assignments, web
  has none, and no service renders class/environment metadata;
- persistent backend output has all and only the six named preserved slots and no literal
  secret, while maintenance has none;
- web has no managed-resource or secret reference;
- maintenance has exact `NEVER` restart policy and 15-second drain plus no domain, TCP,
  cron, health, source, resource reference, preserved slot, or credential path;
- repeated evaluation of the same context is deeply equal; and
- the two-layer source/tree guard rejects the `.railway` root replaced by a symlink,
  rejects an allowlisted path replaced by either a valid or dangling symlink, and rejects
  a symlinked `.railway/node_modules` root, while allowing expected package-manager
  symlinks only inside a verified real `node_modules` directory.

The tests must also reject the appearance of `railway.json`, `railway.toml`, a second IaC
language file, or the canonical `db/migrations/` root while the no-schema guard remains.
They must reject a symlinked `db` parent whose target either has or lacks a `migrations`
entry, rather than following it outside the checkout.
The first schema/operation Issue must test the admission protocol with concurrent and
sequential contenders: exactly one exact binding may commit `PENDING` to `CLAIMED`, while
missing, duplicate, mismatched, already-claimed, terminal, serialization-error, and
commit-unknown cases all stop before business I/O. Crash-after-claim, provider replacement,
redeploy, and rollback tests must prove the admission is never reopened or automatically
retried. Bootstrap tests must prove ledger creation and the claimed bootstrap record are one
transaction with no visible partial effect. Restore/recovery tests must prove the admission
authority lies outside the rewound set, recovered nonterminal entries are irreversibly
cancelled, and a missing or inconsistent role/admission ledger leaves the environment off.
They must assert that `.env.example` contains the exact eight-key/value allowlist above;
an absent/extra key, wrong value, comment assignment, or credential-like value fails. A
future schema Issue must make the canonical root the only migration input accepted by its
tool; it cannot register an alternate root.
Synthetic `pr-*` assertions must be labelled render-policy checks and must not stand in
for the provider evidence below.

For each later authenticated operation session, the operator must first verify the owner-
approved platform release archive's SHA-256, extract it only into the access-restricted
disposable directory, and verify the extracted CLI executable's separately approved
SHA-256. Before every authenticated Railway invocation, the operator must reverify the
executable digest and assert that parsed `railway --version` is exactly `5.45.10`; any
mismatch blocks the command.
The operator must link/select the exact target and run `railway status --json` before and
after `railway config plan --verbose`. Raw status output must be projected immediately to
an allowlist of logical names, counts, regions, and status categories; provider IDs, URLs,
variable material, and every other field are removed before retention. The verbose plan
evidence records CLI/SDK versions, logical resource counts, proposed placement,
source/domain changes, and a redacted diff summary. A separate read-only provider metadata
or control-panel record must prove the actual project/environment identity,
production/staging resource separation, realized regions, generated/public domains,
source/autodeploy state, PR base selection, and sealed variable metadata. Before any
credential-bearing backend deployment, that record must additionally prove the approved
exact-commit image digest, automatic image updates off, and no Railway build/pre-deploy/
install phase in production, staging, or the target preview. Before any maintenance canary,
the record must prove the approved image digest and custom build/start/pre-deploy overrides
absent from both active and staged state. `config plan`
alone does not prove those settings. Neither record may use `--show-values`, decrypted
variables, plan-file contents, secret output, or provider IDs committed to the repository.
`config apply` is not validation and is forbidden in Issue #4.

Because `railway link` stores project/environment identifiers under `.railway`, every
later live link/status/plan operation must run from an access-restricted disposable copy
of the reviewed repository revision, never this Git worktree. The operator must verify
the copied commit before linking, retain only the redacted evidence named above, and
destroy the disposable directory and its link metadata after the operation. A provider
ID appearing in the repository is a release-blocking leak even if ignored by Git.

## Failure modes and disable path

- Missing/unknown environment context renders preview restrictions; it never inherits a
  production enablement or application secret.
- Missing sealed variables make their future owning feature unavailable. Code must not
  replace them with a default, log them, or enable an adjacent path.
- An accidental service deployment reaches a non-zero start guard and fails before a
  health check can cut over.
- A config type/test failure, SDK/CLI incompatibility, unexpected live-plan deletion,
  linked-target mismatch, provider drift, unknown resource region, shared identifier,
  unsealed secret, or PR base other than staging blocks apply.
- A migration guard failure, lock timeout/loss, missing or over-privileged temporary role,
  missing/mismatched/already-consumed admission, failed one-shot job, incomplete credential
  revocation, or ambiguous result keeps
  backend/web down and every enable switch false until offline reconciliation.
- Railway rollback restores an earlier image and custom variables, not a database schema.
  Database changes must be expand/contract compatible; automatic destructive down
  migrations are prohibited. Roll back application code first and leave an incompatible
  or ambiguous schema offline for an approved maintenance decision.
- To disable an eventually deployed service, first close the application safety gates,
  then use the exact environment/service target to stop its deployment. Do not delete a
  service, database, Bucket, environment, or project as an emergency-stop shortcut.
- Permanent project, environment, project-level service, Postgres, Bucket, or data-bearing
  resource deletion requires a reviewed redacted destructive plan, verified backup and
  retention/deletion obligations, exact environment identity, repository-owner approval,
  and Railway's explicit destructive confirmation. It is never automated. The sole
  exception is the stateless maintenance-instance carrier cleanup above: only after the
  role is revoked, its dual-bound canary/Owner/non-data/cross-environment/recreation gates
  apply, and it is never an emergency stop. Production project deletion is outside Issue #4.

## Security, privacy, and data lifecycle

- Railway variables and resource references are trusted infrastructure inputs, but the
  web and community worker remain untrusted. Neither may receive database, Bucket,
  archive, email, signing, deployment, platform, or maintenance credentials.
- The desired state and later rollout contract require production and staging to use
  distinct environment-scoped network, variables, Postgres, and Bucket instances; Issue
  #4 creates none of them. Railway automatic PR environments copy the provider-configured
  base, so the runbook keeps PR environments disabled until a later provider gate proves
  that the base is staging and sealed variables are omitted. The synthetic environment
  classifier is defense in depth only when IaC is explicitly evaluated for that
  environment. Project membership and public endpoint settings are reviewed separately
  because they are not isolated by an IaC resource name.
- The Bucket desired state is private and raw archive stays disabled. Railway Bucket
  privacy is not client-side encryption, versioning, deletion, or recovery evidence;
  Issue #16 owns authenticated encryption and lifecycle controls before any raw object
  exists.
- No plan/evidence command uses `--show-values`, `config pull --include-variables`, a
  decrypted variable option, shell tracing around credentials, or captured environment
  dumps. Temporary plan files are access-restricted, never committed, and removed after
  the approved operation.
- Logs contain only command outcome, environment class, resource/service logical name,
  health status, and stable error code. The controlled presence-only probe may additionally
  emit one of the two fixed logical key labels above and a `present`/`absent` boolean; it
  must reject dynamic key names and never emit a value. Logs contain no URL with
  credentials, event/transcript body, identity, locator, raw payload, or audio.
- No resource is created in Issue #4, so there is no new retention or deletion state.
  Future resource destruction follows the checked-in runbook and the then-current Issue
  #16/#19 data and backup evidence; absence from the IaC file is not proof of deletion.

## Acceptance criteria

- [ ] The only Railway desired-state file is `.railway/railway.ts`, using the pinned current
  IaC package and an externally gated CLI compatibility version rather than deprecated
  Config as Code.
- [ ] Offline type checking and tests cover all environment classes, exact topology,
  Singapore placement, commands, health checks, references, secret rules, default-off
  switches, determinism, and destructive-file exclusions.
- [ ] Offline desired state renders environment-local production/staging resource
  references and a false/fixture preview policy; the runbook keeps PR environments
  disabled until a later provider gate proves staging is the PR base, sealed values do not
  copy, and actual resources are isolated.
- [ ] Exactly one backend authority, private environment-local Postgres/Bucket resources,
  and one non-serving maintenance target are described without creating them.
- [ ] Every target's build/start/health behavior is documented; unimplemented service
  starts fail closed and no product route is claimed.
- [ ] Before any credential-bearing backend code/source or deployment, the runbook requires
  an exact-commit immutable image from a protected credential-free build with recorded
  digest, signature/provenance, SBOM, dependency/license review, and provider proof of no
  Railway source build/pre-deploy/install/autoupdate across persistent and preview targets.
- [ ] The separate migration phase names the canonical root, shared/exclusive database
  fence, durable one-use replay admission, 30-second lock timeout, short-lived least-
  privilege role, sealed temporary variable, immutable prebuilt fixed-dispatcher image, mandatory per-environment canary
  carrier deletion, set-bound recreation deployments/absence proof, and authoritative one-
  use-role revocation; no migration can coexist with the no-schema guard.
- [ ] Before the first maintenance canary, the owning Issue removes the Issue #4 custom
  build/start guards, proves active/staged custom start-command absence, and makes the
  reviewed image's exec-form fixed `ENTRYPOINT` with empty `CMD` the only dispatch path.
- [ ] The future maintenance runbook constrains deletion to exactly one canonical-room-
  all-sessions or immutable-session-only target and admits purge only from a committed,
  read-back-verified, recovery-protected `hidden` tombstone.
- [ ] The secret inventory names scopes, sealed/preserved state, safe local substitutes,
  provisioning/rotation/emergency owners, and prohibited credentials without values.
- [ ] Deployment, rollback, disable, live-plan, and destructive cleanup procedures are
  documented, and no apply/deploy/destruction automation is added.
- [ ] `make verify` and `git diff --check` pass with no secret, audio, production data,
  generated provider identifier, or unrelated feature implementation.
