"""Two-source fixtures verify observations remain independent, including failures."""

import asyncio
from dataclasses import replace

import pytest
from dota2forge_core import (
    AccountId,
    ComparisonState,
    CrossCheckService,
    DataMetadata,
    DataSource,
    FieldComparison,
    MatchDetail,
    MatchDetailUnavailable,
    MatchSummary,
    ObservationState,
    PlayerProfile,
    ProviderError,
    ProviderErrorCode,
    ProviderFailure,
    RecentMatches,
    SourceObservation,
    ValidationError,
)


class SyntheticSource:
    def __init__(self, source, clock, rank=51):
        self.source = source
        self.metadata = DataMetadata(source, clock.now())
        self.rank = rank
        self.error = None
        self.calls = []
        self.ids = (1001,)
        self.result_source = source
        self.account = AccountId(123)
        self.null_detail = False

    def observe(self, method):
        self.calls.append(method)
        if self.error is not None:
            raise self.error
        return replace(self.metadata, source=self.result_source)

    async def get_player(self, account_id):
        return PlayerProfile(self.account, self.observe("player"), "Synthetic", self.rank)

    async def get_recent_matches(self, account_id, limit):
        metadata = self.observe("recent")
        rows = tuple(
            MatchSummary(index, self.account, metadata.fetched_at, metadata, kills=0)
            for index in self.ids
        )
        return RecentMatches(self.account, rows, metadata)

    async def get_match_detail(self, match_id):
        metadata = self.observe("detail")
        if self.null_detail:
            return MatchDetailUnavailable(match_id, metadata)
        return MatchDetail(match_id, metadata, duration_seconds=0, has_stats=False)


def sources(clock):
    return SyntheticSource(DataSource.STRATZ, clock), SyntheticSource(
        DataSource.OPENDOTA, clock, 52
    )


def test_rank_conflict_zero_missing_and_repr_preserve_both_sources(clock, run_async):
    primary, secondary = sources(clock)

    async def check():
        service = CrossCheckService(primary, secondary)
        result = await service.get_player("76561197960265851")
        assert result.primary.value.rank_tier == 51 and result.secondary.value.rank_tier == 52
        assert result.fields[1].state is ComparisonState.DIFFERENT
        assert result.fields[0].state is ComparisonState.AGREE
        assert "Synthetic" not in repr(result) and "123" not in repr(result)
        primary.rank = 0
        secondary.rank = None
        unknown = await service.get_player(123)
        assert (
            unknown.fields[1].primary_value == 0
            and unknown.fields[1].state is ComparisonState.UNKNOWN
        )
        assert FieldComparison("zero", 0, 0).state is ComparisonState.AGREE

    run_async(check())


@pytest.mark.parametrize("operation", ["player", "recent", "detail"])
@pytest.mark.parametrize(
    "code", [ProviderErrorCode.PRIVATE, ProviderErrorCode.TIMEOUT, ProviderErrorCode.RATE_LIMITED]
)
def test_primary_failure_is_preserved_and_private_skips_second_source(
    clock, run_async, operation, code
):
    primary, secondary = sources(clock)
    primary.error = ProviderError(
        code,
        primary.source,
        retry_after_seconds=7 if code is ProviderErrorCode.RATE_LIMITED else None,
    )

    async def check():
        service = CrossCheckService(primary, secondary)
        method = {
            "player": service.get_player,
            "recent": service.get_recent_matches,
            "detail": service.get_match_detail,
        }[operation]
        result = await method(123)
        assert (
            result.primary.state is ObservationState.FAILED and result.primary.failure.code is code
        )
        assert result.primary.value is None and result.fields == ()
        if code is ProviderErrorCode.PRIVATE:
            assert (
                result.secondary.state is ObservationState.SKIPPED_PRIVATE and secondary.calls == []
            )
        else:
            assert result.secondary.state is ObservationState.SUCCESS and secondary.calls == [
                operation
            ]
        if code is ProviderErrorCode.RATE_LIMITED:
            assert result.primary.failure.retry_after_seconds == 7

    run_async(check())


