from __future__ import annotations

from collections.abc import Callable
from typing import Any

from livecho_backend.ingest.session import (
    MAX_RECONNECT_ATTEMPTS,
    IngestSession,
    RoomState,
)


def test_anonymous_cannot_start(load_fixture: Callable[[str], dict[str, Any]]) -> None:
    session = IngestSession()
    assert (
        session.start_fixture("anonymous", "123456", load_fixture("live_free.json"))
        == "actor_forbidden"
    )
    assert session.state == RoomState.OFFLINE


def test_happy_path_and_secret_ram_only(
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    session = IngestSession()
    err = session.start_fixture(
        "operator",
        "123456",
        load_fixture("live_free.json"),
        playback_url="https://play.example.test/token=secret",
        session_token="anon-token",
        force_safety_enabled=True,
    )
    assert err is None
    assert session.state.value == "LIVE"
    assert session.has_playback_secrets
    events = session.snapshot_events()
    assert [e["state"] for e in events] == ["STARTING", "LIVE"]
    blob = repr(events)
    assert "secret" not in blob
    assert "anon-token" not in blob
    session.stop(actor="operator")
    assert session.state.value == "ENDED"
    assert not session.has_playback_secrets


def test_eligibility_failures_end_safely(
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    for name, reason in [
        ("login_required.json", "login_required"),
        ("payment_required.json", "payment_required"),
        ("geo_restricted.json", "geo_restricted"),
        ("offline.json", "offline"),
    ]:
        session = IngestSession()
        assert (
            session.start_fixture(
                "admin",
                "123456",
                load_fixture(name),
                force_safety_enabled=True,
            )
            == reason
        )
        assert session.state == RoomState.ENDED
        assert not session.has_playback_secrets


def test_kill_switch_and_denylist(
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    session = IngestSession()
    assert (
        session.start_fixture(
            "operator", "123456", load_fixture("live_free.json"), force_safety_enabled=True
        )
        is None
    )
    assert session.apply_disable("operator") is None
    assert session.state == RoomState.ENDED
    assert not session.has_playback_secrets
    # New start rejected while disabled.
    assert (
        session.start_fixture(
            "operator", "123456", load_fixture("live_free.json"), force_safety_enabled=False
        )
        == "ingest_disabled"
    )

    session2 = IngestSession()
    assert (
        session2.start_fixture(
            "operator", "123456", load_fixture("live_free.json"), force_safety_enabled=True
        )
        is None
    )
    assert session2.apply_denylist("operator", "123456") is None
    assert session2.state == RoomState.ENDED
    assert (
        session2.start_fixture(
            "operator", "123456", load_fixture("live_free.json"), force_safety_enabled=True
        )
        == "room_denied"
    )


def test_stall_reconnect_clears_locator_and_backoff(
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    session = IngestSession()
    session.start_fixture(
        "operator",
        "123456",
        load_fixture("live_free.json"),
        playback_url="https://play.example.test/old",
        session_token="old",
        force_safety_enabled=True,
    )
    session.note_stall()
    assert session.state.value == "STALLED"
    err = session.reconnect_fixture(
        load_fixture("live_free.json"),
        wall_delta_ms=10,
        playback_url="https://play.example.test/new",
        session_token="new",
    )
    assert err is None
    assert session.state.value == "LIVE"
    assert session.reconnect_attempts == 1
    assert session.backoff_ms(1) == 250
    assert session.backoff_ms(2) == 500
    assert session.backoff_ms(10) == 8_000
    # Old secrets must not remain after reconnect clear+replace.
    assert session.has_playback_secrets
    assert "old" not in repr(session.snapshot_events())


def test_retry_exhausted(load_fixture: Callable[[str], dict[str, Any]]) -> None:
    session = IngestSession()
    session.start_fixture(
        "operator",
        "123456",
        load_fixture("live_free.json"),
        force_safety_enabled=True,
    )
    session.note_stall()
    last: str | None = None
    for _ in range(MAX_RECONNECT_ATTEMPTS + 1):
        last = session.reconnect_fixture(load_fixture("live_free.json"), wall_delta_ms=1)
        if last == "retry_exhausted":
            break
        session.note_stall()
    assert last == "retry_exhausted"
    assert session.state == RoomState.ENDED
    assert not session.has_playback_secrets


def test_real_path_blocked_and_no_audio_handoff(
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    session = IngestSession()
    assert session.safety.globally_enabled is False
    assert session.safety.enable_global("admin") == "ingest_disabled"
    assert session.safety.globally_enabled is False
    session.safety.globally_enabled = True
    assert session.start_real("operator", "123456") == "acquisition_channel_unselected"
    assert session.handoff_playback_url_to_audio() == "encoded_admission_missing"


def test_reconnect_wall_budget_exhausted(
    load_fixture: Callable[[str], dict[str, Any]],
) -> None:
    session = IngestSession()
    session.start_fixture(
        "operator",
        "123456",
        load_fixture("live_free.json"),
        force_safety_enabled=True,
    )
    session.note_stall()
    assert (
        session.reconnect_fixture(
            load_fixture("live_free.json"),
            wall_delta_ms=120_001,
        )
        == "retry_exhausted"
    )
    assert session.state.value == "ENDED"
    assert not session.has_playback_secrets
