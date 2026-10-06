"""Both installed-library runtimes consume the same hero/item contract offline."""

import httpx
import pytest
from dota2forge_renderer import AsyncRenderer, PillowRenderer, RenderError


def data():
    return {
        "start_game_items": {"1": 8, "44": 0, "999999": 2},
        "early_game_items": {},
        "mid_game_items": None,
        "late_game_items": {"1": 3},
    }


def make_runtime(adapter, tmp_path, client, image_mode, renderer_factory=None):
    if adapter == "Dota2UID":
        from Dota2UID.commands import Caller
        from Dota2UID.runtime import Runtime

        config = tmp_path / "config.toml"
        config.write_text(
            'namespace="test-hero"\nstratz_token="synthetic-token"\ntimeout_seconds=10\n'
            f'reply_mode="{"image" if image_mode else "text"}"\n[platforms]\nonebot="qq"\n',
            "utf-8",
        )
        return Runtime(
            config, client_factory=lambda: client, renderer_factory=renderer_factory
        ), Caller("onebot", "bot", "user", "connection")
    from astrbot_plugin_dota2forge.identity import Caller
    from astrbot_plugin_dota2forge.runtime import Runtime

    return Runtime(
        {"stratz_token": "synthetic-token", "reply_mode": "image" if image_mode else "text"},
        tmp_path,
        client_factory=lambda: client,
        renderer_factory=renderer_factory,
    ), Caller("qq", "connection", "bot", "user", conversation_kind="FriendMessage")


@pytest.mark.parametrize("adapter", ["Dota2UID", "astrbot_plugin_dota2forge"])
@pytest.mark.parametrize(
    "command,name", [("do斧王出装", ""), ("doAM出装", ""), ("do出装", "Shadow Fiend")]
)
def test_both_runtimes_resolve_without_binding_and_only_request_opendota(
    adapter, command, name, tmp_path, run_async
):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == "GET" and request.url.host == "api.opendota.com"
        assert "Authorization" not in request.headers
        return httpx.Response(200, json=data())

    async def check():
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        runtime, caller = make_runtime(adapter, tmp_path, client, False)
        replies = []

        async def send(reply):
            replies.append(reply)

        await runtime.dispatch(caller, command, name, send)
        text = replies[0].text
        assert "热门出装" in text and "OPENDOTA" in text and "STRATZ" not in text
        assert "闪烁匕首：8 次" in text and "动物信使" not in text
        assert "装备 ID 999999：2 次" in text and "：0 次" in text
        assert "本次无物品统计" in text and "统计未知（来源未返回）" in text
        assert "补丁" in text and "未知" in text and "热门不等于最优" in text
        assert len(calls) == 1
        before = len(calls)
        await runtime.dispatch(caller, "do猴子出装", "", send)
        assert "歧义" in replies[-1].text and "幻影长矛手" in replies[-1].text
        await runtime.dispatch(caller, "do不存在出装", "", send)
        assert "未识别" in replies[-1].text and len(calls) == before
        await runtime.close()
        assert runtime.client_closed

    run_async(check())


@pytest.mark.parametrize("adapter", ["Dota2UID", "astrbot_plugin_dota2forge"])
@pytest.mark.parametrize("fallback", [False, True])
def test_image_and_render_error_text_fallback_reuse_single_success(
    adapter, fallback, tmp_path, run_async
):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=data())

    class FailedRenderer(PillowRenderer):
        def render(self, card):
            raise RenderError()

    async def check():
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        runtime, caller = make_runtime(
            adapter,
            tmp_path,
            client,
            True,
            lambda: AsyncRenderer(FailedRenderer() if fallback else PillowRenderer()),
        )
        replies = []

        async def send(reply):
            replies.append(reply)

        await runtime.dispatch(caller, "do斧王出装", "", send)
        assert len(calls) == 1
        if fallback:
            assert "OPENDOTA" in replies[0].text
        else:
            assert replies[0].artifact.height == 1674 and replies[0].artifact.data.startswith(
                b"\x89PNG"
            )
        await runtime.close()
        assert client.is_closed

    run_async(check())


@pytest.mark.parametrize("adapter", ["Dota2UID", "astrbot_plugin_dota2forge"])
def test_hero_http_failure_does_not_send_success_or_retry(adapter, tmp_path, run_async):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "20"})

    async def check():
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        runtime, caller = make_runtime(adapter, tmp_path, client, True)
        replies = []

        async def send(reply):
            replies.append(reply)

        await runtime.dispatch(caller, "do斧王出装", "", send)
        assert len(calls) == 1 and "OPENDOTA" in replies[0].text and "20" in replies[0].text
        assert "热门出装" not in replies[0].text
        await runtime.close()

    run_async(check())
