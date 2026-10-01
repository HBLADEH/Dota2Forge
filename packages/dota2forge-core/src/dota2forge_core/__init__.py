"""Dota2Forge public binding and query contracts; import has no I/O side effects."""

from .domain.errors import (
    BindingConflictError,
    BindingNotFoundError,
    DataSource,
    Dota2ForgeError,
    InvalidIdentityError,
    InvalidSteamIdError,
    ProviderError,
    ProviderErrorCode,
    RepositoryError,
    ValidationError,
)
from .domain.identity import AccountId, PlatformIdentity, SteamId64, parse_account_id
from .domain.match_detail import (
    MatchDetail,
    MatchDetailResult,
    MatchDetailUnavailable,
    MatchId,
    MatchParseState,
    MatchParticipant,
    parse_match_id,
)
from .domain.models import DataMetadata, MatchSummary, PlayerBinding, PlayerProfile, RecentMatches
from .use_cases import Dota2Service, MatchDetailService

__all__ = [
    "AccountId",
    "BindingConflictError",
    "BindingNotFoundError",
    "DataMetadata",
    "DataSource",
    "Dota2ForgeError",
    "Dota2Service",
    "InvalidIdentityError",
    "InvalidSteamIdError",
    "MatchSummary",
    "MatchDetail",
    "MatchDetailResult",
    "MatchDetailService",
    "MatchDetailUnavailable",
    "MatchId",
    "MatchParticipant",
    "MatchParseState",
    "PlatformIdentity",
    "PlayerBinding",
    "PlayerProfile",
    "ProviderError",
    "ProviderErrorCode",
    "RecentMatches",
    "RepositoryError",
    "SteamId64",
    "ValidationError",
    "parse_account_id",
    "parse_match_id",
]
