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
from .domain.models import DataMetadata, MatchSummary, PlayerBinding, PlayerProfile, RecentMatches
from .use_cases import Dota2Service

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
]
