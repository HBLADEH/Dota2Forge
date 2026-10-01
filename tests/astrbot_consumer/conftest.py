"""Synthetic Core fixtures for AstrBot-neutral consumer tests."""

import asyncio
from datetime import UTC, datetime

import pytest
import pytest_socket
from dota2forge_core import (
    AccountId,
    DataMetadata,
    DataSource,
    MatchSummary,
    PlatformIdentity,
    PlayerProfile,
    RecentMatches,
)
from dota2forge_core.infrastructure.sqlite import SQLiteBindingRepository


@pytest.fixture
def run_async():
    pytest_socket.enable_socket()
    try:
        loop = asyncio.new_event_loop()
    finally:
        pytest_socket.disable_socket()
    try:
        yield loop.run_until_complete
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())
        loop.close()


@pytest.fixture
def repository(tmp_path, run_async):
    value = SQLiteBindingRepository(tmp_path / "bindings.sqlite3")
    run_async(value.initialize())
    return value


@pytest.fixture
def identity():
    return PlatformIdentity("astrbot-test", "qq", "bot", "user")


@pytest.fixture
def clock():
    class FixedClock:
        def now(self):
            return datetime(2026, 10, 1, tzinfo=UTC)

    return FixedClock()


@pytest.fixture
def provider():
    metadata = DataMetadata(DataSource.FIXTURE, datetime(2026, 10, 1, tzinfo=UTC))
    account = AccountId(123)
    profile = PlayerProfile(account, metadata, "Synthetic", 51)
    match = MatchSummary(
        1, account, metadata.fetched_at, metadata, hero_id=2, kills=0, is_win=False
    )
    recent = RecentMatches(account, (match,), metadata)

    class FixtureProvider:
        source = DataSource.FIXTURE

        def __init__(self):
            self.calls = []

        async def get_player(self, target):
            self.calls.append(("player", target))
            return profile

        async def get_recent_matches(self, target, limit):
            self.calls.append(("recent", target, limit))
            return RecentMatches(account, recent.matches[:limit], metadata)

        async def get_match_detail(self, match_id):
            from dota2forge_core import MatchDetailUnavailable

            self.calls.append(("detail", match_id))
            return MatchDetailUnavailable(match_id, metadata)

    return FixtureProvider()
