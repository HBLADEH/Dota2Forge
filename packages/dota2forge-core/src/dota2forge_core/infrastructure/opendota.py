"""Explicit public player, match, analysis and hero item-statistics provider."""

import httpx

from ..domain.analysis import MatchAnalysisResult
from ..domain.errors import DataSource, ProviderErrorCode, ValidationError
from ..domain.hero_items import Hero, HeroItemStatistics
from ..domain.identity import AccountId
from ..domain.match_detail import MatchDetailResult, MatchId
from ..domain.models import DataMetadata, PlayerProfile, RecentMatches
from ..ports import Clock
from ._analysis_mapping import opendota_analysis
from ._hero_items_mapping import item_statistics
from ._opendota_http import OpenDotaHTTP, failure
from ._opendota_mapping import detail, match_rows, profile

_PROJECT = (
    "start_time",
    "duration",
    "hero_id",
    "kills",
    "deaths",
    "assists",
    "gold_per_min",
    "xp_per_min",
)


class OpenDotaProvider:
    """The caller supplies and closes the client; no I/O occurs during construction."""

    source = DataSource.OPENDOTA

    def __init__(
        self, client: httpx.AsyncClient, *, clock: Clock, timeout_seconds: float = 10
    ) -> None:
        self._http = OpenDotaHTTP(client, clock, timeout_seconds)

    async def get_player(self, account_id: AccountId) -> PlayerProfile:
        if not isinstance(account_id, AccountId):
            raise ValidationError("Expected a validated account")
        payload, fetched_at = await self._http.request(f"/players/{account_id.value}")
        return profile(payload, account_id, DataMetadata(self.source, fetched_at))

    async def get_hero_item_statistics(self, hero: Hero) -> HeroItemStatistics:
        if not isinstance(hero, Hero):
            raise ValidationError("Expected a validated hero")
        payload, fetched_at = await self._http.request(f"/heroes/{hero.hero_id}/itemPopularity")
        return item_statistics(payload, hero, DataMetadata(self.source, fetched_at))

    async def get_recent_matches(self, account_id: AccountId, limit: int) -> RecentMatches:
        if not isinstance(account_id, AccountId) or type(limit) is not int or not 1 <= limit <= 100:
            raise ValidationError("Expected a validated account and limit between 1 and 100")
        params = [("limit", str(limit)), ("significant", "0"), ("sort", "start_time")]
        params.extend(("project", name) for name in _PROJECT)
        payload, fetched_at = await self._http.request(
            f"/players/{account_id.value}/matches", params
        )
        metadata = DataMetadata(self.source, fetched_at)
        try:
            return RecentMatches(
                account_id, match_rows(payload, account_id, metadata, limit), metadata
            )
        except (ValidationError, ValueError, OverflowError, OSError):
            raise failure(ProviderErrorCode.INVALID_RESPONSE) from None

    async def get_match_detail(self, match_id: MatchId) -> MatchDetailResult:
        if not isinstance(match_id, MatchId):
            raise ValidationError("Expected a validated match ID")
        payload, fetched_at = await self._http.request(f"/matches/{match_id.value}")
        return detail(payload, match_id, DataMetadata(self.source, fetched_at))

    async def get_match_analysis(self, match_id: MatchId) -> MatchAnalysisResult:
        if not isinstance(match_id, MatchId):
            raise ValidationError("Expected a validated match ID")
        payload, fetched_at = await self._http.request(f"/matches/{match_id.value}")
        return opendota_analysis(payload, match_id, DataMetadata(self.source, fetched_at))
