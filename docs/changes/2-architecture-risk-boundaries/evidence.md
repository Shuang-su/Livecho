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
| `make bootstrap` | Passed; uv checked 10 packages and pnpm 11.21.0 reported the frozen workspace already up to date. | 2026-08-24 / final staged tree after r3839675466, r3839675474, and r3839675477 |
| `make verify` | Passed; Ruff check/format, workspace lint, mypy, typecheck, 40 pytest tests, pnpm tests, change-artifact gate, and build all succeeded. | 2026-08-24 / final staged tree after r3839675466, r3839675474, and r3839675477 |
| `git diff --check && git diff --cached --check` | Passed with no whitespace errors on the final staged tree. | 2026-08-24 / final staged tree after r3839675466, r3839675474, and r3839675477 |
| `git diff --quiet origin/main -- docs/changes/2-architecture-risk-boundaries/intent.md docs/changes/2-architecture-risk-boundaries/spec.md docs/changes/2-architecture-risk-boundaries/plan.md` | Passed; the owner-merged intent/spec/plan are unchanged from `origin/main` (`a44fc1f`). | 2026-08-24 / final staged tree after r3839675466, r3839675474, and r3839675477 |
| Mermaid CLI render command below | Passed with `@mermaid-js/mermaid-cli` 11.12.0 and system Google Chrome; one 94,811-byte SVG was produced. | 2026-08-24 / final staged tree after r3839675466, r3839675474, and r3839675477 |
| GitHub Markdown API table-render command below | Passed; 35 delimiter tables rendered as 35 GitHub HTML tables; raw and rendered row-width mismatches: 0. | 2026-08-24 / final staged tree after r3839675466, r3839675474, and r3839675477 |
| Local-link and stable-ID audit command below | Passed; links 18/18; CTRL 50 rows/30 unique/16 shared with 0 shared later-Issue owner-set mismatches and 0 undefined; DATA 12 with 0 undefined; FLOW-ALLOW-001–020 and FLOW-DENY-001–018 exact; the 13 High threat rows exactly match 13 decision rows, all `NOT ACCEPTED`; Critical rows: 0. | 2026-08-24 / final staged tree after r3839675466, r3839675474, and r3839675477 |

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
wc -c "$livecho_mmdc_tmp/rendered-1.svg"
```

It produced one 94,811-byte SVG.

The exact GitHub GFM table-render audit was:

```sh
gfm_audit_tmp=$(mktemp -d)
records=(
  docs/architecture/adr/0001-alpha-modular-monolith.md
  docs/security/alpha-threat-model.md
  docs/security/data-lifecycle-and-deletion.md
  docs/policy/bilibili-public-ingest.md
  docs/policy/independent-implementation.md
  docs/operations/incident-disable-and-recovery.md
)
for file in "${records[@]}"; do
  gh api markdown --method POST -f mode=gfm -f context=Shuang-su/Livecho \
    -F text="@$file" > "$gfm_audit_tmp/$(basename "$file").html"
done
GFM_AUDIT_DIR="$gfm_audit_tmp" uv run python - <<'PY'
from html.parser import HTMLParser
from pathlib import Path
import os
import re

records = [
    Path("docs/architecture/adr/0001-alpha-modular-monolith.md"),
    Path("docs/security/alpha-threat-model.md"),
    Path("docs/security/data-lifecycle-and-deletion.md"),
    Path("docs/policy/bilibili-public-ingest.md"),
    Path("docs/policy/independent-implementation.md"),
    Path("docs/operations/incident-disable-and-recovery.md"),
]

class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.table, self.row = [], None, None
    def handle_starttag(self, tag, attrs):
        if tag == "table": self.table = []
        elif tag == "tr" and self.table is not None: self.row = []
        elif tag in ("th", "td") and self.row is not None: self.row.append(tag)
    def handle_endtag(self, tag):
        if tag == "tr" and self.row is not None:
            self.table.append(self.row); self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table); self.table = None

raw_total = html_total = 0
raw_bad, html_bad = [], []
for path in records:
    lines = path.read_text().splitlines()
    delimiters = [i for i, line in enumerate(lines) if re.match(r"^\|\s*:?-{3,}", line)]
    raw_total += len(delimiters)
    for i in delimiters:
        expected = len(lines[i].split("|")[1:-1])
        row_indexes = [i - 1]
        j = i + 1
        while j < len(lines) and lines[j].startswith("|") and lines[j].endswith("|"):
            row_indexes.append(j); j += 1
        for row_index in row_indexes:
            actual = len(lines[row_index].split("|")[1:-1])
            if actual != expected:
                raw_bad.append((str(path), i + 1, row_index + 1, expected, actual))
    rendered = Path(os.environ["GFM_AUDIT_DIR"]) / f"{path.name}.html"
    parsed = Tables(); parsed.feed(rendered.read_text())
    html_total += len(parsed.tables)
    for table_index, table in enumerate(parsed.tables, 1):
        expected = len(table[0])
        for row_index, row in enumerate(table, 1):
            if len(row) != expected:
                html_bad.append((str(path), table_index, row_index, expected, len(row)))
