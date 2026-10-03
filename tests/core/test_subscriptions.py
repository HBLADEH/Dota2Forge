import asyncio
from dataclasses import replace
from datetime import timedelta

import pytest
from dota2forge_core import (
    AccountId,
    DataMetadata,
    DataSource,
    MatchSummary,
    ProviderError,
    ProviderErrorCode,
    RankChange,
    RecentMatches,
    SQLiteSubscriptionRepository,
    SubscriptionKind,
    SubscriptionPollState,
    SubscriptionScope,
    SubscriptionService,
    ValidationError,
)


@pytest.fixture
def subscriptions(tmp_path, provider, clock, run_async):
    repository = SQLiteSubscriptionRepository(tmp_path / "subscriptions.sqlite3")
    run_async(repository.initialize())
    return SubscriptionService(repository, provider, provider, clock), repository


def observe(provider, clock, rows):
    metadata = DataMetadata(provider.source, clock.now())
    start = provider.profile.metadata.fetched_at - timedelta(hours=1)
    matches = tuple(
        MatchSummary(
            match_id,
            provider.profile.account_id,
            start + timedelta(seconds=offset),
            metadata,
            kills=0,
            is_win=outcome,
        )
        for match_id, offset, outcome in sorted(
            rows, key=lambda row: (row[1], row[0]), reverse=True
        )
    )
    provider.recent = RecentMatches(provider.profile.account_id, matches, metadata)


def test_subscription_idempotence_restart_owner_and_binding_snapshot(
    subscriptions, service, tmp_path, identity, provider, clock, run_async
):
    subscriptions_service, repository = subscriptions

    async def scenario():
        binding = await service.bind_account(identity, provider.profile.account_id.value)
        first = await subscriptions_service.subscribe(
            identity, binding.account_id.value, "group:synthetic"
        )
        clock.instant += timedelta(seconds=1)
        assert (
            await subscriptions_service.subscribe(
                identity, binding.account_id.to_steam_id64().value, "group:synthetic"
            )
            == first
        )
        await service.bind_account(identity, 456, replace=True)
        await service.unbind_account(identity)
        assert (await subscriptions_service.list_subscriptions(identity))[
            0
        ].key.account_id == binding.account_id
        reopened = SQLiteSubscriptionRepository(tmp_path / "subscriptions.sqlite3")
        await reopened.initialize()
        assert await reopened.list(SubscriptionScope.for_identity(identity)) == (first,)
        other = replace(identity, user_id="other-synthetic-user")
        assert not await subscriptions_service.list_subscriptions(other)
        assert not await subscriptions_service.unsubscribe(other, first.subscription_id)
        assert await subscriptions_service.unsubscribe(identity, first.subscription_id)
        assert not await subscriptions_service.unsubscribe(identity, first.subscription_id)
        new = await subscriptions_service.subscribe(
            identity, binding.account_id.value, "group:synthetic"
        )
        assert new.subscription_id != first.subscription_id
        assert not provider.calls
        assert await repository.list(SubscriptionScope.for_identity(identity)) == (new,)

    run_async(scenario())


def test_new_matches_baseline_oldest_first_durable_until_delivery_ack(
    subscriptions, identity, provider, clock, tmp_path, run_async
):
    service, repository = subscriptions
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        observe(provider, clock, [(8, 80, True), (7, 70, False)])
        subscription = await service.subscribe(
            identity, provider.profile.account_id.value, "group:synthetic"
        )
        assert (await service.poll_new_matches(scope))[0].state == SubscriptionPollState.BASELINED
        assert not await service.pending_events(identity)
        clock.instant += timedelta(seconds=1)
        observe(provider, clock, [(10, 100, False), (9, 90, True), (8, 80, True)])
        result = (await service.poll_new_matches(scope))[0]
        assert result.state == SubscriptionPollState.EVENTS
        assert not result.coverage_gap
        assert [event.payload.match_id for event in result.events] == [9, 10]
        assert result.events[1].payload.is_win is False
        assert result.events[1].payload.kills == 0
        assert result.events[1].payload.duration_seconds is None
        assert result.events[1].payload.metadata == provider.recent.metadata
        pending = await service.pending_events(identity)
        assert pending == result.events
        assert pending[0].subscription_id == subscription.subscription_id

        async def failed_sender(event):
            raise RuntimeError("synthetic delivery failure")

        with pytest.raises(RuntimeError, match="synthetic delivery failure"):
            await failed_sender(pending[0])
        assert await service.pending_events(identity) == pending
        restarted_repository = SQLiteSubscriptionRepository(tmp_path / "subscriptions.sqlite3")
        await restarted_repository.initialize()
        restarted = SubscriptionService(restarted_repository, provider, provider, clock)
        assert await restarted.pending_events(identity) == pending
        assert (await restarted.poll_new_matches(scope))[0].state == SubscriptionPollState.UNCHANGED
        other = replace(identity, user_id="other-synthetic-user")
        assert not await restarted.acknowledge(other, pending[0].event_id)
        assert await restarted.acknowledge(identity, pending[0].event_id)
        assert not await restarted.acknowledge(identity, pending[0].event_id)
        assert await restarted.pending_events(identity, limit=1) == pending[1:]
        assert await restarted.unsubscribe(identity, subscription.subscription_id)
        assert not await repository.pending(scope)

    run_async(scenario())


