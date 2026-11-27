"""The WSS binding and standalone HTTP admission share only challenge authority."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest

from tests.worker_identity.support import World, hello_for, prove

from .support import enroll

PEER = "127.0.0.1"
HANDSHAKE_KEY = bytes(range(16))


def test_upgrade_context_is_one_shot_and_never_consumes_the_http_admission() -> None:
    world = World()
    device = enroll(world)
    world.allow()
    prove(world, device.key, device.id)
    assert world.service.verify_gateway_upgrade([], PEER) is None
    assert world.service.admit_hello(hello_for(device.id), device.id).accepted

    challenge = device.challenge(world)
    headers = challenge.headers(HANDSHAKE_KEY)
    with ThreadPoolExecutor(max_workers=2) as threads:
        contexts = list(
            threads.map(lambda _: world.service.verify_gateway_upgrade(headers, PEER), range(2))
        )
    accepted_contexts = [context for context in contexts if context is not None]
    assert len(accepted_contexts) == 1
    context = accepted_contexts[0]
    assert not world.service.admit_hello(hello_for(device.id), device.id).accepted
    assert world.service.admit_gateway_hello(hello_for(device.id), context).accepted
    assert not world.service.admit_gateway_hello(hello_for(device.id), context).accepted
    record = world.store.challenges_for(device.id)[-1]
    assert record.used_at is not None and record.nonce is None


@pytest.mark.parametrize("change", ["duplicate", "noncanonical", "wrong_handshake"])
def test_proof_validation_tracks_the_actual_upgrade(change: str) -> None:
    world = World()
    device = enroll(world)
    challenge = device.challenge(world)
    headers = challenge.headers(HANDSHAKE_KEY)
    if change == "duplicate":
        altered = [*headers, headers[-1]]
    elif change == "noncanonical":
        altered = [*headers[:-1], (b"Sec-WebSocket-Key", b"!" * 24)]
    else:
        altered = [*headers[:-1], challenge.headers(bytes(16))[-1]]
    assert world.service.verify_gateway_upgrade(altered, PEER) is None
    record = world.store.challenges_for(device.id)[-1]
    assert (record.used_at is not None) == (change == "wrong_handshake")
    assert (world.service.verify_gateway_upgrade(headers, PEER) is not None) == (
        change != "wrong_handshake"
    )


def test_new_verified_upgrade_supersedes_pending_context_but_issuance_does_not() -> None:
    world = World()
    device = enroll(world)
    world.allow()
    original = device.challenge(world)
    first = world.service.verify_gateway_upgrade(original.headers(HANDSHAKE_KEY), PEER)
    assert first is not None
    unsigned = device.challenge(world)
    assert world.service.admit_gateway_hello(hello_for(device.id), first).accepted

    second = world.service.verify_gateway_upgrade(unsigned.headers(HANDSHAKE_KEY), PEER)
    assert second is not None
    newer = device.challenge(world)
    third = world.service.verify_gateway_upgrade(newer.headers(bytes(16)), PEER)
    assert third is not None
    world.service.discard_gateway_proof(second)
    assert not world.service.admit_gateway_hello(hello_for(device.id), second).accepted
    assert world.service.admit_gateway_hello(hello_for(device.id), third).accepted


@pytest.mark.parametrize("condition", ["revoked", "expired", "wrong_device", "closed"])
def test_pending_context_fails_closed(condition: str) -> None:
    world = World()
    device = enroll(world)
    world.allow()
    challenge = device.challenge(world)
    proof = world.service.verify_gateway_upgrade(challenge.headers(HANDSHAKE_KEY), PEER)
    assert proof is not None
    worker_id = device.id
    if condition == "revoked":
        world.store.revoke(device.id, world.clock.now)
        assert not world.service.device_usable(device.id)
    elif condition == "expired":
        world.clock.advance(timedelta(seconds=120))
    elif condition == "wrong_device":
        worker_id = enroll(world).id
    else:
        world.service.discard_gateway_proof(proof)
    assert not world.service.admit_gateway_hello(hello_for(worker_id), proof).accepted
    assert not world.service.admit_gateway_hello(hello_for(device.id), proof).accepted


def test_malformed_upgrades_share_the_authority_rate_limit() -> None:
    world = World()
    device = enroll(world)
    challenge = device.challenge(world)
    for _ in range(29):
        assert world.service.verify_gateway_upgrade([], PEER) is None
    assert world.service.verify_gateway_upgrade(challenge.headers(HANDSHAKE_KEY), PEER) is None
    assert world.store.challenges_for(device.id)[-1].used_at is None
    assert world.store.audits()[-1].result == "rate_limited"
