# Evidence: Public accounts and self-service device boundaries

## Artifact approval

- Owning Issue: [#38](https://github.com/Shuang-su/Livecho/issues/38).
- Status: **Draft / proposed; repository-owner decision pending**.
- Artifact PR: Independent review complete; draft creation follows this record.
  The PR is linked from owning Issue #38; no merge or owner decision is recorded here.
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

## Deviations

The supplementary ADR draft stays inside this Issue's artifact directory so the existing
artifact-only lifecycle check remains applicable. Its eventual canonical ADR publication
and precise authoritative-document updates are a later owner-approved step.

## Release and rollback evidence

Not deployed. No API, schema, protocol, credential, role grant or operating mode changes.
