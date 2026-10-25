# Evidence: Public accounts and self-service device boundaries

## Publication reconciliation — 2026-10-25

The user authorized publishing the preserved local delivery `b8f643a6dc2e000242d4401ccd8a929e6dc5c4b3` as a draft.
GitHub access is restored: the current owning Issue was read through the official
GitHub connector, and remote main remains `93d8b0a4b3e147ce0b7df903f118060117d56f0a`.
Earlier HTTP 403/unavailable statements below are historical records of October 23,
not a current access blocker. Original verification and independent reviews remain
attributed to their recorded authors and exact revisions.

Publication coordinator: Codex GUI `/root`, limited to repository/Issue status,
publication bookkeeping and recording unresolved scope. The coordinator retains its
prior reference-exposed role and makes no product implementation or requirement-design
changes. No reference expression, local quota logs, credentials or model/audio data
is introduced; existing independent author/reviewer assignments are unchanged.

Existing draft PR #39 is open at `445425757507c6a427f69c87c94042f3e86ff725`,
with no discussion/review entries returned. Current Issue #38 remains a proposed
architecture change. The revised account staging and retained identity-provider goals
are still proposals; history, quotas and adoption require owner decisions. The prior
independent content review at `72699849adfe76ad3fd98be9506fb372ec2d5dbf` is preserved.

### Local publication verification

The following exact command ran from this Issue's worktree on 2026-10-25 and exited 0:

```sh
make artifacts && git diff --check && /usr/bin/python3 -B - <<'PY'
from pathlib import Path
import re
import subprocess
root = Path('docs/changes/38-public-account-devices')
links = 0
for file in sorted(root.glob('*.md')):
    for target in re.findall(r'\]\(([^)]+)\)', file.read_text()):
        if '://' in target or target.startswith('#'):
            continue
        assert (file.parent / target.split('#', 1)[0]).resolve().is_file(), (file, target)
        links += 1
allowed = {str(root / 'evidence.md')}
changed = set(subprocess.check_output(['git', 'diff', '--name-only', 'b8f643a6dc2e000242d4401ccd8a929e6dc5c4b3'], text=True).splitlines())
assert changed == allowed, changed
subprocess.run(['git', 'diff', '--exit-code', 'b8f643a6dc2e000242d4401ccd8a929e6dc5c4b3', '--', str(root / 'spec.md'), str(root / 'plan.md')], check=True)
print(f'Publication check: {links} local links; exact documentation scope; spec/plan unchanged')
PY
```

Observed output: `change artifacts: ok`; `Publication check: 9 local links; exact documentation scope; spec/plan unchanged`.
Only publication evidence and, for the new proposals, the Issue-access status in
intent were edited. Product code, tests and reviewed spec/plan bytes are unchanged;
no product suite or hardware/model/audio check was rerun for this bookkeeping batch.
The previous exact-code validation remains historical evidence. New-head hosted CI
will be read separately after publication.

Draft publication does not grant owner approval or authorize merge,
deployment, model/audio execution or a new quota-monitor round.


## Artifact approval

