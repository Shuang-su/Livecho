"""Fixed auth log lines. Callers must not pass addresses, tokens, or secrets."""

from __future__ import annotations

import logging

LOGGER = logging.getLogger("livecho.auth")


def log_magic_link(status_code: int) -> None:
    LOGGER.info("magic_link status=%s", status_code)


def log_admin(action: str, actor_id: str, target_id: str, result: str) -> None:
    LOGGER.info(
        "action=%s actor=%s target=%s result=%s",
        action,
        actor_id,
        target_id,
        result,
    )
