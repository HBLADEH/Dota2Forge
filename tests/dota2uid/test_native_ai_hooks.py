"""H14's actual empty-query boundary must use the trusted native event."""

from importlib.resources import files
from types import ModuleType, SimpleNamespace

import pytest


@pytest.mark.parametrize("query", ["", "这把有什么问题？"])
def test_tool_hook_accepts_sdk_empty_query_without_changing_reply_trigger(
    monkeypatch, run_async, query
):
    hooks = {}
    received = []
    session = SimpleNamespace(history=["synthetic", "synthetic"])

    def install(name, **values):
        module = ModuleType(name)
        module.__dict__.update(values)
        monkeypatch.setitem(__import__("sys").modules, name, module)

    def on_hook(point, **_):
        def decorate(fn):
            hooks[point] = fn
            return fn

        return decorate

    def review_hint(_caller, _session, _generation, selected_query, history_count):
        received.append((selected_query, history_count))
        return "synthetic-source-hint"

    points = SimpleNamespace(AFTER_CONTEXT="context", ASSEMBLE_TOOLS="tools")
    install(
        "gsuid_core.ai_core.configs.ai_config",
        ai_config=SimpleNamespace(get_config=lambda _: SimpleNamespace(data=True)),
    )
    install("gsuid_core.ai_core.hooks", AgentHookPoint=points, on_agent_hook=on_hook)
    install("gsuid_core.ai_core.models", ToolContext=SimpleNamespace)
    install("gsuid_core.ai_core.register", ai_tools=lambda **_: lambda fn: fn)
    install(
        "gsuid_core.ai_core.session_registry",
        get_ai_session_registry=lambda: SimpleNamespace(get_ai_session=lambda _: session),
    )
    install("gsuid_core.utils.resource_manager", RM=SimpleNamespace())
    install(
        "gsuid_core.ai_core.agent_node.tool_scope",
        get_tool_scope=lambda _: SimpleNamespace(plugin_enabled=lambda _: True),
    )
    namespace = {"__name__": "synthetic_native_bridge"}
    source = files("Dota2UID").joinpath("host_ai.py.template").read_text("utf-8")
    exec(compile(source, "host_ai.py.template", "exec"), namespace)
    runtime = SimpleNamespace(review_hint=review_hint)
    namespace["register_native_ai"](runtime, lambda ev: ev)
    ensured = []
    event = SimpleNamespace(raw_text="这把有什么问题？", is_tome=True)
    context = SimpleNamespace(
        ev=event,
        is_subagent=False,
        is_framework=False,
        persona_name=None,
        session_id="synthetic-session",
        query=query,
        ensure_tools=lambda *names: ensured.extend(names),
    )
    run_async(hooks["tools"](context))
    assert received == [("这把有什么问题？", 2)]
    assert ensured == ["get_dota2_review_context", "render_dota2_review_data"]
    assert event.is_tome is True and event.raw_text == "这把有什么问题？"
