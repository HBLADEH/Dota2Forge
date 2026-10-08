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

from scripts.build_plugin_distributions import build_distributions


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
    command: str = "do绑定"
    text: str = "123"
    regex_dict: dict[str, str] = field(default_factory=dict)
    user_pm: int = 6
    user_type: str = "direct"
    group_id: str | None = None


class CapturingBot:
    def __init__(self):
        self.replies = []

    async def send(self, text):
        self.replies.append(text)


@pytest.mark.parametrize("store_entry", [False, True])
def test_host_bridge_cold_hot_stop_reload_and_command_registration(
    tmp_path, config_path, monkeypatch, run_async, store_entry
):
    hooks = {name: [] for name in ("on_core_start", "on_core_start_before", "on_core_shutdown")}
    commands = {}
    regex_handlers = {}
    routes = {}
    jobs = {}

    class Scheduler:
        def add_job(self, callback, trigger, **options):
            assert trigger == "interval" and options["max_instances"] == 1
            assert options["coalesce"] is True and options["seconds"] == 60
            jobs[options["id"]] = callback

        def get_job(self, job_id):
            return jobs.get(job_id)

        def remove_job(self, job_id):
            del jobs[job_id]

    config_path.write_text(
        "subscriptions_enabled=true\n" + config_path.read_text("utf-8"), encoding="utf-8"
    )

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

        def on_regex(self, pattern, **kwargs):
            def register(func):
                regex_handlers[pattern] = func
                return func

            return register

    for name in (
        "gsuid_core",
        "gsuid_core.bot",
        "gsuid_core.models",
        "gsuid_core.server",
        "gsuid_core.sv",
        "gsuid_core.aps",
        "gsuid_core.logger",
        "fastapi",
        "gsuid_core.webconsole",
        "gsuid_core.webconsole.app_app",
        "gsuid_core.webconsole.web_api",
    ):
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    sys.modules["gsuid_core.bot"].Bot = CapturingBot
    sys.modules["gsuid_core.models"].Event = SyntheticEvent
    sys.modules["gsuid_core.sv"].SV = Service
    sys.modules["gsuid_core.aps"].scheduler = Scheduler()
    sys.modules["gsuid_core.logger"].logger = type("Logger", (), {"info": lambda *_: None})()
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
    if store_entry:
        candidate = build_distributions(
            Path(__file__).resolve().parents[2],
            tmp_path / "candidate",
            "https://github.com/HBLADEH/astrbot_plugin_dota2forge",
            "https://github.com/HBLADEH/Dota2UID",
        )
        entry = candidate / "Dota2UID/__init__.py"
    clients = []

    def factory():
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: pytest.fail("No HTTP for binding"))
        )
        clients.append(client)
        return client

    def load():
        spec = importlib.util.spec_from_file_location(
            "synthetic_host_bridge", entry, submodule_search_locations=[str(entry.parent)]
        )
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, "synthetic_host_bridge", module)
        spec.loader.exec_module(module)
        monkeypatch.delitem(
            sys.modules, "synthetic_host_bridge._dota2forge_bootstrap", raising=False
        )
        module.runtime = Runtime(config_path, client_factory=factory)
        return module

    async def check():
        cold = load()
        assert cold.runtime.state == State.NEW
        assert set(commands) == {
            "do素材状态",
            "do下载素材",
            "do更新素材",
            "do帮助",
            "do菜单",
            "do绑定",
            "do改绑",
            "do账号",
            "do解绑",
            "do查询",
            "do战绩",
            "do比赛",
            "do出装",
            "do停用",
            "do订阅",
            "do订阅玩家",
            "do订阅比赛",
            "do订阅列表",
            "do取消订阅",
            "do重试推送",
        }
        assert commands["do停用"][1] == 0
        assert list(regex_handlers) == [r"^do(?P<hero>.{1,64})出装$"]
        assert set(routes) == {"/api/dota2uid/status", "/api/dota2uid/stop"}
        assert await cold.status_dota2uid() == {
            "state": "new",
            "client_closed": True,
            "assets_state": "checking",
        }
        await cold.start_dota2uid()
        await cold.start_dota2uid()
        assert len(jobs) == 1 and cold.job_registered
        bot = CapturingBot()
        await cold.command_dota2uid(bot, SyntheticEvent())
        assert "绑定已保存" in bot.replies[-1] and len(clients) == 1
        dispatched = []

        async def capture(caller, keyword, text, send):
            dispatched.append((keyword, text))

        with monkeypatch.context() as patch:
            patch.setattr(cold.runtime, "dispatch", capture)
            await regex_handlers[r"^do(?P<hero>.{1,64})出装$"](
                bot, SyntheticEvent(command="AM", text="", regex_dict={"hero": "AM"})
            )
            await cold.command_dota2uid(bot, SyntheticEvent(command="do出装", text="斧王"))
        assert dispatched == [("do出装", "AM"), ("do出装", "斧王")]
        await cold.disable_dota2uid(bot, SyntheticEvent(user_pm=6, text=""))
        assert cold.runtime.state == State.READY
        await cold.disable_dota2uid(bot, SyntheticEvent(user_pm=0, text=""))
        assert cold.runtime.state == State.STOPPED and clients[-1].is_closed
        assert not jobs and not cold.job_registered
        before = len(bot.replies)
        await cold.command_dota2uid(bot, SyntheticEvent())
        assert len(bot.replies) == before
        config_path.write_text(
            config_path.read_text("utf-8").replace('reply_mode="text"', 'reply_mode="image"'),
            encoding="utf-8",
        )
        hot = load()
        await hot.command_dota2uid(bot, SyntheticEvent(command="do菜单", text=""))
        assert isinstance(bot.replies[-1], bytes) and bot.replies[-1].startswith(b"\x89PNG")
        await hot.start_dota2uid()
        assert len(jobs) == 1
        assert len(clients) == 2
        stopped = await hot.close_dota2uid()
        assert stopped == {
            "state": "stopped",
            "client_closed": True,
            "assets_state": hot.runtime.asset_status.state,
        }
        assert stopped["assets_state"] in {"failed", "cancelled", "checking"}
        await hot.stop_dota2uid()
        assert all(c.is_closed for c in clients)
        assert not jobs

    run_async(check())