def test_poll_shares_account_observation_and_isolates_scopes(
    subscriptions, identity, provider, clock, run_async
):
    service, repository = subscriptions
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        observe(provider, clock, [(8, 80, True)])
        for owner, destination in [
            (identity, "group:one"),
            (identity, "group:two"),
            (replace(identity, user_id="another-user"), "group:one"),
            (replace(identity, bot_id="another-bot"), "group:one"),
        ]:
            await service.subscribe(owner, provider.profile.account_id.value, destination)
        first = await service.poll_new_matches(scope)
        assert len(first) == 3
        assert len(provider.calls) == 1
        clock.instant += timedelta(seconds=1)
        observe(provider, clock, [(9, 90, True), (8, 80, True)])
        results = await service.poll_new_matches(scope)
        assert len(provider.calls) == 2
        events = await repository.pending(scope)
        assert len(events) == 3
        assert len({event.event_id for event in events}) == 3
        assert len(await service.pending_events(identity)) == 2
        assert len({result.subscription.subscription_id for result in results}) == 3
        other = SubscriptionScope.for_identity(replace(identity, bot_id="another-bot"))
        assert (await service.poll_new_matches(other))[0].state == SubscriptionPollState.BASELINED
        assert not await repository.pending(other)

    run_async(scenario())


def test_paginated_subscription_polling_is_finite(
    subscriptions, identity, provider, clock, run_async
):
    service, repository = subscriptions
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        for index in range(4):
            await service.subscribe(identity, provider.profile.account_id.value, f"group:{index}")
        first = await service.poll_new_matches(scope, limit=2, match_limit=1)
        last = first[-1].subscription.subscription_id
        second = await service.poll_new_matches(scope, limit=2, after_id=last, match_limit=1)
        assert len(first) == len(second) == 2
        assert len(provider.calls) == 2
        assert all(call[2] == 1 for call in provider.calls)
        ids = [item.subscription.subscription_id for item in (*first, *second)]
        assert ids == sorted(set(ids))
        assert await service.poll_new_matches(scope, after_id=ids[-1]) == ()
        assert len(await repository.list(scope)) == 4

    run_async(scenario())


def test_rank_changes_known_baseline_missing_not_zero_and_decreases(
    subscriptions, identity, provider, clock, run_async
):
    service, repository = subscriptions
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        await service.subscribe(
            identity,
            provider.profile.account_id.value,
            "direct:synthetic",
            kind=SubscriptionKind.RANK_CHANGE,
        )
        for rank, expected in [
            (None, SubscriptionPollState.UNKNOWN),
            (0, SubscriptionPollState.BASELINED),
            (65, SubscriptionPollState.EVENTS),
            (64, SubscriptionPollState.EVENTS),
            (None, SubscriptionPollState.UNKNOWN),
            (64, SubscriptionPollState.UNCHANGED),
            (66, SubscriptionPollState.EVENTS),
        ]:
            clock.instant += timedelta(seconds=1)
            provider.profile = replace(
                provider.profile,
                rank_tier=rank,
                metadata=DataMetadata(provider.source, clock.now()),
            )
            result = (await service.poll_rank_changes(scope))[0]
            assert result.state == expected
            if rank is None and result.subscription.checkpoint.rank_tier is not None:
                assert result.subscription.checkpoint.rank_tier == 64
        events = await repository.pending(scope)
        assert all(isinstance(event.payload, RankChange) for event in events)
        assert [(event.payload.previous_rank, event.payload.current_rank) for event in events] == [
            (0, 65),
            (65, 64),
            (64, 66),
        ]
        assert not await service.poll_new_matches(scope)

    run_async(scenario())


