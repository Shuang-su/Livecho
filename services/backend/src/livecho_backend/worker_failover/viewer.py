"""Bounded synthetic viewer admission and live-only fan-out."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable, MutableMapping
from datetime import datetime
from ipaddress import ip_address
from typing import Any, Final
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from livecho_protocol.compatibility import negotiate_viewer
from livecho_protocol.errors import ProtocolValidationError, StableCode
from livecho_protocol.long_session import Minor1SessionRuntime
from livecho_protocol.models import (
    ProtocolErrorV1,
    StrictModel,
    TimelineEventV1Minor1,
    TranscriptTimelinePayloadV1,
    ViewerReadyV1Minor1,
    ViewerResyncV1,
    ViewerSubscribeV1,
)
from livecho_protocol.parser import canonical_json, parse_control

from livecho_backend.local_vertical.config import MAX_VIEWERS, SEND_DEADLINE_SECONDS
from livecho_backend.local_vertical.fanout import ViewerConnection
from livecho_backend.local_vertical.observations import LocalVerticalObservations
from livecho_backend.worker_gateway.gateway import HELLO_TIMEOUT
from livecho_backend.worker_identity.clock import format_timestamp

VIEWER_PROTOCOL: Final = "livecho.viewer.v1"


def loopback_wss(socket: WebSocket) -> bool:
    if socket.url.scheme != "wss" or socket.client is None:
        return False
    try:
        return ip_address(socket.client.host).is_loopback
    except ValueError:
        return False


class Viewers:
    """State changes run under the scheduler lock. Socket writes run independently."""

    def __init__(
        self,
        runtime: Minor1SessionRuntime,
        room_id: str,
        session_id: str,
        lock: asyncio.Lock,
        clock: Callable[[], datetime],
    ) -> None:
        self._runtime = runtime
        self._room_id = room_id
        self._session_id = session_id
        self._lock = lock
        self._now = clock
        self._clients: dict[ViewerConnection, asyncio.Task[None]] = {}
        self._open_partials: set[str] = set()
        self._revision_boundary = asyncio.Event()
        self._revision_boundary.set()
        self._serving = 0
        self._closed = False
        self.observations = LocalVerticalObservations()

    def publish(self, event: TimelineEventV1Minor1) -> None:
        payload = event.payload
        if isinstance(payload, TranscriptTimelinePayloadV1):
            if payload.is_final:
                self._open_partials.discard(event.event_id)
                if not self._open_partials:
                    self._revision_boundary.set()
            else:
                self._open_partials.add(event.event_id)
                self._revision_boundary.clear()
        encoded = _encode(event)
        seq = int(event.seq)
        for client, task in self._clients.items():
            if not task.cancelling() and not client.offer(encoded, seq, is_terminal=False):
                task.cancel()

    def resync(self, notice: ViewerResyncV1) -> None:
        self._open_partials.clear()
        self._revision_boundary.set()
        encoded = _encode(notice)
        for client, task in self._clients.items():
            if not task.cancelling() and not client.offer_resync(encoded, int(notice.next_seq)):
                task.cancel()

    def close(self) -> None:
        self._closed = True
        self._open_partials.clear()
        self._revision_boundary.set()
        for task in self._clients.values():
            task.cancel()

    async def serve(self, socket: WebSocket) -> None:
        if not loopback_wss(socket):
            await socket.close(code=1008)
            return
        if socket.headers.get("origin") not in (None, f"https://{socket.url.netloc}"):
            await socket.close(code=1008)
            return
        if VIEWER_PROTOCOL not in socket.scope["subprotocols"]:
            await socket.close(code=1002)
            return
        if self._serving >= MAX_VIEWERS:
            await socket.close(code=1013)
            return
        self._serving += 1
        client = ViewerConnection(
            send_json=lambda data: socket.send_text(data.decode("utf-8")),
            close_socket=lambda: asyncio.wait_for(socket.close(code=1000), SEND_DEADLINE_SECONDS),
            observations=self.observations,
        )
        sender: asyncio.Task[None] | None = None
        receiver: asyncio.Task[MutableMapping[str, Any]] | None = None
        try:
            async with asyncio.timeout(HELLO_TIMEOUT.total_seconds()):
                await socket.accept(subprotocol=VIEWER_PROTOCOL)
                text = await socket.receive_text()
                subscribe, _ = parse_control(text, ViewerSubscribeV1)
                reply, sender = await self._admit(client, subscribe)
            if sender is None:
                await asyncio.wait_for(
                    socket.send_text(_encode(reply).decode("utf-8")), SEND_DEADLINE_SECONDS
                )
                return
            # The subscribe is the only client control message. Also wake when a
            # sender is cancelled for a blocked write or finishes on timeout.
            receiver = asyncio.create_task(socket.receive())
            await asyncio.wait((sender, receiver), return_when=asyncio.FIRST_COMPLETED)
        except ProtocolValidationError as failure:
            with contextlib.suppress(TimeoutError, OSError, RuntimeError, WebSocketDisconnect):
                await asyncio.wait_for(
                    socket.send_text(_encode(self._error(failure.code)).decode("utf-8")),
                    SEND_DEADLINE_SECONDS,
                )
        except (TimeoutError, OSError, RuntimeError, KeyError, WebSocketDisconnect):
            pass
        finally:
            self._clients.pop(client, None)
            self._serving -= 1
            for task in (sender, receiver):
                if task is not None:
                    task.cancel()
                    with contextlib.suppress(
                        asyncio.CancelledError, OSError, RuntimeError, WebSocketDisconnect
                    ):
                        await task
            with contextlib.suppress(TimeoutError, OSError, RuntimeError, WebSocketDisconnect):
                if client.open:
                    await client.detach()
                else:
                    await client.close_socket()

    async def _admit(
        self, client: ViewerConnection, subscribe: ViewerSubscribeV1
    ) -> tuple[ViewerReadyV1Minor1 | ViewerResyncV1 | ProtocolErrorV1, asyncio.Task[None] | None]:
        while True:
            async with self._lock:
                reply = self._reply(subscribe)
                if isinstance(reply, ProtocolErrorV1):
                    return reply, None
                # A gap clears the viewer's revision domain. Wait for an
                # admission point that needs no historical partials or replay.
                if not isinstance(reply, ViewerResyncV1) or not self._open_partials:
                    if not client.offer(_encode(reply), int(reply.next_seq) - 1, is_terminal=False):
                        return self._error(StableCode.RESYNC_REQUIRED), None
                    sender = asyncio.create_task(client.run_sender())
                    self._clients[client] = sender
                    self.observations.peak_viewers = max(
                        self.observations.peak_viewers, len(self._clients)
                    )
                    return reply, sender
            await self._revision_boundary.wait()

    def _reply(
        self, subscribe: ViewerSubscribeV1
    ) -> ViewerReadyV1Minor1 | ViewerResyncV1 | ProtocolErrorV1:
        if self._closed or len(self._clients) >= MAX_VIEWERS:
            return self._error(StableCode.RESYNC_REQUIRED)
        selected = negotiate_viewer(subscribe)
        if not selected.decision.accepted:
            return self._error(selected.decision.code)
        if selected.selected_minor != 1:
            return self._error(StableCode.UNSUPPORTED_MINOR)
        if subscribe.room_id != self._room_id:
            return self._error(StableCode.BINDING_MISMATCH)
        notice: ViewerResyncV1 | None = None
        if subscribe.cursor is not None:
            decision, notice = self._runtime.viewer_cursor(subscribe.cursor, now=self._now())
            if not decision.accepted and notice is None:
                return self._error(decision.code)
        # Live-only admission cannot give a fresh revision domain the missing
        # revision 1 of an already-open partial. Exact cursors retain that state.
        if self._open_partials and subscribe.cursor is None:
            return self._error(StableCode.RESYNC_REQUIRED)
        if notice is not None:
            return notice
        return ViewerReadyV1Minor1(
            protocol=VIEWER_PROTOCOL,
            protocol_minor=1,
            message_id=str(uuid4()),
            sent_at=format_timestamp(self._now()),
            type="viewer.ready",
            selected_minor=1,
            minimum_client_version="0.1.0",
            session_id=self._session_id,
            epoch=str(self._runtime.epoch),
            next_seq=str(self._runtime.viewer_next_seq),
            cursor_resumed=subscribe.cursor is not None,
        )

    def _error(self, code: StableCode) -> ProtocolErrorV1:
        return ProtocolErrorV1.model_validate(
            {
                "protocol": VIEWER_PROTOCOL,
                "protocol_minor": 0,
                "message_id": str(uuid4()),
                "sent_at": format_timestamp(self._now()),
                "type": "protocol.error",
                "code": code.value,
                "message": code.value,
                "retryable": code is StableCode.RESYNC_REQUIRED,
            }
        )


def _encode(model: StrictModel) -> bytes:
    return canonical_json(model.model_dump(mode="json"))
