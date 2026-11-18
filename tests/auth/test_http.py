"""HTTP contract for invites, indistinguishable 202s, cookies, and revocation."""

from __future__ import annotations

import json
import logging
from datetime import timedelta

from fastapi import FastAPI
from livecho_backend.auth.app import PROTECTED_ROUTES, PUBLIC_ROUTES, create_auth_app, route_table
from livecho_backend.auth.bootstrap import BootstrapError, bootstrap_first_admin
from livecho_backend.auth.config import AuthConfig, load_config
from livecho_backend.auth.crypto import magic_link_verifier, session_verifier
from livecho_backend.auth.mail import MemoryMailSink
from livecho_backend.auth.policy import HANDLER_OWNER, Action
from livecho_backend.auth.records import SESSION_MAX_AGE_SECONDS, SESSION_TTL
from livecho_backend.auth.store import MemoryAuthStore

from .support import (
    ORIGIN,
    TEST_SIGNING_KEY,
    Sequence,
    TickingClock,
    call_app,
    json_body,
    sending_config,
)

ACCEPTED = b'{"status":"accepted"}'


def _app(
    clock: TickingClock | None = None,
    *,
    config: AuthConfig | None = None,
    sink: MemoryMailSink | None = None,
    sequence: Sequence | None = None,
    store: MemoryAuthStore | None = None,
) -> tuple[FastAPI, MemoryMailSink, MemoryAuthStore, TickingClock, Sequence]:
    clock = clock or TickingClock()
    sink = sink or MemoryMailSink()
    sequence = sequence or Sequence()
    store = store or MemoryAuthStore()
    app = create_auth_app(
        store=store,
        config=config if config is not None else sending_config(),
        mailer=sink,
        clock=clock,
        random_bytes=sequence.bytes,
        new_id=sequence.id,
    )
    return app, sink, store, clock, sequence


def _login(app: FastAPI, email: str, *, client: tuple[str, int] = ("203.0.113.20", 1)) -> str:
    sink = app.state.auth_mailer
    assert isinstance(sink, MemoryMailSink)
    before = len(sink.sent)
    requested = call_app(
        app,
        "POST",
        "/api/auth/magic-link",
        body=json_body({"email": email}),
        client=client,
    )
    assert requested.status == 202
    assert requested.body == ACCEPTED
    assert len(sink.sent) == before + 1
    token = sink.sent[-1].text.split("#", 1)[1]
    redeemed = call_app(
        app,
        "POST",
        "/api/auth/session",
        body=json_body({"token": token}),
        headers={"origin": ORIGIN},
        client=client,
    )
    assert redeemed.status == 204
    set_cookie = redeemed.value("set-cookie")
    assert set_cookie is not None
    return set_cookie.split(";", 1)[0]


def test_invited_and_uninvited_magic_link_bodies_match() -> None:
    app, sink, store, clock, _sequence = _app()
    bootstrap_first_admin(store, "Admin@Example.com", now=clock.now)
    admin = _login(app, "admin@example.com", client=("203.0.113.10", 1))
    call_app(
        app,
        "POST",
        "/api/auth/invites",
        body=json_body({"email": "User+Tag@Example.com", "role": "viewer"}),
        headers={"cookie": admin},
    )
    disabled_account = call_app(
        app,
        "POST",
        "/api/auth/invites",
        body=json_body({"email": "disabled@example.com", "role": "viewer"}),
        headers={"cookie": admin},
    )
    call_app(
        app,
        "POST",
        f"/api/auth/accounts/{disabled_account.json()['account_id']}/disable",
        headers={"cookie": admin},
    )
    before = len(sink.sent)
    invited = call_app(
        app,
        "POST",
        "/api/auth/magic-link",
        body=json_body({"email": "  User+Tag@Example.com "}),
        client=("203.0.113.11", 1),
    )
    unknown = call_app(
        app,
        "POST",
        "/api/auth/magic-link",
        body=json_body({"email": "missing@example.com"}),
        client=("203.0.113.12", 1),
    )
    disabled = call_app(
        app,
        "POST",
        "/api/auth/magic-link",
        body=json_body({"email": "disabled@example.com"}),
        client=("203.0.113.13", 1),
    )
    assert invited.body == unknown.body == disabled.body == ACCEPTED
    assert invited.status == unknown.status == disabled.status == 202
    assert invited.value("content-type") == "application/json"
    assert invited.value("cache-control") == "no-store"
    assert invited.values("set-cookie") == []
    assert len(sink.sent) == before + 1
    assert sink.sent[-1].recipient == "user+tag@example.com"
    assert b"user+tag@example.com" not in invited.body


