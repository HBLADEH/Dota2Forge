import asyncio
import importlib
from dataclasses import replace

import pytest
from dota2forge_core import (
    DeliveryOutcome,
    InvalidIdentityError,
    ProviderError,
    ProviderErrorCode,
    SQLiteSubscriptionRepository,
    SubscriptionKind,
    SubscriptionScope,
    SubscriptionService,
)
from test_subscription_delivery_daily import seed_event


@pytest.fixture(params=["Dota2UID", "astrbot_plugin_dota2forge"])
def controller(request, tmp_path, provider, clock, service, run_async):
    module = importlib.import_module(request.param + ".subscriptions")
    repository = SQLiteSubscriptionRepository(tmp_path / "subscriptions.sqlite3")
    run_async(repository.initialize())
    subscriptions = SubscriptionService(repository, provider, provider, clock, provider, provider)
    monotonic = [0.0]
    worker = module.SubscriptionController(
        "test-deployment",
        service,
        subscriptions,
        repository,
        enabled=True,
        monotonic=lambda: monotonic[0],
        now=clock.now,
    )
    return worker, subscriptions, repository, monotonic, module


def test_subscription_commands_default_snapshot_permissions_and_grammar(
    controller, identity, service, run_async
):
    worker, subscriptions, _repository, _monotonic, _module = controller

    async def scenario():
        denied = await worker.handle(identity, "synthetic", True, False, "do订阅", "比赛 123")
        assert "管理员" in denied and not await subscriptions.list_subscriptions(identity)
        assert "尚未绑定" in await worker.handle(identity, "synthetic", False, False, "do订阅", "")
        await service.bind_account(identity, 123)
        reply = await worker.handle(identity, "synthetic", False, False, "do订阅", "")
        assert "已保存比赛" in reply
        player_reply = await worker.handle(identity, "synthetic", False, False, "do订阅玩家", "123")
        assert "已保存玩家对局订阅" in player_reply
        match_reply = await worker.handle(identity, "synthetic", False, False, "do订阅比赛", "9001")
        assert "已保存指定比赛订阅" in match_reply
        first = (await subscriptions.list_subscriptions(identity))[0]
        assert "本会话订阅" in await worker.handle(
            identity, "synthetic", False, False, "do订阅列表", ""
        )
        assert "没有订阅" in await worker.handle(identity, "other", False, False, "do订阅列表", "")
        for text in ["比赛 01", "日报 123 extra", "unknown", "段位 -1"]:
            assert "参数不正确" in await worker.handle(
                identity, "synthetic", False, False, "do订阅", text
            )
        other = replace(identity, user_id="other-synthetic")
        assert "不属于你" in await worker.handle(
            other, "synthetic", False, False, "do取消订阅", first.subscription_id
        )
        assert "已取消" in await worker.handle(
            identity, "synthetic", False, False, "do取消订阅", first.subscription_id
        )
        assert "参数不正确" in await worker.handle(
            identity, "synthetic", False, False, "do取消订阅", ""
        )
        assert "未被占用" in await worker.handle(
            identity, "synthetic", False, False, "do重试推送", "a" * 32
        )
        worker.enabled = False
        assert "未启用" in await worker.handle(
            identity, "synthetic", False, False, "do订阅", "比赛 123"
        )
        worker.enabled = True
        await worker.close()
        assert "停用" in await worker.handle(identity, "synthetic", False, False, "do订阅列表", "")

    run_async(scenario())


@pytest.mark.parametrize("outcome", list(DeliveryOutcome))
def test_claim_before_send_and_explicit_manual_retry(
    controller, identity, provider, clock, outcome, run_async
):
    worker, service, repository, monotonic, _module = controller
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        event = await seed_event(service, provider, clock, identity)
        calls = []

        async def send(candidate, text):
            assert candidate == event and event.event_id in text
            assert not await repository.deliverable(scope)
            calls.append(candidate)
            return outcome

        await worker.tick(send)
        assert calls == [event]
        if outcome == DeliveryOutcome.ACCEPTED:
            assert not await repository.pending(scope)
        else:
            assert await repository.pending(scope) == (event,)
            assert bool(await repository.deliverable(scope)) == (
                outcome == DeliveryOutcome.NOT_ATTEMPTED
            )
        if outcome == DeliveryOutcome.UNCERTAIN:
            monotonic[0] += 300
            await worker.tick(send)
            assert calls == [event]
            assert "管理员" in await worker.handle(
                identity, "synthetic", True, False, "do重试推送", event.event_id
            )
            assert "可能产生重复" in await worker.handle(
                identity, "synthetic", False, False, "do重试推送", event.event_id
            )
            monotonic[0] += 300
            await worker.tick(send)
            assert calls == [event, event]
        await worker.close()

    run_async(scenario())


def test_close_cancels_sender_without_releasing_claim(
    controller, identity, provider, clock, run_async
):
    worker, service, repository, _monotonic, _module = controller

    async def scenario():
        event = await seed_event(service, provider, clock, identity)
        entered = asyncio.Event()

        async def send(_event, _text):
            entered.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(worker.tick(send))
        await entered.wait()
        await worker.close()
        await worker.close()
        assert task.cancelled()
        scope = SubscriptionScope.for_identity(identity)
        assert await repository.pending(scope) == (event,)
        assert not await repository.deliverable(scope)

    run_async(scenario())


