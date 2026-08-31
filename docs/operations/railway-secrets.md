# Railway references and secret-handling contract

## Scope

This inventory accompanies the repository-only Railway skeleton in Issue #4. It records
names, intended consumers, and future ownership. It does not prove that a Railway project,
environment, resource, variable, secret value, or deployment exists, and it authorizes no
provider operation.

Issue #4 supplies no credential value. A resolved reference, URI, password, token, key,
cookie, signed locator, provider identifier, or decrypted export must not be committed,
logged, placed in a fixture, copied into ordinary evidence, or exposed to a browser or
community worker. If scope, sealing, value provenance, or revocation is uncertain, the
consumer stays disabled.

Production and staging are separate security domains. Values are issued independently;
neither environment is a backup or template for the other. Preview/unclassified graphs
contain no persistent secret slot. Railway PR environments copy a configured base, so a
later live gate—not the synthetic `pr-*` test—must establish that staging is the only PR
base and that sealed values are excluded from copies.

## Non-secret safety literals

These are configuration guards, not credentials. They are the complete contents of the
root `.env.example` and the complete literal-variable set for `backend` and `maintenance`.
`web` receives none of them.

| Name | Required value |
| --- | --- |
| `LIVECHO_GLOBAL_SERVING_ENABLED` | `false` |
| `LIVECHO_INGEST_ENABLED` | `false` |
| `LIVECHO_INGEST_MODE` | `fixture` |
| `LIVECHO_PERSISTENCE_ENABLED` | `false` |
| `LIVECHO_RAW_ARCHIVE_ENABLED` | `false` |
| `LIVECHO_EMAIL_ENABLED` | `false` |
| `LIVECHO_REAL_WORKER_AUDIO_ENABLED` | `false` |
| `LIVECHO_MAINTENANCE_ENABLED` | `false` |

No environment class or Railway environment name is rendered as a service variable. A
later Issue may change a guard only with accepted artifacts and independent evidence for
that capability. The existence of a managed reference or reserved slot never overrides a
false guard.

## Managed references for backend

The selected environment's `backend` is the sole future consumer of these logical
references. Values are resolved by Railway and are never inlined in source or evidence.

| Backend variable | Logical source | Required form | Provisioning / emergency owner |
| --- | --- | --- | --- |
| `DATABASE_URL` | environment-local `Postgres` | typed `Postgres.env.DATABASE_URL` | database and operations / database security |
| `BUCKET` | environment-local private `Archive` | `ref(Archive, "BUCKET")` | data and operations / data security |
| `ENDPOINT` | `Archive` | `ref(Archive, "ENDPOINT")` | data and operations / data security |
| `REGION` | `Archive` | `ref(Archive, "REGION")` | data and operations / data security |
| `ACCESS_KEY_ID` | `Archive` | `ref(Archive, "ACCESS_KEY_ID")` | data and security / data security |
| `SECRET_ACCESS_KEY` | `Archive` | `ref(Archive, "SECRET_ACCESS_KEY")` | data and security / data security |

`Archive` is desired in Bucket region `sin`; its `REGION` output is not evidence of that
physical placement. Likewise, logical references do not prove provider isolation. A later
rollout needs redacted plan and provider-metadata checks for each environment.

`web` has no database, Bucket, mail, signing, archive, deployment, maintenance, or
platform credential. `maintenance` has no managed reference at baseline. Service
variables are available during builds as well as runtime, so any later backend carrying
these references must pull an immutable exact-digest OCI image created by a protected,
credential-free release job. Railway source builds, pre-deploy commands, install hooks,
and image auto-update are prohibited for a credential-bearing target.

## Persistent backend slots

Exact `production` and `staging` renders reserve these six names using `preserve()`.
Issue #4 supplies no value and implements no consumer.

| Name | Environment and consumer | Issue #4 state | Rotation owner | Emergency owner |
| --- | --- | --- | --- | --- |
| `LIVECHO_SESSION_SIGNING_KEY` | one persistent environment's backend | preserved name only | auth/security | security |
| `LIVECHO_WORKER_TOKEN_SIGNING_KEY` | one persistent environment's backend | preserved name only | worker/security | security |
| `LIVECHO_ARCHIVE_ENCRYPTION_KEY` | one persistent environment's backend; archive off | preserved name only | data/security | security |
| `LIVECHO_RECOVERY_INTEGRITY_KEY` | one persistent environment's backend; recovery off | preserved name only | operations/security | security |
| `LIVECHO_AUDIT_INTEGRITY_KEY` | one persistent environment's backend; audit persistence off | preserved name only | data/security | security |
| `RESEND_API_KEY` | one persistent environment's backend; email off | preserved name only | auth/operations | auth/operations |

`preserve()` asks the IaC layer not to replace an already managed value. It neither seals
a value nor proves that one exists. Before provisioning, the owning Issue must verify the
exact environment and consumer, independently generate the value, mark it provider-sealed,
prove previews cannot inherit it, and make the consumer reject absence without logging.
Ordinary evidence may retain only the name, scope, sealed-state category, timestamps,
owners, reviewer, and a redacted result.

Rotate or revoke after suspected disclosure, owner/consumer compromise, scope change,
provider drift, or the owning Issue's cryptographic lifetime. An ambiguous provider reply
is an incident: keep the feature off, replace the authority, and inspect every deployment
that could have received it at build or runtime.

## Temporary maintenance database authority

