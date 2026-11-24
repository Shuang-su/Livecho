"""Injectable UTC timestamps in the protocol's millisecond form."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_millis(value: datetime) -> datetime:
    """Truncate an instant to UTC milliseconds."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    utc = value.astimezone(UTC)
    return utc.replace(microsecond=(utc.microsecond // 1000) * 1000)


def format_timestamp(value: datetime) -> str:
    """Format an instant as ``YYYY-MM-DDTHH:MM:SS.mmmZ``."""
    utc = utc_millis(value)
    return (
        f"{utc.year:04d}-{utc.month:02d}-{utc.day:02d}T"
        f"{utc.hour:02d}:{utc.minute:02d}:{utc.second:02d}."
        f"{utc.microsecond // 1000:03d}Z"
    )
