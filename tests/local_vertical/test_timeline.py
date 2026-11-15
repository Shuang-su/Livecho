"""Pure timeline-rule tests for the bounded publication state machine."""

from __future__ import annotations

from uuid import uuid4

from livecho_backend.local_vertical.config import (
    FIXTURE_ADMISSION_INTERVAL_MS,
    FIXTURE_FINAL_DEADLINE_MS,
)
from livecho_backend.local_vertical.timeline import (
    FixtureDeadlineMissed,
    FixtureScheduleError,
    LocalTimeline,
    RevisionCapacityExceeded,
    utc_stamp,
)
from livecho_protocol.models import PROTOCOL_MINOR, VIEWER_PROTOCOL
from livecho_protocol.state import REVISION_DOMAIN_CAPACITY

from .helpers import FakeMonotonic


def new_timeline() -> LocalTimeline:
    return LocalTimeline(session_id=str(uuid4()), room_id="livecho.fixture.room")


def status_message(
    timeline: LocalTimeline, status: str, reason: str | None = None
) -> dict[str, object]:
    seq = timeline.allocate_seq()
    payload: dict[str, object] = {"status": status}
    if reason is not None:
        payload["reason_code"] = reason
    return {
        "protocol": VIEWER_PROTOCOL,
        "protocol_minor": PROTOCOL_MINOR,
        "message_id": str(uuid4()),
        "sent_at": utc_stamp(),
        "type": "viewer.timeline_event",
        "event_id": str(uuid4()),
        "session_id": timeline.session_id,
        "room_id": timeline.room_id,
        "epoch": str(timeline.epoch),
        "seq": str(seq),
        "revision": "1",
        "occurred_at": utc_stamp(),
        "payload": payload,
    }


def transcript_message(
    timeline: LocalTimeline,
    *,
    event_id: str,
    revision: int,
    text: str,
    is_final: bool,
    start_ms: int = 1_000,
) -> dict[str, object]:
    seq = timeline.allocate_seq()
    return {
        "protocol": VIEWER_PROTOCOL,
        "protocol_minor": PROTOCOL_MINOR,
        "message_id": str(uuid4()),
        "sent_at": utc_stamp(),
        "type": "viewer.timeline_event",
        "event_id": event_id,
        "session_id": timeline.session_id,
        "room_id": timeline.room_id,
        "epoch": str(timeline.epoch),
        "seq": str(seq),
        "revision": str(revision),
        "occurred_at": utc_stamp(),
        "payload": {
            "segment_id": event_id,
            "start_ms": start_ms,
            "end_ms": start_ms + 2_000,
            "text": text,
            "is_final": is_final,
        },
    }


def test_sequence_and_revision_basics() -> None:
    timeline = new_timeline()
    assert timeline.next_seq == 1
    decision = timeline.accept_timeline_event(status_message(timeline, "starting"))
    assert decision.accepted and timeline.next_seq == 2
    assert timeline.session_status == "starting" and timeline.reason_code is None
    event_id = str(uuid4())
    partial = timeline.accept_timeline_event(
        transcript_message(timeline, event_id=event_id, revision=1, text="partial…", is_final=False)
    )
    assert partial.accepted and timeline.mutable is not None
    final = timeline.accept_timeline_event(
        transcript_message(
            timeline, event_id=event_id, revision=2, text="partial text complete", is_final=True
        )
    )
    assert final.accepted and timeline.mutable is None
    assert timeline.next_seq == 4


def test_second_mutable_object_is_rejected() -> None:
    timeline = new_timeline()
    first = str(uuid4())
    timeline.accept_timeline_event(
        transcript_message(timeline, event_id=first, revision=1, text="a…", is_final=False)
    )
    second = str(uuid4())
    try:
        timeline.accept_timeline_event(
            transcript_message(timeline, event_id=second, revision=1, text="b…", is_final=False)
        )
    except FixtureScheduleError:
        pass
    else:
        raise AssertionError("only one mutable fixture object is allowed")
    assert timeline.mutable is not None and timeline.mutable.event_id == first


def test_admission_interval_gates_next_mutable_not_fresh_join() -> None:
    clock = FakeMonotonic()
    timeline = new_timeline()
    event_id = str(uuid4())
    timeline.open_mutable(event_id, now=clock())
    timeline.close_mutable(event_id, now=clock())
    assert timeline.fresh_admission_allowed(now=clock())
    assert not timeline.mutable_open_allowed(now=clock())
    clock.advance((FIXTURE_ADMISSION_INTERVAL_MS - 1) / 1_000)
    assert timeline.fresh_admission_allowed(now=clock())
    assert not timeline.mutable_open_allowed(now=clock())
    clock.advance(0.002)
    assert timeline.mutable_open_allowed(now=clock())


def test_final_deadline_miss_raises() -> None:
    clock = FakeMonotonic()
    timeline = new_timeline()
    event_id = str(uuid4())
    timeline.open_mutable(event_id, now=clock())
    clock.advance((FIXTURE_FINAL_DEADLINE_MS + 1) / 1_000)
    try:
        timeline.close_mutable(event_id, now=clock())
    except FixtureDeadlineMissed:
        pass
    else:
        raise AssertionError("missed final deadline must fail the fixture object")


def test_final_only_revision_one_does_not_open_mutable() -> None:
    timeline = new_timeline()
    event_id = str(uuid4())
    decision = timeline.accept_timeline_event(
        transcript_message(
            timeline, event_id=event_id, revision=1, text="final only", is_final=True
        )
    )
    assert decision.accepted
    assert timeline.mutable is None
    assert timeline.fresh_admission_allowed()


def test_terminal_status_does_not_block_fresh_admission() -> None:
    timeline = new_timeline()
    timeline.accept_timeline_event(status_message(timeline, "stopping"))
    timeline.accept_timeline_event(status_message(timeline, "stopped"))
    assert timeline.session_status == "stopped"
    assert timeline.fresh_admission_allowed()


def test_revision_capacity_refuses_new_identity_without_state_change() -> None:
    timeline = new_timeline()
    # Fill the revision domain to capacity with distinct final-only identities.
    for index in range(REVISION_DOMAIN_CAPACITY):
        event_id = str(uuid4())
        decision = timeline.accept_timeline_event(
            transcript_message(
                timeline,
                event_id=event_id,
                revision=1,
                text=f"item-{index}",
                is_final=True,
                start_ms=1_000 + index,
            )
        )
        assert decision.accepted
    next_seq_before = timeline.next_seq
    try:
        timeline.accept_timeline_event(
            transcript_message(
                timeline,
                event_id=str(uuid4()),
                revision=1,
                text="overflow",
                is_final=True,
                start_ms=9_000_000,
            )
        )
    except RevisionCapacityExceeded:
        pass
    else:
        raise AssertionError("4097th identity must refuse without state change")
    # allocate_seq already advanced before accept; capacity raise is after accept attempt.
    # The ordering state must not have admitted the new identity.
    assert timeline.ordering.revisions.size == REVISION_DOMAIN_CAPACITY
    del next_seq_before
