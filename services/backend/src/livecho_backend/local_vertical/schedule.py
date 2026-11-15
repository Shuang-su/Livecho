"""Bounded fixture text schedule without audio, worker, or lease fabrication."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .config import FIXTURE_ADMISSION_INTERVAL_MS, FIXTURE_MAX_DURATION_SECONDS
from .timeline import FixtureDeadlineMissed, FixtureScheduleError, utc_stamp

if TYPE_CHECKING:
    from .service import LocalVerticalService

FIXTURE_SEGMENT_TEXTS: tuple[str, ...] = (
    "Welcome to the Livecho synthetic caption demonstration.",
    "This stream is a fixture timeline; it is not recognized speech.",
    "实时字幕为合成夹具，不代表真实语音识别。",  # noqa: RUF001
    f"Long words cannot push controls offscreen: {'interoperability' * 20}",
    "The companion page shows one provisional row and four recent final rows.",
    "You can postpone display by up to five seconds, in steps of one tenth.",
    "Disconnecting immediately clears captions so nothing looks live while offline.",
    "Emojis and line breaks\nare preserved exactly.",
    "A gap notice appears after a resync; it never claims history was replayed.",
    "Stopping the session hides all text at once, ahead of any pending delay.",
    "The demonstration stores no captions on your device, online or offline.",
    "That completes the fixture schedule; the room remains available for review.",
)


def long_text_segment() -> str:
    base = "Synthetic fixture text for layout checks. "
    text = base * (4096 // len(base))
    return text[:4090]


@dataclass(frozen=True, slots=True)
class FixtureScheduleSpec:
    """Deterministic fixture controls; demonstration media is bounded to 60 seconds."""

    segments: int = 12
    interval_ms: int = 3_000
    with_partials: bool = True
    stop_after_segment: int | None = None
    stop_reason: str | None = None
    fail_after_segment: int | None = None
    delete_after_segment: int | None = None
    disable_after_segment: int | None = None


async def _wait_until(
    service: LocalVerticalService,
    *,
    generation: int,
    started_at: float,
    offset_seconds: float,
) -> bool:
    while True:
        if service.schedule_generation != generation or not service.ingest_open:
            return False
        remaining = offset_seconds - (time.monotonic() - started_at)
        if remaining <= 0:
            return True
        await asyncio.sleep(min(remaining, 0.05))


async def run_fixture_schedule(
    service: LocalVerticalService,
    spec: FixtureScheduleSpec,
    *,
    generation: int,
) -> None:
    """Emit synthetic transcript/status on the validated viewer path."""

    total = max(1, spec.segments)
    min_step_ms = FIXTURE_ADMISSION_INTERVAL_MS + 1_500 if spec.with_partials else 2_500
    segment_step_ms = max(min_step_ms, spec.interval_ms)
    planned_ms = 800 + total * segment_step_ms + 2_000
    if planned_ms > FIXTURE_MAX_DURATION_SECONDS * 1_000:
        raise FixtureScheduleError("fixture schedule exceeds 60 second bound")

    started_at = time.monotonic()
    if not await _wait_until(
        service, generation=generation, started_at=started_at, offset_seconds=0.05
    ):
        return
    await service.publish_status("starting")
    if not await _wait_until(
        service, generation=generation, started_at=started_at, offset_seconds=0.35
    ):
        return
    await service.publish_status("live")

    viewer_wait_deadline = time.monotonic() + 1.0
    while service.registry.connection_count() == 0 and time.monotonic() < viewer_wait_deadline:
        if service.schedule_generation != generation or not service.ingest_open:
            return
        await asyncio.sleep(0.05)

    for index in range(total):
        at_seconds = (800 + index * segment_step_ms) / 1_000
        if not await _wait_until(
            service, generation=generation, started_at=started_at, offset_seconds=at_seconds
        ):
            return

        segment_number = index + 1
        if spec.stop_after_segment == segment_number:
            await service.publish_status("stopped", spec.stop_reason)
            return
        if spec.delete_after_segment == segment_number:
            await service.publish_status("stopped", "session_deleted")
            return
        if spec.fail_after_segment == segment_number:
            await service.publish_status("failed", "protocol_failed")
            return
        if spec.disable_after_segment == segment_number:
            await service.close_ingest()
            await service.publish_status("stopped", "ingest_disabled")
            return

        segment_id = str(uuid.uuid4())
        event_id = str(uuid.uuid4())
        occurred_at = utc_stamp()
        start_ms = 800 + index * segment_step_ms
        end_ms = start_ms + 2_000
        text = (
            long_text_segment()
            if index == 0
            else FIXTURE_SEGMENT_TEXTS[index % len(FIXTURE_SEGMENT_TEXTS)]
        )

        if spec.with_partials:
            partial_text = f"{text[: max(1, len(text) // 2)]}…"
            await service.publish_transcript(
                event_id=event_id,
                segment_id=segment_id,
                start_ms=start_ms,
                end_ms=end_ms,
                text=partial_text,
                is_final=False,
                occurred_at=occurred_at,
            )
            if not await _wait_until(
                service,
                generation=generation,
                started_at=started_at,
                offset_seconds=at_seconds + 0.6,
            ):
                return

        await service.publish_transcript(
            event_id=event_id,
            segment_id=segment_id,
            start_ms=start_ms,
            end_ms=end_ms,
            text=text,
            is_final=True,
            occurred_at=occurred_at,
            revision=2 if spec.with_partials else 1,
        )
        if service.schedule_generation != generation or not service.ingest_open:
            return

        try:
            service.timeline.check_mutable_deadline()
        except FixtureDeadlineMissed:
            await service.fail_session("protocol_failed")
            return

    completion_at = (800 + total * segment_step_ms + 1_500) / 1_000
    if not await _wait_until(
        service, generation=generation, started_at=started_at, offset_seconds=completion_at
    ):
        return
    await service.publish_status("stopping")
    if not await _wait_until(
        service, generation=generation, started_at=started_at, offset_seconds=completion_at + 0.4
    ):
        return
    await service.publish_status("stopped")
