"""Host-independent asynchronous I/O contracts used by public application services."""

from datetime import datetime
from typing import Protocol

from .domain.errors import DataSource
from .domain.identity import AccountId, PlatformIdentity
from .domain.models import PlayerBinding, PlayerProfile, RecentMatches


class Clock(Protocol):
    def now(self) -> datetime: ...


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
