# Evidence: Requirement authority and evidence index

## Artifact approval

- Artifact PR: [#32](https://github.com/Shuang-su/Livecho/pull/32) (draft; does not close #30).
- Status: Proposed; approved by/date: Pending.
- Authoring base: `67fc6edc6ca2158fe640d73b9d5f8bf674513d6d` (`main`).
- Branch: `codex/issue-30-requirements-index-spec`.
- Substantive artifact snapshot: `c1d21ec`.
- No index, README, roadmap, product code, protocol, provider or approval-state change
  is included in this artifact phase.

## Requirements-author exposure and assignment

- Identity/role/date: `/root/requirements_index` (OpenAI Codex), independent Issue #30
  requirements author, 2026-10-02; paths are only this Issue's four artifact files.
- Assignment source: the coordinating agent delegated the user's authorized documentation
  design work. This is authority to prepare a draft, not owner approval of its contents
  or authority to implement the pending design.
- Exact repository inputs at the base above: `AGENTS.md`, `CONTRIBUTING.md`, `SECURITY.md`,
  `README.md`, `docs/roadmap.md`, `docs/changes/README.md`, every four-file artifact in
  `docs/changes/1-repository-foundation/`,
  `docs/changes/2-architecture-risk-boundaries/`,
  `docs/changes/3-protocol-v1-contract/`, and
  `docs/changes/4-railway-deployment-skeleton/`; the four `docs/changes/_template/`
  files; both `docs/policy/independent-implementation.md` and
  `docs/policy/bilibili-public-ingest.md` in full; `Makefile`; and the artifact checker's
  naming/lifecycle interface in `tools/check_change_artifacts.py`.
- Additional local inputs: status/assurance introductions plus heading/stable-control
  registry excerpts from `docs/architecture/adr/0001-alpha-modular-monolith.md`,
  `docs/security/alpha-threat-model.md`, `docs/security/data-lifecycle-and-deletion.md`,
  `docs/operations/incident-disable-and-recovery.md`,
  `docs/operations/railway-deployment.md`, and `docs/operations/railway-secrets.md`.
  This is an artifact design audit, not a claim to have completed the future full
  requirement inventory in those documents.
- Exact GitHub inputs: #30 body/title/state/URL; #27/#28/#29 body/title/state/URL and
  update time; #5–#19 title/state/update time and only their `## 依赖` sections;
  #1–#4 number/state/closure time/URL. Captured 2026-10-02 through read-only `gh` calls.
- Additional task context: repository guidance and the delegated scope; the known #31
  number and title “开放贡献闭环、可信统计及字幕体验” as a pending proposal only; the
  coordinator's branch-pattern correction and quota-monitor instructions. #31's body,
  research, and proposed behavior were not supplied to this author.
- Indirect exposure disclosed: accepted Livecho artifacts and the local license policy
  contain the earlier authors' reference-repository names, revisions, license metadata,
  and descriptions of their own exposure/review process. This author saw that local
  provenance record, not the upstream files or factual behavior summaries themselves.
  The Issue #4 artifacts also describe vendor-derived contracts and contain vendor URLs;
  those dated local records were read without opening the external sources.
- Exclusions: no reference repository/source/test/fixture/schema/config/comment/docs/
  asset, screenshot, external article/conversation, generated reference-research report,
  or GUI research output was opened. No model, dataset or audio was downloaded. No known
  prior contribution to a reference project exists in this task context. No reference
  expression is a drafting input. Only independently authored Livecho requirements above
  support this proposal.
- Assignment decision: author this documentation artifact only. A fresh implementer
  exposure/assignment record and named separate reviewer are required before the later
  documentation implementation. Independent artifact review is recorded below.

## Read-only Issue snapshot

This snapshot records planning facts, not artifact acceptance or runtime readiness.
Issues #1–#4 are closed; all following rows are open as of 2026-10-02.

| Issue | Direct prerequisites observed |
| --- | --- |
| #5 | #1, #2 |
| #6 | #3, #5 |
| #7 | #2, #3, #8 |
| #8 | #2, #3 |
| #9 | #3, #6, #8 |
| #10 | #2, #3, #7 |
| #11 | #3, #9 |
| #12 | #2, #4 |
| #13 | #3, #6, #12 |
| #14 | #3, #13 |
| #15 | #5, #13, #14, #27 |
| #16 | #2, #4, #10, #12 |
| #17 | #11, #12, #13, #16 |
| #18 | #3, #6, #14 |
| #19 | #4, #7, #11, #15, #16, #17, #18, #27, #28, #29 |
| #27 | #3 |
| #28 | #2, #3 |
| #29 | #10, #11 |
| #30 | #2, #3, #4 |

Exact command forms, executed with each number in the stated set:

```sh
# n = 30
gh issue view "$n" --json number,title,body,url,state
# n = 27, 28, 29
gh issue view "$n" --json number,title,body,url,state,updatedAt
# n = 5 through 19
gh issue view "$n" --json number,title,state,updatedAt,body --jq '{number,title,state,updatedAt,dependencies:(.body|split("## 依赖")[1]|split("## ")[0])}'
# n = 1 through 4
gh issue view "$n" --json number,state,closedAt,url
```

The read-only results establish #27/#28/#29's intended ownership and dependencies, not
their implementation or acceptance. #31's body was deliberately not fetched.

## Automated verification

| Exact command | Result | Date/revision |
| --- | --- | --- |
| `git rev-parse HEAD` | Base is `67fc6edc6ca2158fe640d73b9d5f8bf674513d6d`. | 2026-10-02 / before authoring |
| `make bootstrap` | Passed; frozen uv environment and frozen pnpm install, dependency lifecycle scripts denied. | 2026-10-02 / staged artifact tree |
| `make verify` | Passed; Ruff, mypy on 22 Python files, 107 pytest tests, 128 protocol Vitest tests, 63 Railway Vitest tests, artifact/protocol drift checks and workspace builds. | 2026-10-02 / staged artifact tree |
| `make artifacts` | Passed; `change artifacts: ok`. | 2026-10-02 / staged artifact tree |
| `git diff --check` | Passed; no whitespace errors. | 2026-10-02 / artifact tree |
| `git diff --cached --check` | Passed; no staged whitespace errors. | 2026-10-02 / staged artifact tree |
| `git diff --name-only origin/main...HEAD` | Passed; exactly the four required paths under this Issue's directory. | 2026-10-02 / `c1d21ec` |
| Artifact scope/format audit below | Passed; four artifact paths, two Issue links, accepted sources unchanged. | 2026-10-02 / staged artifact tree |
| `make artifacts`; `git diff --check`; `git diff --cached --check` | Passed after the PR/review evidence append. | 2026-10-02 / evidence-only update after `c1d21ec` |
| `git diff --name-only origin/main` | Passed; exactly the four #30 artifact paths including the evidence append. | 2026-10-02 / evidence-only update after `c1d21ec` |
| `git diff --quiet c1d21ec -- docs/changes/30-requirements-evidence-index/intent.md docs/changes/30-requirements-evidence-index/spec.md docs/changes/30-requirements-evidence-index/plan.md` | Passed; reviewed intent/spec/plan unchanged. | 2026-10-02 / evidence-only update after `c1d21ec` |

Exact artifact scope/format audit, run before the commit and PR-link append:

```sh
uv run python - <<'PY'
from pathlib import Path
import re
import subprocess

root = Path('docs/changes/30-requirements-evidence-index')
expected = {str(root / f'{name}.md') for name in ('intent', 'spec', 'plan', 'evidence')}
changed = set(subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True).splitlines())
assert changed == expected, changed
links = []
for path in sorted(root.glob('*.md')):
    text = path.read_text()
    assert text.endswith('\n') and text.startswith('# '), path
    assert not re.search(r'^# (?:Intent|Specification): <', text, re.M), path
    assert not re.search(r'^- (?:GitHub Issue: #<|Human owner: @<)', text, re.M), path
    links.extend(re.findall(r'\[[^\]]+\]\(([^)]+)\)', text))
assert set(links) == {'https://github.com/Shuang-su/Livecho/issues/30', 'https://github.com/Shuang-su/Livecho/issues/31'}, links
assert '- Approved by/date: Pending' in (root / 'intent.md').read_text()
assert subprocess.run(['git', 'diff', '--quiet', 'origin/main', '--', 'README.md', 'docs/roadmap.md', 'docs/changes/1-repository-foundation', 'docs/changes/2-architecture-risk-boundaries', 'docs/changes/3-protocol-v1-contract', 'docs/changes/4-railway-deployment-skeleton']).returncode == 0
print(f'ARTIFACT_FILES={len(changed)} MARKDOWN_LINKS={len(links)} UNIQUE_ISSUE_LINKS=2 ACCEPTED_SOURCES_UNCHANGED=1')
PY
```

Result: `ARTIFACT_FILES=4 MARKDOWN_LINKS=2 UNIQUE_ISSUE_LINKS=2
ACCEPTED_SOURCES_UNCHANGED=1`. This checks the draft's two known Issue links and format,
not the future index's full link/section inventory. An initial overly broad placeholder
search rejected the legitimate documented branch-pattern token `<number>` in this
evidence file. The audit was narrowed to actual unfilled template headings/owner fields;
the documents did not need a semantic change.

## Manual evidence and review findings

- Source review: #2's accepted artifacts and its merged supporting records distinguish
  documentary constraints from final ADR/risk decisions; the ADR still says Proposed
  and owner approval pending. #3 evidence concerns deterministic protocol verification.
  #4 evidence concerns offline desired state and fail-closed guards, with no live provider
  access. The new artifact preserves each of these qualifications.
- Sequence review: the current roadmap's numeric ordering does not express #7's actual
  dependency on #8; README's status does not explicitly name the merged #3/#4 scope.
  Correction is planned for the separate implementation, not applied in this draft.
- Independent reviewer: `/root/artifact_review`, OpenAI Codex, 2026-10-02. Read-only
  artifact design review of `c1d21ec` found no actionable contradiction in scope,
  evidence/authority separation, source status, or local-synthetic versus production
  gate handling. The reviewer changed no files and did not rerun tests.
- Reviewer provenance: repository `AGENTS.md`; Issue #30 and all four proposed #30
  artifacts; accepted #1 specification in full; relevant visible #2 audio, #3 protocol/
  source-authority, and #4 offline/default-off specification sections; selected local
  ADR/lifecycle policy excerpts. In its separately assigned #5 review, the reviewer also
  read that Issue and its four draft artifacts. The reviewer explicitly reported that
  long supporting-source output was truncated and did not claim a complete inventory
  audit. No reference repository, #31 body, generated research report, or external page
  was accessed; no prior reference-project contribution was known in
  that review context. The author received only this source-based finding/provenance
  summary, with no reference expression.
- The independent result is artifact design review, not implementation, production,
  source-rights, or owner approval. Hardware and provider checks are neither required
  nor performed.
- The final requirement inventory, formal index links/coverage audit, and README/roadmap
  consistency audit remain implementation work after artifact approval.

## Deviations

None. The requested short branch spelling was adjusted to the repository's required
`codex/issue-<number>-<slug>` pattern before authoring; no validator was weakened.

## Release and rollback evidence

Not deployed. This draft creates no runtime, infrastructure, policy authorization,
accepted risk, or source rights. It can be revised or closed without operational effect.

## 2026-11-15 — Documentation implementation (index / README / roadmap)

Implementer: Cursor Auto (cloud agent). Artifact PR [#32](https://github.com/Shuang-su/Livecho/pull/32)
merged as `e62c65f`. Implementation base: `main` at
`c8ee4a1658774416b1a00b70a872f8818110a060` (includes [#44](https://github.com/Shuang-su/Livecho/pull/44)–[#54](https://github.com/Shuang-su/Livecho/pull/54)
fixture/CI slices). Branch: `issue/30-requirements-index-impl`. Accepted
intent/spec/plan were **not** rewritten. Closed unmerged draft
[#35](https://github.com/Shuang-su/Livecho/pull/35) was prior art only (structure
reference); its git history was not merged.

### Author exposure and assignment

- Inputs: AGENTS.md, CONTRIBUTING.md, Issue #30 body, accepted #30 intent/spec/plan,
  prior #35 tree (read-only), current README/roadmap, `docs/requirements-index` seed
  from prior art, architecture/security/policy/operations sources for stable-ID
  inventory, GitHub Issue #5–#19/#27–#31 state+`依赖` via read-only `gh`, merged PR
  list #44–#54 on `main`.
- Exclusions: no #31 body, no live services, no model/audio downloads, no user
  machines, no normative source edits, no M2 implementation.
- Assignment: documentation implementation only under the plan allowlist
  (`docs/requirements-index.md`, `README.md`, `docs/roadmap.md`, this `evidence.md`).

### What landed

- `docs/requirements-index.md` — secondary navigation with evidence profiles for
  foundation/protocol/Railway/policy plus **fixture/CI profiles S5–S11** for landed
  #5–#11 slices; delivery rows distinguish fixture vs missing hardware/rights/wire;
  conflict register notes closed Issues ≠ product acceptance.
- `README.md` — names merged #1–#4 and fixture/gated M1 slices; states real ASR/live/
  production are not established; links index/roadmap and local fixture commands.
- `docs/roadmap.md` — dated GitHub dependency snapshot with planning state and
  fixture/CI notes; conditional gates unchanged in intent.

### Critical-review findings / fixes

- Rejected treating GitHub-closed #5/#6/#7/#8/#10 as real MLX/live acceptance.
- Rejected merging stale #35 history; refreshed against `c8ee4a1`.
- Spec-family inventory (`DEC|FLOW|CTRL|DATA|THREAT|RISK|BILI|LIC|GATE`) excludes
  wildcard prose prefixes `BILI-SRC` / `BILI-RIGHT` and non-required `ENTRY-*` /
  `ASSET-*` / `ACT-*` taxonomy labels (those remain supporting threat-model tables,
  not primary requirement rows).
- Manual traces: #9/#11 fixture path is `fixture_timeline` + Node/Python E2E only;
  #27/#28/#29 remain N; Railway W offline vs live provider missing; thirteen High
  residuals stay NOT ACCEPTED; ADR remains Proposed.
- Independent human reviewer for this documentation PR is **pending** (plan step 8);
  this agent did not invent a second reviewer. Owner review of the draft PR supplies it.

### Exact ephemeral audits (not added to the repository)

Scripts were executed from `/tmp` only. Final counts below were taken after this evidence
append and before commit.

#### Index / link / ownership / scope audit

Command: `uv run python /tmp/livecho-issue30-index-audit.py`

```python
from collections import Counter
from pathlib import Path
import re
import subprocess
import unicodedata

BASE = "c8ee4a1658774416b1a00b70a872f8818110a060"
DELIVERABLES = [Path(p) for p in (
    "README.md", "docs/roadmap.md", "docs/requirements-index.md",
    "docs/changes/30-requirements-evidence-index/evidence.md",
)]
SOURCES = [Path("docs") / (p + ".md") for p in (
    "architecture/adr/0001-alpha-modular-monolith",
    "security/alpha-threat-model", "security/data-lifecycle-and-deletion",
    "policy/bilibili-public-ingest", "policy/independent-implementation",
    "operations/incident-disable-and-recovery",
    "operations/railway-deployment", "operations/railway-secrets",
)]
PATTERN = r"\b(?:DEC|FLOW|CTRL|DATA|THREAT|RISK|BILI|LIC|GATE)-[A-Z0-9]+(?:-[A-Z0-9]+)*"
PROFILE_RE = (
    r"\]\(#(?:foundation|design|protocol|railway|policy|license|pending|"
    r"fixture-asr|fixture-worker|fixture-audio|fixture-ingest|"
    r"fixture-caption|fixture-events|fixture-web)\)"
)
ALLOWED_PATHS = {
    "docs/requirements-index.md", "README.md", "docs/roadmap.md",
    "docs/changes/30-requirements-evidence-index/evidence.md",
}

def prose(path):
    return re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)

def anchors(path):
    result = set(re.findall(r'<a id="([^"]+)"', path.read_text(encoding="utf-8")))
    counts = Counter()
    for heading in re.findall(r"^#{1,6} (.+)$", prose(path), re.M):
        slug = "".join(
            c for c in heading.lower()
            if c in " -_" or unicodedata.category(c)[0] in "LN"
        ).replace(" ", "-")
        count = counts[slug]
        counts[slug] += 1
        result.add(slug + (f"-{count}" if count else ""))
    return result

head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
merge_base = subprocess.check_output(
    ["git", "merge-base", "origin/main", "HEAD"], text=True
).strip()
assert merge_base == BASE or head.startswith(BASE[:7])
all_changed = set(
    subprocess.check_output(["git", "diff", "--name-only", "origin/main...HEAD"], text=True).splitlines()
) | set(
    subprocess.check_output(["git", "diff", "--name-only", "origin/main"], text=True).splitlines()
) | set(
    subprocess.check_output(["git", "diff", "--cached", "--name-only"], text=True).splitlines()
)
assert not sorted(p for p in all_changed if p and p not in ALLOWED_PATHS)
for rel in (
    "docs/changes/30-requirements-evidence-index/intent.md",
    "docs/changes/30-requirements-evidence-index/spec.md",
    "docs/changes/30-requirements-evidence-index/plan.md",
):
    assert subprocess.check_output(["git", "diff", "origin/main", "--", rel], text=True) == ""

local_links, external_links = 0, set()
for path in DELIVERABLES:
    text = prose(path)
    refs = dict(re.findall(r"^\[([^\]]+)\]:\s*(\S+)", text, re.M))
    targets = re.findall(r"\[[^\]\n]+\]\(([^)\n]+)\)", text)
    for label in re.findall(r"\[[^\]\n]+\]\[([^\]\n]+)\]", text):
        assert label in refs
        targets.append(refs[label])
    targets.extend(refs.values())
    for target in targets:
        if re.match(r"https?://", target):
            external_links.add(target)
            continue
        file_part, _, fragment = target.partition("#")
        dest = (path.parent / file_part).resolve() if file_part else path.resolve()
        assert dest.exists(), (path, target)
        if fragment:
            assert dest.is_file() and fragment in anchors(dest), (path, target)
        local_links += 1

source_ids = set()
for path in SOURCES:
    source_ids.update(re.findall(PATTERN, path.read_text(encoding="utf-8")))
source_ids -= {"BILI-SRC", "BILI-RIGHT"}
index = Path("docs/requirements-index.md").read_text(encoding="utf-8")
records = re.findall(
    r"^\| ((?:IDX|DEC|FLOW|CTRL|DATA|THREAT|RISK|BILI|LIC|GATE)-[A-Z0-9-]+) — (.*)$",
    index, re.M,
)
counts = Counter(key for key, _ in records)
assert all(v == 1 for v in counts.values())
indexed_stable = {k for k in counts if not k.startswith("IDX-")}
assert source_ids == indexed_stable
unresolved = 0
for key, rest in records:
    cells = rest.split("|")
    assert len(cells) == 5 and all(c.strip() for c in cells[:4])
    assert len(re.findall(r"\[[^\]]+\](?:\([^)]+\)|\[[^\]]+\])", cells[1])) == 1
    assert re.search(PROFILE_RE, cells[3])
    if "authority unresolved" in rest.lower():
        unresolved += 1
control_owners = {}
for line in Path("docs/security/alpha-threat-model.md").read_text(encoding="utf-8").splitlines():
    if line.startswith("| `CTRL-"):
        cells = line.split("|")
        control_owners[cells[1].strip(" `")] = set(re.findall(r"#(\d+)", cells[3]))
owner_matches = 0
for key, rest in records:
    if key.startswith("CTRL-"):
        owners = set(re.findall(r"#(\d+)", rest.split("|")[2]))
        assert owners == control_owners[key]
        owner_matches += 1
assert owner_matches == 30
false_phrases = (
    "production ready", "fully accepted", "real asr operational",
    "live product ready", "100% complete", "all acceptance complete",
)
false_hits = []
for path in DELIVERABLES:
    low = prose(path).lower()  # strip fences so this deny-list quote cannot self-fail
    for phrase in false_phrases:
        if phrase in low:
            false_hits.append((str(path), phrase))
assert not false_hits
print({
    "MARKDOWN_LOCAL_LINKS": local_links,
    "EXTERNAL_URLS": len(external_links),
    "SOURCE_STABLE_IDS": len(source_ids),
    "INDEX_STABLE_IDS": len(indexed_stable),
    "IDX_NAV": len([k for k in counts if k.startswith("IDX-")]),
    "DUP_PRIMARY": 0,
    "UNRESOLVED_AUTHORITY": unresolved,
    "CTRL_OWNER_MATCHES": owner_matches,
    "FALSE_COMPLETE": false_hits,
    "AUDIT_PASS": True,
})
```

Result (fenced script bodies excluded from link/false-complete scans via `prose()`):
local links 564, external URLs 46, source/index stable IDs 130/130, IDX nav 70,
unresolved 0, CTRL owner matches 30, false-complete none, `AUDIT_PASS`. Rechecked
after this evidence append with the same counts.

#### Dependency / roadmap / merged-PR audit

Command: `uv run python /tmp/livecho-issue30-dependency-audit.py`

```python
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json, re, subprocess

NUMBERS = list(range(1, 20)) + [27, 28, 29, 30]
MERGED_PRS = [
    20, 21, 22, 23, 24, 25, 26, 32, 33, 34, 41, 42,
    44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54,
]

def capture(number):
    value = json.loads(subprocess.check_output([
        "gh", "issue", "view", str(number), "--repo", "Shuang-su/Livecho",
        "--json", "number,title,state,body,url",
    ], text=True))
    section = re.search(r"^## 依赖\s*\n(.*?)(?=^## |\Z)", value.pop("body"), re.M | re.S)
    value["dependencies"] = list(map(int, re.findall(r"#(\d+)", section.group(1)))) if section else []
    return value

roadmap = Path("docs/roadmap.md").read_text(encoding="utf-8")
expected = {}
for line in roadmap.splitlines():
    if re.match(r"\| \[#\d+\]\[i\d+\]", line):
        cells = line.split("|")
        number = int(re.search(r"#(\d+)", cells[1]).group(1))
        expected[number] = (cells[2].strip().upper(), list(map(int, re.findall(r"#(\d+)", cells[4]))))
assert set(expected) == set(NUMBERS)
with ThreadPoolExecutor(max_workers=4) as pool:
    captured = sorted(pool.map(capture, NUMBERS), key=lambda v: v["number"])
differences = []
for value in captured:
    got = (value["state"], value["dependencies"])
    if got != expected[value["number"]]:
        differences.append({"number": value["number"], "github": got, "roadmap": expected[value["number"]]})
proposal = json.loads(subprocess.check_output([
    "gh", "issue", "view", "31", "--repo", "Shuang-su/Livecho",
    "--json", "number,title,state,url",
], text=True))
assert proposal["state"] == "OPEN" and proposal["title"] in roadmap
for number in MERGED_PRS:
    value = json.loads(subprocess.check_output([
        "gh", "pr", "view", str(number), "--repo", "Shuang-su/Livecho",
        "--json", "number,state,mergedAt,mergeCommit,url",
    ], text=True))
    assert value["state"] == "MERGED" and value["mergeCommit"]["oid"]
print({"issues": len(captured),
       "direct_edges": sum(len(v["dependencies"]) for v in captured),
       "roadmap_differences": differences,
       "proposal_title_only": 1,
       "merged_prs_checked": len(MERGED_PRS),
       "AUDIT_PASS": not differences})
assert not differences
```

Result: 23 Issues, 62 direct edges, 0 roadmap differences, #31 title-only OPEN,
23 merged PRs checked (`#20`–`#26`, `#32`–`#34`, `#41`–`#42`, `#44`–`#54`),
`AUDIT_PASS`.

### Automated verification

| Exact command | Result | Date/tree |
| --- | --- | --- |
| `uv run python /tmp/livecho-issue30-index-audit.py` | `AUDIT_PASS`; local links 564; external 46; stable IDs 130; IDX 70; unresolved 0; CTRL owners 30; false-complete none | 2026-11-15 / `issue/30-requirements-index-impl` @ `c8ee4a1` + docs |
| `uv run python /tmp/livecho-issue30-dependency-audit.py` | `AUDIT_PASS`; 23 Issues; 62 edges; 0 roadmap diffs; 23 merged PRs | 2026-11-15 |
| `git diff --quiet origin/main -- docs/changes/30-requirements-evidence-index/intent.md docs/changes/30-requirements-evidence-index/spec.md docs/changes/30-requirements-evidence-index/plan.md` | Exit 0 (accepted artifacts unchanged) | 2026-11-15 |
| `git diff --check` / `git diff --cached --check` | Exit 0 | 2026-11-15 |
| `make artifacts` | `change artifacts: ok` | 2026-11-15 |
| `make verify` | Passed: Ruff; mypy 149 files; TS typecheck; pytest 935 passed (1 deselected); protocol Vitest 262; Railway Vitest 63; web Vitest 51; artifacts ok; protocol codegen ok; web build ok | 2026-11-15 |
| `git diff --name-only origin/main` | Exactly allowlisted four paths | 2026-11-15 |

### Remaining blockers (not claimed done)

- Product/runtime: real MLX/#5 ADR, #8 host/FFmpeg, live `BILI-ACQ-001`/rights,
  #9 `synthetic_mlx`, #10 wire/protocol minor/#29/#16, provider Railway environments,
  M2 identity/gateway, #27/#28. Index maintenance does not enable those capabilities.
- Process: independent human reviewer (plan step 8) and owner merge of this draft PR.
  No auto-close of Issue #30 from this change.

## 2026-11-21 — Index refresh for merged #12 and #27 work

Maintenance refresh under the accepted spec's "README and maintenance behavior" rule:
an owning Issue's later implementation or evidence change triggers review of its rows.
Base: `main` at `f62951f2b5a083610a92d155d28afa19e4159dbe`, which adds
[#56](https://github.com/Shuang-su/Livecho/pull/56)–[#59](https://github.com/Shuang-su/Livecho/pull/59)
to the previous `c8ee4a1` baseline. Branch: `issue/30-requirements-index-refresh`.
Accepted intent/spec/plan are not rewritten. The 2026-11-15 record above stays as
historical evidence for its own baseline.

### Author exposure and assignment

This record is committed before the index, README or roadmap is edited.

- Identity/role/date: StablEdge desktop agent working for @Shuang-su, Issue #30
  documentation implementer, 2026-11-21. Paths: the plan allowlist only
  (`docs/requirements-index.md`, `README.md`, `docs/roadmap.md`, this `evidence.md`).
- Assignment source: the owner asked the agent to keep advancing the repository and
  left the choice of next step to it. The agent chose this refresh because #30 has
  accepted artifacts, its deliverables state the `c8ee4a1` baseline, and `main` has
  since merged #12 and #27 work that the roadmap still reports as not implemented.
  This is authority to prepare the change, not owner approval of its contents.
- Repository inputs read at the base: `AGENTS.md`, `CONTRIBUTING.md`, the accepted #30
  spec and plan and this evidence file, `README.md`, `docs/roadmap.md`,
  `docs/requirements-index.md` (header, profiles, the first two tables, rows naming
  #12 or #27, the protocol/delivery and deployment tables, the discrepancy register
  and link definitions), `docs/changes/12-invite-only-auth/intent.md` and
  `evidence.md` plus its spec headings and acceptance criteria,
  `docs/changes/27-long-session-state/evidence.md` plus its intent deferral and
  non-goal sections and its spec headings and acceptance criteria, the test function
  names in `tests/auth/` and `tests/protocol/test_long_session.py`, the file lists of
  commits `878163e`, `1968239`, `8fbfa8a` and `f62951f`, and
  `docs/policy/independent-implementation.md` (dependency and pull-request gate
  sections). The four files of the unmerged `docs/changes/13-worker-invite-identity/`
  directory were read earlier the same day for [#60](https://github.com/Shuang-su/Livecho/pull/60);
  they are an unmerged proposal and supply no index authority.
- GitHub inputs read 2026-11-21, unauthenticated and read-only: the repository README
  page, the open Issue and pull-request lists, the #30 Issue page, the #60 page, and
  the REST Issue/pull lists used by the dependency audit below. That audit parses
  only the `依赖` section of #1–#19 and #27–#30. For #31 and #38 only number, title
  and state were read; their bodies were not printed, parsed or used.
- Exclusions: no reference repository, upstream source, research report, screenshot,
  model, dataset, audio or credential was opened or downloaded. No live service,
  provider or hardware was used. No normative source is edited.
- Independent reviewer: **pending**. Plan step 8 requires a separate reviewer; this
  author does not invent one. Owner review of the pull request supplies it.

### What changed

- `docs/requirements-index.md` — header baseline; two new evidence profiles, S12
  (`#offline-auth`) and S27 (`#offline-long-session`); nine rows: `IDX-INVITED-IDENTITY`
  and `IDX-LONG-SESSION` now point at their accepted specs and the new profiles,
  `IDX-ROLE-MATRIX`, `FLOW-ALLOW-010`, `CTRL-AUTHZ-DENY-BY-DEFAULT`, `CTRL-AUTH-EXPIRY`,
  `DATA-AUTH-BEARER` and `IDX-PROTOCOL-BOUNDS` keep their primary pointer and owners
  and gain a narrowly worded offline profile, and `IDX-WORKER-IDENTITY-STATS` notes
  the open artifact PR; three new discrepancy-register rows. No ID was added, removed
  or renamed, and no owner cell changed.
- `docs/roadmap.md` — snapshot date and commit; #12 planning state `closed`; fixture
  notes for #12, #13 and #27; a title-only paragraph for #38; two conditional-gate
  bullets; link references for #56 and #58–#60.
- `README.md` — baseline line, one bullet for the offline #12/#27 slices, and invited
  login added to the list of capabilities that are not established.

### Findings

- The roadmap reported #12 as `open` and "not implemented". GitHub closed #12 on
  2026-11-18 and `main` holds a memory-adapter implementation. The row now says both,
  and the register records that closed is not production authentication.
- The roadmap reported #27 as "not implemented". The protocol package holds minor 1.
  A search of `services/`, `workers/`, `apps/` and `tools/` for the minor-1 names
  found no consumer, which matches #27's stated deferral. The row says protocol only.
- #27's own evidence still reads "Artifact PR: Pending" although #56 merged. Recorded
  in the register for #27's owner; not edited here.
- Open Issue #38 was absent from the roadmap. The accepted #30 spec names only #31 as
  title-only. #38 is now listed by number, title and state, with nothing inferred.
  Whether it belongs in the dependency table is an owner decision.
- Not done by this refresh: the full manual source cross-check and selected capability
  traces of plan steps 7 and 8 were repeated only for the nine changed rows and the
  #12/#27 summaries. Every other row keeps its 2026-11-15 review.

### Exact ephemeral audits (not added to the repository)

Scripts were executed from `/tmp` only, with `uv` 0.12.1 and `pnpm` 11.21.0 taken from
temporary directories because the machine's own `uv` was 0.12.2. `gh` was not
installed, so the dependency audit uses unauthenticated read-only REST calls instead
of the `gh` commands in the 2026-11-15 record.

#### Index / link / ownership / scope audit

Command: `uv run python /tmp/livecho-issue30-index-audit.py`

The script is the 2026-11-15 index audit above with these exact differences:

- `BASE = "f62951f2b5a083610a92d155d28afa19e4159dbe"`, and the base assertion is
  `git merge-base origin/main HEAD == BASE`.
- `PROFILE_RE` also accepts `offline-auth` and `offline-long-session`.
- The changed-path set also includes `git ls-files --others --exclude-standard`.
- Every in-page anchor link used in the index must exist as an anchor in the index.
- A small `git(*args)` helper and assertion messages; no other logic change.
- The addition below, placed after the control-owner check.

```python
# Rows untouched by this refresh must be byte-identical to the base.
base_index = git("show", f"{BASE}:docs/requirements-index.md")
base_records = dict(re.findall(
    r"^\| ((?:IDX|DEC|FLOW|CTRL|DATA|THREAT|RISK|BILI|LIC|GATE)-[A-Z0-9-]+) — (.*)$",
    base_index, re.M,
))
assert set(base_records) == set(counts)
changed_rows = sorted(k for k, rest in records if base_records[k] != rest)
for key, rest in records:
    if key in changed_rows:
        old, new = base_records[key].split("|"), rest.split("|")
        assert old[0] == new[0] and old[2].split(";")[0] == new[2].split(";")[0], key
```

Here `git(*args)` is `subprocess.check_output(["git", *args], text=True)`. The last
assertion checks that each changed row kept its summary and its owner list.

Result: local links 581, external URLs 52, source/index stable IDs 130/130, IDX nav
70, duplicates 0, unresolved 0, CTRL owner matches 30, changed rows exactly the nine
named above, false-complete none, `AUDIT_PASS`.

#### Dependency / roadmap / merged-PR audit

Command: `uv run python /tmp/livecho-issue30-dependency-audit.py`

```python
from pathlib import Path
import json
import re
import urllib.request

REPO = "Shuang-su/Livecho"
NUMBERS = [*range(1, 20), 27, 28, 29, 30]
TITLE_ONLY = [31, 38]
MERGED_PRS = [
    20, 21, 22, 23, 24, 25, 26, 32, 33, 34, 41, 42,
    44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54,
    56, 57, 58, 59,
]
OPEN_PRS = [60]


def get(path):
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/{path}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "livecho-issue30-audit"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


items = get("issues?state=all&per_page=100&direction=asc")
assert len(items) < 100, "pagination needed"
issues = {v["number"]: v for v in items if "pull_request" not in v}
pulls = {v["number"]: v for v in get("pulls?state=all&per_page=100&direction=asc")}
assert len(pulls) < 100, "pagination needed"

unknown = sorted(set(issues) - set(NUMBERS) - set(TITLE_ONLY))

roadmap = Path("docs/roadmap.md").read_text(encoding="utf-8")
expected = {}
for line in roadmap.splitlines():
    if re.match(r"\| \[#\d+\]\[i\d+\]", line):
        cells = line.split("|")
        number = int(re.search(r"#(\d+)", cells[1]).group(1))
        expected[number] = (
            cells[2].strip().lower(),
            sorted(map(int, re.findall(r"\[#(\d+)\]\[i\d+\]", cells[4]))),
        )
assert set(expected) == set(NUMBERS), sorted(set(expected) ^ set(NUMBERS))

differences, edges, states = [], 0, {}
for number in NUMBERS:
    value = issues[number]
    section = re.search(r"^## 依赖\s*\n(.*?)(?=^## |\Z)", value["body"] or "", re.M | re.S)
    deps = sorted({int(n) for n in re.findall(r"#(\d+)", section.group(1))}) if section else []
    edges += len(deps)
    states[number] = value["state"]
    got = (value["state"], deps)
    if got != expected[number]:
        differences.append({"number": number, "github": got, "roadmap": expected[number]})

title_only = {}
for number in TITLE_ONLY:
    value = issues[number]
    title_only[number] = {"state": value["state"], "title_in_roadmap": value["title"] in roadmap}

merged = {}
for number in MERGED_PRS:
    value = pulls[number]
    assert value["state"] == "closed" and value["merged_at"], number
    merged[number] = value["merge_commit_sha"][:7]
open_prs = {n: (pulls[n]["state"], pulls[n]["merged_at"]) for n in OPEN_PRS}
other_open_prs = sorted(n for n, v in pulls.items() if v["state"] == "open" and n not in OPEN_PRS)

print(json.dumps({
    "issues": len(NUMBERS),
    "direct_edges": edges,
    "open": sorted(n for n, s in states.items() if s == "open"),
    "closed": sorted(n for n, s in states.items() if s == "closed"),
    "closed_at": {n: issues[n]["closed_at"] for n in (12,)},
    "roadmap_differences": differences,
    "title_only": title_only,
    "unknown_issue_numbers": unknown,
    "merged_prs_checked": len(merged),
    "merge_commits_56_59": {n: merged[n] for n in (56, 57, 58, 59)},
    "open_prs": open_prs,
    "other_open_prs": other_open_prs,
    "AUDIT_PASS": not differences and not unknown and all(
        v["state"] == "open" and v["title_in_roadmap"] for v in title_only.values()
    ),
}, ensure_ascii=False, indent=1))
```

The executed file also began with a docstring stating the same read limits. The Issue
list response contains every Issue body. The script reads the body only for the
numbers in `NUMBERS`, and only its `依赖` section.

First run, before the roadmap edit: one difference, #12 `closed` on GitHub against
`open` in the roadmap; #38 title absent from the roadmap; `AUDIT_PASS` false.

Final run: 23 Issues, 62 direct edges, 0 roadmap differences; open
#9/#11/#13–#19/#27–#30, closed #1–#8/#10/#12; #12 closed at `2026-11-18T03:42:19Z`;
#31 and #38 open with titles present; no unknown Issue number; 27 merged PRs checked,
with #56–#59 at `1968239`, `878163e`, `8fbfa8a`, `f62951f`; #60 open and unmerged; no
other open PR; `AUDIT_PASS`.

### Automated verification

| Exact command | Result | Date/tree |
| --- | --- | --- |
| `uv run python /tmp/livecho-issue30-index-audit.py` | `AUDIT_PASS`; local links 581; external 52; stable IDs 130; IDX 70; unresolved 0; CTRL owners 30; nine changed rows | 2026-11-21 / `issue/30-requirements-index-refresh`, final tree |
| `uv run python /tmp/livecho-issue30-dependency-audit.py` | `AUDIT_PASS`; 23 Issues; 62 edges; 0 roadmap diffs; 27 merged PRs; #60 open | 2026-11-21 / final tree |
| `git diff --quiet origin/main -- docs/changes/30-requirements-evidence-index/intent.md docs/changes/30-requirements-evidence-index/spec.md docs/changes/30-requirements-evidence-index/plan.md` | Exit 0 (accepted artifacts unchanged) | 2026-11-21 / final tree |
| `git diff --check` / `git diff --cached --check` | Exit 0 | 2026-11-21 / final tree |
| `LIVECHO_HEAD_REF=issue/30-requirements-index-refresh make artifacts` | `change artifacts: ok` | 2026-11-21 / final tree |
| `LIVECHO_HEAD_REF=issue/30-requirements-index-refresh make verify` | Exit 0: Ruff; format, 170 files; mypy 170 files; pytest 974 passed (1 deselected); protocol Vitest 314; Railway Vitest 63; web Vitest 51; artifacts ok; protocol codegen ok; web build ok | 2026-11-21 / tree before this section's result text |
| `git diff --name-only origin/main` | Exactly the four allowlisted paths | 2026-11-21 / final tree |

### Remaining blockers (not claimed done)

- Product/runtime: unchanged from the 2026-11-15 list, plus mail delivery, durable
  identity, restore rejection and sealed secrets for #12, and consumer wiring and
  long-run evidence for #27. This refresh enables none of them.
- Process: independent reviewer (plan step 8) and owner merge. This change references
  Issue #30 and must not close it.