def test_recent_match_ids_only_compare_overlap_and_unknown_values(clock, run_async):
    primary, secondary = sources(clock)
    primary.ids, secondary.ids = (1001, 1002), (1002, 1003)

    async def check():
        result = await CrossCheckService(primary, secondary).get_recent_matches(123)
        assert result.only_primary_ids == (1001,) and result.only_secondary_ids == (1003,)
        assert all(value.name.startswith("match.1002.") for value in result.fields)
        assert (
            next(value for value in result.fields if value.name.endswith("kills")).state
            is ComparisonState.AGREE
        )
        assert (
            next(value for value in result.fields if value.name.endswith("hero_id")).state
            is ComparisonState.UNKNOWN
        )
        primary.ids = ()
        empty = await CrossCheckService(primary, secondary).get_recent_matches(123)
        assert empty.primary.value.matches == () and empty.fields == ()

    run_async(check())


def test_detail_null_and_secondary_failure_stay_visible(clock, run_async):
    primary, secondary = sources(clock)

    async def check():
        service = CrossCheckService(primary, secondary)
        result = await service.get_match_detail("1001")
        assert result.fields[1].state is ComparisonState.AGREE
        secondary.null_detail = True
        result = await service.get_match_detail(1001)
        assert isinstance(result.secondary.value, MatchDetailUnavailable) and result.fields == ()
        secondary.error = ProviderError(ProviderErrorCode.UNAVAILABLE, secondary.source)
        result = await service.get_match_detail(1001)
        assert result.primary.value.duration_seconds == 0
        assert result.secondary.state is ObservationState.FAILED

    run_async(check())


@pytest.mark.parametrize("fault", ["wrong_source", "wrong_account", "excess", "foreign_error"])
def test_provider_contract_violations_are_classified(clock, run_async, fault):
    primary, secondary = sources(clock)
    if fault == "wrong_source":
        primary.result_source = DataSource.OPENDOTA
    elif fault == "wrong_account":
        primary.account = AccountId(124)
    elif fault == "excess":
        primary.ids = (1001, 1002)
    else:
        primary.error = ProviderError(ProviderErrorCode.PRIVATE, DataSource.OPENDOTA)

    async def check():
        service = CrossCheckService(primary, secondary)
        result = (
            await service.get_recent_matches(123, 1)
            if fault == "excess"
            else await service.get_player(123)
        )
        assert result.primary.failure.code is ProviderErrorCode.INVALID_RESPONSE
        assert result.primary.failure.source is DataSource.STRATZ
        assert result.secondary.state is ObservationState.SUCCESS

    run_async(check())


@pytest.mark.parametrize("error", [asyncio.CancelledError(), RuntimeError("implementation bug")])
def test_cancel_and_unexpected_errors_propagate_without_second_query(clock, run_async, error):
    primary, secondary = sources(clock)
    primary.error = error

    async def check():
        with pytest.raises(type(error)):
            await CrossCheckService(primary, secondary).get_player(123)
        assert secondary.calls == []

    run_async(check())


def test_public_results_and_inputs_reject_inconsistent_states(clock, run_async):
    primary, secondary = sources(clock)
    with pytest.raises(ValidationError):
        CrossCheckService(primary, primary)
    primary.source = "not classified"
    with pytest.raises(ValidationError):
        CrossCheckService(primary, secondary)
    for source, state, value, failure in [
        (DataSource.STRATZ, ObservationState.SUCCESS, None, None),
        (DataSource.STRATZ, ObservationState.FAILED, None, None),
        (DataSource.STRATZ, ObservationState.SKIPPED_PRIVATE, "data", None),
        (
            DataSource.STRATZ,
            ObservationState.FAILED,
            None,
            ProviderFailure(DataSource.OPENDOTA, ProviderErrorCode.PRIVATE),
        ),
        ("stratz", "success", 1, None),
    ]:
        with pytest.raises(ValidationError):
            SourceObservation(source, state, value, failure)
    primary, secondary = sources(clock)

    async def check():
        service = CrossCheckService(primary, secondary)
        for limit in (0, 101, True):
            with pytest.raises(ValidationError):
                await service.get_recent_matches(123, limit)
        with pytest.raises(ValidationError):
            await service.get_match_detail("01")
        assert primary.calls == [] and secondary.calls == []

    run_async(check())