`LIVECHO_MAINTENANCE_DATABASE_URL` is deliberately absent from the baseline graph. It is
not a `preserve()` slot, is not derived from the backend reference, and has no local
substitute. A later accepted operation may stage it only after the exact environment has
passed the immutable-image, fixed-dispatcher, sealing-canary, carrier-deletion,
zero-credential recreation, and absence-probe gates in
[the deployment contract](railway-deployment.md).

For one operation, an authorized database owner creates a globally unique login role and
one-use password. The role:

- is bound to one environment, database, schema, operation, reviewed image/manifest, and
  recovery-protected target reference;
- is never the backend role and is never reused;
- is `NOINHERIT`, expires in at most 60 minutes, and has only manifest-required
  database/schema/table/function privileges;
- has no superuser, create-role, create-database, replication, or bypass-RLS authority;
  and
- may receive non-admin membership in the environment-local stable `NOLOGIN` schema owner
  only for an accepted migration manifest that requires DDL.

The database-owner credential never enters Railway, CI, the repository, or the maintenance
controller. Only the temporary role URI may be entered, through the separately rehearsed
single-variable dashboard flow, and it must be sealed. Issue #4 does not authorize a CLI,
API, or Raw Editor lifecycle for that sealed URI.

The restricted operation inventory may retain the role name, expiry, logical scope,
approved image/manifest digests, sealed-state metadata, timestamps, owner, and redacted
outcomes—never the URI or password. Closure requires all of the following:

1. restore `LIVECHO_MAINTENANCE_ENABLED=false` and set the role `NOLOGIN`;
2. stop or reconcile every exact carrier deployment;
3. terminate every session for the role;
4. compare ownership and grants with the approved manifest, move only expected persistent
   objects to the stable `NOLOGIN` owner, remove residual grants, and drop the role;
5. remove the sealed URI through the pre-proved dashboard flow;
6. delete only the exact environment's maintenance instance after database revocation;
7. recreate the zero-credential instance, reconcile the nonempty deployment delta, and
   obtain at least one `maintenance-uri: absent` probe; and
8. verify current and staged canary/URI absence and non-actionability of prior carriers.

Credential expiry does not terminate an existing database session. Provider cleanup does
not replace database revocation and does not prove removal from provider audit or backups.
A restore may resurrect a role or admission record, so recovery remains offline until the
role ledger and a recovery-safe one-use admission authority outside the rewound set are
reconciled.

## External operator and automation credentials

These future credential classes are not service variables and are not created by Issue #4.

| Class | Narrow future use | Owner / revocation rule |
| --- | --- | --- |
| Environment-scoped Railway Project Token | one bounded controller for deployment create/observe/stop in one exact environment | operations; revoke after complete reconciliation or explicit terminal handoff, and immediately on scope ambiguity or disclosure |
| Interactive Railway Project Owner session | separately approved dual-bound maintenance-instance deletion | repository/project owner using 2FA; token environment variables unset; end after the action |
| Release/CI credential | protected image publication and provenance only | release/security; rotate on workflow, runner, registry, or signing compromise |
| Database-owner credential | issue/revoke the temporary role and perform exact ownership cleanup | database/security; never exposed to a service or controller |
| Provider-generated Postgres/Bucket credentials | exact environment's reviewed immutable backend at runtime | database or data operations; rotate on exposure, drift, or provider event |

The controller has no account/workspace token, database-owner authority, interactive Owner
session, or service-deletion permission. The 2FA Owner does not give deletion authority or
provider identifiers to the controller. Exact identifiers, where operationally necessary,
remain only in retention-bounded provider-native or restricted admin records; ordinary
evidence uses an opaque audit reference.

## Credentials that must not exist

The following are prohibited rather than empty reservations:

- Bilibili account credentials, cookies, authenticated tokens, or signed playback URLs;
- credentials or DRM material used to evade login, payment, geography, or platform limits;
- server-provided worker download credentials or arbitrary download URLs;
- database, Bucket, mail, signing, archive, deployment, or maintenance credentials sent to
  browsers or community workers;
- archive encryption keys sent to community workers;
- a secret shared between production and staging, or copied into preview/shared context;
  and
- PCM, encoded audio, audio base64, stream buffers, audio digests, or recoverable audio
  derivatives used as fixtures, configuration, logs, or evidence.

Discovery requires immediate capability disablement, authority revocation/replacement,
deployment and log review, value-free quarantine, and the incident runbook. Do not
reproduce the discovered value in a ticket or evidence file.

## Safe local behavior

Local work uses only the eight false/fixture literals. Database and archive adapters remain
disabled; a later owning Issue may use a bounded in-memory fake or loopback-only synthetic
fixture service. Mail uses an in-memory no-send sink. Tests that later need signing or
integrity material generate it per process and never commit, log, snapshot, cache, or write
it to disk. Ingest accepts synthetic fixture input without an account or playback locator.
Maintenance has no local credential fallback.

No local substitute may contain production data, write audio, or persist raw unencrypted
data. Audio remains ephemeral in memory only under separately accepted runtime bounds.

## Value-free review record

Before a future provision, rotation, or revocation, record only:

1. logical name/class, one environment, and one consumer;
2. provisioning, rotation, revocation, and emergency owners;
3. sealing metadata where applicable, without treating `preserve()` as proof;
4. immutable image identity and absence of provider build/install/pre-deploy paths;
5. preview exclusion and production/staging non-reuse;
6. timestamps, reviewer, redacted result, and restricted-audit reference; and
7. disable/revoke/replacement outcome for any suspected disclosure.

Issue #4 performs no Railway login, link, plan, apply, deploy, variable write, secret
provisioning, resource mutation, rotation, or destruction.
