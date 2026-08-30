# Intent: Establish a fail-closed Railway deployment skeleton

## Issue and owner

- GitHub Issue: #4
- Human owner: @Shuang-su
- Stage/area/risk: `stage:m0`, `area:deploy`, `type:chore`, `risk:medium`

## Problem

Livecho has no reviewable declaration of its Railway environments, service topology,
resource isolation, deployment commands, migration boundary, health checks, or secret
ownership. That makes it possible for future service work to grow around dashboard-only
state, accidentally share production resources with previews, or enable an incomplete
ingest path without an auditable kill switch.

Railway has also replaced its per-service `railway.json` / `railway.toml` Config as Code
surface with project-level Infrastructure as Code. New services cannot opt into the old
surface, and existing files stop being read after 2026-12-01, so the skeleton must use
the current `.railway/railway.ts` model rather than introduce a legacy configuration.

## Desired outcome

Add a deterministic, statically tested Railway Infrastructure as Code declaration for
one Livecho project in Singapore. For every selected Railway environment it describes:

- one non-serving web deployment target;
- exactly one non-serving backend deployment target and therefore no second online
  application authority;
- an environment-local managed Postgres resource;
- an environment-local private Bucket;
- one manually invoked, non-serving maintenance target; and
- explicit build, start, health, safety-variable, secret-slot, migration, deployment,
  rollback, and resource-destruction contracts.

The repository change remains fail-closed. It creates no Railway resource, writes no
secret, connects no production source, serves no product route, stores no production
data, and enables no real ingest. The service start targets deliberately refuse to run
until their owning feature Issues replace the guards. A later authorized operations
Issue must inspect a live `railway config plan --verbose` before applying this desired state.

## Non-goals

- Creating, linking, planning against, or applying changes to a real Railway project or
  environment.
- Connecting a production GitHub deployment source, adding an automatic production
  deployment, or claiming production readiness.
- Implementing the web application, backend API, database schema, migrations, archive,
  authentication, email, Bilibili ingest, worker gateway, or observability.
- Provisioning a real Resend key, application signing key, archive key, database
  credential, Bucket credential, Railway token, domain, or other secret.
- Enabling public or authenticated Bilibili acquisition, real community-worker audio,
  persistence, raw archival, email, history, or maintenance execution.
- Replacing the Issue #2 safety, rights, persistence, deletion, restore, and residual-risk
  gates. This skeleton records their disabled state; it does not satisfy them.

## Constraints and data impact

- `.railway/railway.ts` is the only Railway desired-state source. Legacy
  `railway.json`/`railway.toml` files, dashboard-only service settings presented as
  source of truth, and multiple IaC authoring files are prohibited.
- The TypeScript Railway SDK is an exact-version dependency. The later Railway CLI is an
  exact-version external operator tool, not a repository dependency, because its npm
  installer downloads a platform binary outside the tarball integrity boundary. Offline
  CI executes the DSL for production, staging, PR-like, unknown, and missing environment
  contexts; a live `plan` remains a later manual provider check after the rollout Issue
  records and verifies the exact CLI release archive and extracted-executable digests plus
  the parsed version.
- Production and staging must be persistent but isolated Railway environments. The later
  Railway project setup must select staging—not production—as the sole PR base. Railway
  creates PR environments by copying that base; it does not automatically evaluate this
  repository's environment classifier. Preview safety will therefore depend on staging's
  literal false/fixture baseline, sealed values being excluded from copies, and a
  separate provider check of the selected base. Railway-managed database and Bucket
  references resolve inside the selected environment; no provider resource ID or
  credential is shared in source.
- Every environment starts with fixture mode and all ingest, persistence, raw archive,
  email, real-worker-audio, global-serving, and maintenance switches off. An unknown or
  absent environment name receives the same preview restrictions.
- Web, the single backend, Postgres, and maintenance have explicit Singapore desired
  state; the private Bucket uses Railway's separate `sin` storage-region identifier. The
  maintenance target has no domain, cron, health route, automatic source, restart loop,
  or baseline resource credential; its 15-second provider-replacement drain exceeds the
  entrypoint's 10-second child-reap window, while an independent controller enforces a two-
  minute startup/binding limit and waits 46 minutes after observing the armed 45-minute
  internal supervisor. A future approved operation may run only behind a
  database-enforced mutual-exclusion fence and a durable one-use admission whose exact
  role/operation/image/manifest and opaque or keyed target binding can be consumed only
  once, so a provider replacement cannot sequentially replay it. An operation that can
  rewind the database ledger needs an equivalent admission authority outside its recovery
  set or remains prohibited. Its
  distinct, operation-scoped, time-bounded role is narrower than the backend along the
  exact environment, database, schema, operation, object-manifest, lifetime, and external-
  authority dimensions. This does not claim that migration DDL is a subset of backend DML.
- A real maintenance credential may reach only a prebuilt, reviewed immutable image at
  runtime, never a source build or package-install hook. The accepted image-owning Issue
  must remove the Issue #4 custom build/start guards and prove no provider start override,
  so the image's fixed exec-form `ENTRYPOINT` with empty `CMD` is authoritative. Its first use in each environment
  remains blocked until a sealed non-credential canary proves the exact-environment
  deployment, service-instance deletion, zero-credential recreation, and absence-probe
  path. Database-side revocation remains authoritative; provider cleanup never substitutes
  for dropping a unique role whose name and password are never reused.
- A backend that has any managed-resource reference or secret slot current or staged may
  likewise run only an exact-commit immutable image built and reviewed in a protected,
  credential-free release job. Its documented repository build command is not permission
  for a Railway source build; provider source builds, install hooks, and image auto-updates
  remain prohibited for credential-bearing production, staging, and preview instances.
- Secret values are never committed, rendered in tests, printed in plans, or copied to
  previews. `preserve()` records an existing-value slot but does not itself prove the
  provider variable is sealed; a later live-state review must prove sealing separately.
- Issue #4 creates neither Postgres nor Bucket and introduces no stored data. Raw archive
  and ordinary persistence remain disabled. No migration file, production record, raw
  event, account identity,
  credential, playback locator, archive material, or provider export is introduced.
- Audio is unaffected and remains ephemeral RAM-only. No audio, audio encoding, audio
  digest, or recoverable derivative enters configuration, fixtures, logs, state, or
  storage.
- Data classification: configuration metadata and synthetic local flags only; no
  production data, identity, secret, raw event, or persistent audio.

## Success signal

`make verify` type-checks and evaluates the pinned Railway DSL without network access or
credentials. Tests prove the exact topology, explicit Singapore desired state,
one-backend invariant, environment-local references, secret-free preview rendering,
default-off flags, fail-closed start commands, and zero-credential maintenance baseline.
The tests do not claim that automatic Railway PR copies execute the classifier. A human
can follow the checked-in runbook to distinguish offline validation, later provider-state
checks, staging rollout, explicit production approval, rollback, and destructive cleanup
without exposing values or changing live state during Issue #4.

## Human decision

- Status: Approved for artifact review and merge; implementation remains gated on this
  artifact landing in `main` and uses a separate branch and pull request.
- Approved by/date: @Shuang-su / 2026-08-30 (authorized this agent to continue and merge
  after repository checks and review gates pass).
