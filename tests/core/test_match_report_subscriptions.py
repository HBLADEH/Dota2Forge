from dataclasses import replace
from datetime import timedelta

import pytest
from dota2forge_core import (
    AccountId,
    DataMetadata,
    DataSource,
    MatchAnalysis,
    MatchAnalysisUnavailable,
    MatchDetail,
    MatchId,
    MatchParticipant,
    MatchReport,
    MatchSummary,
    MetricSemantic,
    MetricSeries,
    ParticipantAnalysis,
    PlayerProfile,
    PurchaseEvent,
    RecentMatches,
    SQLiteSubscriptionRepository,
    SubscriptionKind,
    SubscriptionPollState,
    SubscriptionScope,
    SubscriptionService,
)


class ReportProvider:
    source = DataSource.STRATZ

    def __init__(self, account_id, clock):
        self.account_id = account_id
        self.clock = clock
        self.rank_tier = 40
        self.match_id = MatchId(9001)
        self.recent = RecentMatches(account_id, (), self.metadata())
        self.detail = MatchDetail(
            self.match_id,
            self.metadata(),
            started_at=self.clock.now(),
            duration_seconds=None,
            did_radiant_win=None,
        )
        self.analysis = MatchAnalysisUnavailable(self.match_id, self.metadata())
        self.calls = []

    def metadata(self):
        return DataMetadata(self.source, self.clock.now())

    async def get_player(self, account_id):
        self.calls.append("player")
        return PlayerProfile(account_id, self.metadata(), rank_tier=self.rank_tier)

    async def get_recent_matches(self, account_id, limit):
        self.calls.append("recent")
        return self.recent

    async def get_match_detail(self, match_id):
        self.calls.append("detail")
        return self.detail

    async def get_match_analysis(self, match_id):
        self.calls.append("analysis")
        return self.analysis


def make_provider(account_id, clock):
    provider = ReportProvider(account_id, clock)
    provider.detail = MatchDetail(
        provider.match_id,
        provider.metadata(),
        started_at=clock.now(),
        duration_seconds=None,
        did_radiant_win=None,
    )
    return provider


def completed_detail(provider, clock):
    metadata = provider.metadata()
    return MatchDetail(
        provider.match_id,
        metadata,
        started_at=clock.now(),
        duration_seconds=1800,
        did_radiant_win=True,
        game_mode="ALL_PICK",
        players=(
            MatchParticipant(
                0,
                AccountId(123),
                "Tracked",
                False,
                True,
                1,
                18,
                2,
                20,
                700,
                600,
                (1, None, None, None, None, None),
            ),
            MatchParticipant(
                1,
                AccountId(456),
                "Teammate",
                False,
                True,
                2,
                10,
                4,
                12,
                600,
                500,
                (2, None, None, None, None, None),
            ),
        ),
    )


def completed_analysis(provider, purchase_time=30):
    return MatchAnalysis(
        provider.match_id,
        provider.detail.metadata,
        (
            ParticipantAnalysis(
                AccountId(123),
                0,
                (MetricSeries("networth", MetricSemantic.NETWORTH_LEVEL, (100, 200)),),
                (PurchaseEvent(purchase_time, item_id=1),),
            ),
        ),
    )


@pytest.fixture
def report_service(tmp_path, identity, clock, run_async):
    provider = make_provider(AccountId(123), clock)
    repository = SQLiteSubscriptionRepository(tmp_path / "subscriptions.sqlite3")
    run_async(repository.initialize())
    return (
        SubscriptionService(repository, provider, provider, clock, provider, provider),
        provider,
        repository,
        identity,
        clock,
    )


@pytest.mark.parametrize("purchase_time", [-89, 30])
def test_specific_match_waits_for_completion_then_persists_detail_analysis_and_candidate(
    report_service, run_async, purchase_time
):
    service, provider, repository, identity, clock = report_service
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        subscription = await service.subscribe_match(identity, "9001", "group:synthetic")
        first = (await service.poll_match_reports(scope))[0]
        assert first.state == SubscriptionPollState.UNCHANGED
        assert not await repository.pending(scope)

        provider.detail = completed_detail(provider, clock)
        provider.analysis = completed_analysis(provider, purchase_time)
        clock.instant += timedelta(seconds=1)
        result = (await service.poll_match_reports(scope))[0]
        assert result.state == SubscriptionPollState.EVENTS
        event = result.events[0]
        assert isinstance(event.payload, MatchReport)
        assert event.payload.completed
        assert event.payload.performance_candidate == (AccountId(123), 0)
        assert isinstance(event.payload.analysis, MatchAnalysis)
        assert await repository.pending(scope) == (event,)

        reopened = SQLiteSubscriptionRepository(repository._database)
        await reopened.initialize()
        persisted = (await reopened.pending(scope))[0].payload
        assert isinstance(persisted, MatchReport)
        assert persisted.detail == event.payload.detail
        assert persisted.analysis == event.payload.analysis
        assert persisted.analysis.participants[0].purchases[0].time_seconds == purchase_time
        again = (await service.poll_match_reports(scope))[0]
        assert again.state == SubscriptionPollState.UNCHANGED
        assert await service.list_subscriptions(identity) == (
            replace(subscription, checkpoint=result.subscription.checkpoint, revision=1),
        )

    run_async(scenario())


def test_player_subscription_turns_new_recent_match_into_report_event(report_service, run_async):
    service, provider, repository, identity, clock = report_service
    scope = SubscriptionScope.for_identity(identity)
    metadata = provider.metadata()

    async def scenario():
        await service.subscribe(identity, 123, "group:synthetic", kind=SubscriptionKind.NEW_MATCH)
        provider.recent = RecentMatches(
            AccountId(123),
            (MatchSummary(1, AccountId(123), clock.now(), metadata, is_win=True),),
            metadata,
        )
        assert (await service.poll_new_matches(scope))[0].state == SubscriptionPollState.BASELINED
        clock.instant += timedelta(seconds=2)
        provider.recent = replace(
            provider.recent,
            metadata=provider.metadata(),
            matches=(
                MatchSummary(2, AccountId(123), clock.now(), provider.metadata(), is_win=True),
                MatchSummary(
                    1, AccountId(123), clock.now() - timedelta(seconds=2), metadata, is_win=True
                ),
            ),
        )
        provider.match_id = type(provider.match_id)(2)
        provider.detail = replace(completed_detail(provider, clock), match_id=provider.match_id)
        provider.analysis = replace(completed_analysis(provider), match_id=provider.match_id)
        result = (await service.poll_new_matches(scope))[0]
        assert result.state == SubscriptionPollState.EVENTS
        assert isinstance(result.events[0].payload, MatchReport)
        assert result.events[0].payload.tracked_account_id == AccountId(123)
        assert len(await repository.pending(scope)) == 1

    run_async(scenario())
