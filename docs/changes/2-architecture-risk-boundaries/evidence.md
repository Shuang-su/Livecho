# Evidence: Architecture, trust, data, and platform boundaries

## Artifact approval

- Artifact PR: #21
- Documentation implementation PR: #22
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
| `make bootstrap` | Passed; uv checked 10 packages and pnpm reported the frozen workspace already up to date. | 2026-08-24 / post-third-remote-review worktree |
| `make verify` | Passed; Ruff, workspace lint, mypy, typecheck, 40 pytest tests, pnpm tests, artifact gate, and build all succeeded. | 2026-08-24 / post-third-remote-review worktree |
| `git diff --check && git diff --cached --check` | Passed with no whitespace errors. | 2026-08-24 / final staged post-third-review tree |
| Mermaid CLI render command below | Passed with `@mermaid-js/mermaid-cli` 11.12.0 and system Google Chrome; the ADR Markdown produced a rendered SVG. | 2026-08-24 / post-third-remote-review worktree |
| GitHub Markdown API table-render comparison | Passed; all 35 Markdown table delimiter rows rendered as 35 HTML tables across the six records. | 2026-08-24 / post-third-remote-review worktree |
| Local Markdown link existence check | Passed; all 18 relative links in `README.md`, `SECURITY.md`, and the six records resolved to existing repository paths. | 2026-08-24 / post-third-remote-review worktree |

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
  bytes and audio exclusions for Postgres, Bucket, application backups, the safety/
  deletion/revocation/auth-invalidation recovery copy, and managed export.
- **Threat and role trace: Passed as a design review.** Every required threat has asset,
  actor, entry point, precondition, prevention, detection, response, later evidence
  owners/dependencies, residual severity, and decision. The anonymous/invited/
  contributor/operator/admin/owner matrix matches the accepted deny-by-default model.
  All 13 High residuals are individually `NOT ACCEPTED`; no Critical residual is listed.
  Their production capabilities remain off or prohibited.
- **Lifecycle trace: Passed as a design review.** Twelve stable data classes cover every
  accepted class plus a separate typed pseudonymous identity/device checkpoint without
  broadening the room/session tombstone. Room/session deletion is an exactly-one typed
  union: canonical-room scope covers room metadata plus every current/historical/pending/
  late/restored child; immutable-session scope covers only the authoritative session and
  its derivatives while preserving siblings/shared room state. Invalid/conflicting scope
  starts no guessed purge, and room tombstones dominate child manifests. Immediate
  containment is provisional: the existing `hidden` tombstone must commit/read back from
  the independent recovery boundary before acknowledgement, reportable state, or purge;
  unresolved intake, empty application state, crashes, and response loss cannot bypass
  restore/re-enable. The exact audio ceilings, no-retry-queue rule, three truthful deletion
  states, immutable late-SLA result, provider-window boundary, checkpoint durability, and
  forced-off restore order are explicit. This is not runtime enforcement evidence.
- **Tabletop 1A — active-room global disable: Passed on paper.** The runbook immediately
  latches off, denies starts/reconnects, stops the platform session, revokes the lease,
  rejects late output, clears conforming audio/locator RAM, hides publication, and keeps
  the system off after a journal/recovery-copy write failure.
- **Tabletop 1B — room-scoped denylist: Passed on paper.** With room `A` active, a
  committed `add(B)` denies unrelated room `B` without touching `A`'s session, lease,
  audio/locator RAM, or publication; `add(A)` cleans only `A`. Canonical/binding,
  predecessor-generation, journal, or recovery-copy uncertainty escalates to global off.
  Global enable preserves the complete denylist, room removal never enables globally,
  and generation change alone only triggers re-evaluation.
- **Tabletop 2 — typed room/session partial and late deletion: Passed on paper.** Separate
  room and session subcases prove exactly-one selector validation; unknown/conflicting/
  composite rejection without guessed purge; room-wide discovery of initial and stale-
  restored sessions; session-only sibling/shared-state preservation; room-over-session
  tombstone dominance; and shared-projection recomputation. Primary-store outage,
  intake/tombstone commit/read-back failure, pre-commit crash, post-commit response loss,
  restart, and empty-store variants return no false success or purge and reuse the same
  selector/manifest/original time. A failed raw-object deletion cannot report active
  completion, retry is idempotent, late success records `sla_breached=true`, and final
  state waits for every window and restore check.
