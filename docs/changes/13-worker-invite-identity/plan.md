# Implementation plan: Worker invite registration, device identity, and contribution statistics

## Order of work

1. **This pull request is documentation only.** Merge `intent.md`, `spec.md`,
   and `plan.md` before any worker-identity code. The diff is the four files in
   `docs/changes/13-worker-invite-identity/`. Do not close #13. Do not edit
   protocol, auth, worker, CI, secret, or production-config files in this
   pull request.
2. After owner merge, open a separate implementation branch from that `main`
   commit. The branch name must match `issue/<number>-<slug>` so the artifact
   check can read issue 13. Append a fresh implementer exposure record to
   `evidence.md` before editing Python. The requirements-author record in this
   file is not that record.
3. Add exactly the Ed25519 dependency named in Ed25519 verifier decision,
   with its lock entries, in the first implementation commit. Stop if owner
   review struck or replaced that name. Do not vendor an implementation, do
   not substitute another package, and do not widen the pin.
4. Add the memory adapter, distinct HMAC label, injected clock, and injected
   random bytes. Unit-test token display-once, verifier-only storage, 24-hour
   absolute expiry, single-use compare-and-set, public-key-only device rows,
   challenge replay, and revoke-without-account-change before mounting routes.
5. Mount the HTTP routes from the spec on `create_worker_identity_app`. Do not
   register them on `create_auth_app` or `create_local_vertical_app`. Do not
   require a cookie on `/health`, `/healthz`, or `/api/viewer/ws`. Admin and
   statistics routes call the existing `authorize` function.
6. Add `admit_hello`, `record_stats`, `record_health`, and `note_online` with
   the precedence and five-field response in the spec. `admit_hello` must call
   the existing `negotiate_worker` with the admin allowlist. Do not edit
   `packages/protocol/`.
7. Assert the audit stand-in for `capability_rejected`, `signature_invalid`,
   and `device_revoked`, and assert that those records omit tokens, nonces,
   signatures, public keys, and email.
8. Keep `LIVECHO_EMAIL_ENABLED=false`. Do not add secret names or values to
   `.env.example`. Do not add `db/migrations/`. Do not read `RESEND_API_KEY` or
   `LIVECHO_SESSION_SIGNING_KEY` from the environment. The HMAC key is an
   in-memory constructor argument in tests.
9. Confirm `git diff` does not touch `workers/mlx/`, the protocol package,
   CI workflows, Railway config, or #12 route behavior except imports of
   existing auth types and `authorize`. Append implementation commands to this
   issue's `evidence.md` only. Do not rewrite the merged intent, spec, or plan.
10. Open one implementation pull request for #13 only after that evidence is
    recorded. Per `CONTRIBUTING.md`, that later pull request is the one that
    closes #13. #14 and #17 stay in their own changes.

## Verification

**This artifact pull request:**

- `LIVECHO_HEAD_REF=issue/13-worker-invite-identity uv run python tools/check_change_artifacts.py`
- `LIVECHO_HEAD_REF=issue/13-worker-invite-identity make artifacts`
- `git diff --check`
- Local Markdown link check for the four new files
- `git diff --name-only origin/main` lists only those four files
- `make verify` from this branch, because `CONTRIBUTING.md` uses that entry
  point for the deterministic check and this change is documentation only

**Later implementation pull request:**

- `uv run pytest -q tests/worker_identity`
- A test that a stored enrollment row has no plaintext token and a device row
  has no private key
- A test that each of the eight small-order point encodings, an encoding with
  `y >= p`, and an encoding with the sign bit set while `x` is zero are
  rejected by `POST /api/worker/devices` with `422` and `invalid_body`, leave
  the token unused, and store no device
- A test that `R = identity, S = 0` does not verify for any device, because
  no such device can be enrolled
- A test that a signature whose `S` is not less than the group order `L` is
  rejected and consumes the challenge
- `uv tree --frozen` shows the verifier and only its named transitive
  packages as new entries
- A test that the second challenge verify returns `401` and the account status
  is unchanged after device revoke
- A test that a manifest mismatch returns `manifest_not_allowed` and an audit
  result of `capability_rejected`
- A test that a Hello `negotiate_worker` accepts for minor 1, including
  `protocol.epoch-rotation`, is admitted when the device proof and allowlist
  match
