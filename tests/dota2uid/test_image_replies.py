"""Pillow replies use successful data once; only the bridge converts replies to host messages."""

import asyncio
import io
import json
import logging
import threading
from dataclasses import replace

import httpx
import pytest
from dota2forge_renderer import AsyncRenderer, ImageArtifact, MenuCard, PillowRenderer, RenderError
from Dota2UID.config import ConfigurationError, load_config
from Dota2UID.replies import ImageReply, TextReply
from Dota2UID.runtime import Runtime, State
from PIL import Image


@pytest.fixture
def image_config(config_path):
    config_path.write_text(
        config_path.read_text("utf-8").replace('reply_mode="text"', 'reply_mode="image"'), "utf-8"
    )
    return config_path


def response(request):
    query = json.loads(request.content)
    account = query["variables"].get("accountId", 123)
    if "Dota2ForgePlayer" in query["query"]:
        return httpx.Response(
            200,
            json={
                "data": {
                    "player": {
                        "steamAccountId": account,
                        "steamAccount": {"id": account, "name": "合成玩家", "seasonRank": 51},
                    }
                }
            },
        )
    if "Dota2ForgeMatchDetail" in query["query"]:
        return httpx.Response(200, json={"data": {"match": None}})
    rows = (
        [
            {
                "id": 7000000000 + index,
                "startDateTime": 1700000000 + index,
                "durationSeconds": 2105,
                "didRadiantWin": False,
                "players": [
                    {
                        "steamAccountId": account,
                        "heroId": 2,
                        "isRadiant": True,
                        "kills": 0,
                        "deaths": 0,
                        "assists": 8,
                        "goldPerMinute": 0,
                        "experiencePerMinute": None,
                    }
                ],
            }
            for index in range(10, 0, -1)
        ]
        if query["variables"]["skip"] == 0
        else []
    )
    return httpx.Response(
        200, json={"data": {"player": {"steamAccountId": account, "matches": rows}}}
    )


async def capture(runtime, caller, keyword, text):
    replies = []

    async def send(reply):
        replies.append(reply)

    await runtime.dispatch(caller, keyword, text, send)
    return replies


def test_images_menu_player_recent_status_and_saved_pages(image_config, caller, run_async):
    requests = []

    def handler(request):
        requests.append(request)
        return response(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    caller = replace(caller, conversation_kind="direct")

    async def check():
        runtime = Runtime(image_config, client_factory=lambda: client)
        for keyword, text in (
            ("dota菜单", ""),
            ("dota帮助", ""),
            ("dota绑定", "123"),
            ("dota账号", ""),
            ("dota玩家", ""),
            ("dota战绩", "10"),
        ):
            replies = await capture(runtime, caller, keyword, text)
            assert replies and all(isinstance(reply, ImageReply) for reply in replies)
            for reply in replies:
                with Image.open(io.BytesIO(reply.artifact.data)) as image:
                    image.load()
                    assert image.width == 780 and image.height <= 1600
        assert len(requests) == 2
        page = await capture(runtime, caller, "dota战绩", "第2页")
        assert isinstance(page[0], ImageReply) and len(requests) == 2
        selected = await capture(runtime, caller, "dota比赛", "第10场")
        assert isinstance(selected[0], TextReply) and "没有返回" in selected[0].text
        assert len(requests) == 3
        assert json.loads(requests[-1].content)["variables"] == {"matchId": 7000000001}
        await runtime.close()
        assert client.is_closed and runtime.state == State.STOPPED and runtime._renderer is None

    run_async(check())


def test_delivery_logs_are_actionable_without_identity_or_message(
    caplog, image_config, caller, run_async
):
    client = httpx.AsyncClient(transport=httpx.MockTransport(response))

    async def check():
        runtime = Runtime(image_config, client_factory=lambda: client)
        with caplog.at_level(logging.INFO, logger="Dota2UID"):
            replies = await capture(runtime, caller, "dota玩家", "123")
            await runtime.close()
        assert isinstance(replies[0], ImageReply)
        messages = "\n".join(record.getMessage() for record in caplog.records)
        assert "operation=dota玩家" in messages
        assert "delivery state=prepared" in messages and "images=1" in messages
        assert "image_sizes=780x850" in messages
        assert "delivery state=completed" in messages
        assert "synthetic-user" not in messages and "123" not in messages

    run_async(check())


class FailingEngine(PillowRenderer):
    def __init__(self, fail_at=1, failure=None):
        super().__init__()
        self.calls = []
        self.fail_at = fail_at
        self.failure = failure if failure is not None else RenderError()
        self.closed = False

    def render(self, card):
        self.calls.append(card)
        if len(self.calls) == self.fail_at:
            raise self.failure
        return ImageArtifact(b"\x89PNG\r\n\x1a\n", 780, 1)

    def close(self):
        self.closed = True
        super().close()


def test_second_card_failure_uses_all_same_data_text_without_refetch(
    image_config, caller, run_async
):
    requests = []

    def handler(request):
        requests.append(request)
        return response(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    engine = FailingEngine(2)
    caller = replace(caller, conversation_kind="direct")

    async def check():
        runtime = Runtime(
            image_config,
            client_factory=lambda: client,
            renderer_factory=lambda: AsyncRenderer(engine),
        )
        replies = await capture(runtime, caller, "dota战绩", "123 10")
        assert len(replies) == 2 and all(isinstance(reply, TextReply) for reply in replies)
        assert "第 1 场" in replies[0].text and "第 10 场" in replies[1].text
        assert len(requests) == 1 and len(engine.calls) == 2
        await capture(runtime, caller, "dota比赛", "第10场")
        assert len(requests) == 2
        assert json.loads(requests[-1].content)["variables"] == {"matchId": 7000000001}
        await runtime.close()
        assert engine.closed and client.is_closed

    run_async(check())


def test_source_error_never_renders_and_programming_bug_does_not_fallback(
    image_config, caller, run_async
):
    engine = FailingEngine(failure=RuntimeError("synthetic render bug"))
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(503)))

    async def check():
        runtime = Runtime(
            image_config,
            client_factory=lambda: client,
            renderer_factory=lambda: AsyncRenderer(engine),
        )
        replies = await capture(runtime, caller, "dota玩家", "123")
        assert isinstance(replies[0], TextReply) and "暂不可用" in replies[0].text
        assert not engine.calls
        with pytest.raises(RuntimeError, match="render bug"):
            await capture(runtime, caller, "dota菜单", "")
        await runtime.close()
        assert engine.closed and client.is_closed

    run_async(check())


