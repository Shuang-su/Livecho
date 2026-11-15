"""Local vertical orchestration: fixture timeline, viewer admission, and publication."""

from __future__ import annotations

import asyncio
import contextlib
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from livecho_protocol.compatibility import negotiate_viewer
from livecho_protocol.errors import StableCode
from livecho_protocol.models import (
    MINIMUM_VIEWER_VERSION,
    PROTOCOL_MINOR,
    VIEWER_PROTOCOL,
    ProtocolErrorV1,
    TimelineEventV1,
    TranscriptTimelinePayloadV1,
    ViewerCursorV1,
    ViewerReadyV1,
    ViewerSubscribeV1,
)
from livecho_protocol.parser import canonical_json, strict_json_loads, validate_object
from livecho_protocol.state import (
    REVISION_DOMAIN_CAPACITY,
    LiveViewerCursor,
    StreamOrderingState,
    decide_viewer_resume,
)
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .config import (
    PRE_TERMINAL_DRAIN_SECONDS,
    VIEWER_ENDPOINT_PATH,
    LocalVerticalConfig,
    LocalVerticalMode,
)
from .fanout import ViewerConnection, ViewerRegistry
from .observations import LocalVerticalObservations
from .schedule import FixtureScheduleSpec, run_fixture_schedule
from .timeline import (
    LocalTimeline,
    RevisionCapacityExceeded,
    event_is_terminal,
    utc_stamp,
)


class ModeBlockedError(Exception):
    """Requested mode is closed until separate execution evidence exists."""

    def __init__(self, mode: LocalVerticalMode) -> None:
        self.mode = mode
        super().__init__(f"mode blocked: {mode.value}")


