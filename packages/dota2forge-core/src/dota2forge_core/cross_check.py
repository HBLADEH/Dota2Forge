"""Explicit two-source observations; never merge, select a winner or fall back."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum

from .domain.errors import DataSource, ProviderError, ProviderErrorCode, ValidationError
from .domain.identity import parse_account_id
from .domain.match_detail import (
    MatchDetail,
    MatchDetailResult,
    MatchDetailUnavailable,
    parse_match_id,
)
from .domain.models import PlayerProfile, RecentMatches
from .ports import ObservationProvider


class ObservationState(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED_PRIVATE = "skipped_private"


class ComparisonState(StrEnum):
    AGREE = "agree"
    DIFFERENT = "different"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ProviderFailure:
    source: DataSource
    code: ProviderErrorCode
    retry_after_seconds: int | None = None

    def __post_init__(self) -> None:
        ProviderError(self.code, self.source, retry_after_seconds=self.retry_after_seconds)


@dataclass(frozen=True, slots=True)
class SourceObservation[T]:
    source: DataSource
    state: ObservationState
    value: T | None = field(default=None, repr=False)
    failure: ProviderFailure | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, DataSource) or not isinstance(self.state, ObservationState):
            raise ValidationError("Expected a classified source observation")
        if self.state == ObservationState.SUCCESS:
            valid = self.value is not None and self.failure is None
        elif self.state == ObservationState.FAILED:
            valid = (
                self.value is None
                and isinstance(self.failure, ProviderFailure)
                and self.failure.source == self.source
            )
        else:
            valid = self.value is None and self.failure is None
        if not valid:
            raise ValidationError("Inconsistent source observation")


@dataclass(frozen=True, slots=True)
class FieldComparison:
    name: str
    primary_value: object = field(repr=False)
    secondary_value: object = field(repr=False)

    @property
    def state(self) -> ComparisonState:
        if self.primary_value is None or self.secondary_value is None:
            return ComparisonState.UNKNOWN
        return (
            ComparisonState.AGREE
            if self.primary_value == self.secondary_value
            else ComparisonState.DIFFERENT
        )


@dataclass(frozen=True, slots=True)
class CrossCheckResult[T]:
    primary: SourceObservation[T]
    secondary: SourceObservation[T]
    fields: tuple[FieldComparison, ...] = ()
    only_primary_ids: tuple[int, ...] = ()
    only_secondary_ids: tuple[int, ...] = ()


def compare_fields(
    left: object, right: object, names: tuple[str, ...], prefix: str = ""
) -> tuple[FieldComparison, ...]:
    return tuple(
        FieldComparison(prefix + name, getattr(left, name), getattr(right, name)) for name in names
    )


class CrossCheckService:
    def __init__(self, primary: ObservationProvider, secondary: ObservationProvider) -> None:
        if (
            not isinstance(primary.source, DataSource)
            or not isinstance(secondary.source, DataSource)
            or primary.source == secondary.source
        ):
            raise ValidationError("Cross-check requires two distinct classified sources")
        self._primary = primary
        self._secondary = secondary

    async def _observe[T](
        self,
        provider: ObservationProvider,
        query: Callable[[], Awaitable[T]],
        valid: Callable[[T, DataSource], bool],
    ) -> SourceObservation[T]:
        try:
            value = await query()
            if not valid(value, provider.source):
                raise ProviderError(ProviderErrorCode.INVALID_RESPONSE, provider.source)
            return SourceObservation(provider.source, ObservationState.SUCCESS, value)
        except ProviderError as error:
            failure = ProviderFailure(
                provider.source,
                error.code
                if error.source == provider.source
                else ProviderErrorCode.INVALID_RESPONSE,
                error.retry_after_seconds if error.source == provider.source else None,
            )
            return SourceObservation(provider.source, ObservationState.FAILED, failure=failure)

    async def _both[T](
        self,
        query: Callable[[ObservationProvider], Awaitable[T]],
        valid: Callable[[T, DataSource], bool],
    ) -> tuple[SourceObservation[T], SourceObservation[T]]:
        left = await self._observe(self._primary, lambda: query(self._primary), valid)
        if left.failure is not None and left.failure.code == ProviderErrorCode.PRIVATE:
            # Do not probe another source after an explicit privacy denial.
            right: SourceObservation[T] = SourceObservation(
                self._secondary.source, ObservationState.SKIPPED_PRIVATE
            )
        else:
            right = await self._observe(self._secondary, lambda: query(self._secondary), valid)
        return left, right

    async def get_player(self, account_id: int | str) -> CrossCheckResult[PlayerProfile]:
        target = parse_account_id(account_id)
        left, right = await self._both(
            lambda provider: provider.get_player(target),
            lambda result, source: (
                isinstance(result, PlayerProfile)
                and result.account_id == target
                and result.metadata.source == source
            ),
        )
        fields = (
            compare_fields(left.value, right.value, ("display_name", "rank_tier"))
            if left.value is not None and right.value is not None
            else ()
        )
        return CrossCheckResult(left, right, fields)

    async def get_recent_matches(
        self, account_id: int | str, limit: int = 10
    ) -> CrossCheckResult[RecentMatches]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValidationError("Expected a recent-match limit between 1 and 100")
        target = parse_account_id(account_id)
        left, right = await self._both(
            lambda provider: provider.get_recent_matches(target, limit),
            lambda result, source: (
                isinstance(result, RecentMatches)
                and result.account_id == target
                and len(result.matches) <= limit
                and result.metadata.source == source
            ),
        )
        if left.value is None or right.value is None:
            return CrossCheckResult(left, right)
        first = {match.match_id: match for match in left.value.matches}
        second = {match.match_id: match for match in right.value.matches}
        fields = tuple(
            comparison
            for match_id in sorted(first.keys() & second.keys())
            for comparison in compare_fields(
                first[match_id],
                second[match_id],
                (
                    "started_at",
                    "duration_seconds",
                    "hero_id",
                    "kills",
                    "deaths",
                    "assists",
                    "is_win",
                    "gold_per_minute",
                    "experience_per_minute",
                ),
                f"match.{match_id}.",
            )
        )
        return CrossCheckResult(
            left,
            right,
            fields,
            tuple(sorted(first.keys() - second.keys())),
            tuple(sorted(second.keys() - first.keys())),
        )

    async def get_match_detail(self, match_id: int | str) -> CrossCheckResult[MatchDetailResult]:
        target = parse_match_id(match_id)
        left, right = await self._both(
            lambda provider: provider.get_match_detail(target),
            lambda result, source: (
                isinstance(result, (MatchDetail, MatchDetailUnavailable))
                and result.match_id == target
                and result.metadata.source == source
            ),
        )
        fields = (
            compare_fields(
                left.value, right.value, ("started_at", "duration_seconds", "did_radiant_win")
            )
            if isinstance(left.value, MatchDetail) and isinstance(right.value, MatchDetail)
            else ()
        )
        # Parser/version/mode IDs and anonymous participant identities are source-specific.
        return CrossCheckResult(left, right, fields)
