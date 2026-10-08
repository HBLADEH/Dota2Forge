"""Offline GsCore registration and lifecycle checks for the bundled entry."""

import builtins
import importlib.util
import inspect
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from _config_sdk import install_config_sdk

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "adapters/Dota2UID/src/Dota2UID"
OWNER_REGISTRY = "_dota2forge_gscore_bootstrap_owners"


@dataclass
class SyntheticEvent:
    user_pm: object = 0
    command: str = "do安装核心"
    text: str = ""
    at: str | None = None
    at_list: list[str] = field(default_factory=list)
    bot_id: str = "onebot"
    bot_self_id: str = "synthetic-bot"
    user_id: str = "synthetic-user"
    WS_BOT_ID: str = "synthetic-connection"
    user_type: str = "direct"
    group_id: str | None = None
    regex_dict: dict[str, str] = field(default_factory=dict)


class CapturingBot:
    def __init__(self):
        self.replies = []

    async def send(self, text):
        self.replies.append(text)


class SyntheticBootstrapError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class SyntheticManager:
    def __init__(self, plugin_root, data_root):
        self.plugin_root = plugin_root
        self.data_root = data_root
        self.state = "unprepared"
        self.error = None
        self.generation = None
        self.local = True
        self.prepare_error = None
        self.activate_error = None
        self.gate = None
        self.started = None
        self.finished = None
        self.prepare_calls = []
        self.activate_calls = 0
        self.close_calls = 0

    async def prepare(self, *, allow_download=False):
        self.prepare_calls.append(allow_download)
        self.state = "preparing"
        if self.started is not None:
            self.started.set()
        if self.gate is not None:
            await self.gate.wait()
        if self.prepare_error is not None:
            self.state = "failed"
            self.error = self.prepare_error
            if self.finished is not None:
                self.finished.set()
            raise SyntheticBootstrapError(self.prepare_error)
        if not self.local and not allow_download:
            self.state = "failed"
            self.error = "missing_wheel"
            if self.finished is not None:
                self.finished.set()
            return None
        self.state = "prepared"
        self.generation = self.data_root / "runtime" / "synthetic-generation"
        if self.finished is not None:
            self.finished.set()
        return self.generation

    def activate(self):
        self.activate_calls += 1
        if self.activate_error:
            self.state = "failed"
            self.error = self.activate_error
            raise SyntheticBootstrapError(self.activate_error)
        self.state = "runtime_available"

    async def close(self):
        self.close_calls += 1
        if self.state == "preparing" and self.finished is not None:
            await self.finished.wait()
        self.state = "stopped"

    def status(self):
        return {
            "state": self.state,
            "error": self.error or "",
            "prepared": self.generation is not None,
            "runtime_available": self.state == "runtime_available",
            "busy": self.state == "preparing",
        }

    def status_text(self):
        return f"Dota2UID 运行库状态：{self.state}，错误：{self.error or '无'}。"


