"""Explicitly constructed infrastructure; importing this module has no I/O effects."""

from datetime import UTC, datetime


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)
