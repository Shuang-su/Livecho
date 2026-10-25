# Evidence: Subtitle companion Web/PWA

## Publication reconciliation — 2026-10-25

The user authorized publishing the preserved local delivery `ff060d0ffec19d89b8528ba02991299f5c5118ff` as a draft.
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

Current Issue #11 still requires the independent subtitle/status companion, bounded
session display delay, current-protocol recovery with explicit gaps, shell-only offline
caching and fast/slow viewer verification. The current proposal retains partial/final
UI behavior and discloses a final-only upstream demo. Upstream #6/#9 scope decisions
remain pending and cannot establish working model inference, browser acceptance or
Issue #11 completion. No UI or protocol code changes in this publication.

### Local publication verification

The following exact command ran from this Issue's worktree on 2026-10-25 and exited 0:

```sh
make artifacts && git diff --check && /usr/bin/python3 -B - <<'PY'
from pathlib import Path
import re
import subprocess
root = Path('docs/changes/11-subtitle-web')
links = 0
for file in sorted(root.glob('*.md')):
    for target in re.findall(r'\]\(([^)]+)\)', file.read_text()):
        if '://' in target or target.startswith('#'):
            continue
        assert (file.parent / target.split('#', 1)[0]).resolve().is_file(), (file, target)
        links += 1
allowed = {str(root / 'evidence.md'), str(root / 'intent.md')}
changed = set(subprocess.check_output(['git', 'diff', '--name-only', 'ff060d0ffec19d89b8528ba02991299f5c5118ff'], text=True).splitlines())
assert changed == allowed, changed
subprocess.run(['git', 'diff', '--exit-code', 'ff060d0ffec19d89b8528ba02991299f5c5118ff', '--', str(root / 'spec.md'), str(root / 'plan.md')], check=True)
print(f'Publication check: {links} local links; exact documentation scope; spec/plan unchanged')
PY
```

Observed output: `change artifacts: ok`; `Publication check: 4 local links; exact documentation scope; spec/plan unchanged`.
Only publication evidence and, for the new proposals, the Issue-access status in
intent were edited. Product code, tests and reviewed spec/plan bytes are unchanged;
no product suite or hardware/model/audio check was rerun for this bookkeeping batch.
The previous exact-code validation remains historical evidence. New-head hosted CI
will be read separately after publication.

Draft publication does not grant owner approval or authorize merge,
deployment, model/audio execution or a new quota-monitor round.


## Artifact approval

