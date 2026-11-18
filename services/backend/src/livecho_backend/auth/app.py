"""HTTP routes for the Issue #12 auth application.

This app is separate from the local fixture viewer. It does not read process
environment and it does not open a network connection.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response

from .config import AuthConfig
from .crypto import clear_session_cookie, session_cookie, session_cookie_value
from .mail import MailSender, MemoryMailSink
from .normalize import normalize_email
from .page import CONTINUE_PAGE
from .policy import Action, Decision, authorize
from .records import IP_FALLBACK, Account, Principal, Role
from .redact import log_admin, log_magic_link
from .service import AuthService, Clock, NewId, RandomBytes, RedeemKind
from .store import InviteKind, MemoryAuthStore

PUBLIC_ROUTES: tuple[tuple[str, str], ...] = (
    ("GET", "/health"),
    ("GET", "/healthz"),
    ("POST", "/api/auth/magic-link"),
    ("POST", "/api/auth/session"),
    ("GET", "/login/continue"),
)
PROTECTED_ROUTES: tuple[tuple[str, str, Action], ...] = (
    ("GET", "/api/auth/session", Action.SESSION_READ_SELF),
    ("DELETE", "/api/auth/session", Action.SESSION_REVOKE_SELF),
    ("GET", "/api/auth/accounts/me", Action.ACCOUNT_READ_SELF),
    ("POST", "/api/auth/invites", Action.INVITE_CREATE),
    ("GET", "/api/auth/invites", Action.INVITE_LIST),
    ("POST", "/api/auth/accounts/{account_id}/role", Action.ACCOUNT_SET_ROLE),
    ("POST", "/api/auth/accounts/{account_id}/disable", Action.ACCOUNT_DISABLE),
    ("POST", "/api/auth/sessions/{session_id}/revoke", Action.SESSION_REVOKE_OTHER),
)
_JSON = "application/json"


def create_auth_app(
    *,
    store: MemoryAuthStore | None = None,
    config: AuthConfig | None = None,
    mailer: MailSender | None = None,
    clock: Clock | None = None,
    random_bytes: RandomBytes | None = None,
    new_id: NewId | None = None,
) -> FastAPI:
    """Build the auth application. Defaults keep mail disabled and secrets absent."""
    auth_store = store if store is not None else MemoryAuthStore()
    auth_config = config if config is not None else AuthConfig()
    auth_mailer = mailer if mailer is not None else MemoryMailSink()
    service = AuthService(
        auth_store,
        auth_config,
        auth_mailer,
        clock=clock,
        random_bytes=random_bytes,
        new_id=new_id,
    )
    app = FastAPI(
        title="Livecho auth",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        redirect_slashes=False,
    )
    app.state.auth_service = service
    app.state.auth_store = auth_store
    app.state.auth_mailer = auth_mailer

    def json_response(status_code: int, payload: object) -> Response:
        return Response(
            content=json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
            status_code=status_code,
            media_type=_JSON,
            headers={"cache-control": "no-store"},
        )

    def empty(status_code: int, cookie: str | None = None) -> Response:
        response = Response(status_code=status_code, headers={"cache-control": "no-store"})
        if cookie is not None:
            response.headers.append("set-cookie", cookie)
        return response

    def error(status_code: int, code: str) -> Response:
        return json_response(status_code, {"error": code})

    def client_ip(request: Request) -> str:
        if request.client is None or not request.client.host:
            return IP_FALLBACK
        return request.client.host

    def principal_for(request: Request) -> Principal | None:
        return service.principal_for_cookie(session_cookie_value(request.headers.get("cookie")))

    def denied(principal: Principal | None, action: Action, target_id: str) -> Response | None:
        if principal is None:
            return error(401, "unauthenticated")
        decision = authorize(principal, action, target_account_id=target_id)
        if decision is not Decision.ALLOW:
            log_admin(action.value, principal.account_id, target_id or "-", "forbidden")
            return error(403, "forbidden")
        return None

    def account_body(account: Account) -> dict[str, str]:
        return {
            "account_id": account.account_id,
            "email": account.email,
            "role": account.role.value,
            "status": account.status.value,
        }

    @app.get("/health")
    @app.get("/healthz")
    async def health() -> Response:
        return json_response(200, {"status": "ok"})

    @app.get("/login/continue")
    async def continue_page() -> HTMLResponse:
        return HTMLResponse(CONTINUE_PAGE, headers={"cache-control": "no-store"})

    @app.post("/api/auth/magic-link")
    async def magic_link(request: Request) -> Response:
        parsed = _parse_object(await request.body(), frozenset({"email"}))
        raw_email = None if parsed is None else parsed.get("email")
        if not isinstance(raw_email, str):
            log_magic_link(422)
            return error(422, "invalid_body")
        email = normalize_email(raw_email)
        if email is None:
            log_magic_link(422)
            return error(422, "invalid_email")
        service.request_magic_link(email, client_ip(request))
        log_magic_link(202)
        return json_response(202, {"status": "accepted"})

    @app.post("/api/auth/session")
    async def redeem(request: Request) -> Response:
        if "token" in request.query_params:
            return error(400, "invalid_body")
        origin = request.headers.get("origin")
        if (
            auth_config.public_origin is not None
            and origin is not None
            and origin != auth_config.public_origin
        ):
            return error(400, "invalid_body")
        if not _is_json(request.headers.get("content-type")):
            return error(400, "invalid_body")
        parsed = _parse_object(await request.body(), frozenset({"token"}))
        raw_token = None if parsed is None else parsed.get("token")
        if not isinstance(raw_token, str):
            return error(400, "invalid_body")
        result = service.redeem(raw_token)
        if result.kind is not RedeemKind.OK or result.cookie_value is None:
            return error(401, "invalid_token")
        return empty(204, session_cookie(result.cookie_value))

    @app.get("/api/auth/session")
    async def read_session(request: Request) -> Response:
        rejection = denied(principal_for(request), Action.SESSION_READ_SELF, "-")
        if rejection is not None:
            return rejection
        principal = principal_for(request)
        if principal is None:
            return error(401, "unauthenticated")
        return json_response(200, {"role": principal.role.value})

    @app.delete("/api/auth/session")
    async def revoke_self(request: Request) -> Response:
        # Always 204 and clear the cookie, including when no session is present.
        service.revoke_cookie(session_cookie_value(request.headers.get("cookie")))
        return empty(204, clear_session_cookie())

    @app.get("/api/auth/accounts/me")
    async def read_me(request: Request) -> Response:
        principal = principal_for(request)
        rejection = denied(principal, Action.ACCOUNT_READ_SELF, "-")
        if rejection is not None:
            return rejection
        if principal is None:
            return error(401, "unauthenticated")
        account = service.account_for_principal(principal)
        if account is None:
            return error(401, "unauthenticated")
        return json_response(200, account_body(account))

    @app.post("/api/auth/invites")
    async def create_invite(request: Request) -> Response:
        principal = principal_for(request)
        rejection = denied(principal, Action.INVITE_CREATE, "-")
        if rejection is not None:
            return rejection
        assert principal is not None
        parsed = _parse_object(await request.body(), frozenset({"email", "role"}))
        raw_email = None if parsed is None else parsed.get("email")
        role = None if parsed is None else _parse_role(parsed.get("role"))
        if not isinstance(raw_email, str) or role is None:
            log_admin(Action.INVITE_CREATE.value, principal.account_id, "-", "invalid_body")
            return error(422, "invalid_body")
        email = normalize_email(raw_email)
        if email is None:
            log_admin(Action.INVITE_CREATE.value, principal.account_id, "-", "invalid_email")
            return error(422, "invalid_email")
        kind, account = service.create_invite(email, role)
        log_admin(Action.INVITE_CREATE.value, principal.account_id, account.account_id, kind.value)
        if kind is InviteKind.CREATED:
            return json_response(201, account_body(account))
        if kind is InviteKind.SAME_ROLE:
            return json_response(200, account_body(account))
        code = "account_disabled" if kind is InviteKind.DISABLED else "role_conflict"
        return error(409, code)

    @app.get("/api/auth/invites")
    async def list_invites(request: Request) -> Response:
        principal = principal_for(request)
        rejection = denied(principal, Action.INVITE_LIST, "-")
        if rejection is not None:
            return rejection
        assert principal is not None
        body = [account_body(account) for account in service.list_accounts()]
        log_admin(Action.INVITE_LIST.value, principal.account_id, "-", "ok")
        return json_response(200, body)

    @app.post("/api/auth/accounts/{account_id}/role")
    async def set_role(account_id: str, request: Request) -> Response:
        principal = principal_for(request)
        rejection = denied(principal, Action.ACCOUNT_SET_ROLE, account_id)
        if rejection is not None:
            return rejection
        assert principal is not None
        parsed = _parse_object(await request.body(), frozenset({"role"}))
        role = None if parsed is None else _parse_role(parsed.get("role"))
        if role is None:
            log_admin(
                Action.ACCOUNT_SET_ROLE.value,
                principal.account_id,
                account_id,
                "invalid_body",
            )
            return error(422, "invalid_body")
        result, account = service.set_role(principal.account_id, account_id, role)
        target = account.account_id if account is not None else account_id
        log_admin(Action.ACCOUNT_SET_ROLE.value, principal.account_id, target, result)
        if result == "updated" and account is not None:
            return json_response(200, account_body(account))
        if result == "not_found":
            return error(404, "not_found")
        return error(409, result)

    @app.post("/api/auth/accounts/{account_id}/disable")
    async def disable_account(account_id: str, request: Request) -> Response:
        principal = principal_for(request)
        rejection = denied(principal, Action.ACCOUNT_DISABLE, account_id)
        if rejection is not None:
            return rejection
        assert principal is not None
        result, _account = service.disable(principal.account_id, account_id)
        log_admin(Action.ACCOUNT_DISABLE.value, principal.account_id, account_id, result)
        if result == "disabled":
            return empty(204)
        if result == "not_found":
            return error(404, "not_found")
        return error(409, result)

    @app.post("/api/auth/sessions/{session_id}/revoke")
    async def revoke_other(session_id: str, request: Request) -> Response:
        principal = principal_for(request)
        rejection = denied(principal, Action.SESSION_REVOKE_OTHER, session_id)
        if rejection is not None:
            return rejection
        assert principal is not None
        found = service.revoke_session(session_id)
        log_admin(
            Action.SESSION_REVOKE_OTHER.value,
            principal.account_id,
            session_id,
            "revoked" if found else "not_found",
        )
        if not found:
            return error(404, "not_found")
        return empty(204)

    @app.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    )
    async def deny_unknown(request: Request) -> Response:
        principal = principal_for(request)
        if principal is None:
            return error(401, "unauthenticated")
        return error(403, "forbidden")

    return app


def _parse_object(raw: bytes, keys: frozenset[str]) -> dict[str, object] | None:
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    parsed: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            return None
        parsed[key] = item
    if set(parsed) != keys:
        return None
    return parsed


def _parse_role(value: object) -> Role | None:
    if not isinstance(value, str):
        return None
    try:
        return Role(value)
    except ValueError:
        return None


def _is_json(value: str | None) -> bool:
    if value is None:
        return False
    media = value.split(";", 1)[0].strip().lower()
    return media == _JSON


def route_table() -> Mapping[tuple[str, str], Action | None]:
    """Map mounted auth routes to actions. Public routes map to None."""
    table: dict[tuple[str, str], Action | None] = {}
    for method, path in PUBLIC_ROUTES:
        table[(method, path)] = None
    for method, path, action in PROTECTED_ROUTES:
        table[(method, path)] = action
    return table
