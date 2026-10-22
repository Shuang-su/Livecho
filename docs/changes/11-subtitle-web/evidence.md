# Evidence: Subtitle companion Web/PWA

## Artifact approval

- Owning Issue: [#11](https://github.com/Shuang-su/Livecho/issues/11).
- Artifact PR: Not created; GitHub read failed with HTTP 403 account suspended.
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

Pending independent review of a stable commit.

## Deviations

GitHub unavailable: prepare a local commit and a local PR title/body draft only.

## Release and rollback evidence

Not deployed. Execution registry, model adoption and production controls remain closed.
