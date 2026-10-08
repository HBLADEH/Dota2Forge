import asyncio
import json

import pytest
from astrbot_plugin_dota2forge.config import load_config as astr_config
from astrbot_plugin_dota2forge.identity import Caller as AstrCaller
from astrbot_plugin_dota2forge.runtime import Runtime as AstrRuntime
from dota2forge_assets import AssetError, AssetSession, load_asset_options
from Dota2UID.commands import Caller as GsCaller
from Dota2UID.config import ensure_config
from Dota2UID.runtime import Runtime as GsRuntime


def runtime(host, tmp_path, backend, *, token="", **options):
    factory = backend.manager

    def client():
        pytest.fail("No provider client without a token")

    if host == "astr":
        return AstrRuntime(
            {"stratz_token": token, **options},
            tmp_path,
            asset_manager_factory=factory,
            client_factory=client if not token else backend.client,
        )
    path = tmp_path / "config.toml"
    ensure_config(path, token=token)
    text = path.read_text("utf-8")
    for key, value in options.items():
        default = {"asset_download_mode": "auto", "reply_mode": "image"}.get(key, "")
        text = text.replace(f"{key} = {json.dumps(default)}", f"{key} = {json.dumps(value)}")
    path.write_text(text, encoding="utf-8")
    return GsRuntime(
        path, asset_manager_factory=factory, client_factory=client if not token else backend.client
    )


def caller(host, admin=False):
    if host == "astr":
        return AstrCaller("qq", "connection", "bot", "user", is_admin=admin)
    return GsCaller("onebot", "bot", "user", "connection", is_admin=admin)


async def command(instance, host, keyword, *, admin=False):
    replies = []

    async def send(reply):
        replies.append(reply)

    await instance.dispatch(caller(host, admin), keyword, "", send)
    assert len(replies) == 1
    return replies[0].text


@pytest.mark.parametrize("host", ["astr", "gs"])
def test_empty_token_prepares_artwork_independently_and_admin_can_repair(
    host,
    tmp_path,
    backend,
    run_async,
):
    async def run():
        instance = runtime(host, tmp_path, backend)
        await instance.start()
        await instance.start()
        assert instance.state.value == "awaiting_config" and instance.client_closed
        assert instance.asset_status.state == "downloading"
        assert instance._assets is not None
        await instance._assets.manager.wait()
        assert instance.asset_status.state == "ready"
        count = len(backend.calls)
        assert "就绪" in await command(instance, host, "do素材状态")
        assert "管理员" in await command(instance, host, "do更新素材")
        assert len(backend.calls) == count
        assert "冷却" in await command(instance, host, "do更新素材", admin=True)
        backend.advance()
        assert "后台下载" in await command(instance, host, "do更新素材", admin=True)
        await instance._assets.manager.wait()
        assert len(backend.calls) > count
        assert not tmp_path.joinpath("bindings.sqlite3").exists()
        await instance.close()
        assert all(c.is_closed for c in backend.clients)
        restored = runtime(host, tmp_path, backend)
        backend.calls.clear()
        await restored.start()
        assert restored.asset_status.state == "ready" and backend.calls == []
        await restored.close()

    run_async(run())


@pytest.mark.parametrize("host", ["astr", "gs"])
@pytest.mark.parametrize(
    "mode,reply,expected",
    [
        ("manual", "image", "checking"),
        ("off", "image", "disabled"),
        ("auto", "text", "checking"),
    ],
)
def test_modes_do_not_start_implicit_network(
    host, mode, reply, expected, tmp_path, backend, run_async
):
    async def run():
        instance = runtime(host, tmp_path, backend, asset_download_mode=mode, reply_mode=reply)
        await instance.start()
        assert instance.asset_status.state == expected and backend.calls == []
        await command(instance, host, "do下载素材", admin=True)
        if mode == "off":
            assert instance.asset_status.state == "disabled" and backend.calls == []
        else:
            await instance._assets.manager.wait()
            assert instance.asset_status.state == "ready"
        await instance.close()

    run_async(run())


