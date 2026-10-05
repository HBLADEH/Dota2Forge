import asyncio
import json
from dataclasses import replace

import httpx
import pytest
from Dota2UID.runtime import UNAVAILABLE, Runtime, State


def profile_reply(request):
    account = json.loads(request.content)["variables"]["accountId"]
    return httpx.Response(
        200,
        json={
            "data": {
                "player": {
                    "steamAccountId": account,
                    "steamAccount": {"id": account, "name": "Synthetic Player", "seasonRank": 51},
                    "matches": [],
                }
            }
        },
    )


def factory_with(handler):
    clients, requests = [], []

    async def transport(request):
        requests.append(request)
        return handler(request)

    def make():
        client = httpx.AsyncClient(transport=httpx.MockTransport(transport))
        clients.append(client)
        return client

    return make, clients, requests


def test_complete_binding_query_journey_and_persistence(config_path, caller, run_async):
    factory, clients, requests = factory_with(profile_reply)

    async def check():
        runtime = Runtime(config_path, client_factory=factory)
        assert runtime.state == State.NEW and not clients
        assert "尚未绑定" in (await runtime.handle(caller, "do查询", ""))[0]
        assert not requests
        assert "绑定已保存" in (await runtime.handle(caller, "do绑定", "123"))[0]
        await runtime.handle(caller, "do绑定", "123")
        assert "其他账号" in (await runtime.handle(caller, "do绑定", "456"))[0]
        assert "已绑定" in (await runtime.handle(caller, "do账号", ""))[0]
        player = (await runtime.handle(caller, "do查询", ""))[0]
        assert "传奇 1 星" in player and "https://stratz.com/players/123" in player
        assert "数据观测时间：未知" in player and "抓取时间：" in player
        assert "0 场" in (await runtime.handle(caller, "do战绩", ""))[0]
        assert "绑定已保存" in (await runtime.handle(caller, "do改绑", "456"))[0]
        await runtime.close()
        assert runtime.client_closed and runtime.state == State.STOPPED
        assert await runtime.handle(caller, "do查询", "") == [UNAVAILABLE]
        restored = Runtime(config_path, client_factory=factory)
        assert "players/456" in (await restored.handle(caller, "do查询", ""))[0]
        assert "已解除" in (await restored.handle(caller, "do解绑", ""))[0]
        assert "没有绑定" in (await restored.handle(caller, "do解绑", ""))[0]
        assert "尚未绑定" in (await restored.handle(caller, "do账号", ""))[0]
        await restored.close()
        assert len(clients) == 2 and all(c.is_closed for c in clients)

    run_async(check())


def test_explicit_queries_do_not_bind_and_identity_failures_do_not_send(
    config_path, caller, run_async
):
    factory, clients, requests = factory_with(profile_reply)

    async def check():
        runtime = Runtime(config_path, client_factory=factory)
        assert "players/123" in (await runtime.handle(caller, "do查询", "123"))[0]
        assert "尚未绑定" in (await runtime.handle(caller, "do账号", ""))[0]
        assert (
            "无法确认"
            in (await runtime.handle(replace(caller, mentioned=True), "do绑定", "123"))[0]
        )
        assert "格式不正确" in (await runtime.handle(caller, "do绑定", "0123"))[0]
        assert "参数不正确" in (await runtime.handle(caller, "do战绩", "101"))[0]
        assert len(requests) == 1
        await runtime.close()
        assert clients[0].is_closed

    run_async(check())


def test_concurrent_start_and_hot_first_command_create_one_client(config_path, caller, run_async):
    factory, clients, requests = factory_with(profile_reply)

    async def check():
        runtime = Runtime(config_path, client_factory=factory)
        await asyncio.gather(
            runtime.start(),
            runtime.start(),
            runtime.handle(caller, "do查询", "123"),
            runtime.handle(caller, "do战绩", "123 1"),
        )
        assert len(clients) == 1 and len(requests) == 2
        await asyncio.gather(runtime.close(), runtime.close())
        assert clients[0].is_closed

    run_async(check())


def test_failed_initialization_stays_unavailable_without_client(config_path, caller, run_async):
    config_path.write_text("malformed", encoding="utf-8")
    factory, clients, _ = factory_with(profile_reply)

    async def check():
        runtime = Runtime(config_path, client_factory=factory)
        assert await runtime.handle(caller, "do绑定", "123") == [UNAVAILABLE]
        assert runtime.state == State.FAILED
        await runtime.start()
        assert not clients and not (config_path.parent / "bindings.sqlite3").exists()
        await runtime.close()

    run_async(check())


