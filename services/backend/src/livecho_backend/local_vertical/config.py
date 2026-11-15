"""Closed mode configuration, loopback binding, and fan-out limits for Issue #9."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

VIEWER_ENDPOINT_PATH = "/api/viewer/ws"
WORKER_ENDPOINT_PATH = "/api/worker/ws"

MAX_VIEWERS = 20
MAX_RETAINED_DOMAINS = 20
DOMAIN_RETENTION_SECONDS = 10.0
PER_VIEWER_MAX_MESSAGES = 32
PER_VIEWER_MAX_BYTES = 262_144
AGGREGATE_QUEUE_BYTES = 5_242_880
SEND_DEADLINE_SECONDS = 0.5
PRE_TERMINAL_DRAIN_SECONDS = 2.0

FIXTURE_FINAL_DEADLINE_MS = 1_000
FIXTURE_ADMISSION_INTERVAL_MS = 2_000
FIXTURE_MAX_DURATION_SECONDS = 60.0

DEFAULT_ROOM_ID = "livecho.fixture.room"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost"})
DEV_ORIGIN_PORTS = frozenset({5173, 4173})


class LocalVerticalMode(StrEnum):
    """Explicitly labeled local vertical modes; only fixture_timeline is enabled."""

    FIXTURE_TIMELINE = "fixture_timeline"
    SYNTHETIC_MLX = "synthetic_mlx"


@dataclass(frozen=True, slots=True)
class LocalVerticalConfig:
    """Loopback-only local vertical configuration."""

    mode: LocalVerticalMode = LocalVerticalMode.FIXTURE_TIMELINE
    host: str = "127.0.0.1"
    port: int = 8787
    room_id: str = DEFAULT_ROOM_ID

    def allowed_origins(self) -> frozenset[str]:
        """Exact-origin allowlist for the serving port and local dev shells."""
        origins: set[str] = set()
        for host in LOOPBACK_HOSTS:
            origins.add(f"http://{host}:{self.port}")
            for dev_port in DEV_ORIGIN_PORTS:
                origins.add(f"http://{host}:{dev_port}")
        return frozenset(origins)

    def is_loopback_host(self) -> bool:
        return self.host in LOOPBACK_HOSTS