- Owning Issue: [#11](https://github.com/Shuang-su/Livecho/issues/11).
- Artifact PR: Draft proposal on this branch; owner approval remains pending.
- Approved by/date: Pending @Shuang-su review and owner merge.
- Base: `93d8b0a4b3e147ce0b7df903f118060117d56f0a` (`origin/main`, local ref).
- Scope: Proposed documentation only; no product implementation or enablement.

## Author exposure and assignment, recorded before drafting

- Author: OpenAI Codex GUI subagent `/root/subtitle_specs_20261023`, independent
  requirements author; assigned `docs/changes/11-subtitle-web/**` on 2026-10-23.
- Reviewer: Separate read-only GUI subagent `/root/audio_code_readiness`.
- Received context: repository AGENTS, the user's synthetic-memory-audio -> one local
  MLX worker -> subtitle companion goal, quota/owner gates, and task coordination.
  No root research conversation was inherited; the task supplied only the stated
  requirements and exclusions. No source material from reference repositories or
  SDK implementations was supplied or inspected.
- Read before drafting: AGENTS; `docs/policy/independent-implementation.md`; artifact
  templates/README and Makefile; accepted Livecho #2/#3 intent/spec/plan and #5/#8
  intent/spec/plan/evidence (truncated combined output was followed by complete focused
  reads of #3/#5/#8 and the tail of #2 spec); the artifact checker and #3 model fields;
  local Git metadata; only the authorized historical Issue #11 JSON body snapshot.
  The snapshot's parent research directory and all other files in it were excluded.
- Memory exposure: Livecho memory registry entries covering GUI-only execution,
  quota/owner gates, product invariants, and historical PR status. Those notes also
  named Issue #31/#38 and ModelScope contracts but provided no reference expression;
  they are not product-requirement or current-status evidence.
- Reading accepted policy exposed upstream repository names, license metadata and
  historical author exposure declarations. No linked upstream source, tests,
  fixtures, schemas, configuration, comments, documentation, screenshots or assets
  were opened. No reference-only product research, Issue #31 expression, generated
  reference summaries or upstream prior contributions are known in this task.
- Assignment decision: requirements only, from accepted Livecho artifacts and user
  goals. No implementation assignment. Any future implementation needs a fresh
  exposure declaration and the owner-merged artifacts.

## Source availability

`gh issue view 11 --json number,title,body,state,url` on 2026-10-23 exited 1:
`HTTP 403: Sorry. Your account was suspended (https://api.github.com/graphql)`.
No further GitHub API attempts were made. The permitted 2026-09-26 Issue #11 snapshot
contains the subtitle-only scope, display delay, reconnect, no-cache, and 20-viewer
criteria. It is historical, and current remote body/comments/approval were not
revalidated. Complete compliance with today's remote Issue is therefore not claimed.

## Automated verification

All commands run in the isolated #11 worktree on 2026-10-23 unless noted.

| Exact command | Result |
| --- | --- |
| `/usr/bin/python3 -B /Users/szmg/.codex/monitors/livecho-20261023/gui_gate.py` | Exit 0, `work_allowed: true`, `reason: active`, before work and after drafting/checks |
| `git log -1 --format='%H %s' origin/main` | Local base `93d8b0a4b3e147ce0b7df903f118060117d56f0a`; remote not fetched |
| `gh issue view 11 --json number,title,body,state,url` | Exit 1, suspended-account HTTP 403; no retry |
| `make artifacts` | Exit 0, `change artifacts: ok`; uv created Python 3.12.13 environment and installed 15 locked packages, no model/audio |
| `git diff --check` | Exit 0; staged files are checked separately before commit |
| `git add docs/changes/11-subtitle-web && git diff --cached --check && make artifacts && git diff --cached --stat && git diff --cached --name-only` | Exit 0; exactly the four Issue #11 Markdown files; no accepted-artifact or product changes |
| Local Markdown target check below | Exit 0; 4 local links, 0 broken |

Exact local link check:

```sh
/usr/bin/python3 -B - <<'PY'
from pathlib import Path
import re
root=Path('docs/changes/11-subtitle-web')
links=[]
for f in sorted(root.glob('*.md')):
    for target in re.findall(r'\]\(([^)]+)\)',f.read_text()):
        if '://' not in target and not target.startswith('#'):
            p=(f.parent / target.split('#')[0]).resolve()
            assert p.is_file(), (f,target)
            links.append((f.name,target))
print(f'local Markdown links: {len(links)} checked, 0 broken')
PY
```

No `make verify`, browser/E2E, model/audio or hardware check was run for this
documentation-only batch. Plan commands for future implementation are not run results.

## Requirement source map

| Requirement | Allowed source and limitation |
| --- | --- |
| Subtitle/status-only PWA, partial/final, gap/resync, shell-only cache, delay and 20 viewers | Historical owning Issue #11 body and current user goal; remote freshness pending |
| Backend authority, untrusted normalized rendering, no raw/audio/secret surface | Accepted #2 spec and independent-implementation policy at the recorded local base |
| Exact subprotocol/models/cursor/revision and 256/4,096 state bounds | Accepted #3 spec and local `ViewerCursorV1`/`ViewerReadyV1`/timeline models |
| Final-only completed-segment path; no invented partial audio protocol | Accepted #8 spec and current user scope; #5 latency/selection remains separately gated |
| Model adoption only after actual report and owner-approved ADR; host evidence required | Accepted #5/#8 specs; no measurements inferred from artifact merge |
| Delay range, queue caps, retry budget, view size and UI labels | Independently proposed Livecho design choices, pending owner approval |

The local Git history contains #5 artifact merge `df9f498` and #8 artifact merge
`93d8b0a`. Their original evidence still contains historical pending-approval wording;
this draft uses their presence in the supplied merged base as local acceptance context
and does not claim a newly verified remote approval or model/runtime approval.

## Manual or hardware evidence

None. No model/audio downloads, model inference, decoder, device, browser, public
account, platform input or production run has been executed for this artifact.

## Review findings

- Independent reviewer `/root/audio_code_readiness` read stable draft
  `56664e17d2b04ae71e0ca1d6bec6a6943126bf52` and found two P2 documentation issues.
  Corrected the capacity rule: existing identity updates/duplicates remain valid at
  4,096; only new identity 4,097 rejects before a fresh visible resync.
- Corrected browser integration scope: current protocol validator imports Node
  built-ins and cannot be imported as-is in Vite. #11 now includes minimum shared
  browser-entry packaging/adapters with unchanged Node API, strict parsing, JCS,
  sequencing/revision and golden results; no independent drift-prone UI validator.
- Author read the current validator imports and package exports to verify the finding.
  Reviewer made no edits or tests.
- Reviewer confirmed exact revised head `38a035c3343f66427a749c0e1de78434022f5367`:
  both findings resolved and no remaining actionable documentation finding. The
  read-only review checked status/head, the complete revision delta and
  `git diff --check 56664e1..38a035c` (exit 0), without rerunning the author's artifact,
  link or runtime tests. GUI gates passed before/after reviewer batches. Browser hash
  candidates must obey the specified bounded input path and reject old-generation
  completions during implementation; this is not current runtime evidence.

## Deviations

GitHub unavailable: prepare a local commit and a local PR title/body draft only.

## Historical unpublished PR draft — 2026-10-23

Superseded by the restored-access publication record above and the current GitHub PR
description. The following text preserves the original handoff and its access limits.

Title: `docs: propose subtitle companion Web/PWA for Issue #11`

Body:

> Proposes the intent, spec, plan and evidence for one room's subtitle/status companion
> page. Defines final-only disclosure, exact cursor/revision handling, visible gaps,
> bounded session-only display delay and static-shell-only offline caching. Includes
> the minimum browser-safe shared-validator packaging work without changing protocol
> semantics or golden outcomes. Danmaku/SC, public accounts and platform ingest stay
> outside this scope.
>
> Documentation only; artifact and whitespace/local-link checks passed as recorded in
> evidence. No UI, model, audio, hardware or production acceptance is claimed. GitHub
> 403 prevents current Issue-body verification; the permitted historical body was used.
> Requests owner artifact review; does not close #11 or authorize production execution.

## Release and rollback evidence

Not deployed. Execution registry, model adoption and production controls remain closed.
