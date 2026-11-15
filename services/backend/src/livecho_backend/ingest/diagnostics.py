"""Payload-free diagnostics. Never echo playback URLs, tokens, or query strings."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit


def redact_url(url: str) -> str:
    try:
        parts = urlsplit(url)
    except ValueError:
        return "redacted"
    host = parts.hostname or "redacted"
    scheme = parts.scheme or "redacted"
    return f"{scheme}://{host}/redacted"


def redact_path(path: str) -> str:
    name = path.replace("\\", "/").rstrip("/").split("/")[-1]
    return name or "redacted"


def status_event(
    *,
    state: str,
    reason: str | None = None,
    counters: dict[str, int] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "state": state,
        "fixture_not_live_integration": True,
    }
    if reason is not None:
        payload["reason"] = reason
    if counters:
        payload["counters"] = dict(counters)
    return payload