def test_disconnected_targets_do_not_starve_later_delivery(
    controller, identity, provider, clock, run_async
):
    worker, service, repository, monotonic, _module = controller
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        provider.profile = replace(provider.profile, rank_tier=40)
        for index in range(6):
            await service.subscribe(
                identity, 123, f"synthetic-{index}", kind=SubscriptionKind.RANK_CHANGE
            )
        await service.poll_rank_changes(scope)
        provider.profile = replace(provider.profile, rank_tier=41)
        await service.poll_rank_changes(scope)
        pending = await repository.pending(scope)
        denied = {event.event_id for event in pending[:5]}
        sent = []

        async def send(event, _text):
            sent.append(event.event_id)
            return (
                DeliveryOutcome.NOT_ATTEMPTED
                if event.event_id in denied
                else DeliveryOutcome.ACCEPTED
            )

        await worker.tick(send)
        assert sent == [event.event_id for event in pending[:5]]
        monotonic[0] += 300
        await worker.tick(send)
        assert sent[-1] == pending[-1].event_id
        assert len(await repository.pending(scope)) == 5
        await worker.close()

    run_async(scenario())


def test_unclassified_sender_failure_pauses_and_retains_reservation(
    controller, identity, provider, clock, run_async
):
    worker, service, repository, _monotonic, module = controller

    async def scenario():
        event = await seed_event(service, provider, clock, identity)

        async def send(_event, _text):
            raise TypeError("synthetic-programming-error")

        with pytest.raises(module.SubscriptionWorkerError):
            await worker.tick(send)
        assert worker.paused and worker.last_error == "TypeError"
        assert await repository.pending(SubscriptionScope.for_identity(identity)) == (event,)
        assert not await repository.deliverable(SubscriptionScope.for_identity(identity))
        await worker.tick(send)
        await worker.close()

    run_async(scenario())


@pytest.mark.parametrize(
    "code,delay",
    [
        (ProviderErrorCode.AUTHENTICATION, None),
        (ProviderErrorCode.RATE_LIMITED, None),
        (ProviderErrorCode.RATE_LIMITED, 600),
        (ProviderErrorCode.PRIVATE, None),
    ],
)
def test_worker_quota_pause_and_no_client_recreation(
    controller, identity, provider, code, delay, run_async
):
    worker, service, _repository, monotonic, _module = controller

    async def scenario():
        await service.subscribe(identity, 123, "synthetic")
        provider.failure = ProviderError(code, provider.source, retry_after_seconds=delay)

        async def send(_event, _text):
            pytest.fail("No event on provider failure")

        await worker.tick(send)
        assert len(provider.calls) == 1
        assert worker.paused == (
            code == ProviderErrorCode.AUTHENTICATION
            or (code == ProviderErrorCode.RATE_LIMITED and delay is None)
        )
        monotonic[0] = 299
        await worker.tick(send)
        assert len(provider.calls) == 1
        if delay == 600:
            monotonic[0] = 599
            await worker.tick(send)
            assert len(provider.calls) == 1
            monotonic[0] = 600
            await worker.tick(send)
            assert len(provider.calls) == 2
        await worker.close()

    run_async(scenario())


@pytest.mark.parametrize("adapter", ["Dota2UID", "astrbot_plugin_dota2forge"])
@pytest.mark.parametrize("kind", ["private", "group"])
def test_routes_roundtrip_target_owner_and_connection_isolation(
    adapter, kind, provider, clock, tmp_path, run_async
):
    routes = importlib.import_module(adapter + ".subscription_routes")
    if adapter == "Dota2UID":
        commands = importlib.import_module(adapter + ".commands")
        config_module = importlib.import_module(adapter + ".config")
        config = config_module.Config(
            "test-deployment", "synthetic", tmp_path / "bindings.sqlite3", {"onebot": "qq"}
        )
        caller = commands.Caller(
            "onebot",
            "synthetic-bot",
            "synthetic-user",
            "synthetic-connection",
            conversation_kind="direct" if kind == "private" else "group",
            conversation_id=None if kind == "private" else "synthetic-group",
        )
        identity = caller.identity(config)
    else:
        caller = importlib.import_module(adapter + ".identity").Caller(
            "qq",
            "synthetic-connection",
            "synthetic-bot",
            "synthetic-user",
            conversation_kind="FriendMessage" if kind == "private" else "GroupMessage",
            conversation_id="" if kind == "private" else "synthetic-group",
        )
        config = "test-deployment"
        identity = caller.identity(config)
    encoded = routes.destination(caller, config)
    assert len(encoded) <= 512 and "synthetic-user" not in encoded
    repository = SQLiteSubscriptionRepository(tmp_path / "route.sqlite3")
    run_async(repository.initialize())
    service = SubscriptionService(repository, provider, provider, clock)
    event = run_async(seed_event(service, provider, clock, identity))
    event = replace(event, key=replace(event.key, destination=encoded))
    route = routes.delivery_route(event, config)
    assert route.user_id == caller.user_id
    assert route.connection_id == caller.connection_id
    for bad in ["bad-prefix", "d2f1.!", "d2f1.W10", "d2f1." + "A" * 506]:
        with pytest.raises(InvalidIdentityError):
            routes.delivery_route(replace(event, key=replace(event.key, destination=bad)), config)
    with pytest.raises(InvalidIdentityError):
        routes.delivery_route(
            replace(event, key=replace(event.key, identity=replace(identity, user_id="other"))),
            config,
        )
    if adapter == "Dota2UID":
        invalid = replace(caller, conversation_kind="channel")
    else:
        invalid = replace(caller, conversation_kind="OtherMessage")
    with pytest.raises(InvalidIdentityError):
        routes.destination(invalid, config)
