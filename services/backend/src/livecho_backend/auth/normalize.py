"""Email and public-origin normalization from the Issue #12 spec."""

from __future__ import annotations

from urllib.parse import urlsplit

_ASCII_WHITESPACE = " \t\n\r\v\f"


def normalize_email(value: str) -> str | None:
    """Return the case-folded mailbox, or None when the syntax is rejected."""
    stripped = value.strip(_ASCII_WHITESPACE)
    if stripped == "" or len(stripped) > 254:
        return None
    if any(ord(character) > 127 or character in _ASCII_WHITESPACE for character in stripped):
        return None
    local, separator, domain = stripped.partition("@")
    if separator != "@" or "@" in domain:
        return None
    if local == "" or len(local) > 64 or domain == "" or len(domain) > 253:
        return None
    if "." not in domain or domain.startswith(".") or domain.endswith(".") or ".." in domain:
        return None
    return f"{local.lower()}@{domain.lower()}"


def parse_origin(value: str | None) -> str | None:
    """Accept one https origin and reject paths, queries, userinfo, and slashes."""
    if value is None or value == "" or value.endswith("/"):
        return None
    parts = urlsplit(value)
    if parts.scheme != "https" or parts.netloc == "":
        return None
    if parts.username or parts.password or parts.path or parts.query or parts.fragment:
        return None
    if value != f"https://{parts.netloc}":
        return None
    return value
