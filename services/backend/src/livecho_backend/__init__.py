"""Livecho backend packages.

Eager imports are avoided so gated modules (e.g. ``audio.preflight``) can load
without pulling unrelated runtime dependencies such as protocol negotiation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from livecho_backend.local_vertical import (
        LocalVerticalConfig,
        LocalVerticalService,
        ModeBlockedError,
        create_local_vertical_app,
    )

__all__ = [
    "LocalVerticalConfig",
    "LocalVerticalService",
    "ModeBlockedError",
    "create_local_vertical_app",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from livecho_backend import local_vertical as package

        return getattr(package, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
