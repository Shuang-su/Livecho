from __future__ import annotations

import json
from copy import deepcopy

import pytest
from livecho_protocol.compatibility import manifest_key, negotiate_viewer, negotiate_worker
from livecho_protocol.errors import ProtocolValidationError, StableCode
from livecho_protocol.models import (
    MODEL_BY_NAME,
    LeaseV1,
    ProtocolAckV1,
    TimelineEventV1,
    TranscriptSegmentV1,
    ViewerSubscribeV1,
    WorkerHelloV1,
    WorkerWelcomeV1,
)
from livecho_protocol.parser import canonical_json, parse_control, strict_json_loads
from pydantic import ValidationError

from tests.protocol.conftest import MANIFEST, MESSAGE_ID, worker_envelope


@pytest.mark.parametrize(
    "model_name",
    [
        "WorkerHelloV1",
        "LeaseV1",
        "HeartbeatV1",
        "WorkerStatsV1",
        "TranscriptSegmentV1",
    ],
)
def test_six_required_worker_models_are_strict(
    model_name: str, valid_messages: dict[str, dict[str, object]]
) -> None:
    model = MODEL_BY_NAME[model_name]
    value = model.model_validate(valid_messages[model_name])
    assert value.model_dump(mode="json") == valid_messages[model_name]


@pytest.mark.parametrize("case_name", ["TimelineEventV1", "TimelineEventStatusV1"])
def test_both_timeline_payloads_are_closed(
    case_name: str, valid_messages: dict[str, dict[str, object]]
) -> None:
    TimelineEventV1.model_validate(valid_messages[case_name])
    changed = deepcopy(valid_messages[case_name])
    assert isinstance(changed["payload"], dict)
    changed["payload"]["raw"] = "forbidden"
    with pytest.raises(ValidationError):
        TimelineEventV1.model_validate(changed)


