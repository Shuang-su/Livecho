"""Small-order and non-canonical keys never become devices."""

from __future__ import annotations

import base64
import threading

from livecho_backend.auth.crypto import decode_secret
from livecho_backend.worker_identity.points import canonical_small_order_encodings, group_order

from .support import World, assert_stored_json, b64, challenge_message, fresh_key


def _unused(world: World, token: str) -> None:
    row = world.store.enrollments()[0]
    assert row.used_at is None
    assert decode_secret(token) is not None
    assert world.store.devices_for(world.contributor.account_id) == ()


def test_small_order_and_noncanonical_keys_do_not_consume_the_token() -> None:
    world = World()
    _private, public = fresh_key()
    token = world.issue().json()["token"]
    identity = bytes([1]) + bytes(31)
    signed_identity = bytearray(identity)
    signed_identity[-1] |= 0x80
    y_at_least_p = (2**255 - 19).to_bytes(32, "little")
    not_on_curve = (2).to_bytes(32, "little")
    rejected = [
        *canonical_small_order_encodings(),
        bytes(signed_identity),
        y_at_least_p,
        not_on_curve,
    ]
    assert len(canonical_small_order_encodings()) == 8
    assert identity in canonical_small_order_encodings()
    for encoding in rejected:
        response = world.enroll(token, encoding)
        assert_stored_json(response, 422)
        assert response.json() == {"error": "invalid_body"}
        _unused(world, token)
    created = world.enroll(token, public)
    assert created.status == 201
    assert world.store.device(created.json()["device_id"]) is not None


def test_identity_signature_does_not_verify_for_an_enrolled_device() -> None:
    world = World()
    private, public = fresh_key()
    token = world.issue().json()["token"]
    identity = bytes([1]) + bytes(31)
    refused = world.enroll(token, identity)
    assert refused.status == 422
    created = world.enroll(token, public)
    device_id = created.json()["device_id"]
    issued = world.challenge(device_id)
    body = issued.json()
    nonce = base64.urlsafe_b64decode(body["nonce"] + "=")
    forged = identity + bytes(32)
    rejected = world.verify(body["challenge_id"], device_id, forged)
    assert_stored_json(rejected, 401)
    assert rejected.json() == {"error": "rejected"}
    assert world.store.challenges_for(device_id)[0].nonce is None
    replay = world.verify(body["challenge_id"], device_id, forged)
    assert replay.status == 401
    message = challenge_message(device_id, body["challenge_id"], nonce)
    assert private.sign(message) != forged
    audits = [item for item in world.store.audits() if item.result == "signature_invalid"]
    assert audits
    assert b64(forged) not in repr(audits[-1])
    assert "contributor@example.com" not in repr(audits[-1])


def test_signature_scalar_not_below_group_order_is_consumed() -> None:
    world = World()
    private, public = fresh_key()
    created = world.enroll(world.issue().json()["token"], public)
    device_id = created.json()["device_id"]
    issued = world.challenge(device_id).json()
    nonce = base64.urlsafe_b64decode(issued["nonce"] + "=")
    message = challenge_message(device_id, issued["challenge_id"], nonce)
    signature = bytearray(private.sign(message))
    scalar = int.from_bytes(signature[32:], "little") + group_order()
    assert scalar < 2**256
    signature[32:] = scalar.to_bytes(32, "little")
    rejected = world.verify(issued["challenge_id"], device_id, bytes(signature))
    assert_stored_json(rejected, 401)
    assert rejected.json() == {"error": "rejected"}
    assert world.store.challenges_for(device_id)[0].used_at is not None
    assert world.store.challenges_for(device_id)[0].nonce is None
    audit = [item for item in world.store.audits() if item.result == "signature_invalid"][-1]
    assert audit.device_id == device_id
    assert audit.object_class == "device"
    assert b64(bytes(signature)) not in repr(audit)
    replacement = world.challenge(device_id).json()
    fresh_nonce = base64.urlsafe_b64decode(replacement["nonce"] + "=")
    fresh = private.sign(challenge_message(device_id, replacement["challenge_id"], fresh_nonce))
    assert world.verify(replacement["challenge_id"], device_id, fresh).status == 204


def test_one_concurrent_enrollment_wins() -> None:
    world = World()
    _private, public = fresh_key()
    token = world.issue().json()["token"]
    barrier = threading.Barrier(2)
    results: list[int] = []

    def attempt() -> None:
        barrier.wait()
        results.append(world.enroll(token, public).status)

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == [201, 401]
    assert len(world.store.devices_for(world.contributor.account_id)) == 1
    assert world.store.enrollments()[0].used_at is not None
