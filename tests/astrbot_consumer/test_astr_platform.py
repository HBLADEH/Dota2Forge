"""SDK-free tests for the AstrBot bridge contracts."""

from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from astrbot_plugin_dota2forge.config import ConfigurationError, load_config
from astrbot_plugin_dota2forge.identity import Caller
from astrbot_plugin_dota2forge.install import build_archive, install_bridge
from astrbot_plugin_dota2forge.runtime import Runtime, State
from astrbot_plugin_dota2forge.selection import SelectionError, SelectionStore
from dota2forge_core import InvalidIdentityError


def test_config_identity_and_selection_boundaries(tmp_path):
    config = load_config(
        {"namespace": "test", "stratz_token": "token", "timeout_seconds": 3}, tmp_path
    )
    assert config.database == tmp_path.resolve() / "bindings.sqlite3"
    assert config.illustration_path is None
    assert (
        load_config(
            {"stratz_token": "synthetic-token", "illustration_path": "art"}, tmp_path
        ).illustration_path
        == tmp_path / "art"
    )
    with pytest.raises(ConfigurationError):
        load_config({"namespace": "test", "stratz_token": ""}, tmp_path)

    caller = Caller("qq", "connection", "bot", "user", conversation_kind="FriendMessage")
    identity = caller.identity(config.namespace)
    assert identity.user_id == "user" and caller.session() == ("FriendMessage", "user")
    assert caller.identity(config.namespace) == identity
    with pytest.raises(InvalidIdentityError):
        Caller("qq", "connection", "bot", "user", True).identity(config.namespace)

    store = SelectionStore(clock=iter((0.0, 0.0, 601.0)).__next__)
    recent = object()
    key = (identity, caller.session())
    store.remember(key, recent, None)  # type: ignore[arg-type]
    with pytest.raises(SelectionError):
        store.get(key, None)


def test_local_art_directory_reaches_shared_renderer_without_eager_io(tmp_path, run_async):
    async def check():
        raw = {"stratz_token": "synthetic-token", "illustration_path": "art"}
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("network")))
        runtime = Runtime(raw, tmp_path, client_factory=lambda: client)
        try:
            await runtime.start()
            renderer = runtime._application._renderer
            assert renderer._engine._illustrations.path == tmp_path / "art"
            assert not renderer._engine._illustrations._loaded
        finally:
            await runtime.close()

    run_async(check())


@pytest.mark.parametrize(
    "override",
    [
        {"namespace": "bad namespace"},
        {"stratz_token": "bad token"},
        {"timeout_seconds": True},
        {"timeout_seconds": 0},
        {"timeout_seconds": 61},
        {"timeout_seconds": float("nan")},
        {"reply_mode": "other"},
        {"unknown": 1},
        {"illustration_path": 1},
        {"illustration_path": "bad\0path"},
    ],
)
def test_invalid_config_has_safe_errors(tmp_path, override):
    raw = {"namespace": "test", "stratz_token": "synthetic-token"} | override
    with pytest.raises(ConfigurationError) as error:
        load_config(raw, tmp_path)
    assert "synthetic-token" not in str(error.value)


def test_identity_separates_deployments_connections_bots_and_users():
    caller = Caller(
        "qq", "connection", "bot", "user", conversation_kind="GroupMessage", conversation_id="group"
    )
    identity = caller.identity("test")
    alternatives = [
        caller.identity("other"),
        replace(caller, connection_id="other").identity("test"),
        replace(caller, bot_id="other").identity("test"),
        replace(caller, user_id="other").identity("test"),
        replace(caller, platform="other").identity("test"),
    ]
    assert len({identity, *alternatives}) == 6
    assert caller.session() == ("GroupMessage", "group")
    assert replace(caller, conversation_id="").session() is None
    assert replace(caller, conversation_id="bad group").session() is None
    assert replace(caller, conversation_kind="OtherMessage").session() is None


def test_installer_is_idempotent_and_keeps_conflicting_files(tmp_path):
    root = tmp_path / "astrbot"
    (root / "astrbot" / "core" / "star").mkdir(parents=True)
    (root / "astrbot" / "core" / "star" / "star_manager.py").write_text("", encoding="utf-8")
    destination = install_bridge(root)
    assert {"main.py", "metadata.yaml", "_conf_schema.json", "requirements.txt"} == {
        path.name for path in destination.iterdir()
    }
    assert install_bridge(root) == destination
    (destination / "main.py").write_text("user", encoding="utf-8")
    with pytest.raises(ValueError, match="bridge differs"):
        install_bridge(root)
    archive = build_archive(tmp_path / "plugin.zip")
    import zipfile

    with zipfile.ZipFile(archive) as value:
        assert "main.py" in value.namelist()
        assert set(value.namelist()) == {
            "main.py",
            "metadata.yaml",
            "_conf_schema.json",
            "requirements.txt",
        }


def test_runtime_lifecycle_and_image_dispatch(tmp_path, run_async):
    clients: list[httpx.AsyncClient] = []

    def client_factory():
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("network")))
        clients.append(client)
        return client

    runtime = Runtime(
        {"namespace": "test", "stratz_token": "token", "reply_mode": "image"},
        Path(tmp_path),
        client_factory=client_factory,
    )
    caller = Caller("qq", "connection", "bot", "user", conversation_kind="FriendMessage")
    replies = []

    async def check():
        await runtime.start()
        await runtime.start()
        assert runtime.state is State.READY and len(clients) == 1

        async def send(reply):
            replies.append(reply)

        await runtime.dispatch(caller, "do菜单", "", send)
        assert replies and getattr(replies[0], "artifact", None) is not None
        await runtime.close()
        await runtime.close()
        assert runtime.state is State.STOPPED and clients[0].is_closed

    run_async(check())
