import asyncio
import json
import sqlite3
from contextlib import closing
from dataclasses import replace
from datetime import date, datetime, timedelta

import pytest
from dota2forge_core import (
    DailyCoverage,
    DailyReport,
    DataMetadata,
    MatchSummary,
    ProviderError,
    ProviderErrorCode,
    RecentMatches,
    SQLiteSubscriptionRepository,
    SubscriptionKind,
    SubscriptionPollState,
    SubscriptionRepositoryError,
    SubscriptionScope,
    SubscriptionService,
    ValidationError,
    report_bounds,
)
from dota2forge_renderer.subscriptions import subscription_event_text


@pytest.fixture
def daily_store(tmp_path, provider, clock, run_async):
    repository = SQLiteSubscriptionRepository(tmp_path / "subscriptions.sqlite3")
    run_async(repository.initialize())
    return SubscriptionService(repository, provider, provider, clock), repository


def daily_observation(provider, clock, rows):
    metadata = DataMetadata(provider.source, clock.now())
    matches = tuple(
        MatchSummary(index, provider.profile.account_id, instant, metadata, is_win=outcome)
        for index, instant, outcome in rows
    )
    provider.recent = RecentMatches(provider.profile.account_id, matches, metadata)


def test_daily_beijing_half_open_bounds_unknowns_dedup_and_restart(
    daily_store, identity, provider, clock, tmp_path, run_async
):
    service, repository = daily_store
    scope = SubscriptionScope.for_identity(identity)
    report_date = date(2026, 9, 30)
    start, end = report_bounds(report_date)
    assert start.isoformat() == "2026-09-30T00:00:00+08:00"
    assert end.isoformat() == "2026-10-01T00:00:00+08:00"

    async def scenario():
        await service.subscribe(identity, 123, "synthetic", kind=SubscriptionKind.DAILY_REPORT)
        clock.instant = end + timedelta(hours=2)
        daily_observation(
            provider,
            clock,
            [
                (5, end, True),
                (4, end - timedelta(seconds=1), None),
                (3, start + timedelta(hours=1), False),
                (2, start, True),
                (1, start - timedelta(seconds=1), True),
            ],
        )
        result = (await service.poll_daily_reports(scope, report_date))[0]
        assert result.state == SubscriptionPollState.EVENTS and not result.coverage_gap
        report = result.events[0].payload
        assert isinstance(report, DailyReport)
        assert [match.match_id for match in report.matches] == [4, 3, 2]
        assert (report.wins, report.losses, report.unknown_outcomes) == (1, 1, 1)
        assert report.coverage == DailyCoverage.WINDOW_SPANNED
        text = subscription_event_text(result.events[0])
        assert "2026-09-30" in text and "未知" in text and "完整" in text
        reopened = SQLiteSubscriptionRepository(tmp_path / "subscriptions.sqlite3")
        await reopened.initialize()
        assert await reopened.pending(scope) == result.events
        again = SubscriptionService(reopened, provider, provider, clock)
        assert (await again.poll_daily_reports(scope, report_date))[0].state == (
            SubscriptionPollState.UNCHANGED
        )
        assert len(provider.calls) == 1
        assert await repository.pending(scope) == result.events

    run_async(scenario())


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("empty", DailyCoverage.EMPTY),
        ("bounded", DailyCoverage.BOUNDED),
        ("truncated", DailyCoverage.TRUNCATED),
        ("spanned", DailyCoverage.WINDOW_SPANNED),
    ],
)
def test_daily_coverage_does_not_claim_complete_history(
    daily_store, identity, provider, clock, mode, expected, run_async
):
    service, _repository = daily_store
    report_date = date(2026, 9, 30)
    start, end = report_bounds(report_date)

    async def scenario():
        await service.subscribe(identity, 123, "synthetic", kind=SubscriptionKind.DAILY_REPORT)
        clock.instant = end + timedelta(hours=1)
        rows = [] if mode == "empty" else [(3, start + timedelta(hours=2), True)]
        if mode == "truncated":
            rows += [(2, start + timedelta(hours=1), False), (1, start, None)]
        if mode == "spanned":
            rows += [(1, start - timedelta(seconds=1), True)]
        daily_observation(provider, clock, rows)
        result = (
            await service.poll_daily_reports(
                SubscriptionScope.for_identity(identity), report_date, match_limit=3
            )
        )[0]
        assert result.events[0].payload.coverage == expected
        assert result.coverage_gap == (expected != DailyCoverage.WINDOW_SPANNED)

    run_async(scenario())


