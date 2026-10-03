"""Host-independent asynchronous I/O contracts used by public application services."""

from datetime import datetime
from typing import Protocol, TypeVar

from .domain.analysis import MatchAnalysisResult
from .domain.errors import DataSource
from .domain.identity import AccountId, PlatformIdentity
from .domain.match_detail import MatchDetailResult, MatchId
from .domain.models import PlayerBinding, PlayerProfile, RecentMatches
from .domain.subscriptions import (
    Subscription,
    SubscriptionCheckpoint,
    SubscriptionEvent,
    SubscriptionKind,
    SubscriptionScope,
)

T = TypeVar("T")


class Clock(Protocol):
    def now(self) -> datetime: ...


class CachePort(Protocol[T]):
    """Async key/value cache used only by infrastructure decorators."""

    async def get(self, key: str) -> T | None: ...

    async def set(self, key: str, value: T, ttl_seconds: float) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def clear(self) -> None: ...


class BindingRepository(Protocol):
    async def get(self, identity: PlatformIdentity) -> PlayerBinding | None: ...

    async def save(self, binding: PlayerBinding, *, replace: bool = False) -> PlayerBinding:
        """Atomically preserve an identical binding or reject an unapproved replacement."""
        ...

    async def delete(self, identity: PlatformIdentity) -> bool:
        """Return whether a binding was removed; absence is a successful no-op."""
        ...


class PlayerProvider(Protocol):
    @property
    def source(self) -> DataSource: ...

    async def get_player(self, account_id: AccountId) -> PlayerProfile:
        """Raise a classified ProviderError for missing, private or failed requests."""
        ...


class MatchProvider(Protocol):
    @property
    def source(self) -> DataSource: ...

    async def get_recent_matches(self, account_id: AccountId, limit: int) -> RecentMatches:
        """Return up to limit newest-first matches; empty is a valid observed result."""
        ...


class MatchDetailProvider(Protocol):
    @property
    def source(self) -> DataSource: ...

    async def get_match_detail(self, match_id: MatchId) -> MatchDetailResult:
        """Query the ID directly; null data remains distinct from classified failures."""
        ...


class MatchAnalysisProvider(Protocol):
    @property
    def source(self) -> DataSource: ...

    async def get_match_analysis(self, match_id: MatchId) -> MatchAnalysisResult:
        """Return source-specific economics and purchase events without IMP inference."""
        ...


class ObservationProvider(PlayerProvider, MatchProvider, MatchDetailProvider, Protocol):
    """A source implementing all three independent observation ports."""


class SubscriptionRepository(Protocol):
    async def save(self, subscription: Subscription) -> Subscription:
        """Atomically return an existing identical key or save a new subscription."""
        ...

    async def list(
        self,
        scope: SubscriptionScope,
        *,
        owner: PlatformIdentity | None = None,
        kind: SubscriptionKind | None = None,
        destination: str | None = None,
        limit: int = 20,
        after_id: str | None = None,
    ) -> tuple[Subscription, ...]: ...

    async def delete(self, identity: PlatformIdentity, subscription_id: str) -> bool:
        """Atomically remove an owner's subscription and its pending events."""
        ...

    async def commit(
        self,
        previous: Subscription,
        checkpoint: SubscriptionCheckpoint,
        events: tuple[SubscriptionEvent, ...],
    ) -> bool:
        """Save checkpoint and outbox together, only if previous is still current."""
        ...

    async def pending(
        self,
        scope: SubscriptionScope,
        *,
        owner: PlatformIdentity | None = None,
        limit: int = 20,
    ) -> tuple[SubscriptionEvent, ...]: ...

    async def acknowledge(self, identity: PlatformIdentity, event_id: str) -> bool:
        """Remove a pending event only after the host has confirmed successful delivery."""
        ...

    async def delete_all(self, identity: PlatformIdentity) -> int: ...

    async def scopes(
        self, namespace: str, *, after: SubscriptionScope | None = None
    ) -> tuple[SubscriptionScope, ...]: ...

    async def deliverable(
        self, scope: SubscriptionScope, *, limit: int = 20, after_sequence: int = 0
    ) -> tuple[SubscriptionEvent, ...]: ...

    async def event_sequence(self, scope: SubscriptionScope, event_id: str) -> int | None: ...

    async def claim(
        self, identity: PlatformIdentity, event_id: str, attempted_at: datetime
    ) -> SubscriptionEvent | None: ...

    async def release(self, identity: PlatformIdentity, event_id: str) -> bool: ...
