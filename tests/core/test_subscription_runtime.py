import asyncio
import importlib
from dataclasses import replace

import httpx
import pytest
from dota2forge_core import SubscriptionRepositoryError


@pytest.fixture(params=["Dota2UID", "astrbot_plugin_dota2forge"])
def subscription_runtime(request, tmp_path):
    adapter = request.param
    raw = {
        "namespace": "test-deployment",
        "stratz_token": "synthetic-token",
        "reply_mode": "text",
        "subscriptions_enabled": True,
    }
    runtime_module = importlib.import_module(adapter + ".runtime")

    def client_factory():
        return httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("network")))

    if adapter == "Dota2UID":
        path = tmp_path / "config.toml"
        path.write_text(
            'namespace="test-deployment"\nstratz_token="synthetic-token"\n'
            'reply_mode="text"\ntimeout_seconds=2\nsubscriptions_enabled=true\n'
            '[platforms]\nonebot="qq"\n',
            encoding="utf-8",
        )
        runtime = runtime_module.Runtime(path, client_factory=client_factory)
        caller = importlib.import_module(adapter + ".commands").Caller(
            "onebot",
            "synthetic-bot",
            "synthetic-user",
            "synthetic-connection",
            conversation_kind="direct",
        )
    else:
        runtime = runtime_module.Runtime(raw, tmp_path, client_factory=client_factory)
        caller = importlib.import_module(adapter + ".identity").Caller(
            "aiocqhttp",
            "synthetic-connection",
            "synthetic-bot",
            "synthetic-user",
            conversation_kind="FriendMessage",
        )
    return runtime, caller, adapter


def test_runtime_permissions_rebinding_and_unbinding_revoke_before_change(
    subscription_runtime, monkeypatch, run_async
):
    runtime, caller, adapter = subscription_runtime
    replies = []

    async def send(reply):
        replies.append(reply.text)

    async def scenario():
        await runtime.start()
        assert runtime.subscriptions_enabled
        await runtime.dispatch(caller, "dota绑定", "123", send)
        await runtime.dispatch(caller, "dota订阅", "", send)
        assert "已保存比赛订阅" in replies[-1]
        if adapter == "Dota2UID":
            identity = caller.identity(runtime._config)
            group = replace(caller, conversation_kind="group", conversation_id="synthetic-group")
            bindings = runtime._service
        else:
            identity = caller.identity(runtime._config.namespace)
            group = replace(
                caller, conversation_kind="GroupMessage", conversation_id="synthetic-group"
            )
            bindings = runtime._application._service
        worker = runtime._subscriptions
        await runtime.dispatch(group, "dota订阅", "日报", send)
        assert "仅限 Bot 管理员" in replies[-1]
        await runtime.dispatch(replace(group, is_admin=True), "dota订阅", "日报", send)
        assert "已保存日报" in replies[-1]
        assert len(await worker.service.list_subscriptions(identity)) == 2
        await runtime.dispatch(caller, "dota改绑", "01", send)
        assert len(await worker.service.list_subscriptions(identity)) == 2
        entered, release = asyncio.Event(), asyncio.Event()
        original = worker.revoke

        async def blocked_revoke(owner):
            entered.set()
            await release.wait()
            await original(owner)

        monkeypatch.setattr(worker, "revoke", blocked_revoke)
        rebind = asyncio.create_task(runtime.dispatch(caller, "dota改绑", "456", send))
        await entered.wait()
        subscribe = asyncio.create_task(runtime.dispatch(caller, "dota订阅", "段位", send))
        await asyncio.sleep(0)
        assert not subscribe.done()
        release.set()
        await asyncio.gather(rebind, subscribe)
        subscriptions = await worker.service.list_subscriptions(identity)
        assert len(subscriptions) == 1 and subscriptions[0].key.account_id.value == 456
        assert (await bindings.get_binding(identity)).account_id.value == 456

        async def unavailable(_owner):
            raise SubscriptionRepositoryError()

        monkeypatch.setattr(worker, "revoke", unavailable)
        await runtime.dispatch(caller, "dota改绑", "789", send)
        assert "不可用" in replies[-1]
        assert (await bindings.get_binding(identity)).account_id.value == 456
        monkeypatch.setattr(worker, "revoke", original)
        await runtime.dispatch(caller, "dota解绑", "", send)
        assert not await worker.service.list_subscriptions(identity)
        await runtime.close()
        await runtime.close()
        assert runtime.client_closed

    run_async(scenario())


@pytest.mark.parametrize(
    "field,value",
    [
        ("subscriptions_enabled", 1),
        ("subscription_interval_seconds", True),
        ("subscription_interval_seconds", 59),
        ("subscription_interval_seconds", 86401),
        ("daily_report_hour", -1),
        ("daily_report_hour", 24),
        ("daily_report_hour", True),
    ],
)
def test_subscription_config_validation_both_adapters(tmp_path, field, value):
    astr = importlib.import_module("astrbot_plugin_dota2forge.config")
    with pytest.raises(astr.ConfigurationError):
        astr.load_config({"stratz_token": "synthetic", field: value}, tmp_path)
    gs = importlib.import_module("Dota2UID.config")
    with pytest.raises(gs.ConfigurationError):
        gs.Config(
            "test", "synthetic", tmp_path / "bindings.sqlite3", {"onebot": "qq"}, **{field: value}
        )