def test_daily_no_backfill_stale_observation_and_future_rejection(
    daily_store, identity, provider, clock, run_async
):
    service, repository = daily_store
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        first = await service.subscribe(
            identity, 123, "synthetic", kind=SubscriptionKind.DAILY_REPORT
        )
        previous = date(2026, 9, 29)
        baseline = (await service.poll_daily_reports(scope, previous))[0]
        assert baseline.state == SubscriptionPollState.BASELINED
        assert baseline.subscription.revision == first.revision + 1
        assert baseline.subscription.checkpoint.report_date == previous
        assert not provider.calls and not await repository.pending(scope)
        with pytest.raises(ValidationError):
            await service.poll_daily_reports(scope, clock.now().date())
        clock.instant += timedelta(days=1)
        stale = (await service.poll_daily_reports(scope, date(2026, 9, 30)))[0]
        assert stale.state == SubscriptionPollState.STALE
        assert not await repository.pending(scope)

    run_async(scenario())


@pytest.mark.parametrize("invalid", [None, "2026-09-30", datetime(2026, 9, 30), date(1, 1, 1)])
def test_invalid_daily_dates(invalid):
    with pytest.raises(ValidationError):
        report_bounds(invalid)


@pytest.mark.parametrize("change", ["account", "source", "duplicate", "time", "id", "rows"])
def test_daily_values_are_strict(provider, change):
    report_date = date(2026, 9, 30)
    start, _end = report_bounds(report_date)
    match = replace(provider.recent.matches[0], started_at=start)
    rows = (match,)
    if change == "account":
        rows = (replace(match, account_id=type(match.account_id)(456)),)
    elif change == "source":
        rows = (
            replace(match, metadata=replace(match.metadata, source=type(provider.source).STRATZ)),
        )
    elif change == "duplicate":
        rows = (match, match)
    elif change == "time":
        rows = (replace(match, started_at=start - timedelta(seconds=1)),)
    elif change == "id":
        rows = (replace(match, match_id=2**63),)
    else:
        rows = [match]
    with pytest.raises(ValidationError):
        DailyReport(
            provider.profile.account_id,
            report_date,
            provider.profile.metadata,
            rows,
            DailyCoverage.BOUNDED,
        )


def seed_event(service, provider, clock, identity):
    async def scenario():
        scope = SubscriptionScope.for_identity(identity)
        await service.subscribe(identity, 123, "synthetic", kind=SubscriptionKind.RANK_CHANGE)
        provider.profile = replace(provider.profile, rank_tier=40)
        await service.poll_rank_changes(scope)
        clock.instant += timedelta(seconds=1)
        provider.profile = replace(
            provider.profile,
            rank_tier=99,
            metadata=replace(provider.profile.metadata, fetched_at=clock.now()),
        )
        return (await service.poll_rank_changes(scope))[0].events[0]

    return scenario()


def test_attempt_atomic_ownership_restart_manual_retry_and_cascade(
    daily_store, identity, provider, clock, tmp_path, run_async
):
    service, repository = daily_store
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        event = await seed_event(service, provider, clock, identity)
        other = replace(identity, user_id="other-synthetic")
        assert await service.claim_event(other, event.event_id) is None
        claims = await asyncio.gather(
            *(service.claim_event(identity, event.event_id) for _ in range(2))
        )
        assert claims.count(event) == 1 and claims.count(None) == 1
        assert not await repository.deliverable(scope)
        assert await repository.pending(scope) == (event,)
        reopened = SQLiteSubscriptionRepository(tmp_path / "subscriptions.sqlite3")
        await reopened.initialize()
        assert not await reopened.deliverable(scope)
        assert not await reopened.release(other, event.event_id)
        assert await service.retry_event(identity, event.event_id)
        assert await reopened.deliverable(scope) == (event,)
        assert await service.claim_event(identity, event.event_id) == event
        assert await service.acknowledge(identity, event.event_id)
        assert not await repository.pending(scope)
        assert not await service.retry_event(identity, event.event_id)
        assert await service.unsubscribe_all(other) == 0
        assert await service.unsubscribe_all(identity) == 1
        assert not await repository.scopes(identity.namespace)

    run_async(scenario())


