"""ASGI caller and deterministic clocks for auth tests. No network and no files."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, MutableMapping
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import FastAPI
from livecho_backend.auth.config import AuthConfig

TEST_SIGNING_KEY = bytes(range(32))
ORIGIN = "https://livecho.example"
FROM_ADDRESS = "invites@example.com"


def sending_config() -> AuthConfig:
    return AuthConfig(
        email_enabled=True,
        resend_api_key="test-resend-key",
        signing_key=TEST_SIGNING_KEY,
        email_from=FROM_ADDRESS,
        public_origin=ORIGIN,
    )


class TickingClock:
    def __init__(self, start: datetime | None = None) -> None:
        self.now = start or datetime(2026, 1, 1, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


class Sequence:
    def __init__(self) -> None:
        self._count = 0

    def bytes(self, size: int) -> bytes:
        self._count += 1
        prefix = self._count.to_bytes(4, "big")
        if size < 4:
            return prefix[:size]
        return prefix + bytes(size - 4)

    def id(self) -> str:
        self._count += 1
        return f"00000000-0000-4000-8000-{self._count:012d}"


class Call:
    def __init__(self, status: int, body: bytes, headers: list[tuple[str, str]]) -> None:
        self.status = status
        self.body = body
        self.headers = headers

    def values(self, name: str) -> list[str]:
        return [value for key, value in self.headers if key.lower() == name.lower()]

    def value(self, name: str) -> str | None:
        found = self.values(name)
        if not found:
            return None
        return found[-1]

    def json(self) -> Any:
        return json.loads(self.body)


def call_app(
    app: FastAPI,
    method: str,
    path: str,
    *,
    body: bytes | None = None,
    headers: Mapping[str, str] | None = None,
    query: str = "",
    client: tuple[str, int] | None = ("203.0.113.10", 4430),
) -> Call:
    merged = {key.lower(): value for key, value in (headers or {}).items()}
    payload = b"" if body is None else body
    if body is not None and "content-type" not in merged:
        merged["content-type"] = "application/json"
    if body is not None:
        merged["content-length"] = str(len(payload))
    raw_headers = [
        (key.encode("latin-1"), value.encode("latin-1")) for key, value in merged.items()
    ]
    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": query.encode("ascii"),
        "headers": raw_headers,
        "client": client,
        "server": ("test.invalid", 443),
    }
    messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": payload, "more_body": False}

    async def send(message: MutableMapping[str, Any]) -> None:
        messages.append(dict(message))

    asyncio.run(app(scope, receive, send))
    status = 500
    chunks: list[bytes] = []
    response_headers: list[tuple[str, str]] = []
    for message in messages:
        if message["type"] == "http.response.start":
            status = int(message["status"])
            for key, value in message.get("headers", []):
                response_headers.append(
                    (bytes(key).decode("latin-1"), bytes(value).decode("latin-1"))
                )
        elif message["type"] == "http.response.body":
            chunk = message.get("body", b"")
            if chunk:
                chunks.append(bytes(chunk))
    return Call(status, b"".join(chunks), response_headers)


def json_body(payload: Mapping[str, object]) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")