- **Tabletop 3 — stale restore: Passed on paper.** The environment starts isolated and
  forced off; purges restored verifier/session rows; advances or reconciles a recovery-
  protected auth-invalidation generation/key version; rejects stateful/stateless pre-
  restore credentials; reconciles every unresolved intake to a verified pending `hidden`
  tombstone; replays typed room-all-child/exact-session manifests with room dominance plus
  typed account/device checkpoints; rejects empty application state as proof of no target;
  and proves deleted authority cannot receive new credentials before orthogonal global/
  denylist safety reconciliation.
  Restored admin sessions stay invalid, and only a fresh non-restored separately audited
  recovery-admin authentication may request re-enable after all other gates pass.
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
re-reviews reported no remaining P1/P2 at implementation head `9b534b6`. GitHub GFM
rendered all record tables, Mermaid rendering passed, local links resolved, official
source URLs were reachable, and the upstream commit/tree/blob/digest checks matched.

The first remote review of PR #22 then found one valid P1:
[restored application backups could recreate deleted account/device authority and accept
backed-up credentials](https://github.com/Shuang-su/Livecho/pull/22#discussion_r3839433951).
The resolution keeps the accepted room/session tombstone unchanged and adds the stricter,
separate `DATA-IDENTITY-REVOCATION-CHECKPOINT` control. It requires durable checkpoint
write/read-back before completion; typed account versus device cascade semantics;
server-side rejection of every stateful/stateless pre-restore credential; non-restorable
current verification-key material; denial of newly issued authority to deleted targets;
and fresh non-restored audited recovery-admin authentication before re-enable. The
accepted `intent.md`, `spec.md`, and `plan.md` remain unchanged; the implementation record
closes the gap without reinterpreting the room/session tombstone.

The post-first-fix independent review and mechanical consistency audit found no remaining
local P1/P2 at head `cc1345c`. The next remote review then found a second valid P1:
[the deletion procedure required both `room_id` and `session_id` instead of supporting
either scope](https://github.com/Shuang-su/Livecho/pull/22#discussion_r3839474501).
The resolution defines an exactly-one typed selector across the ADR, lifecycle, threat,
ingest policy, runbook, and tabletops: canonical-room scope covers room metadata and re-
enumerates every current/historical/pending/late/restored session, while an immutable-
session selector resolves its parent from the authoritative index, purges only that
session, and preserves siblings/shared room state. Room tombstones dominate child
manifests. None, both, ambiguous, conflicting, missing, or non-unique targets block the
widest safely identified exposure and start no guessed destructive purge. The accepted
artifact wording “delete by canonical room/session” remains unchanged and is implemented
as the explicit union rather than a composite requirement.

The post-selector independent review and mechanical consistency audit found no remaining
local P1/P2 at `daa940a`. The delayed remote review of that head then found two additional
valid findings:

- P1: [volatile `hidden` state could lose a deletion target across restart before its
  tombstone was persisted](https://github.com/Shuang-su/Livecho/pull/22#discussion_r3839510673).
  The resolution makes immediate selector containment provisional and keeps the initiating
  intake unresolved. The existing `hidden` tombstone is admitted only after independent-
  recovery-boundary commit/read-back; only then may the request be acknowledged, `hidden`
  reported, or purge begin. Failed/ambiguous intake, both crash windows, response loss,
  restart, restore, audit-only evidence, and an empty application store cannot bypass the
  idempotent admission/replay or re-enable gate. The three deletion states remain unchanged.
- P2: [a room denylist addition incorrectly followed the global-disable cleanup
  path](https://github.com/Shuang-su/Livecho/pull/22#discussion_r3839510676). The resolution
  models the global enable bit and complete canonical-room denylist as orthogonal values
  under one predecessor-bound monotonic generation. A committed `add(R)` changes and
  cleans only `R`, with unrelated-room noninterference; global disable cleans all. Global
  enable preserves the denylist and removing one entry never enables globally. Unknown or
  conflicting canonical/resource binding, stale state, or journal/recovery commit/read-
  back failure escalates to global forced-off, while generation change alone re-evaluates.

Final independent semantic and mechanical re-reviews found no remaining P1/P2. The
semantic review found one intermediate P2 in the revised text—the 24-hour active-purge
SLA was measured from admission rather than the original initiating request—and the final
tree now includes admission delay in that immutable clock. Fresh `make bootstrap && make
verify` passed with 40 pytest tests. The latest worktree has 30 stable controls, 12 data
classes, 13 individually unaccepted High rows, continuous `FLOW-ALLOW-001`–`020` and
`FLOW-DENY-001`–`018`, no shared-control owner mismatch, 35/35 GitHub-rendered GFM tables,
18/18 local links, and a successful Mermaid 11.12.0 render.

## Deviations

None. Missing external permission, provider configuration, runtime controls, production
evidence, or owner risk acceptance is represented as a blocking gate, not treated as a
deviation.

## Release and rollback evidence

Not deployed. Production authentication/restore traffic, ingest, persistence/export, and
community-worker real PCM remain disabled. Repository-owner approval of the final ADR and
threat-model record is pending; no Critical/High residual risk is accepted by this
evidence.