@pytest.mark.parametrize("corrupt", [False, True])
def test_v1_migration_preserves_data_or_rolls_back(
    daily_store, identity, provider, clock, tmp_path, corrupt, run_async
):
    service, _repository = daily_store
    event = run_async(seed_event(service, provider, clock, identity))
    database = tmp_path / "subscriptions.sqlite3"
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("DROP TABLE subscription_attempts")
        connection.execute("ALTER TABLE subscription_events RENAME TO subscription_events_old")
        connection.execute("ALTER TABLE subscriptions RENAME TO subscriptions_old")
        connection.execute(
            "CREATE TABLE subscriptions (subscription_id TEXT NOT NULL PRIMARY KEY, "
            "namespace TEXT NOT NULL, platform TEXT NOT NULL, bot_id TEXT NOT NULL, "
            "user_id TEXT NOT NULL, destination TEXT NOT NULL, account_id INTEGER NOT NULL, "
            "source TEXT NOT NULL, kind TEXT NOT NULL, created_at TEXT NOT NULL, "
            "checkpoint TEXT NOT NULL, revision INTEGER NOT NULL, UNIQUE(namespace, platform, "
            "bot_id, user_id, destination, account_id, source, kind))"
        )
        connection.execute(
            "INSERT INTO subscriptions SELECT subscription_id, namespace, platform, bot_id, "
            "user_id, destination, account_id, source, kind, created_at, checkpoint, revision "
            "FROM subscriptions_old"
        )
        connection.execute(
            "CREATE TABLE subscription_events (sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
            "event_id TEXT NOT NULL UNIQUE, subscription_id TEXT NOT NULL, "
            "detected_at TEXT NOT NULL, payload TEXT NOT NULL, "
            "FOREIGN KEY(subscription_id) REFERENCES subscriptions(subscription_id) "
            "ON DELETE CASCADE)"
        )
        connection.execute(
            "INSERT INTO subscription_events SELECT sequence, event_id, subscription_id, "
            "detected_at, payload "
            "FROM subscription_events_old"
        )
        connection.execute("DROP TABLE subscription_events_old")
        connection.execute("DROP TABLE subscriptions_old")
        connection.execute("PRAGMA user_version = 1")
        for subscription_id, checkpoint in connection.execute(
            "SELECT subscription_id, checkpoint FROM subscriptions"
        ).fetchall():
            raw = json.loads(checkpoint)
            raw.pop("report_date")
            connection.execute(
                "UPDATE subscriptions SET checkpoint = ? WHERE subscription_id = ?",
                (json.dumps(raw), subscription_id),
            )
        if corrupt:
            connection.execute("UPDATE subscription_events SET payload = '{}' ")
    reopened = SQLiteSubscriptionRepository(database)
    if corrupt:
        with pytest.raises(SubscriptionRepositoryError):
            run_async(reopened.initialize())
        with closing(sqlite3.connect(database)) as connection:
            assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
            assert not connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name = 'subscription_attempts'"
            ).fetchone()
    else:
        run_async(reopened.initialize())
        assert run_async(reopened.pending(SubscriptionScope.for_identity(identity))) == (event,)
        assert run_async(reopened.claim(identity, event.event_id, clock.now())) == event


def test_scope_cursor_and_quota_abort_remaining_requests(
    daily_store, identity, provider, clock, run_async
):
    service, repository = daily_store

    async def scenario():
        await service.subscribe(identity, 123, "synthetic")
        second = replace(identity, bot_id="synthetic-bot-z")
        await service.subscribe(second, 123, "synthetic")
        scope = (await repository.scopes(identity.namespace))[0]
        assert (await repository.scopes(identity.namespace, after=scope))[0].bot_id == second.bot_id
        assert not await repository.scopes(
            identity.namespace, after=SubscriptionScope.for_identity(second)
        )
        with pytest.raises(ValidationError):
            await repository.scopes("other", after=scope)
        await service.subscribe(identity, 456, "synthetic")
        provider.failure = ProviderError(
            ProviderErrorCode.RATE_LIMITED, provider.source, retry_after_seconds=60
        )
        result = await service.poll_new_matches(scope)
        assert len(result) == 1 and len(provider.calls) == 1
        assert result[0].failure is provider.failure

    run_async(scenario())
