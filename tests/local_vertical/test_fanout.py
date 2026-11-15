"""Fan-out unit tests with a transport double: caps, deadline, exact-next."""

from __future__ import annotations

import asyncio
import contextlib

from livecho_backend.local_vertical.config import (
    AGGREGATE_QUEUE_BYTES,
    PER_VIEWER_MAX_BYTES,
    PER_VIEWER_MAX_MESSAGES,
    SEND_DEADLINE_SECONDS,
)
from livecho_backend.local_vertical.fanout import ViewerConnection, ViewerRegistry
from livecho_backend.local_vertical.observations import LocalVerticalObservations

from .helpers import StubWebSocket


def new_connection(
    stub: StubWebSocket,
    *,
    position: int = 1,
    observations: LocalVerticalObservations | None = None,
) -> ViewerConnection:
    obs = observations or LocalVerticalObservations()
    connection = ViewerConnection(
        send_json=stub.send_bytes,
        close_socket=stub.close,
        observations=obs,
    )
    connection.next_seq = position
    return connection


def test_offer_enqueues_within_per_viewer_message_cap() -> None:
    stub = StubWebSocket()
    connection = new_connection(stub)
    for index in range(PER_VIEWER_MAX_MESSAGES):
        assert connection.offer(b"x" * 10, index, is_terminal=False)
    assert not connection.offer(b"x" * 10, PER_VIEWER_MAX_MESSAGES, is_terminal=False)
    assert len(connection.queue) == PER_VIEWER_MAX_MESSAGES


def test_offer_enqueues_within_per_viewer_byte_cap() -> None:
    stub = StubWebSocket()
    connection = new_connection(stub)
    big = b"x" * 200_000
    assert connection.offer(big, 1, is_terminal=False)
    overflow = b"x" * PER_VIEWER_MAX_BYTES
    assert not connection.offer(overflow, 2, is_terminal=False)
    assert connection.queue_bytes == len(big)


def test_offer_refuses_beyond_the_aggregate_cap() -> None:
    observations = LocalVerticalObservations()
    registry = ViewerRegistry(observations)
    stub = StubWebSocket()
    connection = new_connection(stub, observations=observations)
    connection.next_seq = 1
    registry.active[1] = connection
    registry.aggregate_queue_bytes = AGGREGATE_QUEUE_BYTES
    detached = registry.offer_all(b"x", 1, is_terminal=False)
    assert detached == [1]


def test_refused_offer_never_grows_state() -> None:
    stub = StubWebSocket()
    connection = new_connection(stub)
    for index in range(PER_VIEWER_MAX_MESSAGES):
        connection.offer(b"x" * 10, index, is_terminal=False)
    before = (len(connection.queue), connection.queue_bytes)
    assert not connection.offer(b"x" * 10, 99, is_terminal=False)
    after = (len(connection.queue), connection.queue_bytes)
    assert before == after


def test_terminal_requires_exact_next_clear_boundary() -> None:
    stub = StubWebSocket()
    connection = new_connection(stub, position=10)
    connection.offer(b"a", 10, is_terminal=False)
    connection.offer(b"b", 11, is_terminal=False)
    assert not connection.can_deliver_terminal(12)
    assert not connection.can_deliver_terminal(10)
    assert not connection.offer(b"t", 12, is_terminal=True)


def test_terminal_delivers_at_clear_exact_next_position() -> None:
    stub = StubWebSocket()
    connection = new_connection(stub, position=12)
    assert connection.can_deliver_terminal(12)
    assert not connection.can_deliver_terminal(13)
    assert connection.offer(b"t", 12, is_terminal=True)


def test_sender_delivers_in_order_and_drops_bodies() -> None:
    async def scenario() -> None:
        stub = StubWebSocket()
        connection = new_connection(stub, position=1)
        for seq in (1, 2, 3):
            connection.offer(f"frame-{seq}".encode(), seq, is_terminal=False)
        task = asyncio.create_task(connection.run_sender())
        deadline = asyncio.get_running_loop().time() + 2
        while connection.queue and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.01)
        assert stub.frames == [b"frame-1", b"frame-2", b"frame-3"]
        assert connection.next_seq == 4
        assert connection.queue_bytes == 0
        connection.open = False
        connection._send_event.set()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    asyncio.run(scenario())


def test_send_failure_removes_only_that_viewer() -> None:
    async def scenario() -> None:
        stub = StubWebSocket(fail=True)
        connection = new_connection(stub, position=1)
        connection.offer(b"frame", 1, is_terminal=False)
        task = asyncio.create_task(connection.run_sender())
        deadline = asyncio.get_running_loop().time() + 2
        while connection.open and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.01)
        assert not connection.open
        assert connection.queue_bytes == 0
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    asyncio.run(scenario())


def test_send_deadline_removes_stalled_viewer() -> None:
    async def scenario() -> None:
        stub = StubWebSocket(block=True)
        observations = LocalVerticalObservations()
        connection = new_connection(stub, observations=observations)
        connection.offer(b"frame", 1, is_terminal=False)
        task = asyncio.create_task(connection.run_sender())
        await asyncio.wait_for(stub.send_started.wait(), timeout=1)
        deadline = asyncio.get_running_loop().time() + SEND_DEADLINE_SECONDS + 1.0
        while connection.open and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.01)
        assert not connection.open
        assert observations.send_deadline_detach_count >= 1
        stub.release()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    asyncio.run(scenario())


def test_detach_drops_every_queued_body_reference() -> None:
    async def scenario() -> None:
        stub = StubWebSocket()
        connection = new_connection(stub, position=1)
        for index in range(5):
            connection.offer(b"x" * 10, index, is_terminal=False)
        await connection.detach_pending()
        assert len(connection.queue) == 0
        assert connection.queue_bytes == 0
        assert not connection.open
        assert not connection.offer(b"x", 9, is_terminal=False)

    asyncio.run(scenario())