assert raw_total == 35, raw_total
assert html_total == 35, html_total
assert not raw_bad, raw_bad
assert not html_bad, html_bad
print("GFM_TABLES=35/35 RAW_WIDTH_MISMATCHES=0 HTML_WIDTH_MISMATCHES=0")
PY
```

It printed `GFM_TABLES=35/35 RAW_WIDTH_MISMATCHES=0 HTML_WIDTH_MISMATCHES=0`.

The exact local-link and stable-ID audit was:

```sh
uv run python - <<'PY'
from pathlib import Path
import re

records = [
    Path("docs/architecture/adr/0001-alpha-modular-monolith.md"),
    Path("docs/security/alpha-threat-model.md"),
    Path("docs/security/data-lifecycle-and-deletion.md"),
    Path("docs/policy/bilibili-public-ingest.md"),
    Path("docs/policy/independent-implementation.md"),
    Path("docs/operations/incident-disable-and-recovery.md"),
]
text = "\n".join(path.read_text() for path in records)

link_pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
links = []
for source in [Path("README.md"), Path("SECURITY.md"), *records]:
    for line_number, line in enumerate(source.read_text().splitlines(), 1):
        for target in link_pattern.findall(line):
            target = target.strip().removeprefix("<").removesuffix(">")
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
                continue
            destination = (source.parent / target.split("#", 1)[0].split("?", 1)[0]).resolve()
            links.append((source, line_number, target, destination.exists()))
missing = [(str(s), n, t) for s, n, t, exists in links if not exists]
assert len(links) == 18, len(links)
assert not missing, missing

control_rows = []
for source in records:
    for line_number, line in enumerate(source.read_text().splitlines(), 1):
        match = re.match(r"^\|\s*`(CTRL-[A-Z0-9-]+)`\s*\|(.*)\|\s*$", line)
        if match:
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            issues = tuple(sorted({int(value) for value in re.findall(r"#(\d+)", cells[-1])}))
            control_rows.append((match.group(1), source, line_number, issues))
control_ids = {row[0] for row in control_rows}
control_references = set(re.findall(r"\bCTRL-[A-Z0-9-]+\b", text))
by_control = {
    identifier: [row for row in control_rows if row[0] == identifier]
    for identifier in control_ids
}
shared = {identifier: rows for identifier, rows in by_control.items() if len(rows) > 1}
owner_mismatches = {
    identifier: rows for identifier, rows in shared.items()
    if len({row[3] for row in rows}) > 1
}
assert len(control_rows) == 50, len(control_rows)
assert len(control_ids) == 30, len(control_ids)
assert len(shared) == 16, len(shared)
assert not owner_mismatches, owner_mismatches
assert not control_references - control_ids, sorted(control_references - control_ids)

data_rows = []
for source in records:
    for line_number, line in enumerate(source.read_text().splitlines(), 1):
        match = re.match(r"^\|\s*`(DATA-[A-Z0-9-]+)`(?::[^|]*)?\s*\|", line)
        if match:
            data_rows.append((match.group(1), source, line_number))
data_ids = {row[0] for row in data_rows}
data_references = set(re.findall(r"(?<![A-Z0-9-])DATA-[A-Z0-9-]+\b", text))
assert len(data_rows) == 12, len(data_rows)
assert len(data_ids) == 12, len(data_ids)
assert not data_references - data_ids, sorted(data_references - data_ids)

flows = {"ALLOW": [], "DENY": []}
for line in records[0].read_text().splitlines():
    if not line.startswith("| `FLOW-"):
        continue
    first_cell = line.split("|")[1]
    for kind, start, end in re.findall(
        r"FLOW-(ALLOW|DENY)-(\d{3})(?:`?–`?FLOW-\1-(\d{3}))?", first_cell
    ):
        flows[kind].extend(
            f"FLOW-{kind}-{number:03d}"
            for number in range(int(start), int(end or start) + 1)
        )
