import ast
import asyncio
import sys
from importlib.resources import files
from types import ModuleType, SimpleNamespace

import pytest
from dota2forge_core import DeliveryOutcome, InvalidIdentityError, SubscriptionEvent


def sender_from_template(adapter, filename, function_name):
    source = files(adapter).joinpath(filename).read_text("utf-8")
    tree = ast.parse(source)
    owner = tree
    if adapter != "Dota2UID":
        owner = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    function = next(
        node
        for node in owner.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name
    )
    namespace = {
        "DeliveryOutcome": DeliveryOutcome,
        "InvalidIdentityError": InvalidIdentityError,
        "SubscriptionEvent": SubscriptionEvent,
        "asyncio": asyncio,
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), filename, "exec"), namespace)
    return namespace[function_name], namespace


def test_gscore_sender_receipt_live_connection_and_current_master(monkeypatch, run_async):
    sender, namespace = sender_from_template(
        "Dota2UID", "host_entry.py.template", "send_subscription"
    )
    route = SimpleNamespace(
        connection_id="connection",
        bot_self_id="bot",
        user_id="owner",
        conversation_kind="group",
        conversation_id="group",
        platform_key="onebot",
    )
    namespace["runtime"] = SimpleNamespace(subscription_route=lambda _: route)
    calls = []
    masters = ["owner"]

    class Bot:
        receipt = ["synthetic-receipt"]

        async def target_send(self, *args, **kwargs):
            calls.append((args, kwargs))
            if isinstance(self.receipt, Exception):
                raise self.receipt
            return self.receipt

    bot = Bot()
    gss = SimpleNamespace(active_ws={}, active_bot={"connection": bot})
    for name in ["gsuid_core", "gsuid_core.config", "gsuid_core.gss"]:
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    sys.modules["gsuid_core.gss"].gss = gss
    sys.modules["gsuid_core.config"].core_config = SimpleNamespace(get_config=lambda _: masters)

    async def scenario():
        assert await sender(object(), "synthetic") == DeliveryOutcome.NOT_ATTEMPTED
        assert not calls
        gss.active_ws["connection"] = object()
        assert await sender(object(), "synthetic") == DeliveryOutcome.ACCEPTED
        assert calls[-1] == (
            ("synthetic", "group", "group", "onebot", "bot"),
            {"wait_recall": True},
        )
        masters.clear()
        assert await sender(object(), "synthetic") == DeliveryOutcome.NOT_ATTEMPTED
        route.conversation_kind, route.conversation_id = "direct", "owner"
        bot.receipt = None
        assert await sender(object(), "synthetic") == DeliveryOutcome.UNCERTAIN
        bot.receipt = TimeoutError()
        assert await sender(object(), "synthetic") == DeliveryOutcome.UNCERTAIN
        bot.receipt = TypeError("synthetic-bug")
        with pytest.raises(TypeError):
            await sender(object(), "synthetic")

    run_async(scenario())


def test_astr_sender_selects_exact_bot_and_rechecks_group_admin(monkeypatch, run_async):
    sender, _namespace = sender_from_template(
        "astrbot_plugin_dota2forge", "host/main.py.template", "_send_subscription"
    )
    route = SimpleNamespace(
        connection_id="connection",
        bot_id="2001",
        user_id="1001",
        platform="aiocqhttp",
        session=lambda: ("GroupMessage", "3001"),
    )
    calls = []

    class Error(Exception):
        pass

    class ApiNotAvailable(Error):
        pass

    for name in ["aiocqhttp", "aiocqhttp.exceptions"]:
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    sys.modules["aiocqhttp.exceptions"].Error = Error
    sys.modules["aiocqhttp.exceptions"].ApiNotAvailable = ApiNotAvailable

    class Client:
        _wsr_api_clients = {}
        receipt = {"message_id": 12345}

        async def call_action(self, action, **params):
            calls.append((action, params))
            if isinstance(self.receipt, Exception):
                raise self.receipt
            return self.receipt

    client = Client()
    platform = SimpleNamespace(
        meta=lambda: SimpleNamespace(id="connection", name="aiocqhttp"), get_client=lambda: client
    )
    admins = ["1001"]
    context = SimpleNamespace(
        platform_manager=SimpleNamespace(platform_insts=[platform]),
        get_config=lambda **_: {"admins_id": admins},
    )
    plugin = SimpleNamespace(
        runtime=SimpleNamespace(subscription_route=lambda _: route), context=context
    )

    async def scenario():
        assert await sender(plugin, object(), "synthetic") == DeliveryOutcome.NOT_ATTEMPTED
        assert not calls
        client._wsr_api_clients["2001"] = object()
        assert await sender(plugin, object(), "synthetic") == DeliveryOutcome.ACCEPTED
        assert calls[-1][0] == "send_group_msg"
        assert calls[-1][1]["self_id"] == "2001" and calls[-1][1]["group_id"] == 3001
        admins.clear()
        assert await sender(plugin, object(), "synthetic") == DeliveryOutcome.NOT_ATTEMPTED
        route.session = lambda: ("FriendMessage", "1001")
        assert await sender(plugin, object(), "synthetic") == DeliveryOutcome.ACCEPTED
        assert calls[-1][0] == "send_private_msg" and calls[-1][1]["user_id"] == 1001
        client.receipt = None
        assert await sender(plugin, object(), "synthetic") == DeliveryOutcome.UNCERTAIN
        client.receipt = Error()
        assert await sender(plugin, object(), "synthetic") == DeliveryOutcome.UNCERTAIN
        client.receipt = ApiNotAvailable()
        assert await sender(plugin, object(), "synthetic") == DeliveryOutcome.NOT_ATTEMPTED
        client.receipt = TypeError("synthetic-bug")
        with pytest.raises(TypeError):
            await sender(plugin, object(), "synthetic")
        route.platform = "unsupported"
        assert await sender(plugin, object(), "synthetic") == DeliveryOutcome.NOT_ATTEMPTED

    run_async(scenario())
