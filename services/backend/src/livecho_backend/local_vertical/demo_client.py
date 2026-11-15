"""Stdout demo viewer that validates frames with shared protocol models."""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass

import websockets
from livecho_protocol.models import (
    MINIMUM_VIEWER_VERSION,
    PROTOCOL_MINOR,
    VIEWER_PROTOCOL,
    SessionStatusTimelinePayloadV1,
    TimelineEventV1,
    TranscriptTimelinePayloadV1,
    ViewerSubscribeV1,
)
from livecho_protocol.parser import strict_json_loads, validate_object
from livecho_protocol.state import StreamOrderingState

from .config import DEFAULT_ROOM_ID, VIEWER_ENDPOINT_PATH
from .timeline import utc_stamp


@dataclass(slots=True)
class DemoClientResult:
    """Outcome of a fixture demo viewer run."""

    exit_code: int
    terminal_status: str | None


async def run_demo_client(
    *,
    host: str,
    port: int,
    room_id: str = DEFAULT_ROOM_ID,
) -> DemoClientResult:
    """Connect to the local viewer socket and print synthetic captions."""
    url = f"ws://{host}:{port}{VIEWER_ENDPOINT_PATH}"
    subscribe = validate_object(
        {
            "protocol": VIEWER_PROTOCOL,
            "protocol_minor": PROTOCOL_MINOR,
            "message_id": str(uuid.uuid4()),
            "sent_at": utc_stamp(),
            "type": "viewer.subscribe",
            "client_version": MINIMUM_VIEWER_VERSION,
            "supported_minors": [0],
            "room_id": room_id,
        },
        ViewerSubscribeV1,
    )
    terminal_status: str | None = None

    for attempt in range(8):
        resync_retry = False
        try:
            async with websockets.connect(
                url,
                subprotocols=[VIEWER_PROTOCOL],  # type: ignore[list-item]
                open_timeout=5,
                close_timeout=2,
            ) as websocket:
                await websocket.send(json.dumps(subscribe.model_dump(mode="json")))
                ordering: StreamOrderingState | None = None
                while True:
                    try:
                        raw = await websocket.recv()
                    except websockets.ConnectionClosed:
                        break
                    if isinstance(raw, bytes):
                        payload = strict_json_loads(raw)
                    else:
                        payload = strict_json_loads(raw.encode("utf-8"))
                    message_type = payload.get("type")
                    if message_type == "protocol.error":
                        if bool(payload.get("retryable")) and attempt + 1 < 8:
                            resync_retry = True
                        break
                    if message_type == "viewer.ready":
                        session_id = str(payload["session_id"])
                        epoch = int(str(payload["epoch"]))
                        next_seq = int(str(payload["next_seq"]))
                        ordering = StreamOrderingState(
                            session_id=session_id,
                            lease_id=None,
                            epoch=epoch,
                            start_seq=next_seq,
                        )
                        continue
                    if message_type != "viewer.timeline_event":
                        continue
                    event = validate_object(payload, TimelineEventV1)
                    if ordering is not None:
                        decision = ordering.accept(payload)
                        if not decision.accepted:
                            return DemoClientResult(exit_code=1, terminal_status=terminal_status)
                    branch = event.payload
                    if isinstance(branch, TranscriptTimelinePayloadV1):
                        label = "FINAL" if branch.is_final else "PARTIAL"
                        print(f"[{label}] {branch.text}")
                    elif isinstance(branch, SessionStatusTimelinePayloadV1):
                        print(f"[STATUS] {branch.status}")
                        if branch.status in {"stopped", "failed"}:
                            terminal_status = branch.status
                            return DemoClientResult(exit_code=0, terminal_status=terminal_status)
                        if branch.status == "stopping":
                            continue
        except OSError:
            if attempt + 1 >= 8:
                return DemoClientResult(exit_code=1, terminal_status=terminal_status)
        if resync_retry:
            await asyncio.sleep(0.35)
            continue
        if terminal_status is not None:
            return DemoClientResult(exit_code=0, terminal_status=terminal_status)
        if attempt + 1 < 8:
            await asyncio.sleep(0.1)
    return DemoClientResult(exit_code=1, terminal_status=terminal_status)


def run_demo_client_sync(host: str, port: int, room_id: str = DEFAULT_ROOM_ID) -> DemoClientResult:
    return asyncio.run(run_demo_client(host=host, port=port, room_id=room_id))