@pytest.fixture
def host(tmp_path, monkeypatch):
    plugin = tmp_path / "host/gsuid_core/plugins/Dota2UID"
    plugin.mkdir(parents=True)
    entry = plugin / "__init__.py"
    entry.write_text((TEMPLATES / "bundled_host_entry.py.template").read_text("utf-8"), "utf-8")
    (plugin / "_dota2forge_business.py").write_text(
        (TEMPLATES / "bundled_business_entry.py.template").read_text("utf-8"), "utf-8"
    )
    (plugin / "_dota2forge_config.py").write_text(
        (TEMPLATES / "host_config.py.template").read_text("utf-8"), "utf-8"
    )
    data = tmp_path / "host/data/Dota2UID"
    data.mkdir(parents=True)
    package = "synthetic_bundled_bridge"
    for name in list(sys.modules):
        if name.startswith(package) or name == OWNER_REGISTRY:
            monkeypatch.delitem(sys.modules, name)

    for name in (
        "gsuid_core",
        "gsuid_core.bot",
        "gsuid_core.models",
        "gsuid_core.server",
        "gsuid_core.sv",
        "gsuid_core.aps",
        "gsuid_core.logger",
        "gsuid_core.trigger",
        "gsuid_core.webconsole",
        "gsuid_core.webconsole.app_app",
        "gsuid_core.webconsole.web_api",
        "fastapi",
    ):
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    sdk = sys.modules["gsuid_core"]
    configuration_registry = install_config_sdk(monkeypatch)
    sdk.server = server = sys.modules["gsuid_core.server"]
    sdk.sv = sv = sys.modules["gsuid_core.sv"]
    registry = sv.SL = SimpleNamespace(lst={}, detail_lst={}, plugins={})
    owner_plugin = object()
    registry.detail_lst[owner_plugin] = []

    class Service:
        def __new__(cls, name, pm):
            if name in registry.lst:
                return registry.lst[name]
            return super().__new__(cls)

        def __init__(self, name, pm):
            if hasattr(self, "TL"):
                return
            # Match the real SDK's filename-derived plugin ownership constraint.
            caller_file = inspect.currentframe().f_back.f_code.co_filename
            assert Path(caller_file).parent == plugin
            self.name, self.pm, self.TL = name, pm, {}
            registry.lst[name] = self
            registry.detail_lst[owner_plugin].append(self)

        def register(self, kind, keywords, **options):
            assert options == {"block": True}

            def decorate(callback):
                triggers = self.TL.setdefault(kind, {})
                for key in keywords if isinstance(keywords, tuple) else (keywords,):
                    triggers[key] = callback
                return callback

            return decorate

        def on_command(self, keywords, **options):
            return self.register("command", keywords, **options)

        def on_regex(self, keywords, **options):
            return self.register("regex", keywords, **options)

    sv.SV = Service
    sv.Plugins = lambda **options: None
    sys.modules["gsuid_core.bot"].Bot = CapturingBot
    sys.modules["gsuid_core.models"].Event = SyntheticEvent
    sys.modules["gsuid_core.logger"].logger = SimpleNamespace(
        info=lambda *_: None, warning=lambda *_: None, error=lambda *_: None
    )
    bumps = []
    sys.modules["gsuid_core.trigger"].bump_registry_version = lambda: bumps.append(True)
    hooks = {}
    for name, collection_name in (
        ("on_core_start", "core_start_def"),
        ("on_core_start_before", "core_start_before_def"),
        ("on_core_shutdown", "core_shutdown_def"),
    ):
        hooks[name] = collection = set()
        setattr(server, collection_name, collection)

        def register(callback, collection=collection):
            collection.add(callback)
            return callback

        setattr(server, name, register)

    def require_admin():
        raise AssertionError("The host owns administrator authentication")

    class App:
        def __init__(self):
            self.router = SimpleNamespace(routes=[])
            self.user_middleware = []
            self.middleware_stack = None

        def route(self, path, *, dependencies):
            assert dependencies == [require_admin]

            def register(endpoint):
                self.router.routes.append(SimpleNamespace(path=path, endpoint=endpoint))
                return endpoint

            return register

        get = post = route

    app = App()
    sys.modules["fastapi"].Depends = lambda dependency: dependency
    sys.modules["gsuid_core.webconsole.app_app"].app = app
    sys.modules["gsuid_core.webconsole.web_api"].require_admin_header = require_admin
    jobs = {}

    class Scheduler:
        def add_job(self, callback, trigger, **options):
            assert trigger == "interval" and options["max_instances"] == 1
            jobs[options["id"]] = callback

        def get_job(self, name):
            return jobs.get(name)

        def remove_job(self, name):
            jobs.pop(name)

    sys.modules["gsuid_core.aps"].scheduler = Scheduler()
    backend = ModuleType(package + "._dota2forge_runtime")
    backend.BundledRuntime = SyntheticManager
    backend.BootstrapError = SyntheticBootstrapError
    monkeypatch.setitem(sys.modules, backend.__name__, backend)

    def load():
        spec = importlib.util.spec_from_file_location(
            package, entry, submodule_search_locations=[str(plugin)]
        )
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, package, module)
        spec.loader.exec_module(module)
        return module

    def commands():
        return {
            command: (callback, service.pm)
            for service in registry.lst.values()
            for command, callback in service.TL.get("command", {}).items()
        }

    yield SimpleNamespace(
        load=load,
        plugin=plugin,
        data=data,
        registry=registry,
        hooks=hooks,
        app=app,
        jobs=jobs,
        commands=commands,
        bumps=bumps,
        package=package,
        configurations=configuration_registry,
    )
    for name in list(sys.modules):
        if name.startswith(package) or name == OWNER_REGISTRY:
            monkeypatch.delitem(sys.modules, name, raising=False)


