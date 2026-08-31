# Evidence: Fail-closed Railway deployment skeleton

## Artifact approval

- Artifact PR: [#25](https://github.com/Shuang-su/Livecho/pull/25) (artifact-only; does not
  close Issue #4)
- Approved by/date: @Shuang-su / 2026-08-30 (authorized continuation and merge after
  repository verification and review gates pass)

## Requirements-author exposure and assignment

- Identity/role/path/date: `/root` (OpenAI Codex), Issue #4 requirements-artifact author,
  `docs/changes/4-railway-deployment-skeleton/**`, 2026-08-30.
- Livecho material viewed: Issue #4; repository `AGENTS.md`; accepted Issues #1–#3
  artifacts; Issue #2 ADR, trust/data-flow records, and independent-implementation policy;
  current repository configuration and tests.
- Upstream/vendor material viewed: Railway official Infrastructure as Code, reference,
  environments, PR environments, variables/sealing, services/image-source/deployment
  lifecycle and teardown, start/pre-deploy, CLI/config/variable/deployment,
  Public API deployment/service management, token and project-member permissions, restart
  policy, regions, Buckets, health-check, retention, and rollback documentation; npm metadata
  and published package
  material for `railway@3.11.0`; the `@railway/cli@5.45.10` npm manifest, installer, and
  postinstall behavior; the published Railway SDK declarations/source for commit
  `c1b6ea8dd3e815e57257b1f17637e59d31db73b5`; the pinned CLI service-delete mutation and
  command source at `6f1b464eb96793700a5d02d2e55ecf69037ccc35`; and read-only sub-reviewer fact summaries
  derived from those materials. Exposure included vendor source and generated reviewer
  summaries, but no copied implementation text or distinctive expression is an input to
  Livecho code.
- Exclusions: no LAPLACE source, tests, fixtures, schemas, configuration, comments,
  documentation, assets, screenshots, pasted snippets, generated code, or distinctive
  implementation summaries were viewed. No prior contribution to those upstream projects
  is known in this task context.
- Assignment decision/reviewer: permitted to author this requirements artifact only.
  Implementation is not yet assigned; a fresh exposure/assignment record and named
  isolated implementation reviewer must be committed before dependencies or code.
  `/root/issue4_artifact_review` and `/root/change_artifact_audit` performed independent
  read-only whole-artifact reviews; `/root/railway_runtime_gate_review` independently
  reviewed the credential-bearing backend build gate and maintenance recreation-deployment
  reconciliation. None patched the files.

## Implementation exposure and assignment

- Identity/role/paths/date: `/root` (OpenAI Codex), Issue #4 implementation author,
  `.railway/**`, `.env.example`, `pnpm-workspace.yaml`, `pnpm-lock.yaml`, `Makefile`,
  `README.md`, `docs/operations/railway-deployment.md`,
  `docs/operations/railway-secrets.md`, focused repository tests, and this evidence file,
  2026-08-31.
- Livecho material viewed before implementation: GitHub Issue #4; repository `AGENTS.md`;
  all accepted Issue #4 intent/spec/plan/evidence; accepted Issues #1–#3 records referenced
  by the artifact; the current `main` tree, root workspace manifest, Makefile, README,
  verification workflow, workspace-script checker, protocol workspace layout, and existing
  foundation verification conventions.
- Upstream/context material viewed: the official Railway documentation, npm metadata, and
  immutable Railway SDK/CLI source revisions enumerated in the provider fact/source map
  below; read-only artifact-review findings derived from those materials; and official
  OpenAI Developer Commands documentation solely to verify the local Codex `/status`
  quota-reading workflow. The OpenAI material does not inform repository implementation.
- Exclusions: no LAPLACE source, tests, fixtures, schemas, configuration, comments,
  documentation, assets, screenshots, pasted snippets, generated code, or distinctive
  implementation summaries were viewed. No third-party implementation repository is an
  implementation input. Railway package declarations are compatibility facts, not code to
  copy.
- Assignment decision/reviewer: repository owner authorization permits only the Issue #4
  repository skeleton and evidence in the paths above. It does not authorize Railway
  login, link, plan, apply, deploy, variable mutation, environment/resource creation, or
  destruction. `/root/issue4_security_test_audit` is the named isolated implementation
  reviewer; it performs read-only review and must not patch implementation files.

## Implementation collaboration exposure and process correction

- Identity/role/paths/date: `/root/issue4_repo_audit` (OpenAI Codex child agent), first a
  read-only Issue #4 repository auditor and later an operations-document draft author for
  `docs/operations/railway-secrets.md` and
  `docs/operations/railway-deployment.md`, 2026-08-31.
- Material viewed before the draft assignment: repository `AGENTS.md`; GitHub Issue #4;
  all accepted Issue #4 intent/spec/plan/evidence; the accepted Issue #2 architecture,
  threat, lifecycle, incident, policy, and independent-implementation records; the current
  repository baseline; and `/root`'s implementation-exposure commit. The child agent saw
  no LAPLACE source, test, fixture, schema, configuration, documentation, asset,
  screenshot, pasted snippet, generated code, or distinctive implementation summary, and
  no other third-party implementation was a drafting input.
- Actual assignment and correction: after completing its read-only audit, the child agent
  was instructed to draft the two operations documents. That was substantive authorship,
  but its individual author identity had not been recorded and committed before the
  assignment. Treating the child as implicitly covered by the parent `/root` identity
  would be inaccurate. The two uncommitted drafts were therefore removed after parent
  review and before inclusion in an implementation snapshot. The child performs no
  further implementation work and is not an independent reviewer of either path.
- `/root` exposure addendum: `/root` read the discarded internal drafts. They were prose
  derived only from the accepted Livecho artifacts above, but they are still disclosed as
  internal requirements-derived draft material. This record is committed before `/root`
  independently forms the final two documents from the accepted Issue #4 intent/spec/plan
  and takes sole authorship responsibility under the paths already authorized in the
  first implementation-exposure record.
- Process classification and reviewer: the missed per-agent pre-assignment record is a
  process deviation, not a secret, audio, license, or external-source contamination event.
  It is not repaired by rewriting the first commit or pretending the record predated the
  work. Remediation is the truthful record here, removal of the drafts, fresh parent
  authorship after this commit, and final read-only review by the already named isolated
  reviewer `/root/issue4_security_test_audit`.

## Planned dependency provenance pre-audit

| Package | Immutable provenance | Observed license | Current decision/obligation |
| --- | --- | --- | --- |
| `railway@3.11.0` | npm SRI `sha512-ehLFHCxV+gITWeBlIVaXulXaVRg4LCxqm0bq64iXSwYL1DESd0pUeLYMP/BMBhnZWeFFBYyJCREaq+Nka7Wgmw==`; `railwayapp/railway-ts-sdk@c1b6ea8dd3e815e57257b1f17637e59d31db73b5` | MIT | Candidate package dependency only; no source copy. Preserve its packaged license/notice if dependency contents are later distributed. |
| `@railway/cli@5.45.10` | npm installer SRI `sha512-bpejtmRBxX98fVHc7SsxxO9IgcSX8rccMlryQsNLm69RHFLyy7az/7j34mY23bT3jBJ2B3c84Ysb2ry5OAJIPA==`; `railwayapp/cli@6f1b464eb96793700a5d02d2e55ecf69037ccc35` | ISC | Rejected as a repository dependency: the SRI covers the JS installer, not its postinstall-fetched platform binary, and pnpm correctly blocks that build absent an allowlist. A later rollout must approve the exact official asset name/URL/platform, verify its archive SHA-256 before disposable extraction, and separately approve/reverify the extracted executable SHA-256 plus parsed version before use. |

`typescript@7.0.2`, `vitest@4.1.11`, and `@types/node@26.4.0` are already exact repository
dependencies and are reused rather than newly introduced. This pre-audit does not approve
a lockfile: before implementation code, the implementation branch must generate the lock,
record every new transitive package and license, resolve distribution obligations, and
remove any package whose provenance or obligation remains unclear.

## Implementation lock and license review

- Comparison input: `origin/main@a39b1f5b345b6b29496c9643e5116aac14ee1bad`
  against implementation lock SHA-256
  `0c02ccbf1ef112a8fa6c36ed6732e459c644314a6c877fe3c58e81cc9241e00f`,
  reviewed 2026-08-31. The lock `packages:` inventory grows from 109 to 140 records:
  exactly 31 additions and zero removals.
- The additions are `@graphql-typed-document-node/core@3.2.0`,
  `graphql@16.14.2`, `railway@3.11.0`, `tsx@4.23.13`, `esbuild@0.28.2`, and the
  26 exact `@esbuild/*@0.28.2` optional packages for
  `aix-ppc64`, `android-arm`, `android-arm64`, `android-x64`, `darwin-arm64`,
  `darwin-x64`, `freebsd-arm64`, `freebsd-x64`, `linux-arm`, `linux-arm64`,
  `linux-ia32`, `linux-loong64`, `linux-mips64el`, `linux-ppc64`,
  `linux-riscv64`, `linux-s390x`, `linux-x64`, `netbsd-arm64`, `netbsd-x64`,
  `openbsd-arm64`, `openbsd-x64`, `openharmony-arm64`, `sunos-x64`,
  `win32-arm64`, `win32-ia32`, and `win32-x64`.
- Exact-version registry manifest and lock-integrity comparison found all 31 records to be
  MIT licensed with matching SRI and no missing/unknown license or version drift. The five
  non-platform SRIs are:
  - `@graphql-typed-document-node/core@3.2.0`:
    `sha512-mB9oAsNCm9aM3/SOv4YtBMqZbYj10R7dkq8byBqxGY/ncFwhf2oQzMV+LCRlWoDSEBJ3COiR1yeDvMtsoOsuFQ==`;
  - `esbuild@0.28.2`:
    `sha512-HKVLS8dvII+xoKW9kmqxbRKrnWEXfJJr/FZhhJmiqIB0e053QNYFqOBouTMO/k5sID4MvCiUCvv8b9M4h32wIA==`;
  - `graphql@16.14.2`:
    `sha512-Chq1s4CY7jmh8gO2qvLIJyfCDIN+EHLFW/9iShnp1z8FjBQMoodWP1kDC36VAMXXIvAjj4ARa7ntfAV2BrjsbA==`;
  - `railway@3.11.0`:
    `sha512-ehLFHCxV+gITWeBlIVaXulXaVRg4LCxqm0bq64iXSwYL1DESd0pUeLYMP/BMBhnZWeFFBYyJCREaq+Nka7Wgmw==`;
    and
  - `tsx@4.23.13`:
    `sha512-BL5MGkRln6aDYhb0xbQlEAGw743BaZYWdbWtdJOBriYJboKgUUYCadFp2/FpBBZquBC/ezNBn7wMMPx7FDZUDw==`.
- Installed contents contain MIT notices for the five ordinary packages. The optional
  platform packages share the esbuild repository and MIT manifest; a platform package can
  contain only its manifest, README, and binary, so any future distribution of that
  binary must also carry `esbuild@0.28.2/LICENSE.md`. This repository vendors or
  distributes none of those contents. No new NOTICE, UI attribution, source-publication,
  or reciprocal-license obligation applies to this source/lock-only change. Future
  distribution of dependency contents must preserve the applicable MIT copyright and
  permission notice.
- `pnpm licenses list --json --long` succeeds for the complete installed graph: 59 MIT,
  5 Apache-2.0, 1 Python-2.0, 2 BSD-3-Clause, 2 MPL-2.0, and 2 ISC package-name
  entries, with no `UNKNOWN`, `UNLICENSED`, `SEE LICENSE`, or incompatible category. The
  other 25 esbuild platform packages are OS/CPU-filtered locally and were covered by the
  exact registry-manifest/SRI review above.
- Manifest, workspace, lock, install-tree, and `pnpm why` checks find no
  `@railway/cli`; there is no `.bin/railway`. The SDK's `railway-iac-ts` compatibility
  shim is not invoked. There is no `allowBuilds` or `onlyBuiltDependencies` entry.
  Bootstrap deliberately uses `pnpm install --ignore-scripts`, so no dependency lifecycle
  script is approved; after a clean install the installed modules state reports exactly
  `pendingBuilds: ["esbuild@0.28.2"]`. The complete offline TypeScript/Vitest checks pass
  without running that install script. Because
  `pnpm ignored-builds` reports `Cannot identify as no node_modules found` after this
  all-script denial, that command is recorded verbatim rather than misrepresented as
  standalone clean evidence.
- Independent read-only reviewer `/root/railway_sdk_feasibility` performed the SDK, lock,
  registry-SRI, license, install-tree, and build-policy comparison and made no file change.
  Result: no unresolved or incompatible dependency obligation.

## Provider fact/source mapping

| Externally imposed fact used by this artifact | Primary source reviewed 2026-08-30 |
| --- | --- |
| Project-level TypeScript IaC is the current one-file surface; legacy `railway.json`/`railway.toml` is deprecated, unavailable to new services, and stops being read on 2026-12-01; plan is read-only/redacted by default and destructive apply is separately confirmed. | [Railway Infrastructure as Code](https://docs.railway.com/infrastructure-as-code) |
| Service/context/database/Bucket helpers, `preserve()`, health, placement, and environment rendering documented by the public DSL. | [Railway IaC reference](https://docs.railway.com/infrastructure-as-code/reference) |
| Locked `railway@3.11.0` additionally exposes Postgres `region`, `preDeploy`, nested deploy/restart fields including `drainingSeconds`, and generic `ref`; the package revision is the immutable implementation reference for exact structural tests. | [`sdk.ts` at `railway-ts-sdk@c1b6ea8`](https://github.com/railwayapp/railway-ts-sdk/blob/c1b6ea8dd3e815e57257b1f17637e59d31db73b5/src/iac/sdk.ts), [`schema.ts` at the same revision](https://github.com/railwayapp/railway-ts-sdk/blob/c1b6ea8dd3e815e57257b1f17637e59d31db73b5/src/iac/schema.ts) |
| Railway Buckets are private, environment-specific resources with structured S3-compatible outputs; Singapore compute identifier is `asia-southeast1-eqsg3a`, while Singapore Bucket physical region is the distinct code `sin` and its credential output reports `auto`. | [Storage Buckets](https://docs.railway.com/storage-buckets), [Deployment regions](https://docs.railway.com/deployments/regions), [Railway Bucket CLI](https://docs.railway.com/cli/bucket) |
| Automatic PR environments copy the selected base; staging must be selected explicitly. Sealed values are not copied to PR/duplicated environments and are not retrievable through the API/CLI. | [PR environments](https://docs.railway.com/guides/preview-deployments-with-pr-environments), [variables and sealing](https://docs.railway.com/variables), [staging/production isolation](https://docs.railway.com/guides/isolate-staging-production) |
| A pre-deploy command runs separately but inherits application variables, is not retried, and needs an explicit timeout; those properties alone do not satisfy Livecho's maintenance ADR. | [Railway pre-deploy command](https://docs.railway.com/deployments/pre-deploy-command) |
| PostgreSQL's two-key session advisory locks provide shared/exclusive modes; `pg_try_advisory_lock*` returns immediately and session end releases held locks. They provide mutual exclusion, not durable sequential-replay admission. A unique binding plus one conditional `UPDATE ... WHERE state = 'PENDING' RETURNING ...` can identify the sole committed claimant; ambiguous/serialization outcomes remain fail-closed rather than retried. Role password `VALID UNTIL` does not revoke an existing session, and role removal may require ownership reassignment/privilege cleanup. | [PostgreSQL advisory locks](https://www.postgresql.org/docs/current/functions-admin.html#FUNCTIONS-ADVISORY-LOCKS), [unique constraints](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-UNIQUE-CONSTRAINTS), [`UPDATE`](https://www.postgresql.org/docs/current/sql-update.html), [transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html), [`CREATE ROLE`](https://www.postgresql.org/docs/current/sql-createrole.html), [`REASSIGN OWNED`](https://www.postgresql.org/docs/current/sql-reassign-owned.html) |
| `railway status --json` describes the linked target/resources; `railway link` writes local link metadata, so live evidence must use a disposable copy. | [CLI status](https://docs.railway.com/cli/status), [CLI link](https://docs.railway.com/cli/link) |
| CLI variable writes support `--skip-deploys`, and Public API variable upsert supports `skipDeploys: true`. The artifact uses those contracts only for the ordinary non-secret maintenance flag; neither source establishes deletion without deployment or a sealed-secret lifecycle. | [CLI variables](https://docs.railway.com/cli/variable), [Manage variables with the Public API](https://docs.railway.com/integrations/api/manage-variables) |
| Railway documents staged variable changes, per-variable dashboard creation/editing and the explicit `Seal` action. Sealed values cannot be retrieved through CLI/API, Raw Editor cannot update them, and service variables/references are available during builds as well as runtime. Each first real maintenance URI therefore requires a prebuilt immutable image and controlled canary lifecycle; any credential-bearing backend likewise requires an exact-commit image produced by a protected credential-free build rather than a Railway source build. | [Railway variables and sealing](https://docs.railway.com/variables) |
| CLI deployment management lists immutable deployment IDs but has no exact-ID stop subcommand; `railway down` targets the mutable latest successful deployment. The Public API supplies exact-ID stop/remove. | [CLI deployments](https://docs.railway.com/cli/deployment), [`railway down`](https://docs.railway.com/cli/down), [Manage deployments with the Public API](https://docs.railway.com/integrations/api/manage-deployments) |
| Service creation or a source change starts a deployment cycle; applying staged changes redeploys affected services; an image source skips the provider build but Railway still starts the service; and Railway may initiate additional deployments. The cleanup design therefore assumes no singleton cardinality: it owns the complete nonempty recreation-ID delta, requires the fixed zero-credential dispatcher absence result, and stop/cancel/reconciles every observed ID without a second trigger. | [Railway deployments reference](https://docs.railway.com/deployments/reference), [Railway staged changes](https://docs.railway.com/deployments/staged-changes), [Manage deployments with the Public API](https://docs.railway.com/integrations/api/manage-deployments) |
| The pinned CLI's immutable `ServiceDelete` mutation requires both `environmentId` and `serviceId`; its command resolves a service instance inside the selected environment and warns that all deployments for that instance are deleted. The prose API page omits this input detail, so a live per-environment canary and sibling-environment non-interference check remain mandatory. | [`ServiceDelete.graphql` at `railwayapp/cli@6f1b464`](https://github.com/railwayapp/cli/blob/6f1b464eb96793700a5d02d2e55ecf69037ccc35/src/gql/mutations/strings/ServiceDelete.graphql), [`service.rs` target resolution/confirmation](https://github.com/railwayapp/cli/blob/6f1b464eb96793700a5d02d2e55ecf69037ccc35/src/commands/service.rs#L620-L700), [`service.rs` dual-bound call](https://github.com/railwayapp/cli/blob/6f1b464eb96793700a5d02d2e55ecf69037ccc35/src/commands/service.rs#L709-L721), [Manage services with the Public API](https://docs.railway.com/integrations/api/manage-services) |
| Project Tokens are bound to one environment and limited to deployment-related actions. Project Owners have full administration, while Editors cannot delete services; the runbook therefore keeps a fresh Project Token in the controller and reserves interactive 2FA deletion for a separate Owner. | [Deploying with the CLI](https://docs.railway.com/cli/deploying#using-project-tokens), [Public API token types](https://docs.railway.com/integrations/api#project-token), [Project member permissions](https://docs.railway.com/projects/project-members) |
| Restart policy `Never` prevents automatic restart after a service stops; it does not impose a wall-clock execution timeout. Railway replacement teardown sends `SIGTERM` and honors configured draining time before `SIGKILL`, so maintenance fixes a 15-second drain around its 10-second handler. The exact-ID stop API does not document the same grace; the independent controller therefore has a two-minute startup/binding limit, arms its hard-stop timestamp 46 minutes after observing the post-arm marker, and pairs any hard stop with database revocation. | [Railway restart policy](https://docs.railway.com/deployments/restart-policy), [Railway deployment teardown](https://docs.railway.com/deployments/deployment-teardown), [Manage deployments with the Public API](https://docs.railway.com/integrations/api/manage-deployments) |
| A custom Railway start command overrides a Dockerfile/image `ENTRYPOINT` in exec form. The Issue #4 maintenance guard may remain for the repository-only skeleton, but the accepted image-owning Issue must remove that override from IaC and provider active/staged state so the fixed OCI `ENTRYPOINT` with empty `CMD` is authoritative before the canary. | [Railway start command](https://docs.railway.com/deployments/start-command) |
| Health checks gate deployment traffic cutover but are not continuous monitoring. | [Railway health checks](https://docs.railway.com/deployments/healthchecks) |
| Railway rollback restores an earlier deployment image and custom variables; removed deployments remain rollback/redeploy candidates under the documented retention behavior. Deployment `Remove` alone therefore cannot prove a temporary credential's carrier history is unreachable, and Railway rollback still does not roll back application-managed database schema. | [Railway deployment actions](https://docs.railway.com/deployments/deployment-actions), [Railway image retention policy](https://docs.railway.com/pricing/plans#image-retention-policy) |

## Automated verification

| Command | Result | Date/commit |
| --- | --- | --- |
| `uv run python tools/check_change_artifacts.py` | Pass — `change artifacts: ok` | 2026-08-30 / `09b9b220798715e64f837d3917bb2b285ec92ae5` |
| `make artifacts` | Pass — artifact checker reported `change artifacts: ok` | 2026-08-30 / `09b9b220798715e64f837d3917bb2b285ec92ae5` |
| `make verify` | Pass — ruff check/format; mypy across 22 source files; 107 pytest tests; 128 Vitest tests; artifact and protocol-generation checks; TypeScript build | 2026-08-30 / `09b9b220798715e64f837d3917bb2b285ec92ae5` |
| `git diff --check` and `git diff --cached --check` | Pass — no whitespace errors before commit | 2026-08-30 / `09b9b220798715e64f837d3917bb2b285ec92ae5` |
| `git diff --name-only origin/main...HEAD` | Pass — exactly the four files under `docs/changes/4-railway-deployment-skeleton/` | 2026-08-30 / `09b9b220798715e64f837d3917bb2b285ec92ae5` |

The commit above is the reviewed substantive artifact snapshot. The following evidence-only
commit adds this table and the PR link; the same deterministic checks are rerun on that
final pull-request head, and required GitHub checks remain authoritative for merge.

## Implementation automated verification

The initial implementation snapshot is
`312524c` (`feat: add fail-closed Railway deployment skeleton`), based on the truthful
collaboration-correction commit `c43e75d` and the required first exposure/assignment commit
`705a48b`. Isolated review found that snapshot's runtime behavior correct but blocked merge
on circular test expectations and an inaccurate `pendingBuilds` evidence claim. Corrective
substantive snapshot `46f886e` (`test: assert Railway safety constants independently`)
changes only `.railway/railway.test.ts`; this evidence-only follow-up records both findings,
their remediation, and the corrected clean review without rewriting history.

| Exact command | Result | Date/commit |
| --- | --- | --- |
| `node --experimental-strip-types --input-type=module -e 'import program from "./railway.ts"; import { createRailwayContext, project } from "railway/iac"; const rendered = await program(createRailwayContext({ environmentName: "production" }), project); console.log(JSON.stringify(rendered, null, 2));'` from `.railway/` | Pass — native Node 22 evaluation produced one `livecho` project with the exact five-resource production definition, 20 backend variables, eight maintenance literals, structured references, preserved slots, and no code-service source | 2026-08-31 / `312524c` |
| `make bootstrap` | Pass — uv frozen sync and pnpm frozen install with all dependency lifecycle scripts denied by `--ignore-scripts`; no allowlist was added | 2026-08-31 / `312524c` |
| `make railway-check` | Pass — lint/typecheck/build no-emit checks and 63 focused Vitest cases, including six environment contexts, exact graph shape, symlink/index/tree guards, three non-zero start guards, and migration file/directory/symlink/FIFO/socket cases | 2026-08-31 / `312524c` |
| `pnpm --filter @livecho/railway-config lint`, `typecheck`, `test`, and `build` | Pass individually — test result 1 file / 63 tests | 2026-08-31 / `312524c` |
| `pnpm licenses list --json --long` | Pass — complete installed graph categorized with no unknown, unlicensed, `SEE LICENSE`, or incompatible result; exact lock-only optional-platform coverage is recorded above | 2026-08-31 / `312524c` |
| `pnpm ignored-builds` | Exit 0 with literal result `Cannot identify as no node_modules found`; not treated as standalone clean proof. After a clean install, `node_modules/.modules.yaml` reports exactly one denied pending build, `esbuild@0.28.2`; the full offline verification passes without it, and manifest/lock/install-tree checks independently exclude Railway CLI | 2026-08-31 / `312524c` |
| `pnpm why @railway/cli --recursive` and `find node_modules .railway/node_modules -path '*/.bin/railway' -print` | Pass — no dependency result and no executable path | 2026-08-31 / `312524c` |
| `uv run python tools/check_change_artifacts.py` and `make artifacts` | Pass — both reported `change artifacts: ok` | 2026-08-31 / `312524c` |
| `make verify` | Pass — ruff check/format, mypy (22 files), 107 pytest tests, 128 protocol Vitest tests, 63 Railway Vitest tests, artifact/protocol generation checks, and both TypeScript workspace builds | 2026-08-31 / `312524c` |
| `git diff --check` | Pass — no whitespace error | 2026-08-31 / `312524c` |
| `rg --files -g 'railway.json' -g 'railway.toml' -g '.railway/railway.py' -g '.railway/railway.go' .` | Expected no output — no legacy or second-language authoring file | 2026-08-31 / `312524c` |
| `rg -n 'show-values\|include-variables\|config apply\|railway up\|environment delete' Makefile package.json .github .railway` | Expected no output — no executable provider mutation/value-dump automation | 2026-08-31 / `312524c` |
| `rg -n -I '(BEGIN (RSA \|EC \|OPENSSH )?PRIVATE KEY\|RAILWAY_(API_)?TOKEN=\|RESEND_API_KEY=.+\|BILI[^=]*(COOKIE\|TOKEN)=.+\|postgres(ql)?://[^[:space:]]+:[^[:space:]@]+@)' --glob '!docs/changes/4-railway-deployment-skeleton/*' .` | Expected no output — no value-bearing private key, token, Bilibili credential, email key, or embedded database credential | 2026-08-31 / `312524c` |
| `find . -path './.git' -prune -o -path './node_modules' -prune -o -path './.venv' -prune -o -type f \( -iname '*.wav' -o -iname '*.pcm' -o -iname '*.mp3' -o -iname '*.flac' -o -iname '*.aac' -o -iname '*.ogg' \) -print` | Expected no output — no audio artifact | 2026-08-31 / `312524c` |
| cold copy: `make -C /tmp/livecho-issue4-cold.AyqMjo bootstrap`; then `git init --quiet`, `git add -- .railway`, and `make railway-check` in that copy | Pass — 72 Node packages installed from an empty local `node_modules` with scripts denied, then all 63 focused tests passed. The first pre-`git init` test attempt failed at the intended Git source guard (`fatal: not a git repository`), identifying a diagnostic-copy setup omission rather than bypassing the guard; the corrected run passed. The disposable copy was moved to Trash after verification | 2026-08-31 / `312524c` |
| `pnpm --filter @livecho/railway-config lint`, `typecheck`, `test`, and `build` after replacing module-derived expectations with independent normative literals | Pass individually — 1 file / 63 tests; compute region, Bucket region, build command, eight default-off/fixture values, six persistent secret slots, rendered graphs, exports, and `.env.example` now compare against test-owned literals | 2026-08-31 / `46f886e` |
| `make verify` | Pass — ruff check/format, mypy (22 files), 107 pytest tests, 128 protocol Vitest tests, 63 Railway Vitest tests, artifact/protocol generation checks, and both TypeScript workspace builds | 2026-08-31 / `46f886e` plus this evidence-only working tree |
| isolated mutations followed each time by `pnpm --filter @livecho/railway-config test` | Expected failure for all six independent mutations: compute region `us-west2`, Bucket region `auto`, build command `railway up`, global serving `false` to `true`, preserve-slot rename, and `.env.example` maintenance `false` to `true`. Each run exited 1; after restoration `git diff --quiet` and 63/63 passed | 2026-08-31 / isolated `git archive 46f886e` copy |

## Manual or hardware evidence

- Railway documentation/API review: the table above maps each externally imposed fact to
  the primary vendor source or immutable SDK revision reviewed on 2026-08-30.
- Live Railway plan/state evidence: Not performed. Issue #4 creates no resource and has no
  project token or provider-state prerequisite. A later authorized rollout must record a
  redacted staging plan and the manual checks named in `plan.md` before any apply.
- Maintenance/migration runtime evidence: Not performed. The advisory-lock protocol,
  durable one-use admission/recovery-boundary protocol, immutable prebuilt image, per-
  environment canary deletion/recreation gate, operation-specific role, and entrypoint/provider supervisors are future contracts whose first
  schema or operation Issue must implement and verify before any real operation.
- Hardware evidence: Not required. This change has no MLX or CUDA behavior.

## Review findings

- Initial scope review confirmed Issue #4 is the next roadmap item, depends only on
  closed Issues #1 and #2, and had no existing artifact, branch, or pull request.
- Provider review found that legacy `railway.json` / `railway.toml` Config as Code is
  deprecated, unavailable to new services, and scheduled for a 2026-12-01 cutoff. The
  artifact therefore requires one current `.railway/railway.ts` project declaration.
- Provider review found different Singapore identifiers for compute
  (`asia-southeast1-eqsg3a`) and Bucket storage (`sin`), no environment-creation helper in
  the documented TypeScript DSL, and no standalone offline `validate` command. The plan
  separates deterministic DSL tests from later authenticated live-plan evidence.
- CLI review found that `railway link` writes project/environment identifiers under the
  same `.railway` directory used by the IaC workspace. The revised artifact requires an
  exact source-file allowlist and confines every later link/status/plan to a disposable,
  access-restricted copy that is destroyed after redacted evidence extraction.
- Published pinned-package source and declaration inspection confirmed that the SDK
  exposes Postgres `region`, service
  `preDeploy`, nested restart policy, and generic resource references even where the prose
  reference does not enumerate every field. The revised artifact requires exact structural
  tests, writes the Postgres Singapore region into desired state, and retains a live-plan
  plus provider-metadata gate.
- Provider review found that `preserve()` does not prove sealing and automatic PR
  environments copy their configured base rather than automatically execute the IaC
  classifier. The revised artifact makes staging's false/fixture state, sealed-value
  exclusion, and separate provider proof of the PR base authoritative; synthetic `pr-*`
  tests are labelled render-policy coverage only.
- Architecture review initially found a permanent maintenance `DATABASE_URL` and manual
  stop checklist inconsistent with `DEC-MAINT-001`. The revised specification removes all
  baseline maintenance credentials and requires a shared/exclusive Postgres advisory-lock
  fence plus a sealed operation-specific role with a maximum 60-minute validity, a
  45-minute internal timeout, 15-second replacement drain, two-minute startup/binding gate,
  46-minute post-observed-start provider fallback,
  a unique atomic one-use admission that remains consumed after crash and cannot be rewound
  by its own restore/recovery operation, `NOLOGIN`, residual-session termination, and mandatory
  ownership cleanup/revoke/drop/removal on every outcome. Persistent migration objects
  remain owned by a stable non-login schema owner rather than the temporary login role.
- Provider lifecycle review found that service variables reach both build and runtime,
  Railway may create additional carrier deployments, deployment history can restore old
  custom variables, and deployment `Remove` is not
  carrier erasure. The revised contract requires exact-commit prebuilt images for both a
  credential-bearing backend and maintenance; a one-use database role as the revocation
  authority; a durable per-operation admission so later carriers cannot sequentially replay
  work after the advisory lock is released; and, before each environment's first real URI, a non-credential canary that
  proves the pinned dual-bound environment/service instance deletion, sibling non-
  interference, recreation-only plan, set-bound provider-triggered deployments, and fixed-
  dispatcher absence proof. It makes no provider-backup erasure claim.
- Policy review found missing author-exposure, dependency provenance/license, and isolated
  review steps. This evidence records the requirements exposure and direct-package
  pre-audit; the plan now blocks implementation until a fresh implementer record and full
  lockfile license inventory predate code, and requires a non-patching isolated final
  reviewer.
- Three isolated read-only reviews resolved every material artifact finding: Railway build-
  time credential exposure; set-based ownership of provider-created deployment IDs; custom
  start-command precedence; replacement-drain and two-phase watchdog timing; restored-role
  cleanup; sequential operation replay; and low-entropy target-digest exposure. The bounded
  runtime-gate reviewer and both whole-artifact reviewers returned `CLEAN`. The final-head
  whole-artifact audit covered Issue #4's six acceptance criteria and locked these content
  blobs before this review/verification metadata append: intent
  `c54d68e9996e091e3445f644d14ac17b7a975c84`, spec
  `a028b464c0b8e91a4fa07920ebd685dae2fe4637`, plan
  `4a562892ae9f64b4d7bbda89908d26cdd23dfabf`, and evidence
  `0d70de906ab9c8a0170363748956ad6747e173df`. The reviewers made no file changes.
- The named isolated implementation reviewer first classified `312524c` as blocked despite
  finding no IaC, guard, runbook, secret-boundary, or provider-action defect. Two Medium
  acceptance blockers were recorded: graph and `.env.example` expectations were partly
  derived from the module constants under test, and committed evidence incorrectly claimed
  `pendingBuilds: []`. The first flaw could allow a wrong region, enabled safety flag, or
  changed preserve slot to move together with its expectation; the second contradicted a
  reproducible clean install.
- Commit `46f886e` closes the test blocker with independently hard-coded expected compute and
  Bucket regions, build command, eight safety values, and six preserve slots. The reviewer
  proved the correction with the six isolated mutations recorded above, then restored the
  archive to a clean tree and reran 63/63 plus `make verify`. The corrected dependency fact
  is that `--ignore-scripts` denies all lifecycle scripts and records exactly one pending
  build, `esbuild@0.28.2`; offline verification does not require that postinstall, and
  `pnpm ignored-builds` is not treated as standalone proof.
- Isolated final substantive verdict for `46f886e4d9e1a31bc2bf0f5a7ad271a70e4ad3ff`:
  `CLEAN`, with no remaining security, specification, or test blocker. Baseline tree is
  `164f04aeee81b1423f23addca03af03e97ac0086`; target tree is
  `e97572546fbfbb8204a7316a707d337a9a998dc6`; baseline-to-target binary diff SHA-256 is
  `a3fea8f7a4fa1e560819e5d6a658e55193c4f337656d081e829db2a220333e89`. The updated test
  blob is `c4f4e6f2300c0c1845dd6174f29c0b0670351c51`; IaC blob
  `535f9b84162d945f00f67411fabe0743e92d0789`; deployment runbook blob
  `157347491c17d083268861d4e1ba821dfb129350`; secrets runbook blob
  `dd8461185de1f1f13397877f6b3c492d841489ef`; lock blob
  `0d5b94a282439d5be0b07120f36779c93f163992`. Persistent and preview render SHA-256 are
  respectively `a3fbb3f5d6504f3a35d7fdba0def3690ba805cd2662c889174d6f19be71b89cd` and
  `68c8c8f4786ebb89e5405371c974ca5d4f06505fd2100911e9b927bd07161ce9`.
- Process-remediation verdict is `PASS`: neither runbook existed before `c43e75d`; both first
  appear at `312524c`; `46f886e` is solely an authorized root-author test correction; and
  the isolated reviewer made no repository change. The merge head remains gated on a
  read-only check that its final delta from `46f886e` is evidence-only, plus required CI.

## Deviations

- No accepted behavior, topology, secret, provider, protocol, schema, or safety requirement
  is intentionally changed.
- Process deviation: `/root/issue4_repo_audit` was reassigned from read-only audit to draft
  two operations documents without its individual author identity being committed first.
  Commit `c43e75d` preserves the truthful exposure and timing record. The uncommitted
  drafts were removed; after that commit, the already authorized `/root` implementation
  author independently formed the final documents from the accepted Issue #4 artifacts.
  `/root`'s exposure to the discarded internal drafts is disclosed. The named isolated
  reviewer remained non-patching and confirmed the remediation as `PASS` on the corrective
  substantive history.
- Implementation detail: pinned `railway@3.11.0` brings `tsx -> esbuild`, whose lifecycle
  script caused pnpm 11.21.0 to propose a forbidden `allowBuilds` placeholder. The
  placeholder was removed and root bootstrap now uses `--ignore-scripts`, denying all
  dependency lifecycle scripts. Cold and ordinary offline checks pass without them. This
  strengthens the accepted no-build-allowlist boundary and does not add a provider tool or
  executable-download path.

## Release and rollback evidence

Not deployed and not linked to Railway. The implementation produces repository-only
desired state, fail-closed command guards, tests, and future-manual runbooks. Before any
later provider apply, rollback is a normal revert of the Issue #4 implementation commits;
the accepted intent remains visible, and a semantic amendment requires a reviewed artifact
update. After a future authorized apply, rollback must follow the runbook's redacted-plan,
exact-image, non-destructive-schema, and provider-state gates rather than assuming IaC
omission is safe deletion.
