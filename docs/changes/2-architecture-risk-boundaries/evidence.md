# Evidence: Architecture, trust, data, and platform boundaries

## Artifact approval

- Artifact PR: #21
- Approved by/date: @Shuang-su / 2026-08-24 authorized this agent to prepare, review,
  and merge the artifact after required checks and review gates pass. Final ADR and
  residual-risk approval remains pending the separate implementation PR.

## Automated verification

| Command | Result | Date/commit |
| --- | --- | --- |
| `make bootstrap` | Passed; frozen uv and pnpm dependencies were already current. | 2026-08-24 / artifact worktree |
| `make verify` | Passed; Ruff, workspace lint, mypy, typecheck, 40 pytest tests, pnpm tests, artifact gate, and build all succeeded. | 2026-08-24 / final staged artifact tree |
| `make artifacts` | Passed; `change artifacts: ok`. | 2026-08-24 / final staged artifact tree |
| `git diff --check && git diff --cached --check` | Passed with no whitespace errors. | 2026-08-24 / final staged artifact tree |

## Manual or hardware evidence

No hardware or production access is required. `git diff --cached --name-only` listed
only the four regular, non-empty Issue #2 lifecycle records. Diagram tracing,
policy/upstream source capture, threat and lifecycle review, deletion/restore tabletop
evidence, and owner risk acceptance belong to the separate documentation implementation
pull request.

## Review findings

Three independent read-only reviews covered repository lifecycle/gates, architecture and
security boundaries, and data/platform/license policy. Initial findings identified:

- anonymous-history and role mismatches, missing safety-state rollback/restore semantics,
  and incomplete maintenance, admin-export, Bilibili-event, and playback-locator flows;
- the impossibility of proving PCM erasure on a malicious community host, requiring a
  synthetic-only default, explicit third-party rights gate, and named High residual;
- restricted-by-default data, source-specific retention rules, distinct deletion states,
  managed export/auth-token lifetimes, and non-physical-erasure wording; and
- path-level mixed-license analysis, author exposure exclusion, independent requirements,
  and mandatory MIT notice preservation.

The artifacts were revised for every finding. Final staged-tree re-reviews reported no
remaining P1/P2; the lifecycle reviewer also confirmed the exact 30-second media window,
960,000-byte canonical PCM limit, fixed process cap, single active Alpha lease, and no
audio retry queue are mutually consistent and testable.

A separate cold final review then found two P2s: the documentation-only acceptance text
claimed runtime audio enforcement, and deletion completion had no truthful state after a
late successful retry. The specification now assigns executable audio enforcement to
Issues #3/#8/#14/#15, and separates active-purge completion from its 24-hour SLA while
retaining an immutable breach result. Both fixes preserve the fail-closed production
gates without claiming implementation in this artifact or its documentation follow-up.

## Deviations

None.

## Release and rollback evidence

Not deployed. Production ingest remains globally disabled by specification.
