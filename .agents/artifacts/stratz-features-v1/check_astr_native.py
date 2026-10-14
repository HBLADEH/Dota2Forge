"""Real AstrBot SDK registration/requests with synthetic source and no model/platform sends."""

import ast
import asyncio
import importlib.util
import json
import os
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]


async def check(directory):
    from astrbot import __version__
    from astrbot.core.agent.tool import ToolSet
    from astrbot.core.platform.astr_message_event import AstrMessageEvent
    from astrbot.core.provider.entities import ProviderRequest
    from astrbot.core.provider.register import llm_tools
    from astrbot.core.star.star_handler import star_handlers_registry
    from dota2forge_core.feature_tools import TOOL_NAMES, tool_schema

    # Reuse only the two pure synthetic response constructors, without importing pytest
    # or adding development dependencies to the user's SDK interpreter.
    fixture_tree = ast.parse((ROOT / "tests/core/test_hero_features.py").read_text("utf-8"))
    fixture_nodes = [
        node
        for node in fixture_tree.body
        if isinstance(node, ast.FunctionDef) and node.name in {"raw_match", "mock_reply"}
    ]
    fixture_namespace = {
        "json": json,
        "NOW": datetime(2026, 10, 10, 12, tzinfo=UTC),
        "timedelta": timedelta,
    }
    exec(
        compile(ast.Module(fixture_nodes, type_ignores=[]), "synthetic-fixtures", "exec"),
        fixture_namespace,
    )
    mock_reply = fixture_namespace["mock_reply"]

    import httpx
    from astrbot_plugin_dota2forge.runtime import Runtime

    bridge = (
        ROOT
        / "adapters/astrbot_plugin_dota2forge/src/astrbot_plugin_dota2forge/host/main.py.template"
    )
    spec = importlib.util.spec_from_file_location(
        "synthetic_native_astr",
        bridge,
        loader=SourceFileLoader("synthetic_native_astr", str(bridge)),
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    tools = [t for t in llm_tools.func_list if t.name in TOOL_NAMES]
    assert {t.name for t in tools} == set(TOOL_NAMES)
    handlers = star_handlers_registry.get_handlers_by_module_name(spec.name)
    assert any(h.handler_name == "review_turn_hint" for h in handlers)

    class Conversations:
        def __init__(self):
            self.value = SimpleNamespace(cid="synthetic-native", created_at=1, history="[]")

        async def get_curr_conversation_id(self, _):
            return self.value.cid

        async def get_conversation(self, _, cid):
            assert cid == self.value.cid
            return self.value

    manager = Conversations()

    async def provider(_):
        return "synthetic-model-not-called"

    context = SimpleNamespace(conversation_manager=manager, get_current_chat_provider_id=provider)
    plugin = module.Dota2ForgePlugin(context, {})

    def handler(request):
        query = json.loads(request.content)["query"]
        if "radiantNetworthLeads" in query:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "match": {
                            "id": 22,
                            "radiantNetworthLeads": [-100, 0, 200],
                            "radiantExperienceLeads": [0, 10, 20],
                            "players": [
                                {
                                    "playerSlot": 0,
                                    "steamAccountId": 321,
                                    "stats": {
                                        "networthPerMinute": [0, 1000, 2100],
                                        "itemPurchases": [{"time": -60, "itemId": 4}],
                                    },
                                }
                            ],
                        }
                    }
                },
            )
        return httpx.Response(200, json=mock_reply(request))

    plugin.runtime = Runtime(
        {"stratz_token": "synthetic", "asset_download_mode": "manual"},
        Path(directory),
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    await plugin.runtime.start()

    class Event:
        unified_msg_origin = "synthetic:FriendMessage:synthetic-user"
        request_llm = AstrMessageEvent.request_llm

        def __init__(self):
            self.query = "do复盘 22 斧王"
            self.sent = []

        def get_self_id(self):
            return "synthetic-bot"

        def get_sender_id(self):
            return "synthetic-user"

        def get_platform_id(self):
            return "synthetic-connection"

        def get_platform_name(self):
            return "qq"

        def get_message_type(self):
            return SimpleNamespace(value="FriendMessage")

        def get_group_id(self):
            return ""

        def get_messages(self):
            return []

        def is_admin(self):
            return False

        def get_message_str(self):
            return self.query

        def chain_result(self, components):
            return components

        async def send(self, value):
            self.sent.append(value)  # Synthetic capture; never calls a platform client.

    event = Event()
    initial = [value async for value in plugin.review_match(event, "22 斧王")]
    assert len(initial) == 1 and isinstance(initial[0], ProviderRequest)
    assert initial[0].conversation is manager.value
    history = [
        {"role": "user", "content": initial[0].prompt},
        {"role": "assistant", "content": "Synthetic review"},
    ]
    manager.value.history = json.dumps(history)
    req = ProviderRequest(func_tool=ToolSet(tools))
    event.query = "为什么？"
    await plugin.review_turn_hint(event, req)
    assert req.extra_user_content_parts
    assert all(tool.parameters == tool_schema(tool.name) for tool in tools)
    for topic in ("laning", "items"):
        result = json.loads(await plugin.get_dota2_review_context(event, topic=topic))
        assert result["match_id"] == 22 and result["target_slot"] == 0
        history.append({"role": "tool", "content": json.dumps(result)})
    figure = json.loads(await plugin.render_dota2_review_data(event, "economy", end_seconds=600))
    assert len(event.sent) == 1 and figure["chart_series"]
    history.append({"role": "tool", "content": json.dumps(figure)})
    final = json.loads(await plugin.get_dota2_review_context(event, topic="economy"))
    assert final["match_id"] == 22
    history.append({"role": "tool", "content": json.dumps(final)})
    assert sum("chart_kind" in item["content"] for item in history) == 1
    manager.value.history = "[]"
    reset = ProviderRequest(func_tool=ToolSet(tools))
    await plugin.review_turn_hint(event, reset)
    assert not reset.extra_user_content_parts
    assert "error" in json.loads(await plugin.get_dota2_review_context(event))
    await plugin.terminate()
    assert plugin.runtime.client_closed
    report = {
        "sdk_version": __version__,
        "real_decorators_and_toolset": True,
        "explicit_schemas": True,
        "real_provider_request": True,
        "same_conversation_five_rounds": True,
        "figure_text_fact_once": True,
        "same_id_history_reset": True,
        "client_closed": True,
        "conversation_manager": "synthetic",
        "real_model": False,
        "real_platform_sends": False,
    }
    (Path(__file__).parent / "astr-native.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    sys.path[:0] = [
        str(ROOT / path)
        for path in (
            "packages/dota2forge-core/src",
            "packages/dota2forge-renderer/src",
            "packages/dota2forge-assets/src",
            "adapters/astrbot_plugin_dota2forge/src",
        )
    ]
    sys.path.append("D:/AstrBot/backend/app")
    with tempfile.TemporaryDirectory(prefix="dota2forge-native-sdk-") as directory:
        os.environ["ASTRBOT_ROOT"] = directory
        asyncio.run(check(directory))
