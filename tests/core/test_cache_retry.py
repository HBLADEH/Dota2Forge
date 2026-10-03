"""Synthetic cache and retry checks; no provider network or real identity is used."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from dota2forge_core import (
    AccountId,
    CacheError,
    DataMetadata,
    DataSource,
    MatchDetailUnavailable,
    MatchId,
    MatchSummary,
    PlayerProfile,
    ProviderError,
    ProviderErrorCode,
    RecentMatches,
    ValidationError,
)
from dota2forge_core.infrastructure.cache import MemoryCache, SQLiteCache
from dota2forge_core.infrastructure.resilience import CachedProvider, RetryingProvider, RetryPolicy

ACCOUNT = AccountId(123)
MATCH = MatchId(1001)


@dataclass
class JsonCodec:
    def encode(self, value):
        return json.dumps(value, sort_keys=True).encode()

    def decode(self, payload):
        return json.loads(payload)


class Source:
    def __init__(self, source=DataSource.STRATZ, clock=None):
        self.source = source
        self.clock = clock or (lambda: datetime(2026, 10, 2, tzinfo=UTC))
        self.calls = []
        self.failures = []
        self.rank = 51

    def _metadata(self):
        return DataMetadata(self.source, self.clock())

    async def get_player(self, account_id):
        self.calls.append(("player", account_id))
        if self.failures:
            raise self.failures.pop(0)
        metadata = self._metadata()
        return PlayerProfile(account_id, metadata, "Cached", self.rank)

    async def get_recent_matches(self, account_id, limit):
        self.calls.append(("recent", account_id, limit))
        if self.failures:
            raise self.failures.pop(0)
        metadata = self._metadata()
        row = MatchSummary(1001, account_id, metadata.fetched_at, metadata, kills=0)
        return RecentMatches(account_id, (row,), metadata)

    async def get_match_detail(self, match_id):
        self.calls.append(("detail", match_id))
        if self.failures:
            raise self.failures.pop(0)
        return MatchDetailUnavailable(match_id, self._metadata())


def test_memory_cache_ttl_capacity_and_input_boundaries(run_async):
    now = [0.0]

    async def check():
        cache = MemoryCache[int](capacity=1, clock=lambda: now[0])
        await cache.set("a", 1, 5)
        assert await cache.get("a") == 1 and await cache.size() == 1
        await cache.set("b", 2, 5)
        assert await cache.get("a") is None and await cache.get("b") == 2
        now[0] = 5
        assert await cache.get("b") is None and await cache.size() == 0
        with pytest.raises(ValidationError):
            await cache.set("bad", 1, 0)
        with pytest.raises(ValidationError):
            await cache.get("")
        with pytest.raises(ValidationError):
            MemoryCache(capacity=0)

    run_async(check())


def test_sqlite_cache_initializes_persists_expires_and_rejects_foreign_database(
    tmp_path, run_async
):
    now = [0.0]

    async def check():
        path = tmp_path / "cache.sqlite3"
        first = SQLiteCache(path, JsonCodec(), clock=lambda: now[0], capacity=2)
        await first.set("a", {"value": 1}, 5)
        assert await first.get("a") == {"value": 1}
        await first.set("b", {"value": 2}, 5)
        await first.set("c", {"value": 3}, 5)
        assert await first.get("a") is None
        await first.close()
        second = SQLiteCache(path, JsonCodec(), clock=lambda: now[0], capacity=2)
        assert await second.get("b") == {"value": 2}
        now[0] = 5
        assert await second.get("b") is None
        await second.clear()
        await second.close()
        with pytest.raises(CacheError):
            await second.get("b")

        foreign = tmp_path / "foreign.sqlite3"
        import sqlite3

        with sqlite3.connect(foreign) as connection:
            connection.execute("PRAGMA application_id = 99")
        with pytest.raises(CacheError):
            await SQLiteCache(foreign, JsonCodec()).initialize()

    run_async(check())


def test_cached_provider_ttl_refresh_invalidation_and_source_keys(run_async):
    now = [0.0]

    async def check():
        cache = MemoryCache(capacity=20, clock=lambda: now[0])
        left = Source(DataSource.STRATZ)
        right = Source(DataSource.OPENDOTA)
        cached_left = CachedProvider(left, cache, ttl_seconds=5)
        cached_right = CachedProvider(right, cache, ttl_seconds=5)
        assert (await cached_left.get_player(ACCOUNT)).rank_tier == 51
        assert (await cached_left.get_player(ACCOUNT)).rank_tier == 51
        assert len(left.calls) == 1
        left.rank = 52
        assert (await cached_left.refresh_player(ACCOUNT)).rank_tier == 52
        assert len(left.calls) == 2
        await cached_left.invalidate_account(ACCOUNT)
        assert (await cached_left.get_player(ACCOUNT)).rank_tier == 52
        assert len(left.calls) == 3
        assert (await cached_right.get_player(ACCOUNT)).metadata.source is DataSource.OPENDOTA
        assert len(right.calls) == 1
        now[0] = 5
        assert (await cached_left.get_player(ACCOUNT)).rank_tier == 52
        assert len(left.calls) == 4
        await cached_left.invalidate_match(MATCH)
        assert isinstance(await cached_left.get_match_detail(MATCH), MatchDetailUnavailable)
        assert len(left.calls) == 5

    run_async(check())


def test_cached_provider_keeps_previous_value_when_refresh_fails_and_rejects_bad_cache(
    run_async,
):
    async def check():
        cache = MemoryCache()
        source = Source()
        cached = CachedProvider(source, cache)
        original = await cached.get_player(ACCOUNT)
        source.failures.append(ProviderError(ProviderErrorCode.UNAVAILABLE, source.source))
        with pytest.raises(ProviderError):
            await cached.refresh_player(ACCOUNT)
        assert await cached.get_player(ACCOUNT) == original
        await cache.set(cached._key("player", ACCOUNT.value), "wrong", 300)
        with pytest.raises(ProviderError) as error:
            await cached.get_player(ACCOUNT)
        assert error.value.code is ProviderErrorCode.INVALID_RESPONSE

    run_async(check())


@pytest.mark.parametrize(
    "code",
    [
        ProviderErrorCode.RATE_LIMITED,
        ProviderErrorCode.AUTHENTICATION,
        ProviderErrorCode.PRIVATE,
        ProviderErrorCode.INVALID_RESPONSE,
    ],
)
def test_retry_only_transient_errors_and_preserves_cancellation(run_async, code):
    async def check():
        source = Source()
        source.failures = [ProviderError(code, source.source)]
        sleeps = []

        async def sleep(seconds):
            sleeps.append(seconds)

        retrying = RetryingProvider(
            source,
            RetryPolicy(max_attempts=3, initial_delay_seconds=0.5, max_delay_seconds=1),
            sleep=sleep,
        )
        with pytest.raises(ProviderError):
            await retrying.get_player(ACCOUNT)
        assert len(source.calls) == 1 and sleeps == []

    run_async(check())


def test_retry_backoff_then_success_and_no_program_error_swallow(run_async):
    async def check():
        source = Source()
        source.failures = [
            ProviderError(ProviderErrorCode.TIMEOUT, source.source),
            ProviderError(ProviderErrorCode.UNAVAILABLE, source.source),
        ]
        sleeps = []

        async def sleep(seconds):
            sleeps.append(seconds)

        retrying = RetryingProvider(
            source,
            RetryPolicy(
                max_attempts=3, initial_delay_seconds=0.5, backoff_factor=2, max_delay_seconds=2
            ),
            sleep=sleep,
        )
        assert (await retrying.get_player(ACCOUNT)).rank_tier == 51
        assert len(source.calls) == 3 and sleeps == [0.5, 1.0]
        source.failures = [RuntimeError("implementation bug")]
        with pytest.raises(RuntimeError):
            await retrying.get_player(ACCOUNT)
        with pytest.raises(ValidationError):
            RetryPolicy(retryable_codes=frozenset({ProviderErrorCode.RATE_LIMITED}))
        with pytest.raises(ValidationError):
            RetryPolicy(max_attempts=6)

    run_async(check())
