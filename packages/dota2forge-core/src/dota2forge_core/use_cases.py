"""Public binding and query operations; dependencies are supplied by the host."""

from .domain.errors import (
    BindingNotFoundError,
    ProviderError,
    ProviderErrorCode,
    ValidationError,
)
from .domain.identity import AccountId, PlatformIdentity, parse_account_id
from .domain.match_detail import (
    MatchDetail,
    MatchDetailResult,
    MatchDetailUnavailable,
    parse_match_id,
)
from .domain.models import PlayerBinding, PlayerProfile, RecentMatches
from .ports import BindingRepository, Clock, MatchDetailProvider, MatchProvider, PlayerProvider

MAX_RECENT_MATCHES = 100


class MatchDetailService:
    """Direct historical lookup, with no binding or recent-list requirement."""

    def __init__(self, details: MatchDetailProvider) -> None:
        self._details = details

    async def get_match_detail(self, match_id: int | str) -> MatchDetailResult:
        target = parse_match_id(match_id)
        result = await self._details.get_match_detail(target)
        if (
            not isinstance(result, (MatchDetail, MatchDetailUnavailable))
            or result.match_id != target
            or result.metadata.source != self._details.source
        ):
            raise ProviderError(ProviderErrorCode.INVALID_RESPONSE, self._details.source)
        return result


class Dota2Service:
    def __init__(
        self,
        bindings: BindingRepository,
        players: PlayerProvider,
        matches: MatchProvider,
        clock: Clock,
    ) -> None:
        self._bindings = bindings
        self._players = players
        self._matches = matches
        self._clock = clock

    async def bind_account(
        self, identity: PlatformIdentity, steam_id: int | str, *, replace: bool = False
    ) -> PlayerBinding:
        """Save a lookup preference, not proof of Steam account ownership."""
        if type(replace) is not bool:
            raise ValidationError("Replacement must be explicitly boolean")
        binding = PlayerBinding(identity, parse_account_id(steam_id), self._clock.now())
        return await self._bindings.save(binding, replace=replace)

    async def get_binding(self, identity: PlatformIdentity) -> PlayerBinding:
        self._validate_identity(identity)
        binding = await self._bindings.get(identity)
        if binding is None:
            raise BindingNotFoundError()
        return binding

    async def unbind_account(self, identity: PlatformIdentity) -> bool:
        self._validate_identity(identity)
        return await self._bindings.delete(identity)

    async def get_player(
        self, identity: PlatformIdentity, *, account_id: AccountId | None = None
    ) -> PlayerProfile:
        target = await self._resolve_account(identity, account_id)
        result = await self._players.get_player(target)
        if (
            not isinstance(result, PlayerProfile)
            or result.account_id != target
            or result.metadata.source != self._players.source
        ):
            raise ProviderError(ProviderErrorCode.INVALID_RESPONSE, self._players.source)
        return result

    async def get_recent_matches(
        self, identity: PlatformIdentity, limit: int = 10, *, account_id: AccountId | None = None
    ) -> RecentMatches:
        if type(limit) is not int or not 1 <= limit <= MAX_RECENT_MATCHES:
            raise ValidationError("Recent-match limit must be an integer between 1 and 100")
        target = await self._resolve_account(identity, account_id)
        result = await self._matches.get_recent_matches(target, limit)
        if (
            not isinstance(result, RecentMatches)
            or result.account_id != target
            or result.metadata.source != self._matches.source
            or len(result.matches) > limit
        ):
            raise ProviderError(ProviderErrorCode.INVALID_RESPONSE, self._matches.source)
        return result

    async def _resolve_account(
        self, identity: PlatformIdentity, account_id: AccountId | None
    ) -> AccountId:
        self._validate_identity(identity)
        if account_id is not None:
            if not isinstance(account_id, AccountId):
                raise ValidationError("Explicit query target must be an AccountId")
            return account_id
        return (await self.get_binding(identity)).account_id

    @staticmethod
    def _validate_identity(identity: PlatformIdentity) -> None:
        if not isinstance(identity, PlatformIdentity):
            raise ValidationError("Expected an authenticated platform identity")
