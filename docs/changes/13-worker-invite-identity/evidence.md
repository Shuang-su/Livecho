# Evidence: Worker invite registration, device identity, and contribution statistics

## Artifact approval

- Artifact PR: Pending. This pull request is documentation only.
- Status: Proposed. Worker-identity code waits until the owner merges
  `intent.md`, `spec.md`, and `plan.md`. That merge names the Ed25519 package
  proposed in the plan, unless owner review replaces it first.
- Approved by/date: Pending @Shuang-su review and merge.
- Authoring base: `f62951f2b5a083610a92d155d28afa19e4159dbe` (`main`). That
  commit is the squash-merged Issue #12 implementation from PR #59.
- Branch: `issue/13-worker-invite-identity`.

## Requirements-author exposure and assignment

- Identity/role/date: Cursor cloud agent, independent author for
  `docs/changes/13-worker-invite-identity/**` only, 2026-11-20. This is
  authority to prepare the draft, not owner approval and not authority to
  implement.
- Assignment source: the task asked for a documentation-only contract for
  Issue #13. The task states that #3 and #6 are closed and that #12 is on
  `main` at `f62951f`. Implementation of enrollment, device keys, challenges,
  and statistics is out of scope for this pull request.
- Repository inputs read: `AGENTS.md`, `CONTRIBUTING.md`,
  `docs/changes/README.md`, the four `_template` files,
  `.github/pull_request_template.md`, `docs/roadmap.md` (the #13 row),
  `docs/requirements-index.md` (`IDX-WORKER-IDENTITY-STATS` and the #31 note
  in the #30 spec), `docs/policy/independent-implementation.md` (author
  exposure rule), `docs/security/data-lifecycle-and-deletion.md`
  (`DATA-AUTH-BEARER`, `DATA-WORKER-DEVICE`, the #13 ownership row),
  `docs/security/alpha-threat-model.md` (worker and auth controls),
  `docs/operations/incident-disable-and-recovery.md` (device revocation
  procedure), `docs/changes/3-protocol-v1-contract/spec.md` (Hello, manifest,
  capabilities, version policy), `docs/changes/6-local-mlx-worker/spec.md`
  (local `enroll` is not community enrollment),
  `docs/changes/12-invite-only-auth/intent.md`, `spec.md`, `plan.md`, and
  `evidence.md`, `tools/check_change_artifacts.py` (branch pattern and
  artifact-only rule), `Makefile` (`artifacts`, `verify`), `pyproject.toml`
  (no Ed25519 dependency), and the existing auth modules `policy.py`,
  `crypto.py`, `records.py`, and `app.py` (matrix actions and HMAC labels
  already on `main`).
- GitHub inputs read 2026-11-20: Issue #13 body and the 2026-09-26 owner
  comment that points at #31 and says that direction conflicts with the
  invite-only premise. Issue #31's body was not opened.
- External fact used: RFC 8032 names the Ed25519 signature algorithm the issue
  body already requires. No RFC text is copied. No sample key is copied.
- Exclusions: no reference repository, upstream worker source, test, fixture,
  schema, screenshot, or research summary was opened. No model, dataset,
  audio, or live credential was downloaded. No known upstream contribution is
  an input.
- Assignment decision: author this documentation artifact only. A fresh
  implementer exposure record, a named Ed25519 package, and a separate
  reviewer are required before the later implementation. Owner merge of
  intent, spec, and plan is required before that code.

### Second requirements-author revision (2026-11-21)

- Identity/role/date: StablEdge desktop agent working for @Shuang-su,
  requirements author for `docs/changes/13-worker-invite-identity/**` only,
  2026-11-21. Not owner approval and not authority to implement.
- Purpose: resolve the plan's open Ed25519 package decision into a named
  proposal, and close a key-validation gap found while evaluating it.
- Repository inputs read: `AGENTS.md`, `CONTRIBUTING.md`, the four files in
  this directory at `310bad0`, `pyproject.toml`, the package names in
  `uv.lock`, `Makefile`, `tools/check_change_artifacts.py` (function list
  only), and `docs/policy/independent-implementation.md`.
- GitHub inputs read 2026-11-21: the repository README, the open Issue list,
  and the PR #60 description. Issue #31's body was not opened.
- External inputs: PyPI JSON metadata (version, upload time, license
  expression, `requires_dist`, wheel names and digests) for `cryptography`,
  `pynacl`, `cffi`, and `pycparser`. No package source was read.
- Local probe, outside this repository: a throwaway virtual environment in
  `/tmp` with Python 3.12.13, `cryptography==50.0.2`, `pynacl==1.6.2`, and
  `mypy==1.17.1`. It checked the RFC 8032 section 7.1 TEST 1 vector held in
  process memory, a tampered message, an `S + L` signature, the identity
  public key, a 31-byte key, and `mypy --strict` on a ten-line verify helper.
  Results: TEST 1 verified with both packages; tampered message and `S + L`
  were rejected by `cryptography`; `cryptography` accepted the identity key
  and verified `R = identity, S = 0` for an arbitrary message; `pynacl`
  rejected that same input; the 31-byte key was rejected; `mypy --strict`
  reported no issues; `cryptography` ships `py.typed`. No vector, key, or
  probe file was written into the repository.
- Exclusions: no reference repository, upstream worker source, model,
  dataset, audio, or live credential was opened or downloaded.
- Changes made: the plan's Open decisions section became the Ed25519 verifier
  decision proposing `cryptography==50.0.2`; the spec gained the
  enrollment-time small-order and non-canonical public-key rejection, the
  `S < L` rule, two failure-table rows, and one acceptance sentence; the plan
  gained the matching tests; the intent and this file were aligned.

## Automated verification

Commands below were run from this worktree on 2026-11-20 against base
`f62951f`, on branch `issue/13-worker-invite-identity`. `uv` 0.12.1 was
installed into the user account because it was not on `PATH`. The checker is
the standard-library script CI runs. `make verify` ran before this result
table was inserted. The artifact, whitespace, link, and path commands were
run again after the table was written.

| Command | Result | Date/commit |
| --- | --- | --- |
| `LIVECHO_HEAD_REF=issue/13-worker-invite-identity uv run python tools/check_change_artifacts.py` | Exit 0. `change artifacts: ok`. | 2026-11-20 / documentation tree |
| `LIVECHO_HEAD_REF=issue/13-worker-invite-identity make artifacts` | Exit 0. `change artifacts: ok`. | 2026-11-20 / documentation tree |
| `make verify` | Exit 0. ruff check passed; ruff format, 170 files already formatted; mypy, no issues in 170 source files; pytest `974 passed, 1 deselected`; Railway vitest 63, protocol vitest 314, web vitest 51; `change artifacts: ok`; `protocol generated artifacts: ok`; web production build ok. | 2026-11-20 / tree before this table text |
| `git diff --check` | Exit 0. No whitespace errors. | 2026-11-20 / documentation tree |
| Local Markdown link check | Exit 0. `local links checked: 6`; `local links ok`. | 2026-11-20 / documentation tree |
| `git diff --name-only origin/main` and untracked files | Exit 0. Exactly the four files in this directory. | 2026-11-20 / documentation tree |

Second revision, 2026-11-21, on branch `issue/13-worker-invite-identity`
from `310bad0`:

| Command | Result | Date/commit |
| --- | --- | --- |
| `LIVECHO_HEAD_REF=issue/13-worker-invite-identity uv run python tools/check_change_artifacts.py` | Exit 0. `change artifacts: ok`. | 2026-11-21 / documentation tree |
| `git diff --check` | Exit 0. No whitespace errors. | 2026-11-21 / documentation tree |
| `git diff --name-only origin/main` and untracked files | Exit 0. Exactly the four files in this directory. | 2026-11-21 / documentation tree |
| `make bootstrap` then `LIVECHO_HEAD_REF=issue/13-worker-invite-identity make verify` | Exit 0. ruff check passed; ruff format, 170 files already formatted; mypy, no issues in 170 source files; pytest `974 passed, 1 deselected`; Railway vitest 63, protocol vitest 314, web vitest 51; `change artifacts: ok`; `protocol generated artifacts: ok`; web production build ok. | 2026-11-21 / tree before this table text |

The second-revision run used `uv` 0.12.1 and `pnpm` 11.21.0 from temporary
directories outside the repository, because the machine's own `uv` was
0.12.2 and the repository pins 0.12.1. No new local Markdown link was added.

`make verify` is the GitHub `Verify` workflow's local entry point. It was run
on this branch. Live enrollment, Resend, Railway provisioning, production
auth, MLX, CUDA, and live ingest were not run. A documentation-only tree has
no implementation verification to record.

## Manual or hardware evidence

Not applicable. This pull request does not enroll a device, sign a challenge,
call Resend, or run MLX, CUDA, live ingest, or a browser. No audio bytes were
created.

## Review findings

- 2026-11-21, requirements-author self-review: the original spec stored any
  32-byte public key. With the proposed verifier, a small-order key makes
  `R = identity, S = 0` verify for every challenge, so device proof would not
  require a private key. Resolved in the spec by an enrollment-time key rule
  that does not depend on the library.

Owner review is pending. This author does not merge
the pull request and does not close Issue #13.

## Deviations

None relative to the issue body premises. The #31 self-service direction is
recorded as not adopted. The branch is `issue/13-worker-invite-identity` so
the artifact lifecycle check can read issue 13. A `cursor/…` name fails that
check. Product code is intentionally absent. `docs/changes/README.md` and
`docs/requirements-index.md` are unchanged: the change README does not require
a new directory to be listed, and an artifact-only diff must stay under
`docs/changes/13-`.

## Release and rollback evidence

Not deployed. No production traffic, real email, live credential, production
auth, community-worker PCM, or CUDA runtime is enabled. Rollback of this pull
request deletes the four new Markdown files and leaves runtime behavior
unchanged.

## Implementer exposure and assignment

- Identity/role/date: Cursor cloud agent, implementer for Issue #13 worker
  invite registration, device identity, and contribution statistics,
  2026-11-21. This record is the pre-code assignment. It is not owner approval,
  not a license compatibility opinion, and not the post-implementation
  similarity review.
- Assignment source: the task asked to implement Issue #13 from `main` at
  `57236d26de3f9aadd88b55163963919364aff273` (squash-merged documentation PR
  #60). The accepted inputs are `intent.md`, `spec.md`, and `plan.md` in this
  directory. Those three files are not rewritten. The 2026-09-26 Issue #13
  comment that points at #31 is not adopted.
- Repository inputs read before Python edits: `AGENTS.md`, `CONTRIBUTING.md`,
  `.github/pull_request_template.md`, `Makefile`, `pyproject.toml`,
  `tools/check_change_artifacts.py` (branch pattern and the rule that an
  implementation must not rewrite accepted intent/spec/plan),
  `docs/policy/independent-implementation.md` (exposure rule, and the
  requirement to review a new dependency's lock, license inventory, and
  distribution obligations without treating that review as a legal
  conclusion), the four files in this directory, the Issue #12 modules
  `policy.py`, `crypto.py`, `records.py`, `app.py`, `store.py`, `service.py`,
  `config.py`, `bootstrap.py`, `redact.py`, and `auth/__init__.py`, the
  protocol modules `compatibility.py` (`negotiate_worker`), `errors.py`,
  `models.py`, `scalars.py`, and the synthetic golden hello/manifest values in
  `golden.py`, `local_vertical/service.py` and `config.py` (health and
  `/api/viewer/ws` stay session-free), `tests/auth/support.py`, and
  `tests/auth/test_boundaries.py`. The Issue #4 evidence license section was
  read only as an example of how an earlier change recorded a lock inventory.
- GitHub inputs: none opened in this assignment. Issue #13 and Issue #31 were
  not fetched. The #31 direction remains excluded by the accepted spec.
- External facts used: RFC 8032 is the public signature standard the issue and
  the accepted spec already name. The implementation uses the spec's stated
  checks (field prime `p = 2^255 - 19`, strict decoding, order dividing 8,
  sign bit when `x` is zero, and `S < L`). No RFC text is copied. No sample
  key, test vector, or library source is copied. PyPI metadata for the pinned
  package is recorded with the lock, after this exposure and only as
  inventory.
- Exclusions: no LAPLACE repository, reference-only source, test, fixture,
  schema, screenshot, or generated summary was opened. No model, dataset,
  audio, or live credential was downloaded. `workers/mlx/` was not opened.
  No known upstream contribution is an input.
- Assignment decision: implement the process-local worker-identity module,
  its tests, and the plan's exact `cryptography==50.0.2` pin. Do not edit
  `packages/protocol/`, `workers/mlx/`, CI workflows, Railway config,
  `.env.example`, or `db/migrations/`. Do not enable mail, production auth, or
  production traffic.
- Independent reviewer: a different post-implementation reviewer is still
  required before merge for provenance and similarity review. This author does
  not inspect reference-only upstream material, does not merge, and does not
  close Issue #13.

## Implementation verification

Recorded 2026-11-21 on branch `issue/13-worker-invite-identity-impl` from
`57236d26de3f9aadd88b55163963919364aff273`. `uv` 0.12.1 was installed for this
run because it was not on `PATH`. The first local `make verify` failed in
`test_change_artifacts_are_complete` because the snapshot's `origin/main` was
still `f62951f` and did not contain the merged Issue #13 documents. `git fetch
origin main` moved `origin/main` to `57236d2`. The results below are from the
rerun after that fetch. Live enrollment, Resend, Railway provisioning,
production auth, MLX, CUDA, and live ingest were not run. They are not passes.

| Command | Result | Date |
| --- | --- | --- |
| `uv run pytest -q tests/worker_identity` | Exit 0. `27 passed`. Includes token-versus-verifier storage, the eight small-order encodings plus `y >= p` and the sign-bit encoding, `R = identity, S = 0`, `S >= L`, challenge replay and revoke, `manifest_not_allowed` with audit `capability_rejected`, minor-1 `protocol.epoch-rotation` admission, the six statistics keys, and `create_local_vertical_app` / `create_auth_app` without `/api/worker/`. | 2026-11-21 |
| `uv tree --frozen` | Exit 0. New runtime dependency is `cryptography v50.0.2`, depending on `cffi v2.1.1`, depending on `pycparser v3.12`. No other new root dependency. | 2026-11-21 |
| `make bootstrap` then `make verify` | Exit 0. ruff check passed; ruff format, 187 files already formatted; mypy, no issues in 187 source files; pytest `1001 passed, 1 deselected`; Railway vitest 63, protocol vitest 314, web vitest 51; `change artifacts: ok`; `protocol generated artifacts: ok`; web production build ok. | 2026-11-21 |
| `git diff --check` | Exit 0 on the tracked diff. A trailing-whitespace scan of the new Python files found none. | 2026-11-21 |
| Diff path and secret scan | No path under `packages/protocol/`, `workers/mlx/`, `.github/`, `db/migrations/`, or `.env.example`. No `RESEND_API_KEY=` or `LIVECHO_SESSION_SIGNING_KEY=` assignment. The worker-identity package source does not read those names. | 2026-11-21 |

### Lock and license inventory

`uv.lock` is the authoritative digest set. The only packages added relative to
`57236d2` are `cryptography==50.0.2`, `cffi==2.1.1`, and `pycparser==3.12`.
Installed distribution metadata on this machine, read 2026-11-21, reports:

| Package | License-Expression | License files in the installed distribution |
| --- | --- | --- |
| `cryptography` 50.0.2 | `Apache-2.0 OR BSD-3-Clause` | `cryptography-50.0.2.dist-info/licenses/LICENSE`, `LICENSE.APACHE`, `LICENSE.BSD` |
| `cffi` 2.1.1 | `MIT-0` | `cffi-2.1.1.dist-info/licenses/LICENSE` |
| `pycparser` 3.12 | `BSD-3-Clause` | `pycparser-3.12.dist-info/licenses/LICENSE` |

These expressions match the table already in the merged plan. This change does
not vendor the wheels or copy those license files into the tree. It does not
copy LAPLACE or other reference-only material. No compatibility or
distribution-obligation conclusion is made here. A later distribution of the
locked wheels would need a separate review of those packages' own license
files. The post-implementation similarity reviewer named above is still
required before merge.

## Implementation limitations

The adapter is process-local memory. There is no `db/migrations/` change, no
backup, and no restore drill. `create_worker_identity_app` is unmounted by
`create_auth_app`, `create_local_vertical_app`, and the Railway start
commands. The HMAC key is a constructor argument. `LIVECHO_EMAIL_ENABLED`
stays false. Production auth, live ingest, real ASR, community-worker PCM,
wired danmaku or superchat, real MLX, and real CUDA stay off. This pull
request relates to Issue #13 and does not close it.
