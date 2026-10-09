"""AstrBot-neutral consumer tests; no AstrBot SDK or network is required."""

import json

import httpx
import pytest
from astrbot_plugin_dota2forge.application import AstrApplication, AstrImageReply, AstrTextReply
from dota2forge_core import Dota2Service, MatchAnalysisService, MatchDetailService
from dota2forge_core.infrastructure.stratz import (
    MATCH_ANALYSIS_QUERY,
    MATCH_DETAIL_QUERY,
    StratzProvider,
)
from dota2forge_renderer import AsyncRenderer, RenderError


def test_astrbot_application_is_shared_core_renderer_consumer(
    repository, provider, identity, clock, run_async
):
    async def check():
        service = Dota2Service(repository, provider, provider, clock)
        application = AstrApplication(
            service, MatchDetailService(provider), AsyncRenderer(), image_mode=True
        )
        menu = await application.handle(identity, "do菜单", "")
        assert isinstance(menu[0], AstrImageReply)
        await service.bind_account(identity, "123")
        player = await application.handle(identity, "do查询", "")
        assert isinstance(player[0], AstrImageReply)
        recent = await application.handle(identity, "do战绩", "2")
        assert len(recent) == 1 and isinstance(recent[0], AstrImageReply)
        detail = await application.handle(identity, "do比赛", "1")
        assert isinstance(detail[0], AstrTextReply) and "原因和隐私状态未知" in detail[0].text
        assert [kind for kind, *_ in provider.calls] == ["player", "recent", "detail"]
        await application.close()

    run_async(check())


def test_astrbot_text_mode_and_render_fallback_use_same_data(
    repository, provider, identity, clock, run_async
):
    async def check():
        service = Dota2Service(repository, provider, provider, clock)
        text_app = AstrApplication(service, MatchDetailService(provider), image_mode=False)
        assert isinstance((await text_app.handle(identity, "do查询", "123"))[0], AstrTextReply)
        await text_app.close()
        broken = AsyncRenderer()
        broken._engine.render = lambda _: (_ for _ in ()).throw(RenderError())
        fallback = AstrApplication(service, MatchDetailService(provider), broken, image_mode=True)
        assert isinstance((await fallback.handle(identity, "do菜单", ""))[0], AstrTextReply)
        await fallback.close()

    run_async(check())


@pytest.mark.parametrize("purchase_time", [-89, 0])
def test_astrbot_match_query_accepts_pregame_purchase_analysis(
    repository, identity, clock, run_async, purchase_time
):
    requests = []

    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert payload["variables"] == {"matchId": 1001}
        if payload["query"] == MATCH_DETAIL_QUERY:
            match = {
                "id": 1001,
                "startDateTime": None,
                "durationSeconds": 0,
                "didRadiantWin": False,
                "gameMode": None,
                "gameVersionId": None,
                "isStats": True,
                "parsedDateTime": None,
                "players": [],
            }
        else:
            assert payload["query"] == MATCH_ANALYSIS_QUERY
            match = {
                "id": 1001,
                "players": [
                    {
                        "playerSlot": 0,
                        "steamAccountId": None,
                        "stats": {
                            "networthPerMinute": [600],
                            "itemPurchases": [{"time": purchase_time, "itemId": 1}],
                        },
                    }
                ],
            }
        return httpx.Response(200, json={"data": {"match": match}})

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = StratzProvider(client, token="synthetic", clock=clock)
            application = AstrApplication(
                Dota2Service(repository, provider, provider, clock),
                MatchDetailService(provider),
                image_mode=False,
                analysis=MatchAnalysisService(provider),
            )
            replies = await application.handle(identity, "do比赛", "1001")
            text = "\n".join(reply.text for reply in replies)
            assert "比赛 1001" in text and "购买事件 1 条" in text
            assert len(requests) == 2
            await application.close()
        assert client.is_closed

    run_async(check())
