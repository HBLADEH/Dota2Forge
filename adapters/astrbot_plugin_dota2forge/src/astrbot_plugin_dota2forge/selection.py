"""Bounded interaction state for the last completely sent recent result."""

import time
from collections.abc import Callable
from dataclasses import dataclass

from dota2forge_core import PlatformIdentity, PlayerBinding, RecentMatches

type Session = tuple[str, str]
type Key = tuple[PlatformIdentity, Session]


class SelectionError(Exception):
    def __init__(self) -> None:
        super().__init__("No valid delivered AstrBot list")


@dataclass(frozen=True, repr=False)
class Selection:
    recent: RecentMatches
    binding: PlayerBinding | None
    written_at: float


class SelectionStore:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._entries: dict[Key, Selection] = {}

    def _expire(self) -> None:
        now = self._clock()
        self._entries = {
            key: value for key, value in self._entries.items() if now - value.written_at < 600
        }

    def remember(self, key: Key, recent: RecentMatches, binding: PlayerBinding | None) -> None:
        self._expire()
        self._entries.pop(key, None)
        if len(self._entries) >= 128:
            del self._entries[next(iter(self._entries))]
        self._entries[key] = Selection(recent, binding, self._clock())

    def get(self, key: Key | None, binding: PlayerBinding | None) -> RecentMatches:
        self._expire()
        entry = self._entries.get(key) if key is not None else None
        if entry is None or entry.binding != binding:
            if key is not None:
                self._entries.pop(key, None)
            raise SelectionError()
        return entry.recent

    def invalidate(self, identity: PlatformIdentity) -> None:
        self._entries = {key: value for key, value in self._entries.items() if key[0] != identity}

    def clear(self) -> None:
        self._entries.clear()
