"""Synthetic providers only. No API token, recorded identity, or network is needed."""

import asyncio
import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest
import pytest_socket
from dota2forge_core import (
    AccountId,
    DataMetadata,
    DataSource,
    Dota2Service,
    MatchSummary,
    PlatformIdentity,
    PlayerProfile,
    RecentMatches,
)
from dota2forge_core.infrastructure.sqlite import SQLiteBindingRepository


@pytest.fixture
def run_async():
    # asyncio needs its local wakeup socket before starting. No application code
    # runs in this narrow window; sockets/DNS are blocked before any coroutine.
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
def identity():
    return PlatformIdentity("test-deployment", "test-chat", "synthetic-bot", "synthetic-user")


@pytest.fixture
def metadata():
    return DataMetadata(DataSource.FIXTURE, datetime.fromisoformat("2026-09-30T00:00:00+00:00"))


@pytest.fixture
def clock(metadata):
    class FixedClock:
        instant = metadata.fetched_at

        def now(self):
            return self.instant

    return FixedClock()


@pytest.fixture
def repository(tmp_path, run_async):
    repository = SQLiteBindingRepository(tmp_path / "bindings.sqlite3")
    run_async(repository.initialize())
    return repository


@pytest.fixture
def provider():
    raw = json.loads((Path(__file__).parent / "fixtures/public-player.json").read_text("utf-8"))
    assert raw["fixture_kind"] == "synthetic-normalized-v1"
    metadata = DataMetadata(
        source=DataSource(raw["source"]),
        fetched_at=datetime.fromisoformat(raw["fetched_at"]),
        observed_at=None,
        patch=None,
    )
    account_id = AccountId(raw["account_id"])
    profile = PlayerProfile(account_id, metadata, **raw["player"])
    matches = tuple(
        MatchSummary(
            **{key: value for key, value in item.items() if key != "started_at"},
            account_id=account_id,
            started_at=datetime.fromisoformat(item["started_at"]),
            metadata=metadata,
        )
        for item in raw["matches"]
    )

    class FixtureProvider:
        source = DataSource.FIXTURE

        def __init__(self):
            self.profile = profile
            self.recent = RecentMatches(account_id, matches, metadata)
            self.failure = None
            self.calls = []

        async def get_player(self, target):
            self.calls.append(("player", target))
            if self.failure is not None:
                raise self.failure
            return self.profile

        async def get_recent_matches(self, target, limit):
            self.calls.append(("recent", target, limit))
            if self.failure is not None:
                raise self.failure
            return replace(self.recent, matches=self.recent.matches[:limit])

    return FixtureProvider()


@pytest.fixture
def service(repository, provider, clock):
    return Dota2Service(repository, provider, provider, clock)