- Owning Issue: [#38](https://github.com/Shuang-su/Livecho/issues/38).
- Status: **Draft / proposed; repository-owner decision pending**.
- Artifact PR: [#39](https://github.com/Shuang-su/Livecho/pull/39), open draft;
  no merge or owner adoption is recorded here.
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

## 2026-10-23 revision source declaration and assignment

- Author: `/root/account_roadmap_20261023`, independent document author assigned by
  `/root` on 2026-10-23 Asia/Shanghai. Scope is clarification of staging, retained
  roadmap goals, owning Issues and open decisions in these five Issue #38 files only.
  This declaration is committed before the content revision.
- Independent reviewer: `/root/audio_code_readiness`. `/root` coordinates and may
  review read-only; it does not supply reference-product expression to this author.
- Inputs read for this revision: AGENTS.md, the local independent-implementation policy,
  all five existing Issue #38 artifacts at
  `445425757507c6a427f69c87c94042f3e86ff725`, and the user's revision direction relayed
  in this assignment. The local Makefile was read only to select document checks.
- Actual exposure: the policy and existing evidence contain upstream names, revision,
  path/license metadata and prior authors' exposure records. This author has not read
  reference-product source, UI, screenshots, layouts, research reports, Issue #31
  expression or the coordinator's research. None is an input to this revision. No
  external source, model, audio, download or execution contract is introduced.
- Assignment decision: proceed with this isolated document scope using the approved
  user goals and existing project requirements. New reference-only expression would
  stop the affected authorship. This is not implementation or license/legal clearance.
- User direction: retain public accounts and self-service devices; email first is a
  stage, while Google/GitHub/Bilibili identity entry remains a long-term goal. Separate
  site identity, platform acquisition authorization and device identity. Prioritize
  personal devices and own contribution feedback before a voluntary public leaderboard;
  keep history independently authorized. The first subtitle loop does not depend on
  public accounts, platform authorization or rankings. Preserve every existing safety,
  capacity, revocation and current anonymous-ingest/invitation rule; document revision
  authorization is not owner adoption or enablement approval.
- Remote limitation reported by the coordinator: GitHub authentication currently returns
  HTTP 403 for a suspended account. This author did not re-query Issue #38 or PR #39;
  their current remote state is unverified. Work is local and reviewable only, with no
  push, merge, deployment or inference of owner approval.

## Local requirement register

| Input | Role in this proposal |
| --- | --- |
| User direction, 2026-10-05, recorded in [Issue #38](https://github.com/Shuang-su/Livecho/issues/38) | Public unified site accounts and own-device self-service, with platform acquisition authorization separate. Drafting only; no decision or rollout approval inferred. |
| [Issue #12 original body](https://github.com/Shuang-su/Livecho/issues/12) | Existing invited email, magic-link/session, roles, non-enumeration, idempotency and secret constraints. No comments read. |
| [Issue #13 original body](https://github.com/Shuang-su/Livecho/issues/13) | Existing administrator enrollment, key proof, revocation, manifests and non-financial own aggregates. No comments read. |
| [Issue #17 original body](https://github.com/Shuang-su/Livecho/issues/17) | Existing history, own-statistics, privileged controls, raw isolation and accessibility boundaries. No comments read. |
| [Issue #2 specification](../2-architecture-risk-boundaries/spec.md), [ADR 0001](../../architecture/adr/0001-alpha-modular-monolith.md) | Existing authority, role, no-secret, worker/ingest and recovery constraints; invitation clauses are mapped rather than rewritten. |
| [Threat model](../../security/alpha-threat-model.md), [data lifecycle](../../security/data-lifecycle-and-deletion.md) | Default-deny access, identity/devices, scoped revocation/deletion, audit and restore obligations. |
| [Bilibili public-ingest policy](../../policy/bilibili-public-ingest.md) | On 2026-10-05 Asia/Shanghai, read only the local `BILI-RIGHT-WORKER` / identified-invited-worker matching lines to resolve independent-review mapping feedback. No external links were followed; this requirement remains in force. |
| [Independent-implementation policy](../../policy/independent-implementation.md) | Source restrictions and author/reviewer separation. |

The quota numbers, 10-minute enrollment lifetime, recent-auth bound and recommended
independent-history grant are explicitly local proposed choices. They are not extracted
from a reference product or asserted to be vendor limits, measured capacity or legal rules.

## Automated verification

Author checks on 2026-10-05 Asia/Shanghai (2026-10-04 UTC), including the final content
snapshot `f508c415ab1e15cdd75af1127b6dd44fe8c9eb03`:

| Command / check | Actual result |
| --- | --- |
| `uv run python tools/check_change_artifacts.py` | Exit 0, `change artifacts: ok`, on the initial snapshot and after both review corrections. |
| `git diff --check`; `git diff --cached --check` | Exit 0, no whitespace errors before each content commit. |
| `git diff --check origin/main` | Exit 0 for the complete proposal including this evidence update. |
| `git diff --name-only origin/main...HEAD` | Exactly the five Issue #38 Markdown artifacts; no product code or existing authoritative documents. |
| `git status -sb`; `git rev-parse HEAD` | Clean at final content snapshot `f508c415ab1e15cdd75af1127b6dd44fe8c9eb03`. |
| Relative-link/file-inventory script below | Exit 0: `Document scope and relative links: 5 files, 9 local links passed` after the corrections (8 local links before the policy provenance row). |
| `/usr/bin/python3 /Users/szmg/.codex/monitors/livecho-20261005/gui_gate.py` | Separately checked before/after batches and at review boundaries; all observed exits 0, `work_allowed: true`, `reason: active`. |
| `git ls-remote origin refs/heads/main` | Still `93d8b0a4b3e147ce0b7df903f118060117d56f0a` before draft publication. |

Exact relative-link/file-inventory command, run from the worktree:

```sh
python3 - <<'PY'
from pathlib import Path
import re
root = Path('docs/changes/38-public-account-devices')
files = sorted(root.glob('*.md'))
links = 0
for file in files:
    for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', file.read_text()):
        if target.startswith(('https://', 'http://', '#')):
            continue
        assert (file.parent / target.split('#', 1)[0]).is_file(), (file, target)
        links += 1
assert {file.name for file in files} == {'intent.md', 'spec.md', 'plan.md', 'evidence.md', 'adr-proposal.md'}
print(f'Document scope and relative links: {len(files)} files, {links} local links passed')
PY
```

This batch changes documents only. No unchanged-code `make bootstrap` / `make verify`
rerun was requested or performed. No runtime, hardware, account, email, device or platform
test result is claimed. Later implementation Issues retain their full verification gates.

## Manual evidence and review findings

- Independent reviewer `/root/audio_code_readiness` reviewed all five proposal documents
  at `53b949811a95812f9e35cb9a3c921856a58f3670`, comparing the allowed accepted local
  requirements and original #12/#13/#17 bodies. No external reference browsing, file edits
  or product tests were performed. Reviewer independently ran artifact validation
  (exit 0), initial relative links (5 documents / 8 links), full-PR whitespace check
  (exit 0), and verified the five-file-only scope.
- Two documentation findings were corrected: clarify that every active verified role
  retains its own-account/device baseline while operator cross-account administration
  is denied; and map both existing invited-history clauses plus the retained
  `BILI-RIGHT-WORKER` requirement. Operator positive/negative scenarios and separate
  future worker-population rights/policy approval are now explicit.
- Reviewer confirmed the entire four-document correction delta at
  `f508c415ab1e15cdd75af1127b6dd44fe8c9eb03` with no remaining actionable finding in this
  bounded scope. Exact final reviewer checks: `git status --short` (empty),
  `git rev-parse HEAD`,
  `git diff 53b949811a95812f9e35cb9a3c921856a58f3670..f508c415ab1e15cdd75af1127b6dd44fe8c9eb03 -- docs/changes/38-public-account-devices`
  (all delta read), and
  `git diff --check 53b949811a95812f9e35cb9a3c921856a58f3670..f508c415ab1e15cdd75af1127b6dd44fe8c9eb03`
  (exit 0). Reviewer gate before/after both returned exit 0 / active. Final 9-link check
  belongs to the author, not the reviewer.
- Source isolation and scope were checked before assignment. This is a local-source
  document-contract review, not runtime verification, reference-expression similarity
  review, or license/legal clearance. These evidence-only additions do not change the
  reviewed intent/spec/plan/ADR content.

## 2026-10-23 revision verification and publication state

Source/assignment commit: `7c640f8`. The author then revised only the original intent,
spec, plan, ADR proposal and this evidence. The content revision clarifies staging and
retained goals; it does not adopt any pending architecture decision. No product code,
authoritative policy, model, audio or protocol changed.

| Command / check | Actual result on the local revision |
| --- | --- |
| `/usr/bin/python3 -B /Users/szmg/.codex/monitors/livecho-20261023/gui_gate.py` | Run separately before/after work batches and at review boundaries; every observed result so far is exit 0, `work_allowed: true`, `reason: active`. |
| `make artifacts` | Exit 0, `change artifacts: ok`. |
| `git diff --check 445425757507c6a427f69c87c94042f3e86ff725` | Exit 0; no whitespace errors. |
| Relative-link/file-inventory command above | Exit 0: `Document scope and relative links: 5 files, 9 local links passed`. |
| Boundary/scope comparison below | Exit 0: `Unchanged boundary sections: 6 passed`; changed paths equal the five original Issue #38 files. |

Exact boundary/scope comparison, run from this worktree:

```sh
python3 - <<'PY'
from pathlib import Path
import subprocess
root = Path('docs/changes/38-public-account-devices')
base = '445425757507c6a427f69c87c94042f3e86ff725'
protected = {
    'spec.md': [
        ('## Proposed quotas and exact admission semantics', '## Interfaces and compatibility'),
        ('## Failure modes and disable path', '## Acceptance criteria'),
        ('### DEV-38-001:', '### DEV-38-002:'),
        ('Registration establishes ownership.', '## Proposed quotas and exact admission semantics'),
        ('### AUTH-38-002:', '### DEV-38-001:'),
    ],
    'adr-proposal.md': [
        ('## Proposed permission matrix', '## Alternatives and consequences'),
    ],
}
count = 0
for name, ranges in protected.items():
    path = root / name
    old = subprocess.check_output(['git', 'show', f'{base}:{path}'], text=True)
    new = path.read_text()
    for start, end in ranges:
        assert old.split(start, 1)[1].split(end, 1)[0] == new.split(start, 1)[1].split(end, 1)[0], (name, start)
        count += 1
changed = subprocess.check_output(['git', 'diff', '--name-only', base], text=True).splitlines()
assert set(changed) == {str(file) for file in root.glob('*.md')}, changed
print(f'Unchanged boundary sections: {count} passed')
PY
```

The first local checks passed before the review handoff. On 2026-10-23 Asia/Shanghai,
independent reviewer `/root/audio_code_readiness` reviewed the complete five-file delta
from `445425757507c6a427f69c87c94042f3e86ff725` to clean content commit
`72699849adfe76ad3fd98be9506fb372ec2d5dbf` and reported no actionable finding.
The review confirmed retained provider-identity goals without capability claims, the
site/acquisition/device separation, private feedback before voluntary publication with
separate consent/withdrawal, and no added account/platform-authorization/ranking
dependency for the first subtitle loop. It found no change to the existing independent
history, quota, revocation, adoption, invitation or anonymous-ingest boundaries.

The reviewer's actual commands were `git rev-parse HEAD`, `git status --short` (empty),
`git diff 445425757507c6a427f69c87c94042f3e86ff725..72699849adfe76ad3fd98be9506fb372ec2d5dbf -- docs/changes/38-public-account-devices`
(complete delta read in batches),
`git diff --name-only 445425757507c6a427f69c87c94042f3e86ff725..72699849adfe76ad3fd98be9506fb372ec2d5dbf`
(only the original five files), and
`git diff --check 445425757507c6a427f69c87c94042f3e86ff725..72699849adfe76ad3fd98be9506fb372ec2d5dbf`
(exit 0). Separate October 23 gate calls before/after review batches returned exit 0.
The reviewer did not rerun the author's artifact/link/six-section checks, run product
tests, edit files, make external requests or inspect reference material. Those checks
remain attributed to the author. This evidence-only follow-up changes no reviewed
intent/spec/plan/ADR content; the author reran `make artifacts`, `git diff --check` and
`git diff --cached --check`, all exit 0, before committing it.

No runtime, provider, account, worker, capacity, real-audio or legal-clearance result is
claimed, and no unrelated `make verify` run was performed for these document-only
changes. Independent document review does not establish current remote PR status or
approve owner adoption, implementation or rollout.

### Historical prepared PR #39 update draft — 2026-10-23

The publication reconciliation above supersedes this draft's access-status statements.

Proposed title: `docs(issue-38): clarify public-account stages and retained identity goals`

Proposed body:

> Proposes public Livecho accounts and self-service own-device management for Issue #38.
> Email verification is the first account phase; Google, GitHub and Bilibili identity
> entry remain explicit long-term goals with separate reviewed contracts. Site identity,
> platform acquisition authorization and device identity remain independent, and history
> keeps the recommended separate grant.
>
> Personal devices and private contribution feedback precede a voluntary public
> leaderboard. The first subtitle loop has no dependency on public-account rollout,
> new platform acquisition authorization or rankings. Existing quotas, revocation,
> safety, invitation and anonymous-ingest rules remain unchanged by this pending proposal.
>
> Validation: `make artifacts`, whitespace, relative-link/five-file scope and six
> unchanged-boundary checks passed locally. Independent review of content commit
> `72699849adfe76ad3fd98be9506fb372ec2d5dbf` found no actionable issue; the reviewer
> separately verified the complete five-file delta and whitespace. No product code or
> runtime capability changed; owner adoption remains pending and no rollout is authorized.

This is a local publication draft. The reported HTTP 403 account suspension prevents
current Issue #38/PR #39 status verification; no remote update, push, merge or deployment
was attempted in this revision.

## Deviations

The supplementary ADR draft stays inside this Issue's artifact directory so the existing
artifact-only lifecycle check remains applicable. Its eventual canonical ADR publication
and precise authoritative-document updates are a later owner-approved step.

## Release and rollback evidence

Not deployed. No API, schema, protocol, credential, role grant or operating mode changes.
