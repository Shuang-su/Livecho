"""Closed-by-default live / wire / archive entry points."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Reason = Literal[
    "live_adapter_disabled",
    "wire_publish_disabled",
    "archive_disabled",
]


@dataclass(frozen=True, slots=True)
class FeatureFlags:
    live_chat_adapter: bool = False
    wire_publish: bool = False
    raw_archive: bool = False


# Checked-in defaults stay off. Tests assert these remain False.
FLAGS = FeatureFlags()


def attempt_live_adapter() -> Reason:
    return "live_adapter_disabled"


def attempt_wire_publish() -> Reason:
    return "wire_publish_disabled"


def attempt_archive() -> Reason:
    return "archive_disabled"
