"""Bounded JSON parsing, model validation, and RFC 8785 identity helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Any

import rfc8785
from pydantic import ValidationError

from .errors import ProtocolValidationError, StableCode
from .models import MODEL_BY_NAME, VIEWER_PROTOCOL, WORKER_PROTOCOL, StrictModel

MAX_CONTROL_BYTES = 65_536


def _reject_constant(_value: str) -> None:
    raise ValueError("non-finite JSON number")


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolValidationError(StableCode.DUPLICATE_KEY)
        result[key] = value
    return result


def strict_json_loads(raw: str | bytes) -> dict[str, Any]:
    """Parse one bounded UTF-8 JSON object while rejecting duplicate members."""
    if isinstance(raw, bytes):
        if len(raw) > MAX_CONTROL_BYTES:
            raise ProtocolValidationError(StableCode.CONTROL_FRAME_TOO_LARGE)
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise ProtocolValidationError(StableCode.MALFORMED_JSON) from error
    else:
        try:
            encoded = raw.encode("utf-8", errors="strict")
        except UnicodeEncodeError as error:
            raise ProtocolValidationError(StableCode.MALFORMED_JSON) from error
        if len(encoded) > MAX_CONTROL_BYTES:
            raise ProtocolValidationError(StableCode.CONTROL_FRAME_TOO_LARGE)
        text = raw
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_constant,
        )
    except ProtocolValidationError:
        raise
    except (json.JSONDecodeError, ValueError, RecursionError) as error:
        raise ProtocolValidationError(StableCode.MALFORMED_JSON) from error
    if not isinstance(value, dict):
        raise ProtocolValidationError(StableCode.SCHEMA_INVALID)
    return value


def canonical_json(value: Any) -> bytes:
    """Return RFC 8785 bytes for an already validated JSON value."""
    try:
        return rfc8785.dumps(value)
    except (rfc8785.CanonicalizationError, UnicodeEncodeError, ValueError) as error:
        raise ProtocolValidationError(StableCode.SCHEMA_INVALID) from error


def canonical_digest(value: Any) -> bytes:
    return hashlib.sha256(canonical_json(value)).digest()


def _precheck_version(value: dict[str, Any], allowed_protocols: frozenset[str] | None) -> None:
    if allowed_protocols is None and "protocol" not in value:
        return
    protocol = value.get("protocol")
    if allowed_protocols is not None and protocol not in allowed_protocols:
        raise ProtocolValidationError(StableCode.UNKNOWN_MAJOR)
    if value.get("protocol_minor") != 0:
        raise ProtocolValidationError(StableCode.UNSUPPORTED_MINOR)


def _validation_code(error: ValidationError) -> StableCode:
    errors = error.errors(include_url=False, include_context=False, include_input=False)
    if any(item["type"] == "extra_forbidden" for item in errors):
        return StableCode.UNKNOWN_FIELD
    if any(item.get("loc", ())[:1] == ("capabilities",) for item in errors):
        return StableCode.CAPABILITY_REQUIRED
    return StableCode.SCHEMA_INVALID


def validate_object[ModelT: StrictModel](value: dict[str, Any], model: type[ModelT]) -> ModelT:
    allowed: set[str] = set()
    protocol_annotation = model.model_fields.get("protocol")
    if protocol_annotation is not None:
        annotation_text = str(protocol_annotation.annotation)
        if WORKER_PROTOCOL in annotation_text:
            allowed.add(WORKER_PROTOCOL)
        if VIEWER_PROTOCOL in annotation_text:
            allowed.add(VIEWER_PROTOCOL)
    _precheck_version(value, frozenset(allowed) if protocol_annotation is not None else None)
    try:
        return model.model_validate(value)
    except ValidationError as error:
        raise ProtocolValidationError(_validation_code(error)) from error


def parse_control[ModelT: StrictModel](
    raw: str | bytes, model: type[ModelT]
) -> tuple[ModelT, dict[str, Any]]:
    value = strict_json_loads(raw)
    return validate_object(value, model), value


def validate_named(raw: str | bytes, model_name: str) -> tuple[StrictModel, dict[str, Any]]:
    try:
        model = MODEL_BY_NAME[model_name]
    except KeyError as error:
        raise ProtocolValidationError(StableCode.SCHEMA_INVALID) from error
    return parse_control(raw, model)


def decision_for(action: Callable[[], Any]) -> StableCode:
    """Convert a validation action to one stable acceptance/rejection code."""
    try:
        action()
    except ProtocolValidationError as error:
        return error.code
    return StableCode.ACCEPTED
