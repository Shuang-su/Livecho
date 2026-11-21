"""Challenges are single-use, and revoking one device leaves the account alone."""

from __future__ import annotations

import threading
from datetime import timedelta

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from livecho_backend.auth.records import AccountStatus, Role

from .support import (
    World,
    assert_no_cookie,
    assert_stored_json,
    b64decode,
    challenge_message,
    fresh_key,
)


def _device(world: World) -> tuple[Ed25519PrivateKey, str]:
    private, public = fresh_key()
    created = world.enroll(world.issue().json()["token"], public)
    assert created.status == 201
    return private, created.json()["device_id"]


def test_replay_replacement_and_expiry_reject_the_challenge() -> None:
    world = World()
    private, device_id = _device(world)
    first = world.challenge(device_id).json()
    second = world.challenge(device_id).json()
    stale_nonce = b64decode(first["nonce"])
    stale = private.sign(challenge_message(device_id, first["challenge_id"], stale_nonce))
    replaced = world.verify(first["challenge_id"], device_id, stale)
    assert_stored_json(replaced, 401)
    nonce = b64decode(second["nonce"])
    signature = private.sign(challenge_message(device_id, second["challenge_id"], nonce))
    assert world.verify(second["challenge_id"], device_id, signature).status == 204
    assert world.verify(second["challenge_id"], device_id, signature).status == 401
    assert_no_cookie(world.verify(second["challenge_id"], device_id, signature))

    later = world.challenge(device_id).json()
    world.clock.advance(timedelta(seconds=120))
    expired_nonce = b64decode(later["nonce"])
    expired = private.sign(challenge_message(device_id, later["challenge_id"], expired_nonce))
    assert world.verify(later["challenge_id"], device_id, expired).status == 401
    assert world.store.challenges_for(device_id)[-1].nonce is None


def test_revoke_leaves_the_account_and_stops_only_that_device() -> None:
    world = World()
    private, first = _device(world)
    _other_private, second_public = fresh_key()
    second_token = world.issue().json()["token"]
    second = world.enroll(second_token, second_public).json()["device_id"]
    account = world.auth.account_by_id(world.contributor.account_id)
    assert account is not None
    before = (account.role, account.status)
    revoked = world.call(
        "POST",
        f"/api/worker/devices/{first}/revoke",
        account=world.admin.account_id,
    )
    assert revoked.status == 204
    assert revoked.body == b""
    assert_no_cookie(revoked)
    repeat = world.call(
        "POST",
        f"/api/worker/devices/{first}/revoke",
        account=world.admin.account_id,
    )
    assert repeat.status == 204
    after = world.auth.account_by_id(world.contributor.account_id)
    assert after is not None
    assert (after.role, after.status) == before
    assert after.status is AccountStatus.ACTIVE
    assert after.role is Role.CONTRIBUTOR
    denied = world.challenge(first)
    assert_stored_json(denied, 401)
    assert denied.json() == {"error": "rejected"}
    assert any(item.result == "device_revoked" for item in world.store.audits())
    assert world.challenge(second).status == 201
    stranger = world.call(
        "POST",
        f"/api/worker/devices/{first}/revoke",
        account=world.contributor.account_id,
    )
    assert stranger.status == 403
    missing = world.call(
        "POST",
        "/api/worker/devices/00000000-0000-4000-8000-000000000099/revoke",
        account=world.admin.account_id,
    )
    assert missing.status == 404
    assert world.store.audits()[-1].device_id is None
    del private


def test_challenge_quota_does_not_replace_the_current_challenge() -> None:
    world = World()
    _private, device_id = _device(world)
    last = None
    for _ in range(30):
        last = world.challenge(device_id)
        assert last.status == 201
    assert last is not None
    blocked = world.challenge(device_id)
    assert_stored_json(blocked, 401)
    assert blocked.json() == {"error": "rejected"}
    assert any(item.result == "rate_limited" for item in world.store.audits())
    current = last.json()
    stored = world.store.challenges_for(device_id)
    live = [item for item in stored if item.used_at is None]
    assert len(live) == 1
    assert live[0].challenge_id == current["challenge_id"]
    assert live[0].nonce is not None
    world.clock.advance(timedelta(minutes=15))
    assert world.challenge(device_id).status == 201


def test_ip_quota_hides_malformed_bodies_and_ignores_forwarded_for() -> None:
    world = World()
    _private, public = fresh_key()
    token = world.issue().json()["token"]
    client = ("203.0.113.50", 4430)
    for _ in range(30):
        response = world.call(
            "POST",
            "/api/worker/devices",
            body=b"not-json",
            client=client,
            headers={"x-forwarded-for": "198.51.100.2"},
        )
        assert response.status == 422
    hidden = world.call("POST", "/api/worker/devices", body=b"not-json", client=client)
    assert hidden.status == 401
    assert hidden.json() == {"error": "rejected"}
    assert world.store.enrollments()[0].used_at is None
    created = world.enroll(token, public, client=("203.0.113.51", 4430))
    assert created.status == 201
    bad_path = world.call(
        "POST",
        "/api/worker/devices/NOT-A-UUID/challenges",
        body=b"{}",
        client=("203.0.113.60", 1),
    )
    assert bad_path.status == 401
    assert world.store.challenges_for("NOT-A-UUID") == ()


def test_one_concurrent_verify_wins() -> None:
    world = World()
    private, device_id = _device(world)
    issued = world.challenge(device_id).json()
    nonce = b64decode(issued["nonce"])
    signature = private.sign(challenge_message(device_id, issued["challenge_id"], nonce))
    barrier = threading.Barrier(2)
    results: list[int] = []

    def attempt() -> None:
        barrier.wait()
        results.append(world.verify(issued["challenge_id"], device_id, signature).status)

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == [204, 401]
