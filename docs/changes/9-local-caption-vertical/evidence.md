# Evidence: Single local worker caption vertical

## Artifact approval

- Owning Issue: [#9](https://github.com/Shuang-su/Livecho/issues/9).
- Artifact PR: Not created; authenticated GitHub reads are blocked by account suspension.
- Approved by/date: Pending @Shuang-su review and merge.
- Local base: `93d8b0a4b3e147ce0b7df903f118060117d56f0a` (`origin/main`).
- Documentation proposal only; no implementation, model or runtime approval.

## Author exposure and assignment, before drafting

- Author: OpenAI Codex GUI subagent `/root/subtitle_specs_20261023`, independent
  requirements author for `docs/changes/9-local-caption-vertical/**`, 2026-10-23.
- Independent read-only reviewer: `/root/audio_code_readiness`.
- Context: user goal of synthetic memory speech -> one local MLX worker -> subtitle
  companion, repository AGENTS and task boundaries. No root reference-research context
  was inherited. Allowed local inputs read: independent-implementation policy;
  #2/#3 intent/spec/plan; #5/#8 all four artifacts; change templates and checker,
  Makefile, package/workspace configuration, roadmap, Git metadata, #3 viewer models
  and a filename/line search for binary terminal handling. Focused reads replaced the
  initially truncated combined artifact output; no full #2/#3 evidence review claimed.
- Also authored separate unmerged #11 and #6 proposals. Only #11's explicitly
  authorized historical Issue body was read. Those proposals are integration context,
  not accepted authority; each Issue retains its own approval gate.
- Policy reading exposed repository names/license metadata and historical exposure
  declarations; no upstream source, tests, fixtures, schemas, configuration, comments,
  docs/assets/screenshots or expression-bearing summaries were inspected. No Issue #31
  expression, research report, reference repository or SDK implementation was read.
  No known upstream contribution is present in this task context.
- Memory exposure: Livecho registry notes about GUI/quota/owner gates and historical
  statuses, including names of #31/#38 and ModelScope gaps, with no reference
  expression. These are not current evidence or product requirements.
- Assignment decision: independent documentation only. Future code requires fresh
  exposure registration, accepted artifacts and isolated review. No model/audio or
  implementation dependency has been downloaded for this assignment.

## Source availability and limits

A single authenticated Issue #11 read in this documentation batch returned
`HTTP 403: Sorry. Your account was suspended (https://api.github.com/graphql)` on
2026-10-23. No Issue #9 read was retried after that global authentication failure.
No authorized historical #9 body was available to this author. The local roadmap
names #9 "Single-worker end-to-end caption pipeline". The proposal uses current user
goals and accepted local artifacts; the current remote Issue body/comments and complete
Issue compliance remain unverified, not reconstructed.

## Automated verification

All commands ran in the isolated #9 worktree on 2026-10-23, except the absolute gate.

| Exact command | Result |
| --- | --- |
| `/usr/bin/python3 -B /Users/szmg/.codex/monitors/livecho-20261023/gui_gate.py` | Exit 0, `work_allowed: true`, before and after drafting/checks |
| `make artifacts && git diff --check && git add docs/changes/9-local-caption-vertical && git diff --cached --check && git diff --cached --name-only` | Exit 0; `change artifacts: ok`; exactly four Issue #9 Markdown files; Python 3.12.13 with 15 locked packages, no model/audio |
| Local Markdown check below | Exit 0; 5 local links, 0 broken |

```sh
/usr/bin/python3 -B - <<'PY'
from pathlib import Path
import re
root=Path('docs/changes/9-local-caption-vertical')
links=[]
for f in sorted(root.glob('*.md')):
    for target in re.findall(r'\]\(([^)]+)\)',f.read_text()):
        if '://' not in target and not target.startswith('#'):
            assert (f.parent/target.split('#')[0]).resolve().is_file(), (f,target)
            links.append(target)
print(f'local Markdown links: {len(links)} checked, 0 broken')
PY
```

No full runtime suite, browser/worker, model/audio, host or end-to-end check was run.
Future plan commands are requirements, not run evidence.

For the 2026-10-23 P2 revision,
`make artifacts && git diff --check && git diff --name-only`
exited 0 (`change artifacts: ok`; only spec/plan/evidence changed).
The exact local link check above was rerun: 5 local links, 0 broken. After staging,
`git diff --cached --check && git diff --cached --name-only` exited 0 and again listed
only spec/plan/evidence. Oct23 GUI gate checks passed before and after the batch.
These results check documentation only; the new acceptance scenarios have not run.

## Requirement source map

| Requirement | Allowed source and limit |
| --- | --- |
| Memory synthetic speech -> one local MLX worker -> subtitle companion | Current user goal; roadmap names #9; current remote Issue body unavailable |
| Backend authority, source/production default-off, no persistent audio | Accepted #2 and #8 specs |
| Existing wire models, lease/epoch/seq/revision, current-cursor semantics and bounded protocol state | Accepted #3 spec/models; no new lifecycle or replay field |
| Actual model report, final manifest and owner-approved selection ADR | Accepted #5 spec; no coordinator completion or artifact merge substitutes for evidence |
| Completed-segment/final-only path, PTS/context and required runtime host evidence | Accepted #8 spec and user's explicit partial-unavailable scope |
| Local modes/endpoints/reasons, 60-second demo, bounded fan-out and no-resume source failure | Independently proposed Livecho choices, pending owner approval |

This author also read the accepted local `PcmLeaseState.accept` and worker models for
the #6 terminal boundary. The independent #6 review's finding about atomic precommit
generation/lease/expiry checks was applied here too. Separate #6/#11 draft interfaces
are coordinated but never treated as owner-accepted requirements.

## Manual or hardware evidence

None. No MLX execution, model selection/acquisition, audio generation/download,
host privacy proof, device connection or public account action occurred. The execution
registry stays closed. Synthetic text fan-out cannot establish working audio/ASR.

## Review findings

- Independent read-only reviewer `/root/audio_code_readiness` reviewed clean
  `53b570ee0c8dfa36d4be144e0f75f4b20e0e6660` and found three P2 documentation gaps.
  No edits or tests were performed; Oct23 gates passed before/after review.
- Worker output sequencing is clarified: backend supplies the lease start position,
  worker alone advances its shared heartbeat/stats/transcript sequence, and backend
  validates while separately advancing viewer timeline sequences.
- A new viewer cannot accept an unknown event's revision 2 after joining between its
  partial/final. The fixture now has one bounded mutable object, a fixed final deadline
  and admission interval; fresh/resync is refused until the current object finalizes.
  No cursor is prematurely issued and no old body, identity or revision is rewritten.
- Dropping queued text cannot make a later terminal status exact-next. Terminal sends
  now require a clear exact-next send boundary; any dropped-position gap or partially
  written message instead closes/aborts the viewer for #11's disconnect clearing.
  Planned metadata cases explicitly cover all three findings.
- Revised-head independent confirmation remains pending. These are documentation fixes,
  not executable compatibility, UI or actual audio evidence.

## Deviations

GitHub unavailable; local commit and local PR title/body draft only.

## Unpublished PR draft

Title: `docs: propose single-worker local caption vertical for Issue #9`

Body:

> Proposes the intent, spec, plan and evidence for a short synthetic memory speech ->
> one local MLX worker -> normalized viewer timeline. Separates text-only fixture
> demonstration from real inference, requires #5 model ADR/report and host/source
> evidence before execution, and fixes loopback routes, statuses, bounded fan-out,
> current-cursor resync, cancellation and timing attribution without changing v1.
>
> Documentation only; local artifact/link/whitespace outcomes are in evidence. No
> model/audio download, inference, platform access, account/device flow or deployment
> is enabled. Current Issue #9 body is unverified because GitHub authentication is
> blocked with HTTP 403. Requests artifact review; does not close #9 or claim real
> end-to-end acceptance.

## Release and rollback evidence

Not deployed. No production/source/model/worker enrollment gate is enabled.
