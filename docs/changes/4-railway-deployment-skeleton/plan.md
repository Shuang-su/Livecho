# Implementation plan: Fail-closed Railway deployment skeleton

## Order of work

1. Merge this artifact-only pull request before changing configuration, dependencies,
   Make targets, CI, operations documentation, or runtime paths. Start the implementation
   branch from the resulting `main` commit and keep Issue #4 as its only feature Issue.
2. Before assigning any implementation work, append a fresh implementer exposure record
   to `evidence.md`: identity, role and paths, date, every upstream/context material seen,
   exposed material classes, assignment decision, and named independent reviewer. Commit
   that record as the implementation branch's first commit, before dependency or code
   changes. A requirements-author record in the artifact is not a substitute.
3. Before adding a package, record immutable npm provenance for every new direct
   dependency: exact version, repository/git revision, registry integrity, license, and
   distribution/notice obligations. Reject `@railway/cli` as a repository dependency
   because its postinstall-fetched binary is outside npm integrity and would require a
   pnpm build allowlist. After lock generation, inventory and review every transitive
   license and unresolved obligation; a missing or incompatible record removes the
   dependency rather than weakening the gate.
4. Add `.railway` to `pnpm-workspace.yaml` and create the private
   `@livecho/railway-config` workspace. Pin `railway@3.11.0`,
   `typescript@7.0.2`, `vitest@4.1.11`, and `@types/node@26.4.0`; refresh the lockfile with
   the repository's pinned pnpm version. Add no `onlyBuiltDependencies`/`allowBuilds`
   exception and no downloaded CLI binary.
5. Implement `.railway/railway.ts` as the only authoring file. Export pure environment
   classification and non-secret policy constants, then declare `web`, exactly one
   `backend`, Singapore `Postgres`, `sin` `Archive`, and zero-credential `maintenance`
   with the exact placement, command, health, structured reference, preserved-slot,
   restart-policy, 15-second maintenance drain, and no-source behavior in the specification. Do not configure
   `preDeploy`, legacy Config as Code, provider IDs, values, or an apply path.
6. Add `.railway/railway.test.ts` and strict TypeScript configuration. Evaluate production,
   staging, PR-like, unknown, empty, and missing contexts; recursively inspect the exact
   pinned DSL output for topology, all region structures, typed/generic references,
   commands, exact eight-key safety assignments on backend/maintenance with none on web,
   six persistent-backend-only preserved slots, no class/environment service metadata,
   restart policy, exact maintenance drain, preview rendering, maintenance, determinism, and forbidden files. Label
   synthetic PR coverage as render policy, not provider-state proof.
7. Add `.env.example` with exactly the eight specified safety assignments: fixture ingest
   mode and seven false switches, with no class or extra assignment. Add
   `docs/operations/railway-secrets.md` with the exact reference/secret inventory,
   environment scopes, sealing caveat, temporary maintenance-role lifecycle, safe
   substitutes, and provisioning, rotation, revocation, and emergency owners. Search the
   entire implementation diff for values, cookies, tokens, signed URLs, provider IDs,
   audio, and production exports.
8. Add the five Make contracts. `railway-check` runs only the offline workspace checks;
   `railway-start-web`, `railway-start-backend`, and `railway-run-maintenance` are explicit
   non-zero guards with no side effect; `railway-migrate` first requires any `db` ancestor
   to be a real non-symlink directory, then returns `NO_MIGRATIONS` only when `lstat` would
   report no `db/migrations/` entry and fails for every existing root-entry kind, including
   an empty directory or dangling symlink. Add focused automated tests for the guards
   rather than depending on prose.