def test_magic_link_is_single_use_hashed_and_expires() -> None:
    app, sink, store, clock, _sequence = _app()
    from fastapi import FastAPI

    assert isinstance(app, FastAPI)
    bootstrap_first_admin(store, "admin@example.com", now=clock.now)
    admin_cookie = _login(app, "admin@example.com", client=("203.0.113.30", 1))
    created = call_app(
        app,
        "POST",
        "/api/auth/invites",
        body=json_body({"email": "viewer@example.com", "role": "viewer"}),
        headers={"cookie": admin_cookie},
    )
    assert created.status == 201
    call_app(
        app,
        "POST",
        "/api/auth/magic-link",
        body=json_body({"email": "viewer@example.com"}),
        client=("203.0.113.31", 1),
    )
    assert len(sink.sent) == 2
    token = sink.sent[-1].text.split("#", 1)[1]
    link = store.magic_links_for(created.json()["account_id"])[0]
    from livecho_backend.auth.crypto import decode_secret

    raw = decode_secret(token)
    assert raw is not None
    assert link.verifier == magic_link_verifier(TEST_SIGNING_KEY, raw)
    assert token.encode() not in link.verifier
    assert not hasattr(link, "token")
    fields = set(type(link).__dataclass_fields__)
    assert fields == {"link_id", "account_id", "verifier", "created_at", "expires_at", "used_at"}
    first = call_app(
        app,
        "POST",
        "/api/auth/session",
        body=json_body({"token": token}),
        headers={"origin": ORIGIN},
    )
    assert first.status == 204
    cookie = first.value("set-cookie")
    assert cookie is not None
    secret = cookie.split(";", 1)[0].split("=", 1)[1]
    assert cookie == (
        f"livecho_session={secret}; Secure; HttpOnly; SameSite=Lax; Path=/; "
        f"Max-Age={SESSION_MAX_AGE_SECONDS}"
    )
    assert "Domain=" not in cookie
    assert SESSION_TTL.total_seconds() == SESSION_MAX_AGE_SECONDS
    second = call_app(app, "POST", "/api/auth/session", body=json_body({"token": token}))
    assert second.status == 401
    assert second.body == b'{"error":"invalid_token"}'
    assert second.values("set-cookie") == []
    clock.advance(timedelta(minutes=15))
    call_app(
        app,
        "POST",
        "/api/auth/magic-link",
        body=json_body({"email": "viewer@example.com"}),
        client=("203.0.113.32", 1),
    )
    expired = sink.sent[-1].text.split("#", 1)[1]
    clock.advance(timedelta(minutes=15))
    rejected = call_app(app, "POST", "/api/auth/session", body=json_body({"token": expired}))
    assert rejected.status == 401


