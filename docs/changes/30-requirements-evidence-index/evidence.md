# Evidence: Requirement authority and evidence index

## Artifact approval

- Artifact PR: Pending draft creation; this artifact does not close #30.
- Status: Proposed; approved by/date: Pending.
- Authoring base: `67fc6edc6ca2158fe640d73b9d5f8bf674513d6d` (`main`).
- Branch: `codex/issue-30-requirements-index-spec`.
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
  documentation implementation. Independent artifact review: pending.

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
| `git diff --name-only origin/main...HEAD` | Pending. | Artifact branch |
| Artifact scope/format audit below | Passed; four artifact paths, two Issue links, accepted sources unchanged. | 2026-10-02 / staged artifact tree |

Exact artifact scope/format audit:

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
- Independent review: pending. Hardware and provider checks are not required or performed.
- The final requirement inventory, formal index links/coverage audit, and README/roadmap
  consistency audit remain implementation work after artifact approval.

## Deviations

None. The requested short branch spelling was adjusted to the repository's required
`codex/issue-<number>-<slug>` pattern before authoring; no validator was weakened.

## Release and rollback evidence

Not deployed. This draft creates no runtime, infrastructure, policy authorization,
accepted risk, or source rights. It can be revised or closed without operational effect.
