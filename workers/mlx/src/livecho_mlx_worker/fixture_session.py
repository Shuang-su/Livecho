"""In-memory fixture transcription. Not speech recognition; no audio or MLX."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from livecho_protocol.errors import StableCode
from livecho_protocol.models import TranscriptSegmentV1
from livecho_protocol.state import StreamOrderingState

from .lifecycle import Lifecycle, State


def _ts() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


@dataclass
class FixtureBinding:
    lease_id: str
    session_id: str
    epoch: str
    output_start_seq: int
    start_ms: int = 0
    end_ms: int = 1000


@dataclass
class FixtureSession:
    """One-owner fixture path: legal partial then final against protocol ordering."""

    binding: FixtureBinding
    lifecycle: Lifecycle = field(default_factory=Lifecycle)
    cancelled: bool = False
    _stream: StreamOrderingState | None = None
    _segment_id: str | None = None
    _next_seq: int = 0
    _published: list[dict[str, Any]] = field(default_factory=list)
    _audio_held: bool = False
    label: Literal["fixture_not_speech_recognition"] = "fixture_not_speech_recognition"

    def start(self) -> None:
        self.lifecycle.transition(State.CONNECTING)
        self.lifecycle.transition(State.READY)
        self.lifecycle.open_admission()
        self._stream = StreamOrderingState(
            session_id=self.binding.session_id,
            lease_id=self.binding.lease_id,
            epoch=int(self.binding.epoch),
            start_seq=self.binding.output_start_seq,
        )
        self._next_seq = self.binding.output_start_seq
        self._segment_id = str(uuid4())
        self._audio_held = True

    def cancel(self) -> None:
        self.cancelled = True
        self.lifecycle.close_admission()
        self._release_audio()
        if self.lifecycle.state not in {State.STOPPING, State.STOPPED, State.FAILED}:
            self.lifecycle.transition(State.STOPPING)
            self.lifecycle.transition(State.STOPPED)
        if self._stream is not None:
            self._stream.clear()

    def _release_audio(self) -> None:
        # Fixture never allocates PCM; the flag models ownership for terminal gates.
        self._audio_held = False

    def _message(
        self,
        *,
        revision: str,
        text: str,
        is_final: bool,
        seq: int | None = None,
    ) -> dict[str, Any]:
        assert self._segment_id is not None
        payload = {
            "protocol": "livecho.worker.v1",
            "protocol_minor": 0,
            "message_id": str(uuid4()),
            "type": "worker.transcript",
            "sent_at": _ts(),
            "lease_id": self.binding.lease_id,
            "session_id": self.binding.session_id,
            "segment_id": self._segment_id,
            "epoch": self.binding.epoch,
            "seq": str(self._next_seq if seq is None else seq),
            "revision": revision,
            "start_ms": self.binding.start_ms,
            "end_ms": self.binding.end_ms,
            "text": text,
            "language": None,
            "confidence": None,
            "is_final": is_final,
        }
        # Validate against the authoritative model before ordering.
        TranscriptSegmentV1.model_validate(payload)
        return payload

    def emit_partial_then_final(
        self,
        *,
        partial_text: str = "fixture partial…",
        final_text: str = "fixture partial complete",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if self.cancelled or not self.lifecycle.admission_open or self._stream is None:
            raise RuntimeError("admission_closed")
        if self._audio_held is False:
            raise RuntimeError("audio_already_released")
        self.lifecycle.transition(State.RECEIVING)
        self.lifecycle.transition(State.TRANSCRIBING)

        partial = self._message(revision="1", text=partial_text, is_final=False)
        decision = self._stream.accept(partial)
        if decision.code != StableCode.ACCEPTED:
            raise RuntimeError(f"protocol:{decision.code}")
        self._published.append(partial)
        self._next_seq += 1

        final = self._message(revision="2", text=final_text, is_final=True)
        # Terminal ownership gate: release fixture audio before commit/ack.
        self._release_audio()
        if self.cancelled:
            raise RuntimeError("cancelled_before_commit")
        decision = self._stream.accept(final)
        if decision.code != StableCode.ACCEPTED:
            raise RuntimeError(f"protocol:{decision.code}")
        self._published.append(final)
        self._next_seq += 1
        self.lifecycle.transition(State.READY)
        return partial, final

    def reject_stale_revision(self, text: str = "tampered") -> StableCode:
        if self._stream is None or self._segment_id is None:
            raise RuntimeError("not_started")
        stale = self._message(
            revision="1",
            text=text,
            is_final=False,
            seq=self._next_seq,
        )
        return self._stream.accept(stale).code

    def reject_after_final(self, text: str = "late change") -> StableCode:
        if self._stream is None:
            raise RuntimeError("not_started")
        late = self._message(
            revision="3",
            text=text,
            is_final=True,
            seq=self._next_seq,
        )
        return self._stream.accept(late).code

    @property
    def published(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._published)

    @property
    def audio_held(self) -> bool:
        return self._audio_held