def test_session_cookie_expires_and_revoke_fails_closed() -> None:
    app, _sink, store, clock, _sequence = _app()
    bootstrap_first_admin(store, "admin@example.com", now=clock.now)
    cookie = _login(app, "admin@example.com")
    from fastapi import FastAPI

    assert isinstance(app, FastAPI)
    seen = call_app(app, "GET", "/api/auth/session", headers={"cookie": cookie})
    assert seen.status == 200
    assert seen.body == b'{"role":"admin"}'
    me = call_app(app, "GET", "/api/auth/accounts/me", headers={"cookie": cookie})
    assert me.json()["email"] == "admin@example.com"
    assert b"email" not in seen.body
    clock.advance(timedelta(days=30) - timedelta(seconds=1))
    assert call_app(app, "GET", "/api/auth/session", headers={"cookie": cookie}).status == 200
    clock.advance(timedelta(seconds=1))
    assert call_app(app, "GET", "/api/auth/session", headers={"cookie": cookie}).status == 401
    clock.now = clock.now - timedelta(days=30)
    fresh = call_app(app, "GET", "/api/auth/session", headers={"cookie": cookie})
    assert fresh.status == 200
    deleted = call_app(app, "DELETE", "/api/auth/session", headers={"cookie": cookie})
    assert deleted.status == 204
    cleared = deleted.value("set-cookie")
    assert cleared == "livecho_session=; Secure; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"
    assert call_app(app, "GET", "/api/auth/session", headers={"cookie": cookie}).status == 401
    anonymous = call_app(app, "DELETE", "/api/auth/session")
    assert anonymous.status == 204
    assert anonymous.value("set-cookie") == cleared


def test_admin_revoke_and_role_are_loaded_from_the_account() -> None:
    app, sink, store, clock, _sequence = _app()
    bootstrap_first_admin(store, "admin@example.com", now=clock.now)
    admin = _login(app, "admin@example.com", client=("203.0.113.40", 1))
    from fastapi import FastAPI

    assert isinstance(app, FastAPI)
    invited = call_app(
        app,
        "POST",
        "/api/auth/invites",
        body=json_body({"email": "viewer@example.com", "role": "viewer"}),
        headers={"cookie": admin},
    )
    viewer = _login(app, "viewer@example.com", client=("203.0.113.41", 1))
    assert (
        call_app(app, "GET", "/api/auth/session", headers={"cookie": viewer}).json()["role"]
        == "viewer"
    )
    account_id = invited.json()["account_id"]
    changed = call_app(
        app,
        "POST",
        f"/api/auth/accounts/{account_id}/role",
        body=json_body({"role": "contributor"}),
        headers={"cookie": admin},
    )
    assert changed.status == 200
    assert (
        call_app(app, "GET", "/api/auth/session", headers={"cookie": viewer}).json()["role"]
        == "contributor"
    )
    admin_id = call_app(app, "GET", "/api/auth/accounts/me", headers={"cookie": admin}).json()
    self_change = call_app(
        app,
        "POST",
        f"/api/auth/accounts/{admin_id['account_id']}/role",
        body=json_body({"role": "viewer"}),
        headers={"cookie": admin},
    )
    assert self_change.status == 409
    assert self_change.body == b'{"error":"self_role_change"}'
    session_id = store.session_by_verifier(
        session_verifier(TEST_SIGNING_KEY, _cookie_secret(viewer))
    )
    assert session_id is not None
    revoked = call_app(
        app,
        "POST",
        f"/api/auth/sessions/{session_id.session_id}/revoke",
        headers={"cookie": admin},
    )
    assert revoked.status == 204
    assert call_app(app, "GET", "/api/auth/session", headers={"cookie": viewer}).status == 401
    missing = call_app(
        app,
        "POST",
        "/api/auth/sessions/00000000-0000-4000-8000-000000000099/revoke",
        headers={"cookie": admin},
    )
    assert missing.status == 404
    assert missing.body == b'{"error":"not_found"}'
    assert (
        sink.sent[0].idempotency_key
        == store.magic_links_for(
            call_app(app, "GET", "/api/auth/accounts/me", headers={"cookie": admin}).json()[
                "account_id"
            ]
        )[0].link_id
    )