for kind, maximum in (("ALLOW", 20), ("DENY", 18)):
    expected = {f"FLOW-{kind}-{number:03d}" for number in range(1, maximum + 1)}
    assert len(flows[kind]) == maximum, (kind, len(flows[kind]))
    assert set(flows[kind]) == expected, (kind, sorted(set(flows[kind]) ^ expected))

threat_rows, decision_rows, critical_rows = [], [], []
for line_number, line in enumerate(records[1].read_text().splitlines(), 1):
    if not re.match(r"^\|\s*`(?:THREAT|RISK)-", line):
        continue
    cells = [cell.strip() for cell in line.split("|")[1:-1]]
    if len(cells) == 11:
        if "**High**" in cells[-2]:
            threat_rows.append((cells[0].strip("`"), cells[-1]))
        if "**Critical**" in cells[-2]:
            critical_rows.append(line_number)
    elif len(cells) == 6:
        if cells[2] == "High":
            decision_rows.append((cells[0].strip("`"), cells[-1]))
        if cells[2] == "Critical":
            critical_rows.append(line_number)
assert len(threat_rows) == 13, len(threat_rows)
assert len(decision_rows) == 13, len(decision_rows)
assert {row[0] for row in threat_rows} == {row[0] for row in decision_rows}
assert all("NOT ACCEPTED" in row[1] for row in threat_rows)
assert all("NOT ACCEPTED" in row[1] for row in decision_rows)
assert not critical_rows, critical_rows
print(
    "LINKS=18/18 CTRL_ROWS=50 CTRL_UNIQUE=30 CTRL_SHARED=16 "
    "SHARED_ISSUE_OWNER_MISMATCHES=0 CTRL_UNDEFINED=0 DATA=12 "
    "DATA_UNDEFINED=0 FLOW_ALLOW=1-20 FLOW_DENY=1-18 "
    "HIGH=13/13_ALL_NOT_ACCEPTED CRITICAL=0"
)
PY
```

It printed `LINKS=18/18 CTRL_ROWS=50 CTRL_UNIQUE=30 CTRL_SHARED=16
SHARED_ISSUE_OWNER_MISMATCHES=0 CTRL_UNDEFINED=0 DATA=12 DATA_UNDEFINED=0
FLOW_ALLOW=1-20 FLOW_DENY=1-18 HIGH=13/13_ALL_NOT_ACCEPTED CRITICAL=0`.

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
  a commit/read-back-verified `open(E)` intake-continuity epoch exists before deletion
  ingress opens. Durable intake atomically retains selector, idempotency, and immutable
  original initiating-request time for tombstone reuse. A first target-write failure,
  source disappearance, and backend crash leave the target-free epoch unmatched, so an
  empty application store cannot bypass restore/re-enable even when the exact target is
  unavailable; the epoch authorizes no guessed purge or fourth state. The exact audio
  ceilings, no-retry-queue rule, three truthful deletion
  states, immutable late-SLA result, provider-window boundary, checkpoint durability, and
  forced-off restore order are explicit. This is not runtime enforcement evidence.
- **Tabletop 1A — active-room global disable: Passed on paper.** The runbook immediately
  latches off, closes admission/publication/lease/output authority, and issues every
  active/queued-room termination, revocation, clear, and hide action before the first
  journal/recovery-copy await. Slow, hung, failed, or split durability cannot postpone
  locally controlled cleanup. A relaxation is first a non-effective `PREPARED` proposal;
  conditional recovery-head promotion makes it `COMMITTED`, but only a non-restorable
  activation installed by that same live incarnation can serve. Global disable raises the
  global guard and revokes activation before durability, while `add(R)` raises only the
  room guard and preserves unrelated-room activation. Both record their exact scope as
  safety-pending until durably reconciled, and both prevent `clean-close(E)`; pending by
  itself is not a global effect. Tabletop races `clean-close(E)` against global disable and
  room add in both orders, including durability failure plus exit. The atomic serving/
  safety/deletion-ingress close fence forces a late tightening to reconcile before close
  or be rejected/bound to a new verified epoch. Prepare/promotion/final-activation races,
  crashes, and late responses never let a dead incarnation reopen. Alpha has one active
  serving authority; a future unacknowledged owner is isolated/terminated and keeps the
  deployment off.
- **Tabletop 1B — room-scoped denylist: Passed on paper.** With room `A` active, a
  pending or committed `add(B)` denies unrelated room `B` without touching `A`'s global
  activation, session, lease, audio/locator RAM, or publication; `add(A)` begins target
  cleanup before durability. Canonical/binding, predecessor-generation, journal, or
  recovery-copy failure/uncertainty invokes a distinct global-disable transition, which is
  the point that revokes global activation and starts all-room cleanup.
  Disable/add same-predecessor races reapply a losing tightening to the newest complete
  head; add response loss and add/remove races before/after durable promotion and local
  activation never reopen a newer block. Global enable preserves the complete denylist,
  room removal never enables globally, and generation change alone creates no activation.
  Ordinary initial-offline, normal-end, and reconnect-offline outcomes stop and clear only
  the attempted/current session without changing the journal, generation, or denylist;
  later live status must pass fresh eligibility but needs no denylist-removal approval.
  Missing or stale prerequisites deny the attempted action and trigger review, while only
  an explicit authorized exact-room policy/rights/safety incident can create `add(R)`.
- **Tabletop 2 — typed room/session partial and late deletion: Passed on paper.** Separate
  room and session subcases prove exactly-one selector validation; unknown/conflicting/
  composite rejection without guessed purge; room-wide discovery of initial and stale-
  restored sessions; session-only sibling/shared-state preservation; room-over-session
  tombstone dominance; and shared-projection recomputation. A normal valid room/session
  intake fences concurrent relaxation and installs only selector-scoped provisional
  containment; a normal invalid request obtains durable denial. Neither case revokes the
  existing global activation or disrupts a non-target room/session. Intake, denial, or
  tombstone persistence failure, or inability to prove scoped isolation, instead taints
  continuity and explicitly escalates to global off. Primary-store outage,
  continuity-epoch open/close failure and close-versus-late-request races, first target-
  write failure followed by source loss and backend crash, tombstone commit/read-back
  failure, post-commit response loss, restart, and empty-store variants return no false
  success or purge. An unmatched epoch
  blocks every traffic class and relaxation indefinitely unless authoritative replay
  recovers the original request; it does not name a target or reset the clock. Durable
  intake and the tombstone reuse the same selector/idempotency/original-time triple. A failed raw-
  object deletion cannot report active
  completion, retry is idempotent, late success records `sla_breached=true`, and final
  state waits for every window and restore check.
- **Tabletop 3 — stale restore: Passed on paper.** The environment starts isolated and
  forced off with a new incarnation and no activation; rejects prepared/split relaxation
  and a prior incarnation's committed enable/late response; quarantines unmatched
  continuity epochs; purges restored verifier/session rows; advances or reconciles a recovery-
  protected auth-invalidation generation/key version; rejects stateful/stateless pre-
  restore credentials; reconciles every unresolved valid intake to a verified pending
  `hidden` tombstone and every invalid request to durable denial; replays typed room-all-
  child/exact-session manifests with room dominance plus
  typed account/device checkpoints; rejects empty application state as proof of no target;
  and proves deleted authority cannot receive new credentials before orthogonal global/
  denylist safety reconciliation.
  Restored admin sessions stay invalid. Only after authoritative continuity replay and all
  other gates may a fresh non-restored separately audited recovery-admin authentication
  prepare/commit an exact-head transition whose current incarnation separately installs
  activation.
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

Independent semantic and mechanical re-reviews found no remaining P1/P2 in the resulting
head `4d7e0a9`. The semantic review found one intermediate P2 in the revised text—the
24-hour active-purge SLA was measured from admission rather than the original initiating
request—and that head included admission delay in the immutable clock. Fresh `make
bootstrap && make verify` passed with 40 pytest tests.

The next delayed remote review found another valid P1:
[global disable waited for journal/recovery durability before active cleanup started](https://github.com/Shuang-su/Livecho/pull/22#discussion_r3839563695). The resolution
separates the immediate local safety path from durable transition I/O: one Alpha serving
authority atomically latches off, closes local admission/publication/lease/output gates,
and starts every active/queued-room cleanup before the first durability await. Cleanup
continues independently under slow, hung, failed, split, or ambiguous I/O; failure keeps
the deployment off, alerts, retries, and blocks relaxation. A high-priority tightening
fence plus atomic final relaxation check/effect closes late enable/remove races in both
linearization orders. The paper tests also cover future-owner fence failure, crash and
response loss, disable/add predecessor races, and room-scoped noninterference.

Cursor Bugbot on the same prior head found a valid P2:
[durable intake omitted the original request time and could reset the 24-hour SLA clock before tombstone admission](https://github.com/Shuang-su/Livecho/pull/22#discussion_r3839566055).
The authenticated intake now assigns one immutable original initiating-request time before
its first durability attempt and atomically stores it with selector/idempotency. If the
write fails, the initiating source retains/retries that same triple; once durable, every
pre-tombstone crash, tombstone admission, response-loss retry, and restore reuses the
unchanged time. Missing or mismatched time fails admission and cannot mint a later clock.

Independent semantic and mechanical re-reviews found no remaining P1/P2 in `af5aecd`, and
fresh verification passed with 40 pytest tests. The delayed remote review of that head
then found two additional valid blockers:

- P1: [a failed first deletion-intake write still relied on the initiating source to
  survive and retry](https://github.com/Shuang-su/Livecho/pull/22#discussion_r3839611978).
  If that source and backend both disappeared, recovery had no durable fact that a request
  might be missing. The resolution pre-arms each serving incarnation with an append-only,
  commit/read-back-verified `open(E)` intake-continuity epoch before deletion ingress or
  activation. A failed exact intake taints the incarnation and forbids `clean-close(E)`;
  after a crash the unmatched target-free epoch quarantines every traffic class and
  relaxation even with an empty application store. It cannot report `hidden`, start
  purge, or guess a selector, and without exact authoritative replay the deployment stays
  off indefinitely. The initiating source may aid replay but is no longer the safety
  authority.
- High/P1: [a durable global-enable candidate could outlive a failed final fence and
  reopen after crash](https://github.com/Shuang-su/Livecho/pull/22#discussion_r3839614028).
  The resolution makes a predecessor-bound `PREPARED` proposal non-current and uses a
  conditional recovery-head promotion as the `COMMITTED` durable linearization point.
  Even a committed enabled snapshot cannot serve: the same live incarnation must pass a
  separate final fence/continuity check and install a non-restorable activation. Every
  restart has a new incarnation and no activation; old commits, capabilities, and delayed
  responses cannot reopen. Global disable first revokes global activation; room add keeps
  unrelated activation and changes only its room block. If either loses a durable
  predecessor race, it reapplies its safe action to the newest complete head; relaxation
  never automatically rebases.

Independent deletion-continuity, safety-race, and mechanical reviews found no local P1/P2
before `89b891f`, but the remote review of that head found three additional valid scope
findings:

- P2: [ordinary offline/not-live status was incorrectly made a durable denylist
  entry](https://github.com/Shuang-su/Livecho/pull/22#discussion_r3839675466). The
  resolution separates transient eligibility from explicit safety state: initial offline,
  normal end, and reconnect offline stop/clear only that attempt or current session and do
  not change generation, journal, or denylist. Missing/stale prerequisites deny the action
  and trigger review. Only an authorized, exactly bound room policy/rights/safety incident
  creates `add(R)`; unknown/platform-wide scope invokes global disable without guessing a
  room entry.
- High/P1: [every deletion intake incorrectly revoked global serving
  activation](https://github.com/Shuang-su/Livecho/pull/22#discussion_r3839675474). The
  resolution makes `intake-pending` a concurrency/accounting fence, not a global stop.
  Valid selectors immediately contain only their room/session scope, and normal invalid
  selectors receive durable denial; both preserve unrelated activation. Intake, denial,
  tombstone, or scope-isolation failure instead becomes `tainted` and explicitly escalates
  to global disable, while admitted purge failures remain scoped `hidden` unless isolation
  can no longer be proved.
- High/P1: [generic unresolved-tightening wording made a pending room add revoke global
  activation](https://github.com/Shuang-su/Livecho/pull/22#discussion_r3839675477). The
  resolution distinguishes the sticky global guard from per-room guard `Q[R]`. A pending
  exact `add(R)` blocks/cleans only `R`, preserves unrelated activation, and prevents epoch
  close until reconciled. Binding, timeout, journal/recovery, or result uncertainty invokes
  a separate global-disable transition; that escalation, not ordinary room pending, revokes
  global activation and cleans all rooms.

Final independent deletion-scope, offline/denylist, guard-scope, and mechanical reviews
found no remaining P1/P2 in the resulting tree. Fresh `make bootstrap && make verify`
passed with 40 pytest tests. The final staged tree has 30 stable controls, 12 data classes,
13 individually unaccepted High rows, continuous `FLOW-ALLOW-001`–`020` and
`FLOW-DENY-001`–`018`, no shared-control owner mismatch, 35/35 GitHub-rendered GFM tables,
18/18 local links, and a successful Mermaid 11.12.0 render producing one 94,811-byte SVG.

## Deviations

None. Missing external permission, provider configuration, runtime controls, production
evidence, or owner risk acceptance is represented as a blocking gate, not treated as a
deviation.

## Release and rollback evidence

Not deployed. Production authentication/restore traffic, ingest, persistence/export, and
community-worker real PCM remain disabled. Repository-owner approval of the final ADR and
threat-model record is pending; no Critical/High residual risk is accepted by this
evidence.
