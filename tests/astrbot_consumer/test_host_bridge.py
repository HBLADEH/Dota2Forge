"""Exercise the installed bridge with host API doubles, without importing AstrBot."""

import importlib.util
import logging
import sys
from enum import StrEnum
from types import ModuleType, SimpleNamespace

import httpx
import pytest
from astrbot_plugin_dota2forge.install import install_bridge
from astrbot_plugin_dota2forge.runtime import State


def test_bridge_registration_permissions_reloading_and_png_messages(
    tmp_path, monkeypatch, run_async
):
    commands = {}

    class Star:
        def __init__(self, context):
            self.context = context

    class GreedyStr(str):
        pass

    class At:
        def __init__(self, qq):
            self.qq = qq

    class AtAll:
        pass

    class Image:
        @staticmethod
        def fromBytes(value):
            assert value.startswith(b"\x89PNG")
            return ("image", value)

    class PermissionType(StrEnum):
        ADMIN = "admin"

    def permission_type(permission):
        def decorate(func):
            func.permission = permission
            return func

        return decorate

    def command(name, alias=None):
        def decorate(func):
            # AstrBot's GreedyStr consumes all tokens, including no tokens.
            assert func.__annotations__["text"] is GreedyStr
            commands[name] = func
            for other in alias or ():
                commands[other] = func
            return func

        return decorate

    class Event:
        def __init__(self, *, admin=False, components=()):
            self.admin = admin
            self.components = components
            self.sent = []
            self.stopped = False

        def get_self_id(self):
            return "bot"

        def get_sender_id(self):
            return "user"

        def get_platform_id(self):
            return "connection"

        def get_platform_name(self):
            return "qq"

        def get_messages(self):
            return self.components

        def get_message_type(self):
            return SimpleNamespace(value="FriendMessage")

        def get_group_id(self):
            return ""

        def is_admin(self):
            return self.admin

        def stop_event(self):
            self.stopped = True

        def plain_result(self, text):
            return text

        def chain_result(self, chain):
            return chain

        async def send(self, result):
            self.sent.append(result)

    for name in (
        "astrbot",
        "astrbot.api",
        "astrbot.api.event",
        "astrbot.api.star",
        "astrbot.api.message_components",
        "astrbot.core",
        "astrbot.core.star",
        "astrbot.core.star.filter",
        "astrbot.core.star.filter.command",
    ):
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    sys.modules["astrbot.api"].AstrBotConfig = dict
    sys.modules["astrbot.api"].logger = logging.getLogger("synthetic")
    sys.modules["astrbot.api.event"].AstrMessageEvent = Event
    sys.modules["astrbot.api.event"].filter = SimpleNamespace(
        command=command, permission_type=permission_type, PermissionType=PermissionType
    )
    sys.modules["astrbot.api.star"].Star = Star
    sys.modules["astrbot.api.star"].Context = object
    sys.modules["astrbot.api.star"].StarTools = SimpleNamespace(
        get_data_dir=lambda _: tmp_path / "plugin_data"
    )
    for name, value in {"At": At, "AtAll": AtAll, "Image": Image}.items():
        setattr(sys.modules["astrbot.api.message_components"], name, value)
    sys.modules["astrbot.core.star.filter.command"].GreedyStr = GreedyStr
    source = tmp_path / "host" / "astrbot" / "core" / "star" / "star_manager.py"
    source.parent.mkdir(parents=True)
    source.write_text("", encoding="utf-8")
    bridge = install_bridge(tmp_path / "host") / "main.py"
    spec = importlib.util.spec_from_file_location("synthetic_astr_bridge", bridge)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert set(commands) == {
        "dota帮助",
        "dota菜单",
        "dota绑定",
        "dota改绑",
        "dota账号",
        "dota解绑",
        "dota玩家",
        "dota战绩",
        "dota比赛",
        "dota最近",
        "dota段位",
        "dota停用",
        "dota状态",
        "dota订阅",
        "dota订阅玩家",
        "dota订阅比赛",
        "dota订阅列表",
        "dota取消订阅",
        "dota重试推送",
    }
    assert commands["dota停用"].permission == PermissionType.ADMIN
    assert commands["dota状态"].permission == PermissionType.ADMIN
    clients = []

    def factory():
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("network")))
        clients.append(client)
        return client

    async def check():
        plugin = module.Dota2ForgePlugin(
            object(),
            {
                "stratz_token": "synthetic-token",
                "subscriptions_enabled": True,
            },
        )
        assert plugin.runtime is None and not (tmp_path / "plugin_data").exists()
        await plugin.initialize()
        # Replace an unused client before dispatch, keeping startup test offline.
        await plugin.runtime._client.aclose()
        plugin.runtime._client = factory()
        timer = plugin._subscription_timer
        await plugin.initialize()
        assert plugin._subscription_timer is timer and not timer.done()
        assert plugin.runtime.state == State.READY
        menu = Event(components=(At("bot"),))
        await plugin.menu(menu, "")
        assert menu.stopped and menu.sent[0][0][0] == "image"
        bind = Event(components=(At("other"),))
        await plugin.bind(bind, "123")
        assert "身份" in bind.sent[-1] and "未执行" in bind.sent[-1]
        await plugin.bind(menu, "123 extra")
        assert "参数不正确" in menu.sent[-1]
        member = Event()
        await plugin.stop(member, "")  # Server-side check survives bypassed decorator.
        assert plugin.runtime.state == State.READY and not member.sent
        admin = Event(admin=True)
        await plugin.status(admin, "")
        assert "state=ready" in admin.sent[-1]
        await plugin.stop(admin, "")
        await plugin.terminate()
        assert plugin.runtime.state == State.STOPPED and clients[-1].is_closed
        assert plugin._subscription_timer is None and timer.done()
        replacement = module.Dota2ForgePlugin(object(), {"stratz_token": "synthetic-token"})
        await replacement.initialize()
        assert replacement.runtime is not plugin.runtime
        await replacement.terminate()

    run_async(check())
