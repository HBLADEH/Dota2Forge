"""Subscription batches own rendering and delivery without querying providers."""

import asyncio
from datetime import UTC, datetime

import httpx
import pytest
from dota2forge_core import (
    AccountId,
    DataMetadata,
    DataSource,
    DeliveryOutcome,
    MatchAnalysisUnavailable,
    MatchDetail,
    MatchId,
    MatchParticipant,
    MatchReport,
    PlatformIdentity,
    SubscriptionEvent,
    SubscriptionKey,
    SubscriptionKind,
)
from dota2forge_renderer import ImageArtifact, MatchReportCard, RenderError
from Dota2UID.replies import ImageReply, TextReply
from Dota2UID.runtime import Runtime


def match_event():
    metadata = DataMetadata(DataSource.STRATZ, datetime(2026, 10, 12, tzinfo=UTC))
    match_id = MatchId(1001)
    players = tuple(
        MatchParticipant(
            player_slot=i if i < 5 else 128 + i - 5,
            account_id=AccountId(123 + i),
            display_name=f"合成参赛者{i}",
            is_anonymous=False,
            is_radiant=i < 5,
            hero_id=2,
            kills=1,
            deaths=0,
            assists=1,
            gold_per_minute=500,
        )
        for i in range(10)
    )
    report = MatchReport(
        match_id,
        metadata,
        AccountId(123),
        None,
        MatchDetail(
            match_id, metadata, duration_seconds=1800, did_radiant_win=True, players=players
        ),
        MatchAnalysisUnavailable(match_id, metadata),
    )
    key = SubscriptionKey(
        PlatformIdentity("synthetic-deployment", "qq", "synthetic-bot", "synthetic-user"),
        "synthetic-route",
        AccountId(123),
        DataSource.STRATZ,
        SubscriptionKind.NEW_MATCH,
    )
    return SubscriptionEvent("a" * 32, "b" * 32, key, metadata.fetched_at, report)


class Renderer:
    def __init__(self, failure=None):
        self.cards = []
        self.failure = failure
        self.closed = False

    async def render(self, card):
        self.cards.append(card)
        if self.failure is not None and len(self.cards) == 2:
            raise self.failure
        return ImageArtifact(b"\x89PNG\r\n\x1a\n", 1600, 1)

    async def close(self):
        self.closed = True


class Worker:
    enabled = True

    def __init__(self, event):
        self.event = event
        self.outcome = None
        self.active = None

    async def tick(self, send):
        self.active = asyncio.current_task()
        try:
            self.outcome = await send(self.event, "legacy text")
        finally:
            self.active = None

    async def close(self):
        if self.active is not None:
            self.active.cancel()
            await asyncio.gather(self.active, return_exceptions=True)


async def start(config_path, renderer, mode="image"):
    config_path.write_text(
        config_path.read_text("utf-8").replace('reply_mode="text"', f'reply_mode="{mode}"'),
        "utf-8",
    )
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: pytest.fail("provider called"))
    )
    runtime = Runtime(config_path, client_factory=lambda: client, renderer_factory=lambda: renderer)
    await runtime.start()
    await runtime._subscriptions.close()
    runtime._subscriptions = Worker(match_event())
    return runtime


@pytest.mark.parametrize(
    "mode,failure", [("image", None), ("text", None), ("image", RenderError())]
)
def test_subscription_prepares_one_complete_batch_or_full_text(
    config_path, run_async, mode, failure
):
    async def scenario():
        renderer = Renderer(failure)
        runtime = await start(config_path, renderer, mode)
        batches = []

        async def send(event, replies):
            batches.append((event, replies))
            if mode == "image" and failure is None:
                assert len(renderer.cards) == 3
            return DeliveryOutcome.UNCERTAIN

        await runtime.poll_subscriptions(send)
        assert len(batches) == 1
        event, replies = batches[0]
        assert runtime._subscriptions.outcome == DeliveryOutcome.UNCERTAIN
        if mode == "image" and failure is None:
            assert len(replies) == 3 and all(isinstance(reply, ImageReply) for reply in replies)
            assert all(isinstance(card, MatchReportCard) for card in renderer.cards)
            assert all(card.subscription_event == event for card in renderer.cards)
        else:
            assert replies and all(isinstance(reply, TextReply) for reply in replies)
            text = "\n".join(reply.text for reply in replies)
            assert event.event_id in text and "订阅玩家" in text
            assert "非官方" in text and "有限来源观察" in text
            assert "K/D/A" in text and "合成参赛者9" in text
            assert all(len(reply.text) <= 1400 for reply in replies)
            assert len(renderer.cards) == (2 if failure is not None else 0)
        await runtime.close()
        assert runtime.client_closed

    run_async(scenario())


def test_subscription_program_error_never_falls_back_or_sends(config_path, run_async):
    async def scenario():
        runtime = await start(config_path, Renderer(TypeError("synthetic bug")))

        async def send(_event, _replies):
            pytest.fail("unexpected send")

        with pytest.raises(TypeError):
            await runtime.poll_subscriptions(send)
        await runtime.close()

    run_async(scenario())


def test_subscription_asset_swap_waits_for_whole_batch_send(
    config_path, tmp_path, monkeypatch, run_async
):
    async def scenario():
        old, candidate = Renderer(), Renderer()
        runtime = await start(config_path, old)
        entered, release, committed = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def send(_event, _replies):
            entered.set()
            await release.wait()
            return DeliveryOutcome.ACCEPTED

        async def commit():
            committed.set()

        monkeypatch.setattr("Dota2UID.runtime.AsyncRenderer", lambda _: candidate)
        poll = asyncio.create_task(runtime.poll_subscriptions(send))
        await entered.wait()
        activation = asyncio.create_task(runtime._activate_assets(tmp_path, commit))
        await asyncio.sleep(0)
        assert not committed.is_set() and not old.closed
        release.set()
        await asyncio.gather(poll, activation)
        assert committed.is_set() and old.closed and runtime._renderer is candidate
        await runtime.close()
        assert candidate.closed

    run_async(scenario())


def test_subscription_shutdown_cancels_send_and_drains_before_renderer_close(
    config_path, run_async
):
    async def scenario():
        renderer = Renderer()
        runtime = await start(config_path, renderer)
        entered, cleanup, release = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def send(_event, _replies):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleanup.set()
                await release.wait()
                assert not renderer.closed

        poll = asyncio.create_task(runtime.poll_subscriptions(send))
        await entered.wait()
        close = asyncio.create_task(runtime.close())
        await cleanup.wait()
        assert not renderer.closed and not close.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await poll
        await close
        assert renderer.closed and runtime.client_closed

    run_async(scenario())
