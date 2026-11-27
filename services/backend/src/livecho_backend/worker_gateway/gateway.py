"""Issue #14 single-lease worker gateway (in-memory, synthetic audio only).

Unmounted by default. It reads no environment variable, sets no cookie, and
never writes PCM, transcript text, or proof material to disk, logs, or queues.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections import OrderedDict, deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Final
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from livecho_protocol.binary import MAX_FRAME_LENGTH, PcmHeaderV1, decode_header
from livecho_protocol.errors import Decision, ProtocolValidationError, StableCode
from livecho_protocol.models import (
    HeartbeatV1,
    LeaseV1,
    ModelManifestRefV1,
    StrictModel,
    WorkerHelloV1,
    WorkerStatsV1,
)
from livecho_protocol.parser import MAX_CONTROL_BYTES, canonical_json, parse_control
from livecho_protocol.runtime import LeaseRuntimeCoordinator, LeaseRuntimeState
from livecho_protocol.state import SEQUENCE_WINDOW_CAPACITY, LiveWorkerCursor, decide_worker_resume

from livecho_backend.worker_identity.clock import format_timestamp, utc_millis
from livecho_backend.worker_identity.service import WorkerIdentityService

from . import wire

SUBPROTOCOL: Final = "livecho.worker.v1"
HELLO_TIMEOUT: Final = timedelta(seconds=5)
HEARTBEAT_INTERVAL: Final = timedelta(seconds=5)
LEASE_LIFETIME: Final = timedelta(seconds=20)
RATE_WINDOW: Final = timedelta(seconds=1)
SEND_TIMEOUT_SECONDS: Final = 2.0
TEXT_FRAMES_PER_WINDOW: Final = 10
BINARY_FRAMES_PER_WINDOW: Final = 2
PCM_FRAMES_PER_WINDOW: Final = 50
PCM_BYTES_PER_WINDOW: Final = 32_000
CONTROL_FRAMES_PER_WINDOW: Final = 10
WORKER_PATH: Final = "/api/worker/ws"


@dataclass(slots=True)
class _Rate:
    events: deque[tuple[datetime, int]] = field(default_factory=deque)
    byte_count: int = 0

    def admit(
        self, now: datetime, maximum: int, *, size: int = 0, byte_maximum: int | None = None
    ) -> bool:
        while self.events and self.events[0][0] <= now - RATE_WINDOW:
            self.byte_count -= self.events.popleft()[1]
        if len(self.events) >= maximum:
            return False
        if byte_maximum is not None and self.byte_count + size > byte_maximum:
            return False
        self.events.append((now, size))
        self.byte_count += size
        return True


@dataclass(slots=True, eq=False)
class _Connection:
    socket: WebSocket
    id: str
    device_id: str
    identity: WorkerIdentityService
    minor: int = 0
    manifests: list[ModelManifestRefV1] = field(default_factory=list)
    online_since: datetime | None = None
    open: bool = True
    lease: _Lease | None = None
    text_in: _Rate = field(default_factory=_Rate)
    binary_in: _Rate = field(default_factory=_Rate)
    text_out: _Rate = field(default_factory=_Rate)
    pcm_out: _Rate = field(default_factory=_Rate)


@dataclass(slots=True)
class _Lease:
    model: LeaseV1
    runtime: LeaseRuntimeState
    connection: _Connection
    next_input: int
    heartbeat_at: datetime

    def live_cursor(self) -> LiveWorkerCursor:
        return LiveWorkerCursor(
            self.connection.id,
            self.model.lease_id,
            self.model.session_id,
            self.runtime.epoch,
            self.next_input,
            self.runtime.output_next_expected_seq,
            self.model.expires_at,
        )


@dataclass(frozen=True, slots=True)
class _Grant:
    session_id: str
    room_id: str
    manifest: ModelManifestRefV1


class WorkerGateway:
    """Serialized authority for an isolated synthetic gateway."""

    def __init__(
        self,
        identity: WorkerIdentityService,
        *,
        clock: Callable[[], datetime] | None = None,
        new_id: Callable[[], str] | None = None,
    ) -> None:
        self.identity = identity
        self._clock = clock or (lambda: datetime.now(UTC))
        self._new_id = new_id or (lambda: str(uuid4()))
        self._lock = asyncio.Lock()
        self._leases = LeaseRuntimeCoordinator(accepted_manifests=frozenset())
        self._active: _Lease | None = None
        self._grant: _Grant | None = None
        self._connections: dict[str, _Connection] = {}
        self._issued_sessions: set[str] = set()
        self._void_sessions: set[str] = set()
        self._results: OrderedDict[str, None] = OrderedDict()

    def _now(self) -> datetime:
        return utc_millis(self._clock())

    def _fields(self, kind: str, minor: int, now: datetime) -> dict[str, Any]:
        return {
            "protocol": SUBPROTOCOL,
            "protocol_minor": minor,
            "type": kind,
            "message_id": self._new_id(),
            "sent_at": format_timestamp(now),
        }

    def device_checked(self, connection_id: str) -> bool:
        connection = self._connections.get(connection_id)
        return (
            connection is not None
            and connection.open
            and self.identity.device_usable(connection.device_id)
        )

    def lease_valid(self, connection_id: str) -> bool:
        active = self._active
        return (
            active is not None
            and active.connection.id == connection_id
            and active.connection.open
            and active.runtime.cancellation_active
            and self._now() < active.runtime.expires_at
        )

    def heartbeat_healthy(self, connection_id: str) -> bool:
        active = self._active
        return (
            active is not None
            and self.lease_valid(connection_id)
            and self._now() - active.heartbeat_at < HEARTBEAT_INTERVAL
        )

    def result_accepted(self, message_id: str) -> bool:
        return message_id in self._results

    async def arm_grant(self, session_id: str, room_id: str, manifest: ModelManifestRefV1) -> bool:
        async with self._lock:
            now = self._now()
            await self._expire_locked(now)
            grant = _Grant(session_id, room_id, manifest)
            if self._grant is not None:
                return self._grant == grant
            if (
                self._leases.active_lease_count
                or session_id in self._issued_sessions
                or session_id in self._void_sessions
            ):
                return False
            self._grant = grant
            await self._issue_locked(now)
            return session_id not in self._void_sessions

    async def expire_due(self) -> None:
        async with self._lock:
            await self._expire_locked(self._now())

    async def restart(self, identity: WorkerIdentityService) -> None:
        async with self._lock:
            now = self._now()
            for connection in tuple(self._connections.values()):
                await self._detach(connection, now)
            for session_id in self._issued_sessions:
                self._leases.session_teardown(session_id)
            self._active = None
            self._grant = None
            self._issued_sessions.clear()
            self._void_sessions.clear()
            self._results.clear()
            self.identity = identity

    async def submit_synthetic_pcm(self, lease_id: str, frame: bytes) -> bool:
        async with self._lock:
            now = self._now()
            await self._expire_locked(now)
            active = self._active
            if active is None or active.model.lease_id != lease_id:
                return False
            connection = active.connection
            if not self.lease_valid(connection.id) or not self.device_checked(connection.id):
                return False
            try:
                header = decode_header(frame)
            except ProtocolValidationError:
                return False
            if not connection.pcm_out.admit(
                now,
                PCM_FRAMES_PER_WINDOW,
                size=header.payload_length,
                byte_maximum=PCM_BYTES_PER_WINDOW,
            ):
                return False
            if self._accept_pcm_header(active, header, now).code is not StableCode.ACCEPTED:
                return False
            active.next_input = header.seq + 1
            try:
                await asyncio.wait_for(connection.socket.send_bytes(frame), SEND_TIMEOUT_SECONDS)
            except (TimeoutError, OSError, RuntimeError, WebSocketDisconnect):
                await self._detach(connection, now)
                return False
            return True

    def _accept_pcm_header(self, active: _Lease, header: PcmHeaderV1, now: datetime) -> Decision:
        return active.runtime.accept_pcm_header(header, now=now)

    async def consume_pcm(self, lease_id: str, byte_count: int) -> bool:
        async with self._lock:
            active = self._active
            if (
                active is None
                or active.model.lease_id != lease_id
                or not 0 <= byte_count <= active.runtime.buffered_audio_bytes
            ):
                return False
            active.runtime.consume_pcm(byte_count)
            return True

    async def serve(self, socket: WebSocket) -> None:
        subprotocols = socket.scope.get("subprotocols", [])
        correct_protocol = subprotocols == [SUBPROTOCOL]
        eligible = (
            correct_protocol and "origin" not in socket.headers and socket.scope["scheme"] == "wss"
        )
        identity = self.identity
        proof = identity.verify_gateway_upgrade(
            socket.scope["headers"],
            socket.client.host if socket.client is not None else "",
            eligible=eligible,
        )
        if proof is None:
            await _close(socket, 1008 if correct_protocol else 1002)
            return
        connection: _Connection | None = None
        try:
            connection = _Connection(socket, self._new_id(), proof.device_id, identity)
            await asyncio.wait_for(socket.accept(subprotocol=SUBPROTOCOL), SEND_TIMEOUT_SECONDS)
            accepted_at = self._now()
            deadline = min(accepted_at + HELLO_TIMEOUT, proof.expires_at)
            try:
                async with asyncio.timeout(max(0, (deadline - accepted_at).total_seconds())):
                    frame = await socket.receive()
            except TimeoutError:
                return
            text = frame.get("text")
            if frame["type"] != "websocket.receive":
                return
            async with self._lock:
                now = self._now()
                if now >= deadline or identity is not self.identity:
                    return
                if not isinstance(text, str):
                    await self._error(connection, StableCode.SCHEMA_INVALID, now)
                    return
                connection.text_in.admit(now, TEXT_FRAMES_PER_WINDOW)
                try:
                    hello, _ = parse_control(text, WorkerHelloV1)
                except ProtocolValidationError as failure:
                    await self._error(connection, failure.code, now)
                    return
                decision = identity.admit_gateway_hello(hello, proof)
                if not decision.accepted or not identity.device_usable(connection.device_id):
                    await self._error(connection, decision.protocol_code, now)
                    return
                assert decision.selected_minor is not None
                connection.minor = decision.selected_minor
                connection.manifests = hello.model_manifests
                await self._expire_locked(now)
                if not await self._admit_connection(connection, hello, now):
                    return
            while connection.open:
                try:
                    frame = await asyncio.wait_for(
                        socket.receive(), HEARTBEAT_INTERVAL.total_seconds()
                    )
                except TimeoutError:
                    await self.expire_due()
                    continue
                if frame["type"] != "websocket.receive":
                    break
                async with self._lock:
                    now = self._now()
                    await self._expire_locked(now)
                    if connection.open:
                        await self._received(connection, frame, now)
        except (TimeoutError, OSError, RuntimeError, WebSocketDisconnect):
            pass
        finally:
            identity.discard_gateway_proof(proof)
            if connection is None:
                await _close(socket, 1008)
            else:
                async with self._lock:
                    await self._detach(connection, self._now())

    async def _admit_connection(
        self, connection: _Connection, hello: WorkerHelloV1, now: datetime
    ) -> bool:
        active = self._active
        resumed = False
        if hello.resume is not None:
            live = active.live_cursor() if active is not None else None
            if active is not None and active.connection.device_id != connection.device_id:
                await self._error(connection, StableCode.BINDING_MISMATCH, now)
                return False
            decision = decide_worker_resume(hello.resume, live, now)
            if not decision.accepted or active is None or not active.runtime.cancellation_active:
                await self._error(
                    connection,
                    decision.code if not decision.accepted else StableCode.LEASE_CLOSED,
                    now,
                )
                return False
            if (
                active.model.protocol_minor != connection.minor
                or active.model.model_manifest not in (connection.manifests)
            ):
                await self._error(connection, StableCode.BINDING_MISMATCH, now)
                return False
            await self._detach_for_resume(active.connection, now)
            active.connection = connection
            connection.lease = active
            resumed = True
        elif self._leases.active_lease_count and not self._allows_standby():
            await self._error(connection, StableCode.RESYNC_REQUIRED, now)
            return False
        connection.online_since = now
        self._connections[connection.id] = connection
        sent = await self._send(
            connection,
            wire.welcome(
                self._fields("worker.welcome", connection.minor, now),
                minor=connection.minor,
                connection_id=connection.id,
                resumed=resumed,
                manifests=connection.manifests,
            ),
            now,
        )
        if not sent:
            return False
        await self._issue_locked(now)
        return connection.open

    def _allows_standby(self) -> bool:
        return False

    async def _detach_for_resume(self, connection: _Connection, now: datetime) -> None:
        await self._detach(connection, now)

    async def _issue_locked(self, now: datetime) -> None:
        grant = self._grant
        if grant is None or self._leases.active_lease_count:
            return
        candidates = [
            connection
            for connection in self._connections.values()
            if connection.lease is None
            and self.device_checked(connection.id)
            and grant.manifest in connection.manifests
        ]
        if not candidates:
            return
        self._grant = None
        if len(candidates) != 1:
            self._void_sessions.add(grant.session_id)
            for connection in candidates:
                await self._detach(connection, now)
            return
        connection = candidates[0]
        model = wire.lease(
            self._fields("worker.lease", connection.minor, now),
            minor=connection.minor,
            lease_id=self._new_id(),
            session_id=grant.session_id,
            room_id=grant.room_id,
            issued_at=format_timestamp(now),
            expires_at=format_timestamp(now + LEASE_LIFETIME),
            manifest=grant.manifest,
        )
        coordinator = LeaseRuntimeCoordinator(
            accepted_manifests=frozenset(entry.key() for entry in self.identity.store.allowlist())
        )
        try:
            runtime = coordinator.create(model)
        except ProtocolValidationError as failure:
            await self._error(connection, failure.code, now)
            return
        self._issued_sessions.add(grant.session_id)
        active = _Lease(model, runtime, connection, int(model.input_start_seq), now)
        self._active = active
        connection.lease = active
        await self._send(connection, model, now)

    async def _received(
        self, connection: _Connection, frame: Mapping[str, Any], now: datetime
    ) -> None:
        text = frame.get("text")
        if not isinstance(text, str):
            body = frame.get("bytes")
            if not connection.binary_in.admit(now, BINARY_FRAMES_PER_WINDOW):
                await self._cancel(connection, "protocol_violation", now)
            elif isinstance(body, bytes) and len(body) > MAX_FRAME_LENGTH:
                await self._error(connection, StableCode.BINARY_FRAME_TOO_LARGE, now)
                await self._cancel(connection, "protocol_violation", now)
            else:
                await self._error(connection, StableCode.BINARY_HEADER_INVALID, now)
            return
        if not connection.text_in.admit(now, TEXT_FRAMES_PER_WINDOW):
            await self._cancel(connection, "protocol_violation", now)
            return
        try:
            message, raw = wire.parse_output(text, connection.minor)
        except ProtocolValidationError as failure:
            await self._error(connection, failure.code, now)
            if failure.code is StableCode.CONTROL_FRAME_TOO_LARGE:
                await self._cancel(connection, "protocol_violation", now)
            return
        await self._accept_output(connection, message, raw, now)

    async def _accept_output(
        self,
        connection: _Connection,
        message: wire.WorkerOutput,
        raw: dict[str, Any],
        now: datetime,
    ) -> None:
        active = connection.lease
        if active is None or active.connection is not connection:
            await self._error(connection, StableCode.LEASE_UNKNOWN, now)
            return
        decision = active.runtime.accept_output(raw, now=now)
        await self._acknowledge_output(active, message, decision, now)

    async def _acknowledge_output(
        self, active: _Lease, message: wire.WorkerOutput, decision: Decision, now: datetime
    ) -> None:
        connection = active.connection
        if not decision.accepted:
            await self._error(connection, decision.code, now)
            return
        if decision.code is StableCode.ACCEPTED:
            if isinstance(message, HeartbeatV1):
                active.heartbeat_at = now
                self.identity.record_health(connection.device_id, message.state, now)
            else:
                if isinstance(message, WorkerStatsV1):
                    self.identity.record_stats(connection.device_id, message)
                self._results[message.message_id] = None
                self._results.move_to_end(message.message_id)
                if len(self._results) > SEQUENCE_WINDOW_CAPACITY:
                    self._results.popitem(last=False)
        await self._send(
            connection,
            wire.ack(
                self._fields("protocol.ack", connection.minor, now),
                minor=connection.minor,
                message=message,
                outcome=decision.code,
            ),
            now,
        )

    async def _expire_locked(self, now: datetime) -> None:
        active = self._active
        if active is not None and now >= active.runtime.expires_at:
            self._finish_online(active.connection, active.runtime.expires_at)
            self._leases.prune(now)
        for connection in tuple(self._connections.values()):
            if not self.identity.device_usable(connection.device_id):
                await self._cancel(connection, "policy_disable", now)

    async def _cancel(self, connection: _Connection, reason: str, now: datetime) -> None:
        active = connection.lease
        if (
            active is not None
            and active.connection is connection
            and active.runtime.cancellation_active
            and now < active.runtime.expires_at
        ):
            model = wire.cancel(
                self._fields("worker.lease_cancel", connection.minor, now),
                minor=connection.minor,
                active_lease=active.model,
                revision=active.runtime.lease_revision,
                reason=reason,
            )
            active.runtime.cancel(model, model.model_dump(mode="json"), now)
            await self._send(connection, model, now)
        await self._detach(connection, now)

    async def _error(self, connection: _Connection, code: str, now: datetime) -> None:
        await self._send(
            connection,
            wire.error(
                self._fields("protocol.error", connection.minor, now),
                minor=connection.minor,
                code=code,
            ),
            now,
        )

    async def _send(self, connection: _Connection, model: StrictModel, now: datetime) -> bool:
        data = canonical_json(model.model_dump(mode="json"))
        if (
            not connection.open
            or len(data) > MAX_CONTROL_BYTES
            or not connection.text_out.admit(now, CONTROL_FRAMES_PER_WINDOW)
        ):
            await self._detach(connection, now)
            return False
        try:
            await asyncio.wait_for(
                connection.socket.send_text(data.decode("utf-8")), SEND_TIMEOUT_SECONDS
            )
        except (TimeoutError, OSError, RuntimeError, WebSocketDisconnect):
            await self._detach(connection, now)
            return False
        return True

    def _finish_online(self, connection: _Connection, now: datetime) -> None:
        began, connection.online_since = connection.online_since, None
        if began is not None:
            connection.identity.note_online(connection.device_id, began, now)

    async def _detach(self, connection: _Connection, now: datetime) -> None:
        if not connection.open:
            return
        connection.open = False
        self._connections.pop(connection.id, None)
        self._finish_online(connection, now)
        active = connection.lease
        if active is not None and active.connection is connection:
            active.runtime.consume_pcm(active.runtime.buffered_audio_bytes)
        await _close(connection.socket, 1008)


async def _close(socket: WebSocket, code: int) -> None:
    with contextlib.suppress(TimeoutError, OSError, RuntimeError, WebSocketDisconnect):
        await asyncio.wait_for(socket.close(code=code), SEND_TIMEOUT_SECONDS)


def create_worker_gateway_app(gateway: WorkerGateway) -> FastAPI:
    app = FastAPI(title="Livecho worker gateway", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_api_websocket_route(WORKER_PATH, gateway.serve)
    return app
