# Evidence: Architecture, trust, data, and platform boundaries

## Artifact approval

- Artifact PR: #21
- Documentation implementation PR: Pending
- Approved by/date: @Shuang-su / 2026-08-24 authorized this agent to prepare, review,
  and merge the artifact after required checks and review gates pass. Final ADR and
  residual-risk approval remains pending the separate implementation PR.

## Artifact-phase automated verification

| Command | Result | Date/commit |
| --- | --- | --- |
| `make bootstrap` | Passed; frozen uv and pnpm dependencies were already current. | 2026-08-24 / artifact worktree |
| `make verify` | Passed; Ruff, workspace lint, mypy, typecheck, 40 pytest tests, pnpm tests, artifact gate, and build all succeeded. | 2026-08-24 / final staged artifact tree |
| `make artifacts` | Passed; `change artifacts: ok`. | 2026-08-24 / final staged artifact tree |
| `git diff --check && git diff --cached --check` | Passed with no whitespace errors. | 2026-08-24 / final staged artifact tree |

## Documentation implementation verification

| Command | Result | Date/commit |
| --- | --- | --- |
| `make bootstrap` | Passed; uv checked 10 packages and pnpm reported the frozen workspace already up to date. | 2026-08-24 / final implementation worktree |
| `make verify` | Passed; Ruff, workspace lint, mypy, typecheck, 40 pytest tests, pnpm tests, artifact gate, and build all succeeded. | 2026-08-24 / final implementation worktree |
| `git diff --check && git diff --cached --check` | Passed with no whitespace errors. | 2026-08-24 / final staged implementation tree |
| Mermaid CLI render command below | Passed with `@mermaid-js/mermaid-cli` 11.12.0 and system Google Chrome; the ADR Markdown produced a rendered SVG. | 2026-08-24 / final implementation worktree |
| GitHub Markdown API table-render comparison | Passed; all 34 Markdown table delimiter rows rendered as 34 HTML tables across the six records. | 2026-08-24 / final implementation worktree |
| Local Markdown link existence check | Passed; every relative link in `README.md`, `SECURITY.md`, and the six records resolved to an existing repository path. | 2026-08-24 / final implementation worktree |

The isolated Mermaid render used no repository dependency or output path:

```sh
livecho_mmdc_tmp=$(mktemp -d)
cd "$livecho_mmdc_tmp"
npm init -y >/dev/null
PUPPETEER_SKIP_DOWNLOAD=1 npm install --cache "$livecho_mmdc_tmp/npm-cache" \
  --no-save @mermaid-js/mermaid-cli@11.12.0 >/dev/null
PUPPETEER_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  ./node_modules/.bin/mmdc -q \
  -i /Users/szmg/Documents/Livecho/docs/architecture/adr/0001-alpha-modular-monolith.md \
  -o "$livecho_mmdc_tmp/rendered.md"
```

## Manual or hardware evidence

No hardware or production access was used. The artifact phase changed only the four
regular, non-empty Issue #2 lifecycle records. The documentation implementation phase
contains only the six required records, `README.md`, `SECURITY.md`, and this evidence
update; it adds no runtime or deployment resource.

- **Diagram trace: Passed.** Mermaid CLI rendered every required zone plus the Issue #4
  maintenance, safety recovery, and managed-export boundaries. The registries trace 20
  conditionally allowed flows and 18 explicit no-flows, including transient playback
  bytes and audio exclusions for Postgres, Bucket, application backups, the safety copy,
  and managed export.
- **Threat and role trace: Passed as a design review.** Every required threat has asset,
  actor, entry point, precondition, prevention, detection, response, later evidence
  owners/dependencies, residual severity, and decision. The anonymous/invited/
  contributor/operator/admin/owner matrix matches the accepted deny-by-default model.
  All 13 High residuals are individually `NOT ACCEPTED`; no Critical residual is listed.
  Their production capabilities remain off or prohibited.
- **Lifecycle trace: Passed as a design review.** Every accepted data class and exact
  audio ceiling is present, there is no audio retry queue, and the three truthful
  deletion states, immutable late-SLA result, provider-window boundary, tombstone, and
  forced-off restore order are explicit. This is not runtime enforcement evidence.
- **Tabletop 1 — active-room global disable: Passed on paper.** The runbook immediately
  latches off, denies starts/reconnects, stops the platform session, revokes the lease,
  rejects late output, clears conforming audio/locator RAM, hides publication, and keeps
  the system off after a journal/recovery-copy write failure.
- **Tabletop 2 — partial and late deletion: Passed on paper.** The target becomes hidden
  before purge, a failed raw-object deletion cannot report active completion, retry is
  idempotent, a late success records `sla_breached=true`, and the final state waits for
  every enumerated export/provider window and a post-window restore check.
- **Tabletop 3 — stale restore: Passed on paper.** The environment starts isolated and
  forced off, replays current tombstones before reconciling the newer safety generation
  and denylist, rejects the backed-up enabled value, and admits no traffic before every
  gate succeeds.
- **Tabletop 4 — malicious authenticated worker: Passed on paper.** Authentication is
  never treated as trusted execution or proof of RAM erasure. Missing third-party rights
  or an individual `RISK-WORKER-AUDIO-RETENTION` decision keeps real PCM off and synthetic
  frames as the default.
- **Platform/source review: Passed for documenting the current blocker, not for enabling
  production.** Six current official Bilibili entries were reachable and the record
  distinguishes stable entry, aggregator/resolved content, displayed version, and
  review date. The exact acquisition channel, platform permission, room-rights evidence,
  worker-disclosure basis, retention grant, output grant, and channel/rightsholder
  contacts remain missing; `BILI-DEC-001` therefore stays production off.
- **Upstream provenance review: Passed.** Independent review matched the three pinned
  LAPLACE commits, path-level tree/license blobs and SHA-256 values. Chatterbox is
  AGPL-marked; event-bridge is path-level mixed/unclear; the two MIT-marked candidates
  remain reference-only with no selected source blob or notice mapping. The author
  exposure/exclusion record includes generated README factual summaries; no upstream
  source, test, fixture, schema, configuration, comment, documentation text, or asset was
  copied into Livecho.

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

The implementation review then found and resolved:

- malformed GFM separator rows that prevented two threat tables from rendering, and a
  missing ADR link in `SECURITY.md`;
- operator deletion overreach and geographic/DRM wording weaker than the accepted
  fail-closed policy;
- a missing transient-playback-bytes label, incomplete audio-to-persistent-boundary
  no-flows, and an inaccurate statement about provider backup mediation in the diagram;
- inconsistent later-Issue ownership sets for shared stable control IDs; and
- stale Bilibili privacy/user-agreement routing, an incorrect browser/event Issue owner,
  and an incomplete account of generated upstream-summary exposure.

After those revisions, independent architecture/security and data/platform/license
re-reviews reported no remaining P1/P2. GitHub GFM rendered all record tables, Mermaid
rendering passed, local links resolved, official source URLs were reachable, and the
upstream commit/tree/blob/digest checks matched.

## Deviations

None. Missing external permission, provider configuration, runtime controls, production
evidence, or owner risk acceptance is represented as a blocking gate, not treated as a
deviation.

## Release and rollback evidence

Not deployed. Production ingest, production persistence/export, and community-worker
real PCM remain disabled. Repository-owner approval of the final ADR and threat-model
record is pending; no Critical/High residual risk is accepted by this evidence.