class _NoStoreHeaders(BaseHTTPMiddleware):
    """Apply Cache-Control: no-store to every HTTP response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response


@dataclass(slots=True)
class LocalVerticalService:
    """Fixture-only local caption vertical without worker, audio, or leases."""

    config: LocalVerticalConfig
    timeline: LocalTimeline = field(init=False)
    registry: ViewerRegistry = field(init=False)
    observations: LocalVerticalObservations = field(init=False)
    ingest_open: bool = True
    schedule_generation: int = 0
    run_generation: int = 0
    _publish_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _schedule_task: asyncio.Task[None] | None = None

    def __post_init__(self) -> None:
        self.timeline = LocalTimeline(
            session_id=str(uuid.uuid4()),
            room_id=self.config.room_id,
        )
        self.observations = LocalVerticalObservations()
        self.registry = ViewerRegistry(self.observations)

    def blocked_evidence(self) -> dict[str, object]:
        """Payload-free blocked run diagnostics for closed MLX admission."""
        return {
            "mode": LocalVerticalMode.SYNTHETIC_MLX.value,
            "outcome": "blocked_evidence",
            "real_asr_evidence": False,
            "partial_availability": self.observations.partial_availability,
            "cross_process_latency": self.observations.cross_process_latency,
        }

    async def start_fixture_session(self, spec: FixtureScheduleSpec | None = None) -> None:
        if self.config.mode != LocalVerticalMode.FIXTURE_TIMELINE:
            raise ModeBlockedError(self.config.mode)
        if spec is None:
            spec = FixtureScheduleSpec()
        self.ingest_open = True
        self.schedule_generation += 1
        self.run_generation = self.schedule_generation
        generation = self.schedule_generation
        self.timeline.reset_session(room_id=self.config.room_id)
        self.registry.retained.clear()
        if self._schedule_task is not None:
            self._schedule_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._schedule_task
        self._schedule_task = asyncio.create_task(
            run_fixture_schedule(self, spec, generation=generation)
        )

    async def _publish_locked(
        self,
        build: Callable[[], tuple[dict[str, Any], int]],
    ) -> None:
        async with self._publish_lock:
            message, seq = build()
            wire = canonical_json(message)
            terminal = event_is_terminal(message)
            self.observations.publish_count += 1
            if terminal:
                await self.registry.fanout_terminal(
                    wire,
                    seq,
                    pre_terminal_drain_seconds=PRE_TERMINAL_DRAIN_SECONDS,
                )
            else:
                await self.registry.fanout_event(wire, seq, is_terminal=False)

    def _commit_timeline_event(self, message: dict[str, Any]) -> int:
        seq = int(str(message["seq"]))
        started = time.monotonic()
        self.timeline.accept_timeline_event(message)
        self.observations.record_publish_interval((time.monotonic() - started) * 1_000)
        return seq

    def _build_status_event(
        self,
        status: str,
        *,
        reason_code: str | None = None,
    ) -> tuple[dict[str, Any], int]:
        payload: dict[str, object]
        if reason_code is None:
            payload = {"status": status}
        else:
            payload = {"status": status, "reason_code": reason_code}
        seq = self.timeline.allocate_seq()
        message = {
            **self.timeline.envelope_fields(),
            "type": "viewer.timeline_event",
            "event_id": str(uuid.uuid4()),
            "session_id": self.timeline.session_id,
            "room_id": self.timeline.room_id,
            "epoch": str(self.timeline.epoch),
            "seq": str(seq),
            "revision": "1",
            "occurred_at": utc_stamp(),
            "payload": payload,
        }
        validate_object(message, TimelineEventV1)
        self._commit_timeline_event(message)
        return message, seq

    def _build_transcript_event(
        self,
        *,
        event_id: str,
        segment_id: str,
        start_ms: int,
        end_ms: int,
        text: str,
        is_final: bool,
        occurred_at: str,
        revision: int,
    ) -> tuple[dict[str, Any], int]:
        seq = self.timeline.allocate_seq()
        payload = TranscriptTimelinePayloadV1(
            segment_id=segment_id,
            start_ms=start_ms,
            end_ms=end_ms,
            text=text,
            is_final=is_final,
        )
        message = {
            **self.timeline.envelope_fields(),
            "type": "viewer.timeline_event",
            "event_id": event_id,
            "session_id": self.timeline.session_id,
            "room_id": self.timeline.room_id,
            "epoch": str(self.timeline.epoch),
            "seq": str(seq),
            "revision": str(revision),
            "occurred_at": occurred_at,
            "payload": payload.model_dump(mode="json"),
        }
        validate_object(message, TimelineEventV1)
        self._commit_timeline_event(message)
        return message, seq

    async def publish_status(
        self,
        status: str,
        reason_code: str | None = None,
    ) -> None:
        if self.run_generation != self.schedule_generation:
            return
        await self._publish_locked(
            lambda: self._build_status_event(status, reason_code=reason_code)
        )

    async def publish_transcript(
        self,
        *,
        event_id: str,
        segment_id: str,
        start_ms: int,
        end_ms: int,
        text: str,
        is_final: bool,
        occurred_at: str,
        revision: int = 1,
    ) -> None:
        if self.run_generation != self.schedule_generation or not self.ingest_open:
            return

        def build() -> tuple[dict[str, Any], int]:
            return self._build_transcript_event(
                event_id=event_id,
                segment_id=segment_id,
                start_ms=start_ms,
                end_ms=end_ms,
                text=text,
                is_final=is_final,
                occurred_at=occurred_at,
                revision=revision,
            )

        try:
            await self._publish_locked(build)
        except RevisionCapacityExceeded:
            self.observations.revision_capacity_rejects += 1
            await self.fail_session("protocol_failed")

    async def operator_stop(self) -> None:
        await self._invalidate_schedule()
        await self.publish_status("stopping")
        await self.publish_status("stopped")

    async def close_ingest(self) -> None:
        self.ingest_open = False
        await self._invalidate_schedule()

    async def delete_session(self) -> None:
        await self._invalidate_schedule()
        await self.publish_status("stopped", "session_deleted")

    async def fail_session(self, reason: str = "protocol_failed") -> None:
        await self._invalidate_schedule()
        await self.publish_status("failed", reason)

    async def _invalidate_schedule(self) -> None:
        self.ingest_open = False
        self.schedule_generation += 1
        if self._schedule_task is not None:
            self._schedule_task.cancel()
            self._schedule_task = None

    async def handle_viewer_websocket(self, websocket: WebSocket) -> None:
        await websocket.accept(subprotocol=VIEWER_PROTOCOL)
        connection = ViewerConnection(
            send_json=lambda payload: websocket.send_bytes(payload),
            close_socket=lambda: websocket.close(code=1000),
            observations=self.observations,
        )
        admitted_id: int | None = None
        stored: ViewerConnection | None = None
        try:
            raw = await websocket.receive_text()
            payload = strict_json_loads(raw)
            subscribe = validate_object(payload, ViewerSubscribeV1)
            negotiation = negotiate_viewer(subscribe)
            if not negotiation.decision.accepted:
                await self._send_protocol_error(websocket, negotiation.decision.code.value, False)
                return
            if subscribe.room_id != self.config.room_id:
                await self._send_protocol_error(websocket, "binding_mismatch", False)
                return

            if subscribe.cursor is not None:
                if not await self._admit_resume(websocket, connection, subscribe.cursor):
                    return
            elif not await self._admit_fresh(websocket, connection):
                return

            admitted_id = self.registry.admit(connection)
            if admitted_id is None:
                await websocket.close(code=1013)
                return

            try:
                while True:
                    message = await websocket.receive()
                    if message.get("type") == "websocket.disconnect":
                        break
            except WebSocketDisconnect:
                pass
        except WebSocketDisconnect:
            pass
        finally:
            if admitted_id is not None:
                stored = self.registry.remove(admitted_id)
            else:
                for candidate_id, candidate in list(self.registry.active.items()):
                    if candidate is connection:
                        stored = self.registry.remove(candidate_id)
                        break
            if stored is not None and stored.next_seq is not None:
                cursor = LiveViewerCursor(
                    session_id=self.timeline.session_id,
                    epoch=self.timeline.epoch,
                    next_seq=stored.next_seq,
                )
                ordering = StreamOrderingState(
                    session_id=self.timeline.session_id,
                    lease_id=None,
                    epoch=self.timeline.epoch,
                    start_seq=cursor.next_seq,
                    revision_capacity=REVISION_DOMAIN_CAPACITY,
                )
                self.registry.retain_domain(cursor, ordering)
            if stored is not None and stored.sender_task is not None:
                stored.sender_task.cancel()

    async def _send_protocol_error(
        self,
        websocket: WebSocket,
        code: str,
        retryable: bool,
    ) -> None:
        frame = validate_object(
            {
                "protocol": VIEWER_PROTOCOL,
                "protocol_minor": PROTOCOL_MINOR,
                "message_id": str(uuid.uuid4()),
                "sent_at": utc_stamp(),
                "type": "protocol.error",
                "code": code,
                "message": "Rejected viewer admission",
                "retryable": retryable,
            },
            ProtocolErrorV1,
        )
        await websocket.send_bytes(canonical_json(frame.model_dump(mode="json")))
        await websocket.close(code=1000)

    async def _admit_fresh(self, websocket: WebSocket, connection: ViewerConnection) -> bool:
        if not self.timeline.fresh_admission_allowed():
            self.observations.resync_required_count += 1
            self.observations.viewer_refuse_count += 1
            await self._send_protocol_error(websocket, "resync_required", True)
            return False
        async with self._publish_lock:
            status_message, status_seq = self._build_status_event(
                self.timeline.session_status,
                reason_code=self.timeline.reason_code,
            )
            ready = validate_object(
                {
                    "protocol": VIEWER_PROTOCOL,
                    "protocol_minor": PROTOCOL_MINOR,
                    "message_id": str(uuid.uuid4()),
                    "sent_at": utc_stamp(),
                    "type": "viewer.ready",
                    "selected_minor": 0,
                    "minimum_client_version": MINIMUM_VIEWER_VERSION,
                    "session_id": self.timeline.session_id,
                    "epoch": str(self.timeline.epoch),
                    "next_seq": str(status_seq),
                    "cursor_resumed": False,
                },
                ViewerReadyV1,
            )
            connection.next_seq = status_seq
            await websocket.send_bytes(canonical_json(ready.model_dump(mode="json")))
            status_wire = canonical_json(status_message)
            await websocket.send_bytes(status_wire)
            connection.next_seq = status_seq + 1
            for _viewer_id, viewer in list(self.registry.active.items()):
                if viewer is connection:
                    continue
                viewer.offer(
                    status_wire,
                    status_seq,
                    is_terminal=event_is_terminal(status_message),
                )
        return True

    async def _admit_resume(
        self,
        websocket: WebSocket,
        connection: ViewerConnection,
        cursor: ViewerCursorV1,
    ) -> bool:
        live = LiveViewerCursor(
            session_id=self.timeline.session_id,
            epoch=self.timeline.epoch,
            next_seq=int(cursor.next_seq),
        )
        decision = decide_viewer_resume(cursor, live)
        if decision.code != StableCode.ACCEPTED:
            retained = self.registry.find_resume_domain(live)
            if retained is None:
                self.observations.resync_required_count += 1
                self.observations.viewer_refuse_count += 1
                await self._send_protocol_error(websocket, "resync_required", True)
                return False
            live = retained.cursor
            decision = decide_viewer_resume(cursor, live)
        if decision.code != StableCode.ACCEPTED:
            self.observations.resync_required_count += 1
            self.observations.viewer_refuse_count += 1
            await self._send_protocol_error(websocket, "resync_required", True)
            return False
        ready = validate_object(
            {
                "protocol": VIEWER_PROTOCOL,
                "protocol_minor": PROTOCOL_MINOR,
                "message_id": str(uuid.uuid4()),
                "sent_at": utc_stamp(),
                "type": "viewer.ready",
                "selected_minor": 0,
                "minimum_client_version": MINIMUM_VIEWER_VERSION,
                "session_id": live.session_id,
                "epoch": str(live.epoch),
                "next_seq": str(live.next_seq),
                "cursor_resumed": True,
            },
            ViewerReadyV1,
        )
        connection.next_seq = live.next_seq
        await websocket.send_bytes(canonical_json(ready.model_dump(mode="json")))
        return True


def create_local_vertical_app(service: LocalVerticalService) -> FastAPI:
    """Create a loopback FastAPI application with the viewer WebSocket route."""

    app = FastAPI(title="Livecho local vertical", docs_url=None, redoc_url=None)
    app.add_middleware(_NoStoreHeaders)

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "mode": service.config.mode.value})

    @app.websocket(VIEWER_ENDPOINT_PATH)
    async def viewer_ws(websocket: WebSocket) -> None:
        origin = websocket.headers.get("origin")
        if origin is not None and origin not in service.config.allowed_origins():
            await websocket.close(code=1008)
            return
        await service.handle_viewer_websocket(websocket)

    return app
