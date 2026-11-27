"""Exercise the standalone worker endpoint through real loopback WSS."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from livecho_backend.worker_gateway.gateway import WorkerGateway, create_worker_gateway_app
from livecho_protocol.binary import PcmHeaderV1, encode_header
from livecho_protocol.golden import _public_values
from livecho_protocol.models import ModelManifestRefV1, WorkerHelloV1
from livecho_protocol.parser import canonical_json, strict_json_loads
from livecho_protocol.scalars import parse_timestamp
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from tests.worker_identity.support import MANIFEST, World, hello_for, prove

from .support import GATEWAY_PROTOCOL, connect_worker, enroll, serve_gateway

ROOM = "synthetic-room"


async def _read(client: ClientConnection) -> dict[str, Any]:
    raw = await asyncio.wait_for(client.recv(), timeout=3)
    assert isinstance(raw, str)
    return strict_json_loads(raw)


async def _send(client: ClientConnection, body: dict[str, Any] | WorkerHelloV1) -> None:
    value = body.model_dump(mode="json") if isinstance(body, WorkerHelloV1) else body
    await client.send(canonical_json(value).decode("utf-8"))


def _output(
    name: str,
    lease: dict[str, Any],
    seq: int,
    **changes: object,
) -> dict[str, Any]:
    raw = _public_values()[name]
    raw.update(
        protocol_minor=lease["protocol_minor"],
        lease_id=lease["lease_id"],
        session_id=lease["session_id"],
        epoch=lease["epoch"],
        seq=str(seq),
        message_id=str(uuid4()),
    )
    raw.update(changes)
    return raw


def test_real_wss_rejects_standalone_http_admission_and_accepts_the_bound_key() -> None:
    world = World()
    device = enroll(world)
    prove(world, device.key, device.id)
    world.allow()
    gateway = WorkerGateway(world.service, clock=world.clock)
    app = create_worker_gateway_app(gateway)

    async def scenario() -> None:
        async with serve_gateway(app) as (url, tls):
            with pytest.raises(InvalidStatus) as failure:
                async with connect(
                    url,
                    ssl=tls,
                    proxy=None,
                    subprotocols=[GATEWAY_PROTOCOL],
                    additional_headers={"livecho-device-id": device.id},
                ):
                    pytest.fail("HTTP admission cannot authorize an upgrade")
            assert failure.value.response.status_code == 403
            challenge = device.challenge(world)
            async with connect_worker(url, tls, challenge) as client:
                await _send(client, hello_for(device.id))
                welcome = await _read(client)
                assert welcome["type"] == "worker.welcome"
                assert welcome["selected_minor"] == 0
                assert gateway.device_checked(welcome["connection_id"])
                assert not gateway.lease_valid(welcome["connection_id"])
            with pytest.raises(InvalidStatus):
                async with connect_worker(url, tls, challenge):
                    pytest.fail("a consumed challenge cannot admit another connection")

    asyncio.run(scenario())


@pytest.mark.parametrize("minor", [0, 1])
def test_lease_heartbeats_results_and_expiry_use_one_runtime(minor: int) -> None:
    world = World()
    device = enroll(world)
    world.allow()
    gateway = WorkerGateway(world.service, clock=world.clock)
    app = create_worker_gateway_app(gateway)

    async def scenario() -> None:
        try:
            session_id = str(uuid4())
            manifest = ModelManifestRefV1.model_validate(MANIFEST)
            assert await gateway.arm_grant(session_id, ROOM, manifest)
            assert await gateway.arm_grant(session_id, ROOM, manifest)
            async with (
                serve_gateway(app) as (url, tls),
                connect_worker(url, tls, device.challenge(world)) as client,
            ):
                await _send(client, hello_for(device.id, minor1=minor == 1))
                welcome, lease = await _read(client), await _read(client)
                assert welcome["selected_minor"] == lease["protocol_minor"] == minor
                assert lease["type"] == "worker.lease"
                assert lease["audio_origin"] == "synthetic"
                connection_id = welcome["connection_id"]
                assert gateway.lease_valid(connection_id)
                assert gateway.heartbeat_healthy(connection_id)
                assert parse_timestamp(lease["expires_at"]) - parse_timestamp(
                    lease["issued_at"]
                ) == timedelta(seconds=20)
                assert not await gateway.arm_grant(str(uuid4()), ROOM, manifest)

                frame = encode_header(
                    PcmHeaderV1(
                        lease_id=lease["lease_id"],
                        epoch=1,
                        seq=minor,
                        pts_ms=0,
                        sample_count=320,
                        payload_length=640,
                        protocol_minor=minor,
                    )
                ) + bytes(640)
                assert await gateway.submit_synthetic_pcm(lease["lease_id"], frame)
                assert await asyncio.wait_for(client.recv(), timeout=3) == frame
                assert await gateway.consume_pcm(lease["lease_id"], 640)

                world.clock.advance(timedelta(seconds=5))
                assert not gateway.heartbeat_healthy(connection_id)
                assert gateway.lease_valid(connection_id)
                heartbeat = _output("HeartbeatV1", lease, minor)
                await _send(client, heartbeat)
                assert (await _read(client))["outcome"] == "accepted"
                assert gateway.heartbeat_healthy(connection_id)
                assert not gateway.result_accepted(heartbeat["message_id"])

                stats = _output(
                    "WorkerStatsV1",
                    lease,
                    minor + 1,
                    segments_accepted="1",
                    processed_audio_ms="1000",
                )
                await _send(client, stats)
                assert (await _read(client))["outcome"] == "accepted"
                assert gateway.result_accepted(stats["message_id"])
                await _send(client, stats)
                assert (await _read(client))["outcome"] == "seq_duplicate"
                recorded = world.store.statistic(device.id)
                assert recorded is not None and recorded.segments_accepted == 1
                wrong_epoch = _output("HeartbeatV1", lease, minor + 2, epoch="2")
                await _send(client, wrong_epoch)
                assert (await _read(client))["code"] == "epoch_unknown"
                ahead = _output("HeartbeatV1", lease, minor + 3)
                await _send(client, ahead)
                assert (await _read(client))["code"] == "seq_gap"

                world.clock.advance(timedelta(seconds=15))
                await gateway.expire_due()
                assert not gateway.lease_valid(connection_id)
                for _ in range(2):
                    late = _output("HeartbeatV1", lease, minor + 2)
                    await _send(client, late)
                    assert (await _read(client))["code"] == "lease_expired"
                assert not await gateway.submit_synthetic_pcm(lease["lease_id"], frame)
        finally:
            await gateway.restart(World().service)

    asyncio.run(scenario())


def test_resume_uses_the_original_lease_and_rejects_a_second_device() -> None:
    world = World()
    primary, other = enroll(world), enroll(world)
    world.allow()
    gateway = WorkerGateway(world.service, clock=world.clock)
    app = create_worker_gateway_app(gateway)

    async def scenario() -> None:
        try:
            manifest = ModelManifestRefV1.model_validate(MANIFEST)
            assert await gateway.arm_grant(str(uuid4()), ROOM, manifest)
            async with serve_gateway(app) as (url, tls):
                async with connect_worker(url, tls, primary.challenge(world)) as first:
                    await _send(first, hello_for(primary.id, minor1=True))
                    welcome, lease = await _read(first), await _read(first)
                    assert gateway.lease_valid(welcome["connection_id"])
                    async with connect_worker(url, tls, other.challenge(world)) as second:
                        await _send(second, hello_for(other.id, minor1=True))
                        assert (await _read(second))["type"] != "worker.lease"
                    assert gateway.lease_valid(welcome["connection_id"])
                    world.clock.advance(timedelta(seconds=2))

                resume = hello_for(primary.id, minor1=True).model_dump(mode="json")
                resume["resume"] = {
                    "connection_id": welcome["connection_id"],
                    "lease_id": lease["lease_id"],
                    "session_id": lease["session_id"],
                    "epoch": lease["epoch"],
                    "next_input_seq": lease["input_start_seq"],
                    "next_output_seq": lease["output_start_seq"],
                }
                async with connect_worker(url, tls, primary.challenge(world)) as resumed:
                    await _send(resumed, resume)
                    renewed = await _read(resumed)
                    assert renewed["type"] == "worker.welcome" and renewed["resume_succeeded"]
                    assert gateway.lease_valid(renewed["connection_id"])
                    assert not gateway.lease_valid(welcome["connection_id"])
                    await _send(resumed, _output("HeartbeatV1", lease, 1))
                    assert (await _read(resumed))["outcome"] == "accepted"
        finally:
            await gateway.restart(World().service)

    asyncio.run(scenario())


def test_two_verified_waiters_void_a_grant_without_opening_a_lease() -> None:
    world = World()
    first_device, second_device = enroll(world), enroll(world)
    world.allow()
    gateway = WorkerGateway(world.service, clock=world.clock)
    app = create_worker_gateway_app(gateway)

    async def scenario() -> None:
        try:
            async with (
                serve_gateway(app) as (url, tls),
                connect_worker(url, tls, first_device.challenge(world)) as first,
                connect_worker(url, tls, second_device.challenge(world)) as second,
            ):
                await _send(first, hello_for(first_device.id))
                await _send(second, hello_for(second_device.id))
                welcome_first, welcome_second = await _read(first), await _read(second)
                for welcome in (welcome_first, welcome_second):
                    assert welcome["type"] == "worker.welcome"
                    assert gateway.device_checked(welcome["connection_id"])
                    assert not gateway.lease_valid(welcome["connection_id"])
                session_id = str(uuid4())
                manifest = ModelManifestRefV1.model_validate(MANIFEST)
                assert not await gateway.arm_grant(session_id, ROOM, manifest)
                for client in (first, second):
                    with pytest.raises(ConnectionClosed):
                        await _read(client)
                assert not await gateway.arm_grant(session_id, ROOM, manifest)
        finally:
            await gateway.restart(World().service)

    asyncio.run(scenario())


def test_pcm_rate_then_device_revocation_releases_the_lease() -> None:
    world = World()
    device = enroll(world)
    world.allow()
    gateway = WorkerGateway(world.service, clock=world.clock)

    async def scenario() -> None:
        try:
            manifest = ModelManifestRefV1.model_validate(MANIFEST)
            assert await gateway.arm_grant(str(uuid4()), ROOM, manifest)
            async with (
                serve_gateway(create_worker_gateway_app(gateway)) as (url, tls),
                connect_worker(url, tls, device.challenge(world)) as client,
            ):
                await _send(client, hello_for(device.id))
                welcome, lease = await _read(client), await _read(client)

                def pcm(seq: int) -> bytes:
                    return encode_header(
                        PcmHeaderV1(
                            lease_id=lease["lease_id"],
                            epoch=1,
                            seq=seq,
                            pts_ms=seq * 20,
                            sample_count=320,
                            payload_length=640,
                        )
                    ) + bytes(640)

                for seq in range(50):
                    frame = pcm(seq)
                    assert await gateway.submit_synthetic_pcm(lease["lease_id"], frame)
                    assert await asyncio.wait_for(client.recv(), timeout=3) == frame
                    assert await gateway.consume_pcm(lease["lease_id"], 640)
                assert not await gateway.submit_synthetic_pcm(lease["lease_id"], pcm(50))
                world.clock.advance(timedelta(seconds=1))
                assert await gateway.submit_synthetic_pcm(lease["lease_id"], pcm(50))
                assert await asyncio.wait_for(client.recv(), timeout=3) == pcm(50)
                world.store.revoke(device.id, world.clock.now)
                assert not await gateway.submit_synthetic_pcm(lease["lease_id"], pcm(51))
                cancel = await _read(client)
                assert cancel["type"] == "worker.lease_cancel"
                assert cancel["reason"] == "policy_disable"
                assert not gateway.device_checked(welcome["connection_id"])
                assert not gateway.lease_valid(welcome["connection_id"])
                assert not await gateway.consume_pcm(lease["lease_id"], 640)
        finally:
            await gateway.restart(World().service)

    asyncio.run(scenario())