def test_root_registers_diagnostics_without_any_project_import(host, monkeypatch, run_async):
    original_import = builtins.__import__

    def import_without_projects(name, *args, **kwargs):
        if name.split(".", 1)[0] in {
            "Dota2UID",
            "dota2forge_core",
            "dota2forge_renderer",
            "dota2forge_assets",
        }:
            raise AssertionError("Bootstrap must not import a project runtime package")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_projects)
    module = host.load()
    assert set(host.commands()) == {"do安装核心", "do核心状态", "do停用", "do帮助", "do菜单"}
    assert all(host.commands()[name][1] == 0 for name in ("do安装核心", "do核心状态", "do停用"))
    assert module.owner.manager.prepare_calls == []
    assert not (host.data / "config.toml").exists()
    assert (host.data / "config.json").is_file()
    assert host.configurations["Dota2UID"].plugin_name == "Dota2UID"
    assert len(host.configurations["Dota2UID"].config) == 11

    async def check():
        bot = CapturingBot()
        await module.help_dota2uid(bot, SyntheticEvent(command="do帮助", user_pm=6))
        await module.help_dota2uid(bot, SyntheticEvent(command="do菜单", user_pm=6))
        assert len(bot.replies) == 2 and all("do安装核心" in text for text in bot.replies)
        await module.core_status_dota2uid(bot, SyntheticEvent())
        assert "unprepared" in bot.replies[-1]
        await module.stop_dota2uid()

    run_async(check())


@pytest.mark.parametrize(
    "event",
    [SyntheticEvent(user_pm=value) for value in (6, 1, -1, True, False, 0.0, "0", None)]
    + [
        SyntheticEvent(text="https://example.invalid/runtime.whl"),
        SyntheticEvent(text="--force"),
        SyntheticEvent(at="synthetic-user"),
        SyntheticEvent(at_list=["synthetic-user"]),
    ],
)
def test_admin_handlers_recheck_exact_permission_and_no_arguments(host, run_async, event):
    module = host.load()

    async def check():
        bot = CapturingBot()
        await module.install_dota2uid(bot, event)
        await module.core_status_dota2uid(bot, event)
        await module.disable_dota2uid(bot, event)
        assert not bot.replies
        assert module.owner.manager.prepare_calls == []
        assert not module.owner.closed
        await module.stop_dota2uid()

    run_async(check())


def test_missing_local_runtime_keeps_help_and_management(host, run_async):
    module = host.load()
    module.owner.manager.local = False

    async def check():
        await module.start_dota2uid()
        await module.start_dota2uid()
        assert module.owner.manager.prepare_calls == [False]
        assert module.owner.manager.activate_calls == 0
        assert set(host.commands()) == {"do安装核心", "do核心状态", "do停用", "do帮助", "do菜单"}
        bot = CapturingBot()
        await module.help_dota2uid(bot, SyntheticEvent(command="do帮助", user_pm=6))
        await module.core_status_dota2uid(bot, SyntheticEvent())
        assert "do安装核心" in bot.replies[0] and "missing_wheel" in bot.replies[-1]
        await module.stop_dota2uid()

    run_async(check())


def test_install_prepares_but_never_activates_and_repeated_install_is_idempotent(host, run_async):
    module = host.load()

    async def check():
        bot = CapturingBot()
        await module.install_dota2uid(bot, SyntheticEvent())
        await module.owner.install_task
        assert module.owner.manager.prepare_calls == [True]
        assert module.owner.manager.activate_calls == 0
        assert module.owner.business is None
        status = await module.status_dota2uid()
        assert status["state"] == "pending_restart" and status["prepared"] is True
        assert status["business_state"] == "unavailable"
        assert "完整重启" in bot.replies[-1]
        await module.start_dota2uid()
        assert module.owner.manager.activate_calls == 0
        await module.install_dota2uid(bot, SyntheticEvent())
        await module.owner.install_task
        assert module.owner.manager.prepare_calls == [True, True]
        assert module.owner.manager.activate_calls == 0
        await module.stop_dota2uid()

    run_async(check())


