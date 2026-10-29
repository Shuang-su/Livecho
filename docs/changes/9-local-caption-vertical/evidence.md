# Evidence: Single local worker caption vertical

## Fixture-scope revision: exposure and sources — 2026-10-30

- Author: Codex GUI `/root/caption_author_astra_20261029`, independent requirements
  author; scope is this Issue's four Markdown artifacts only. Registered before edits
  to intent/spec/plan. Independent reviewer: `/root/subtitle_reviewer_terra_20261029`.
- Allowed inputs read: repository AGENTS.md, independent-implementation policy, all
  four current #9 artifacts, Makefile and live Issue #9 body/comments using
  `gh issue view 9 --json title,body,comments` (exit 0; no comments).
- Context contains local task instructions and memory registry gate/history notes,
  including a generic independently-authored design summary mentioning Danmakus;
  that summary is excluded from requirements. The policy and historical #9 evidence
  expose upstream names/license metadata and prior authors' exposure declarations.
  No upstream source, tests, fixtures, schema, configuration, documentation expression,
  screenshots, assets or reference implementation was opened or supplied. No known
  upstream contribution is present. No old research or reference repository was read.
- Assignment: documentation clarification from Livecho's existing mode split and the
  current user-authorized fixture-only phase. No implementation assignment or runtime
  authorization follows from this record. No external requirement was introduced.
- Current Issue #9 still asks for actual partial/final ASR. This revision accepts no
  such outcome: text-only fixtures and eventual final-only MLX remain distinct, and
  actual partial inference/latency acceptance remains open. Artifact adoption still
  requires independent review, CI and owner/delegated-owner merge.

### Verification for this revision

From this worktree, the following command exited 0, with `change artifacts: ok` and
`Fixture scope check: 5 local links; exactly four Issue 9 Markdown artifacts`:

```sh
make artifacts && git diff --check && /usr/bin/python3 -B - <<'PY'
from pathlib import Path
import re
import subprocess
root = Path('docs/changes/9-local-caption-vertical')
links = 0
for file in sorted(root.glob('*.md')):
    for target in re.findall(r'\]\(([^)]+)\)', file.read_text()):
        if '://' in target or target.startswith('#'):
            continue
        assert (file.parent / target.split('#', 1)[0]).resolve().is_file(), (file, target)
        links += 1
changed = set(subprocess.check_output(['git', 'diff', '--name-only'], text=True).splitlines())
assert changed == {str(root / name) for name in ('intent.md', 'spec.md', 'plan.md', 'evidence.md')}, changed
print(f'Fixture scope check: {links} local links; exactly four Issue 9 Markdown artifacts')
PY
```

`/usr/bin/python3 -B /Users/szmg/.codex/monitors/livecho-20261029/gui_gate.py`
returned exit 0, `work_allowed: true`, before reads, before specification edits and
before verification. Product code and tests are unchanged; no runtime suite, audio,
model or hardware execution was performed. Hosted CI and independent review of the
published revision are separate pending outcomes, not implied by these local checks.

## Publication reconciliation — 2026-10-25

The user authorized publishing the preserved local delivery `f8f99d0eb9337d85db727c78842b21e2b5b84dbe` as a draft.
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

Current Issue #9 requires partial/final on the single-worker path and measurements
of readable partial latency. This draft proposes a final-only first real path and
exercises partial/revision behavior through text fixtures. Fixture results cannot
satisfy real partial inference or its latency acceptance. This phased scope difference
requires an owner decision before artifact adoption and implementation. Publishing
the draft neither changes the Issue nor closes any missing acceptance item.

### Local publication verification

The following exact command ran from this Issue's worktree on 2026-10-25 and exited 0:

```sh
make artifacts && git diff --check && /usr/bin/python3 -B - <<'PY'
from pathlib import Path
import re
import subprocess
root = Path('docs/changes/9-local-caption-vertical')
links = 0
for file in sorted(root.glob('*.md')):
    for target in re.findall(r'\]\(([^)]+)\)', file.read_text()):
        if '://' in target or target.startswith('#'):
            continue
        assert (file.parent / target.split('#', 1)[0]).resolve().is_file(), (file, target)
        links += 1
allowed = {str(root / 'evidence.md'), str(root / 'intent.md')}
changed = set(subprocess.check_output(['git', 'diff', '--name-only', 'f8f99d0eb9337d85db727c78842b21e2b5b84dbe'], text=True).splitlines())
assert changed == allowed, changed
subprocess.run(['git', 'diff', '--exit-code', 'f8f99d0eb9337d85db727c78842b21e2b5b84dbe', '--', str(root / 'spec.md'), str(root / 'plan.md')], check=True)
print(f'Publication check: {links} local links; exact documentation scope; spec/plan unchanged')
PY
```