@pytest.mark.parametrize("code", list(ProviderErrorCode))
@pytest.mark.parametrize(
    "kind",
    [SubscriptionKind.NEW_MATCH, SubscriptionKind.RANK_CHANGE, SubscriptionKind.DAILY_REPORT],
)
def test_provider_failure_is_classified_without_mutation(
    subscriptions, identity, provider, clock, code, kind, run_async
):
    service, repository = subscriptions
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        first = await service.subscribe(
            identity, provider.profile.account_id.value, "group:synthetic", kind=kind
        )
        provider.failure = ProviderError(
            code,
            provider.source,
            retry_after_seconds=17 if code == ProviderErrorCode.RATE_LIMITED else None,
        )
        poll = (
            service.poll_new_matches
            if kind == SubscriptionKind.NEW_MATCH
            else service.poll_rank_changes
        )
        if kind == SubscriptionKind.DAILY_REPORT:
            report_date = clock.now().date()
            clock.instant += timedelta(days=1)
            result = (await service.poll_daily_reports(scope, report_date))[0]
        else:
            result = (await poll(scope))[0]
        assert result.state == SubscriptionPollState.FAILED
        assert result.failure is provider.failure
        assert await repository.list(scope) == (first,)
        assert not await repository.pending(scope)
        assert len(provider.calls) == 1

    run_async(scenario())


@pytest.mark.parametrize(
    "failure", [RuntimeError("synthetic programming error"), asyncio.CancelledError()]
)
def test_programming_errors_and_cancellation_propagate(
    subscriptions, identity, provider, failure, run_async
):
    service, repository = subscriptions
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        first = await service.subscribe(
            identity, provider.profile.account_id.value, "group:synthetic"
        )
        provider.failure = failure
        with pytest.raises(type(failure)):
            await service.poll_new_matches(scope)
        assert await repository.list(scope) == (first,)
        assert not await repository.pending(scope)

    run_async(scenario())


@pytest.mark.parametrize("invalid", ["type", "account", "source", "limit", "id"])
def test_bad_provider_observations_are_not_events(
    subscriptions, identity, provider, monkeypatch, invalid, run_async
):
    service, repository = subscriptions
    scope = SubscriptionScope.for_identity(identity)
    observation = provider.recent
    if invalid == "type":
        observation = provider.profile
    elif invalid == "account":
        observation = replace(observation, account_id=AccountId(456), matches=())
    elif invalid == "source":
        observation = replace(
            observation,
            matches=(),
            metadata=replace(observation.metadata, source=DataSource.STRATZ),
        )
    elif invalid == "id":
        observation = replace(
            observation, matches=(replace(observation.matches[0], match_id=2**63),)
        )

    async def get_recent(account, limit):
        return observation

    monkeypatch.setattr(provider, "get_recent_matches", get_recent)

    async def scenario():
        first = await service.subscribe(
            identity, provider.profile.account_id.value, "group:synthetic"
        )
        result = (await service.poll_new_matches(scope, match_limit=1))[0]
        assert result.failure.code == ProviderErrorCode.INVALID_RESPONSE
        assert await repository.list(scope) == (first,)

    run_async(scenario())


def test_changed_provider_source_never_silently_rebases(
    subscriptions, identity, provider, run_async
):
    service, repository = subscriptions
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        first = await service.subscribe(
            identity, provider.profile.account_id.value, "group:synthetic"
        )
        provider.source = DataSource.STRATZ
        result = (await service.poll_new_matches(scope))[0]
        assert result.failure.source == first.key.source
        assert result.failure.code == ProviderErrorCode.INVALID_RESPONSE
        assert not provider.calls
        assert await repository.list(scope) == (first,)

    run_async(scenario())


