"""Three proof-bound workers and independent live viewers on actual loopback WSS."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, replace
from datetime import timedelta
from pathlib import Path
from ssl import SSLContext
from time import monotonic
from typing import Any
from uuid import uuid4

import pytest
from fastapi import WebSocket
from livecho_backend.worker_failover.app import create_failover_app
from livecho_backend.worker_failover.gateway import SyntheticFailoverGateway, SyntheticObservation
from livecho_protocol.binary import PcmHeaderV1, encode_header
from livecho_protocol.errors import StableCode
from livecho_protocol.models import ModelManifestRefV1, TranscriptSegmentV1Minor1
from livecho_protocol.state import REVISION_DOMAIN_CAPACITY
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed
from websockets.typing import Subprotocol

from tests.worker_gateway.support import (
    Device,
    connect_worker,
    enroll,
    read_control,
    send_control,
    serve_gateway,
    worker_output,
)
from tests.worker_identity.support import MANIFEST, World, hello_for

ROOM = "livecho.fixture.room"
PROTOCOL = Subprotocol("livecho.viewer.v1")
WEB = Path(__file__).resolve().parents[2] / "apps/web"


@dataclass(slots=True)
class Worker:
    device: Device
    socket: ClientConnection
    connection_id: str


def _setup(
    count: int = 3,
) -> tuple[World, SyntheticFailoverGateway, list[Device], list[SyntheticObservation]]:
    world = World()
    devices = [enroll(world) for _ in range(count)]
    world.allow()
    observations = [
        SyntheticObservation(world.clock.now + timedelta(minutes=3), True, count - index, 0.8, 0.99)
        for index in range(count)
    ]
    gateway = SyntheticFailoverGateway(
        world.service,
        session_id=str(uuid4()),
        room_id=ROOM,
        manifest=ModelManifestRefV1.model_validate(MANIFEST),
        observations=dict(zip((device.id for device in devices), observations, strict=True)),
        clock=world.clock,
    )
    return world, gateway, devices, observations


async def _arm(gateway: SyntheticFailoverGateway) -> None:
    assert await gateway.arm_grant(gateway.session_id, ROOM, gateway.manifest)


async def _workers(
    stack: AsyncExitStack, url: str, tls: SSLContext, world: World, devices: list[Device]
) -> list[Worker]:
    workers: list[Worker] = []
    # Reverse admission order to prove the scheduler follows measurements.
    for device in reversed(devices):
        socket = await stack.enter_async_context(connect_worker(url, tls, device.challenge(world)))
        await send_control(socket, hello_for(device.id, minor1=True))
        welcome = await read_control(socket)
        assert welcome["type"] == "worker.welcome" and welcome["selected_minor"] == 1
        workers.insert(0, Worker(device, socket, welcome["connection_id"]))
    return workers


async def _subscribe(
    client: ClientConnection,
    cursor: dict[str, str] | None = None,
    *,
    minors: list[int] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "protocol": str(PROTOCOL),
        "protocol_minor": 0,
        "message_id": str(uuid4()),
        "sent_at": "2026-01-01T00:00:00.000Z",
        "type": "viewer.subscribe",
        "client_version": "0.1.0",
        "supported_minors": [0, 1] if minors is None else minors,
        "room_id": ROOM,
    }
    if cursor is not None:
        body["cursor"] = cursor
    await send_control(client, body)
    return await read_control(client)


def _viewer(url: str, tls: SSLContext, *, user_agent: str = "Livecho fixture viewer") -> connect:
    return connect(
        url.replace("/api/worker/ws", "/api/viewer/ws"),
        ssl=tls,
        proxy=None,
        user_agent_header=user_agent,
        subprotocols=[PROTOCOL],
        open_timeout=3,
        close_timeout=2,
    )


def _pcm(lease: dict[str, Any], pts_ms: int, *, seq: int = 1) -> bytes:
    return encode_header(
        PcmHeaderV1(lease["lease_id"], int(lease["epoch"]), seq, pts_ms, 320, 640, protocol_minor=1)
    ) + bytes(640)


async def _assert_only_primary(
    gateway: SyntheticFailoverGateway, active: Worker, standbys: list[Worker]
) -> None:
    assert gateway.lease_valid(active.connection_id)
    for standby in standbys:
        assert not gateway.lease_valid(standby.connection_id)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(standby.socket.recv(), 0.025)


async def _send_caption(
    worker: Worker, lease: dict[str, Any], seq: int, **changes: Any
) -> dict[str, Any]:
    message = worker_output("TranscriptSegmentV1", lease, seq, **changes)
    await send_control(worker.socket, message)
    return message


@asynccontextmanager
async def _browser(url: str, enabled: bool) -> AsyncIterator[Callable[[str], Awaitable[None]]]:
    """Optional Chromium drives the same TLS application alongside Python peers."""
    if not enabled:

        async def skip(stage: str) -> None:
            pass

        yield skip
        return

    node = await asyncio.create_subprocess_exec(
        "node",
        str(WEB / "tests/e2e-python/failover-probe.mjs"),
        url.replace("wss://", "https://").removesuffix("/api/worker/ws"),
        cwd=WEB,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )

    async def check(stage: str) -> None:
        assert node.stdin is not None and node.stdout is not None
        node.stdin.write(stage.encode() + b"\n")
        await node.stdin.drain()
        assert await asyncio.wait_for(node.stdout.readline(), 12) == stage.encode() + b"\n"

    try:
        yield check
    finally:
        assert node.stdin is not None
        node.stdin.close()
        try:
            await asyncio.wait_for(node.wait(), 8)
        except TimeoutError:
            node.kill()
            await node.wait()
            raise
    assert node.returncode == 0


@pytest.mark.parametrize("fault", ["disconnect", "expiry"])
def test_three_worker_live_failover(fault: str, monkeypatch: pytest.MonkeyPatch) -> None:
    world, gateway, devices, _ = _setup()
    blocked = asyncio.Event()
    never = asyncio.Event()
    actual_send = WebSocket.send_text
    use_browser = os.environ.get("LIVECHO_FAILOVER_BROWSER") == "1" and fault == "expiry"

    async def block_one_viewer(socket: WebSocket, data: str) -> None:
        if (
            socket.headers.get("user-agent") == "Livecho blocked fixture viewer"
            and '"type":"viewer.timeline_event"' in data
        ):
            blocked.set()
            await never.wait()
        await actual_send(socket, data)

    monkeypatch.setattr(WebSocket, "send_text", block_one_viewer)

    async def scenario() -> None:
        app = create_failover_app(gateway, WEB / "dist" if use_browser else None)
        async with serve_gateway(app) as (url, tls), AsyncExitStack() as stack:
            stack.push_async_callback(gateway.stop)
            primary, backup, last = await _workers(stack, url, tls, world, devices)
            viewer = await stack.enter_async_context(_viewer(url, tls))
            slow = await stack.enter_async_context(
                _viewer(url, tls, user_agent="Livecho blocked fixture viewer")
            )
            assert (await _subscribe(viewer))["next_seq"] == "1"
            assert (await _subscribe(slow))["type"] == "viewer.ready"
            browser = await stack.enter_async_context(_browser(url, use_browser))
            await browser("ready")
            await _arm(gateway)
            lease = await read_control(primary.socket)
            assert lease["epoch"] == "1"
            await _assert_only_primary(gateway, primary, [backup, last])
            frame = _pcm(lease, 0)
            assert await gateway.submit_synthetic_pcm(lease["lease_id"], frame)
            assert await asyncio.wait_for(primary.socket.recv(), 2) == frame
            await _assert_only_primary(gateway, primary, [backup, last])

            world.clock.advance(timedelta(seconds=18))
            heartbeat = worker_output("HeartbeatV1", lease, 1)
            await send_control(primary.socket, heartbeat)
            assert (await read_control(primary.socket))["outcome"] == "accepted"
            last_heartbeat = monotonic()
            assert gateway.heartbeat_healthy(primary.connection_id)

            await _send_caption(
                primary,
                lease,
                2,
                text="Synthetic outgoing partial",
                is_final=False,
                start_ms=0,
                end_ms=20,
                segment_id=str(uuid4()),
            )
            assert (await read_control(primary.socket))["outcome"] == "accepted"
            assert (await read_control(viewer))["payload"]["is_final"] is False
            await asyncio.wait_for(blocked.wait(), 1)
            await browser("partial")
            await _send_caption(
                primary,
                lease,
                3,
                text="Synthetic queued old text",
                is_final=False,
                start_ms=0,
                end_ms=20,
                segment_id=str(uuid4()),
            )
            assert (await read_control(primary.socket))["outcome"] == "accepted"
            assert (await read_control(viewer))["seq"] == "2"
            stale_viewer = await stack.enter_async_context(_viewer(url, tls))
            waiting = asyncio.create_task(
                _subscribe(
                    stale_viewer,
                    {"session_id": gateway.session_id, "epoch": "1", "next_seq": "1"},
                )
            )
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(waiting), 0.01)

            fault_at = monotonic()
            if fault == "expiry":
                world.clock.advance(timedelta(seconds=2))
                await gateway.expire_due()
                rotation = await read_control(primary.socket)
                assert rotation["type"] == "worker.epoch_rotated"
                assert rotation["reason"] == "lease_replaced"
                assert rotation["pcm_continue_pts"] == "20"
            else:
                await primary.socket.close()
            gap = await read_control(viewer)
            gap_at = monotonic()
            assert (gap["type"], gap["epoch"], gap["next_seq"], gap["gap"]) == (
                "viewer.resync",
                "2",
                "1",
                True,
            )
            assert gap["reason"] == "epoch_rotated"
            rebuilt = await waiting
            assert (rebuilt["type"], rebuilt["epoch"], rebuilt["reason"]) == (
                "viewer.resync",
                "2",
                "epoch_rotated",
            )
            successor = await read_control(backup.socket)
            lease_at = monotonic()
            assert successor["session_id"] == lease["session_id"]
            assert successor["type"] == "worker.lease"
            assert successor["lease_id"] != lease["lease_id"]
            assert (
                successor["epoch"],
                successor["input_start_seq"],
                successor["output_start_seq"],
            ) == ("2", "1", "1")
            assert not gateway.lease_valid(primary.connection_id)
            assert not await gateway.submit_synthetic_pcm(lease["lease_id"], frame)
            assert not await gateway.consume_pcm(lease["lease_id"], 640)
            await _assert_only_primary(gateway, backup, [last])
            with pytest.raises(ConnectionClosed):
                await asyncio.wait_for(slow.recv(), 1)

            if fault == "expiry":
                with pytest.raises(ConnectionClosed):
                    await asyncio.wait_for(primary.socket.recv(), 1)

            await browser("gap")
            assert not await gateway.submit_synthetic_pcm(successor["lease_id"], _pcm(successor, 0))
            frame = _pcm(successor, 60)
            assert await gateway.submit_synthetic_pcm(successor["lease_id"], frame)
            assert await asyncio.wait_for(backup.socket.recv(), 2) == frame
            final = await _send_caption(
                backup,
                successor,
                1,
                text="Synthetic successor final",
                is_final=True,
                start_ms=60,
                end_ms=80,
                segment_id=str(uuid4()),
            )
            assert (await read_control(backup.socket))["outcome"] == "accepted"
            final_at = monotonic()
            assert gateway.result_accepted(final["message_id"])
            event = await read_control(viewer)
            assert (event["epoch"], event["seq"], event["payload"]["start_ms"]) == ("2", "1", 60)
            await send_control(backup.socket, final)
            assert (await read_control(backup.socket))["outcome"] == "seq_duplicate"
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(viewer.recv(), 0.025)
            await browser("final")

            cursor = {"session_id": gateway.session_id, "epoch": "2", "next_seq": "2"}
            async with _viewer(url, tls) as resumed:
                ready = await _subscribe(resumed, cursor)
                assert ready["type"] == "viewer.ready" and ready["cursor_resumed"]
                assert ready["next_seq"] == "2"
            for epoch, next_seq, reason in (
                ("2", "1", "cursor_expired"),
                ("1", "3", "epoch_rotated"),
                ("20", "1", "cursor_unknown"),
            ):
                async with _viewer(url, tls) as stale:
                    resync = await _subscribe(stale, dict(cursor, epoch=epoch, next_seq=next_seq))
                    assert (resync["type"], resync["reason"], resync["next_seq"]) == (
                        "viewer.resync",
                        reason,
                        "2",
                    )
                    with pytest.raises(TimeoutError):
                        await asyncio.wait_for(stale.recv(), 0.025)
            async with _viewer(url, tls) as wrong:
                assert (await _subscribe(wrong, dict(cursor, session_id=str(uuid4()))))["code"] == (
                    "binding_mismatch"
                )
            async with _viewer(url, tls) as minor0:
                rejected = await _subscribe(minor0, minors=[0])
                assert rejected["code"] == "unsupported_minor" and rejected["protocol_minor"] == 0

            await backup.socket.close()
            assert (await read_control(viewer))["epoch"] == "3"
            third_lease = await read_control(last.socket)
            assert third_lease["epoch"] == "3"
            await _assert_only_primary(gateway, last, [])
            # A retired worker releases its slot and can come back on a new proof,
            # without ever inheriting the current primary's lease.
            async with connect_worker(url, tls, primary.device.challenge(world)) as rejoined:
                await send_control(rejoined, hello_for(primary.device.id, minor1=True))
                new_welcome = await read_control(rejoined)
                assert new_welcome["type"] == "worker.welcome"
                assert not gateway.lease_valid(new_welcome["connection_id"])
            assert final_at - last_heartbeat <= 60
            print(
                f"{fault}: heartbeat-to-final={1000 * (final_at - last_heartbeat):.1f}ms; "
                f"fault-to-gap={1000 * (gap_at - fault_at):.1f}ms; "
                f"fault-to-lease={1000 * (lease_at - fault_at):.1f}ms; "
                f"gap-to-final={1000 * (final_at - gap_at):.1f}ms; "
                "live source skipped 40ms beyond the retired PCM cursor"
            )

    asyncio.run(scenario())


@pytest.mark.parametrize("unavailable", ["no_backup", "cold", "all_slow", "stale"])
def test_gap_without_eligible_backup_and_fresh_selection(unavailable: str) -> None:
    world, gateway, devices, observed = _setup(1 if unavailable == "no_backup" else 3)

    async def scenario() -> None:
        async with (
            serve_gateway(create_failover_app(gateway)) as (url, tls),
            AsyncExitStack() as stack,
        ):
            stack.push_async_callback(gateway.stop)
            primary, *standbys = await _workers(stack, url, tls, world, devices)
            viewer = await stack.enter_async_context(_viewer(url, tls))
            await _subscribe(viewer)
            for standby, measurement in zip(standbys, observed[1:], strict=True):
                settings = {
                    "cold": replace(measurement, warm=False),
                    "all_slow": replace(measurement, realtime_factor=1.25),
                    "stale": replace(measurement, fresh_until=world.clock.now),
                }
                await gateway.observe(standby.device.id, settings[unavailable])
            if unavailable == "all_slow":
                await gateway.observe(primary.device.id, replace(observed[0], realtime_factor=2))
                await _arm(gateway)
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(primary.socket.recv(), 0.025)
                await gateway.observe(primary.device.id, observed[0])
            else:
                await _arm(gateway)
            lease = await read_control(primary.socket)
            assert lease["type"] == "worker.lease"
            await primary.socket.close()
            assert (await read_control(viewer))["gap"] is True
            assert gateway.protocol.active_lease_runtime is None
            assert not await gateway.submit_synthetic_pcm(lease["lease_id"], _pcm(lease, 0))
            for standby in standbys:
                assert not gateway.lease_valid(standby.connection_id)
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(standby.socket.recv(), 0.025)
            if standbys:
                await gateway.observe(standbys[0].device.id, observed[1])
                assert (await read_control(standbys[0].socket))["epoch"] == "2"

    asyncio.run(scenario())


def test_capacity_trigger_publishes_resync_and_does_not_acknowledge_candidate() -> None:
    world, gateway, devices, _ = _setup(1)

    async def scenario() -> None:
        async with (
            serve_gateway(create_failover_app(gateway)) as (url, tls),
            AsyncExitStack() as stack,
        ):
            stack.push_async_callback(gateway.stop)
            (worker,) = await _workers(stack, url, tls, world, devices)
            await _arm(gateway)
            lease = await read_control(worker.socket)
            # Prime with accepted protocol frames without attempting to squeeze
            # 4,095 WSS messages into a 20-second immutable, rate-limited lease.
            for seq in range(1, REVISION_DOMAIN_CAPACITY):
                message = TranscriptSegmentV1Minor1.model_validate(
                    worker_output(
                        "TranscriptSegmentV1",
                        lease,
                        seq,
                        segment_id=str(uuid4()),
                        start_ms=0,
                        end_ms=20,
                        is_final=True,
                    )
                )
                now = world.clock.now
                admission = gateway.protocol.accept_worker(message, now=now)
                assert admission.decision.code is StableCode.ACCEPTED
                timeline = gateway.protocol.accept_viewer_event(
                    gateway._caption(message, now), now=now
                )
                assert timeline.decision.code is StableCode.ACCEPTED
            async with _viewer(url, tls) as viewer:
                ready = await _subscribe(viewer)
                assert ready["next_seq"] == str(REVISION_DOMAIN_CAPACITY)
                await _send_caption(
                    worker,
                    lease,
                    REVISION_DOMAIN_CAPACITY,
                    segment_id=str(uuid4()),
                    start_ms=0,
                    end_ms=20,
                    is_final=True,
                )
                assert (await read_control(worker.socket))["outcome"] == "accepted"
                assert (await read_control(viewer))["seq"] == str(REVISION_DOMAIN_CAPACITY)
                rejected = await _send_caption(
                    worker,
                    lease,
                    REVISION_DOMAIN_CAPACITY + 1,
                    segment_id=str(uuid4()),
                    start_ms=0,
                    end_ms=20,
                    is_final=True,
                )
                rotation = await read_control(worker.socket)
                error = await read_control(worker.socket)
                replacement = await read_control(worker.socket)
                gap = await read_control(viewer)
                assert (rotation["reason"], rotation["opened_epoch"]) == ("revision_capacity", "2")
                assert (
                    error["code"],
                    error["retryable"],
                    error["expected"],
                    error["received"],
                ) == ("epoch_rotated", True, "2", "1")
                assert (gap["type"], gap["epoch"], gap["next_seq"]) == ("viewer.resync", "2", "1")
                assert not gateway.result_accepted(rejected["message_id"])
                assert replacement["lease_id"] != lease["lease_id"]
                await send_control(worker.socket, rejected)
                assert (await read_control(worker.socket))["code"] == "epoch_stale"
                assert not gateway.result_accepted(rejected["message_id"])
                await _send_caption(
                    worker,
                    replacement,
                    1,
                    segment_id=rejected["segment_id"],
                    start_ms=20,
                    end_ms=40,
                    is_final=True,
                )
                assert (await read_control(worker.socket))["outcome"] == "accepted"
                assert (await read_control(viewer))["epoch"] == "2"

    asyncio.run(scenario())


def test_cancelled_lease_send_retires_the_undelivered_lease(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world, gateway, devices, _ = _setup(2)
    sending = asyncio.Event()
    actual_send = WebSocket.send_text

    async def block_first_lease(socket: WebSocket, data: str) -> None:
        if not sending.is_set() and '"type":"worker.lease"' in data:
            sending.set()
            await asyncio.Future()
        await actual_send(socket, data)

    monkeypatch.setattr(WebSocket, "send_text", block_first_lease)

    async def scenario() -> None:
        async with (
            serve_gateway(create_failover_app(gateway)) as (url, tls),
            AsyncExitStack() as stack,
        ):
            stack.push_async_callback(gateway.stop)
            primary, standby = await _workers(stack, url, tls, world, devices)
            viewer = await stack.enter_async_context(_viewer(url, tls))
            await _subscribe(viewer)
            arming = asyncio.create_task(_arm(gateway))
            await asyncio.wait_for(sending.wait(), 2)
            arming.cancel()
            with pytest.raises(asyncio.CancelledError):
                await arming
            assert (await read_control(viewer))["epoch"] == "2"
            assert (await read_control(standby.socket))["epoch"] == "2"
            assert gateway.lease_valid(standby.connection_id)
            assert not gateway.device_checked(primary.connection_id)

    asyncio.run(scenario())


def test_eligibility_is_rechecked_after_welcome(monkeypatch: pytest.MonkeyPatch) -> None:
    world, gateway, devices, observed = _setup(1)
    actual_send = WebSocket.send_text

    async def advance_on_welcome(socket: WebSocket, data: str) -> None:
        if '"type":"worker.welcome"' in data:
            world.clock.advance(timedelta(seconds=2))
        await actual_send(socket, data)

    monkeypatch.setattr(WebSocket, "send_text", advance_on_welcome)

    async def scenario() -> None:
        async with (
            serve_gateway(create_failover_app(gateway)) as (url, tls),
            AsyncExitStack() as stack,
        ):
            stack.push_async_callback(gateway.stop)
            await gateway.observe(
                devices[0].id,
                replace(observed[0], fresh_until=world.clock.now + timedelta(seconds=1)),
            )
            await _arm(gateway)
            (worker,) = await _workers(stack, url, tls, world, devices)
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(worker.socket.recv(), 0.025)
            await gateway.observe(worker.device.id, observed[0])
            assert (await read_control(worker.socket))["epoch"] == "1"

    asyncio.run(scenario())


def test_pending_pcm_write_observes_remaining_lease_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world, gateway, devices, _ = _setup(2)

    async def block_pcm(socket: WebSocket, data: bytes) -> None:
        await asyncio.Future()

    monkeypatch.setattr(WebSocket, "send_bytes", block_pcm)

    async def scenario() -> None:
        async with (
            serve_gateway(create_failover_app(gateway)) as (url, tls),
            AsyncExitStack() as stack,
        ):
            stack.push_async_callback(gateway.stop)
            primary, standby = await _workers(stack, url, tls, world, devices)
            await _arm(gateway)
            lease = await read_control(primary.socket)
            world.clock.advance(timedelta(milliseconds=19_960))
            assert not await asyncio.wait_for(
                gateway.submit_synthetic_pcm(lease["lease_id"], _pcm(lease, 0)), timeout=0.5
            )
            assert (await read_control(standby.socket))["epoch"] == "2"
            assert gateway.lease_valid(standby.connection_id)
            assert not gateway.lease_valid(primary.connection_id)

    asyncio.run(scenario())


def test_exact_worker_transfer_preserves_the_live_epoch() -> None:
    world, gateway, devices, _ = _setup(2)

    async def scenario() -> None:
        async with (
            serve_gateway(create_failover_app(gateway)) as (url, tls),
            AsyncExitStack() as stack,
        ):
            stack.push_async_callback(gateway.stop)
            primary, standby = await _workers(stack, url, tls, world, devices)
            await _arm(gateway)
            lease = await read_control(primary.socket)
            hello = hello_for(primary.device.id, minor1=True).model_dump(mode="json")
            hello["resume"] = {
                "connection_id": primary.connection_id,
                "lease_id": lease["lease_id"],
                "session_id": lease["session_id"],
                "epoch": "1",
                "next_input_seq": "1",
                "next_output_seq": "1",
            }
            async with connect_worker(url, tls, primary.device.challenge(world)) as socket:
                await send_control(socket, hello)
                resumed = await read_control(socket)
                assert resumed["resume_succeeded"]
                assert not gateway.lease_valid(primary.connection_id)
                assert gateway.protocol.epoch == 1
                await send_control(socket, worker_output("HeartbeatV1", lease, 1))
                assert (await read_control(socket))["outcome"] == "accepted"
                await _assert_only_primary(
                    gateway, Worker(primary.device, socket, resumed["connection_id"]), [standby]
                )

    asyncio.run(scenario())