def test_disable_revokes_sessions_and_blocks_new_mail() -> None:
    app, sink, store, clock, _sequence = _app()
    bootstrap_first_admin(store, "admin@example.com", now=clock.now)
    admin = _login(app, "admin@example.com", client=("203.0.113.50", 1))
    from fastapi import FastAPI

    assert isinstance(app, FastAPI)
    created = call_app(
        app,
        "POST",
        "/api/auth/invites",
        body=json_body({"email": "viewer@example.com", "role": "viewer"}),
        headers={"cookie": admin},
    )
    viewer = _login(app, "viewer@example.com", client=("203.0.113.51", 1))
    sent_before = len(sink.sent)
    disabled = call_app(
        app,
        "POST",
        f"/api/auth/accounts/{created.json()['account_id']}/disable",
        headers={"cookie": admin},
    )
    assert disabled.status == 204
    assert call_app(app, "GET", "/api/auth/session", headers={"cookie": viewer}).status == 401
    again = call_app(
        app,
        "POST",
        "/api/auth/magic-link",
        body=json_body({"email": "viewer@example.com"}),
        client=("203.0.113.52", 1),
    )
    assert again.body == ACCEPTED
    assert len(sink.sent) == sent_before
    admin_id = call_app(app, "GET", "/api/auth/accounts/me", headers={"cookie": admin}).json()
    self_disable = call_app(
        app,
        "POST",
        f"/api/auth/accounts/{admin_id['account_id']}/disable",
        headers={"cookie": admin},
    )
    assert self_disable.status == 409
    assert self_disable.body == b'{"error":"self_disable"}'
    assert call_app(app, "GET", "/api/auth/session", headers={"cookie": admin}).status == 200


def test_non_admin_routes_default_to_deny_without_existence_leak() -> None:
    app, _sink, store, clock, _sequence = _app()
    bootstrap_first_admin(store, "admin@example.com", now=clock.now)
    admin = _login(app, "admin@example.com", client=("203.0.113.60", 1))
    from fastapi import FastAPI

    assert isinstance(app, FastAPI)
    call_app(
        app,
        "POST",
        "/api/auth/invites",
        body=json_body({"email": "viewer@example.com", "role": "viewer"}),
        headers={"cookie": admin},
    )
    viewer = _login(app, "viewer@example.com", client=("203.0.113.61", 1))
    anonymous = call_app(app, "GET", "/api/auth/invites")
    assert anonymous.status == 401
    assert anonymous.body == b'{"error":"unauthenticated"}'
    forbidden = call_app(app, "GET", "/api/auth/invites", headers={"cookie": viewer})
    assert forbidden.status == 403
    assert forbidden.body == b'{"error":"forbidden"}'
    hidden = call_app(
        app,
        "POST",
        "/api/auth/accounts/does-not-exist/role",
        body=json_body({"role": "admin"}),
        headers={"cookie": viewer},
    )
    assert hidden.status == 403
    assert hidden.body == b'{"error":"forbidden"}'
    unknown = call_app(app, "GET", "/api/not-in-the-matrix", headers={"cookie": viewer})
    assert unknown.status == 403
    assert call_app(app, "GET", "/api/not-in-the-matrix").status == 401
    health = call_app(app, "GET", "/health")
    healthz = call_app(app, "GET", "/healthz")
    assert health.status == healthz.status == 200
    assert health.body == healthz.body == b'{"status":"ok"}'
    page = call_app(app, "GET", "/login/continue")
    assert page.status == 200
    assert "history.replaceState" in page.body.decode()
    assert page.body.decode().index('params.has("token")') < page.body.decode().index("fetch(")
    assert 'credentials: "same-origin"' in page.body.decode()
    assert "AAAA" not in page.body.decode()


