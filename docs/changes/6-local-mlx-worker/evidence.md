# Evidence: Local MLX worker requirements

## Publication reconciliation — 2026-10-25

The user authorized publishing the preserved local delivery `c9d5b9ba56d4c44847d89c669b622c6c1961a1bb` as a draft.
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

Current Issue #6 requests `enroll`, `doctor`, `benchmark`, `run` and installation
through `uv tool`/`uvx`; this draft instead proposes `check`, `preflight`, `run`.
It also proposes a final-only first real path, whereas the Issue requires partial/final
transcription and partial revision acceptance. These are unresolved scope differences,
not completed requirements or an approved reduction. Owner reconciliation is required
before artifact adoption and implementation. This publication does not alter the Issue,
choose a command mapping or change the reviewed specification.

### Local publication verification

The following exact command ran from this Issue's worktree on 2026-10-25 and exited 0:

```sh
make artifacts && git diff --check && /usr/bin/python3 -B - <<'PY'
from pathlib import Path
import re
import subprocess
root = Path('docs/changes/6-local-mlx-worker')
links = 0
for file in sorted(root.glob('*.md')):
    for target in re.findall(r'\]\(([^)]+)\)', file.read_text()):
        if '://' in target or target.startswith('#'):
            continue
        assert (file.parent / target.split('#', 1)[0]).resolve().is_file(), (file, target)
        links += 1
allowed = {str(root / 'evidence.md'), str(root / 'intent.md')}
changed = set(subprocess.check_output(['git', 'diff', '--name-only', 'c9d5b9ba56d4c44847d89c669b622c6c1961a1bb'], text=True).splitlines())
assert changed == allowed, changed
subprocess.run(['git', 'diff', '--exit-code', 'c9d5b9ba56d4c44847d89c669b622c6c1961a1bb', '--', str(root / 'spec.md'), str(root / 'plan.md')], check=True)
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

- Owning Issue: [#6](https://github.com/Shuang-su/Livecho/issues/6).
- Artifact PR: Draft proposal on this branch; owner approval remains pending.
- Approved by/date: Pending @Shuang-su review and merge.
- Local base: `93d8b0a4b3e147ce0b7df903f118060117d56f0a` (`origin/main`).
- Documentation proposal only; no implementation, model or runtime approval.

## Author exposure and assignment, before drafting

- Author: OpenAI Codex GUI subagent `/root/subtitle_specs_20261023`, independent
  requirements author for `docs/changes/6-local-mlx-worker/**`, 2026-10-23.
- Independent read-only reviewer: `/root/audio_code_readiness`.
- Context: user goal of synthetic memory speech -> one local MLX worker -> subtitle
  companion, repository AGENTS and task boundaries. No root reference-research context
  was inherited. Allowed local inputs read: independent-implementation policy;
  #2/#3 intent/spec/plan; #5/#8 all four artifacts; change templates and checker,
  Makefile, package/workspace configuration, roadmap, Git metadata, #3 viewer models
  and a filename/line search for binary terminal handling. Focused reads replaced the
  initially truncated combined artifact output; no full #2/#3 evidence review claimed.
- Also authored the separate unmerged #11 proposal and read only its specifically
  authorized historical Issue body. That proposal is coordination context, not an
  accepted requirement for #6. #9 is a separate upcoming local proposal.
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
2026-10-23. No Issue #6 read was retried after that global authentication failure.
No authorized historical #6 body was available to this author. The local roadmap
names #6 "MLX worker CLI and local-fixture transcription"; audio fixtures remain
forbidden, so fixtures here mean synthetic text/metadata and fresh in-memory samples.
The proposal uses current user goals and accepted local artifacts. The remote Issue
body/comments and full Issue compliance remain unverified, not reconstructed.

## Automated verification

All commands ran in the isolated #6 worktree on 2026-10-23, except the absolute gate.

| Exact command | Result |
| --- | --- |
| `/usr/bin/python3 -B /Users/szmg/.codex/monitors/livecho-20261023/gui_gate.py` | Exit 0, `work_allowed: true`, before and after drafting |
| `make artifacts && git diff --check` | Exit 0, `change artifacts: ok`; Python 3.12.13 environment with 15 locked packages, no model/audio |
| `git add docs/changes/6-local-mlx-worker && git diff --cached --check && make artifacts && git diff --cached --name-only` | Exit 0; exactly four Issue #6 Markdown files |
| Local link check below | Exit 0; 5 local links, 0 broken |

```sh
/usr/bin/python3 -B - <<'PY'
from pathlib import Path
import re
root=Path('docs/changes/6-local-mlx-worker')
links=[]
for f in sorted(root.glob('*.md')):
    for target in re.findall(r'\]\(([^)]+)\)',f.read_text()):
        if '://' not in target and not target.startswith('#'):
            assert (f.parent/target.split('#')[0]).resolve().is_file(), (f,target)
            links.append(target)
print(f'local Markdown links: {len(links)} checked, 0 broken')
PY
```

No full runtime suite, model/audio, MLX or hardware check ran. Future plan commands are
requirements, not run evidence.

The 2026-10-23 review-record follow-up reran `make artifacts && git diff --check`
(exit 0, `change artifacts: ok`) and
`git diff --cached --check && git diff --cached --name-only`
(exit 0; only this evidence file). The Oct23 GUI gate exited 0 before
and after the batch. No specification or runtime change was made in this follow-up.

## Requirement source map

| Requirement | Allowed source and limit |
| --- | --- |
| One local MLX worker and synthetic memory speech | Current user goal and local roadmap; remote Issue #6 body unavailable |
| Versioned synthetic leases, manifests, final/ordering/terminal state | Accepted #3 spec and `models.py`/`binary.py`; no validator omission grants permission |
| Complete model report, final manifest and owner-approved model ADR | Accepted #5 spec; no model selected or measured by this proposal |
| Completed segments, sample/byte bounds, overlap and host proof | Accepted #8 and #2 specs; runtime evidence remains missing |
| No reference-derived implementation | Accepted independent-implementation policy |
| CLI, local-only endpoint, limits below inherited ceilings, no-resume and transaction proposal | Independent Livecho design choices, pending owner review and explicit compatibility gate |

Additional focused source read after assignment: accepted #3 `PcmLeaseState.accept`
and worker/lease/transcript models, to identify terminal accounting versus actual
allocation ownership. No reference implementation was inspected.

## Manual or hardware evidence

None. No MLX execution, model selection/acquisition, audio generation/download,
host privacy proof, device connection or public account action occurred. The execution
registry stays closed. Text-only contracts cannot establish working inference.

## Review findings

- Independent read-only reviewer `/root/audio_code_readiness` reviewed stable
  `32b7e30c1151e4b55d34bac0145461b9be05a84e` and the relevant accepted terminal code.
  One P2 gap was identified: a late inference completion must not commit terminal
  sequence/PTS before checking cancellation/expiry/generation. The proposal now requires
  one-owner atomic precommit revalidation and confirmed actual audio release, plus
  held-completion metadata race cases. Failed checks keep admission closed with no
  commit/ack/output.
- Reviewer confirmed clean revised head `a740c10e18f039173b7d934817f6aa6e24057e2f`:
  read the complete `32b7e30..a740c10` spec/plan/evidence delta and ran
  `git diff --check 32b7e30..a740c10` (exit 0). The P2 is resolved with no remaining
  actionable documentation finding. GUI gate checks passed before/after review.
  No tests were run; this confirmation does not replace executable compatibility or
  actual audio-ownership evidence.
- No direct irreconcilable v1 conflict was identified by static review. The explicit
  executable compatibility/actual ownership gate remains before real inference;
  document review is not runtime evidence. Reviewer made no edits and ran no tests.

## Deviations

GitHub unavailable; local commit and local PR title/body draft only.

## Historical unpublished PR draft — 2026-10-23

Superseded by the restored-access publication record above and the current GitHub PR
description. The following text preserves the original handoff and its access limits.

Title: `docs: propose local MLX worker contract for Issue #6`

Body:

> Proposes the intent, specification, implementation plan and evidence for one
> synthetic-only local MLX worker. The worker stays blocked without the complete #5
> report, approved final manifest and owner-approved model ADR, host audio proof and
> separate execution authorization. Defines final-only output, bounded ownership,
> cancellation and an explicit terminal-frame compatibility gate without changing v1.
>
> Documentation only; no feature code, model/audio download, execution or enablement.
> Remote Issue #6 body remains unverified because GitHub account authentication returns
> HTTP 403. Local artifact, link and whitespace results are recorded in evidence.
> Requests artifact review; does not close #6 or authorize runtime work by itself.

## Release and rollback evidence

Not deployed. No production/source/model/worker enrollment gate is enabled.
