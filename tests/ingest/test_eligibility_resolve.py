from __future__ import annotations

from collections.abc import Callable
from typing import Any

from livecho_backend.ingest.eligibility import evaluate_fixture_metadata
from livecho_backend.ingest.resolve import resolve_room_id


def test_resolve_numeric_and_alias() -> None:
    assert resolve_room_id("123456") == "123456"
    assert resolve_room_id("live.bilibili.com/123456") == "123456"
    assert resolve_room_id("") is None
    assert resolve_room_id("https://evil.example/123") is None
    assert resolve_room_id("alias", {"alias": "99"}) == "99"
    assert resolve_room_id("alias", {"alias": "bad"}) is None


def test_fixture_eligibility_matrix(load_fixture: Callable[[str], dict[str, Any]]) -> None:
    assert evaluate_fixture_metadata(load_fixture("live_free.json")).reason is None
    assert evaluate_fixture_metadata(load_fixture("offline.json")).reason == "offline"
    assert evaluate_fixture_metadata(load_fixture("login_required.json")).reason == "login_required"
    assert (
        evaluate_fixture_metadata(load_fixture("payment_required.json")).reason
        == "payment_required"
    )
    assert evaluate_fixture_metadata(load_fixture("geo_restricted.json")).reason == "geo_restricted"
    assert evaluate_fixture_metadata(load_fixture("drm_restricted.json")).reason == "drm_restricted"
    assert evaluate_fixture_metadata(load_fixture("rate_limited.json")).reason == "rate_limited"
    assert evaluate_fixture_metadata(load_fixture("schema_invalid.json")).reason == "schema_invalid"
