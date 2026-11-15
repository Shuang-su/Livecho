# Evidence: Local MLX worker artifacts

## Artifact approval

- Artifact PR: Pending (this documentation draft)
- Approved by/date: Pending @Shuang-su review and merge
- Base: `main` at `7c1043dee6db3f7872c6c4293cfa9e1485ba1a82` (includes squash-merged #8
  control plane). Owning Issue #6 reread 2026-11-15.
- Branch: `issue/6-local-worker-spec`

## Prior art (not approval)

Closed draft [#40](https://github.com/Shuang-su/Livecho/pull/40) on
`codex/issue-6-local-worker-spec` (published head `b3f7c7e`) proposed
`check`/`preflight`/`run` and a final-only-first product path, and itself recorded those
as unresolved mismatches vs Issue #6. That draft is **prior art only**—not an accepted
spec, not runtime evidence, and not model-selection approval. Useful ideas retained
after reconciliation: empty execution registry, stale-completion / terminal ownership
gate, loopback-only endpoint registry, and separation of contract doubles from trusted
MLX runs.

## Scope reconciliation (Issue vs #40)

| Topic | Issue #6 (normative for this draft) | Closed #40 | This artifact |
| --- | --- | --- | --- |
| CLI | `enroll`, `doctor`, `benchmark`, `run` + `uv tool`/`uvx` | `check`, `preflight`, `run` | Follow Issue names; map enroll=local config only (not public signup); doctor=diagnostics; benchmark=link/#5 blocked harness; run=gated |
| Partial/final | Fixture produces legal partial/final; protocol revision rules | Final-only product path | Fixture **must** emit legal partial→final; real MLX may be final-only + `partial_unavailable` until proven; never fabricate partials (aligns with accepted #9) |
| Model selection | Approved manifest digests | Require #5 ADR/report | Unchanged: no implied selection without ADR |
| Implementation in artifact PR | Forbidden until merge | Docs only | Docs only |

## Requirements-author exposure and provenance

- Author: Cursor Auto (cloud agent), 2026-11-15.
- Livecho inputs: AGENTS.md, CONTRIBUTING.md, owning Issue #6, change templates and
  artifact checker, accepted Issue #2/#3/#5/#8/#9 intent/spec (and #5/#8 evidence for
  gate status), protocol `TranscriptSegmentV1` / worker hello/lease prose, closed #40
  trees as prior art only.
- No model download, MLX execution, paid API, user-machine access, audio capture, or
  fabricated CER/RTF numbers were performed for this documentation batch.

## Automated verification

| Exact command | Result | Date/tree |
| --- | --- | --- |
| `make artifacts` | Exit 0; `change artifacts: ok` | 2026-11-15 / docs worktree on `7c1043d` |
| `git diff --check` | Exit 0; no whitespace errors | 2026-11-15 |
| `make verify` | Exit 0; Ruff/mypy/TypeScript ok; `880 passed, 1 deselected`; protocol 262 + Railway 63 + web 51 Vitest; artifact/protocol checks and build ok | 2026-11-15 |
| Local Markdown link check | 7 relative/absolute refs inspected; 0 broken | 2026-11-15 |
| `git diff --cached --name-only` | Exactly four files under `docs/changes/6-local-mlx-worker/` | 2026-11-15 |

## Manual or hardware evidence

None. No decoder, MLX, audio, or doctor-on-Apple-Silicon run is claimed by this PR.

## Review findings (critical review before return)

- **CLI consistency:** Issue names restored; renaming to #40's `check`/`preflight` would
  silently narrow operator surface—rejected.
- **Partial truth:** Fixture partials ≠ model partials; final-only real providers must
  declare unavailability rather than invent revisions—aligned with #9.
- **Gate consistency:** Real `run` still requires #5 ADR/report, #8 host/audio clearance,
  and a closed-by-default execution registry; empty registries must not be populated in
  the docs PR.
- **Owner-only ambiguity (recommendation):** Exact ADR/manifest identities and the date
  a real adapter becomes partial-capable remain owner evidence decisions. Recommend
  merging this contract now so implementation can land Linux-safe fixture/doctor work
  without waiting for hardware, while keeping real inference blocked.

## Deviations

Uses branch `issue/6-local-worker-spec` (repository-accepted `issue/<n>-<slug>` form).
Directory slug `6-local-mlx-worker` matches the prior draft path for continuity.
No product code, protocol edit, or production enablement.

## Release and rollback evidence

Not deployed. No production/source/model/worker cloud enrollment gate is enabled.
