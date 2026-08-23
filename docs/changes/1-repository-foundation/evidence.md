# Evidence: repository and SDLC foundation

## Artifact approval

- Artifact/foundation PR: [#20](https://github.com/Shuang-su/Livecho/pull/20)
- Approved by/date: Pending repository-owner merge

## Automated verification

| Command | Result | Date/commit |
| --- | --- | --- |
| `make bootstrap` | Passed; frozen uv and pnpm installs completed | 2026-08-24, PR branch |
| `make verify` | Passed; ruff, mypy, 18 pytest cases, base-artifact/workspace gates, pnpm checks | 2026-08-24, PR branch |
| `git diff --check` | Passed on the complete staged diff | 2026-08-24, PR branch |

## Manual evidence

- GitHub Issue: [#1](https://github.com/Shuang-su/Livecho/issues/1)
- Roadmap: Issues
  [#1](https://github.com/Shuang-su/Livecho/issues/1)–[#19](https://github.com/Shuang-su/Livecho/issues/19),
  labels, and M0/M1/M2 milestones created
- PR file-list review: 36 foundation/documentation files; no product runtime directories
- GitHub Actions run:
  [Verify #32651929263](https://github.com/Shuang-su/Livecho/actions/runs/32651929263),
  passed on Ubuntu 24.04 with pinned Node 24-compatible action releases
- Main protection: pull request required, branch-current `verify` required, conversations
  resolved, administrators included, force-push/deletion disabled; squash is the only
  merge method and merged branches are deleted

## Review findings

Owner review is pending. `@codex review` was requested on PR #20; automated review is
advisory and cannot approve or merge the change. Cursor Bugbot correctly found that the
foundation test covered only three AGENTS.md invariants. The test was expanded to cover
audio, arbitrary worker execution, credential isolation, raw archive access, protocol
idempotency, public-ingest boundaries, and CUDA mock-only status individually. Codex
review additionally identified that branch protection needed to be active before this
merge, implementation changes were not tied to artifacts already in the base, workspace
scripts could be silently absent, and auto-merge wording was too narrow. Protection and
repository-wide auto-merge disablement are active; the artifact and workspace gates now
have positive and negative tests.

## Deviations

The remote contained a seed `.gitkeep` commit but had no checked-out project files. A
second zero-file commit (`c137843`) was pushed to establish the local/remote `main`
tracking branch before opening the first pull request. No foundation or product file
bypassed review.

## Release and rollback evidence

No runtime behavior or infrastructure is deployed by this change.