def test_duplicate_invite_does_not_change_role_or_send_mail() -> None:
    app, sink, store, clock, _sequence = _app()
    bootstrap_first_admin(store, "admin@example.com", now=clock.now)
    admin = _login(app, "admin@example.com", client=("203.0.113.70", 1))
    from fastapi import FastAPI

    assert isinstance(app, FastAPI)
    first = call_app(
        app,
        "POST",
        "/api/auth/invites",
        body=json_body({"email": "Viewer@Example.com", "role": "viewer"}),
        headers={"cookie": admin},
    )
    before = len(sink.sent)
    second = call_app(
        app,
        "POST",
        "/api/auth/invites",
        body=json_body({"email": "viewer@example.com", "role": "viewer"}),
        headers={"cookie": admin},
    )
    conflict = call_app(
        app,
        "POST",
        "/api/auth/invites",
        body=json_body({"email": "viewer@example.com", "role": "operator"}),
        headers={"cookie": admin},
    )
    assert first.status == 201
    assert second.status == 200
    assert first.json()["account_id"] == second.json()["account_id"]
    assert conflict.status == 409
    assert conflict.body == b'{"error":"role_conflict"}'
    assert len(sink.sent) == before
    listed = call_app(app, "GET", "/api/auth/invites", headers={"cookie": admin})
    account_ids = [item["account_id"] for item in listed.json()]
    assert account_ids == sorted(account_ids)
    assert "viewer@example.com" in [item["email"] for item in listed.json()]


def test_redeem_rejects_query_token_bad_origin_and_bad_body() -> None:
    app, sink, store, clock, _sequence = _app()
    bootstrap_first_admin(store, "admin@example.com", now=clock.now)
    _login(app, "admin@example.com", client=("203.0.113.80", 1))
    from fastapi import FastAPI

    assert isinstance(app, FastAPI)
    call_app(
        app,
        "POST",
        "/api/auth/magic-link",
        body=json_body({"email": "admin@example.com"}),
        client=("203.0.113.81", 1),
    )
    token = sink.sent[-1].text.split("#", 1)[1]
    leaked = call_app(
        app,
        "POST",
        "/api/auth/session",
        body=json_body({"token": token}),
        query="token=super-secret-query",
    )
    assert leaked.status == 400
    assert leaked.body == b'{"error":"invalid_body"}'
    assert leaked.values("set-cookie") == []
    wrong_origin = call_app(
        app,
        "POST",
        "/api/auth/session",
        body=json_body({"token": token}),
        headers={"origin": "https://evil.example"},
    )
    assert wrong_origin.status == 400
    still = call_app(
        app,
        "POST",
        "/api/auth/session",
        body=json_body({"token": token}),
        headers={"origin": ORIGIN},
    )
    assert still.status == 204
    assert call_app(app, "POST", "/api/auth/magic-link", body=b"{").status == 422
    assert (
        call_app(
            app,
            "POST",
            "/api/auth/magic-link",
            body=json_body({"email": "not an email"}),
        ).body
        == b'{"error":"invalid_email"}'
    )


def test_magic_link_logs_do_not_include_addresses_or_secrets() -> None:
    app, _sink, store, clock, _sequence = _app()
    bootstrap_first_admin(store, "admin@example.com", now=clock.now)
    records: list[logging.LogRecord] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = Capture()
    logger = logging.getLogger("livecho.auth")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        from fastapi import FastAPI

        assert isinstance(app, FastAPI)
        call_app(
            app,
            "POST",
            "/api/auth/magic-link",
            body=json_body({"email": "zeta-not-in-logs@example.com"}),
        )
        rendered = " ".join(record.getMessage() for record in records)
        assert "zeta-not-in-logs@example.com" not in rendered
        assert "test-resend-key" not in rendered
        assert "magic_link status=202" in rendered
        assert "invited" not in rendered
        assert "uninvited" not in rendered
    finally:
        logger.removeHandler(handler)


