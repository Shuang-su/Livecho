"""Idempotency, quotas, and suppressed sends. The sink never touches disk or Resend."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

from livecho_backend.auth.app import create_auth_app
from livecho_backend.auth.bootstrap import bootstrap_first_admin
from livecho_backend.auth.config import AuthConfig
from livecho_backend.auth.crypto import magic_link_verifier, session_verifier
from livecho_backend.auth.mail import MemoryMailSink, TransportMailer, prepare_resend_call
from livecho_backend.auth.records import IP_QUOTA, IP_WINDOW, MAGIC_LINK_TTL
from livecho_backend.auth.store import MemoryAuthStore

from .support import TEST_SIGNING_KEY, TickingClock, call_app, json_body, sending_config

ACCEPTED = b'{"status":"accepted"}'


def test_unused_link_is_reused_and_retry_keeps_one_idempotency_key() -> None:
    clock = TickingClock()
    store = MemoryAuthStore()
    sink = MemoryMailSink(failures=1)
    app = create_auth_app(
        store=store,
        config=sending_config(),
        mailer=sink,
        clock=clock,
    )
    bootstrap_first_admin(store, "viewer@example.com", now=clock.now)
    first = call_app(
        app, "POST", "/api/auth/magic-link", body=json_body({"email": "viewer@example.com"})
    )
    second = call_app(
        app, "POST", "/api/auth/magic-link", body=json_body({"email": "viewer@example.com"})
    )
    assert first.body == second.body == ACCEPTED
    assert sink.attempts == [sink.attempts[0], sink.attempts[0]]
    assert len(sink.sent) == 1
    assert sink.sent[0].idempotency_key == sink.attempts[0]
    assert sink.sent[0].contained_token is True
    account = store.account_by_email("viewer@example.com")
    assert account is not None
    assert len(store.magic_links_for(account.account_id)) == 1
    prepared = prepare_resend_call(
        sink.sent[0],
        sender="invites@example.com",
        api_key="test-resend-key",
    )
    assert prepared.url == "https://api.resend.com/emails"
    assert ("Idempotency-Key", sink.sent[0].idempotency_key) in prepared.headers
    assert b"cc" not in prepared.body
    assert b"bcc" not in prepared.body
    assert b"html" not in prepared.body
    sink.clear()
    assert sink.sent == []
    assert sink.attempts == []


def test_address_quota_suppresses_the_sixth_mint() -> None:
    clock = TickingClock()
    store = MemoryAuthStore()
    sink = MemoryMailSink()
    app = create_auth_app(store=store, config=sending_config(), mailer=sink, clock=clock)
    bootstrap_first_admin(store, "viewer@example.com", now=clock.now)
    for _ in range(5):
        response = call_app(
            app,
            "POST",
            "/api/auth/magic-link",
            body=json_body({"email": "viewer@example.com"}),
            client=("203.0.113.40", 1),
        )
        assert response.body == ACCEPTED
        clock.advance(MAGIC_LINK_TTL + timedelta(seconds=1))
    assert len(sink.sent) == 5
    blocked = call_app(
        app,
        "POST",
        "/api/auth/magic-link",
        body=json_body({"email": "viewer@example.com"}),
        client=("203.0.113.41", 1),
    )
    assert blocked.body == ACCEPTED
    assert len(sink.sent) == 5
    account = store.account_by_email("viewer@example.com")
    assert account is not None
    assert len(store.magic_links_for(account.account_id)) == 5


def test_missing_signing_key_suppresses_without_a_different_body() -> None:
    clock = TickingClock()
    store = MemoryAuthStore()
    sink = MemoryMailSink()
    config = AuthConfig(
        email_enabled=True,
        resend_api_key="test-resend-key",
        signing_key=None,
        email_from="invites@example.com",
        public_origin="https://livecho.example",
    )
    app = create_auth_app(store=store, config=config, mailer=sink, clock=clock)
    bootstrap_first_admin(store, "viewer@example.com", now=clock.now)
    response = call_app(
        app, "POST", "/api/auth/magic-link", body=json_body({"email": "viewer@example.com"})
    )
    assert response.body == ACCEPTED
    assert sink.sent == []
    account = store.account_by_email("viewer@example.com")
    assert account is not None
    assert store.magic_links_for(account.account_id) == ()
    assert (
        call_app(app, "POST", "/api/auth/session", body=json_body({"token": "x" * 43})).status
        == 401
    )


def test_transport_is_refused_until_mail_is_fully_configured() -> None:
    try:
        TransportMailer(AuthConfig(), lambda _prepared: 200)
    except RuntimeError as error:
        assert "refused" in str(error)
    else:
        raise AssertionError("incomplete config should refuse a transport")
    calls: list[int] = []

    def transport(prepared: object) -> int:
        calls.append(1)
        assert getattr(prepared, "url", "").startswith("https://")
        return 204

    mailer = TransportMailer(sending_config(), transport)
    clock = TickingClock()
    store = MemoryAuthStore()
    app = create_auth_app(store=store, config=sending_config(), mailer=mailer, clock=clock)
    bootstrap_first_admin(store, "viewer@example.com", now=clock.now)
    response = call_app(
        app, "POST", "/api/auth/magic-link", body=json_body({"email": "viewer@example.com"})
    )
    assert response.body == ACCEPTED
    assert calls == [1]
    assert len(mailer.calls) == 1
    assert mailer.calls[0].headers[2][0] == "Idempotency-Key"


def test_rate_limit_buckets_stay_bounded_and_idle_buckets_leave() -> None:
    store = MemoryAuthStore()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    for _ in range(IP_QUOTA + 40):
        store.prepare_magic_link(
            account=None,
            ip="203.0.113.8",
            now=now,
            verifier=None,
            link_id=None,
            can_send=False,
            created_at=now,
            expires_at=now,
        )
    assert len(store._ip_hits["203.0.113.8"]) == IP_QUOTA
    store.prepare_magic_link(
        account=None,
        ip="198.51.100.9",
        now=now,
        verifier=None,
        link_id=None,
        can_send=False,
        created_at=now,
        expires_at=now,
    )
    later = now + IP_WINDOW
    allowed = store.prepare_magic_link(
        account=None,
        ip="203.0.113.50",
        now=later,
        verifier=None,
        link_id=None,
        can_send=False,
        created_at=later,
        expires_at=later,
    )
    assert allowed.kind.value == "noop"
    assert "203.0.113.8" not in store._ip_hits
    assert "198.51.100.9" not in store._ip_hits
    assert len(store._ip_hits["203.0.113.50"]) == 1


def test_one_consume_wins_and_labels_do_not_match() -> None:
    store = MemoryAuthStore()
    now = TickingClock().now
    account = bootstrap_first_admin(store, "viewer@example.com", now=now)
    token = bytes(range(32))
    verifier = magic_link_verifier(TEST_SIGNING_KEY, token)
    prepared = store.prepare_magic_link(
        account=account,
        ip="203.0.113.8",
        now=now,
        verifier=verifier,
        link_id="link-1",
        can_send=True,
        created_at=now,
        expires_at=now + MAGIC_LINK_TTL,
    )
    assert prepared.kind.value == "minted"
    barrier = threading.Barrier(2)
    results: list[object] = []

    def consume() -> None:
        barrier.wait()
        results.append(store.consume_magic_link(verifier, now))

    threads = [threading.Thread(target=consume), threading.Thread(target=consume)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(item is not None for item in results) == 1
    assert session_verifier(TEST_SIGNING_KEY, token) != verifier


def test_default_app_does_not_read_environment() -> None:
    import os

    previous_flag = os.environ.get("LIVECHO_EMAIL_ENABLED")
    previous_key = os.environ.get("RESEND_API_KEY")
    os.environ["LIVECHO_EMAIL_ENABLED"] = "true"
    os.environ["RESEND_API_KEY"] = "test-resend-key"
    try:
        app = create_auth_app()
        response = call_app(
            app,
            "POST",
            "/api/auth/magic-link",
            body=json_body({"email": "viewer@example.com"}),
        )
        assert response.body == ACCEPTED
        assert app.state.auth_service.config.email_enabled is False
        assert app.state.auth_service.config.resend_api_key is None
    finally:
        _restore_env("LIVECHO_EMAIL_ENABLED", previous_flag)
        _restore_env("RESEND_API_KEY", previous_key)


def _restore_env(name: str, previous: str | None) -> None:
    import os

    if previous is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous
