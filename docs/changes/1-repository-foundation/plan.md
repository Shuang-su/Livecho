# Implementation plan: repository and SDLC foundation

## Order of work

1. Create and assign GitHub Issue 1 with measurable acceptance criteria.
2. Add repository metadata, MIT license, language/runtime version files, and monorepo
   workspace manifests.
3. Add the four-file change-artifact convention, bootstrap artifacts, contributor guide,
   and concise `AGENTS.md` invariants.
4. Add GitHub Issue/PR templates, CODEOWNERS, and read-only CI.
5. Add a standard-library artifact validator and foundation tests.
6. Generate frozen Python and pnpm lock files with the declared toolchain.
7. Run `make bootstrap` and `make verify`, record evidence, inspect the complete diff,
   and open a pull request without merging it.
8. Configure labels and roadmap Issues; document branch-protection settings that require
   the verified CI check and prevent direct pushes.

## Verification

- `make bootstrap`
- `make verify`
- `git diff --check`
- `git status --short`
- Inspect the PR file list and confirm it contains no apps, services, workers, schemas,
  migrations, or runtime configuration.

## Rollout and rollback

The repository owner reviews and merges the pull request. If the foundation is not
acceptable, close the PR or revert its single merge commit; no runtime or data migration
exists.

## Open decisions

None. Product architecture choices remain in later Issues and are intentionally absent.
