"""Twenty-viewer fan-out saturation (stress; excluded from `make verify`)."""

from __future__ import annotations

import asyncio

import pytest
from livecho_backend.local_vertical.config import MAX_VIEWERS
from livecho_backend.local_vertical.schedule import FixtureScheduleSpec
from websockets.asyncio.client import ClientConnection

from .helpers import (
    OrderChecker,
    backend_server,
    connect_viewer,
    expect_rejected,
    read_ready,
)


async def _drain_fast(
    connection: ClientConnection, checker: OrderChecker, *, timeout: float = 40.0
) -> list[tuple[int, str, str]]:
    while True:
        terminal = await checker.consume(connection, timeout=timeout)
        if terminal is not None and terminal[2] in ("stopped", "failed"):
            return list(checker.events)


async def _drain_paced(
    connection: ClientConnection,
    checker: OrderChecker,
    *,
    hz: float,
    timeout: float = 45.0,
) -> list[tuple[int, str, str]]:
    interval = 1.0 / hz
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        remaining = deadline - asyncio.get_running_loop().time()
        terminal = await checker.consume(connection, timeout=max(0.5, remaining))
        if terminal is not None and terminal[2] in ("stopped", "failed"):
            return list(checker.events)
        await asyncio.sleep(interval)
    raise AssertionError("paced viewer did not reach a terminal status")


async def _drain_stalled(
    connection: ClientConnection,
    checker: OrderChecker,
    *,
    stall_seconds: float = 2.0,
    timeout: float = 45.0,
) -> list[tuple[int, str, str]]:
    await asyncio.sleep(stall_seconds)
    while True:
        terminal = await checker.consume(connection, timeout=timeout)
        if terminal is not None and terminal[2] in ("stopped", "failed"):
            return list(checker.events)


@pytest.mark.stress
def test_twenty_viewers_reach_shared_terminal_without_holding_fast_peers() -> None:
    async def scenario() -> None:
        spec = FixtureScheduleSpec(
            segments=2,
            interval_ms=2_500,
            with_partials=True,
        )
        async with backend_server() as server:
            await server.start_session(spec)

            fast_connections: list[ClientConnection] = []
            checkers: list[OrderChecker] = []
            for _ in range(18):
                connection = await connect_viewer(server)
                ready = await read_ready(connection)
                checker = OrderChecker(ready["session_id"], ready["epoch"], ready["next_seq"])
                # Admission status is consumed inside the drain loop.
                fast_connections.append(connection)
                checkers.append(checker)

            paced_connection = await connect_viewer(server)
            paced_ready = await read_ready(paced_connection)
            paced_checker = OrderChecker(
                paced_ready["session_id"], paced_ready["epoch"], paced_ready["next_seq"]
            )

            stalled_connection = await connect_viewer(server)
            stalled_ready = await read_ready(stalled_connection)
            stalled_checker = OrderChecker(
                stalled_ready["session_id"],
                stalled_ready["epoch"],
                stalled_ready["next_seq"],
            )

            assert server.admitted_count() == MAX_VIEWERS
            await expect_rejected(connect_viewer(server), status=403)

            fast_tasks = [
                asyncio.create_task(_drain_fast(connection, checker))
                for connection, checker in zip(fast_connections, checkers, strict=True)
            ]
            paced_task = asyncio.create_task(_drain_paced(paced_connection, paced_checker, hz=1.0))
            stalled_task = asyncio.create_task(
                _drain_stalled(stalled_connection, stalled_checker, stall_seconds=2.0)
            )

            fast_results = await asyncio.gather(*fast_tasks)
            paced_events = await paced_task
            stalled_events = await stalled_task

            # Fresh joins fan out a newly sequenced status to peers, so absolute
            # event lists differ by join order. Each viewer must still reach the
            # shared terminal with contiguous sequences and no ordering break.
            for events in (*fast_results, paced_events, stalled_events):
                assert events, "viewer observed no timeline events"
                assert events[-1][2] == "stopped"
                seqs = [seq for seq, _kind, _status in events]
                assert seqs == list(range(seqs[0], seqs[0] + len(seqs)))

            snapshot = server.service.observations.snapshot()
            assert snapshot.get("real_asr_evidence") is False
            assert snapshot.get("peak_viewers") == MAX_VIEWERS
            for connection in (*fast_connections, paced_connection, stalled_connection):
                await connection.close()

    asyncio.run(scenario())
