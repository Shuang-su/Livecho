"""Verifiers, unpadded base64url secrets, and the session cookie."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re

from .records import SESSION_MAX_AGE_SECONDS

COOKIE_NAME = "livecho_session"
_SECRET_RE = re.compile(r"[A-Za-z0-9_-]{43}\Z")
_MAGIC_LABEL = b"livecho-magic-link-v1\x00"
_SESSION_LABEL = b"livecho-session-v1\x00"
_SIGN_IN_SENTENCE = "This link signs you in once and expires in 15 minutes."


def encode_secret(raw: bytes) -> str:
    """Encode 32 bytes as unpadded base64url."""
    if len(raw) != 32:
        raise ValueError("secret must be 32 bytes")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_secret(value: str) -> bytes | None:
    """Decode an unpadded 32-byte base64url secret, or return None."""
    if not isinstance(value, str) or _SECRET_RE.fullmatch(value) is None:
        return None
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except ValueError:
        return None
    if len(raw) != 32:
        return None
    return raw


def parse_signing_key(value: str | None) -> bytes | None:
    """Accept only an unpadded 32-byte key. Never include the value in errors."""
    if value is None:
        return None
    return decode_secret(value)


def magic_link_verifier(key: bytes, token: bytes) -> bytes:
    return hmac.new(key, _MAGIC_LABEL + token, hashlib.sha256).digest()


def session_verifier(key: bytes, cookie_secret: bytes) -> bytes:
    return hmac.new(key, _SESSION_LABEL + cookie_secret, hashlib.sha256).digest()


def magic_link_text(origin: str, token: str) -> str:
    return f"{_SIGN_IN_SENTENCE}\n{origin}/login/continue#{token}"


def session_cookie(value: str) -> str:
    return (
        f"{COOKIE_NAME}={value}; Secure; HttpOnly; SameSite=Lax; Path=/; "
        f"Max-Age={SESSION_MAX_AGE_SECONDS}"
    )


def clear_session_cookie() -> str:
    return f"{COOKIE_NAME}=; Secure; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"


def session_cookie_value(header: str | None) -> str | None:
    if header is None:
        return None
    for part in header.split(";"):
        name, separator, value = part.strip().partition("=")
        if separator and name == COOKIE_NAME:
            return value
    return None
