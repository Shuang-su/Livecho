from __future__ import annotations

from uuid import uuid4

from livecho_mlx_worker.fixture_session import FixtureBinding, FixtureSession
from livecho_protocol.errors import StableCode


def binding() -> FixtureBinding:
    return FixtureBinding(
        lease_id=str(uuid4()),
        session_id=str(uuid4()),
        epoch="1",
        output_start_seq=0,
        start_ms=0,
        end_ms=1200,
    )


def test_fixture_emits_legal_partial_then_final() -> None:
    session = FixtureSession(binding())
    session.start()
    partial, final = session.emit_partial_then_final()
    assert partial["is_final"] is False
    assert final["is_final"] is True
    assert partial["segment_id"] == final["segment_id"]
    assert partial["start_ms"] == final["start_ms"] == 0
    assert partial["end_ms"] == final["end_ms"] == 1200
    assert int(partial["seq"]) == 0
    assert int(final["seq"]) == 1
    assert int(partial["revision"]) == 1
    assert int(final["revision"]) == 2
    assert session.label == "fixture_not_speech_recognition"
    assert session.audio_held is False
    assert len(session.published) == 2


def test_stale_and_post_final_revisions_rejected() -> None:
    session = FixtureSession(binding())
    session.start()
    session.emit_partial_then_final()
    assert session.reject_stale_revision() == StableCode.REVISION_STALE
    assert session.reject_after_final() == StableCode.OBJECT_FINAL


def test_cancel_suppresses_commit_and_releases_audio() -> None:
    session = FixtureSession(binding())
    session.start()
    assert session.audio_held is True
    session.cancel()
    assert session.audio_held is False
    try:
        session.emit_partial_then_final()
    except RuntimeError as error:
        assert "admission_closed" in str(error)
    else:
        raise AssertionError("cancelled session must not publish")
    assert session.published == ()


def test_epoch_and_session_binding_enforced() -> None:
    session = FixtureSession(binding())
    session.start()
    partial, _ = session.emit_partial_then_final(
        partial_text="a…",
        final_text="a complete",
    )
    assert partial["epoch"] == "1"
    assert partial["session_id"] == session.binding.session_id
    assert partial["lease_id"] == session.binding.lease_id
