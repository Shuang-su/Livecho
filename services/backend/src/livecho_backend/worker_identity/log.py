"""Fixed worker-identity log lines. Callers must not pass secrets."""

from __future__ import annotations

import logging

LOGGER = logging.getLogger("livecho.worker_identity")


def log_worker(action: str, actor_id: str, target_id: str, result: str) -> None:
    LOGGER.info(
        "action=%s actor=%s target=%s result=%s",
        action,
        actor_id,
        target_id,
        result,
    )