@pytest.mark.parametrize("code", ["hash_mismatch", "third_party", "disk", "timeout"])
def test_prepare_failure_remains_diagnosable(host, run_async, code):
    module = host.load()
    module.owner.manager.prepare_error = code

    async def check():
        bot = CapturingBot()
        await module.install_dota2uid(bot, SyntheticEvent())
        await module.owner.install_task
        assert code in bot.replies[-1]
        assert module.owner.manager.activate_calls == 0
        assert (await module.status_dota2uid())["bootstrap_error"] == code
        await module.stop_dota2uid()

    run_async(check())


def test_concurrent_install_returns_progress_and_close_waits_for_preparation(host, run_async):
    import asyncio

    module = host.load()

    async def check():
        manager = module.owner.manager
        manager.gate, manager.finished = asyncio.Event(), asyncio.Event()
        bot = CapturingBot()
        await asyncio.gather(
            module.install_dota2uid(bot, SyntheticEvent()),
            module.install_dota2uid(bot, SyntheticEvent()),
        )
        await asyncio.sleep(0)
        assert manager.prepare_calls == [True]
        assert len(bot.replies) == 2 and "正在准备" in bot.replies[-1]
        closing = asyncio.create_task(module.stop_dota2uid())
        await asyncio.sleep(0)
        assert module.owner.closed and not closing.done()
        manager.gate.set()
        await closing
        assert module.owner.install_task.done() and manager.close_calls == 1
        assert len(bot.replies) == 2
        await module.stop_dota2uid()
        assert manager.close_calls == 1
        assert (await module.status_dota2uid())["state"] == "stopped"

    run_async(check())


def test_cold_activation_waiting_config_and_help_forwarding_preserve_data(
    host, config_path, run_async
):
    config = host.data / "config.toml"
    config.write_text(config_path.read_text("utf-8").replace("synthetic-token", ""), "utf-8")
    module = host.load()
    database = host.data / "bindings.sqlite3"
    database.write_bytes(b"synthetic-existing-database")
    original = config.read_bytes(), database.read_bytes()

    async def check():
        await module.start_dota2uid()
        await module.start_dota2uid()
        assert module.owner.manager.prepare_calls == [False]
        assert module.owner.manager.activate_calls == 1
        assert (await module.status_dota2uid())["state"] == "awaiting_config"
        assert (await module.status_dota2uid())["runtime_state"] == "runtime_available"
        assert "等待配置" in module.owner.status_text()
        assert all(len(collection) == 1 for collection in host.hooks.values())
        assert "do绑定" in host.commands() and "do下载素材" in host.commands()
        helpers = [
            service
            for service in host.registry.lst.values()
            if "do帮助" in service.TL.get("command", {})
        ]
        assert len(helpers) == 1 and helpers[0].name == "Dota2UID帮助入口"
        bot = CapturingBot()
        await host.commands()["do帮助"][0](bot, SyntheticEvent(command="do帮助", user_pm=6))
        assert "等待配置" in bot.replies[-1]
        await module.close_dota2uid()
        before = len(bot.replies)
        await module.owner.business.command_dota2uid(
            bot, SyntheticEvent(command="do绑定", text="123")
        )
        assert len(bot.replies) == before
        assert (await module.status_dota2uid())["client_closed"] is True

    run_async(check())
    assert (config.read_bytes(), database.read_bytes()) == original


def test_ready_business_subscription_job_and_hero_dispatch(
    host, config_path, monkeypatch, run_async
):
    (host.data / "config.toml").write_text(
        "subscriptions_enabled=true\n" + config_path.read_text("utf-8"), "utf-8"
    )
    module = host.load()

    async def check():
        await module.start_dota2uid()
        await module.start_dota2uid()
        assert (await module.status_dota2uid())["state"] == "ready"
        assert len(host.jobs) == 1
        dispatched = []

        async def dispatch(caller, keyword, text, send):
            dispatched.append((keyword, text, caller.is_admin))

        monkeypatch.setattr(module.owner.business.runtime, "dispatch", dispatch)
        bot = CapturingBot()
        await module.help_dota2uid(bot, SyntheticEvent(command="do菜单", user_pm=6))
        await module.owner.business.command_dota2uid(
            bot, SyntheticEvent(command="AM", regex_dict={"hero": "AM"})
        )
        assert dispatched == [("do菜单", "", False), ("do出装", "AM", True)]
        await module.disable_dota2uid(bot, SyntheticEvent())
        assert not host.jobs and module.owner.business.runtime.client_closed

    run_async(check())