- A test that a statistics response has exactly the six keys in the spec and
  that a danmaku field is rejected
- A test that `create_local_vertical_app` still serves `/health` and
  `/api/viewer/ws` without a cookie and does not mount `/api/worker/`
- `make verify`
- `git diff --check`
- A scan of the diff for `RESEND_API_KEY=` values, session-key values, audio
  fixtures, and edits under `packages/protocol/` or `workers/mlx/`

Skipped live ingest, real ASR, CUDA, Resend, Railway provisioning, and
production-auth checks stay recorded as not run. They are not passes.

## Rollout and rollback

No flag, secret, or deployment changes in either pull request. The
worker-identity application stays unmounted by the local viewer app and by
Railway start commands. Public live viewing stays anonymous. Community-worker
audio stays synthetic. Rollback of the implementation reverts the
worker-identity module and its tests. Rollback of this documentation pull
request deletes the four new Markdown files and leaves runtime behavior
unchanged.

A later owner who stores devices in Postgres must replace the Issue #4
no-schema guard in that same change and must satisfy the existing restore
rules before production authentication. That store is not authorized here.

## Ed25519 verifier decision

Python 3.12's standard library does not verify RFC 8032 Ed25519, and
`pyproject.toml` does not already depend on a library that does. This
documentation pull request adds no dependency. Owner merge of this plan names
the package below. Owner review may strike or replace that name before merge;
the implementation then follows the merged text.

**Proposed package:** `cryptography==50.0.2`, runtime dependency in
`pyproject.toml`, through
`cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PublicKey` only:
`from_public_bytes` and `verify`. The implementation must not import
`hazmat` backends, OpenSSL bindings, or private modules directly.

| Fact | Value recorded 2026-11-21 from PyPI JSON metadata |
| --- | --- |
| Release | 50.0.2, uploaded 2026-09-30 |
| License expression | `Apache-2.0 OR BSD-3-Clause` |
| New transitive packages | `cffi` 2.1.1 (`MIT-0`), `pycparser` 3.12 (`BSD-3-Clause`) |
| Python 3.12 wheels | `cp311-abi3` for macOS arm64 and manylinux x86_64; no source build needed |
| Bundled native library seen in a local probe | OpenSSL 4.0.3 |

The implementation pull request's `uv.lock` is the authoritative digest set.
The table above is a review aid, not a lock. Adding the package still
requires the license-inventory and distribution review that
`docs/policy/independent-implementation.md` names. This plan does not make a
legal determination.

Why this package and not `pynacl==1.6.2` (`Apache-2.0`, libsodium):

- Both need `cffi` and `pycparser`, so the transitive set is the same size.
- Issue #16 must encrypt raw archives. `cryptography` already provides the
  authenticated encryption that change is likely to need, so the repository
  can stay at one native crypto dependency. #16 still decides its own
  primitive; this plan does not.
- `cryptography` publishes type annotations that pass the repository's
  `mypy --strict` setting without a stub package.

The known difference that matters here: the local probe showed that
`Ed25519PublicKey.from_public_bytes` accepts the identity point, and that
`R = identity, S = 0` then verifies for any message. libsodium rejects that
key. The spec therefore requires the application to reject small-order and
non-canonical public keys at enrollment, independent of the library. With
that rule, either package satisfies the spec. If the owner replaces the name
with `pynacl==1.6.2`, the spec rule and its tests still apply unchanged.

The verifier's only job is signature verification. The implementation must
not generate server keys with it, must not shell out, and must not download a
model or a binary at runtime. Tests may generate worker keys with it in
process memory only.

## Fixed bounds

Every other rule in the spec is fixed for Issue #13. That includes the route
list, HMAC label `livecho-worker-enrollment-v1`, 24-hour absolute token
lifetime, 120-second absolute challenge lifetime, the quota table, the
`ModelManifestRefV1` mapping of backend/model/revision/SHA, Hello binding
through the existing `worker_id`, the enrollment-time rejection of
small-order and non-canonical public keys, and the five statistic
definitions. Those
bounds are this spec's proposed contract. The issue body requires the
properties they implement and does not state each number or path. Owner merge
of this directory accepts them. A different value, a signature field on
`WorkerHelloV1`, self-service enrollment from Issue #31, or a published metric
outside the five named fields requires a new owner-merged artifact before code
that depends on that change.
