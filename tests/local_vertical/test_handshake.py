"""Wire-level handshake tests for the exact livecho.viewer.v1 mount."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from livecho_backend.local_vertical.config import MAX_VIEWERS, WORKER_ENDPOINT_PATH
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import InvalidStatus
from websockets.typing import Subprotocol

from .helpers import (
    backend_server,
    connect_viewer,
    expect_closed,
    expect_rejected,
    next_message,
    raw_http_request,
    read_ready,
    subscribe_text,
)

SUBSCRIBE_BASE = {
    "protocol": "livecho.viewer.v1",
    "protocol_minor": 0,
    "message_id": "11111111-1111-4111-8111-111111111111",
    "sent_at": "2026-01-01T00:00:00.000Z",
    "type": "viewer.subscribe",
    "client_version": "0.1.0",
    "supported_minors": [0],
    "room_id": "livecho.fixture.room",
}


def subscribe_with(overrides: dict[str, Any]) -> str:
    return json.dumps({**SUBSCRIBE_BASE, **overrides})


async def expect_protocol_error(
    connection: Any, code: str, *, retryable: bool | None = None
) -> None:
    value = await next_message(connection)
    assert value["type"] == "protocol.error", value
    assert value["code"] == code, value
    if retryable is not None:
        assert value["retryable"] is retryable
    assert await expect_closed(connection) is not None


def test_fresh_subscribe_receives_ready_and_current_status() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            connection = await connect_viewer(server)
            ready = await read_ready(connection)
            assert ready["cursor_resumed"] is False
            assert ready["epoch"] == "1"
            status = await next_message(connection)
            assert status["type"] == "viewer.timeline_event"
            assert status["payload"]["status"] == "live"
            assert int(status["seq"]) == int(ready["next_seq"])
            await connection.close()

    asyncio.run(scenario())


def test_malformed_json_is_rejected() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            connection = await connect_viewer(server, subscribe=False)
            await connection.send("this is not json")
            await expect_protocol_error(connection, "malformed_json")

    asyncio.run(scenario())


def test_duplicate_keys_are_rejected() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            connection = await connect_viewer(server, subscribe=False)
            await connection.send('{"room_id":1,"room_id":2}')
            await expect_protocol_error(connection, "duplicate_key")

    asyncio.run(scenario())


def test_unknown_field_is_rejected() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            connection = await connect_viewer(server, subscribe=False)
            await connection.send(subscribe_with({"unexpected": True}))
            await expect_protocol_error(connection, "unknown_field")

    asyncio.run(scenario())


def test_unknown_major_protocol_is_rejected() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            connection = await connect_viewer(server, subscribe=False)
            await connection.send(subscribe_with({"protocol": "livecho.worker.v1"}))
            await expect_protocol_error(connection, "unknown_major")

    asyncio.run(scenario())


def test_unsupported_minor_is_rejected() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            connection = await connect_viewer(server, subscribe=False)
            await connection.send(subscribe_with({"protocol_minor": 1, "supported_minors": [1]}))
            await expect_protocol_error(connection, "unsupported_minor")

    asyncio.run(scenario())


def test_old_client_version_is_rejected() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            connection = await connect_viewer(server, subscribe=False)
            await connection.send(subscribe_with({"client_version": "0.0.1"}))
            await expect_protocol_error(connection, "worker_version_too_old")

    asyncio.run(scenario())


def test_unknown_room_binding_is_rejected() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            connection = await connect_viewer(server, subscribe=False)
            await connection.send(subscribe_with({"room_id": "some.other.room"}))
            await expect_protocol_error(connection, "binding_mismatch")

    asyncio.run(scenario())


def test_binary_control_input_is_rejected() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            connection = await connect_viewer(server, subscribe=False)
            await connection.send(b"\x00\x01")
            await expect_protocol_error(connection, "schema_invalid")

    asyncio.run(scenario())


def test_browser_origin_allowlist_is_exact() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            await expect_rejected(connect_viewer(server, origin="http://evil.example"), status=403)
            allowed = await connect_viewer(server, origin="http://localhost:5173")
            ready = await read_ready(allowed)
            assert ready["type"] == "viewer.ready"
            await allowed.close()

    asyncio.run(scenario())


def test_control_frames_are_websocket_text_not_binary() -> None:
    """Protocol v1 requires JSON control as UTF-8 text frames (browser rejects binary)."""

    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            viewer = await connect_viewer(server)
            # websockets exposes the last frame opcode via the protocol after recv.
            ready = await viewer.recv(decode=True)
            assert isinstance(ready, str)
            assert '"viewer.ready"' in ready or '"type":"viewer.ready"' in ready.replace(" ", "")
            status = await viewer.recv(decode=True)
            assert isinstance(status, str)
            assert "viewer.timeline_event" in status
            await viewer.close()

    asyncio.run(scenario())


def test_missing_subprotocol_is_refused_before_handshake() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            await expect_rejected(connect_viewer(server, subprotocol=False), status=403)

    asyncio.run(scenario())


def test_worker_endpoint_is_not_mounted() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            uri = server.viewer_uri().replace("/api/viewer/ws", WORKER_ENDPOINT_PATH)
            try:
                connection = await ws_connect(uri, subprotocols=[Subprotocol("livecho.worker.v1")])
            except InvalidStatus as error:
                assert error.response.status_code in {403, 404}
                return
            await connection.close()
            raise AssertionError("the fixture slice must not mount a worker endpoint")

    asyncio.run(scenario())


def test_plain_http_requests_get_no_store_responses() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            status, response = await raw_http_request(server.port, "/health")
            assert status == 200
            assert "cache-control: no-store" in response.lower()
            status, response = await raw_http_request(server.port, "/api/control/start")
            assert status == 404
            assert "cache-control: no-store" in response.lower()

    asyncio.run(scenario())


def test_oversized_control_frame_closes_the_connection() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            connection = await connect_viewer(server, subscribe=False)
            await connection.send("x" * 70_000)
            assert await expect_closed(connection) is not None

    asyncio.run(scenario())


def test_post_subscribe_traffic_fails_closed() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            connection = await connect_viewer(server)
            await read_ready(connection)
            await next_message(connection)  # current status
            await connection.send(subscribe_text("livecho.fixture.room"))
            assert await expect_closed(connection) is not None

    asyncio.run(scenario())


def test_twenty_first_viewer_is_refused_before_creating_a_domain() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            viewers = []
            for _ in range(MAX_VIEWERS):
                connection = await connect_viewer(server)
                await read_ready(connection)
                await next_message(connection)
                viewers.append(connection)
            assert server.admitted_count() == MAX_VIEWERS
            await expect_rejected(connect_viewer(server), status=403)
            for connection in viewers:
                await connection.close()

    asyncio.run(scenario())
