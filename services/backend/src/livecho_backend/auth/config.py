"""Auth configuration. Defaults cannot send mail and hold no secret values."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .crypto import parse_signing_key
from .normalize import normalize_email, parse_origin


@dataclass(frozen=True, slots=True, repr=False)
class AuthConfig:
    """Non-secret flags plus optional secret material that must not be logged."""

    email_enabled: bool = False
    resend_api_key: str | None = None
    signing_key: bytes | None = None
    email_from: str | None = None
    public_origin: str | None = None

    def __repr__(self) -> str:
        return (
            "AuthConfig("
            f"email_enabled={self.email_enabled!r}, "
            f"resend_api_key={'set' if self.resend_api_key else 'absent'}, "
            f"signing_key={'set' if self.signing_key else 'absent'}, "
            f"email_from={'set' if self.email_from else 'absent'}, "
            f"public_origin={'set' if self.public_origin else 'absent'})"
        )


def can_send(config: AuthConfig) -> bool:
    """True only when the flag and every send input are present and valid."""
    return bool(
        config.email_enabled
        and config.resend_api_key
        and config.signing_key is not None
        and config.email_from
        and config.public_origin
    )


def load_config(environ: Mapping[str, str]) -> AuthConfig:
    """Read the sealed-variable names. Empty or invalid secrets stay absent."""
    from_value = environ.get("LIVECHO_EMAIL_FROM")
    return AuthConfig(
        email_enabled=environ.get("LIVECHO_EMAIL_ENABLED") == "true",
        resend_api_key=environ.get("RESEND_API_KEY") or None,
        signing_key=parse_signing_key(environ.get("LIVECHO_SESSION_SIGNING_KEY")),
        email_from=None if from_value is None else normalize_email(from_value),
        public_origin=parse_origin(environ.get("LIVECHO_PUBLIC_ORIGIN")),
    )