Observed output: `change artifacts: ok`; `Publication check: 5 local links; exact documentation scope; spec/plan unchanged`.
Only publication evidence and, for the new proposals, the Issue-access status in
intent were edited. Product code, tests and reviewed spec/plan bytes are unchanged;
no product suite or hardware/model/audio check was rerun for this bookkeeping batch.
The previous exact-code validation remains historical evidence. New-head hosted CI
will be read separately after publication.

Draft publication does not grant owner approval or authorize merge,
deployment, model/audio execution or a new quota-monitor round.


## Artifact approval

- Owning Issue: [#9](https://github.com/Shuang-su/Livecho/issues/9).
- Artifact PR: Draft proposal on this branch; owner approval remains pending.
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

The final review-record follow-up on 2026-10-23 ran `make artifacts`,
`git diff --check`, and `git diff --cached --check && git diff --cached --name-only`:
all exited 0, artifacts reported `change artifacts: ok`, and only this evidence file
was staged. Oct23 gate checks before/after returned exit 0, `work_allowed: true`.
No specification, other Issue artifact, product code or runtime verification changed.

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
- Reviewer confirmed clean exact head `240570eb855a8ba237eef7fc4a812b9cb4890d90`:
  read the complete `53b570e..240570e` spec/plan/evidence delta and ran
  `git diff --check 53b570e..240570e` (exit 0). All three P2 findings are resolved,
  with no remaining actionable documentation finding. Oct23 gates passed before/after
  review. The reviewer made no edits, external queries or test runs and did not rerun
  the author's artifact/link checks.
- Additional static review covered the accepted #3 handshake/error models and
  `negotiate_viewer`, plus #11 head `ff060d0` reconnect/fresh-resync/clear-on-disconnect
  rules. After valid viewer negotiation, existing `resync_required` with
  `retryable: true` can reject local admission before any ready message or new domain;
  no protocol field or meaning is added. #11's clear-and-no-cursor retry is compatible.
  The fixture's 1,000 ms mutable limit and 2,000 ms admission interval restrict its
  schedule; they do not guarantee that a client's retry succeeds.
- Implementation verification must cover error followed by close scheduling only one
  retry, without resetting the five-retries-per-outage budget, and the same-owner
  interleaving of final publication, a new partial and fresh admission. These refine
  acceptance of the existing contracts; they add no wire fields or runtime authority.
- This confirmation establishes documentation review only, not executable compatibility,
  UI behavior, model/host acceptance or actual audio ownership evidence.

## Deviations

GitHub unavailable; local commit and local PR title/body draft only.

## Historical unpublished PR draft — 2026-10-23

Superseded by the restored-access publication record above and the current GitHub PR
description. The following text preserves the original handoff and its access limits.

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
>
> Independent documentation review of `240570e` resolved all three reported P2
> findings with no remaining actionable documentation finding. Owner artifact approval
> and implementation/runtime evidence remain pending.

## Release and rollback evidence

Not deployed. No production/source/model/worker enrollment gate is enabled.

## Fixture-only independent review — 2026-10-30

- Independent reviewer: Codex GUI `/root/subtitle_reviewer_terra_20261029`.
  Read-only specification review of exact head
  `61009e06f20c29c2506356c6d3c829233ab1e87c`; result: PASS, reported by the reviewer
  through the coordinator. The reviewer did not modify author files.
- Reviewer source/exposure declaration: read AGENTS.md, independent-implementation
  policy metadata and historical records, Issues #9/#11 and Livecho specifications
  and deltas. Did not read reference repository contents, old research, external
  screenshots, reference summaries, or reference code/assets.
- Findings: fixture boundaries, endpoints and reason mapping agree. Actual model,
  audio and partial-inference acceptance remain incomplete. This is documentation
  review, not runtime verification or authorization to enable those paths.
- The coordinator independently verified the remote push of `61009e06`. The first
  ordinary push was rejected with `remote rejected (failed)`; an ordinary retry
  succeeded. No forced update was used.
- This follow-up changes only this evidence file. Exact verification command:
  `make artifacts && git diff --check && git diff --exit-code 61009e06f20c29c2506356c6d3c829233ab1e87c -- docs/changes/9-local-caption-vertical/intent.md docs/changes/9-local-caption-vertical/spec.md docs/changes/9-local-caption-vertical/plan.md`.
  Result: exit 0, `change artifacts: ok`; intent/spec/plan unchanged.
- Staged verification: `git diff --cached --check && git diff --cached --name-only`;
  exit 0, only `docs/changes/9-local-caption-vertical/evidence.md`.
  No code or runtime tests were rerun for this review record. Final hosted CI and
  owner/delegated-owner merge remain separate gates before implementation.