def test_bad_storage_fails_before_http_allocation(config_path, caller, run_async):
    (config_path.parent / "bindings.sqlite3").write_bytes(b"not a database")
    factory, clients, _ = factory_with(profile_reply)

    async def check():
        runtime = Runtime(config_path, client_factory=factory)
        assert await runtime.handle(caller, "do绑定", "123") == [UNAVAILABLE]
        assert runtime.state == State.FAILED and not clients
        await runtime.close()

    run_async(check())


def test_shutdown_cancels_inflight_query_and_closes_client(config_path, caller, run_async):
    async def check():
        started = asyncio.Event()

        async def stalled(_):
            started.set()
            await asyncio.Event().wait()

        client = httpx.AsyncClient(transport=httpx.MockTransport(stalled))
        runtime = Runtime(config_path, client_factory=lambda: client)
        query = asyncio.create_task(runtime.handle(caller, "do查询", "123"))
        await started.wait()
        queued = asyncio.create_task(runtime.handle(caller, "do查询", "123"))
        await runtime.close()
        with pytest.raises(asyncio.CancelledError):
            await query
        assert await queued == [UNAVAILABLE]
        assert client.is_closed and runtime.state == State.STOPPED

    run_async(check())


def test_cancelled_close_waiter_does_not_abandon_client(config_path, run_async):
    async def check():
        started, release = asyncio.Event(), asyncio.Event()

        class SlowClose(httpx.AsyncClient):
            async def aclose(self):
                started.set()
                await release.wait()
                await super().aclose()

        client = SlowClose(transport=httpx.MockTransport(profile_reply))
        runtime = Runtime(config_path, client_factory=lambda: client)
        await runtime.start()
        task = asyncio.create_task(runtime.close())
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        release.set()
        await runtime.close()
        assert client.is_closed and runtime.state == State.STOPPED

    run_async(check())


def test_provider_failure_preserves_binding_and_quota_state(config_path, caller, run_async):
    factory, clients, requests = factory_with(
        lambda _: httpx.Response(429, headers={"Retry-After": "600"})
    )

    async def check():
        runtime = Runtime(config_path, client_factory=factory)
        await runtime.handle(caller, "do绑定", "123")
        for _ in range(2):
            assert "额度已用尽" in (await runtime.handle(caller, "do查询", ""))[0]
        assert len(requests) == 1 and len(clients) == 1
        assert "已绑定" in (await runtime.handle(caller, "do账号", ""))[0]
        await runtime.close()

    run_async(check())


def test_start_cancel_and_stop_during_start_do_not_leak(config_path, run_async, monkeypatch):
    from Dota2UID import runtime as module

    async def check(cancel):
        entered, release = asyncio.Event(), asyncio.Event()

        async def initialize(self):
            entered.set()
            await release.wait()

        monkeypatch.setattr(module.SQLiteBindingRepository, "initialize", initialize)
        factory, clients, _ = factory_with(profile_reply)
        runtime = Runtime(config_path, client_factory=factory)
        task = asyncio.create_task(runtime.start())
        await entered.wait()
        if cancel:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert runtime.state == State.FAILED
            await runtime.close()
        else:
            closing = asyncio.create_task(runtime.close())
            await asyncio.sleep(0)
            release.set()
            await task
            await closing
        assert not clients and runtime.state == State.STOPPED

    run_async(check(True))
    run_async(check(False))


def test_unexpected_errors_propagate_and_close_still_works(config_path, caller, run_async):
    def bug(_):
        raise RuntimeError("synthetic bug")

    factory, clients, _ = factory_with(bug)

    async def check():
        runtime = Runtime(config_path, client_factory=factory)
        with pytest.raises(RuntimeError, match="synthetic bug"):
            await runtime.handle(caller, "do查询", "123")
        await runtime.close()
        assert clients[0].is_closed

    run_async(check())


def test_provider_construction_failure_closes_candidate(config_path, run_async, monkeypatch):
    from dota2forge_core import ValidationError
    from Dota2UID import runtime as module

    factory, clients, _ = factory_with(profile_reply)

    def rejected(*args, **kwargs):
        raise ValidationError("synthetic construction")

    monkeypatch.setattr(module, "StratzProvider", rejected)

    async def check():
        runtime = Runtime(config_path, client_factory=factory)
        await runtime.start()
        assert runtime.state == State.FAILED and clients[0].is_closed
        await runtime.close()

    run_async(check())
