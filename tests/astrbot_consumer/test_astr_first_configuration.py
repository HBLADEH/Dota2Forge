"""AstrBot's empty-token configuration is distinct from invalid configuration."""

import httpx
import pytest
from astrbot_plugin_dota2forge.identity import Caller
from astrbot_plugin_dota2forge.runtime import AWAITING_CONFIG, Runtime, State


def test_empty_token_waits_and_new_configured_lifecycle_is_ready(tmp_path, run_async, caplog):
    clients = []
    replies = []

    def factory():
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("network")))
        clients.append(client)
        return client

    async def send(reply):
        replies.append(reply)

    async def check():
        pending = Runtime({}, tmp_path / "data", client_factory=factory)
        await pending.start()
        await pending.start()
        assert pending.state is State.AWAITING_CONFIG and pending.client_closed
        assert not clients
        assert not (tmp_path / "data/bindings.sqlite3").exists()
        assert not (tmp_path / "data/subscriptions.sqlite3").exists()
        assert pending.asset_status.state in {"checking", "downloading", "failed"}
        caller = Caller("qq", "connection", "bot", "user", conversation_kind="FriendMessage")
        await pending.dispatch(caller, "do菜单", "", send)
        assert replies[-1].text == AWAITING_CONFIG
        await pending.close()
        restored = Runtime(
            {"stratz_token": "synthetic-token", "reply_mode": "text"},
            tmp_path / "data",
            client_factory=factory,
        )
        await restored.start()
        assert restored.state is State.READY and len(clients) == 1
        await restored.dispatch(caller, "do绑定", "123", send)
        assert "绑定已保存" in replies[-1].text
        await restored.close()
        assert clients[0].is_closed

    run_async(check())
    assert "synthetic-token" not in caplog.text


def test_empty_token_does_not_mask_invalid_configuration(tmp_path, run_async):
    async def check():
        runtime = Runtime(
            {"stratz_token": "", "timeout_seconds": 0},
            tmp_path,
            client_factory=lambda: pytest.fail("no client"),
        )
        await runtime.start()
        assert runtime.state is State.FAILED
        await runtime.close()

    run_async(check())
