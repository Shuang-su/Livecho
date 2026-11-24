"""Contribution statistics expose six keys and no scoring fields."""

from __future__ import annotations

import inspect
from datetime import timedelta

from livecho_backend.auth.records import Role

from .support import World, assert_stored_json, fresh_key, stamp, stats_for


def _device(world: World) -> str:
    _private, public = fresh_key()
    created = world.enroll(world.issue().json()["token"], public)
    assert created.status == 201
    device_id = created.json()["device_id"]
    assert isinstance(device_id, str)
    return device_id


def test_statistics_response_has_exactly_the_six_keys() -> None:
    world = World()
    device_id = _device(world)
    other = _device(world)
    start = stamp()
    assert world.service.record_stats(device_id, stats_for(accepted=0, rejected=0, rtf=1.0))
    assert world.service.record_stats(
        device_id, stats_for(accepted=1, rejected=2, processed_ms=2500, rtf=1.5)
    )
    assert world.service.note_online(
        device_id, start, start + timedelta(seconds=2, milliseconds=900)
    )
    assert world.service.note_online(device_id, start, start + timedelta(milliseconds=900))
    assert world.service.record_health(device_id, "ready", start)
    assert world.service.record_health(device_id, "error", start - timedelta(seconds=1)) is True
    assert world.service.record_health(device_id, "busy", start + timedelta(seconds=1))
    listed = world.call(
        "GET",
        "/api/worker/statistics",
        account=world.contributor.account_id,
    )
    assert_stored_json(listed, 200)
    body = listed.json()
    assert set(body) == {"devices"}
    assert [item["device_id"] for item in body["devices"]] == sorted([device_id, other])
    row = next(item for item in body["devices"] if item["device_id"] == device_id)
    assert set(row) == {
        "device_id",
        "online_duration_seconds",
        "processed_seconds",
        "success_rate",
        "rtf",
        "recent_health",
    }
    assert row["online_duration_seconds"] == 2
    assert row["processed_seconds"] == 2
    assert row["success_rate"] == "0.333333"
    assert row["rtf"] == "1.5"
    assert row["recent_health"] == {"state": "busy", "observed_at": "2026-01-01T00:00:01.000Z"}
    assert "danmaku" not in listed.body.decode("utf-8")
    same = world.call(
        "GET",
        "/api/worker/statistics",
        query=f"account_id={world.contributor.account_id}",
        account=world.contributor.account_id,
    )
    assert same.json() == body
    with_danmaku = stats_for(accepted=1, rejected=2)
    signature = inspect.signature(world.service.record_stats)
    assert "danmaku" not in signature.parameters
    try:
        world.service.record_stats(device_id, with_danmaku, danmaku=4)  # type: ignore[call-arg]
    except TypeError:
        pass
    else:
        raise AssertionError("danmaku must be rejected")
    regressed = world.service.record_stats(
        device_id,
        stats_for(accepted=0, rejected=2, processed_ms=2500, rtf=9.0),
    )
    assert regressed is False
    current = next(
        item
        for item in world.call(
            "GET",
            "/api/worker/statistics",
            account=world.contributor.account_id,
        ).json()["devices"]
        if item["device_id"] == device_id
    )
    assert current["success_rate"] == "0.333333"
    assert current["rtf"] == "1.5"
    negative = world.service.note_online(device_id, start, start - timedelta(seconds=1))
    assert negative is False
    assert any(
        item.result == "rejected" and item.object_class == "statistics"
        for item in world.store.audits()
    )


def test_zero_denominator_is_null_and_equal_counters_refresh_rtf() -> None:
    world = World()
    device_id = _device(world)
    assert world.service.record_stats(device_id, stats_for(accepted=0, rejected=0, rtf=2.0))
    row = world.call("GET", "/api/worker/statistics", account=world.contributor.account_id).json()
    assert row["devices"][0]["success_rate"] is None
    assert row["devices"][0]["rtf"] == "2"
    assert world.service.record_stats(device_id, stats_for(accepted=0, rejected=0, rtf=0.25))
    refreshed = world.call(
        "GET",
        "/api/worker/statistics",
        account=world.contributor.account_id,
    ).json()
    assert refreshed["devices"][0]["success_rate"] is None
    assert refreshed["devices"][0]["rtf"] == "0.25"
    assert refreshed["devices"][0]["processed_seconds"] == 0


def test_statistics_authorization_and_revoked_visibility() -> None:
    world = World()
    keep = _device(world)
    drop = _device(world)
    world.service.record_stats(keep, stats_for(accepted=2, rejected=2, rtf=1.0))
    assert (
        world.call(
            "POST",
            f"/api/worker/devices/{drop}/revoke",
            account=world.admin.account_id,
        ).status
        == 204
    )
    visible = world.call(
        "GET", "/api/worker/statistics", account=world.contributor.account_id
    ).json()
    assert [item["device_id"] for item in visible["devices"]] == [keep]
    other = world.activate("other@example.com", Role.CONTRIBUTOR)
    forbidden = world.call(
        "GET",
        "/api/worker/statistics",
        query=f"account_id={other.account_id}",
        account=world.contributor.account_id,
    )
    assert_stored_json(forbidden, 403)
    assert forbidden.json() == {"error": "forbidden"}
    anonymous = world.call("GET", "/api/worker/statistics")
    assert anonymous.status == 401
    admin_missing = world.call("GET", "/api/worker/statistics", account=world.admin.account_id)
    assert admin_missing.status == 422
    admin = world.call(
        "GET",
        "/api/worker/statistics",
        query=f"account_id={world.contributor.account_id}",
        account=world.admin.account_id,
    )
    assert_stored_json(admin, 200)
    assert [item["device_id"] for item in admin.json()["devices"]] == sorted([keep, drop])
    unknown = world.call(
        "GET",
        "/api/worker/statistics",
        query="account_id=00000000-0000-4000-8000-000000000099",
        account=world.admin.account_id,
    )
    assert unknown.status == 404
    assert world.service.record_stats(drop, stats_for(accepted=3, rejected=1)) is False
    assert any(item.result == "device_revoked" for item in world.store.audits())
    identity = world.call(
        "GET",
        "/api/worker/devices",
        query=f"account_id={world.contributor.account_id}",
        account=world.admin.account_id,
    )
    assert_stored_json(identity, 200)
    assert {item["status"] for item in identity.json()} == {"active", "revoked"}
    assert "public_key" in identity.json()[0]
    assert "public_key" not in admin.json()["devices"][0]
    contributor_identity = world.call(
        "GET",
        "/api/worker/devices",
        query=f"account_id={world.contributor.account_id}",
        account=world.contributor.account_id,
    )
    assert contributor_identity.status == 403
