"""Fixed metadata codec for ephemeral in-memory PCM messages."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from uuid import UUID

from .errors import Decision, ProtocolValidationError, StableCode
from .state import PcmSequenceWindow

MAGIC = b"LPCM"
PROTOCOL_MAJOR = 1
PROTOCOL_MINOR = 0
HEADER_LENGTH = 56
END_OF_SEGMENT = 0x01
MAX_SAMPLE_COUNT = 16_000
MAX_PAYLOAD_LENGTH = 32_000
MAX_FRAME_LENGTH = HEADER_LENGTH + MAX_PAYLOAD_LENGTH
LEASE_AUDIO_BUDGET = 960_000
PROCESS_AUDIO_BUDGET = 16_777_216
_HEADER = struct.Struct("!4sBBBB16sQQQII")


@dataclass(frozen=True, slots=True)
class PcmHeaderV1:
    lease_id: str
    epoch: int
    seq: int
    pts_ms: int
    sample_count: int
    payload_length: int
    end_of_segment: bool = False


def _valid_header(header: PcmHeaderV1) -> bool:
    try:
        lease = UUID(header.lease_id)
    except ValueError:
        return False
    return (
        str(lease) == header.lease_id
        and header.epoch >= 1
        and 0 <= header.seq <= 18_446_744_073_709_551_615
        and 0 <= header.pts_ms <= 18_446_744_073_709_551_615
        and 1 <= header.sample_count <= MAX_SAMPLE_COUNT
        and 2 <= header.payload_length <= MAX_PAYLOAD_LENGTH
        and header.payload_length == header.sample_count * 2
    )


def encode_header(header: PcmHeaderV1) -> bytes:
    """Encode only the 56-byte metadata header, never an audio payload."""
    if not _valid_header(header):
        raise ProtocolValidationError(StableCode.BINARY_HEADER_INVALID)
    flags = END_OF_SEGMENT if header.end_of_segment else 0
    return _HEADER.pack(
        MAGIC,
        PROTOCOL_MAJOR,
        PROTOCOL_MINOR,
        flags,
        HEADER_LENGTH,
        UUID(header.lease_id).bytes,
        header.epoch,
        header.seq,
        header.pts_ms,
        header.sample_count,
        header.payload_length,
    )


def decode_header(frame: bytes | bytearray | memoryview) -> PcmHeaderV1:
    """Validate frame structure and return metadata without copying or reading payload values."""
    view = memoryview(frame)
    if len(view) > MAX_FRAME_LENGTH:
        raise ProtocolValidationError(StableCode.BINARY_FRAME_TOO_LARGE)
    if len(view) < HEADER_LENGTH:
        raise ProtocolValidationError(StableCode.BINARY_HEADER_INVALID)
    (
        magic,
        major,
        minor,
        flags,
        header_length,
        lease_bytes,
        epoch,
        seq,
        pts_ms,
        sample_count,
        payload_length,
    ) = _HEADER.unpack(view[:HEADER_LENGTH])
    if (
        magic != MAGIC
        or major != PROTOCOL_MAJOR
        or minor != PROTOCOL_MINOR
        or flags & ~END_OF_SEGMENT
        or header_length != HEADER_LENGTH
        or len(view) != HEADER_LENGTH + payload_length
    ):
        raise ProtocolValidationError(StableCode.BINARY_HEADER_INVALID)
    header = PcmHeaderV1(
        lease_id=str(UUID(bytes=bytes(lease_bytes))),
        epoch=epoch,
        seq=seq,
        pts_ms=pts_ms,
        sample_count=sample_count,
        payload_length=payload_length,
        end_of_segment=bool(flags & END_OF_SEGMENT),
    )
    if not _valid_header(header):
        raise ProtocolValidationError(StableCode.BINARY_HEADER_INVALID)
    return header


class PcmLeaseState:
    """No-retention PCM ordering, PTS, and aggregate budget state."""

    def __init__(
        self,
        *,
        lease_id: str,
        epoch: int,
        input_start_seq: int,
        lease_budget: int = LEASE_AUDIO_BUDGET,
    ) -> None:
        self.lease_id = lease_id
        self.epoch = epoch
        self.sequence = PcmSequenceWindow(input_start_seq)
        self.lease_budget = lease_budget
        self.buffered_bytes = 0
        self.last_pts_ms: int | None = None
        self.closed = False

    def accept(
        self,
        frame: bytes | bytearray | memoryview,
        *,
        session_buffered_bytes: int = 0,
        process_buffered_bytes: int = 0,
    ) -> Decision:
        if self.closed:
            return Decision(StableCode.LEASE_CLOSED)
        try:
            header = decode_header(frame)
        except ProtocolValidationError as error:
            return Decision(error.code)
        if header.lease_id != self.lease_id:
            return Decision(StableCode.BINDING_MISMATCH)
        if header.epoch < self.epoch:
            return Decision(StableCode.EPOCH_STALE)
        if header.epoch > self.epoch:
            return Decision(StableCode.EPOCH_UNKNOWN)
        sequence = self.sequence.preview(header.seq)
        if sequence.code != StableCode.ACCEPTED:
            return sequence
        if self.last_pts_ms is not None and header.pts_ms < self.last_pts_ms:
            return Decision(StableCode.AUDIO_PTS_INVALID)
        if (
            self.buffered_bytes + header.payload_length > self.lease_budget
            or session_buffered_bytes + header.payload_length > LEASE_AUDIO_BUDGET
            or process_buffered_bytes + header.payload_length > PROCESS_AUDIO_BUDGET
        ):
            return Decision(StableCode.AUDIO_BUDGET_EXCEEDED)
        self.sequence.commit(header.seq)
        self.buffered_bytes += header.payload_length
        self.last_pts_ms = header.pts_ms
        if header.end_of_segment:
            self.buffered_bytes = 0
        return Decision(StableCode.ACCEPTED)

    def consume(self, byte_count: int) -> None:
        if byte_count < 0 or byte_count > self.buffered_bytes:
            raise ValueError("invalid consumed byte count")
        self.buffered_bytes -= byte_count

    def clear(self) -> None:
        self.buffered_bytes = 0
        self.last_pts_ms = None
        self.sequence.clear()
        self.closed = True
