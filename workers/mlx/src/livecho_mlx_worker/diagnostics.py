"""Payload-free diagnostics. Never echo transcript text, audio, or absolute paths."""

from __future__ import annotations

import json
from typing import Any

from .gates import Reason


def redact_path(path: str) -> str:
    # Retain only the final path component for operator orientation.
    name = path.replace("\\", "/").rstrip("/").split("/")[-1]
    return name or "redacted"


def result(
    *,
    action: str,
    state: str,
    reasons: tuple[Reason, ...] | list[Reason] = (),
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "action": action,
        "state": state,
        "reasons": list(reasons),
        "fixture_not_speech_recognition": True,
        "real_mlx_partial_support": False,
    }
    if extra:
        # Strip any accidental path/text fields.
        for key, value in extra.items():
            if key in {"text", "transcript", "audio", "path", "model_path"}:
                continue
            if isinstance(value, str) and ("/" in value or "\\" in value):
                payload[key] = redact_path(value)
            else:
                payload[key] = value
    return payload


def write_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"
