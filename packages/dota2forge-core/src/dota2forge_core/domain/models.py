"""Normalized observations: unknown values stay None, never fabricated zeroes."""

from dataclasses import dataclass, field
from datetime import datetime

from .errors import DataSource, ValidationError
from .identity import AccountId, PlatformIdentity


def require_aware_time(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError("Expected a timezone-aware timestamp")


def require_nonnegative(value: int | None) -> None:
    if value is not None and (type(value) is not int or value < 0):
        raise ValidationError("Expected a nonnegative integer or missing value")


@dataclass(frozen=True, slots=True)
class DataMetadata:
    source: DataSource
    fetched_at: datetime
    observed_at: datetime | None = None
    patch: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, DataSource):
            raise ValidationError("Expected a known data source")
        require_aware_time(self.fetched_at)
        if self.observed_at is not None:
            require_aware_time(self.observed_at)
        if self.patch is not None and (
            not isinstance(self.patch, str) or not self.patch.strip() or len(self.patch) > 64
        ):
            raise ValidationError("Invalid game version")


@dataclass(frozen=True, slots=True)
class PlayerBinding:
    identity: PlatformIdentity = field(repr=False)
    account_id: AccountId = field(repr=False)
    bound_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.identity, PlatformIdentity) or not isinstance(
            self.account_id, AccountId
        ):
            raise ValidationError("Expected validated binding identities")
        require_aware_time(self.bound_at)


@dataclass(frozen=True, slots=True)
class PlayerProfile:
    account_id: AccountId = field(repr=False)
    metadata: DataMetadata
    display_name: str | None = field(default=None, repr=False)
    rank_tier: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, AccountId) or not isinstance(
            self.metadata, DataMetadata
        ):
            raise ValidationError("Expected validated player metadata")
        if self.display_name is not None and not isinstance(self.display_name, str):
            raise ValidationError("Expected a display name or missing value")
        require_nonnegative(self.rank_tier)

    @property
    def missing_fields(self) -> tuple[str, ...]:
        return tuple(name for name in ("display_name", "rank_tier") if getattr(self, name) is None)


@dataclass(frozen=True, slots=True)
class MatchSummary:
    match_id: int
    account_id: AccountId = field(repr=False)
    started_at: datetime
    metadata: DataMetadata
    hero_id: int | None = None
    duration_seconds: int | None = None
    kills: int | None = None
    deaths: int | None = None
    assists: int | None = None
    gold_per_minute: int | None = None
    experience_per_minute: int | None = None
    is_win: bool | None = None

    def __post_init__(self) -> None:
        if type(self.match_id) is not int or self.match_id <= 0:
            raise ValidationError("Expected a positive match ID")
        if not isinstance(self.account_id, AccountId) or not isinstance(
            self.metadata, DataMetadata
        ):
            raise ValidationError("Expected validated match metadata")
        require_aware_time(self.started_at)
        for name in (
            "hero_id",
            "duration_seconds",
            "kills",
            "deaths",
            "assists",
            "gold_per_minute",
            "experience_per_minute",
        ):
            require_nonnegative(getattr(self, name))
        if self.hero_id == 0:
            raise ValidationError("A missing hero must be None")
        if self.is_win is not None and type(self.is_win) is not bool:
            raise ValidationError("Expected a boolean outcome or missing value")

    @property
    def missing_fields(self) -> tuple[str, ...]:
        return tuple(
            name
            for name in (
                "hero_id",
                "duration_seconds",
                "kills",
                "deaths",
                "assists",
                "gold_per_minute",
                "experience_per_minute",
                "is_win",
            )
            if getattr(self, name) is None
        )


@dataclass(frozen=True, slots=True)
class RecentMatches:
    account_id: AccountId = field(repr=False)
    matches: tuple[MatchSummary, ...]
    metadata: DataMetadata

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, AccountId) or not isinstance(
            self.metadata, DataMetadata
        ):
            raise ValidationError("Expected validated recent-match metadata")
        if not isinstance(self.matches, tuple):
            raise ValidationError("Expected an immutable match collection")
        seen: set[int] = set()
        previous: datetime | None = None
        for match in self.matches:
            if (
                not isinstance(match, MatchSummary)
                or match.account_id != self.account_id
                or match.metadata.source != self.metadata.source
                or match.match_id in seen
            ):
                raise ValidationError("Inconsistent recent-match collection")
            if previous is not None and match.started_at > previous:
                raise ValidationError("Recent matches must be newest first")
            seen.add(match.match_id)
            previous = match.started_at
