"""Delivery and shutdown invariants, using synthetic models and no host SDK."""

import asyncio
from dataclasses import replace
from datetime import timedelta

import httpx
import pytest
from astrbot_plugin_dota2forge.application import AstrApplication, AstrImageReply, AstrTextReply
from astrbot_plugin_dota2forge.identity import Caller
from astrbot_plugin_dota2forge.runtime import Runtime, State
from astrbot_plugin_dota2forge.selection import SelectionError, SelectionStore
from dota2forge_core import (
    AccountId,
    Dota2Service,
    MatchDetail,
    MatchDetailService,
    MatchId,
    MatchParticipant,
    MatchSummary,
    PlatformIdentity,
    ProviderError,
    ProviderErrorCode,
    RecentMatches,
    RepositoryError,
)
from dota2forge_renderer import AsyncRenderer, RenderError


def test_complete_delivery_controls_selection_and_binding_invalidation(
    repository, provider, identity, clock, run_async
):
    async def check():
        service = Dota2Service(repository, provider, provider, clock)
        app = AstrApplication(service, MatchDetailService(provider), image_mode=False)
        await service.bind_account(identity, "123")
        profile = await provider.get_player(AccountId(123))
        metadata = profile.metadata
        rows = tuple(
            MatchSummary(
                i + 1, AccountId(123), metadata.fetched_at - timedelta(minutes=i), metadata
            )
            for i in range(100)
        )
        current = [RecentMatches(AccountId(123), rows, metadata)]

        async def recent(account, limit):
            provider.calls.append(("recent", account, limit))
            return replace(current[0], matches=current[0].matches[:limit])

        provider.get_recent_matches = recent
        replies = []

        async def send(reply):
            replies.append(reply.text)

        session = ("GroupMessage", "group")
        await app.dispatch(identity, "dota战绩", "100", send, session)
        assert len(replies) == 3 and "20 页" in replies[-1]
        count = len(provider.calls)
        await app.dispatch(identity, "dota战绩", "第20页", send, session)
        assert "第 100 场" in replies[-1] and len(provider.calls) == count
        await app.dispatch(identity, "dota比赛", "第100场", send, session)
        assert provider.calls[-1] == ("detail", MatchId(100))
        await app.dispatch(identity, "dota战绩", "第2页", send, ("GroupMessage", "other"))
        assert "没有有效" in replies[-1]
        another = PlatformIdentity(identity.namespace, identity.platform, identity.bot_id, "other")
        await app.dispatch(another, "dota比赛", "第1场", send, session)
        assert "没有有效" in replies[-1]

        current[0] = RecentMatches(AccountId(123), (), metadata)
        partial = []

        async def broken(reply):
            partial.append(reply)
            raise OSError("synthetic transport failure")

        with pytest.raises(OSError):
            await app.dispatch(identity, "dota战绩", "100", broken, session)
        assert len(partial) == 1
        await app.dispatch(identity, "dota比赛", "第100场", send, session)
        assert provider.calls[-1] == ("detail", MatchId(100))
        await app.dispatch(identity, "dota战绩", "100", send, session)
        assert "0 场" in replies[-1]
        await app.dispatch(identity, "dota比赛", "第1场", send, session)
        assert "只有 0 场" in replies[-1]
        await app.dispatch(identity, "dota改绑", "124", send, session)
        await app.dispatch(identity, "dota比赛", "第1场", send, session)
        assert "没有有效" in replies[-1]
        await app.close()

    run_async(check())


