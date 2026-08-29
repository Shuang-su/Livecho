from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

MESSAGE_ID = "00000000-0000-4000-8000-000000000001"
MESSAGE_ID_2 = "00000000-0000-4000-8000-000000000002"
WORKER_ID = "00000000-0000-4000-8000-000000000010"
CONNECTION_ID = "00000000-0000-4000-8000-000000000011"
LEASE_ID = "00000000-0000-4000-8000-000000000020"
SESSION_ID = "00000000-0000-4000-8000-000000000030"
SEGMENT_ID = "00000000-0000-4000-8000-000000000040"
STATS_ID = "00000000-0000-4000-8000-000000000050"
EVENT_ID = "00000000-0000-4000-8000-000000000060"
TIMESTAMP = "2026-01-01T00:00:00.000Z"
TIMESTAMP_1 = "2026-01-01T00:00:01.000Z"
MANIFEST = {
    "provider": "synthetic",
    "model_id": "fixture-asr",
    "revision": "1",
    "sha256": "a" * 64,
}


def worker_envelope(message_type: str, message_id: str = MESSAGE_ID) -> dict[str, Any]:
    return {
        "protocol": "livecho.worker.v1",
        "protocol_minor": 0,
        "message_id": message_id,
        "type": message_type,
        "sent_at": TIMESTAMP,
    }


def viewer_envelope(message_type: str, message_id: str = MESSAGE_ID) -> dict[str, Any]:
    return {
        "protocol": "livecho.viewer.v1",
        "protocol_minor": 0,
        "message_id": message_id,
        "type": message_type,
        "sent_at": TIMESTAMP,
    }


@pytest.fixture
def valid_messages() -> dict[str, dict[str, Any]]:
    worker_hello = {
        **worker_envelope("worker.hello"),
        "worker_id": WORKER_ID,
        "worker_version": "0.1.0",
        "supported_minors": [0],
        "capabilities": ["asr.transcribe", "protocol.binary-pcm"],
        "model_manifests": [deepcopy(MANIFEST)],
        "resume": None,
    }
    lease = {
        **worker_envelope("worker.lease"),
        "lease_id": LEASE_ID,
        "session_id": SESSION_ID,
        "room_id": "synthetic-room",
        "epoch": "1",
        "revision": "1",
        "issued_at": TIMESTAMP,
        "expires_at": "2026-01-01T00:02:00.000Z",
        "input_start_seq": "0",
        "output_start_seq": "0",
        "model_manifest": deepcopy(MANIFEST),
        "audio_format": {"encoding": "pcm_s16le", "sample_rate_hz": 16000, "channels": 1},
        "audio_origin": "synthetic",
    }
    heartbeat = {
        **worker_envelope("worker.heartbeat"),
        "lease_id": LEASE_ID,
        "session_id": SESSION_ID,
        "epoch": "1",
        "seq": "0",
        "state": "ready",
        "last_input_seq": None,
        "last_output_seq": None,
        "audio_buffer_bytes": 0,
        "observed_at": TIMESTAMP,
    }
    stats = {
        **worker_envelope("worker.stats"),
        "lease_id": LEASE_ID,
        "session_id": SESSION_ID,
        "stats_id": STATS_ID,
        "epoch": "1",
        "seq": "0",
        "revision": "1",
        "processed_audio_ms": "0",
        "segments_accepted": "0",
        "segments_rejected": "0",
        "realtime_factor": 1.0,
        "window_started_at": TIMESTAMP,
        "window_ended_at": TIMESTAMP_1,
    }
    transcript = {
        **worker_envelope("worker.transcript"),
        "lease_id": LEASE_ID,
        "session_id": SESSION_ID,
        "segment_id": SEGMENT_ID,
        "epoch": "1",
        "seq": "0",
        "revision": "1",
        "start_ms": 0,
        "end_ms": 1000,
        "text": "synthetic caption",
        "language": "en",
        "confidence": 0.9,
        "is_final": False,
    }
    timeline_transcript = {
        **viewer_envelope("viewer.timeline_event"),
        "event_id": EVENT_ID,
        "session_id": SESSION_ID,
        "room_id": "synthetic-room",
        "epoch": "1",
        "seq": "0",
        "revision": "1",
        "occurred_at": TIMESTAMP,
        "payload": {
            "segment_id": SEGMENT_ID,
            "start_ms": 0,
            "end_ms": 1000,
            "text": "synthetic caption",
            "language": "en",
            "confidence": 0.9,
            "is_final": False,
        },
    }
    timeline_status = deepcopy(timeline_transcript)
    timeline_status["payload"] = {"status": "live", "reason_code": None}
    viewer_subscribe = {
        **viewer_envelope("viewer.subscribe"),
        "client_version": "0.1.0",
        "supported_minors": [0],
        "room_id": "synthetic-room",
        "cursor": None,
    }
    return {
        "WorkerHelloV1": worker_hello,
        "LeaseV1": lease,
        "HeartbeatV1": heartbeat,
        "WorkerStatsV1": stats,
        "TranscriptSegmentV1": transcript,
        "TimelineEventV1": timeline_transcript,
        "TimelineEventStatusV1": timeline_status,
        "ViewerSubscribeV1": viewer_subscribe,
    }
