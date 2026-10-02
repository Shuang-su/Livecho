"""Benchmark-only ownership and scheduling seams; the real MLX adapter is unapproved.

No function in this module allocates, downloads, serializes or hashes audio. Budget
reservations precede a provider's allocation and remain live until its release hook
finishes. Metadata doubles exercise controls without pretending to test host paging.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol

from .contracts import NS, InferenceManifest, Settings


class BlockedEvidence(RuntimeError):
    """Stable reason only: callers must never log a provider exception payload."""


@dataclass(frozen=True)
class Allocation:
    allocation_id: str
    start_pts_ns: int
    end_pts_ns: int
    audio_bytes: int
    canonical_bytes: int


class Budget:
    def __init__(self) -> None:
        self._live: dict[str, tuple[Allocation, Callable[[], None]]] = {}
        self.peak_audio_bytes = 0
        self.peak_canonical_bytes = 0
        self.peak_media_ns = 0
        self.tainted = False

    def reserve(self, allocation: Allocation, release: Callable[[], None]) -> None:
        if self.tainted:
            raise BlockedEvidence("teardown_failed")
        if allocation.allocation_id in self._live:
            raise BlockedEvidence("allocation_duplicate")
        if not (
            0 <= allocation.start_pts_ns < allocation.end_pts_ns
            and allocation.audio_bytes > 0
            and 0 <= allocation.canonical_bytes <= allocation.audio_bytes
        ):
            raise BlockedEvidence("allocation_invalid")
        inventory = [item[0] for item in self._live.values()] + [allocation]
        media = max(a.end_pts_ns for a in inventory) - min(a.start_pts_ns for a in inventory)
        audio = sum(a.audio_bytes for a in inventory)
        canonical = sum(a.canonical_bytes for a in inventory)
        if media > 30 * NS or audio > 16_777_216 or canonical > 960_000:
            raise BlockedEvidence("budget_exceeded")
        self._live[allocation.allocation_id] = (allocation, release)
        self.peak_audio_bytes = max(self.peak_audio_bytes, audio)
        self.peak_canonical_bytes = max(self.peak_canonical_bytes, canonical)
        self.peak_media_ns = max(self.peak_media_ns, media)

    def release(self, allocation_id: str) -> None:
        item = self._live.get(allocation_id)
        if item is None:
            return
        try:
            item[1]()
        except BaseException:
            self.tainted = True
            raise BlockedEvidence("teardown_failed") from None
        del self._live[allocation_id]

    def close(self) -> None:
        for allocation_id in tuple(self._live):
            try:
                self.release(allocation_id)
            except BlockedEvidence:
                continue
        if self._live:
            raise BlockedEvidence("teardown_failed")

    @property
    def live_count(self) -> int:
        return len(self._live)


@dataclass(frozen=True)
class Prefix:
    new_duration_ns: int
    kind: Literal["provisional", "final"]


class PrefixScheduler:
    """One pending *metadata* prefix, never a queue of audio snapshots."""

    def __init__(self, window_ns: int) -> None:
        if window_ns not in {NS, 2 * NS, 4 * NS, 6 * NS}:
            raise ValueError("window")
        self.window_ns = window_ns
        self.latest_ns = 0
        self.next_tick_ns = 250_000_000
        self.pending: Prefix | None = None
        self.running: Prefix | None = None
        self.closed = False
        self.completed = False
        self.missed_opportunities = 0
        self.evaluated_prefixes = 0

    def arrive(self, new_duration_ns: int) -> None:
        if self.closed or not self.latest_ns < new_duration_ns <= self.window_ns:
            raise BlockedEvidence("invalid_timing")
        self.latest_ns = new_duration_ns
        while self.next_tick_ns <= new_duration_ns and self.next_tick_ns < self.window_ns:
            if self.pending is not None:
                self.missed_opportunities += 1
            self.pending = Prefix(self.next_tick_ns, "provisional")
            self.next_tick_ns += 250_000_000

    def close_segment(self) -> None:
        if self.closed or not self.latest_ns:
            raise BlockedEvidence("invalid_timing")
        self.closed = True
        if self.pending is not None:
            self.missed_opportunities += 1
        self.pending = Prefix(self.latest_ns, "final")

    def take(self) -> Prefix | None:
        if self.running is not None or self.completed:
            return None
        self.running, self.pending = self.pending, None
        if self.running and self.running.kind == "provisional":
            self.evaluated_prefixes += 1
        return self.running

    def finish(self) -> None:
        if self.running is None:
            raise BlockedEvidence("call_not_running")
        self.completed = self.running.kind == "final"
        self.running = None


class ProgressWatch:
    """Monotonic source PTS and input-stall checks, using the same runner clock."""

    def __init__(self, now_ns: int) -> None:
        if now_ns < 0:
            raise BlockedEvidence("invalid_timing")
        self.last_input_ns = now_ns
        self.last_pts_ns: int | None = None

    def check(self, now_ns: int) -> None:
        if now_ns < self.last_input_ns:
            raise BlockedEvidence("invalid_timing")
        if now_ns - self.last_input_ns >= 2 * NS:
            raise BlockedEvidence("input_stall")

    def input(self, pts_ns: int, now_ns: int) -> None:
        self.check(now_ns)
        if pts_ns < 0 or (self.last_pts_ns is not None and pts_ns <= self.last_pts_ns):
            raise BlockedEvidence("invalid_timing")
        self.last_pts_ns, self.last_input_ns = pts_ns, now_ns


@dataclass(frozen=True)
class MemoryInput:
    """Borrowed view; never persist/log/repr this object or its underlying storage."""

    view: memoryview
    start_pts_ns: int
    end_pts_ns: int

    def __repr__(self) -> str:
        return "MemoryInput(<ephemeral>)"


@dataclass(frozen=True)
class TextUpdate:
    text: str
    observed_ns: int
    output_tokens: int


class Provider(Protocol):
    def load(self, manifest: InferenceManifest, settings: Settings) -> None: ...

    def transcribe(self, memory_view: MemoryInput, timing: Prefix) -> TextUpdate: ...

    def synchronize(self) -> None: ...

    def close(self) -> None: ...


class UnavailableMLXProvider:
    """No architecture, dependency, allocation or host evidence is installed.

    A model card/label does not authorize loading an arbitrary adapter. These stable
    failures are deliberate; implementing Qwen's MLX forward pass is still required.
    """

    def load(self, manifest: InferenceManifest, settings: Settings) -> None:
        raise BlockedEvidence("independent_mlx_adapter_unavailable")

    def transcribe(self, memory_view: MemoryInput, timing: Prefix) -> TextUpdate:
        raise BlockedEvidence("independent_mlx_adapter_unavailable")

    def synchronize(self) -> None:
        raise BlockedEvidence("independent_mlx_adapter_unavailable")

    def close(self) -> None:
        pass


def guarded_session(provider: Provider, budget: Budget, operation: Callable[[], None]) -> None:
    """Teardown every owned allocation even if operation or provider close fails."""
    failure: str | None = None
    try:
        operation()
    except BlockedEvidence as exc:
        failure = str(exc)
    except BaseException:
        failure = "provider_failure"
    finally:
        try:
            provider.close()
        except BaseException:
            failure = "teardown_failed"
        try:
            budget.close()
        except BlockedEvidence:
            failure = "teardown_failed"
    if failure:
        raise BlockedEvidence(failure) from None
