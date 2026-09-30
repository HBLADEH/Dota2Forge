import asyncio
import socket
from dataclasses import replace
from datetime import timedelta

import pytest
from dota2forge_core import (
    AccountId,
    BindingConflictError,
    BindingNotFoundError,
    DataSource,
    Dota2Service,
    ProviderError,
    ProviderErrorCode,
    ValidationError,
)
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure.sqlite import SQLiteBindingRepository
from pytest_socket import SocketBlockedError


def test_complete_offline_user_journey(service, identity, provider, clock, tmp_path, run_async):
    async def journey():
        with pytest.raises(BindingNotFoundError):
            await service.get_player(identity)
        assert provider.calls == []
        binding = await service.bind_account(identity, str(AccountId(123).to_steam_id64().value))
        assert binding.account_id == AccountId(123)
        assert provider.calls == []  # Binding is not an external ownership check.
        clock.instant += timedelta(days=1)
        assert await service.bind_account(identity, "123") == binding

        restarted_repo = SQLiteBindingRepository(tmp_path / "bindings.sqlite3")
        await restarted_repo.initialize()
        restarted = Dota2Service(restarted_repo, provider, provider, clock)
        assert (await restarted.get_player(identity)).display_name == "Synthetic Player"
        recent = await restarted.get_recent_matches(identity, limit=1)
        assert [match.match_id for match in recent.matches] == [1002]
        assert recent.metadata.source == DataSource.FIXTURE
        assert recent.matches[0].gold_per_minute is None
        assert provider.calls == [("player", AccountId(123)), ("recent", AccountId(123), 1)]
        with pytest.raises(BindingConflictError):
            await restarted.bind_account(identity, "456")
        assert (
            await restarted.bind_account(identity, "456", replace=True)
        ).account_id == AccountId(456)
        assert await restarted.unbind_account(identity)
        assert not await restarted.unbind_account(identity)
        with pytest.raises(BindingNotFoundError):
            await restarted.get_recent_matches(identity)

    run_async(journey())


def test_explicit_query_works_without_binding_and_does_not_write(
    service, repository, provider, identity, run_async
):
    result = run_async(service.get_player(identity, account_id=AccountId(123)))
    recent = run_async(service.get_recent_matches(identity, account_id=AccountId(123)))
    assert result == provider.profile
    assert recent == provider.recent
    assert run_async(repository.get(identity)) is None


@pytest.mark.parametrize("code", list(ProviderErrorCode))
@pytest.mark.parametrize("operation", ["get_player", "get_recent_matches"])
def test_provider_failures_propagate_without_fallback_retry_or_binding_loss(
    service, repository, identity, provider, run_async, code, operation
):
    binding = run_async(service.bind_account(identity, "123"))
    failure = ProviderError(
        code,
        DataSource.FIXTURE,
        retry_after_seconds=12 if code == ProviderErrorCode.RATE_LIMITED else None,
    )
    provider.failure = failure
    with pytest.raises(ProviderError) as caught:
        run_async(getattr(service, operation)(identity))
    assert caught.value is failure
    assert run_async(repository.get(identity)) == binding
    assert len(provider.calls) == 1


def test_valid_empty_result_keeps_source_and_observation_time(
    service, identity, provider, run_async
):
    provider.recent = replace(provider.recent, matches=())
    result = run_async(service.get_recent_matches(identity, account_id=AccountId(123)))
    assert result.matches == ()
    assert result.metadata == provider.recent.metadata


@pytest.mark.parametrize("limit", [0, -1, 101, True, 1.5, "1", None])
def test_invalid_limits_do_not_access_provider(service, identity, provider, run_async, limit):
    with pytest.raises(ValidationError):
        run_async(service.get_recent_matches(identity, limit, account_id=AccountId(123)))
    assert provider.calls == []


@pytest.mark.parametrize("operation", ["get_player", "get_recent_matches"])
def test_mismatched_player_and_source_are_invalid_response(
    service, identity, provider, run_async, operation
):
    target = "profile" if operation == "get_player" else "recent"
    original = getattr(provider, target)
    if operation == "get_recent_matches":
        original = replace(original, matches=())
    variants = [
        None,
        replace(original, account_id=AccountId(456)),
        replace(original, metadata=replace(original.metadata, source=DataSource.STRATZ)),
    ]
    for result in variants:

        async def malformed(*args, response=result):
            return response

        setattr(provider, operation, malformed)
        with pytest.raises(ProviderError) as caught:
            run_async(getattr(service, operation)(identity, account_id=AccountId(123)))
        assert caught.value.code == ProviderErrorCode.INVALID_RESPONSE


def test_provider_cannot_exceed_requested_limit(service, identity, provider, run_async):
    async def ignoring_limit(*args):
        return provider.recent

    provider.get_recent_matches = ignoring_limit
    with pytest.raises(ProviderError) as caught:
        run_async(service.get_recent_matches(identity, limit=1, account_id=AccountId(123)))
    assert caught.value.code == ProviderErrorCode.INVALID_RESPONSE


def test_invalid_use_case_inputs_do_not_write_or_call_provider(
    service, repository, identity, provider, run_async
):
    with pytest.raises(ValidationError):
        run_async(service.bind_account(identity, "123", replace="yes"))
    with pytest.raises(ValidationError):
        run_async(service.bind_account(None, "123"))
    with pytest.raises(ValidationError):
        run_async(service.get_player(None, account_id=AccountId(123)))
    with pytest.raises(ValidationError):
        run_async(service.get_player(identity, account_id="123"))
    assert run_async(repository.get(identity)) is None
    assert provider.calls == []


def test_cancellation_and_unexpected_bugs_are_not_swallowed(service, provider, identity, run_async):
    for failure in (asyncio.CancelledError(), RuntimeError("synthetic bug")):
        provider.failure = failure
        with pytest.raises(type(failure)) as caught:
            run_async(service.get_player(identity, account_id=AccountId(123)))
        assert caught.value is failure


def test_sockets_remain_blocked_in_coroutines_and_sqlite_workers(run_async):
    def blocked():
        with pytest.warns(UserWarning, match="socket.socket"), pytest.raises(SocketBlockedError):
            socket.socket()

    async def verify():
        blocked()
        await asyncio.to_thread(blocked)

    run_async(verify())


def test_system_clock_returns_aware_utc():
    assert SystemClock().now().utcoffset() == timedelta(0)
