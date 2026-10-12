"""Subscription batches use durable data and the command renderer lifecycle lock."""

import asyncio
from dataclasses import replace
from datetime import timedelta

import httpx
import pytest
from astrbot_plugin_dota2forge.application import (
    AstrApplication,
    AstrImageReply,
    AstrTextReply,
)
from astrbot_plugin_dota2forge.runtime import Runtime, State
from dota2forge_core import (
    AccountId,
    DailyCoverage,
    DailyReport,
    DeliveryOutcome,
    Dota2Service,
    MatchAnalysisUnavailable,
    MatchDetail,
    MatchDetailService,
    MatchDetailUnavailable,
    MatchId,
    MatchParticipant,
    MatchReport,
    RankChange,
    Subscription,
    SubscriptionCheckpoint,
    SubscriptionEvent,
    SubscriptionKey,
    SubscriptionKind,
    SubscriptionScope,
)
from dota2forge_renderer import ImageArtifact, RenderError
from dota2forge_renderer.subscriptions import (
    subscription_event_cards,
    subscription_event_text_pages,
)


class RecordingRenderer:
    def __init__(self, *, fail_page=None, error=None, blocked=None):
        self.cards = []
        self.closed = False
        self.fail_page, self.error, self.blocked = fail_page, error, blocked

    async def render(self, card):
        assert not self.closed
        self.cards.append(card)
        if self.blocked is not None:
            entered, release = self.blocked
            entered.set()
            await release.wait()
        if card.page == self.fail_page:
            raise self.error or RenderError()
        return ImageArtifact(b"\x89PNG\r\n\x1a\n" + bytes([card.page]), 1600, 100)

    async def close(self):
        self.closed = True


@pytest.fixture
def report_event(provider, identity, run_async):
    metadata = run_async(provider.get_player(AccountId(123))).metadata
    provider.calls.clear()
    detail = MatchDetail(
        MatchId(9001),
        metadata,
        duration_seconds=2000,
        did_radiant_win=False,
        game_mode="ALL_PICK_RANKED",
        players=(
            MatchParticipant(
                account_id=AccountId(123),
                is_anonymous=False,
                is_radiant=True,
                kills=4,
                deaths=2,
                assists=7,
            ),
            MatchParticipant(
                account_id=AccountId(124),
                is_anonymous=False,
                is_radiant=False,
                kills=8,
                deaths=1,
                assists=5,
            ),
        ),
    )
    report = MatchReport(
        detail.match_id,
        metadata,
        AccountId(123),
        None,
        detail,
        MatchAnalysisUnavailable(detail.match_id, metadata),
    )
    key = SubscriptionKey(
        identity, "synthetic", AccountId(123), metadata.source, SubscriptionKind.NEW_MATCH
    )
    return SubscriptionEvent("a" * 32, "b" * 32, key, metadata.fetched_at, report)


@pytest.mark.parametrize("fail_page", [None, 2])
def test_complete_image_batch_or_same_snapshot_text_fallback(
    repository, provider, clock, report_event, fail_page, run_async
):
    async def check():
        renderer = RecordingRenderer(fail_page=fail_page)
        app = AstrApplication(
            Dota2Service(repository, provider, provider, clock),
            MatchDetailService(provider),
            renderer,
        )
        batches = []
        cards = subscription_event_cards(report_event)
        assert len(cards) == 3

        async def send(event, replies):
            assert event is report_event
            assert len(renderer.cards) == (len(cards) if fail_page is None else fail_page)
            batches.append(replies)
            return DeliveryOutcome.ACCEPTED

        assert await app.dispatch_subscription(report_event, send) == DeliveryOutcome.ACCEPTED
        assert len(batches) == 1 and not provider.calls
        if fail_page is None:
            assert renderer.cards == list(cards)
            assert all(isinstance(reply, AstrImageReply) for reply in batches[0])
        else:
            assert all(isinstance(reply, AstrTextReply) for reply in batches[0])
            assert tuple(reply.text for reply in batches[0]) == subscription_event_text_pages(
                report_event
            )
            text = "\n".join(reply.text for reply in batches[0])
            assert "比赛 9001" in text and report_event.event_id in text
            assert "123" in text and "124" in text
        await app.close()

    run_async(check())


@pytest.mark.parametrize("kind", ["text_mode", "rank", "daily", "unavailable"])
def test_other_subscription_observations_and_text_mode_keep_text(
    repository, provider, clock, report_event, kind, run_async
):
    async def check():
        event = report_event
        metadata = event.payload.metadata
        if kind == "rank":
            event = replace(
                event,
                key=replace(event.key, kind=SubscriptionKind.RANK_CHANGE),
                payload=RankChange(40, 50, metadata),
            )
        elif kind == "daily":
            event = replace(
                event,
                key=replace(event.key, kind=SubscriptionKind.DAILY_REPORT),
                payload=DailyReport(
                    AccountId(123), metadata.fetched_at.date(), metadata, (), DailyCoverage.EMPTY
                ),
            )
        elif kind == "unavailable":
            event = replace(
                event,
                payload=replace(
                    event.payload,
                    detail=MatchDetailUnavailable(event.payload.match_id, metadata),
                ),
            )
        renderer = RecordingRenderer()
        app = AstrApplication(
            Dota2Service(repository, provider, provider, clock),
            MatchDetailService(provider),
            renderer,
            image_mode=kind != "text_mode",
        )
        batches = []

        async def send(candidate, replies):
            assert candidate is event
            batches.append(replies)
            return DeliveryOutcome.UNCERTAIN

        assert await app.dispatch_subscription(event, send) == DeliveryOutcome.UNCERTAIN
        assert not renderer.cards and not provider.calls
        assert all(isinstance(reply, AstrTextReply) for reply in batches[0])
        assert tuple(reply.text for reply in batches[0]) == subscription_event_text_pages(event)
        await app.close()

    run_async(check())


