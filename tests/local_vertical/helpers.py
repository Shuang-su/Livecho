"""Shared wire-level harness for the local caption vertical tests.

Every integration test drives a real loopback backend over the real WebSocket
endpoint: no in-process ASGI shortcut. Tests use synthetic fixture text only.
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from typing import Any, cast
from uuid import uuid4

import uvicorn
from livecho_backend.local_vertical.config import (
    DEFAULT_ROOM_ID,
    VIEWER_ENDPOINT_PATH,
    LocalVerticalConfig,
    LocalVerticalMode,
)
from livecho_backend.local_vertical.schedule import FixtureScheduleSpec
from livecho_backend.local_vertical.service import (
    LocalVerticalService,
    create_local_vertical_app,
)
from livecho_backend.local_vertical.timeline import utc_stamp
from livecho_protocol import (
    StableCode,
    TimelineEventV1,
    TranscriptTimelinePayloadV1,
    ViewerCursorV1,
    ViewerReadyV1,
    ViewerSubscribeV1,
    canonical_json,
    strict_json_loads,
)
from livecho_protocol.models import VIEWER_PROTOCOL
from livecho_protocol.parser import MAX_CONTROL_BYTES, validate_object
from livecho_protocol.state import StreamOrderingState
from websockets.asyncio.client import ClientConnection
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import InvalidStatus
from websockets.typing import Subprotocol

CLIENT_VERSION = "0.1.0"


def reserve_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class LocalServer:
    """One loopback backend server instance for a single test."""

    def __init__(
        self,
        *,
        room_id: str = DEFAULT_ROOM_ID,
        port: int | None = None,
    ) -> None:
        self.port = port if port is not None else reserve_loopback_port()
        self.config = LocalVerticalConfig(
            mode=LocalVerticalMode.FIXTURE_TIMELINE,
            host="127.0.0.1",
            port=self.port,
            room_id=room_id,
        )
        self.service = LocalVerticalService(self.config)
        self._server: uvicorn.Server | None = None
        self._serve_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        app = create_local_vertical_app(self.service)
        self._server = uvicorn.Server(
            uvicorn.Config(
                app,
                host="127.0.0.1",
                port=self.port,
                log_level="warning",
                ws_max_size=MAX_CONTROL_BYTES,
                ws_ping_interval=10.0,
                ws_ping_timeout=10.0,
            )
        )
        self._serve_task = asyncio.create_task(self._server.serve())
        while not self._server.started:
            await asyncio.sleep(0.01)

    async def stop(self) -> None:
        if self.service._schedule_task is not None:
            self.service._schedule_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.service._schedule_task
            self.service._schedule_task = None
        if self._server is not None:
            self._server.should_exit = True
            with contextlib.suppress(TimeoutError, Exception):
                await asyncio.wait_for(self._server.shutdown(), timeout=5)
        if self._serve_task is not None:
            try:
                await asyncio.wait_for(self._serve_task, timeout=10)
            except (TimeoutError, asyncio.CancelledError):
                self._serve_task.cancel()

    async def start_session(self, spec: FixtureScheduleSpec | None = None) -> None:
        await self.service.start_fixture_session(spec)

    async def open_session(self) -> None:
        await self.service.open_fixture_session()

    def viewer_uri(self) -> str:
        return f"ws://127.0.0.1:{self.port}{VIEWER_ENDPOINT_PATH}"

    def admitted_count(self) -> int:
        return self.service.registry.connection_count()


@asynccontextmanager
async def backend_server(**kwargs: Any) -> AsyncIterator[LocalServer]:
    server = LocalServer(**kwargs)
    await server.start()
    try:
        yield server
    finally:
        await server.stop()


def subscribe_text(room_id: str, cursor: ViewerCursorV1 | None = None) -> str:
    value: dict[str, Any] = {
        "protocol": VIEWER_PROTOCOL,
        "protocol_minor": 0,
        "message_id": str(uuid4()),
        "sent_at": utc_stamp(),
        "type": "viewer.subscribe",
        "client_version": CLIENT_VERSION,
        "supported_minors": [0],
        "room_id": room_id,
    }
    if cursor is not None:
        value["cursor"] = {
            "session_id": cursor.session_id,
            "epoch": cursor.epoch,
            "next_seq": cursor.next_seq,
        }
    subscribe = ViewerSubscribeV1.model_validate(value)
    return canonical_json(subscribe.model_dump(mode="json")).decode("utf-8")


async def connect_viewer(
    server: LocalServer,
    *,
    room_id: str | None = None,
    origin: str | None = None,
    subprotocol: bool = True,
    cursor: ViewerCursorV1 | None = None,
    subscribe: bool = True,
) -> ClientConnection:
    connect_kwargs: dict[str, Any] = {
        "subprotocols": [cast(Subprotocol, VIEWER_PROTOCOL)] if subprotocol else None,
        "open_timeout": 5,
    }
    if origin is not None:
        connect_kwargs["origin"] = origin
    connection = await ws_connect(server.viewer_uri(), **connect_kwargs)
    if subscribe:
        await connection.send(subscribe_text(room_id or server.config.room_id, cursor))
    return connection


async def raw_http_request(port: int, path: str, *, host: str = "127.0.0.1") -> tuple[int, str]:
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(
        f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n".encode()
    )
    await writer.drain()
    response = await asyncio.wait_for(reader.read(8_192), timeout=5)
    writer.close()
    await writer.wait_closed()
    text = response.decode("utf-8", errors="replace")
    return int(text.split(" ", 2)[1]), text


async def next_message(connection: ClientConnection, timeout: float = 5.0) -> dict[str, Any]:
    text = await asyncio.wait_for(connection.recv(decode=True), timeout=timeout)
    return strict_json_loads(text)


async def expect_no_message(connection: ClientConnection, timeout: float = 0.5) -> None:
    try:
        text = await asyncio.wait_for(connection.recv(decode=True), timeout=timeout)
    except TimeoutError:
        return
    raise AssertionError(f"unexpected frame: {text[:120]}")


async def expect_closed(connection: ClientConnection, timeout: float = 5.0) -> int | None:
    with contextlib.suppress(Exception):
        await asyncio.wait_for(connection.recv(decode=True), timeout=timeout)
    return connection.close_code


async def expect_rejected(connect_coro: Awaitable[ClientConnection], status: int) -> None:
    try:
        connection = await connect_coro
    except InvalidStatus as error:
        assert error.response.status_code == status
        return
    await connection.close()
    raise AssertionError(f"expected HTTP {status} rejection")


async def read_ready(connection: ClientConnection) -> dict[str, Any]:
    value = await next_message(connection)
    assert value["type"] == "viewer.ready", value
    validate_object(value, ViewerReadyV1)
    return value


class OrderChecker:
    """Client-side acceptance through the shared reducer; aborts on rejection."""

    def __init__(self, session_id: str, epoch: str, next_seq: str) -> None:
        self.ordering = StreamOrderingState(
            session_id=session_id,
            lease_id=None,
            epoch=int(epoch),
            start_seq=int(next_seq),
        )
        self.events: list[tuple[int, str, str]] = []
        self.duplicates = 0

    @property
    def next_seq(self) -> int:
        return self.ordering.sequence.next_expected_seq

    def accept(self, value: dict[str, Any]) -> bool:
        event = validate_object(value, TimelineEventV1)
        decision = self.ordering.accept(event.model_dump(mode="json"))
        if decision.code == StableCode.ACCEPTED:
            payload = event.payload
            status = getattr(payload, "status", None)
            if status is not None:
                self.events.append((int(event.seq), "status", str(status)))
                # Wait for stopped/failed, not stopping.
                return status in ("stopped", "failed")
            if isinstance(payload, TranscriptTimelinePayloadV1):
                kind = "final" if payload.is_final else "partial"
                self.events.append((int(event.seq), kind, ""))
            return False
        if decision.code in (StableCode.SEQ_DUPLICATE, StableCode.REVISION_DUPLICATE):
            self.duplicates += 1
            return False
        raise AssertionError(f"backend frame rejected: {decision.code.value}")

    async def consume(
        self, connection: ClientConnection, timeout: float = 8.0
    ) -> tuple[int, str, str] | None:
        value = await next_message(connection, timeout=timeout)
        if value.get("type") == "viewer.timeline_event":
            if self.accept(value):
                return self.events[-1]
        elif value.get("type") == "protocol.error":
            raise AssertionError(f"backend protocol error: {value['code']}")
        return None


def viewer_cursor(session_id: str, epoch: str, next_seq: str) -> ViewerCursorV1:
    return ViewerCursorV1.model_validate(
        {"session_id": session_id, "epoch": epoch, "next_seq": next_seq}
    )


class FakeMonotonic:
    """Controllable monotonic clock for pure timeline-rule tests."""

    def __init__(self) -> None:
        self.value = 1_000.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class StubWebSocket:
    """Transport double for fan-out unit tests: blocks sends until released."""

    def __init__(self, *, block: bool = False, fail: bool = False) -> None:
        self.frames: list[bytes] = []
        self.blocked = block
        self.fail = fail
        self.close_codes: list[int] = []
        self._release = asyncio.Event()
        self._block_started = asyncio.Event()

    async def send_bytes(self, data: bytes) -> None:
        if self.fail:
            raise RuntimeError("transport write failed")
        if self.blocked:
            self._block_started.set()
            await self._release.wait()
        self.frames.append(data)

    async def close(self, code: int = 1000) -> None:
        self.close_codes.append(code)

    def release(self) -> None:
        self._release.set()

    @property
    def send_started(self) -> asyncio.Event:
        return self._block_started