def test_existing_module_conflict_prevents_business_activation(host, run_async):
    module = host.load()
    module.owner.manager.activate_error = "module_conflict"

    async def check():
        await module.start_dota2uid()
        assert module.owner.business is None
        assert (await module.status_dota2uid())["bootstrap_error"] == "module_conflict"
        assert "Dota2UID账号与查询" not in host.registry.lst
        bot = CapturingBot()
        await module.core_status_dota2uid(bot, SyntheticEvent())
        assert "module_conflict" in bot.replies[-1]
        await module.stop_dota2uid()

    run_async(check())


def test_business_import_failure_rolls_back_only_new_business_registrations(host, run_async):
    (host.plugin / "_dota2forge_business.py").write_text(
        'from gsuid_core.sv import SV\nqueries = SV("Dota2UID账号与查询", pm=6)\n'
        '@queries.on_command("do绑定", block=True)\n'
        'async def query(bot, ev): pass\nraise RuntimeError("synthetic private details")\n',
        "utf-8",
    )
    module = host.load()

    async def check():
        await module.start_dota2uid()
        assert module.owner.business is None
        assert (await module.status_dota2uid())["state"] == "business_failed"
        assert "Dota2UID账号与查询" not in host.registry.lst
        assert all(
            service.name != "Dota2UID账号与查询"
            for children in host.registry.detail_lst.values()
            for service in children
        )
        assert host.bumps == [True]
        assert set(host.commands()) == {"do安装核心", "do核心状态", "do停用", "do帮助", "do菜单"}
        assert host.package + "._dota2forge_business" not in sys.modules
        bot = CapturingBot()
        await module.core_status_dota2uid(bot, SyntheticEvent())
        assert "business_import" in bot.replies[-1]
        assert "synthetic private details" not in bot.replies[-1]
        await module.stop_dota2uid()

    run_async(check())


@pytest.mark.parametrize("native_cleanup", [False, True])
def test_live_hot_reload_requires_restart_and_restores_management_hooks(
    host, run_async, native_cleanup
):
    module = host.load()

    async def check():
        await module.start_dota2uid()
        old_business = module.owner.business
        if native_cleanup:
            for collection in host.hooks.values():
                collection.clear()
            host.registry.lst.clear()
            for children in host.registry.detail_lst.values():
                children.clear()
            host.app.router.routes.clear()
        reloaded = host.load()
        assert reloaded.owner is module.owner and reloaded.owner.restart_required
        await reloaded.start_dota2uid()
        assert reloaded.owner.business is old_business
        assert reloaded.owner.manager.prepare_calls == [False]
        assert all(len(collection) == 1 for collection in host.hooks.values())
        assert len(host.app.router.routes) == 2
        assert {route.path for route in host.app.router.routes} == {
            "/api/dota2uid/status",
            "/api/dota2uid/stop",
        }
        bot = CapturingBot()
        await reloaded.core_status_dota2uid(bot, SyntheticEvent())
        assert "完整重启" in bot.replies[-1]
        await reloaded.help_dota2uid(bot, SyntheticEvent(command="do帮助", user_pm=6))
        assert "do安装核心" in bot.replies[-1]
        await reloaded.close_dota2uid()

    run_async(check())


def test_completed_explicit_stop_allows_configuration_reload(host, config_path, run_async):
    config = host.data / "config.toml"
    config.write_text(config_path.read_text("utf-8").replace("synthetic-token", ""), "utf-8")
    module = host.load()
    legacy = config.read_bytes()
    retained = host.data / "synthetic-existing-data"
    retained.write_bytes(b"preserved")

    async def check():
        await module.start_dota2uid()
        assert (await module.status_dota2uid())["state"] == "awaiting_config"
        await module.stop_dota2uid()
        assert module.settings.set_config("stratz_token", "synthetic-token")
        reloaded = host.load()
        assert reloaded.owner is not module.owner
        assert not reloaded.owner.restart_required
        assert all(len(collection) == 1 for collection in host.hooks.values())
        await reloaded.start_dota2uid()
        assert (await reloaded.status_dota2uid())["state"] == "ready"
        assert reloaded.owner.manager.prepare_calls == [False]
        assert reloaded.owner.manager.activate_calls == 1
        assert len(host.app.router.routes) == 2
        await reloaded.stop_dota2uid()
        assert retained.read_bytes() == b"preserved"
        assert config.read_bytes() == legacy

    run_async(check())


