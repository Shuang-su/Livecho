"""Synthetic fixture validation. Not a live Bilibili schema."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Literal

Reason = Literal[
    "schema_invalid",
    "sensitive_field_refused",
    "text_invalid",
    "batch_too_large",
]

CLASSES = frozenset({"danmaku", "superchat", "status", "transcript_companion"})
STATUS_VALUES = frozenset({"starting", "live", "stopping", "stopped", "failed"})
SOURCE_EVENT_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
ROOM_ID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
REASON_CODE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
CURRENCY = re.compile(r"^[A-Z]{3,8}$")
TIMESTAMP = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$")
SESSION_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
SENSITIVE = frozenset(
    {
        "cookie",
        "cookies",
        "authorization",
        "auth_token",
        "sessdata",
        "bili_jct",
        "signed_url",
        "playback_url",
        "pcm",
        "wav",
        "audio",
        "base64",
        "password",
    }
)
MAX_ITEM_BYTES = 8 * 1024
MAX_BATCH = 256
TOP_KEYS = frozenset({"fixture_class", "source_event_id", "source_ts", "body"})
OUTPUT_KEYS = frozenset(
    {
        "schema_version",
        "class",
        "source_event_id",
        "source_ts",
        "received_ts",
        "room_id",
        "session_id",
        "payload",
    }
)


def _require_nfc(text: object, *, min_len: int, max_len: int) -> str | None:
    if not isinstance(text, str):
        return None
    if unicodedata.normalize("NFC", text) != text:
        return None
    try:
        text.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        return None
    if any(unicodedata.category(ch) == "Cs" for ch in text):
        return None
    n = len(text)
    if n < min_len or n > max_len:
        return None
    return text


def _collect_keys(value: Any, into: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str):
                into.add(key)
            _collect_keys(child, into)
    elif isinstance(value, list):
        for child in value:
            _collect_keys(child, into)


def sensitive_keys_present(item: dict[str, Any]) -> bool:
    names: set[str] = set()
    _collect_keys(item, names)
    return any(name.casefold() in SENSITIVE for name in names)


def item_utf8_size(item: dict[str, Any]) -> int:
    return len(json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def validate_room_session(room_id: str, session_id: str) -> Reason | None:
    if not isinstance(room_id, str) or not ROOM_ID.fullmatch(room_id):
        return "schema_invalid"
    if not isinstance(session_id, str) or not SESSION_UUID.fullmatch(session_id):
        return "schema_invalid"
    return None


def validate_fixture_item(item: object) -> tuple[dict[str, Any] | None, Reason | None]:
    if not isinstance(item, dict):
        return None, "schema_invalid"
    if sensitive_keys_present(item):
        return None, "sensitive_field_refused"
    if item_utf8_size(item) > MAX_ITEM_BYTES:
        return None, "schema_invalid"
    if set(item.keys()) != TOP_KEYS:
        return None, "schema_invalid"

    fixture_class = item.get("fixture_class")
    source_event_id = item.get("source_event_id")
    source_ts = item.get("source_ts")
    body = item.get("body")
    if fixture_class not in CLASSES:
        return None, "schema_invalid"
    if not isinstance(source_event_id, str) or not SOURCE_EVENT_ID.fullmatch(source_event_id):
        return None, "schema_invalid"
    if not isinstance(source_ts, str) or not TIMESTAMP.fullmatch(source_ts):
        return None, "schema_invalid"
    if not isinstance(body, dict):
        return None, "schema_invalid"
    for value in body.values():
        if isinstance(value, dict | list):
            return None, "schema_invalid"

    if fixture_class == "danmaku":
        return _validate_danmaku(fixture_class, source_event_id, source_ts, body)
    if fixture_class == "superchat":
        return _validate_superchat(fixture_class, source_event_id, source_ts, body)
    if fixture_class == "status":
        return _validate_status(fixture_class, source_event_id, source_ts, body)
    return _validate_transcript(fixture_class, source_event_id, source_ts, body)


def _ok(
    fixture_class: str,
    source_event_id: str,
    source_ts: str,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], None]:
    return (
        {
            "fixture_class": fixture_class,
            "source_event_id": source_event_id,
            "source_ts": source_ts,
            "payload": payload,
        },
        None,
    )


def _validate_danmaku(
    fixture_class: str,
    source_event_id: str,
    source_ts: str,
    body: dict[str, Any],
) -> tuple[dict[str, Any] | None, Reason | None]:
    allowed = {"text", "sender_display"}
    if not set(body.keys()).issubset(allowed) or "text" not in body:
        return None, "schema_invalid"
    text = _require_nfc(body["text"], min_len=1, max_len=512)
    if text is None:
        return None, "text_invalid" if isinstance(body["text"], str) else "schema_invalid"
    out: dict[str, Any] = {"text": text}
    if "sender_display" in body:
        sender = _require_nfc(body["sender_display"], min_len=1, max_len=64)
        if sender is None:
            reason: Reason = (
                "text_invalid" if isinstance(body["sender_display"], str) else "schema_invalid"
            )
            return None, reason
        out["sender_display"] = sender
    return _ok(fixture_class, source_event_id, source_ts, out)


def _validate_superchat(
    fixture_class: str,
    source_event_id: str,
    source_ts: str,
    body: dict[str, Any],
) -> tuple[dict[str, Any] | None, Reason | None]:
    allowed = {"text", "sender_display", "amount_display", "currency_code"}
    if not set(body.keys()).issubset(allowed) or "text" not in body:
        return None, "schema_invalid"
    text = _require_nfc(body["text"], min_len=1, max_len=512)
    if text is None:
        return None, "text_invalid" if isinstance(body["text"], str) else "schema_invalid"
    out: dict[str, Any] = {"text": text}
    if "sender_display" in body:
        sender = _require_nfc(body["sender_display"], min_len=1, max_len=64)
        if sender is None:
            reason: Reason = (
                "text_invalid" if isinstance(body["sender_display"], str) else "schema_invalid"
            )
            return None, reason
        out["sender_display"] = sender
    if "amount_display" in body:
        amount = _require_nfc(body["amount_display"], min_len=1, max_len=32)
        if amount is None:
            reason = "text_invalid" if isinstance(body["amount_display"], str) else "schema_invalid"
            return None, reason
        out["amount_display"] = amount
    if "currency_code" in body:
        code = body["currency_code"]
        if not isinstance(code, str) or not CURRENCY.fullmatch(code):
            return None, "schema_invalid"
        out["currency_code"] = code
    return _ok(fixture_class, source_event_id, source_ts, out)


def _validate_status(
    fixture_class: str,
    source_event_id: str,
    source_ts: str,
    body: dict[str, Any],
) -> tuple[dict[str, Any] | None, Reason | None]:
    allowed = {"status", "reason_code"}
    if not set(body.keys()).issubset(allowed) or "status" not in body:
        return None, "schema_invalid"
    status = body["status"]
    if status not in STATUS_VALUES:
        return None, "schema_invalid"
    out: dict[str, Any] = {"status": status}
    if "reason_code" in body:
        reason = body["reason_code"]
        if not isinstance(reason, str) or not REASON_CODE.fullmatch(reason):
            return None, "schema_invalid"
        out["reason_code"] = reason
    return _ok(fixture_class, source_event_id, source_ts, out)


def _validate_transcript(
    fixture_class: str,
    source_event_id: str,
    source_ts: str,
    body: dict[str, Any],
) -> tuple[dict[str, Any] | None, Reason | None]:
    allowed = {"text", "start_ms", "end_ms", "is_final"}
    if not set(body.keys()).issubset(allowed):
        return None, "schema_invalid"
    if "text" not in body or "start_ms" not in body or "end_ms" not in body:
        return None, "schema_invalid"
    text = _require_nfc(body["text"], min_len=1, max_len=4096)
    if text is None:
        return None, "text_invalid" if isinstance(body["text"], str) else "schema_invalid"
    start = body["start_ms"]
    end = body["end_ms"]
    if type(start) is not int or type(end) is not int:
        return None, "schema_invalid"
    if not (0 <= start < end <= start + 30_000):
        return None, "schema_invalid"
    out: dict[str, Any] = {"text": text, "start_ms": start, "end_ms": end}
    if "is_final" in body:
        if not isinstance(body["is_final"], bool):
            return None, "schema_invalid"
        out["is_final"] = body["is_final"]
    return _ok(fixture_class, source_event_id, source_ts, out)
