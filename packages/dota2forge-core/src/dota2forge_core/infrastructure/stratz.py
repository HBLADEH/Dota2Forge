"""STRATZ player and recent-match providers, with explicitly injected HTTP lifetime."""

from dataclasses import replace

import httpx

from ..domain.errors import DataSource, ProviderErrorCode, ValidationError
from ..domain.identity import AccountId
from ..domain.models import DataMetadata, MatchSummary, PlayerProfile, RecentMatches
from ..ports import Clock
from ._stratz_http import StratzHTTP, failure
from ._stratz_mapping import match_page, player_data, profile

# Selections and scalar types checked against STRATZ introspection on 2026-09-30.
PLAYER_QUERY = """
query Dota2ForgePlayer($accountId: Long!) {
  player(steamAccountId: $accountId) {
    steamAccountId
    steamAccount { id name seasonRank }
  }
}
"""

RECENT_MATCHES_QUERY = """
query Dota2ForgeRecentMatches($accountId: Long!, $take: Int!, $skip: Int!) {
  player(steamAccountId: $accountId) {
    steamAccountId
    matches(request: {take: $take, skip: $skip, orderBy: DESC}) {
      id startDateTime durationSeconds didRadiantWin
      players(steamAccountId: $accountId) {
        steamAccountId heroId isRadiant kills deaths assists
        goldPerMinute experiencePerMinute
      }
    }
  }
}
"""

PAGE_SIZE = 20
MAX_PAGES = 10


class StratzProvider:
    """Implements both ports. Reuse one instance/client per token and event loop.

    The caller owns and closes the dedicated AsyncClient (prefer async with).
    Importing or constructing this provider does not send requests or read configuration.
    """

    source = DataSource.STRATZ

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        token: str,
        clock: Clock,
        timeout_seconds: float = 10,
    ) -> None:
        self._http = StratzHTTP(client, token, clock, timeout_seconds)

    async def get_player(self, account_id: AccountId) -> PlayerProfile:
        self._validate_account(account_id)
        payload, fetched_at = await self._http.request(
            PLAYER_QUERY, {"accountId": account_id.value}
        )
        metadata = DataMetadata(self.source, fetched_at)
        return profile(player_data(payload, account_id), account_id, metadata)

    async def get_recent_matches(self, account_id: AccountId, limit: int = 10) -> RecentMatches:
        self._validate_account(account_id)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValidationError("Recent-match limit must be an integer between 1 and 100")
        found: dict[int, MatchSummary] = {}
        offset = 0
        for _ in range(MAX_PAGES):
            take = min(PAGE_SIZE, limit - len(found))
            payload, fetched_at = await self._http.request(
                RECENT_MATCHES_QUERY,
                {"accountId": account_id.value, "take": take, "skip": offset},
            )
            metadata = DataMetadata(self.source, fetched_at)
            page = match_page(player_data(payload, account_id), account_id, metadata, take)
            previous_count = len(found)
            for match in page:
                previous = found.get(match.match_id)
                if previous is not None:
                    if replace(previous, metadata=match.metadata) != match:
                        raise failure(ProviderErrorCode.INVALID_RESPONSE)
                else:
                    found[match.match_id] = match
            if len(found) == limit or len(found) == previous_count:
                break
            # A short page might be a remote take cap. Advance by actual rows, not take.
            offset += len(page)
        ordered = tuple(
            sorted(found.values(), key=lambda item: (item.started_at, item.match_id), reverse=True)
        )
        return RecentMatches(account_id, ordered, metadata)

    @staticmethod
    def _validate_account(account_id: AccountId) -> None:
        if not isinstance(account_id, AccountId):
            raise ValidationError("Expected an AccountId")
