"""Strict scalar definitions for protocol major version 1."""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any
from uuid import UUID

from pydantic import AfterValidator, Field

UINT64_MAX = 18_446_744_073_709_551_615
UINT64_PATTERN = re.compile(r"^(?:0|[1-9][0-9]{0,19})$")
UUID4_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
TIMESTAMP_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$"
)
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-((?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))*))?$"
)


def _uint64(value: str) -> str:
    if not UINT64_PATTERN.fullmatch(value) or int(value) > UINT64_MAX:
        raise ValueError("invalid uint64 decimal")
    return value


def _positive_uint64(value: str) -> str:
    _uint64(value)
    if value == "0":
        raise ValueError("value must be positive")
    return value


def _uuid4(value: str) -> str:
    if not UUID4_PATTERN.fullmatch(value):
        raise ValueError("invalid canonical UUIDv4")
    parsed = UUID(value)
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError("invalid canonical UUIDv4")
    return value


def _timestamp(value: str) -> str:
    if not TIMESTAMP_PATTERN.fullmatch(value):
        raise ValueError("timestamp must use canonical UTC milliseconds")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)
    except ValueError as error:
        raise ValueError("invalid timestamp") from error
    if parsed.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z" != value:
        raise ValueError("timestamp must use canonical UTC milliseconds")
    return value


def _nfc(value: str) -> str:
    if unicodedata.normalize("NFC", value) != value:
        raise ValueError("text must already be NFC")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise ValueError("text must contain Unicode scalar values") from error
    if any(unicodedata.category(character) == "Cs" for character in value):
        raise ValueError("text must contain Unicode scalar values")
    return value


def _semver(value: str) -> str:
    if len(value) > 64 or not SEMVER_PATTERN.fullmatch(value):
        raise ValueError("invalid SemVer without build metadata")
    return value


def decimal_places(value: Any) -> int:
    """Return the number of decimal places in a finite JSON number."""
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError("invalid decimal") from error
    if not decimal.is_finite():
        raise ValueError("number must be finite")
    exponent = decimal.as_tuple().exponent
    if not isinstance(exponent, int):
        raise ValueError("number must be finite")
    return max(0, -exponent)


def parse_timestamp(value: str) -> datetime:
    """Parse a value that has already passed ``TimestampString`` validation."""
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)


Uint64Decimal = Annotated[
    str,
    Field(pattern=r"^(?:0|[1-9][0-9]{0,19})$", json_schema_extra={"format": "uint64-decimal"}),
    AfterValidator(_uint64),
]
PositiveUint64Decimal = Annotated[
    str,
    Field(pattern=r"^(?:[1-9][0-9]{0,19})$", json_schema_extra={"format": "uint64-decimal"}),
    AfterValidator(_positive_uint64),
]
UUID4String = Annotated[
    str,
    Field(pattern=UUID4_PATTERN.pattern, json_schema_extra={"format": "uuid"}),
    AfterValidator(_uuid4),
]
TimestampString = Annotated[
    str,
    Field(pattern=TIMESTAMP_PATTERN.pattern, json_schema_extra={"format": "date-time"}),
    AfterValidator(_timestamp),
]
NFCString = Annotated[str, AfterValidator(_nfc)]
SemVerString = Annotated[
    str,
    Field(min_length=5, max_length=64, pattern=SEMVER_PATTERN.pattern),
    AfterValidator(_semver),
]
RoomId = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._:-]*$")]
ManifestText = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"),
]
Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
LanguageTag = Annotated[
    str,
    Field(min_length=2, max_length=35, pattern=r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$"),
]
ReasonCode = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")]
