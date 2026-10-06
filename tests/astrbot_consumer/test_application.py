"""AstrBot-neutral consumer tests; no AstrBot SDK or network is required."""

from astrbot_plugin_dota2forge.application import AstrApplication, AstrImageReply, AstrTextReply
from dota2forge_core import Dota2Service, MatchDetailService
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
