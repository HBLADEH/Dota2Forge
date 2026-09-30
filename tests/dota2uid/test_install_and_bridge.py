import importlib
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

import httpx
import pytest
from Dota2UID.install import install_bridge
from Dota2UID.runtime import Runtime, State


def test_installer_is_idempotent_and_preserves_local_config(tmp_path):
    server = tmp_path / "gsuid_core" / "server.py"
    server.parent.mkdir()
    server.write_text("", encoding="utf-8")
    entry, config = install_bridge(tmp_path, token="synthetic-token")
    assert entry.parent.name == "Dota2UID"
    assert "synthetic-token" in config.read_text("utf-8")
    compile(entry.read_text("utf-8"), str(entry), "exec")
    config.write_text("local-custom-config", encoding="utf-8")
    assert install_bridge(tmp_path, token="different-token") == (entry, config)
    assert config.read_text("utf-8") == "local-custom-config"
    entry.write_text("existing-user-code", encoding="utf-8")
    with pytest.raises(ValueError, match="Existing bridge differs"):
        install_bridge(tmp_path)
    assert entry.read_text("utf-8") == "existing-user-code"


def test_installer_requires_real_host_layout(tmp_path):
    with pytest.raises(ValueError, match="GsCore checkout"):
        install_bridge(tmp_path)
    assert not (tmp_path / "gsuid_core").exists()


def test_package_import_is_inert(monkeypatch):
    import os

    import Dota2UID

    def forbidden(*args, **kwargs):
        pytest.fail("Ordinary import must not create resources")

    monkeypatch.setattr(httpx.AsyncClient, "__init__", forbidden)
    monkeypatch.setattr(os, "getenv", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    importlib.reload(Dota2UID)


@dataclass
class SyntheticEvent:
    bot_id: str = "onebot"
    bot_self_id: str = "synthetic-bot"
    user_id: str = "synthetic-user"
    WS_BOT_ID: str = "synthetic-connection"
    at_list: list[str] = field(default_factory=list)
    at: str | None = None
    command: str = "dota绑定"
    text: str = "123"
    user_pm: int = 6


class CapturingBot:
    def __init__(self):
        self.replies = []

    async def send(self, text):
        self.replies.append(text)


def test_host_bridge_cold_hot_stop_reload_and_command_registration(
    tmp_path, config_path, monkeypatch, run_async
):
    hooks = {name: [] for name in ("on_core_start", "on_core_start_before", "on_core_shutdown")}
    commands = {}
    routes = {}

    class App:
        def route(self, path, *, dependencies):
            assert len(dependencies) == 1
            assert dependencies[0] is require_admin

            def register(func):
                routes[path] = func
                return func

            return register

        get = post = route

    def require_admin():
        raise AssertionError("The host owns authentication")

    class Service:
        def __init__(self, name, pm):
            self.pm = pm

        def on_command(self, keywords, **kwargs):
            def register(func):
                for key in keywords if isinstance(keywords, tuple) else [keywords]:
                    commands[key] = (func, self.pm)
                return func

            return register

    for name in (
        "gsuid_core",
        "gsuid_core.bot",
        "gsuid_core.models",
        "gsuid_core.server",
        "gsuid_core.sv",
        "fastapi",
        "gsuid_core.webconsole",
        "gsuid_core.webconsole.app_app",
        "gsuid_core.webconsole.web_api",
    ):
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    sys.modules["gsuid_core.bot"].Bot = CapturingBot
    sys.modules["gsuid_core.models"].Event = SyntheticEvent
    sys.modules["gsuid_core.sv"].SV = Service
    sys.modules["gsuid_core.sv"].Plugins = lambda **kwargs: None
    sys.modules["fastapi"].Depends = lambda dependency: dependency
    sys.modules["gsuid_core.webconsole.app_app"].app = App()
    sys.modules["gsuid_core.webconsole.web_api"].require_admin_header = require_admin
    for name, callbacks in hooks.items():

        def register(func, callbacks=callbacks):
            callbacks.append(func)
            return func

        setattr(sys.modules["gsuid_core.server"], name, register)
    server = tmp_path / "host" / "gsuid_core" / "server.py"
    server.parent.mkdir(parents=True)
    server.write_text("", encoding="utf-8")
    entry, _ = install_bridge(tmp_path / "host")
    clients = []

    def factory():
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: pytest.fail("No HTTP for binding"))
        )
        clients.append(client)
        return client

    def load():
        spec = importlib.util.spec_from_file_location("synthetic_host_bridge", entry)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.runtime = Runtime(config_path, client_factory=factory)
        return module

    async def check():
        cold = load()
        assert cold.runtime.state == State.NEW
        assert set(commands) == {
            "dota帮助",
            "dota绑定",
            "dota改绑",
            "dota账号",
            "dota解绑",
            "dota玩家",
            "dota战绩",
            "dota停用",
        }
        assert commands["dota停用"][1] == 0
        assert set(routes) == {"/api/dota2uid/status", "/api/dota2uid/stop"}
        assert await cold.status_dota2uid() == {"state": "new", "client_closed": True}
        await cold.start_dota2uid()
        await cold.start_dota2uid()
        bot = CapturingBot()
        await cold.command_dota2uid(bot, SyntheticEvent())
        assert "绑定已保存" in bot.replies[-1] and len(clients) == 1
        await cold.disable_dota2uid(bot, SyntheticEvent(user_pm=6, text=""))
        assert cold.runtime.state == State.READY
        await cold.disable_dota2uid(bot, SyntheticEvent(user_pm=0, text=""))
        assert cold.runtime.state == State.STOPPED and clients[-1].is_closed
        before = len(bot.replies)
        await cold.command_dota2uid(bot, SyntheticEvent())
        assert len(bot.replies) == before
        hot = load()
        await hot.command_dota2uid(bot, SyntheticEvent(command="dota账号", text=""))
        assert "已绑定" in bot.replies[-1]
        await hot.start_dota2uid()
        assert len(clients) == 2
        assert await hot.close_dota2uid() == {"state": "stopped", "client_closed": True}
        await hot.stop_dota2uid()
        assert all(c.is_closed for c in clients)

    run_async(check())
