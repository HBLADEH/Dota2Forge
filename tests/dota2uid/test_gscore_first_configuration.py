"""GsCore first startup waits for local credentials without creating business resources."""

import tomllib
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from Dota2UID.config import ConfigurationPending, ensure_config, load_config
from Dota2UID.runtime import AWAITING_CONFIG, UNAVAILABLE, Runtime, State


def test_initial_config_is_exclusive_and_matches_example(tmp_path):
    from pathlib import Path

    path = tmp_path / "data/config.toml"
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(lambda _: ensure_config(path), range(8)))
    expected = tomllib.loads(
        (Path(__file__).resolve().parents[2] / "adapters/Dota2UID/config.example.toml").read_text(
            "utf-8"
        )
    )
    assert tomllib.loads(path.read_text("utf-8")) == expected
    with pytest.raises(ConfigurationPending):
        load_config(path)
    path.write_text("local-custom-configuration", encoding="utf-8")
    ensure_config(path, token="synthetic-token")
    assert path.read_text("utf-8") == "local-custom-configuration"


def test_config_path_directory_is_failure(tmp_path):
    with pytest.raises(IsADirectoryError):
        ensure_config(tmp_path)
    assert not list(tmp_path.iterdir())


def test_first_command_waits_then_configured_reload_is_ready(tmp_path, caller, run_async, caplog):
    path = tmp_path / "data/Dota2UID/config.toml"
    clients = []

    def factory():
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("network")))
        clients.append(client)
        return client

    async def check():
        pending = Runtime(path, client_factory=factory)
        assert not path.exists()
        assert await pending.handle(caller, "do菜单", "") == [AWAITING_CONFIG]
        assert pending.state is State.AWAITING_CONFIG and pending.client_closed
        await pending.start()
        assert not clients and not path.with_name("bindings.sqlite3").exists()
        assert not path.with_name("subscriptions.sqlite3").exists()
        path.write_text(
            path.read_text("utf-8").replace(
                'stratz_token = ""', 'stratz_token = "synthetic-token"'
            ),
            encoding="utf-8",
        )
        await pending.close()
        restored = Runtime(path, client_factory=factory)
        await restored.start()
        assert restored.state is State.READY and len(clients) == 1
        assert "绑定已保存" in (await restored.handle(caller, "do绑定", "123"))[0]
        await restored.close()
        assert clients[0].is_closed

    run_async(check())
    assert "synthetic-token" not in caplog.text


def test_invalid_config_is_not_misreported_as_waiting(tmp_path, caller, run_async):
    path = tmp_path / "config.toml"
    ensure_config(path)
    path.write_text(
        path.read_text("utf-8").replace("timeout_seconds = 10", "timeout_seconds = 0"),
        encoding="utf-8",
    )
    contents = path.read_bytes()

    async def check():
        runtime = Runtime(path, client_factory=lambda: pytest.fail("no client for invalid config"))
        assert await runtime.handle(caller, "do菜单", "") == [UNAVAILABLE]
        assert runtime.state is State.FAILED and path.read_bytes() == contents
        await runtime.close()

    run_async(check())