def test_unreadable_configuration_preserves_diagnostics_and_original_file(host, run_async):
    config = host.data / "config.toml"
    config.write_text('stratz_token = "synthetic-secret"\nbroken = [', "utf-8")
    original = config.read_bytes()
    module = host.load()
    assert module.settings is None
    assert "do核心状态" in host.commands()
    assert not (host.data / "config.json").exists()

    async def check():
        await module.start_dota2uid()
        result = await module.status_dota2uid()
        assert result["state"] == "failed" and not result["configuration_available"]
        assert result["client_closed"]
        bot = CapturingBot()
        await module.core_status_dota2uid(bot, SyntheticEvent())
        assert "原文件已保留" in bot.replies[-1]
        assert "synthetic-secret" not in bot.replies[-1]
        await module.stop_dota2uid()

    run_async(check())
    assert config.read_bytes() == original


def test_startup_failure_closes_partial_business_and_preserves_management(host, run_async):
    backend = sys.modules[host.package + "._dota2forge_runtime"]
    backend.cleanup_probe = []
    (host.plugin / "_dota2forge_business.py").write_text(
        "from gsuid_core.sv import SV\nfrom ._dota2forge_runtime import cleanup_probe\n"
        'queries = SV("Dota2UID账号与查询", pm=6)\n'
        '@queries.on_command("do绑定", block=True)\nasync def command(bot, ev): pass\n'
        'async def start_dota2uid(): raise RuntimeError("synthetic-start-error")\n'
        'async def stop_dota2uid(): cleanup_probe.append("closed")\n',
        "utf-8",
    )
    module = host.load()

    async def check():
        await module.start_dota2uid()
        assert backend.cleanup_probe == ["closed"]
        assert module.owner.business is None
        assert "Dota2UID账号与查询" not in host.registry.lst
        assert len(host.app.router.routes) == 2
        assert all(len(collection) == 1 for collection in host.hooks.values())
        assert "do安装核心" in host.commands()
        await module.stop_dota2uid()

    run_async(check())


def test_install_during_startup_reports_progress_and_shutdown_prevents_activation(host, run_async):
    import asyncio

    module = host.load()

    async def check():
        manager = module.owner.manager
        manager.gate, manager.finished = asyncio.Event(), asyncio.Event()
        manager.started = asyncio.Event()
        starting = asyncio.create_task(module.start_dota2uid())
        await manager.started.wait()
        bot = CapturingBot()
        await module.install_dota2uid(bot, SyntheticEvent())
        assert manager.prepare_calls == [False] and "正在准备" in bot.replies[-1]
        closing = asyncio.create_task(module.stop_dota2uid())
        await asyncio.sleep(0)
        manager.gate.set()
        await asyncio.gather(starting, closing)
        assert manager.activate_calls == 0 and module.owner.business is None
        assert module.owner.start_task is None

    run_async(check())


def test_install_with_active_business_only_prepares_and_waits_for_cold_start(
    host, config_path, run_async
):
    (host.data / "config.toml").write_text(config_path.read_text("utf-8"), "utf-8")
    module = host.load()

    async def check():
        await module.start_dota2uid()
        business = module.owner.business
        bot = CapturingBot()
        await module.install_dota2uid(bot, SyntheticEvent())
        await module.owner.install_task
        assert module.owner.manager.prepare_calls == [False, True]
        assert module.owner.manager.activate_calls == 1
        assert module.owner.business is business and not business.runtime.client_closed
        status = await module.status_dota2uid()
        assert status["state"] == "pending_restart" and status["business_state"] == "ready"
        await module.start_dota2uid()
        assert module.owner.manager.activate_calls == 1
        await module.stop_dota2uid()

    run_async(check())


def test_stopped_reload_still_rejects_loaded_different_generation(host, run_async):
    module = host.load()

    async def check():
        await module.start_dota2uid()
        await module.stop_dota2uid()
        reloaded = host.load()
        reloaded.owner.manager.activate_error = "module_conflict"
        await reloaded.start_dota2uid()
        assert reloaded.owner.business is None
        assert (await reloaded.status_dota2uid())["bootstrap_error"] == "module_conflict"
        bot = CapturingBot()
        await reloaded.core_status_dota2uid(bot, SyntheticEvent())
        assert "module_conflict" in bot.replies[-1]
        await reloaded.stop_dota2uid()

    run_async(check())