def test_image_send_failure_does_not_repeat_or_commit_list(image_config, caller, run_async):
    requests = []

    def handler(request):
        requests.append(request)
        return response(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    caller = replace(caller, conversation_kind="direct")

    async def check():
        runtime = Runtime(image_config, client_factory=lambda: client)
        sends = []

        async def failed(reply):
            sends.append(reply)
            raise RuntimeError("synthetic send failure")

        with pytest.raises(RuntimeError, match="send failure"):
            await runtime.dispatch(caller, "dota战绩", "123 10", failed)
        assert len(requests) == 1 and len(sends) == 1 and isinstance(sends[0], ImageReply)
        assert not runtime._selections._results
        await runtime.close()

    run_async(check())


def test_admin_menu_requires_exact_trusted_boolean(image_config, caller, run_async):
    engine = FailingEngine(fail_at=99)
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: pytest.fail("Menu used HTTP"))
    )

    async def check():
        runtime = Runtime(
            image_config,
            client_factory=lambda: client,
            renderer_factory=lambda: AsyncRenderer(engine),
        )
        for is_admin, expected in ((False, False), (1, False), (True, True)):
            await capture(runtime, replace(caller, is_admin=is_admin), "dota菜单", "")
            assert (
                isinstance(engine.calls[-1], MenuCard)
                and engine.calls[-1].include_admin is expected
            )
        await runtime.close()

    run_async(check())


def test_text_mode_has_no_renderer_and_legacy_config_defaults_image(config_path, caller, run_async):
    assert load_config(config_path).reply_mode == "text"
    contents = config_path.read_text("utf-8")
    config_path.write_text(contents.replace('reply_mode="text"\n', ""), "utf-8")
    assert load_config(config_path).reply_mode == "image"
    config_path.write_text(contents, "utf-8")
    client = httpx.AsyncClient(transport=httpx.MockTransport(response))

    async def check():
        def forbidden():
            pytest.fail("Text mode allocated renderer")

        runtime = Runtime(config_path, client_factory=lambda: client, renderer_factory=forbidden)
        assert isinstance((await capture(runtime, caller, "dota菜单", ""))[0], TextReply)
        await runtime.close()

    run_async(check())


@pytest.mark.parametrize("mode", ['"other"', "true", "123"])
def test_invalid_reply_modes_fail_closed(config_path, mode):
    config_path.write_text(
        config_path.read_text("utf-8").replace('reply_mode="text"', f"reply_mode={mode}"), "utf-8"
    )
    with pytest.raises(ConfigurationError):
        load_config(config_path)


def test_stop_waits_for_cancelled_render_thread(image_config, caller, run_async):
    class SlowEngine(PillowRenderer):
        def __init__(self):
            super().__init__()
            self.entered = threading.Event()
            self.release = threading.Event()
            self.closed = False

        def render(self, card):
            self.entered.set()
            assert self.release.wait(5)
            return ImageArtifact(b"\x89PNG\r\n\x1a\n", 780, 1)

        def close(self):
            self.closed = True
            super().close()

    async def check():
        engine = SlowEngine()
        client = httpx.AsyncClient(transport=httpx.MockTransport(response))
        runtime = Runtime(
            image_config,
            client_factory=lambda: client,
            renderer_factory=lambda: AsyncRenderer(engine),
        )
        task = asyncio.create_task(capture(runtime, caller, "dota菜单", ""))
        try:
            for _ in range(500):
                if engine.entered.is_set():
                    break
                await asyncio.sleep(0.001)
            assert engine.entered.is_set()
            closing = asyncio.create_task(runtime.close())
            await asyncio.sleep(0)
            with pytest.raises(asyncio.CancelledError):
                await task
            assert not engine.closed
            engine.release.set()
            await closing
            assert engine.closed and runtime.state == State.STOPPED and client.is_closed
        finally:
            engine.release.set()
            await runtime.close()

    run_async(check())