9. Add `docs/operations/railway-deployment.md`. Cover empty environment creation,
   provider-verified staging PR base, an access-restricted disposable copy for CLI link
   metadata, owner-approved asset name/URL/platform plus separate archive and extracted-
   executable SHA-256 evidence for external `@railway/cli@5.45.10`, archive verification
   before disposable extraction, executable digest and parsed exact version verification
   before each authenticated command, linked-target checks before/after a redacted verbose
   plan,
   destruction of that copy, separate provider metadata evidence, the exact-commit backend
   image gate (credential-free protected build, digest, signature/provenance, SBOM,
   dependency/license review, and no Railway source build/pre-deploy/install/autoupdate in
   production, staging, or previews), the shared/exclusive advisory-lock fence, durable
   one-use admission bound to the exact role/operation/image/manifest and an opaque or keyed
   target reference, plus a recovery-boundary-safe authority for restore/recovery, immutable
   prebuilt maintenance-image verification and removal/read-back absence of the Issue #4
   custom build/start overrides so the image `ENTRYPOINT` is authoritative, a separate per-
   environment sealed-variable canary carrier deployment, dual-bound environment/service
   instance deletion with cross-environment non-interference evidence, zero-credential
   recreation, set-based pre/post inventory ownership of its nonempty provider-triggered
   deployment delta, at least one fixed-dispatcher absence result, terminal reconciliation
   and exact-ID stop/cancel of every delta member with no second trigger before the first
   real URI, dashboard-
   only per-variable URI staging, a frozen carrier inventory, the pre-proved URI removal/
   recreation sequence, exact-target/no-deploy flag writes/resets, secret-metadata-only
   read-back plus an exact allowlist of non-secret safety literals,
   deterministic digests of redacted active/staged logical snapshots, any provider-exposed
   revision markers, and a freeze on every other IaC/source/image/
   variable/service/domain/scale/environment mutation,
   privilege separation between the non-destructive controller and interactive cleanup
   operator, a bounded Owner-approved project-wide maintenance change freeze with mutator
   acknowledgements/readbacks and sibling-environment quiescence,
   controller-token revocation only after complete reconciliation or an acknowledged
   terminal handoff rather than prematurely at the operation process deadline,
   prohibition of `service delete --yes`,
   operation-specific role issue/revoke flow, an entrypoint supervisor that enforces a
   monotonic 45-minute deadline with bounded `TERM`/`KILL`, an exact 15-second maintenance
   drain for provider replacement, an independent provider kill-after fallback pre-armed
   for one environment/service with a two-minute startup/binding deadline and a second
   deadline 46 minutes after observing the post-arm/pre-child marker, and acting as the
   sole deploy caller, immediate volatile binding/read-back of the returned immutable
   deployment ID, the exact-ID Public API stop operation, a provider-native or access-
   restricted retention-bounded admin record for exact-target recovery/audit with only an
   opaque reference in ordinary evidence, prohibition of the mutable
   `railway down` operation, and an independent operator/database-owner response when
   binding, supervision, or stop is unconfirmed, `NOLOGIN`, stable schema ownership,
   residual-session/ownership cleanup, service deployment order,
   deletion's exact single-target and verified-`hidden`-tombstone admission, health
   cutover, production owner gate, rollback, disable, and destructive cleanup. Mark every
   live command as later manual work and do not execute it for Issue #4.
10. Link the operations documents from the root README without claiming that controls or
    environments exist. Run focused checks and the full deterministic repository gate;
    record exact command, result, date, and commit in this directory's `evidence.md`.
11. Have an isolated post-implementation reviewer who did not patch the implementation
    record immutable comparison inputs, scope, tools/thresholds, dependency/license
    result, provenance/similarity result, and any quarantined path. Resolve every material
    finding, including trust/no-flow, one-backend, PR-base, provider-gap, secret, audio,
    source/deploy/apply, and destructive-omission findings, before merge.
12. Open one implementation pull request that closes #4. Merge only after required CI and
    final-head review are clean. Do not link a Railway project, create an environment,
    run a live plan, apply the IaC, upload code, or close the Issue through any other path.

## Verification

Artifact pull request:

- `uv run python tools/check_change_artifacts.py`
- `make artifacts`
- `make verify`
- `git diff --check`
- `git diff --name-only origin/main...HEAD` — exactly the four files under
  `docs/changes/4-railway-deployment-skeleton/`

Focused implementation checks:

- `make bootstrap`
- `make railway-check`
- `pnpm --filter @livecho/railway-config lint`
- `pnpm --filter @livecho/railway-config typecheck`
- `pnpm --filter @livecho/railway-config test`
- `pnpm --filter @livecho/railway-config build`
- `pnpm licenses list --json` — reviewed transitive license inventory with every new
  package obligation recorded in `evidence.md`
- `pnpm ignored-builds` plus manifest/lock inspection — no ignored or allowlisted Railway
  CLI postinstall and no `@railway/cli` repository dependency/binary