@pytest.mark.parametrize("invalid", ["type", "account", "source", "error_source"])
def test_bad_rank_observations_are_classified(
    subscriptions, identity, provider, monkeypatch, invalid, run_async
):
    service, repository = subscriptions
    scope = SubscriptionScope.for_identity(identity)
    observation = provider.profile
    if invalid == "type":
        observation = provider.recent
    elif invalid == "account":
        observation = replace(observation, account_id=AccountId(456))
    elif invalid == "source":
        observation = replace(
            observation, metadata=replace(observation.metadata, source=DataSource.STRATZ)
        )

    async def get_player(account):
        if invalid == "error_source":
            raise ProviderError(ProviderErrorCode.PRIVATE, DataSource.STRATZ)
        return observation

    monkeypatch.setattr(provider, "get_player", get_player)

    async def scenario():
        subscription = await service.subscribe(
            identity,
            provider.profile.account_id.value,
            "group:synthetic",
            kind=SubscriptionKind.RANK_CHANGE,
        )
        result = (await service.poll_rank_changes(scope))[0]
        assert result.failure.code == ProviderErrorCode.INVALID_RESPONSE
        assert result.failure.source == DataSource.FIXTURE
        assert await repository.list(scope) == (subscription,)

    run_async(scenario())


def test_empty_unknown_gap_and_regression_preserve_frontier(
    subscriptions, identity, provider, clock, run_async
):
    service, repository = subscriptions
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        await service.subscribe(identity, provider.profile.account_id.value, "group:synthetic")
        observe(provider, clock, [])
        assert (await service.poll_new_matches(scope))[0].state == SubscriptionPollState.EMPTY
        observe(provider, clock, [(8, 80, None)])
        assert (await service.poll_new_matches(scope))[0].state == SubscriptionPollState.UNKNOWN
        observe(provider, clock, [(8, 80, False)])
        baseline = (await service.poll_new_matches(scope))[0]
        assert baseline.state == SubscriptionPollState.BASELINED
        observe(provider, clock, [])
        empty = (await service.poll_new_matches(scope))[0]
        assert empty.subscription.checkpoint.match_ids == (8,)
        observe(provider, clock, [(10, 100, True), (9, 90, None), (8, 80, False)])
        unknown = (await service.poll_new_matches(scope))[0]
        assert unknown.state == SubscriptionPollState.UNKNOWN
        assert unknown.subscription.checkpoint.match_ids == (8,)
        assert not await repository.pending(scope)
        observe(provider, clock, [(10, 100, True), (9, 90, False), (8, 80, False)])
        completed = (await service.poll_new_matches(scope))[0]
        assert [event.payload.match_id for event in completed.events] == [9, 10]
        observe(provider, clock, [(20, 200, True)])
        gap = (await service.poll_new_matches(scope))[0]
        assert gap.coverage_gap is True
        assert gap.events[0].payload.match_id == 20
        before = await repository.list(scope)
        observe(provider, clock, [(19, 190, True)])
        assert (await service.poll_new_matches(scope))[0].state == SubscriptionPollState.STALE
        assert await repository.list(scope) == before

    run_async(scenario())


def test_equal_time_deduplicates_by_id_not_numeric_max(
    subscriptions, identity, provider, clock, run_async
):
    service, _ = subscriptions
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        await service.subscribe(identity, provider.profile.account_id.value, "group:synthetic")
        observe(provider, clock, [(50, 50, True)])
        await service.poll_new_matches(scope)
        observe(provider, clock, [(50, 50, True), (1, 50, False)])
        result = (await service.poll_new_matches(scope))[0]
        assert [event.payload.match_id for event in result.events] == [1]
        assert result.subscription.checkpoint.match_ids == (1, 50)
        observe(provider, clock, [(1, 50, False)])
        assert (await service.poll_new_matches(scope))[0].state == SubscriptionPollState.UNCHANGED
        assert len(await service.pending_events(identity)) == 1

    run_async(scenario())


def test_old_fetch_is_stale_even_with_new_match_ids(
    subscriptions, identity, provider, clock, run_async
):
    service, repository = subscriptions
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        await service.subscribe(identity, provider.profile.account_id.value, "group:synthetic")
        observe(provider, clock, [(8, 80, True)])
        await service.poll_new_matches(scope)
        before = await repository.list(scope)
        clock.instant -= timedelta(seconds=1)
        observe(provider, clock, [(9, 90, True), (8, 80, True)])
        assert (await service.poll_new_matches(scope))[0].state == SubscriptionPollState.STALE
        assert await repository.list(scope) == before
        assert not await repository.pending(scope)

    run_async(scenario())


