"""Composable provider caching and bounded transient retries."""

import asyncio
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar, cast

from ..domain.errors import DataSource, ProviderError, ProviderErrorCode, ValidationError
from ..domain.identity import AccountId
from ..domain.match_detail import MatchDetail, MatchDetailResult, MatchDetailUnavailable, MatchId
from ..domain.models import PlayerProfile, RecentMatches
from ..ports import ObservationProvider

T = TypeVar("T")


class Cache(Protocol):
    async def get(self, key: str) -> object | None: ...

    async def set(self, key: str, value: object, ttl_seconds: float) -> None: ...

    async def delete(self, key: str) -> None: ...


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_delay_seconds: float = 0.25
    backoff_factor: float = 2.0
    max_delay_seconds: float = 2.0
    retryable_codes: frozenset[ProviderErrorCode] = frozenset(
        {ProviderErrorCode.TIMEOUT, ProviderErrorCode.UNAVAILABLE}
    )

    def __post_init__(self) -> None:
        if type(self.max_attempts) is not int or not 1 <= self.max_attempts <= 5:
            raise ValidationError("Retry attempts must be an integer between 1 and 5")
        for value in (
            self.initial_delay_seconds,
            self.backoff_factor,
            self.max_delay_seconds,
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                raise ValidationError("Retry delays and backoff must be finite nonnegative numbers")
        if self.backoff_factor < 1 or self.max_delay_seconds < self.initial_delay_seconds:
            raise ValidationError("Retry backoff must grow from the initial delay")
        if not self.retryable_codes or not self.retryable_codes <= {
            ProviderErrorCode.TIMEOUT,
            ProviderErrorCode.UNAVAILABLE,
        }:
            raise ValidationError("Only timeout and unavailable errors may be retried")

    def delay_after(self, failed_attempt: int) -> float:
        return min(
            self.max_delay_seconds,
            self.initial_delay_seconds * self.backoff_factor ** max(0, failed_attempt - 1),
        )


async def _sleep(seconds: float) -> None:
    if seconds:
        await asyncio.sleep(seconds)


class RetryingProvider:
    """Retries only classified transient provider failures; caller owns the wrapped client."""

    def __init__(
        self,
        provider: ObservationProvider,
        policy: RetryPolicy | None = None,
        *,
        sleep: Callable[[float], Awaitable[None]] = _sleep,
    ) -> None:
        if not isinstance(provider.source, DataSource):
            raise ValidationError("Retrying provider requires a classified source")
        self._provider = provider
        self._policy = RetryPolicy() if policy is None else policy
        self._sleep = sleep

    @property
    def source(self) -> DataSource:
        return self._provider.source

    async def _call(self, operation: Callable[[], Awaitable[T]]) -> T:
        for attempt in range(1, self._policy.max_attempts + 1):
            try:
                return await operation()
            except ProviderError as error:
                if (
                    error.code not in self._policy.retryable_codes
                    or attempt == self._policy.max_attempts
                ):
                    raise
                await self._sleep(self._policy.delay_after(attempt))
        raise AssertionError("Retry loop must return or raise")

    async def get_player(self, account_id: AccountId) -> PlayerProfile:
        return await self._call(lambda: self._provider.get_player(account_id))

    async def get_recent_matches(self, account_id: AccountId, limit: int) -> RecentMatches:
        return await self._call(lambda: self._provider.get_recent_matches(account_id, limit))

    async def get_match_detail(self, match_id: MatchId) -> MatchDetailResult:
        return await self._call(lambda: self._provider.get_match_detail(match_id))


class CachedProvider:
    """Caches immutable successful observations and exposes explicit refresh methods."""

    def __init__(
        self, provider: ObservationProvider, cache: Cache, *, ttl_seconds: float = 300
    ) -> None:
        if not isinstance(provider.source, DataSource):
            raise ValidationError("Cached provider requires a classified source")
        if ttl_seconds <= 0 or not math.isfinite(ttl_seconds):
            raise ValidationError("Provider cache TTL must be finite and positive")
        self._provider = provider
        self._cache = cache
        self._ttl = float(ttl_seconds)

    @property
    def source(self) -> DataSource:
        return self._provider.source

    def _key(self, operation: str, value: int, extra: int | None = None) -> str:
        suffix = "" if extra is None else f":{extra}"
        return f"dota2forge:{self.source.value}:{operation}:{value}{suffix}"

    async def _get_or_fetch(
        self,
        key: str,
        expected: type[object] | tuple[type[object], ...],
        operation: Callable[[], Awaitable[T]],
        valid: Callable[[T], bool],
        *,
        refresh: bool,
    ) -> T:
        if not refresh:
            cached = await self._cache.get(key)
            if cached is not None:
                if not isinstance(cached, expected) or not valid(cast(T, cached)):
                    await self._cache.delete(key)
                    raise ProviderError(ProviderErrorCode.INVALID_RESPONSE, self.source)
                return cast(T, cached)
        value = await operation()
        if not isinstance(value, expected) or not valid(value):
            raise ProviderError(ProviderErrorCode.INVALID_RESPONSE, self.source)
        await self._cache.set(key, value, self._ttl)
        return value

    async def get_player(self, account_id: AccountId) -> PlayerProfile:
        return await self._get_player(account_id, refresh=False)

    async def refresh_player(self, account_id: AccountId) -> PlayerProfile:
        return await self._get_player(account_id, refresh=True)

    async def _get_player(self, account_id: AccountId, *, refresh: bool) -> PlayerProfile:
        if not isinstance(account_id, AccountId):
            raise ValidationError("Expected an AccountId")
        return await self._get_or_fetch(
            self._key("player", account_id.value),
            PlayerProfile,
            lambda: self._provider.get_player(account_id),
            lambda value: value.account_id == account_id and value.metadata.source == self.source,
            refresh=refresh,
        )

    async def get_recent_matches(self, account_id: AccountId, limit: int) -> RecentMatches:
        return await self._get_recent(account_id, limit, refresh=False)

    async def refresh_recent_matches(self, account_id: AccountId, limit: int) -> RecentMatches:
        return await self._get_recent(account_id, limit, refresh=True)

    async def _get_recent(
        self, account_id: AccountId, limit: int, *, refresh: bool
    ) -> RecentMatches:
        if not isinstance(account_id, AccountId) or type(limit) is not int or not 1 <= limit <= 100:
            raise ValidationError("Expected an AccountId and limit between 1 and 100")
        return await self._get_or_fetch(
            self._key("recent", account_id.value, limit),
            RecentMatches,
            lambda: self._provider.get_recent_matches(account_id, limit),
            lambda value: (
                value.account_id == account_id
                and value.metadata.source == self.source
                and len(value.matches) <= limit
            ),
            refresh=refresh,
        )

    async def get_match_detail(self, match_id: MatchId) -> MatchDetailResult:
        return await self._get_detail(match_id, refresh=False)

    async def refresh_match_detail(self, match_id: MatchId) -> MatchDetailResult:
        return await self._get_detail(match_id, refresh=True)

    async def _get_detail(self, match_id: MatchId, *, refresh: bool) -> MatchDetailResult:
        if not isinstance(match_id, MatchId):
            raise ValidationError("Expected a MatchId")
        result = await self._get_or_fetch(
            self._key("detail", match_id.value),
            (MatchDetail, MatchDetailUnavailable),
            lambda: self._provider.get_match_detail(match_id),
            lambda value: value.match_id == match_id and value.metadata.source == self.source,
            refresh=refresh,
        )
        return result

    async def invalidate_account(self, account_id: AccountId) -> None:
        if not isinstance(account_id, AccountId):
            raise ValidationError("Expected an AccountId")
        await self._cache.delete(self._key("player", account_id.value))
        for limit in range(1, 101):
            await self._cache.delete(self._key("recent", account_id.value, limit))

    async def invalidate_match(self, match_id: MatchId) -> None:
        if not isinstance(match_id, MatchId):
            raise ValidationError("Expected a MatchId")
        await self._cache.delete(self._key("detail", match_id.value))