@pytest.mark.parametrize("failure", ["cancel", "program"])
def test_preparation_cancel_and_program_errors_never_invoke_sender(
    repository, provider, clock, report_event, failure, run_async
):
    async def check():
        entered, release = asyncio.Event(), asyncio.Event()
        renderer = RecordingRenderer(
            blocked=(entered, release) if failure == "cancel" else None,
            fail_page=2 if failure == "program" else None,
            error=TypeError("synthetic render bug") if failure == "program" else None,
        )
        app = AstrApplication(
            Dota2Service(repository, provider, provider, clock),
            MatchDetailService(provider),
            renderer,
        )

        async def send(*_):
            pytest.fail("preparation did not complete")

        task = asyncio.create_task(app.dispatch_subscription(report_event, send))
        if failure == "cancel":
            await entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            with pytest.raises(TypeError, match="synthetic render bug"):
                await task
        assert not provider.calls
        await app.close()

    run_async(check())


@pytest.mark.parametrize("stage", ["render", "send"])
def test_asset_swap_and_close_wait_for_subscription_batch(
    repository, provider, clock, report_event, stage, run_async
):
    async def check():
        entered, release = asyncio.Event(), asyncio.Event()
        previous = RecordingRenderer(blocked=(entered, release) if stage == "render" else None)
        candidate = RecordingRenderer()
        app = AstrApplication(
            Dota2Service(repository, provider, provider, clock),
            MatchDetailService(provider),
            previous,
        )
        committed = []

        async def commit():
            committed.append(True)

        async def send(_event, replies):
            assert not committed and not previous.closed
            assert len(replies) == 3
            if stage == "send":
                entered.set()
                await release.wait()
            return DeliveryOutcome.ACCEPTED

        delivery = asyncio.create_task(app.dispatch_subscription(report_event, send))
        await entered.wait()
        swap = asyncio.create_task(app.replace_renderer(candidate, commit, lambda: True))
        closing = asyncio.create_task(app.close())
        await asyncio.sleep(0)
        assert not committed and not swap.done() and not closing.done()
        release.set()
        assert await delivery == DeliveryOutcome.ACCEPTED
        await swap
        await closing
        assert committed == [True] and previous.closed and candidate.closed

    run_async(check())


@pytest.mark.parametrize("stage", ["queued", "render"])
def test_stop_gate_is_rechecked_after_lock_wait_and_preparation(
    repository, provider, clock, report_event, stage, run_async
):
    async def check():
        entered, release = asyncio.Event(), asyncio.Event()
        renderer = RecordingRenderer(blocked=(entered, release) if stage == "render" else None)
        app = AstrApplication(
            Dota2Service(repository, provider, provider, clock),
            MatchDetailService(provider),
            renderer,
        )
        ready = [True]

        async def send(*_):
            pytest.fail("a stopped runtime must not start a delivery")

        if stage == "queued":
            await app._dispatch_lock.acquire()
        delivery = asyncio.create_task(
            app.dispatch_subscription(report_event, send, permitted=lambda: ready[0])
        )
        if stage == "queued":
            await asyncio.sleep(0)
        else:
            await entered.wait()
        ready[0] = False
        if stage == "queued":
            app._dispatch_lock.release()
        else:
            release.set()
        assert await delivery == DeliveryOutcome.NOT_ATTEMPTED
        assert len(renderer.cards) == (0 if stage == "queued" else 3)
        assert not provider.calls
        await app.close()

    run_async(check())


@pytest.mark.parametrize("stage", ["render", "send"])
def test_runtime_shutdown_cancels_subscription_and_retains_claim(
    tmp_path, provider, report_event, stage, run_async
):
    async def check():
        entered, release = asyncio.Event(), asyncio.Event()
        renderer = RecordingRenderer(blocked=(entered, release) if stage == "render" else None)
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("network")))
        runtime = Runtime(
            {
                "stratz_token": "synthetic-token",
                "namespace": "astrbot-test",
                "subscriptions_enabled": True,
                "asset_download_mode": "off",
            },
            tmp_path,
            client_factory=lambda: client,
            renderer_factory=lambda: renderer,
        )
        await runtime.start()
        controller = runtime._subscriptions
        event = replace(
            report_event,
            key=replace(
                report_event.key,
                kind=SubscriptionKind.MATCH_REPORT,
                account_id=None,
                match_id=report_event.payload.match_id,
            ),
        )
        subscription = Subscription(
            event.subscription_id, event.key, event.detected_at - timedelta(seconds=1)
        )
        await controller.repository.save(subscription)
        await controller.repository.commit(
            subscription,
            SubscriptionCheckpoint(fetched_at=event.detected_at, match_reported=True),
            (event,),
        )
        batches = []

        async def send(candidate, replies):
            assert candidate == event
            batches.append(replies)
            entered.set()
            await release.wait()
            return DeliveryOutcome.ACCEPTED

        polling = asyncio.create_task(runtime.poll_subscriptions(send))
        await entered.wait()
        await runtime.close()
        with pytest.raises(asyncio.CancelledError):
            await polling
        scope = SubscriptionScope.for_identity(event.key.identity)
        assert await controller.repository.pending(scope) == (event,)
        assert not await controller.repository.deliverable(scope)
        assert len(batches) == (0 if stage == "render" else 1)
        assert renderer.closed and client.is_closed and runtime.state == State.STOPPED

    run_async(check())
