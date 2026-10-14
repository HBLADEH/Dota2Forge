"""Real GsCore decorators/schema/hooks; side-effect dependencies isolated, no model/sends."""

import ast
import asyncio
import json
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
SDK = Path("D:/bot/gsuid_core")


def module(name, **values):
    value = ModuleType(name)
    value.__dict__.update(values)
    sys.modules[name] = value
    return value


def package(name, path):
    return module(name, __path__=[str(path)])


async def check(directory):
    import httpx
    from dota2forge_core.feature_tools import TOOL_NAMES
    from Dota2UID.commands import Caller
    from Dota2UID.runtime import Runtime
    from gsuid_core.ai_core.agent_node.tool_scope import ToolScope
    from gsuid_core.ai_core.hooks.models import AgentHookContext
    from gsuid_core.ai_core.hooks.points import AgentHookPoint
    from gsuid_core.ai_core.hooks.registry import hooks_for
    from gsuid_core.ai_core.models import ToolContext
    from gsuid_core.ai_core.register import get_registered_tools

    fixture_tree = ast.parse((ROOT / "tests/core/test_hero_features.py").read_text("utf-8"))
    fixture_nodes = [
        node
        for node in fixture_tree.body
        if isinstance(node, ast.FunctionDef) and node.name in {"raw_match", "mock_reply"}
    ]
    namespace = {
        "json": json,
        "NOW": datetime(2026, 10, 10, 12, tzinfo=UTC),
        "timedelta": timedelta,
    }
    exec(
        compile(ast.Module(fixture_nodes, type_ignores=[]), "synthetic-fixtures", "exec"), namespace
    )

    def handler(request):
        return httpx.Response(200, json=namespace["mock_reply"](request))

    config = Path(directory) / "config.toml"
    config.write_text(
        'namespace="sdk-synthetic"\nstratz_token="synthetic"\ntimeout_seconds=10\nreply_mode="image"\nasset_download_mode="manual"\n[platforms]\nonebot="qq"\n',
        encoding="utf-8",
    )
    runtime = Runtime(
        config, client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    await runtime.start()
    plugin = module("gsuid_core.plugins.Dota2UID._dota2forge_ai")
    plugin.__file__ = str(ROOT / "adapters/Dota2UID/src/Dota2UID/host_ai.py.template")
    exec(
        compile(Path(plugin.__file__).read_text("utf-8"), plugin.__file__, "exec"), plugin.__dict__
    )

    def caller(event):
        return Caller(
            "onebot", "synthetic-bot", "synthetic-user", "connection", conversation_kind="direct"
        )

    native = plugin.register_native_ai(runtime, caller)
    registered = get_registered_tools()["common"]
    assert set(TOOL_NAMES) <= set(registered)
    assert all(registered[name].plugin == "Dota2UID" for name in TOOL_NAMES)
    assert all(
        "ctx" not in registered[name].tool.function_schema.json_schema["properties"]
        for name in TOOL_NAMES
    )
    session = SimpleNamespace(history=["Synthetic user", "Synthetic assistant"])
    SESSIONS["synthetic-native"] = session
    event = SimpleNamespace(raw_text="do复盘 22 斧王")
    ctx = ToolContext(ev=event, parent_session_id="synthetic-native", allow_user_outbound=True)

    async def invoke(name, **args):
        result = await registered[name].tool.function(SimpleNamespace(deps=ctx), **args)
        return json.loads(result)

    first = await invoke("get_dota2_review_context", match_id="22", hero_name="斧王")
    assert first["match_id"] == 22
    for topic in ("laning", "items"):
        assert (await invoke("get_dota2_review_context", topic=topic))["match_id"] == 22
    figure = await invoke(
        "render_dota2_review_data", kind="items", start_seconds=-120, end_seconds=600
    )
    assert figure["image_resource_id"] in RESOURCES
    assert figure["image_delivery"].startswith("尚未发送")
    assert (await invoke("get_dota2_review_context", topic="economy"))["target_slot"] == 0
    hint = AgentHookContext(
        AgentHookPoint.AFTER_CONTEXT, ev=event, session_id="synthetic-native", query="为什么？"
    )
    for hook in hooks_for(AgentHookPoint.AFTER_CONTEXT):
        if hook.module == plugin.__name__:
            await hook.func(hint)
    assert len(hint.hints) == 1
    event.raw_text = "这把有什么问题？"
    tools = AgentHookContext(AgentHookPoint.ASSEMBLE_TOOLS, ev=event, session_id="synthetic-native")
    assert tools.query == ""  # Actual SDK H14 leaves query empty.
    for hook in hooks_for(AgentHookPoint.ASSEMBLE_TOOLS):
        if hook.module == plugin.__name__:
            await hook.func(tools)
    assert tools.ensured_tools == ["get_dota2_review_context", "render_dota2_review_data"]
    ctx.tool_scope = ToolScope.from_spec(["!Dota2UID", "*"])
    assert (await invoke("get_dota2_review_context"))["error"] == "tool_disabled_by_persona"
    ctx.tool_scope = None
    ctx.allow_user_outbound = False
    assert (await invoke("get_dota2_review_context"))[
        "error"
    ] == "invalid_arguments_or_native_session"
    ctx.allow_user_outbound = True
    SESSIONS["synthetic-native"] = SimpleNamespace(history=[])
    assert "error" in await invoke("get_dota2_review_context")
    await native.close()
    await runtime.close()
    assert all(name not in get_registered_tools().get("common", {}) for name in TOOL_NAMES)
    assert not any(h.module == plugin.__name__ for p in AgentHookPoint for h in hooks_for(p))
    assert runtime.client_closed
    report = {
        "real_registration_and_pydantic_schema": True,
        "real_hook_registry": True,
        "trusted_context_hidden": True,
        "same_session_five_rounds": True,
        "generic_followup_tool_recall": True,
        "tool_hook_empty_query_event_fallback": True,
        "persona_disabled_respected": True,
        "subagent_outbound_rejected": True,
        "same_id_generation_reset": True,
        "unregister_and_close": True,
        "side_effect_dependencies": "synthetic",
        "real_model": False,
        "real_platform_sends": False,
    }
    (Path(__file__).parent / "gscore-native.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    sys.path[:0] = [
        str(ROOT / p)
        for p in (
            "packages/dota2forge-core/src",
            "packages/dota2forge-renderer/src",
            "packages/dota2forge-assets/src",
            "adapters/Dota2UID/src",
        )
    ]
    package("gsuid_core", SDK / "gsuid_core")
    package("gsuid_core.ai_core", SDK / "gsuid_core/ai_core")
    package("gsuid_core.ai_core.configs", SDK / "gsuid_core/ai_core/configs")
    package("gsuid_core.ai_core.hooks", SDK / "gsuid_core/ai_core/hooks")
    package("gsuid_core.utils", SDK / "gsuid_core/utils")
    module("gsuid_core.i18n", t=lambda key, **kwargs: key)
    logger = SimpleNamespace(
        **{
            name: lambda *args, **kwargs: None
            for name in ("info", "debug", "trace", "warning", "error")
        }
    )
    module("gsuid_core.logger", logger=logger, hl_plugin=lambda value: value)
    module("gsuid_core.bot", Bot=type("Bot", (), {}))
    from gsuid_core.models import Message

    module("gsuid_core.segment", Message=Message)

    async def serialize(_bot, result):
        return result if isinstance(result, str) else json.dumps(result)

    module("gsuid_core.ai_core.utils", handle_tool_result=serialize)
    module(
        "gsuid_core.ai_core.tool_health",
        is_tool_frozen=lambda _: False,
        record_tool_failure=lambda *args: None,
        record_tool_success=lambda *args: None,
    )
    module(
        "gsuid_core.ai_core.configs.ai_config",
        ai_config=SimpleNamespace(get_config=lambda _: SimpleNamespace(data=True)),
    )
    SESSIONS, RESOURCES = {}, {}
    module(
        "gsuid_core.ai_core.session_registry",
        get_ai_session_registry=lambda: SimpleNamespace(
            get_ai_session=lambda key: SESSIONS.get(key)
        ),
    )

    def register_resource(data):
        key = "img_synthetic_" + str(len(RESOURCES))
        RESOURCES[key] = data
        return key

    module("gsuid_core.utils.resource_manager", RM=SimpleNamespace(register=register_resource))
    from gsuid_core.ai_core.hooks.points import AgentHookPoint
    from gsuid_core.ai_core.hooks.registry import drop_hooks_for_module, on_agent_hook

    hooks = sys.modules["gsuid_core.ai_core.hooks"]
    hooks.AgentHookPoint, hooks.on_agent_hook, hooks.drop_hooks_for_module = (
        AgentHookPoint,
        on_agent_hook,
        drop_hooks_for_module,
    )
    with tempfile.TemporaryDirectory(prefix="dota2forge-gscore-native-") as directory:
        asyncio.run(check(directory))
