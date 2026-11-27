"""Serialized synthetic worker promotion and caption publication."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from livecho_protocol.binary import PcmHeaderV1
from livecho_protocol.compatibility import manifest_key
from livecho_protocol.errors import Decision, StableCode
from livecho_protocol.long_session import Minor1SessionRuntime, SessionUpdate
from livecho_protocol.models import (
    ModelManifestRefV1,
    TimelineEventV1Minor1,
    TranscriptSegmentV1,
    TranscriptTimelinePayloadV1,
    WorkerHelloV1,
)
from livecho_protocol.runtime import LeaseRuntimeCoordinator

from livecho_backend.worker_gateway import wire
from livecho_backend.worker_gateway.gateway import (
    LEASE_LIFETIME,
    WorkerGateway,
    _Connection,
    _Grant,
    _Lease,
)
from livecho_backend.worker_identity.clock import format_timestamp
from livecho_backend.worker_identity.service import WorkerIdentityService

from .viewer import Viewers

MAX_WORKERS = 3


@dataclass(frozen=True, slots=True)
class SyntheticObservation:
    """Trusted fixture observation for the fixed manifest, independent of Hello."""

    fresh_until: datetime
    warm: bool
    capacity: int
    realtime_factor: float
    reliability: float

    def qualifies(self, now: datetime) -> bool:
        return (
            now < self.fresh_until
            and self.warm
            and self.capacity > 0
            and 0 < self.realtime_factor <= 1
            and 0 <= self.reliability <= 1
        )

    def rank(self, device_id: str) -> tuple[int, float, float, str]:
        return (-self.capacity, self.realtime_factor, -self.reliability, device_id)


class SyntheticFailoverGateway(WorkerGateway):
    """One fixed synthetic session and the #27 owner of both ordering domains."""

    def __init__(
        self,
        identity: WorkerIdentityService,
        *,
        session_id: str,
        room_id: str,
        manifest: ModelManifestRefV1,
        observations: Mapping[str, SyntheticObservation],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__(identity, clock=clock)
        self.session_id = session_id
        self.room_id = room_id
        self.manifest = manifest
        self._observed = dict(observations)
        self._key = manifest_key(manifest)
        self._leases = LeaseRuntimeCoordinator(accepted_manifests=frozenset({self._key}))
        self.protocol = Minor1SessionRuntime(session_id, room_id, leases=self._leases)
        self.viewers = Viewers(self.protocol, room_id, session_id, self._lock, self._now)
        self._occurred_at = format_timestamp(self._now())
        self._stopped = False

    def _allowlisted(self) -> bool:
        return any(entry.key() == self._key for entry in self.identity.store.allowlist())

    async def arm_grant(self, session_id: str, room_id: str, manifest: ModelManifestRefV1) -> bool:
        if (session_id, room_id, manifest) != (self.session_id, self.room_id, self.manifest):
            return False
        async with self._lock:
            if self._stopped or not self._allowlisted():
                return False
            self._grant = _Grant(session_id, room_id, manifest)
            await self._expire_locked(self._now())
            return not self._stopped

    async def observe(self, device_id: str, observation: SyntheticObservation) -> None:
        """Refresh admission measurements for a fixture worker."""
        async with self._lock:
            if device_id in self._observed:
                self._observed[device_id] = observation
                await self._expire_locked(self._now())

    def _allows_standby(self) -> bool:
        return True

    async def _detach_for_resume(self, connection: _Connection, now: datetime) -> None:
        # A freshly proved exact cursor transfers the existing lease without rotating it.
        await super()._detach(connection, now)
        connection.lease = None

    async def _admit_connection(
        self, connection: _Connection, hello: WorkerHelloV1, now: datetime
    ) -> bool:
        if connection.minor != 1:
            await self._error(connection, StableCode.UNSUPPORTED_MINOR, now)
            return False
        if (
            self._stopped
            or connection.device_id not in self._observed
            or self.manifest not in connection.manifests
            or not self._allowlisted()
        ):
            await self._error(connection, StableCode.BINDING_MISMATCH, now)
            return False
        if hello.resume is None and (
            len(self._connections) >= MAX_WORKERS
            or any(other.device_id == connection.device_id for other in self._connections.values())
        ):
            await self._error(connection, StableCode.RESYNC_REQUIRED, now)
            return False
        return await super()._admit_connection(connection, hello, now)

    async def _issue_locked(self, _requested_at: datetime) -> None:
        if self._stopped or self._grant is None or self._active is not None:
            return
        if not self._allowlisted():
            return
        now = self._now()
        eligible = [
            connection
            for connection in self._connections.values()
            if connection.lease is None
            and self.device_checked(connection.id)
            and self.manifest in connection.manifests
            and self._observed[connection.device_id].qualifies(now)
        ]
        if not eligible:
            return
        connection = min(eligible, key=lambda c: self._observed[c.device_id].rank(c.device_id))
        model = wire.lease(
            self._fields("worker.lease", 1, now),
            minor=1,
            lease_id=self._new_id(),
            session_id=self.session_id,
            room_id=self.room_id,
            issued_at=format_timestamp(now),
            expires_at=format_timestamp(now + LEASE_LIFETIME),
            manifest=self.manifest,
            epoch=self.protocol.epoch,
        )
        decision = self.protocol.install_lease(model, now=now)
        if not decision.accepted:
            await self._error(connection, decision.code, now)
            return
        runtime = self.protocol.active_lease_runtime
        assert runtime is not None
        active = _Lease(model, runtime, connection, 1, now)
        self._active = connection.lease = active
        try:
            await self._send(connection, model, now)
        except asyncio.CancelledError:
            if self._active is active:
                await self._detach(connection, self._now())
            raise

    def _accept_pcm_header(self, active: _Lease, header: PcmHeaderV1, now: datetime) -> Decision:
        return self.protocol.accept_pcm_header(header, now=now)

    async def _accept_output(
        self,
        connection: _Connection,
        message: wire.WorkerOutput,
        raw: dict[str, Any],
        now: datetime,
    ) -> None:
        active = self._active
        if active is None or active.connection is not connection:
            await self._error(connection, StableCode.LEASE_UNKNOWN, now)
            return
        if not self.device_checked(connection.id) or not self._allowlisted():
            await self._cancel(connection, "policy_disable", now)
            return
        update = self.protocol.accept_worker(message, now=now)
        if update.decision.code is StableCode.ACCEPTED and isinstance(message, TranscriptSegmentV1):
            event = self._caption(message, now)
            update = self.protocol.accept_viewer_event(event, now=now)
            if update.decision.code is StableCode.ACCEPTED:
                self.viewers.publish(event)
        if update.rotation is not None:
            await self._apply_rotation(active, update, now, notify_worker=True)
            await self._issue_locked(self._now())
            return
        await self._acknowledge_output(active, message, update.decision, now)

    def _caption(self, message: TranscriptSegmentV1, now: datetime) -> TimelineEventV1Minor1:
        return TimelineEventV1Minor1(
            protocol="livecho.viewer.v1",
            protocol_minor=1,
            type="viewer.timeline_event",
            message_id=self._new_id(),
            sent_at=format_timestamp(now),
            session_id=self.session_id,
            room_id=self.room_id,
            event_id=message.segment_id,
            epoch=message.epoch,
            seq=str(self.protocol.viewer_next_seq),
            revision=message.revision,
            occurred_at=self._occurred_at,
            payload=TranscriptTimelinePayloadV1(
                segment_id=message.segment_id,
                start_ms=message.start_ms,
                end_ms=message.end_ms,
                text=message.text,
                language=message.language,
                confidence=message.confidence,
                is_final=message.is_final,
            ),
        )

    async def _expire_locked(self, now: datetime) -> None:
        for connection in tuple(self._connections.values()):
            if not self.device_checked(connection.id) or not self._allowlisted():
                await self._cancel(connection, "policy_disable", now)
        active = self._active
        if active is not None and now >= active.runtime.expires_at:
            self._finish_online(active.connection, active.runtime.expires_at)
            try:
                await self._replace(active, now, notify_worker=True)
            finally:
                await super()._detach(active.connection, self._now())
        await self._issue_locked(now)

    async def _replace(self, active: _Lease, now: datetime, *, notify_worker: bool) -> None:
        self._active = None
        update = self.protocol.replace_lease(now=now)
        await self._apply_rotation(active, update, now, notify_worker=notify_worker)

    async def _apply_rotation(
        self, active: _Lease, update: SessionUpdate, now: datetime, *, notify_worker: bool
    ) -> None:
        self._active = None
        rotation = update.rotation
        if rotation is None:
            await self._stop_locked(now)
            return
        self.viewers.resync(rotation.viewer)
        previous = active.connection
        if rotation.worker.reason == "revision_capacity":
            # Capacity is an ordering boundary, so a healthy peer can qualify again.
            previous.lease = None
        if notify_worker and previous.open:
            await self._send(previous, rotation.worker, now)
        if previous.open and rotation.worker.reason == "revision_capacity":
            await self._send(
                previous,
                wire.error(
                    self._fields("protocol.error", 1, now),
                    minor=1,
                    code=update.decision.code,
                    expected=rotation.worker.opened_epoch,
                    received=rotation.worker.closed_epoch,
                ),
                now,
            )

    async def _detach(self, connection: _Connection, now: datetime) -> None:
        active = self._active
        if active is not None and active.connection is connection:
            try:
                await self._replace(active, now, notify_worker=False)
            finally:
                await super()._detach(connection, self._now())
            await self._issue_locked(self._now())
        else:
            await super()._detach(connection, now)

    async def _stop_locked(self, now: datetime) -> None:
        self._stopped = True
        self._active = self._grant = None
        self.protocol.close()
        self.viewers.close()
        self._results.clear()
        for connection in tuple(self._connections.values()):
            await super()._detach(connection, now)

    async def stop(self) -> None:
        async with self._lock:
            await self._stop_locked(self._now())

    async def restart(self, identity: WorkerIdentityService) -> None:
        # Restart is terminal for a fixed synthetic session.
        await self.stop()
        await super().restart(identity)
