"""Wire-level lifecycle tests: statuses, invalidation, and session rules."""

from __future__ import annotations

import asyncio
from uuid import uuid4

from livecho_backend.local_vertical.schedule import FixtureScheduleSpec
from livecho_backend.local_vertical.timeline import utc_stamp
from websockets.asyncio.client import ClientConnection

from .helpers import (
    OrderChecker,
    backend_server,
    connect_viewer,
    expect_no_message,
    read_ready,
)


async def consume_terminal(
    connection: ClientConnection, checker: OrderChecker, timeout: float = 25.0
) -> tuple[int, str, str]:
    while True:
        terminal = await checker.consume(connection, timeout=timeout)
        if terminal is not None:
            return terminal


def test_schedule_completion_emits_stopping_then_stopped() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.start_session(
                FixtureScheduleSpec(segments=2, interval_ms=2_500, with_partials=True)
            )
            viewer = await connect_viewer(server)
            ready = await read_ready(viewer)
            checker = OrderChecker(ready["session_id"], ready["epoch"], ready["next_seq"])
            terminal = await consume_terminal(viewer, checker)
            assert terminal[1] == "status" and terminal[2] == "stopped"
            kinds = [record[1] for record in checker.events]
            assert kinds.count("partial") == 2
            assert kinds.count("final") == 2
            statuses = [record[2] for record in checker.events if record[1] == "status"]
            assert statuses[-2:] == ["stopping", "stopped"]
            assert "live" in statuses
            await expect_no_message(viewer, timeout=0.6)
            await viewer.close()

    asyncio.run(scenario())


def test_operator_stop_mid_run_closes_publication_immediately() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.start_session(
                FixtureScheduleSpec(segments=3, interval_ms=2_500, stop_after_segment=1)
            )
            viewer = await connect_viewer(server)
            ready = await read_ready(viewer)
            checker = OrderChecker(ready["session_id"], ready["epoch"], ready["next_seq"])
            terminal = await consume_terminal(viewer, checker)
            assert terminal[2] == "stopped"
            statuses = [record[2] for record in checker.events if record[1] == "status"]
            assert statuses[-2:] == ["stopping", "stopped"]
            assert not any(record[1] in {"partial", "final"} for record in checker.events)
            await expect_no_message(viewer, timeout=1.2)
            await viewer.close()

    asyncio.run(scenario())


def test_ingest_disabled_maps_to_stopped_with_reason() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.start_session(
                FixtureScheduleSpec(segments=2, interval_ms=2_500, disable_after_segment=1)
            )
            viewer = await connect_viewer(server)
            ready = await read_ready(viewer)
            checker = OrderChecker(ready["session_id"], ready["epoch"], ready["next_seq"])
            terminal = await consume_terminal(viewer, checker)
            assert terminal[2] == "stopped"
            assert server.service.timeline.reason_code == "ingest_disabled"
            await viewer.close()

    asyncio.run(scenario())


def test_session_deletion_maps_to_stopped_with_reason() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.start_session(
                FixtureScheduleSpec(segments=2, interval_ms=2_500, delete_after_segment=1)
            )
            viewer = await connect_viewer(server)
            ready = await read_ready(viewer)
            checker = OrderChecker(ready["session_id"], ready["epoch"], ready["next_seq"])
            terminal = await consume_terminal(viewer, checker)
            assert terminal[2] == "stopped"
            assert server.service.timeline.reason_code == "session_deleted"
            await viewer.close()

    asyncio.run(scenario())


def test_runtime_failure_maps_to_failed_with_fixed_reason() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.start_session(
                FixtureScheduleSpec(segments=2, interval_ms=2_500, fail_after_segment=1)
            )
            viewer = await connect_viewer(server)
            ready = await read_ready(viewer)
            checker = OrderChecker(ready["session_id"], ready["epoch"], ready["next_seq"])
            terminal = await consume_terminal(viewer, checker)
            assert terminal[2] == "failed"
            assert server.service.timeline.reason_code == "protocol_failed"
            await viewer.close()

    asyncio.run(scenario())


def test_stop_during_open_partial() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            viewer = await connect_viewer(server)
            ready = await read_ready(viewer)
            checker = OrderChecker(ready["session_id"], ready["epoch"], ready["next_seq"])
            await checker.consume(viewer)  # admission live status
            event_id = str(uuid4())
            await server.service.publish_transcript(
                event_id=event_id,
                revision=1,
                segment_id=event_id,
                start_ms=9_000,
                end_ms=11_000,
                text="open partial…",
                is_final=False,
                occurred_at=utc_stamp(),
            )
            await checker.consume(viewer)
            await server.service.operator_stop()
            terminal = await consume_terminal(viewer, checker, timeout=5)
            assert terminal[2] == "stopped"
            kinds = [record[1] for record in checker.events]
            assert kinds == ["status", "partial", "status", "status"]
            assert not any(record[1] == "final" for record in checker.events)
            assert server.service.timeline.mutable is None
            stale_generation = server.service.run_generation
            await server.service.publish_transcript(
                event_id=event_id,
                revision=2,
                segment_id=event_id,
                start_ms=9_000,
                end_ms=11_000,
                text="late final",
                is_final=True,
                occurred_at=utc_stamp(),
            )
            # Invalidation bumps schedule_generation; held publish is a no-op.
            assert (
                server.service.schedule_generation != stale_generation
                or not server.service.ingest_open
            )
            await expect_no_message(viewer, timeout=0.6)
            await viewer.close()

    asyncio.run(scenario())


def test_stale_generation_publishes_nothing() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            viewer = await connect_viewer(server)
            ready = await read_ready(viewer)
            checker = OrderChecker(ready["session_id"], ready["epoch"], ready["next_seq"])
            await checker.consume(viewer)
            publish_before = server.service.observations.publish_count
            await server.service.close_ingest()
            # Wait for terminal to drain so we know close_ingest published.
            await consume_terminal(viewer, checker, timeout=5)
            after_terminal = server.service.observations.publish_count
            assert after_terminal > publish_before
            # Stale generation: run_generation lags schedule_generation after invalidate.
            await server.service.publish_status("live")
            assert server.service.observations.publish_count == after_terminal
            await expect_no_message(viewer, timeout=0.5)
            await viewer.close()

    asyncio.run(scenario())


def test_new_session_replaces_prior_session() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            first_session = server.service.timeline.session_id
            await server.open_session()
            assert server.service.timeline.session_id != first_session
            assert server.service.timeline.epoch == 1
            viewer = await connect_viewer(server)
            ready = await read_ready(viewer)
            assert ready["session_id"] == server.service.timeline.session_id
            assert ready["epoch"] == "1"
            await viewer.close()

    asyncio.run(scenario())
