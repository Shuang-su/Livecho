"""Issue #7 Bilibili public-room ingest (fixture/contract path).

Real acquisition, channel selection, and production enablement stay closed.
"""

from .gates import blocked_reasons, real_acquisition_allowed
from .session import IngestSession, RoomState

__all__ = [
    "IngestSession",
    "RoomState",
    "blocked_reasons",
    "real_acquisition_allowed",
]