@pytest.mark.parametrize("host", ["astr", "gs"])
def test_external_directory_wins_and_invalid_configuration_starts_no_download(
    host,
    tmp_path,
    backend,
    run_async,
):
    async def run():
        pack = backend.manager(tmp_path / "source")
        await pack.ensure()
        await pack.wait()
        path = pack.path
        await pack.close()
        backend.calls.clear()
        instance = runtime(host, tmp_path / "host", backend, illustration_path=str(path))
        await instance.start()
        assert instance.asset_status.state == "external" and backend.calls == []
        assert "自定义" in await command(instance, host, "do更新素材", admin=True)
        assert backend.calls == [] and not tmp_path.joinpath("host/illustrations").exists()
        await instance.close()
        invalid = runtime(host, tmp_path / "invalid", backend, asset_download_mode="anything")
        await invalid.start()
        assert invalid.state.value == "failed" and backend.calls == []
        await invalid.close()

    run_async(run())


@pytest.mark.parametrize("host", ["astr", "gs"])
def test_ready_image_runtime_uses_new_generation_and_waits_for_whole_send_batch(
    host,
    tmp_path,
    backend,
    run_async,
):
    async def run():
        instance = runtime(host, tmp_path, backend, token="synthetic-token")
        await instance.start()
        await instance._assets.manager.wait()
        assert instance.state.value == "ready" and instance.asset_status.state == "ready"
        owner = instance._application if host == "astr" else instance
        old_renderer = owner._renderer
        old_generation = instance.asset_status.generation
        entered, release = asyncio.Event(), asyncio.Event()
        images = []

        async def send(reply):
            images.append(reply.artifact.data)
            entered.set()
            await release.wait()

        dispatch = asyncio.create_task(instance.dispatch(caller(host), "do菜单", "", send))
        await entered.wait()
        backend.advance()
        backend.color = "blue"
        # Start directly while a reply holds the send lock; permissions are covered above.
        await instance._assets.manager.update()
        await asyncio.sleep(0.05)
        assert (
            owner._renderer is old_renderer and instance.asset_status.generation == old_generation
        )
        release.set()
        await dispatch
        await instance._assets.manager.wait()
        assert owner._renderer is not old_renderer
        assert instance.asset_status.generation != old_generation
        assert len(images) == 1 and images[0].startswith(b"\x89PNG")
        assert all("stratz" not in str(r.url) for r in backend.calls)
        await instance.close()

    run_async(run())


@pytest.mark.parametrize(
    "options",
    [
        {"asset_download_mode": False},
        {"asset_proxy": "http://proxy.invalid"},
        {"asset_proxy": "http://host:1/path"},
        {"asset_proxy": "file:///tmp"},
        {"illustration_path": "bad\npath"},
        {"reply_mode": "html"},
    ],
)
def test_strict_shared_options_and_both_config_consumers(options, tmp_path):
    with pytest.raises(AssetError, match="configuration"):
        load_asset_options(options, tmp_path)
    from astrbot_plugin_dota2forge.config import ConfigurationError as AstrError

    with pytest.raises(AstrError):
        astr_config({"stratz_token": "synthetic", **options}, tmp_path)


def test_session_arguments_external_invalid_and_closed_commands(tmp_path, backend, run_async):
    async def run():
        session = AssetSession(
            load_asset_options({"illustration_path": "absent"}, tmp_path),
            tmp_path / "managed",
            manager_factory=backend.manager,
        )
        await session.start()
        assert session.status().state == "external_invalid"
        assert "不接受参数" in await session.handle("do下载素材", "URL", is_admin=True)
        assert "管理员" in await session.handle("do下载素材", "", is_admin=False)
        await session.close()
        assert "已关闭" in await session.handle("do下载素材", "", is_admin=True)
        assert backend.calls == []

    run_async(run())


@pytest.mark.parametrize("host", ["astr", "gs"])
def test_stop_during_replacement_waits_for_retired_renderer(
    host,
    tmp_path,
    backend,
    run_async,
):
    async def run():
        entered, finish = asyncio.Event(), asyncio.Event()

        class RetiredRenderer:
            async def close(self):
                entered.set()
                await finish.wait()

        instance = runtime(
            host, tmp_path, backend, token="synthetic-token", asset_download_mode="manual"
        )
        await instance.start()
        owner = instance._application if host == "astr" else instance
        await owner._renderer.close()
        owner._renderer = RetiredRenderer()
        await instance._assets.manager.ensure()
        await entered.wait()
        closing = asyncio.create_task(instance.close())
        await asyncio.sleep(0.02)
        assert not closing.done()
        assert instance._assets.manager.store.lease.stream is not None
        finish.set()
        await closing
        assert instance.state.value == "stopped"
        assert instance._assets.manager.store.lease.stream is None

    run_async(run())