- focused tests for the fail-closed start targets; absent, file, empty/non-empty directory,
  valid-symlink, and dangling-symlink states of the canonical `db/migrations/` guard; and a
  symlinked `db` parent whose external target both has and lacks `migrations`
- future owning-Issue tests for the complete maintenance flag/two-key membership matrix,
  rejection of every argument or override, value-access traps on both probe branches, and
  output free of values/dynamic keys
- future supervisor tests for normal completion, monotonic timeout, external `TERM`, a child
  ignoring `TERM`, and a same-process-group grandchild, with marker-after-arm/before-child
  ordering, bounded kill/reap, and no escape
- future admission tests with concurrent and sequential contenders proving exactly one
  atomic `PENDING` to `CLAIMED` transition; rejection of missing, duplicate, mismatched,
  already-claimed, terminal, and uncertain states; crash-after-claim non-retry; provider
  replacement/redeploy/rollback denial after lock release; transactional first-schema
  bootstrap; and restore/recovery proof that the authority cannot be rewound with the data
- exact structural coverage for maintenance `drainingSeconds=15`, while later provider
  evidence must not claim an exact-ID API stop honors replacement-drain behavior
- `rg --files -g 'railway.json' -g 'railway.toml' -g '.railway/railway.py' -g '.railway/railway.go'`
  — no matches
- an initial `lstat` gate requiring the `.railway` root itself to be a real non-symlink
  directory; exact tracked/nonignored source allowlist entries that must be regular
  non-symlink files; and a physical tree scan that prunes `node_modules` only after its
  root is verified as a real directory — ignored/untracked CLI link metadata, provider
  ID/state, second authoring file, and unexpected generated content all fail
- focused negative tests replace the entire `.railway` root with a symlink, replace an
  allowlisted path with a valid and a dangling symlink, and replace the
  `.railway/node_modules` root with a symlink — each must fail, while pnpm links inside a
  verified real `node_modules` directory remain allowed
- `rg -n 'show-values|include-variables|config apply|railway up|environment delete' Makefile package.json .github .railway`
  — no executable automation; documentation/test assertions may name prohibited text
- `git grep -n -I -E '(BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|RAILWAY_(API_)?TOKEN=|RESEND_API_KEY=.+|BILI.*(COOKIE|TOKEN)=.+)' -- ':!docs/changes/4-railway-deployment-skeleton/*'`
  — no value-bearing match
- `git diff --check`
- `make verify`

Later provider evidence, explicitly not executed in Issue #4:

- `railway status --json` before and after an authenticated `railway config plan --verbose`,
  using the exact external CLI only after the approved platform release archive's SHA-256
  is verified before disposable extraction and the separately approved executable SHA-256
  plus parsed `railway --version == 5.45.10` are verified before every authenticated
  invocation;
  retain only an allowlisted projection of logical names, counts, regions, and status
  categories with provider IDs, URLs, variables, and all other fields removed, proving the
  linked project/environment stayed the intended target while the redacted logical diff
  and proposed placement were reviewed; link metadata exists only in an access-restricted
  disposable copy of the reviewed commit and that copy is destroyed after evidence
  extraction;
- separate read-only provider metadata/control-panel evidence confirming realized
  web/backend/maintenance/Postgres Singapore placement, Bucket physical region `sin`,
  production/staging resource separation, sealed secret metadata, generated/public
  domains, production source/autodeploy state, and staging as the PR base—none of which is
  inferred from `config plan` alone; before any credential-bearing backend deploy, the same
  evidence proves the exact-commit image digest, image autoupdates off, and no Railway build/
  pre-deploy/install phase for the exact persistent or preview target; it also proves the
  maintenance service's realized 15-second replacement drain, approved image digest, and
  active/staged absence of any custom build/start/pre-deploy override before the canary;
- before any real maintenance URI in a target environment, the complete immutable-image/
  fixed-dispatcher/canary/dual-bound instance-delete/set-bound recreation absence rehearsal
  above, including the project-wide governance/readback freeze, unchanged sibling instances,
  carrier action rejection, and a redacted recreation-only plan; and
- a separate repository-owner-approved production plan/apply and service deployment only
  in the Issue that owns production rollout.

## Rollout and rollback

Issue #4 rollout ends when repository-only configuration, offline tests, guards, and
runbooks merge. It performs no Railway login/link, environment creation, plan, apply,
deployment, domain change, variable write, migration, or resource destruction.

