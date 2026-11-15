"""Payload-free stage observations for the local caption vertical."""

from __future__ import annotations

from dataclasses import dataclass, field


def _percentile(samples: list[float], ratio: float) -> float | None:
    if not samples:
        return None
    ordered = sorted(samples)
    index = min(len(ordered) - 1, int(ratio * (len(ordered) - 1)))
    return ordered[index]


@dataclass(slots=True)
class LocalVerticalObservations:
    """Counters and peaks without transcript or diagnostic payloads."""

    partial_availability: str = "fixture_partial_only"
    cross_process_latency: str = "unavailable"
    real_asr_evidence: bool = False

    publish_count: int = 0
    viewer_admit_count: int = 0
    viewer_refuse_count: int = 0
    viewer_detach_count: int = 0
    resync_required_count: int = 0
    revision_capacity_rejects: int = 0
    terminal_clear_close_count: int = 0
    send_deadline_detach_count: int = 0
    peak_viewers: int = 0
    peak_aggregate_queue_bytes: int = 0
    peak_per_viewer_queue_bytes: int = 0
    publish_intervals_ms: list[float] = field(default_factory=list)
    send_intervals_ms: list[float] = field(default_factory=list)

    def record_publish_interval(self, interval_ms: float) -> None:
        self.publish_intervals_ms.append(interval_ms)
        if len(self.publish_intervals_ms) > 256:
            self.publish_intervals_ms.pop(0)

    def record_send_interval(self, interval_ms: float) -> None:
        self.send_intervals_ms.append(interval_ms)
        if len(self.send_intervals_ms) > 256:
            self.send_intervals_ms.pop(0)

    def snapshot(self) -> dict[str, object]:
        """Return a payload-free diagnostics summary."""
        return {
            "partial_availability": self.partial_availability,
            "cross_process_latency": self.cross_process_latency,
            "real_asr_evidence": self.real_asr_evidence,
            "publish_count": self.publish_count,
            "viewer_admit_count": self.viewer_admit_count,
            "viewer_refuse_count": self.viewer_refuse_count,
            "viewer_detach_count": self.viewer_detach_count,
            "resync_required_count": self.resync_required_count,
            "revision_capacity_rejects": self.revision_capacity_rejects,
            "terminal_clear_close_count": self.terminal_clear_close_count,
            "send_deadline_detach_count": self.send_deadline_detach_count,
            "peak_viewers": self.peak_viewers,
            "peak_aggregate_queue_bytes": self.peak_aggregate_queue_bytes,
            "peak_per_viewer_queue_bytes": self.peak_per_viewer_queue_bytes,
            "publish_interval_ms_p50": _percentile(self.publish_intervals_ms, 0.5),
            "publish_interval_ms_p95": _percentile(self.publish_intervals_ms, 0.95),
            "send_interval_ms_p50": _percentile(self.send_intervals_ms, 0.5),
            "send_interval_ms_p95": _percentile(self.send_intervals_ms, 0.95),
            "publish_sample_count": len(self.publish_intervals_ms),
            "send_sample_count": len(self.send_intervals_ms),
        }
