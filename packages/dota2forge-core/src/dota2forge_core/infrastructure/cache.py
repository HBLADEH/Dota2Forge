"""Bounded async caches with explicit ownership and expiry semantics."""

import asyncio
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, TypeVar

from ..domain.errors import CacheError, ValidationError

T = TypeVar("T")


class CacheCodec(Protocol[T]):
    def encode(self, value: T) -> bytes: ...

    def decode(self, payload: bytes) -> T: ...


class _Entry[T]:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: T, expires_at: float) -> None:
        self.value = value
        self.expires_at = expires_at


class MemoryCache[T]:
    """A process-local TTL cache; it stores successful values only by convention."""

    def __init__(
        self,
        *,
        capacity: int = 256,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if type(capacity) is not int or capacity < 1:
            raise ValidationError("Cache capacity must be a positive integer")
        self._capacity = capacity
        self._clock = clock
        self._entries: dict[str, _Entry[T]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> T | None:
        self._validate_key(key)
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= self._clock():
                del self._entries[key]
                return None
            return entry.value

    async def set(self, key: str, value: T, ttl_seconds: float) -> None:
        self._validate_key(key)
        ttl = _ttl(ttl_seconds)
        async with self._lock:
            self._purge_expired()
            self._entries.pop(key, None)
            if len(self._entries) >= self._capacity:
                del self._entries[next(iter(self._entries))]
            self._entries[key] = _Entry(value, self._clock() + ttl)

    async def delete(self, key: str) -> None:
        self._validate_key(key)
        async with self._lock:
            self._entries.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._entries.clear()

    async def size(self) -> int:
        async with self._lock:
            self._purge_expired()
            return len(self._entries)

    def _purge_expired(self) -> None:
        now = self._clock()
        self._entries = {
            key: entry for key, entry in self._entries.items() if entry.expires_at > now
        }

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str) or not key or len(key) > 512:
            raise ValidationError("Cache keys must be nonempty strings up to 512 characters")


class SQLiteCache[T]:
    """A caller-codec SQLite cache; initialization and closing are explicit."""

    def __init__(
        self,
        path: Path,
        codec: CacheCodec[T],
        *,
        clock: Callable[[], float] = time.time,
        capacity: int = 2048,
    ) -> None:
        if (
            not isinstance(path, Path)
            or not hasattr(codec, "encode")
            or not hasattr(codec, "decode")
        ):
            raise ValidationError("SQLite cache requires a path and codec")
        if type(capacity) is not int or capacity < 1:
            raise ValidationError("Cache capacity must be a positive integer")
        self._path = path
        self._codec = codec
        self._clock = clock
        self._capacity = capacity
        self._init_lock = asyncio.Lock()
        self._initialized = False
        self._closed = False

    async def initialize(self) -> None:
        async with self._init_lock:
            if self._closed:
                raise CacheError()
            if self._initialized:
                return
            try:
                await asyncio.to_thread(self._initialize_sync)
            except (OSError, sqlite3.Error):
                raise CacheError() from None
            self._initialized = True

    async def close(self) -> None:
        async with self._init_lock:
            self._closed = True
            self._initialized = False

    async def get(self, key: str) -> T | None:
        self._validate_key(key)
        await self.initialize()
        try:
            payload = await asyncio.to_thread(self._get_sync, key)
            if payload is None:
                return None
            try:
                return self._codec.decode(payload)
            except Exception:
                raise CacheError() from None
        except CacheError:
            raise
        except (OSError, sqlite3.Error):
            raise CacheError() from None

    async def set(self, key: str, value: T, ttl_seconds: float) -> None:
        self._validate_key(key)
        ttl = _ttl(ttl_seconds)
        await self.initialize()
        try:
            payload = self._codec.encode(value)
            if not isinstance(payload, bytes):
                raise CacheError()
            await asyncio.to_thread(self._set_sync, key, payload, self._clock() + ttl)
        except CacheError:
            raise
        except (OSError, sqlite3.Error):
            raise CacheError() from None
        except Exception:
            raise CacheError() from None

    async def delete(self, key: str) -> None:
        self._validate_key(key)
        await self.initialize()
        try:
            await asyncio.to_thread(self._delete_sync, key)
        except (OSError, sqlite3.Error):
            raise CacheError() from None

    async def clear(self) -> None:
        await self.initialize()
        try:
            await asyncio.to_thread(self._clear_sync)
        except (OSError, sqlite3.Error):
            raise CacheError() from None

    def _initialize_sync(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._path) as connection:
            application_id = int(connection.execute("PRAGMA application_id").fetchone()[0])
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if application_id not in (0, 0xD2A2F0C):
                raise sqlite3.DatabaseError("foreign database")
            if version not in (0, 1):
                raise sqlite3.DatabaseError("unsupported cache version")
            connection.execute("PRAGMA application_id = 0xD2A2F0C")
            connection.execute("PRAGMA user_version = 1")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS cache_entries ("
                "cache_key TEXT PRIMARY KEY, expires_at REAL NOT NULL, payload BLOB NOT NULL)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS cache_entries_expiry ON cache_entries(expires_at)"
            )

    def _get_sync(self, key: str) -> bytes | None:
        now = self._clock()
        with sqlite3.connect(self._path) as connection:
            connection.execute("DELETE FROM cache_entries WHERE expires_at <= ?", (now,))
            row = connection.execute(
                "SELECT payload FROM cache_entries WHERE cache_key = ? AND expires_at > ?",
                (key, now),
            ).fetchone()
            return None if row is None else bytes(row[0])

    def _set_sync(self, key: str, payload: bytes, expires_at: float) -> None:
        now = self._clock()
        with sqlite3.connect(self._path) as connection:
            connection.execute("DELETE FROM cache_entries WHERE expires_at <= ?", (now,))
            connection.execute(
                "INSERT INTO cache_entries(cache_key, expires_at, payload) VALUES (?, ?, ?) "
                "ON CONFLICT(cache_key) DO UPDATE SET expires_at=excluded.expires_at, "
                "payload=excluded.payload",
                (key, expires_at, payload),
            )
            keys = connection.execute(
                "SELECT cache_key FROM cache_entries ORDER BY expires_at ASC, cache_key ASC"
            ).fetchall()
            for (old_key,) in keys[: -self._capacity]:
                connection.execute("DELETE FROM cache_entries WHERE cache_key = ?", (old_key,))

    def _delete_sync(self, key: str) -> None:
        with sqlite3.connect(self._path) as connection:
            connection.execute("DELETE FROM cache_entries WHERE cache_key = ?", (key,))

    def _clear_sync(self) -> None:
        with sqlite3.connect(self._path) as connection:
            connection.execute("DELETE FROM cache_entries")

    @staticmethod
    def _validate_key(key: str) -> None:
        MemoryCache._validate_key(key)


def _ttl(value: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or value <= 0
        or value != value
        or value == float("inf")
    ):
        raise ValidationError("Cache TTL must be a finite positive number")
    return float(value)
