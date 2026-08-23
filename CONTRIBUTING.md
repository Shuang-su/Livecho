# Contributing

## Change lifecycle

1. Create or select a GitHub Issue with outcome, non-goals, dependencies, risks, data
   impact, and executable acceptance criteria.
2. Add `docs/changes/<issue>-<slug>/intent.md`, `spec.md`, and `plan.md` in an artifact
   pull request.
3. Wait for the repository owner to merge that artifact pull request.
4. Implement on a separate branch and record exact commands and results in
   `evidence.md`.
5. Open an implementation pull request that closes the Issue and explains every
   deviation from the accepted artifacts.

Issue 1 is the bootstrap exception: its artifacts and repository foundation share one
pull request, and that pull request contains no product behavior.

## Required checks

Run the same deterministic entry point used by CI:

```sh
make bootstrap
make verify
```

Hardware-specific MLX checks never run for untrusted pull requests. They use an
explicitly approved manual workflow on a trusted Apple Silicon machine.

## Branches and commits

- Use `codex/issue-<number>-<slug>` or `issue/<number>-<slug>`.
- Keep generated schemas and lock files in the same commit as their source changes.
- Do not commit secrets, account cookies, playback tokens, raw audio, model weights, or
  production exports.
- Do not merge your own automation output without reviewing the diff and evidence.