def test_mounted_routes_are_only_the_contract() -> None:
    app = create_auth_app()
    seen: set[tuple[str, str]] = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not isinstance(path, str) or not isinstance(methods, set):
            continue
        if path == "/{path:path}":
            continue
        for method in methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            seen.add((str(method), path))
    assert seen == set(route_table())
    for method, path, action in PROTECTED_ROUTES:
        assert (method, path) in seen
        assert HANDLER_OWNER[action] == "#12"
    for method, path in PUBLIC_ROUTES:
        assert (method, path) in seen
    owners = {HANDLER_OWNER[action] for _method, _path, action in PROTECTED_ROUTES}
    assert owners == {"#12"}
    assert Action.RAW_EXPORT not in {action for _m, _p, action in PROTECTED_ROUTES}


def test_loader_keeps_defaults_off_and_masks_repr() -> None:
    config = load_config({})
    assert config.email_enabled is False
    assert config.resend_api_key is None
    assert config.signing_key is None
    loaded = load_config(
        {
            "LIVECHO_EMAIL_ENABLED": "true",
            "RESEND_API_KEY": "test-resend-key",
            "LIVECHO_SESSION_SIGNING_KEY": "not-a-valid-key",
            "LIVECHO_EMAIL_FROM": "invites@example.com",
            "LIVECHO_PUBLIC_ORIGIN": "https://livecho.example",
        }
    )
    assert loaded.email_enabled is True
    assert loaded.signing_key is None
    assert "test-resend-key" not in repr(loaded)
    assert load_config({"LIVECHO_EMAIL_ENABLED": "True"}).email_enabled is False


def test_bootstrap_is_once_and_does_not_send() -> None:
    store = MemoryAuthStore()
    clock = TickingClock()
    sink = MemoryMailSink()
    app = create_auth_app(store=store, config=sending_config(), mailer=sink, clock=clock)
    account = bootstrap_first_admin(
        store, " Admin@Example.com ", now=clock.now, account_id="admin-1"
    )
    assert account.role.value == "admin"
    assert account.status.value == "active"
    assert account.email == "admin@example.com"
    assert sink.sent == []
    try:
        bootstrap_first_admin(store, "other@example.com", now=clock.now)
    except BootstrapError as error:
        assert "other@example.com" not in str(error)
    else:
        raise AssertionError("second bootstrap should fail")
    assert app.state.auth_store is store


def test_forwarded_for_does_not_select_the_quota_bucket() -> None:
    app, sink, store, clock, _sequence = _app()
    bootstrap_first_admin(store, "admin@example.com", now=clock.now)
    _login(app, "admin@example.com", client=("203.0.113.90", 1))
    from fastapi import FastAPI

    assert isinstance(app, FastAPI)
    call_app(
        app,
        "POST",
        "/api/auth/invites",
        body=json_body({"email": "viewer@example.com", "role": "viewer"}),
        headers={"cookie": _login(app, "admin@example.com", client=("203.0.113.91", 1))},
    )
    # The second login above consumes another send. Fill the peer address, not the header.
    for index in range(30):
        call_app(
            app,
            "POST",
            "/api/auth/magic-link",
            body=json_body({"email": f"nobody{index}@example.com"}),
            headers={"x-forwarded-for": "198.51.100.2"},
            client=("203.0.113.99", 1),
        )
    before = len(sink.sent)
    blocked = call_app(
        app,
        "POST",
        "/api/auth/magic-link",
        body=json_body({"email": "viewer@example.com"}),
        headers={"x-forwarded-for": "198.51.100.2"},
        client=("203.0.113.99", 1),
    )
    assert blocked.body == ACCEPTED
    assert len(sink.sent) == before


def _cookie_secret(cookie_pair: str) -> bytes:
    from livecho_backend.auth.crypto import decode_secret

    value = cookie_pair.split("=", 1)[1]
    raw = decode_secret(value)
    assert raw is not None
    return raw


def test_response_is_json() -> None:
    assert json.loads(ACCEPTED) == {"status": "accepted"}