A later authorized rollout proceeds in this order: create an empty staging environment;
prove the linked target; review and apply a redacted staging plan; set only independently
issued sealed staging values; keep all flags false/fixture; select and verify staging as
the PR base; prove isolation and placement through separate provider metadata; and run the
Issue #4 no-schema guard while every flag remains false. After a future schema/operation
Issue, first add the reviewed fixed dispatcher and rehearse the exact dashboard lifecycle
separately in the target environment. First build and review a secret-free immutable image,
record its digest/provenance, then review an exact-target compatibility plan that clears the
Issue #4 custom build/start commands and configures that digest with no provider source
build, pre-deploy, or install hook. Pre-arm a bounded inventory-reconciliation window before
applying only that plan. Repeatedly
diff through the provider-settled final readback; bind every member of the nonempty new-ID
set to the environment/service and image digest with no custom start override; require every started member to report
`maintenance-uri: absent`, at least one member to complete that probe, and every member to
reach an explicit stop/cancel terminal state; and fail on an empty set, unbound/mismatched/
unreadable ID, missing probe result, or unsettled queue. Then prove both active and staged
custom start-command absence in provider metadata. With the maintenance flag
false and no real URI, create and seal `LIVECHO_MAINTENANCE_SEAL_CANARY` with a volatile
non-credential value and prove staged-without-deploy behavior. The short-deadline controller
then owns and binds one exact-ID deployment whose fixed `canary` probe reports only
`present`, and stops it. Remove the canary through the dashboard, enumerate every carrier,
snapshot all sibling-environment maintenance instances, and obtain separate owner approval
for the pinned interactive `serviceDelete(environmentId, serviceId)` call after both opaque
IDs are freshly resolved and verified. A separately authenticated cleanup operator—not the
environment-scoped Project-Token controller—is a Railway Project Owner with token
environment variables unset. The Owner must first declare the bounded project-wide change
freeze, obtain every authorized mutator's acknowledgement, and prove each sibling has no
current/staged canary or URI, a false maintenance flag, and no active operation/cleanup.
After matching configuration/activity readbacks, the Owner accepts the target/2FA prompt
without `--yes`. From that authorized session, accept
only typed not-found/deleted/non-actionable carrier results—not auth/network/unknown errors;
an unexpectedly accepted action is stopped by the controller and fails cleanup. Prove every
carrier rejects restart/redeploy/rollback and
every sibling instance is unchanged. Review a redacted plan containing only the expected
target-instance recreation and pre-arm the same bounded set-based reconciliation. Obtain
separate apply approval, restore the zero-credential immutable-image target under a new
cleanup generation and any available instance marker without requiring the project service
ID to change, and apply the same nonempty-delta binding/probe/terminal-stop rules through the
provider-settled final readback. That bound recreation set is the absence proof; no second
deploy trigger is allowed. An empty/unbound/mismatched/unreadable/unsettled set, missing
probe result, deployment `Remove`, single-ID delete, broader plan, or cross-environment
change does not qualify. Prove provider active/staged state clear. Only
after the authorized Owner repeats every pre-delete carrier action check and again obtains
only typed not-found/deleted/non-actionable results may the owner end the freeze. This
evidence does not transfer to another environment. Revoke the rehearsal controller token
after complete reconciliation or an acknowledged terminal handoff; a real operation must
receive a fresh exact-environment token. Only after that proof may the owner stop
serving; keep every serving, ingest, persistence,
archive, email, and worker flag false/fixture; issue a globally unique bounded maintenance
role with a one-use password and create its unique `PENDING` admission bound to the exact
environment/database/schema/operation/image/manifest plus a recovery-protected opaque
target reference or canonical-control-record keyed digest—never a low-entropy target's
unkeyed digest; freeze the instance and capture a deterministic digest of its
redacted active/staged logical snapshot, any provider-exposed revision marker, and its
deployment inventory; perform the sole reviewed target-bound URI create/edit, `Seal`, and
staged write through the proven single-variable dashboard flow; read back only staged key/
sealed metadata and proof that no unowned deployment was created; verify the
reviewed immutable image digest, 15-second provider replacement drain, and its entrypoint-
supervisor contract; pre-arm and read back the exact environment/service, 45-minute internal
duration, two-minute startup/binding deadline, and 46-minute post-observed-start provider
delay; and stage only the maintenance flag true
with documented exact-target no-deploy semantics. The
external controller then acts as sole deploy caller, immediately captures/verifies the
returned immutable deployment ID, and supervises the run as defense in depth while the
entrypoint arms its timer and the operation child acquires the exclusive advisory lock,
then atomically commits the sole exact `PENDING` to `CLAIMED` transition before business
I/O. Any later provider-created carrier must be denied admission and stopped even after
the lock becomes available; a crash or ambiguous claim cannot be retried. On every outcome,
immediately restore the maintenance flag to false with no-deploy semantics and set the role
`NOLOGIN`, then stop every carrier ID, terminate residual role sessions, record a terminal
admission outcome without ever reopening it, and prove all persistent objects remain
with the stable `NOLOGIN` schema owner, revoke/drop the role, and remove the URI through
the pre-proved cleanup flow. Database revocation must finish before provider deletion.
Enumerate and stop every URI carrier, snapshot sibling environments, delete only the exact
dual-bound target instance, and prove carrier mutations fail and siblings are unchanged.
Pre-arm the same bounded set-based reconciliation, then apply an owner-approved redacted
plan that recreates only the zero-credential immutable-image target under a new cleanup
generation and any available instance marker; the logical project service ID may remain
stable. Apply the same nonempty-delta binding/probe/terminal-stop rules through the provider-
settled final readback; that bound recreation set is the absence proof and no second deploy
trigger is allowed. Never
reuse the dropped role name or password. After provider active/staged state is clear, the
authorized Owner must repeat every
pre-delete carrier action check and again obtain only typed not-found/deleted/non-actionable
results. Revoke the controller token only after complete reconciliation or an acknowledged
terminal handoff; the child result or operation deadline must not revoke it prematurely.
Only then, and only after an exact-commit backend OCI image has been produced by the
protected credential-free release job with its digest, signature/provenance, SBOM,
dependency/license review, and verification recorded, may the Owner configure that digest
and bind every resulting deployment ID to the exact environment/service/commit/digest.
At least one reviewed-image deployment must pass the runtime health contract; every other
new ID must reach a reconciled terminal state, and any mismatch or unsettled ID fails the
rollout. Provider metadata must prove no backend GitHub source, Railway build/pre-deploy/
install hook, or image auto-update; this gate also applies to every preview. Web may then
deploy under its own accepted Issue. Verify health and disable paths, then collect
new owner approval before even planning production. Production never inherits staging
values and never autodeploys.