def test_completion_reply_failure_does_not_erase_prepared_runtime(host, run_async):
    module = host.load()

    class FailingCompletionBot(CapturingBot):
        async def send(self, text):
            if self.replies:
                raise RuntimeError("synthetic transport failure")
            await super().send(text)

    async def check():
        bot = FailingCompletionBot()
        await module.install_dota2uid(bot, SyntheticEvent())
        await module.owner.install_task
        status = await module.status_dota2uid()
        assert status["state"] == "pending_restart" and status["bootstrap_error"] == ""
        assert status["prepared"] is True
        await module.stop_dota2uid()

    run_async(check())


@pytest.mark.parametrize("repeat_cancel", [False, True])
def test_cancelled_start_closes_partial_business_and_rolls_back_registrations(
    host, run_async, repeat_cancel
):
    import asyncio

    backend = sys.modules[host.package + "._dota2forge_runtime"]
    backend.cleanup_probe = []
    (host.plugin / "_dota2forge_business.py").write_text(
        "from gsuid_core.sv import SV\n"
        "from ._dota2forge_runtime import (\n"
        "start_gate, start_entered, cleanup_probe, close_gate, close_entered)\n"
        'queries = SV("Dota2UID账号与查询", pm=6)\n'
        '@queries.on_command("do绑定", block=True)\nasync def command(bot, ev): pass\n'
        "async def start_dota2uid():\n start_entered.set()\n await start_gate.wait()\n"
        "async def stop_dota2uid():\n close_entered.set()\n await close_gate.wait()\n"
        ' cleanup_probe.append("closed")\n',
        "utf-8",
    )
    module = host.load()

    async def check():
        backend.start_gate = asyncio.Event()
        backend.start_entered = asyncio.Event()
        backend.close_gate, backend.close_entered = asyncio.Event(), asyncio.Event()
        starting = asyncio.create_task(module.start_dota2uid())
        await backend.start_entered.wait()
        assert "Dota2UID账号与查询" in host.registry.lst
        starting.cancel()
        await backend.close_entered.wait()
        if repeat_cancel:
            starting.cancel()
            await asyncio.sleep(0)
        assert not starting.done()
        backend.close_gate.set()
        with pytest.raises(asyncio.CancelledError):
            await starting
        assert backend.cleanup_probe == ["closed"]
        assert "Dota2UID账号与查询" not in host.registry.lst
        assert host.package + "._dota2forge_business" not in sys.modules
        assert module.owner.business is None and module.owner.start_task is None
        assert (await module.status_dota2uid())["bootstrap_error"] == "cancelled"
        assert set(host.commands()) == {"do安装核心", "do核心状态", "do停用", "do帮助", "do菜单"}
        await module.stop_dota2uid()

    run_async(check())


def test_shutdown_waits_only_for_plugin_start_not_the_host_callers_later_work(host, run_async):
    import asyncio

    backend = sys.modules[host.package + "._dota2forge_runtime"]
    backend.cleanup_probe = []
    (host.plugin / "_dota2forge_business.py").write_text(
        "from gsuid_core.sv import SV\n"
        "from ._dota2forge_runtime import start_gate, start_entered, cleanup_probe\n"
        'queries = SV("Dota2UID账号与查询", pm=6)\n'
        "async def start_dota2uid():\n start_entered.set()\n await start_gate.wait()\n"
        'async def stop_dota2uid(): cleanup_probe.append("closed")\n',
        "utf-8",
    )
    module = host.load()

    async def check():
        backend.start_gate, backend.start_entered = asyncio.Event(), asyncio.Event()
        later_work = asyncio.Event()

        async def host_caller():
            await module.start_dota2uid()
            await later_work.wait()

        caller = asyncio.create_task(host_caller())
        await backend.start_entered.wait()
        closing = asyncio.create_task(module.stop_dota2uid())
        await asyncio.sleep(0)
        backend.start_gate.set()
        await asyncio.wait_for(closing, timeout=2)
        assert not caller.done()
        assert backend.cleanup_probe == ["closed"]
        assert module.owner.business is None
        assert "Dota2UID账号与查询" not in host.registry.lst
        later_work.set()
        await caller

    run_async(check())
