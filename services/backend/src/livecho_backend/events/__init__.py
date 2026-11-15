"""Issue #10 internal offline event normalization (fixture path only).

No Timeline/WS publication, protocol edits, live chat, or raw archive.
"""

from .gates import FLAGS, attempt_archive, attempt_live_adapter, attempt_wire_publish
from .normalize import NormalizeEngine, NormalizeResult

__all__ = [
    "FLAGS",
    "NormalizeEngine",
    "NormalizeResult",
    "attempt_archive",
    "attempt_live_adapter",
    "attempt_wire_publish",
]
