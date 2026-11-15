"""Independent per-viewer fan-out with bounded queues and terminal clear-send."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from livecho_protocol.state import LiveViewerCursor, StreamOrderingState

from .config import (
    AGGREGATE_QUEUE_BYTES,
    DOMAIN_RETENTION_SECONDS,
    MAX_RETAINED_DOMAINS,
    MAX_VIEWERS,
    PER_VIEWER_MAX_BYTES,
    PER_VIEWER_MAX_MESSAGES,
    SEND_DEADLINE_SECONDS,
)
from .observations import LocalVerticalObservations


@dataclass(slots=True)
class QueuedFrame:
    payload: bytes
    seq: int
    is_terminal: bool


@dataclass(slots=True)
class RetainedDomain:
    """Disconnected viewer protocol metadata retained without body replay."""

    key: str
    cursor: LiveViewerCursor
    ordering: StreamOrderingState
    expires_at: float


class ViewerConnection:
    """One admitted viewer with independent send ownership."""

    def __init__(
        self,
        *,
        send_json: Callable[[bytes], Awaitable[None]],
        close_socket: Callable[[], Awaitable[None]],
        observations: LocalVerticalObservations,
    ) -> None:
        self._send_json = send_json
        self._close_socket = close_socket
        self._observations = observations
        self.next_seq: int | None = None
        self.queue: list[QueuedFrame] = []
        self.queue_bytes = 0
        self.open = True
        self.send_in_flight = False
        self.stall_since: float | None = None
        self._send_event = asyncio.Event()
        self.sender_task: asyncio.Task[None] | None = None

    def offer(self, frame: bytes, seq: int, *, is_terminal: bool) -> bool:
        """Count-before-enqueue; return False when this viewer must be detached."""
        if not self.open:
            return False
        if is_terminal and not self.can_deliver_terminal(seq):
            return False
        pending = len(self.queue)
        prospective = pending + (1 if self.send_in_flight else 0)
        prospective_bytes = self.queue_bytes + len(frame)
        if prospective + 1 > PER_VIEWER_MAX_MESSAGES or prospective_bytes > PER_VIEWER_MAX_BYTES:
            return False
        self.queue.append(QueuedFrame(frame, seq, is_terminal))
        self.queue_bytes += len(frame)
        self._send_event.set()
        return True

    def can_deliver_terminal(self, seq: int) -> bool:
        """Terminal may send only as exact-next with no queued or partial write."""
        if self.next_seq is None or seq != self.next_seq:
            return False
        if self.send_in_flight:
            return False
        return len(self.queue) == 0

    async def run_sender(self) -> None:
        """Drain this viewer's queue with a bounded 500 ms send deadline."""
        while self.open:
            await self._send_event.wait()
            self._send_event.clear()
            started = time.monotonic()
            while self.queue and self.open:
                if time.monotonic() - started > SEND_DEADLINE_SECONDS:
                    self._observations.send_deadline_detach_count += 1
                    await self.detach()
                    return
                frame = self.queue[0]
                if frame.is_terminal and not self.can_deliver_terminal(frame.seq):
                    self._observations.terminal_clear_close_count += 1
                    await self.detach()
                    return
                self.send_in_flight = True
                self.stall_since = time.monotonic()
                try:
                    await self._send_json(frame.payload)
                except Exception:
                    await self.detach()
                    return
                finally:
                    self.send_in_flight = False
                self.queue.pop(0)
                self.queue_bytes -= len(frame.payload)
                self.next_seq = frame.seq + 1
                self.stall_since = None
                self._observations.record_send_interval((time.monotonic() - started) * 1_000)

    async def detach(self) -> None:
        if not self.open:
            return
        self.open = False
        self.queue.clear()
        self.queue_bytes = 0
        self._send_event.set()
        await self._close_socket()

    async def detach_pending(self) -> None:
        """Cancel partial send ownership and abandon queued bodies."""
        self.queue.clear()
        self.queue_bytes = 0
        await self.detach()

    async def wait_until_idle(self, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.open and not self.queue and not self.send_in_flight:
                return True
            await asyncio.sleep(0.01)
        return not self.queue and not self.send_in_flight


class ViewerRegistry:
    """Fan-out with aggregate byte accounting and retained disconnect domains."""

    def __init__(self, observations: LocalVerticalObservations) -> None:
        self._observations = observations
        self.active: dict[int, ViewerConnection] = {}
        self._next_connection_id = 1
        self.retained: dict[str, RetainedDomain] = {}
        self.aggregate_queue_bytes = 0

    def connection_count(self) -> int:
        return len(self.active)

    def _retained_key(self, cursor: LiveViewerCursor) -> str:
        return f"{cursor.session_id}|{cursor.epoch}|{cursor.next_seq}"

    def prune_retained(self, now: float | None = None) -> None:
        reference = time.monotonic() if now is None else now
        expired = [key for key, domain in self.retained.items() if domain.expires_at <= reference]
        for key in expired:
            del self.retained[key]

    def find_resume_domain(self, cursor: LiveViewerCursor) -> RetainedDomain | None:
        self.prune_retained()
        return self.retained.get(self._retained_key(cursor))

    def retain_domain(
        self,
        cursor: LiveViewerCursor,
        ordering: StreamOrderingState,
        *,
        now: float | None = None,
    ) -> None:
        reference = time.monotonic() if now is None else now
        self.prune_retained()
        key = self._retained_key(cursor)
        if len(self.retained) >= MAX_RETAINED_DOMAINS and key not in self.retained:
            oldest = next(iter(self.retained))
            del self.retained[oldest]
        self.retained[key] = RetainedDomain(
            key=key,
            cursor=cursor,
            ordering=ordering,
            expires_at=reference + DOMAIN_RETENTION_SECONDS,
        )

    def admit(self, connection: ViewerConnection) -> int | None:
        if len(self.active) >= MAX_VIEWERS:
            return None
        connection_id = self._next_connection_id
        self._next_connection_id += 1
        self.active[connection_id] = connection
        self._observations.viewer_admit_count += 1
        self._observations.peak_viewers = max(self._observations.peak_viewers, len(self.active))
        connection.sender_task = asyncio.create_task(connection.run_sender())
        return connection_id

    def remove(self, connection_id: int) -> ViewerConnection | None:
        return self.active.pop(connection_id, None)

    def _recompute_aggregate(self) -> None:
        total = sum(connection.queue_bytes for connection in self.active.values())
        self.aggregate_queue_bytes = total
        self._observations.peak_aggregate_queue_bytes = max(
            self._observations.peak_aggregate_queue_bytes, total
        )
        for connection in self.active.values():
            self._observations.peak_per_viewer_queue_bytes = max(
                self._observations.peak_per_viewer_queue_bytes,
                connection.queue_bytes,
            )

    def offer_all(
        self,
        frame: bytes,
        seq: int,
        *,
        is_terminal: bool,
    ) -> list[int]:
        """Offer one frame to each active viewer; detach viewers that cannot accept it."""
        detached: list[int] = []
        for connection_id, connection in list(self.active.items()):
            if self.aggregate_queue_bytes + len(frame) > AGGREGATE_QUEUE_BYTES:
                detached.append(connection_id)
                continue
            if not connection.offer(frame, seq, is_terminal=is_terminal):
                detached.append(connection_id)
                continue
        self._recompute_aggregate()
        return detached

    async def detach_all(self, connection_ids: list[int]) -> None:
        for connection_id in connection_ids:
            connection = self.active.pop(connection_id, None)
            if connection is None:
                continue
            self._observations.viewer_detach_count += 1
            if connection.sender_task is not None:
                connection.sender_task.cancel()
            await connection.detach_pending()
        self._recompute_aggregate()

    async def drain_committed(self, *, timeout: float) -> None:
        """Await in-flight sends so exact-next checks reflect real delivery."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.active:
                return
            if all(
                connection.open
                and not connection.send_in_flight
                and not connection.queue
                for connection in self.active.values()
            ):
                return
            await asyncio.sleep(0.01)

    async def fanout_terminal(
        self,
        frame: bytes,
        seq: int,
        *,
        pre_terminal_drain_seconds: float,
    ) -> None:
        deadline = time.monotonic() + pre_terminal_drain_seconds
        while time.monotonic() < deadline:
            await asyncio.gather(
                *[
                    connection.wait_until_idle(pre_terminal_drain_seconds)
                    for connection in self.active.values()
                ]
            )
            if not self.active:
                return
            if all(connection.can_deliver_terminal(seq) for connection in self.active.values()):
                break
            await asyncio.sleep(0.01)
        detached = self.offer_all(frame, seq, is_terminal=True)
        await self.detach_all(detached)
        self._recompute_aggregate()

    async def fanout_event(self, frame: bytes, seq: int, *, is_terminal: bool = False) -> None:
        detached = self.offer_all(frame, seq, is_terminal=is_terminal)
        await self.detach_all(detached)
        self._recompute_aggregate()

    async def close_all(self) -> None:
        await self.detach_all(list(self.active))
        self.retained.clear()