def test_source_errors_and_render_fallback_do_not_trigger_second_query(
    repository, provider, identity, clock, run_async
):
    async def check():
        service = Dota2Service(repository, provider, provider, clock)
        await service.bind_account(identity, "123")
        engine = AsyncRenderer()
        engine._engine.render = lambda _: (_ for _ in ()).throw(RenderError())
        app = AstrApplication(service, MatchDetailService(provider), engine)
        replies = await app.handle(identity, "dota玩家", "")
        assert isinstance(replies[0], AstrTextReply) and "Synthetic" in replies[0].text
        assert len(provider.calls) == 1

        async def limited(account):
            raise ProviderError(
                ProviderErrorCode.RATE_LIMITED, provider.source, retry_after_seconds=5
            )

        provider.get_player = limited
        replies = await app.handle(identity, "dota玩家", "")
        assert "rate_limited" in replies[0].text and "5 秒" in replies[0].text
        assert "没有战绩" not in replies[0].text
        await app.handle(identity, "dota绑定", "124")
        conflict = await app.handle(identity, "dota绑定", "124")
        assert "dota改绑" in conflict[0].text

        async def unavailable(_):
            raise RepositoryError()

        repository.get = unavailable
        assert "存储不可用" in (await app.handle(identity, "dota账号", ""))[0].text
        await app.close()

    run_async(check())


def test_real_detail_model_is_rendered_for_each_side(
    repository, provider, identity, clock, run_async
):
    async def check():
        service = Dota2Service(repository, provider, provider, clock)
        profile = await provider.get_player(AccountId(123))
        detail = MatchDetail(
            MatchId(17),
            profile.metadata,
            players=(
                MatchParticipant(account_id=AccountId(123), is_anonymous=False, is_radiant=True),
                MatchParticipant(is_anonymous=True, is_radiant=False),
            ),
        )

        async def get_detail(match_id):
            provider.calls.append(("detail", match_id))
            return detail

        provider.get_match_detail = get_detail
        renderer = AsyncRenderer()
        app = AstrApplication(service, MatchDetailService(provider), renderer)
        replies = await app.handle(identity, "dota比赛", "17")
        assert len(replies) == 2 and all(isinstance(reply, AstrImageReply) for reply in replies)
        await app.close()

    run_async(check())


def test_selection_capacity_expiry_and_changed_binding(provider, identity, run_async):
    recent = run_async(provider.get_recent_matches(AccountId(123), 1))
    now = [0.0]
    store = SelectionStore(lambda: now[0])
    keys = [(identity, ("GroupMessage", str(i))) for i in range(129)]
    for key in keys:
        store.remember(key, recent, None)
    with pytest.raises(SelectionError):
        store.get(keys[0], None)
    assert store.get(keys[-1], None) is recent
    now[0] = 599
    assert store.get(keys[-1], None) is recent
    now[0] = 600
    with pytest.raises(SelectionError):
        store.get(keys[-1], None)
    store.remember(keys[-1], recent, None)
    store.invalidate(identity)
    with pytest.raises(SelectionError):
        store.get(keys[-1], None)


@pytest.mark.parametrize("stage", ["query", "send"])
def test_stop_cancels_work_and_new_lifecycle_owns_new_resources(tmp_path, run_async, stage):
    clients = []
    renderers = []

    def factory():
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("network")))
        clients.append(client)
        return client

    def rendering():
        renderer = AsyncRenderer()
        renderers.append(renderer)
        return renderer

    async def check():
        raw = {"stratz_token": "synthetic-token", "reply_mode": "image"}
        runtime = Runtime(raw, tmp_path, client_factory=factory, renderer_factory=rendering)
        await runtime.start()
        started = asyncio.Event()
        caller = Caller("qq", "connection", "bot", "user", conversation_kind="FriendMessage")
        assert runtime._application is not None

        async def blocked(*_):
            started.set()
            await asyncio.Future()

        if stage == "query":
            runtime._application.handle = blocked
            runtime._application._prepare = blocked
        task = asyncio.create_task(runtime.dispatch(caller, "dota菜单", "", blocked))
        await started.wait()
        await runtime.close()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert runtime.state == State.STOPPED and clients[0].is_closed
        assert renderers[0]._closed
        await runtime.dispatch(caller, "dota菜单", "", blocked)
        await runtime.close()
        replacement = Runtime(raw, tmp_path, client_factory=factory, renderer_factory=rendering)
        await replacement.start()
        assert len(clients) == 2 and clients[1] is not clients[0]
        await replacement.close()
        assert clients[1].is_closed

    run_async(check())
