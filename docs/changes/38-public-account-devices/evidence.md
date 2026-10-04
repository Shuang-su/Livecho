# Evidence: Public accounts and self-service device boundaries

## Artifact approval

- Owning Issue: [#38](https://github.com/Shuang-su/Livecho/issues/38).
- Status: **Draft / proposed; repository-owner decision pending**.
- Artifact PR: Pending independent review and creation.
- Approval date: None. No existing invitation, history, role, ingest or runtime rule is
  superseded by creating this proposal.
- Base: `93d8b0a4b3e147ce0b7df903f118060117d56f0a`, confirmed against remote main on
  2026-10-05 Asia/Shanghai.

## Author exposure and assignment before artifact drafting

- Author: `/root/asr_implementation`, independent requirements/ADR author for Issue #38
  account and device governance only, assigned 2026-10-05 Asia/Shanghai after an explicit
  source self-check and coordinator approval. The Issue body follows only the user's
  product direction and existing Livecho constraints. This record precedes drafting the
  spec, plan and supplementary ADR.
- Reviewer: `/root/audio_code_readiness`, separate from this author. `/root` may conduct
  read-only technical review and does not author this proposal.
- Permitted inputs read: AGENTS.md; `docs/policy/independent-implementation.md`; the
  locally accepted Issue #2 architecture, role, threat, identity-lifecycle and recovery
  requirements; original bodies of Issues #12/#13/#17 (no comments); and the user's
  2026-10-05 product direction. No new external sources have been fetched for this task.
- Prior exposure is not zero: the local policy exposes upstream repository/license and
  prior-author exposure metadata. Earlier Issue #5 work consulted official Qwen/MLX
  papers, model/configuration/API documentation and examples. A 2026-10-03 search exposed
  download implementation/example snippets outside its intended documentation scope;
  the event and URLs are recorded in Issue #5 evidence commit `e64f90d`. This author
  remains excluded from the corresponding HTTPS/download/transfer modules. None of
  that expression is supplied as an Issue #38 requirement or reproduced here.
- The author has not viewed reference-site identity/invitation/device/contribution UI
  text, screenshots, layouts or research summaries in the available task context, and
  has not accessed Issue #31 or the coordinator's reference research. No new subtitle/
  ASR behavior, download module, third-party source or reference-site expression is in
  this assignment. A future corresponding exposure stops affected authorship.
- Worktree: independent managed checkout `livecho-public-account-architecture/Livecho`,
  branch `codex/issue-38-public-account-device-artifacts`. The main and ASR worktrees are
  preserved.

## Local requirement register

| Input | Role in this proposal |
| --- | --- |
| User direction, 2026-10-05, recorded in [Issue #38](https://github.com/Shuang-su/Livecho/issues/38) | Public unified site accounts and own-device self-service, with platform acquisition authorization separate. Drafting only; no decision or rollout approval inferred. |
| [Issue #12 original body](https://github.com/Shuang-su/Livecho/issues/12) | Existing invited email, magic-link/session, roles, non-enumeration, idempotency and secret constraints. No comments read. |
| [Issue #13 original body](https://github.com/Shuang-su/Livecho/issues/13) | Existing administrator enrollment, key proof, revocation, manifests and non-financial own aggregates. No comments read. |
| [Issue #17 original body](https://github.com/Shuang-su/Livecho/issues/17) | Existing history, own-statistics, privileged controls, raw isolation and accessibility boundaries. No comments read. |
| [Issue #2 specification](../2-architecture-risk-boundaries/spec.md), [ADR 0001](../../architecture/adr/0001-alpha-modular-monolith.md) | Existing authority, role, no-secret, worker/ingest and recovery constraints; invitation clauses are mapped rather than rewritten. |
| [Threat model](../../security/alpha-threat-model.md), [data lifecycle](../../security/data-lifecycle-and-deletion.md) | Default-deny access, identity/devices, scoped revocation/deletion, audit and restore obligations. |
| [Independent-implementation policy](../../policy/independent-implementation.md) | Source restrictions and author/reviewer separation. |

The quota numbers, 10-minute enrollment lifetime, recent-auth bound and recommended
independent-history grant are explicitly local proposed choices. They are not extracted
from a reference product or asserted to be vendor limits, measured capacity or legal rules.

## Automated verification

Pending the completed documentation snapshot. This batch changes documents only;
verification will use artifact lifecycle, whitespace/path/link checks and independent
review. No runtime, hardware, account, email, device or platform test result is claimed.

## Manual evidence and review findings

Pending. Source isolation and scope were checked before assignment; this is not a
license/legal clearance or a reference-expression similarity review.

## Deviations

The supplementary ADR draft stays inside this Issue's artifact directory so the existing
artifact-only lifecycle check remains applicable. Its eventual canonical ADR publication
and precise authoritative-document updates are a later owner-approved step.

## Release and rollback evidence

Not deployed. No API, schema, protocol, credential, role grant or operating mode changes.
