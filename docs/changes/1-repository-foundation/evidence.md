# Evidence: repository and SDLC foundation

## Artifact approval

- Artifact/foundation PR: [#20](https://github.com/Shuang-su/Livecho/pull/20)
- Approved by/date: @Shuang-su, 2026-08-24 (explicit merge authorization)

## Automated verification

| Command | Result | Date/commit |
| --- | --- | --- |
| `make bootstrap` | Passed; project-enforced uv 0.12.1 and frozen pnpm installs completed | 2026-08-24, PR branch |
| `make verify` | Passed; ruff, repository-wide mypy, 39 pytest cases, base/result artifact and pnpm-native workspace gates | 2026-08-24, PR branch |
| `uv run pytest -q tests/foundation/test_repository_contract.py -k 'accepted_decisions or artifact_templates or lifecycle_rejects'` | Passed; 3 targeted rewrite-gate regressions | 2026-08-24, PR branch |
| `uv run pytest -q tests/foundation/test_repository_contract.py -k 'other_issue_artifacts or bootstrap_cannot_include or mypy_covers'` | Passed; 3 targeted Issue-scope and Python-discovery regressions | 2026-08-24, PR branch |
| `uv run pytest -q tests/foundation/test_repository_contract.py -k uv_version_matches_local_docs_and_ci` | Passed; exact local/CI uv pin alignment and fail-closed mismatch regression | 2026-08-24, PR branch |
| `uv run pytest -q tests/foundation/test_repository_contract.py -k 'symlink or case_sensitive'` | Passed; 7 filesystem, Git-index, ancestor, base-tree, and case-sensitive-name regressions | 2026-08-24, PR branch |
| `git diff --check` | Passed on the complete working-tree diff | 2026-08-24, PR branch |

## Manual evidence

- GitHub Issue: [#1](https://github.com/Shuang-su/Livecho/issues/1)
- Roadmap: Issues
  [#1](https://github.com/Shuang-su/Livecho/issues/1)–[#19](https://github.com/Shuang-su/Livecho/issues/19),
  labels, and M0/M1/M2 milestones created
- PR file-list review: 37 changed paths (36 foundation/documentation additions and the
  seed `.gitkeep` deletion); no product runtime directories
- GitHub Actions run:
  [Verify #32651929263](https://github.com/Shuang-su/Livecho/actions/runs/32651929263),
  passed on Ubuntu 24.04 with pinned Node 24-compatible action releases
- Main protection: pull request required, branch-current `verify` required, conversations
  resolved, administrators included, force-push/deletion disabled; squash is the only
  merge method and merged branches are deleted

## Review findings

The repository owner explicitly authorized squash merge on 2026-08-24 after required
checks and review threads pass. `@codex review` was requested on PR #20; automated
review remains advisory. Cursor Bugbot correctly found that the
foundation test covered only three AGENTS.md invariants. The test was expanded to cover
audio, arbitrary worker execution, credential isolation, raw archive access, protocol
idempotency, public-ingest boundaries, and CUDA mock-only status individually. Codex
review additionally identified that branch protection needed to be active before this
merge, implementation changes were not tied to artifacts already in the base, workspace
scripts could be silently absent, and auto-merge wording was too narrow. Protection and
repository-wide auto-merge disablement are active; the artifact and workspace gates now
have positive and negative tests. Final Codex re-review found three additional bypasses:
a fork head named `main`, configured workspace globs drifting from the checker, and
deletion of durable artifacts. Validation now uses the presence of a PR base instead of
trusting the head name, derives manifests from `pnpm-workspace.yaml`, and requires both
base artifacts and the resulting artifact tree to remain complete.
The final-head review additionally caught a pnpm/Python glob mismatch and mutable
accepted decisions during implementation. Workspace enumeration now delegates to pnpm,
and implementation PRs cannot rewrite merged intent/spec/plan artifacts; `evidence.md`
remains writable for verification results.
Cursor Bugbot's final-head review found that the accepted-decision rewrite check also
treated `_template` files as accepted Issue decisions. The check now applies the same
real Issue-directory pattern as the durable-artifact gate, and a regression confirms
that implementation PRs may update templates without making accepted Issue decisions
mutable.
The subsequent Codex review found that an implementation PR could still add a different
Issue's artifact directory and that mypy's closed input list omitted future runtime
Python roots. Lifecycle validation now rejects every changed numbered artifact directory
whose Issue differs from the branch, including during the Issue 1 bootstrap exception.
Mypy now discovers Python from the repository root while honoring the tracked
`.gitignore`; a synthetic `services/backend` type error is detected while ignored `dist`
output remains excluded.
The latest Codex review found that local bootstrap accepted any uv version while CI
installed 0.12.1. The project now requires that same exact version, the README documents
it, and a contract test keeps the project pin aligned with CI. A real temporary-project
regression confirms that a mismatched uv exits before lock processing.
The merge-gate review then found that Git symlinks could masquerade as required change
artifacts because filesystem reads followed their targets and base validation inspected
only path names. The full `docs/changes` tree now rejects non-regular entries, including
protected root components, templates, numbered directories, and auxiliary files.
Index-mode validation remains fail-closed when `core.symlinks=false`, including for
invalid directory names, and base acceptance considers exactly the four required regular
Git blobs before implementation begins. Evidence remains writable afterward so
implementation verification can be recorded. Regressions cover filesystem, index,
ancestor, template, auxiliary-file, invalid-slug, case-insensitive filesystem, and
implementation-base attacks.

## Deviations

The remote contained a seed `.gitkeep` commit but had no checked-out project files. A
second zero-file commit (`c137843`) was pushed to establish the local/remote `main`
tracking branch before opening the first pull request. No foundation or product file
bypassed review.

## Release and rollback evidence

No runtime behavior or infrastructure is deployed by this change.
