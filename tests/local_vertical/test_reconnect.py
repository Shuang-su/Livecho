"""Wire-level reconnect tests: cursor resume, domain expiry, fresh admission."""

from __future__ import annotations

import asyncio
from uuid import uuid4

from livecho_backend.local_vertical.config import MAX_RETAINED_DOMAINS
from livecho_backend.local_vertical.timeline import utc_stamp

from .helpers import (
    LocalServer,
    OrderChecker,
    backend_server,
    connect_viewer,
    expect_closed,
    next_message,
    read_ready,
    viewer_cursor,
)


async def publish_event(
    server: LocalServer,
    *,
    event_id: str,
    is_final: bool,
    text: str,
    start_ms: int,
    revision: int = 1,
    occurred_at: str | None = None,
) -> None:
    await server.service.publish_transcript(
        event_id=event_id,
        revision=revision,
        segment_id=event_id,
        start_ms=start_ms,
        end_ms=start_ms + 2_000,
        text=text,
        is_final=is_final,
        occurred_at=occurred_at or utc_stamp(),
    )


def test_exact_zero_loss_resume() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            first = await connect_viewer(server)
            ready = await read_ready(first)
            checker = OrderChecker(ready["session_id"], ready["epoch"], ready["next_seq"])
            await checker.consume(first)  # admission live status
            position = checker.next_seq
            await first.close()
            # Domain retention happens in the websocket finally; give it a tick.
            await asyncio.sleep(0.05)
            resumed = await connect_viewer(
                server, cursor=viewer_cursor(ready["session_id"], "1", str(position))
            )
            resumed_ready = await read_ready(resumed)
            assert resumed_ready["cursor_resumed"] is True
            assert int(resumed_ready["next_seq"]) == position
            checker_two = OrderChecker(
                resumed_ready["session_id"], resumed_ready["epoch"], resumed_ready["next_seq"]
            )
            await publish_event(
                server, event_id=str(uuid4()), is_final=True, text="post resume", start_ms=9_000
            )
            assert await checker_two.consume(resumed) is None
            assert checker_two.events == [(position, "final", "")]
            await resumed.close()

    asyncio.run(scenario())


def test_resume_after_timeline_advanced_is_refused_with_resync() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            first = await connect_viewer(server)
            ready = await read_ready(first)
            checker = OrderChecker(ready["session_id"], ready["epoch"], ready["next_seq"])
            await checker.consume(first)
            position = checker.next_seq
            await first.close()
            await asyncio.sleep(0.05)
            await server.service.publish_status("live")
            stale = await connect_viewer(
                server, cursor=viewer_cursor(ready["session_id"], "1", str(position))
            )
            error = await next_message(stale)
            assert error["type"] == "protocol.error"
            assert error["code"] == "resync_required"
            assert error["retryable"] is True
            await expect_closed(stale)
            fresh = await connect_viewer(server)
            fresh_ready = await read_ready(fresh)
            assert fresh_ready["cursor_resumed"] is False
            status = await next_message(fresh)
            assert status["payload"]["status"] == "live"
            assert int(status["seq"]) > position
            await fresh.close()

    asyncio.run(scenario())


def test_retained_domain_expiry_forces_resync() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            first = await connect_viewer(server)
            ready = await read_ready(first)
            checker = OrderChecker(ready["session_id"], ready["epoch"], ready["next_seq"])
            await checker.consume(first)
            position = checker.next_seq
            await first.close()
            await asyncio.sleep(0.05)
            # Force-expire every retained domain without waiting the full TTL.
            for domain in list(server.service.registry.retained.values()):
                domain.expires_at = 0.0
            stale = await connect_viewer(
                server, cursor=viewer_cursor(ready["session_id"], "1", str(position))
            )
            error = await next_message(stale)
            assert error["code"] == "resync_required"
            await expect_closed(stale)

    asyncio.run(scenario())


def test_retained_domain_limit_evicts_oldest() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            # Fill retained domains by connecting and disconnecting.
            for _ in range(MAX_RETAINED_DOMAINS + 2):
                connection = await connect_viewer(server)
                await read_ready(connection)
                await next_message(connection)
                await connection.close()
                await asyncio.sleep(0.02)
            assert len(server.service.registry.retained) <= MAX_RETAINED_DOMAINS

    asyncio.run(scenario())


def test_fresh_refused_while_partial_open_then_admitted_after_final() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            admitted = await connect_viewer(server)
            ready = await read_ready(admitted)
            checker = OrderChecker(ready["session_id"], ready["epoch"], ready["next_seq"])
            await checker.consume(admitted)
            event_id = str(uuid4())
            occurred_at = utc_stamp()
            await publish_event(
                server,
                event_id=event_id,
                is_final=False,
                text="open…",
                start_ms=1_000,
                occurred_at=occurred_at,
            )
            await checker.consume(admitted)
            refused = await connect_viewer(server)
            error = await next_message(refused)
            assert error["code"] == "resync_required"
            assert error["retryable"] is True
            await expect_closed(refused)
            await publish_event(
                server,
                event_id=event_id,
                is_final=True,
                text="open final",
                start_ms=1_000,
                revision=2,
                occurred_at=occurred_at,
            )
            await checker.consume(admitted)
            # Fresh admission is allowed immediately after final (interval gates
            # the next mutable object, not viewer joins).
            fresh = await connect_viewer(server)
            fresh_ready = await read_ready(fresh)
            assert fresh_ready["cursor_resumed"] is False
            status = await next_message(fresh)
            assert status["payload"]["status"] == "live"
            assert int(status["revision"]) == 1
            await fresh.close()
            await admitted.close()

    asyncio.run(scenario())


def test_eligible_resume_while_partial_open() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            first = await connect_viewer(server)
            ready = await read_ready(first)
            checker = OrderChecker(ready["session_id"], ready["epoch"], ready["next_seq"])
            await checker.consume(first)
            event_id = str(uuid4())
            occurred_at = utc_stamp()
            await publish_event(
                server,
                event_id=event_id,
                is_final=False,
                text="keep…",
                start_ms=2_000,
                occurred_at=occurred_at,
            )
            await checker.consume(first)
            position = checker.next_seq
            await first.close()
            await asyncio.sleep(0.05)
            resumed = await connect_viewer(
                server, cursor=viewer_cursor(ready["session_id"], "1", str(position))
            )
            resumed_ready = await read_ready(resumed)
            assert resumed_ready["cursor_resumed"] is True
            assert int(resumed_ready["next_seq"]) == position
            await publish_event(
                server,
                event_id=event_id,
                is_final=True,
                text="keep final",
                start_ms=2_000,
                revision=2,
                occurred_at=occurred_at,
            )
            # Client keeps reducer state across a zero-loss resume.
            assert await checker.consume(resumed) is None
            assert checker.events[-1][1] == "final"
            await resumed.close()

    asyncio.run(scenario())


def test_new_session_clears_retained_domains() -> None:
    async def scenario() -> None:
        async with backend_server() as server:
            await server.open_session()
            first = await connect_viewer(server)
            ready = await read_ready(first)
            checker = OrderChecker(ready["session_id"], ready["epoch"], ready["next_seq"])
            await checker.consume(first)
            position = checker.next_seq
            await first.close()
            await asyncio.sleep(0.05)
            assert server.service.registry.retained
            await server.open_session()
            assert not server.service.registry.retained
            stale = await connect_viewer(
                server, cursor=viewer_cursor(ready["session_id"], "1", str(position))
            )
            error = await next_message(stale)
            assert error["code"] == "resync_required"
            await expect_closed(stale)

    asyncio.run(scenario())