def test_match_payload_keeps_its_own_fetch_and_observation_times(
    subscriptions, identity, provider, clock, run_async
):
    service, repository = subscriptions
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        await service.subscribe(identity, provider.profile.account_id.value, "group:synthetic")
        observe(provider, clock, [(8, 80, True)])
        await service.poll_new_matches(scope)
        original = provider.recent.metadata
        clock.instant += timedelta(seconds=2)
        observe(provider, clock, [(9, 90, True), (8, 80, True)])
        payload_metadata = replace(original, observed_at=original.fetched_at - timedelta(minutes=1))
        first, second = provider.recent.matches
        provider.recent = replace(
            provider.recent, matches=(replace(first, metadata=payload_metadata), second)
        )
        result = (await service.poll_new_matches(scope))[0]
        assert result.state == SubscriptionPollState.EVENTS
        assert result.subscription.checkpoint.fetched_at == clock.now()
        assert result.events[0].payload.metadata == payload_metadata
        assert (await repository.pending(scope))[0].payload.metadata == payload_metadata

    run_async(scenario())


def test_concurrent_poll_commits_only_one_event(
    subscriptions, identity, provider, clock, monkeypatch, run_async
):
    service, repository = subscriptions
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        await service.subscribe(identity, provider.profile.account_id.value, "group:synthetic")
        observe(provider, clock, [(8, 80, True)])
        await service.poll_new_matches(scope)
        observe(provider, clock, [(9, 90, True), (8, 80, True)])
        ready = asyncio.Event()
        count = 0

        async def get_recent(account, limit):
            nonlocal count
            count += 1
            if count == 2:
                ready.set()
            await ready.wait()
            return provider.recent

        monkeypatch.setattr(provider, "get_recent_matches", get_recent)
        results = await asyncio.gather(
            service.poll_new_matches(scope), service.poll_new_matches(scope)
        )
        assert {result[0].state for result in results} == {
            SubscriptionPollState.EVENTS,
            SubscriptionPollState.STALE,
        }
        assert len(await repository.pending(scope)) == 1

    run_async(scenario())


def test_unsubscribe_during_query_cannot_resurrect_or_send_old_subscription(
    subscriptions, identity, provider, clock, monkeypatch, run_async
):
    service, repository = subscriptions
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        old = await service.subscribe(
            identity, provider.profile.account_id.value, "group:synthetic"
        )
        observe(provider, clock, [(8, 80, True)])
        await service.poll_new_matches(scope)
        observe(provider, clock, [(9, 90, True), (8, 80, True)])
        entered, release = asyncio.Event(), asyncio.Event()

        async def get_recent(account, limit):
            entered.set()
            await release.wait()
            return provider.recent

        monkeypatch.setattr(provider, "get_recent_matches", get_recent)
        task = asyncio.create_task(service.poll_new_matches(scope))
        await entered.wait()
        assert await service.unsubscribe(identity, old.subscription_id)
        new = await service.subscribe(
            identity, provider.profile.account_id.value, "group:synthetic"
        )
        release.set()
        assert (await task)[0].state == SubscriptionPollState.STALE
        assert new.subscription_id != old.subscription_id
        assert await repository.list(scope) == (new,)
        assert not await repository.pending(scope)

    run_async(scenario())


def test_cancel_after_commit_does_not_lose_outbox(
    subscriptions, identity, provider, clock, monkeypatch, run_async
):
    service, repository = subscriptions
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        await service.subscribe(identity, provider.profile.account_id.value, "group:synthetic")
        observe(provider, clock, [(8, 80, True)])
        await service.poll_new_matches(scope)
        observe(provider, clock, [(9, 90, True), (8, 80, True)])
        committed = asyncio.Event()
        original = repository.commit

        async def commit(previous, checkpoint, events):
            result = await original(previous, checkpoint, events)
            committed.set()
            await asyncio.Future()
            return result

        monkeypatch.setattr(repository, "commit", commit)
        task = asyncio.create_task(service.poll_new_matches(scope))
        await committed.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        pending = await repository.pending(scope)
        assert len(pending) == 1
        assert pending[0].payload.match_id == 9

    run_async(scenario())


@pytest.mark.parametrize("limit", [0, 101, True, 1.5, "1"])
def test_bad_poll_limits_fail_before_io(subscriptions, identity, provider, limit, run_async):
    service, _ = subscriptions
    scope = SubscriptionScope.for_identity(identity)
    with pytest.raises(ValidationError):
        run_async(service.poll_new_matches(scope, match_limit=limit))
    with pytest.raises(ValidationError):
        run_async(service.poll_rank_changes(scope, limit=limit))
    assert not provider.calls