def test_timeline_known_value_error_is_schema_invalid(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    changed = deepcopy(valid_messages["TimelineEventV1"])
    assert isinstance(changed["payload"], dict)
    changed["payload"]["text"] = ""
    with pytest.raises(ProtocolValidationError) as invalid:
        parse_control(json.dumps(changed), TimelineEventV1)
    assert invalid.value.code == StableCode.SCHEMA_INVALID


def test_unknown_fields_and_non_nfc_fail_closed(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    transcript = deepcopy(valid_messages["TranscriptSegmentV1"])
    transcript["command"] = "forbidden"
    with pytest.raises(ValidationError):
        TranscriptSegmentV1.model_validate(transcript)
    transcript.pop("command")
    transcript["text"] = "e\u0301"
    with pytest.raises(ValidationError):
        TranscriptSegmentV1.model_validate(transcript)


@pytest.mark.parametrize(
    ("start", "end"),
    [(1000, 1000), (1000, 999), (0, 30001)],
)
def test_transcript_time_range_is_bounded(
    start: int, end: int, valid_messages: dict[str, dict[str, object]]
) -> None:
    transcript = deepcopy(valid_messages["TranscriptSegmentV1"])
    transcript["start_ms"] = start
    transcript["end_ms"] = end
    with pytest.raises(ValidationError):
        TranscriptSegmentV1.model_validate(transcript)


def test_lease_lifetime_is_at_most_120_seconds(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    LeaseV1.model_validate(valid_messages["LeaseV1"])
    lease = deepcopy(valid_messages["LeaseV1"])
    lease["expires_at"] = "2026-01-01T00:02:00.001Z"
    with pytest.raises(ValidationError):
        LeaseV1.model_validate(lease)


def test_parser_rejects_duplicate_keys_unknown_fields_and_oversize(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    with pytest.raises(ProtocolValidationError) as duplicate:
        strict_json_loads('{"protocol":1,"protocol":2}')
    assert duplicate.value.code == StableCode.DUPLICATE_KEY

    hello = deepcopy(valid_messages["WorkerHelloV1"])
    hello["unknown"] = True
    with pytest.raises(ProtocolValidationError) as unknown:
        parse_control(json.dumps(hello), WorkerHelloV1)
    assert unknown.value.code == StableCode.UNKNOWN_FIELD

    with pytest.raises(ProtocolValidationError) as large:
        strict_json_loads("{" + " " * 65_536 + "}")
    assert large.value.code == StableCode.CONTROL_FRAME_TOO_LARGE


def test_parser_classifies_version_before_schema(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    hello = deepcopy(valid_messages["WorkerHelloV1"])
    hello["protocol"] = "livecho.worker.v2"
    with pytest.raises(ProtocolValidationError) as major:
        parse_control(json.dumps(hello), WorkerHelloV1)
    assert major.value.code == StableCode.UNKNOWN_MAJOR
    hello["protocol"] = "livecho.worker.v1"
    hello["protocol_minor"] = 1
    with pytest.raises(ProtocolValidationError) as minor:
        parse_control(json.dumps(hello), WorkerHelloV1)
    assert minor.value.code == StableCode.UNSUPPORTED_MINOR


def test_rfc8785_normalizes_representation_variants() -> None:
    first = strict_json_loads('{"b":1.0,"a":"synthetic"}')
    second = strict_json_loads('{"a":"synthetic","b":1e0}')
    assert canonical_json(first) == canonical_json(second)
    assert canonical_json(first) != canonical_json({"a": "synthetic", "b": None})


def test_worker_and_viewer_negotiation(valid_messages: dict[str, dict[str, object]]) -> None:
    hello = WorkerHelloV1.model_validate(valid_messages["WorkerHelloV1"])
    allowlist = frozenset({manifest_key(hello.model_manifests[0])})
    assert negotiate_worker(hello, allowlist).decision.code == StableCode.ACCEPTED
    assert negotiate_worker(hello, frozenset()).decision.code == StableCode.MANIFEST_NOT_ALLOWED

    old = {**valid_messages["WorkerHelloV1"], "worker_version": "0.1.0-rc.1"}
    old_hello = WorkerHelloV1.model_validate(old)
    assert negotiate_worker(old_hello, allowlist).decision.code == StableCode.WORKER_VERSION_TOO_OLD

    viewer = ViewerSubscribeV1.model_validate(valid_messages["ViewerSubscribeV1"])
    assert negotiate_viewer(viewer).selected_minor == 0


def test_manifest_shape_has_no_locator_or_execution_surface() -> None:
    hello = {
        **worker_envelope("worker.hello", MESSAGE_ID),
        "worker_id": "00000000-0000-4000-8000-000000000010",
        "worker_version": "0.1.0",
        "supported_minors": [0],
        "capabilities": ["asr.transcribe", "protocol.binary-pcm"],
        "model_manifests": [{**MANIFEST, "url": "forbidden"}],
        "resume": None,
    }
    with pytest.raises(ValidationError):
        WorkerHelloV1.model_validate(hello)


def test_handshake_collections_are_unique(
    valid_messages: dict[str, dict[str, object]],
) -> None:
    hello = deepcopy(valid_messages["WorkerHelloV1"])
    hello["supported_minors"] = [0, 0]
    with pytest.raises(ValidationError):
        WorkerHelloV1.model_validate(hello)

    welcome = {
        **worker_envelope("worker.welcome"),
        "connection_id": "00000000-0000-4000-8000-000000000011",
        "selected_minor": 0,
        "minimum_worker_version": "0.1.0",
        "resume_succeeded": False,
        "accepted_capabilities": ["asr.transcribe", "asr.transcribe"],
        "accepted_manifests": [],
    }
    with pytest.raises(ValidationError):
        WorkerWelcomeV1.model_validate(welcome)


@pytest.mark.parametrize(
    ("outcome", "seq", "revision", "expected_revision", "valid"),
    [
        ("accepted", "0", None, None, True),
        ("accepted", None, "1", None, True),
        ("accepted", None, None, "1", True),
        ("accepted", None, None, None, False),
        ("seq_duplicate", "0", None, None, True),
        ("seq_duplicate", None, "1", None, False),
        ("seq_duplicate", "0", None, "1", False),
        ("revision_duplicate", None, "1", None, True),
        ("revision_duplicate", "0", "1", None, True),
        ("revision_duplicate", "0", None, None, False),
        ("cancel_duplicate", None, None, "1", True),
        ("cancel_duplicate", "0", None, None, False),
    ],
)
def test_ack_position_is_outcome_specific(
    outcome: str,
    seq: str | None,
    revision: str | None,
    expected_revision: str | None,
    valid: bool,
) -> None:
    ack = {
        **worker_envelope("protocol.ack"),
        "outcome": outcome,
        "acknowledged_message_id": MESSAGE_ID,
        "seq": seq,
        "revision": revision,
        "expected_revision": expected_revision,
    }
    if valid:
        ProtocolAckV1.model_validate(ack)
    else:
        with pytest.raises(ValidationError):
            ProtocolAckV1.model_validate(ack)
