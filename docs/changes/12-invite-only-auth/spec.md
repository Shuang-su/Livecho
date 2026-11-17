# Specification: Invite-only magic-link authentication and roles

Normative terms **must**, **must not**, and **may** apply to the later Issue #12
implementation. This document does not enable that implementation. Issues #13,
#16, and #17 must call this contract's authorization decision for the actions
assigned to them below. They must not define a second role or a second session.

Accepted constraints that this spec uses without rewriting:

- Role boundaries and deny-by-default in
  [the #2 spec](../2-architecture-risk-boundaries/spec.md) and
  [the threat model](../../security/alpha-threat-model.md)
- Bearer lifetimes and verifier-only storage in
  [the data lifecycle](../../security/data-lifecycle-and-deletion.md)
  (`DATA-ACCOUNT-IDENTITY`, `DATA-AUTH-BEARER`, `CTRL-AUTH-EXPIRY`)
- Sealed `RESEND_API_KEY` and `LIVECHO_SESSION_SIGNING_KEY` slots in
  [the Railway secret inventory](../../operations/railway-secrets.md)

The owner comment on Issue #12 (2026-09-26) is an unapproved pointer to Issue
#31. It is not an input that adds registration, OAuth, or account linking.

## Behavior

### Actors

| Principal | How it is established |
| --- | --- |
| Anonymous | No valid session cookie |
| `viewer` | Invited account whose current role is `viewer` and whose status is `active` |
| `contributor` | Same, with role `contributor` |
| `operator` | Same, with role `operator` |
| `admin` | Same, with role `admin` |

There is no public registration. The only application roles are those four
strings. Repository owner is not a fifth role and is not granted by any route
in this contract. One account has one role. Roles are not a ladder: an operator
does not receive contributor statistics, and a contributor does not receive
room control.

Account status is `invited`, `active`, or `disabled`. A disabled account matches
no authenticated principal. The server loads the role and status from the
account row on every authenticated request. The cookie must not contain the
role, the email, or a signed claim of either.

### Email normalization

The mail parser accepts one string after trimming leading and trailing ASCII
whitespace. It rejects the address when any of the following is true:

- the trimmed value is longer than 254 characters, or empty;
- it contains ASCII whitespace or a code point above 127;
- it does not contain exactly one `@`;
- the local part is empty or longer than 64 characters;
- the domain is empty or longer than 253 characters, lacks a `.`, starts or
  ends with `.`, or contains `..`.

The stored and compared value is the trimmed address with the local part and
the domain case-folded to lowercase. Two requests that case-fold to the same
value are the same address. The implementation must not strip plus-tags or
otherwise fold distinct mailboxes together.

### Invite allowlist

`POST /api/auth/invites` with exactly `{"email":"<string>","role":"<role>"}`
is admin-only.

- A new normalized address creates an `invited` account with that role and
  returns `201` and `{"account_id","email","role","status"}`.
- The same address and the same role returns `200` and the same shape. It does
  not create a second row and does not send mail.
- The same address with a different role returns `409` and
  `{"error":"role_conflict"}`. The stored role stays unchanged. Role change is
  the separate route below.
- A disabled account returns `409` and `{"error":"account_disabled"}`.
- A role outside the four strings, a non-object body, a missing key, or an
  extra key returns `422` and `{"error":"invalid_body"}`.
- A syntactically invalid email returns `422` and `{"error":"invalid_email"}`.

`POST /api/auth/accounts/{account_id}/role` with exactly `{"role":"<role>"}`
is admin-only. It changes the role of another account. The caller must not
change their own role (`409`, `{"error":"self_role_change"}`). A change that
would leave zero `admin` accounts returns `409` and `{"error":"last_admin"}`.
An unknown account id returns `404` and `{"error":"not_found"}` only after the
caller has already been authorized as admin. A non-admin receives `403` and
`{"error":"forbidden"}` with no existence check in the response.

`POST /api/auth/accounts/{account_id}/disable` is admin-only and returns `204`.
The caller must not disable their own account (`409`,
`{"error":"self_disable"}`). Success sets `disabled`, revokes every session of
that account, and expires every unused magic-link row for that account. A
disabled account cannot receive a new link.

`GET /api/auth/invites` is admin-only. It returns the accounts as a JSON array
of `{"account_id","email","role","status"}` sorted by `account_id`. It is the
only collection route that returns email addresses, and only to an admin.

The first admin is not created over HTTP. A local operator function inserts one
`active` admin only when the account store is empty, and it fails if any
account already exists. It does not send mail, does not print the address, and
is not invoked by a Railway start command. Tests call it inside the test
process. Production invocation is a later owner decision and is outside this
artifact.

### Magic-link request

`POST /api/auth/magic-link` accepts exactly `{"email":"<string>"}`.

| Condition | Status | Body |
| --- | --- | --- |
| Malformed JSON, non-object, missing or extra key, or non-string email | `422` | `{"error":"invalid_body"}` |
| String that fails normalization | `422` | `{"error":"invalid_email"}` |
| Any syntactically valid address | `202` | `{"status":"accepted"}` |

The `202` body is byte-identical for an invited address, an uninvited address,
a disabled account, a rate-limited request, a suppressed resend, and a request
that cannot send because mail or the signing key is off. The response must not
include an account id, a token, or a `Set-Cookie` header. `Content-Type` is
`application/json` and `Cache-Control` is `no-store`.

A send is attempted only when every item below is true:

- the address matches an account whose status is `invited` or `active`;
- `LIVECHO_EMAIL_ENABLED` is exactly `true`;
- `RESEND_API_KEY`, `LIVECHO_SESSION_SIGNING_KEY`, `LIVECHO_EMAIL_FROM`, and
  `LIVECHO_PUBLIC_ORIGIN` are all present and valid;
- the account is under the send quotas in the next section;
- the account has no unexpired unused magic-link row.

Otherwise the handler returns `202` and must not call Resend and must not
insert a magic-link row. Invalid configuration is a suppressed send, not a
distinct HTTP error.

### Token, hash, and single use

A new magic link uses 32 bytes from a cryptographic generator. The email and
the redeem request carry that value as unpadded base64url. The database stores
only:

- the account id;
- HMAC-SHA-256 over the label `livecho-magic-link-v1` followed by one `0x00`
  byte and the raw 32 token bytes, keyed by the raw session signing key;
- `created_at` and `expires_at = created_at + 15 minutes`;
- `used_at`, null until the single successful redeem.

The plaintext token, the email URL, and the HMAC key must not be stored.
Lookup uses the verifier. Redeem is one conditional update that sets `used_at`
only when it is still null and `expires_at` is in the future. Exactly one
concurrent redeem wins. The loser, a second use, an expired token, and an
unknown verifier all return the same `401` body. Expiry is an absolute 15
minutes from `created_at`, not a sliding window.

While an unused row is unexpired, a later request for that account reuses it:
no second row, no second Resend call, and the same `202` body.

### Resend send

The message is plain text to exactly one recipient, with no `cc`, `bcc`,
attachment, HTML, or template. The body is the fixed sentence `This link signs
you in once and expires in 15 minutes.` plus the URL on the following line. The
URL is `{LIVECHO_PUBLIC_ORIGIN}/login/continue#{token}` with no query string.
The fragment holds the token so access logs of the page navigation do not
receive it.

`LIVECHO_PUBLIC_ORIGIN` is an `https` origin with no path, query, userinfo, or
trailing slash. `LIVECHO_EMAIL_FROM` is one normalized mailbox and is not a
secret. Neither variable enables sending by itself.

The Resend HTTP call sets `Idempotency-Key` to the magic-link row id (a UUID,
which fits Resend's documented 256-character, 24-hour idempotency key). A
retry of that same send reuses the key. The key is not the token and not the
email. The provider fact is Resend's send-email header `Idempotency-Key`
(<https://resend.com/docs/api-reference/emails/send-email>, reviewed
2026-11-17). Tests must not call that API. They use an in-memory sink that
records the recipient, the idempotency key, and whether the body contained a
token, then discards the message at the end of the test. The sink must not
write a file.

### Rate limits

Limits are enforced before a send. Exceeding a limit returns the same `202`
body and sends nothing.

| Key | Quota | Window |
| --- | --- | --- |
| Normalized address, newly minted magic-link rows | 5 | rolling 24 hours |
| Client IP, `POST /api/auth/magic-link` requests with a syntactically valid address | 30 | rolling 15 minutes |

The unexpired-unused-token rule above is stricter than the address quota and
applies first. The client IP is the immediate peer address. This contract does
not trust `X-Forwarded-For`. A missing peer uses one shared fallback bucket.

### Redeem and session cookie

`POST /api/auth/session` accepts exactly `{"token":"<unpadded base64url>"}`
and `Content-Type: application/json`. A `token` query parameter is rejected
with `400` and `{"error":"invalid_body"}` and must not be logged. A present
`Origin` header must equal `LIVECHO_PUBLIC_ORIGIN` when that origin is
configured; any other present `Origin` returns `400` and
`{"error":"invalid_body"}` and creates no session.

Success returns `204`, an empty body, and one new session. Failure, including
expired, reused, unknown, and disabled-account tokens, returns `401` and
`{"error":"invalid_token"}` with no session cookie. The first successful redeem
of an `invited` account sets that account to `active`.

The session id shown to the browser is a separate 32 cryptographically random
bytes, unpadded base64url, in the cookie below. The database stores
HMAC-SHA-256 over `livecho-session-v1`, one `0x00`, and those raw bytes, under
the same signing key, plus `created_at`, `expires_at = created_at + 30 days`,
and `revoked_at`. The two HMAC labels must not be interchangeable. The signing
key is 32 raw bytes, supplied as unpadded base64url. Any other length is
rejected without logging the value.

The cookie is:

```text
livecho_session=<value>; Secure; HttpOnly; SameSite=Lax; Path=/; Max-Age=2592000
```

It must not set `Domain`. `Max-Age=2592000` is 30 days. The server rejects a
session when `revoked_at` is set, the account is disabled, or now is at or
after `created_at + 30 days`, even if the browser still presents the cookie.
Lifetime does not slide. Redeem always mints a new session id and must not
adopt a pre-existing cookie.

`GET /api/auth/session` returns `200` and `{"role":"<role>"}` for a valid
session, and `401` with `{"error":"unauthenticated"}` otherwise. It must not
return the email.

`GET /api/auth/accounts/me` returns `200` and
`{"account_id","email","role","status"}` for the current account only.

`DELETE /api/auth/session` always returns `204` and always sends a clearing
cookie with the same name, `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/`, and
`Max-Age=0`. If the presented cookie matched a live session, that session's
`revoked_at` is set.

`POST /api/auth/sessions/{session_id}/revoke` is admin-only, returns `204`, and
revokes that one session. `session_id` is the row id, not the cookie secret.
Unknown id returns `404` and `{"error":"not_found"}` for an admin.

`GET /login/continue` returns an HTML document that does not contain a token.
Its script reads `location.hash`, strips the hash with `history.replaceState`,
and `POST`s JSON `{"token":...}` to `/api/auth/session` with
`credentials: "same-origin"`. If `location.search` contains `token`, the script
must not submit it. The page is anonymous. It is not the #17 console.

### Authorization matrix

Unauthenticated protected routes return `401` and `{"error":"unauthenticated"}`.
An authenticated principal that loses the matrix returns `403` and
`{"error":"forbidden"}`. A route that is not in this table and is not on the
public allowlist is denied. Tests must default to deny: every principal is
denied unless the cell says allow.

Public allowlist, no session required:

| Route | Purpose |
| --- | --- |
| `GET /health` | Existing local health |
| `GET /healthz` | Railway health contract |
| `GET` or WebSocket `/api/viewer/ws` | Public live viewing |
| `POST /api/auth/magic-link` | Enumeration-safe link request |
| `POST /api/auth/session` | One-time redeem |
| `GET /login/continue` | Fragment handler with no token in the document |

Protected actions. "Self" means the target account is the caller.

| Action | Anonymous | viewer | contributor | operator | admin | Handler owner |
| --- | --- | --- | --- | --- | --- | --- |
| `session.read_self` | deny | allow | allow | allow | allow | #12 |
| `session.revoke_self` | deny | allow | allow | allow | allow | #12 |
| `account.read_self` | deny | allow | allow | allow | allow | #12 |
| `invite.create`, `invite.list` | deny | deny | deny | deny | allow | #12 |
| `account.set_role`, `account.disable` | deny | deny | deny | deny | allow | #12 |
| `session.revoke_other` | deny | deny | deny | deny | allow | #12 |
| `history.read` | deny | allow | allow | allow | allow | #17 |
| `statistics.read_own` | deny | deny | self | deny | allow | #13 and #17 |
| `device.issue_enrollment`, `device.manage` | deny | deny | deny | deny | allow | #13 |
| `room.control`, `denylist.add`, `safety.disable` | deny | deny | deny | allow | allow | #17 |
| `denylist.remove`, `safety.reenable` | deny | deny | deny | deny | role only | #17 |
| `deletion.request` | deny | deny | deny | deny | allow | #16 and #17 |
| `raw.export` | deny | deny | deny | deny | role only | #16 |

`role only` means an admin principal passes the role check and still fails
closed unless the later owning issue has the accepted governance and audit
gate. #12 must not treat `role only` as permission to re-enable ingest, remove
a denylist entry, or export raw data. Contributor `statistics.read_own` is deny
when the target is a different account.

#12 mounts HTTP handlers only for its own rows and the public allowlist. The
other rows exist as a decision function that later issues must call. A test
enumerates every row and every principal, and it fails if a mounted non-public
route has no row.

### Continue page and local fixture boundary

The implementation must not add a session dependency to
`create_local_vertical_app` or to `/api/viewer/ws`. Existing anonymous viewer
tests remain the regression check. Auth routes live on the backend auth
application, which the local fixture app does not mount.

## Interfaces and compatibility

The later implementation may add:

- backend auth routes and the continue page described above;
- one repository port for accounts, magic-link verifiers, and session
  verifiers, with a process-local memory adapter used by tests;
- Postgres DDL for those three records under the canonical `db/migrations/`
  root, only in the same change that replaces the Issue #4 no-schema guard as
  that accepted spec already requires.

Logical columns are fixed:

| Record | Columns |
| --- | --- |
| Account | id, normalized email (unique), role, status, created_at, disabled_at |
| Magic link | id, account id, 32-byte verifier, created_at, expires_at, used_at |
| Session | id, account id, 32-byte verifier, created_at, expires_at, revoked_at |

No token, cookie, signing key, or Resend key column exists. This artifact adds
no schema, no route, and no change to `epoch`, `seq`, or `revision`.

`LIVECHO_EMAIL_FROM` and `LIVECHO_PUBLIC_ORIGIN` are non-secret and absent by
default. They must not be added to `.env.example`. The eight safety literals
in that file stay as Issue #4 left them, including `LIVECHO_EMAIL_ENABLED=false`.
`LIVECHO_PERSISTENCE_ENABLED` stays false; it governs event persistence owned
by #16, not these identity rows.

The mail port's default adapter is the in-memory sink. A Resend adapter may
be constructed only when the email flag is true and the sealed key is present.
Tests must not construct it against the network. Use the standard library for
that adapter if it is added. Do not add the Resend SDK in the implementation
that satisfies this contract.

## Failure modes and disable path

- Missing signing key, missing Resend key, flag not exactly `true`, or an
  invalid from-address or origin: magic-link requests still return `202` and
  send nothing. Redeem and new session mint fail closed.
- Resend timeout, non-2xx, or an ambiguous result: return `202`, do not mark a
  token used, and retry only with the same idempotency key. Do not log the
  provider body.
- Clock skew does not extend the 15-minute or 30-day bounds. Tests inject the
  clock.
- To stop mail later, set `LIVECHO_EMAIL_ENABLED=false`. Existing sessions
  remain until they expire or are revoked. To stop sessions, revoke them or
  remove the signing key from the process; cookies then fail verification.
  There is no production auth to disable in this issue's rollout.
- Account deletion checkpoints, backup replay, and restore rejection of old
  credentials stay with Issues #4 and #16. #12 disable is local revocation of
  sessions and unused links, not a claim that those controls are done.

## Security, privacy, and data lifecycle

- Logs for `POST /api/auth/magic-link` may contain the route and the HTTP
  status only. They must not contain a suppression reason that distinguishes
  invited from uninvited, and they must not contain the address, token, URL,
  cookie, verifier, idempotency key, or `Authorization` material.
- Admin mutations may log the actor account id, target account id, action, and
  result code. They must not log the email. This is the #12 stand-in for
  `CTRL-AUDIT-PAYLOAD-FREE`. The 365-day audit store remains #16.
- Responses other than the admin invite routes and `GET /api/auth/accounts/me`
  must not echo an email address. `accounts/me` returns the caller's own
  address because subject access is allowed. Its access log follows the same
  redaction rule.
- Staging and production each have their own sealed `RESEND_API_KEY` and
  `LIVECHO_SESSION_SIGNING_KEY` on that environment's backend only. Neither
  value is a copy of the other. Preview environments receive neither, as #4
  already requires. This contract does not provision either value.
- Tests generate the signing key in process memory and must not write it to
  disk, fixtures, or logs.
- No password hash, OAuth state, or public signup table is part of the schema.

## Acceptance criteria

- [ ] A syntactically valid uninvited address and an invited address both
      receive `202` and the same body bytes. No field in that response reveals
      which one was invited.
- [ ] A magic-link token expires 15 minutes after creation, a second redeem
      fails, and the database row holds the HMAC verifier rather than the
      token or the URL.
- [ ] The session cookie is `Secure`, `HttpOnly`, and `SameSite=Lax`, the
      server rejects it at 30 days, and revoke makes that cookie fail closed.
- [ ] The matrix above is tested for every action and every principal.
      Unlisted authenticated use is denied. `/api/viewer/ws` and `/health`
      still succeed with no cookie.
- [ ] A repeated send for one magic-link row reuses one Resend
      `Idempotency-Key`. The address quota and the client quota suppress
      further sends while still returning `202`. Logs of those requests omit
      the address, token, link, cookie, and secrets.
- [ ] Repository defaults leave `LIVECHO_EMAIL_ENABLED=false`. The Resend key
      and the session signing key are named only as the existing Railway sealed
      slots, with independent staging and production values, and this change
      supplies neither value.
- [ ] The implementation diff for #12 does not add passwords, social OAuth,
      public registration, live Resend calls in CI, production auth, real ASR,
      live Bilibili ingest, wire danmaku or superchat, or CUDA.