Repository rollback is a normal revert of the Issue #4 implementation commit. If IaC has
not been applied, that is complete. If a later Issue has applied it, first generate and
review a redacted plan from the reverted tree; never apply an unexpected deletion. Roll
back an application to a retained prior successful Railway deployment before considering
schema action. Do not run destructive down migrations. An incompatible or ambiguous
database, safety state, or maintenance result remains offline until an approved recovery
operation completes. After any database restore, enumerate both role and recovery-safe
admission ledgers, irreversibly cancel every restored nonterminal/unknown/inconsistent
admission in the recovery window, and prove every recorded one-use maintenance role still
absent or, for each present role, set `NOLOGIN`, terminate exact-role sessions, reconcile
ownership/grants against the approved manifest, reassign only exact expected objects to the
stable `NOLOGIN` owner, keep unknown/extra ownership offline, run `DROP OWNED`/residual-grant
revocation, and drop the role before traffic or another maintenance operation. A missing
role/admission ledger, rewindable admission authority, or unbounded recovery window remains
offline.

Permanent resource destruction is never part of rollback or CI. A later runbook operator
first disables serving, satisfies current backup/deletion evidence, identifies the exact
non-production environment, reviews the destructive plan, obtains repository-owner
approval, and uses Railway's explicit destructive confirmation. The only exception is the
stateless maintenance-instance carrier cleanup specified above, after database-role
revocation and under its dual-bound canary/interactive-Owner/non-data/sibling/recreation
gates; it is not an emergency stop. Production project, project-level service, Postgres,
Bucket, and backup deletion require their then-current #16/#19 evidence and are outside
this Issue.

## Open decisions

None for Issue #4. Runtime package paths, implemented start commands, schemas, migration
framework, public domains, automatic staging deploys, secret values, encryption format,
and production enablement deliberately belong to their named later Issues and cannot be
inferred from this skeleton.
