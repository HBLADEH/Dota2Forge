import ast
import asyncio
import base64
import sys
from importlib.resources import files
from types import ModuleType, SimpleNamespace

import pytest
from astrbot_plugin_dota2forge.application import AstrImageReply, AstrReply, AstrTextReply
from dota2forge_core import DeliveryOutcome, InvalidIdentityError, SubscriptionEvent
from dota2forge_renderer import ImageArtifact
from Dota2UID.replies import ImageReply, Reply, TextReply


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
        "base64": base64,
        "Reply": Reply,
        "ImageReply": ImageReply,
        "AstrReply": AstrReply,
        "AstrImageReply": AstrImageReply,
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), filename, "exec"), namespace)
    return namespace[function_name], namespace


@pytest.mark.parametrize(
    "filename", ["host_entry.py.template", "bundled_business_entry.py.template"]
)
def test_gscore_sender_receipt_live_connection_and_current_master(monkeypatch, run_async, filename):
    sender, namespace = sender_from_template("Dota2UID", filename, "send_subscription")
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
    for name in ["gsuid_core", "gsuid_core.config", "gsuid_core.gss", "gsuid_core.models"]:
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    sys.modules["gsuid_core.gss"].gss = gss
    sys.modules["gsuid_core.config"].core_config = SimpleNamespace(get_config=lambda _: masters)
    sys.modules["gsuid_core.models"].Message = lambda **kwargs: SimpleNamespace(**kwargs)
    artifact = ImageArtifact(b"\x89PNG\r\n\x1a\n", 1600, 1)
    replies = (ImageReply(artifact), ImageReply(artifact), TextReply("synthetic"))

    async def scenario():
        assert await sender(object(), replies) == DeliveryOutcome.NOT_ATTEMPTED
        assert not calls
        gss.active_ws["connection"] = object()
        assert await sender(object(), replies) == DeliveryOutcome.ACCEPTED
        assert len(calls) == 1
        assert await sender(object(), ()) == DeliveryOutcome.NOT_ATTEMPTED
        assert len(calls) == 1
        args, kwargs = calls[-1]
        assert args[1:] == ("group", "group", "onebot", "bot")
        assert kwargs == {"wait_recall": True}
        assert [message.type for message in args[0]] == ["image", "image", "text"]
        assert args[0][0].data == artifact.data and args[0][2].data == "synthetic\n"
        masters.clear()
        assert await sender(object(), replies) == DeliveryOutcome.NOT_ATTEMPTED
        route.conversation_kind, route.conversation_id = "direct", "owner"
        for receipt in (None, [], [None], [""], {"message_id": "truthy"}):
            bot.receipt = receipt
            assert await sender(object(), replies) == DeliveryOutcome.UNCERTAIN
        bot.receipt = TimeoutError()
        assert await sender(object(), replies) == DeliveryOutcome.UNCERTAIN
        bot.receipt = TypeError("synthetic-bug")
        with pytest.raises(TypeError):
            await sender(object(), replies)

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
    artifact = ImageArtifact(b"\x89PNG\r\n\x1a\n", 1600, 1)
    replies = (AstrImageReply(artifact), AstrImageReply(artifact), AstrTextReply("synthetic"))

    async def scenario():
        assert await sender(plugin, object(), replies) == DeliveryOutcome.NOT_ATTEMPTED
        assert not calls
        client._wsr_api_clients["2001"] = object()
        assert await sender(plugin, object(), replies) == DeliveryOutcome.ACCEPTED
        assert len(calls) == 1
        assert await sender(plugin, object(), ()) == DeliveryOutcome.NOT_ATTEMPTED
        assert len(calls) == 1
        assert calls[-1][0] == "send_group_msg"
        assert calls[-1][1]["self_id"] == "2001" and calls[-1][1]["group_id"] == 3001
        segments = calls[-1][1]["message"]
        assert [segment["type"] for segment in segments] == ["image", "image", "text"]
        assert base64.b64decode(segments[0]["data"]["file"][9:]) == artifact.data
        assert "synthetic" in segments[2]["data"]["text"]
        admins.clear()
        assert await sender(plugin, object(), replies) == DeliveryOutcome.NOT_ATTEMPTED
        route.session = lambda: ("FriendMessage", "1001")
        assert await sender(plugin, object(), replies) == DeliveryOutcome.ACCEPTED
        assert calls[-1][0] == "send_private_msg" and calls[-1][1]["user_id"] == 1001
        for receipt in (None, {}, {"message_id": ""}, {"message_id": True}, {"message_id": 0}):
            client.receipt = receipt
            assert await sender(plugin, object(), replies) == DeliveryOutcome.UNCERTAIN
        client.receipt = Error()
        assert await sender(plugin, object(), replies) == DeliveryOutcome.UNCERTAIN
        client.receipt = ApiNotAvailable()
        assert await sender(plugin, object(), replies) == DeliveryOutcome.NOT_ATTEMPTED
        client.receipt = TypeError("synthetic-bug")
        with pytest.raises(TypeError):
            await sender(plugin, object(), replies)
        route.platform = "unsupported"
        assert await sender(plugin, object(), replies) == DeliveryOutcome.NOT_ATTEMPTED

    run_async(scenario())
