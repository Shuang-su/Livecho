"""Guards that this change does not enable mail, secrets, or the local viewer gate."""

from __future__ import annotations

from pathlib import Path

from livecho_backend.local_vertical.config import VIEWER_ENDPOINT_PATH, LocalVerticalConfig
from livecho_backend.local_vertical.service import LocalVerticalService, create_local_vertical_app

from .support import call_app

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "services" / "backend" / "src" / "livecho_backend" / "auth"


def test_repository_defaults_and_local_viewer_stay_unchanged() -> None:
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "LIVECHO_EMAIL_ENABLED=false" in example
    assert "RESEND_API_KEY" not in example
    assert "LIVECHO_SESSION_SIGNING_KEY" not in example
    assert not (ROOT / "db" / "migrations").exists()
    service = LocalVerticalService(LocalVerticalConfig())
    app = create_local_vertical_app(service)
    health = call_app(app, "GET", "/health")
    assert health.status == 200
    assert b"unauthenticated" not in health.body
    paths = [getattr(route, "path", None) for route in app.routes]
    assert VIEWER_ENDPOINT_PATH in paths
    source = Path(create_local_vertical_app.__code__.co_filename).read_text(encoding="utf-8")
    assert "livecho_backend.auth" not in source


def test_auth_package_has_no_network_opener_or_oauth() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in AUTH.rglob("*.py"))
    assert "urlopen" not in combined
    assert "oauth" not in combined.lower()
    assert "socket.create_connection" not in combined
