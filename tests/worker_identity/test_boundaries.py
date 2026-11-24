"""Worker routes stay off the auth and local viewer apps."""

from __future__ import annotations

from pathlib import Path

from livecho_backend.auth.app import create_auth_app
from livecho_backend.auth.config import AuthConfig
from livecho_backend.auth.crypto import encode_secret, session_verifier
from livecho_backend.auth.mail import MemoryMailSink
from livecho_backend.auth.records import SESSION_TTL, Session
from livecho_backend.auth.service import AuthService
from livecho_backend.local_vertical.config import VIEWER_ENDPOINT_PATH, LocalVerticalConfig
from livecho_backend.local_vertical.service import LocalVerticalService, create_local_vertical_app
from livecho_backend.worker_identity.app import create_worker_identity_app

from tests.auth.support import call_app, json_body

from .support import MANIFEST, World, assert_no_cookie, assert_stored_json

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "services" / "backend" / "src" / "livecho_backend" / "worker_identity"


def test_local_viewer_and_auth_do_not_mount_worker_routes() -> None:
    vertical = create_local_vertical_app(LocalVerticalService(LocalVerticalConfig()))
    health = call_app(vertical, "GET", "/health")
    assert health.status == 200
    assert b"unauthenticated" not in health.body
    assert_no_cookie(health)
    paths = [getattr(route, "path", "") for route in vertical.routes]
    assert VIEWER_ENDPOINT_PATH in paths
    assert not any(path.startswith("/api/worker/") for path in paths)
    viewer = call_app(vertical, "GET", VIEWER_ENDPOINT_PATH)
    assert b"unauthenticated" not in viewer.body

    auth = create_auth_app()
    assert call_app(auth, "GET", "/health").status == 200
    assert call_app(auth, "GET", "/healthz").status == 200
    auth_paths = [getattr(route, "path", "") for route in auth.routes]
    assert not any(path.startswith("/api/worker") for path in auth_paths)
    assert "/api/worker/devices" not in auth_paths

    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "LIVECHO_EMAIL_ENABLED=false" in example
    assert "RESEND_API_KEY" not in example
    assert "LIVECHO_SESSION_SIGNING_KEY" not in example
    assert not (ROOT / "db" / "migrations").exists()


def test_worker_package_does_not_read_secrets_or_generate_keys() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in PACKAGE.rglob("*.py"))
    assert "os.environ" not in combined
    assert "RESEND_API_KEY" not in combined
    assert "LIVECHO_SESSION_SIGNING_KEY" not in combined
    assert "Ed25519PrivateKey" not in combined
    assert "subprocess" not in combined
    assert "urlopen" not in combined
    assert "hazmat.backends" not in combined
    assert "cryptography.hazmat.bindings" not in combined
    assert "LIVECHO_EMAIL_ENABLED" not in combined


def test_worker_routes_do_not_set_a_session_cookie() -> None:
    world = World()
    issued = world.issue()
    assert_stored_json(issued, 201)
    allow = world.allow()
    assert allow.status == 201
    duplicate = world.allow()
    assert duplicate.status == 200
    listed = world.call("GET", "/api/worker/allowlist", account=world.admin.account_id)
    assert_stored_json(listed, 200)
    assert listed.json() == [MANIFEST]
    removed = world.call(
        "DELETE",
        "/api/worker/allowlist",
        body=json_body(MANIFEST),
        account=world.admin.account_id,
    )
    assert removed.status == 204
    assert_no_cookie(removed)
    missing = world.call(
        "DELETE",
        "/api/worker/allowlist",
        body=json_body(MANIFEST),
        account=world.admin.account_id,
    )
    assert missing.status == 404
    rejected = world.call(
        "POST",
        "/api/worker/allowlist",
        body=json_body(
            {
                "provider": "https://example.invalid/model",
                "model_id": "x",
                "revision": "1",
                "sha256": "a" * 64,
            }
        ),
        account=world.admin.account_id,
    )
    assert rejected.status == 422
    bare = create_worker_identity_app()
    response = call_app(
        bare,
        "POST",
        "/api/worker/enrollment-tokens",
        body=json_body({"account_id": "00000000-0000-4000-8000-000000000099"}),
    )
    assert response.status == 401
    assert_no_cookie(response)


def test_account_session_authorizes_without_setting_a_worker_cookie() -> None:
    world = World()
    signing_key = bytes(reversed(range(32)))
    auth = AuthService(
        world.auth,
        AuthConfig(signing_key=signing_key),
        MemoryMailSink(),
        clock=world.clock,
    )
    secret = bytes(range(32))
    assert world.key is not None
    world.auth.insert_session(
        Session(
            session_id=world.ids.id(),
            account_id=world.admin.account_id,
            verifier=session_verifier(signing_key, secret),
            created_at=world.clock.now,
            expires_at=world.clock.now + SESSION_TTL,
            revoked_at=None,
        )
    )
    app = create_worker_identity_app(
        store=world.store,
        accounts=world.auth,
        principal_for_cookie=auth.principal_for_cookie,
        enrollment_key=world.key,
        clock=world.clock,
        random_bytes=world.random.bytes,
        new_id=world.ids.id,
    )
    response = call_app(
        app,
        "POST",
        "/api/worker/enrollment-tokens",
        body=json_body({"account_id": world.contributor.account_id}),
        headers={"cookie": f"livecho_session={encode_secret(secret)}"},
    )
    assert_stored_json(response, 201)
    assert_no_cookie(response)
