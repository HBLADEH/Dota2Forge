"""Bounded delivered-list state with synthetic sessions and a monotonic clock."""

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from dota2forge_core import (
    AccountId,
    DataMetadata,
    DataSource,
    MatchSummary,
    PlatformIdentity,
    PlayerBinding,
    RecentMatches,
)
from Dota2UID.commands import CommandError, parse_command
from Dota2UID.config import load_config
from Dota2UID.replies import TextReply
from Dota2UID.runtime import Runtime, State
from Dota2UID.selection import RecentSelectionStore, ResultKey, SelectionError, result_key

META = DataMetadata(DataSource.FIXTURE, datetime(2026, 10, 1, tzinfo=UTC))


def normalized(match_id=1):
    return RecentMatches(
        AccountId(123), (MatchSummary(match_id, AccountId(123), META.fetched_at, META),), META
    )


def key(index=1):
    return ResultKey(
        PlatformIdentity("test", "qq", "bot", f"user-{index}"), "connection", "group", "group"
    )


def raw_matches(count=12, base=1000):
    return [
        {
            "id": base + count - index,
            "startDateTime": 1700000000 - index,
            "durationSeconds": 1800,
            "didRadiantWin": True,
            "players": [
                {
                    "steamAccountId": 123,
                    "heroId": 2,
                    "isRadiant": True,
                    "kills": 0,
                    "deaths": 0,
                    "assists": 1,
                    "goldPerMinute": 0,
                    "experiencePerMinute": None,
                }
            ],
        }
        for index in range(count)
    ]


def transport_for(rows, requests, *, recent_failure=None):
    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        if "Dota2ForgeRecentMatches" in payload["query"]:
            if recent_failure is not None:
                return httpx.Response(recent_failure)
            variables = payload["variables"]
            page = rows[variables["skip"] : variables["skip"] + variables["take"]]
            return httpx.Response(
                200, json={"data": {"player": {"steamAccountId": 123, "matches": page}}}
            )
        assert "Dota2ForgeMatchDetail" in payload["query"]
        return httpx.Response(200, json={"data": {"match": None}})

    return httpx.MockTransport(handler)


async def capture(runtime, caller, keyword, text):
    messages = []

    async def send(message):
        assert isinstance(message, TextReply)
        messages.append(message.text)

    await runtime.dispatch(caller, keyword, text, send)
    return messages


@pytest.mark.parametrize(
    ("keyword", "text", "field", "value"),
    [
        ("dota比赛", "第1场", "match_index", 1),
        ("dota比赛", "第100场", "match_index", 100),
        ("dota战绩", "第1页", "page", 1),
        ("dota战绩", "第20页", "page", 20),
    ],
)
def test_selection_and_page_grammar(keyword, text, field, value):
    command = parse_command(keyword, text)
    assert getattr(command, field) == value and command.match_id is None


@pytest.mark.parametrize(
    ("keyword", "text"),
    [
        ("dota比赛", "第0场"),
        ("dota比赛", "第01场"),
        ("dota比赛", "第101场"),
        ("dota比赛", "第１场"),
        ("dota比赛", "第1场 2"),
        ("dota比赛", "第1页"),
        ("dota战绩", "第0页"),
        ("dota战绩", "第01页"),
        ("dota战绩", "第21页"),
        ("dota战绩", "第1场"),
        ("dota战绩", "123 第1页"),
    ],
)
def test_invalid_selection_grammar_never_guesses(keyword, text):
    with pytest.raises(CommandError):
        parse_command(keyword, text)


@pytest.mark.parametrize(
    "changes",
    [
        {"conversation_kind": None},
        {"conversation_kind": "channel"},
        {"conversation_kind": "group", "conversation_id": None},
        {"conversation_kind": "group", "conversation_id": " "},
        {"conversation_kind": "group", "conversation_id": "x" * 129},
        {"connection_id": "connection space"},
    ],
)
def test_session_mapping_fails_closed(config_path, caller, changes):
    with pytest.raises(SelectionError):
        result_key(replace(caller, **changes), load_config(config_path))


def test_result_keys_isolate_every_host_dimension(config_path, caller):
    config = load_config(config_path)
    caller = replace(caller, conversation_kind="group", conversation_id="group")
    keys = {
        result_key(caller, config),
        result_key(replace(caller, user_id="other"), config),
        result_key(replace(caller, bot_self_id="other"), config),
        result_key(replace(caller, platform_key="telegram"), config),
        result_key(replace(caller, connection_id="other"), config),
        result_key(replace(caller, conversation_id="other"), config),
        result_key(replace(caller, conversation_kind="direct"), config),
        result_key(caller, replace(config, namespace="other")),
    }
    assert len(keys) == 8 and all("synthetic-user" not in repr(item) for item in keys)


def test_capacity_expiry_replacement_and_binding_record_checks():
    now = [0.0]
    store = RecentSelectionStore(clock=lambda: now[0], capacity=2)
    first = normalized(1)
    store.remember(key(1), first, None)
    now[0] = 599
    assert store.get(key(1), None) is first
    now[0] = 600
    with pytest.raises(SelectionError):
        store.get(key(1), None)
    store.remember(key(1), first, None)
    store.remember(key(2), first, None)
    store.remember(key(3), first, None)
    assert len(store._results) == 2
    with pytest.raises(SelectionError):
        store.get(key(1), None)
    second = normalized(2)
    store.remember(key(2), second, None)
    assert store.get(key(2), None) is second
    binding = PlayerBinding(key(2).identity, AccountId(123), META.fetched_at)
    with pytest.raises(SelectionError):
        store.get(key(2), binding)
    store.remember(key(2), second, binding)
    changed = replace(binding, bound_at=binding.bound_at + timedelta(seconds=1))
    with pytest.raises(SelectionError):
        store.get(key(2), changed)
    store.clear()
    assert not store._results


def test_invalidation_clears_all_sessions_of_identity_only():
    store = RecentSelectionStore()
    store.remember(key(1), normalized(), None)
    store.remember(replace(key(1), conversation_id="other"), normalized(), None)
    store.remember(key(2), normalized(), None)
    store.invalidate(key(1).identity)
    assert len(store._results) == 1 and store.get(key(2), None)


@pytest.mark.parametrize(
    "changes",
    [
        {"capacity": 0},
        {"capacity": True},
        {"capacity": 129},
        {"ttl_seconds": 0},
        {"ttl_seconds": 601},
        {"ttl_seconds": True},
        {"ttl_seconds": float("inf")},
        {"ttl_seconds": float("nan")},
    ],
)
def test_selection_configuration_is_bounded(changes):
    with pytest.raises(ValueError):
        RecentSelectionStore(**changes)


def test_last_delivered_list_pages_and_selection_use_saved_ids_without_refetch(
    config_path, caller, run_async
):
    requests = []
    client = httpx.AsyncClient(transport=transport_for(raw_matches(), requests))
    caller = replace(caller, conversation_kind="group", conversation_id="group")

    async def check():
        runtime = Runtime(config_path, client_factory=lambda: client)
        messages = await capture(runtime, caller, "dota战绩", "123 12")
        assert len(messages) == 3 and "第N页" in messages[-1]
        assert sum("Dota2ForgeRecentMatches" in req["query"] for req in requests) == 1
        before = len(requests)
        page = await capture(runtime, caller, "dota战绩", "第3页")
        assert len(page) == 1 and "第 11 场" in page[0] and "第 12 场" in page[0]
        assert len(requests) == before
        selected = await capture(runtime, caller, "dota比赛", "第12场")
        assert "没有返回" in selected[0]
        assert requests[-1]["variables"] == {"matchId": 1001}
        assert len(requests) == before + 1
        assert "只有 12 场" in (await capture(runtime, caller, "dota比赛", "第13场"))[0]
        assert "只有 3 页" in (await capture(runtime, caller, "dota战绩", "第4页"))[0]
        assert len(requests) == before + 1
        await runtime.close()
        assert not runtime._selections._results and client.is_closed

    run_async(check())


def test_no_send_no_selection_and_cross_session_expiry_rebind_unbind_reload(
    config_path, caller, run_async
):
    requests = []
    now = [0.0]
    client = httpx.AsyncClient(transport=transport_for(raw_matches(1), requests))
    caller = replace(caller, conversation_kind="direct")

    async def check():
        runtime = Runtime(
            config_path, client_factory=lambda: client, selection_clock=lambda: now[0]
        )
        await runtime.handle(caller, "dota战绩", "123 1")
        assert "不存在" in (await capture(runtime, caller, "dota比赛", "第1场"))[0]
        await capture(runtime, caller, "dota战绩", "123 1")
        for other in (
            replace(caller, user_id="other"),
            replace(caller, bot_self_id="other"),
            replace(caller, conversation_kind="group", conversation_id="group"),
            replace(caller, connection_id="other"),
        ):
            assert "不存在" in (await capture(runtime, other, "dota比赛", "第1场"))[0]
        now[0] = 600
        assert "过期" in (await capture(runtime, caller, "dota比赛", "第1场"))[0]
        await capture(runtime, caller, "dota战绩", "123 1")
        await runtime.handle(caller, "dota改绑", "123")
        assert "绑定已变化" in (await capture(runtime, caller, "dota比赛", "第1场"))[0]
        await capture(runtime, caller, "dota战绩", "1")
        await runtime.handle(caller, "dota解绑", "")
        assert "绑定已变化" in (await capture(runtime, caller, "dota比赛", "第1场"))[0]
        await runtime.close()
        restored_client = httpx.AsyncClient(transport=transport_for(raw_matches(1), requests))
        restored = Runtime(config_path, client_factory=lambda: restored_client)
        assert "不存在" in (await capture(restored, caller, "dota比赛", "第1场"))[0]
        await restored.close()

    run_async(check())


def test_partial_send_failure_preserves_previous_list_and_empty_success_replaces_it(
    config_path, caller, run_async
):
    requests = []
    rows = raw_matches(12)
    client = httpx.AsyncClient(transport=transport_for(rows, requests))
    caller = replace(caller, conversation_kind="direct")

    async def check():
        runtime = Runtime(config_path, client_factory=lambda: client)
        await capture(runtime, caller, "dota战绩", "123 12")
        previous = runtime._selections.get(result_key(caller, runtime._config), None)
        rows[:] = raw_matches(12, base=2000)
        sends = []

        async def broken(message):
            sends.append(message)
            if len(sends) == 2:
                raise RuntimeError("synthetic send failure")

        with pytest.raises(RuntimeError, match="send failure"):
            await runtime.dispatch(caller, "dota战绩", "123 12", broken)
        assert len(sends) == 2
        assert runtime._selections.get(result_key(caller, runtime._config), None) is previous
        rows.clear()
        await capture(runtime, caller, "dota战绩", "123 12")
        assert "只有 0 场" in (await capture(runtime, caller, "dota比赛", "第1场"))[0]
        await runtime.close()

    run_async(check())


def test_failed_provider_query_preserves_last_delivered_list(
    config_path, caller, run_async, monkeypatch
):
    from dota2forge_core import ProviderError, ProviderErrorCode

    requests = []
    client = httpx.AsyncClient(transport=transport_for(raw_matches(1), requests))
    caller = replace(caller, conversation_kind="direct")

    async def check():
        runtime = Runtime(config_path, client_factory=lambda: client)
        await capture(runtime, caller, "dota战绩", "123 1")
        previous = runtime._selections.get(result_key(caller, runtime._config), None)

        async def failed(*args):
            raise ProviderError(ProviderErrorCode.UNAVAILABLE, DataSource.STRATZ)

        monkeypatch.setattr(runtime._service._matches, "get_recent_matches", failed)
        assert "暂不可用" in (await capture(runtime, caller, "dota战绩", "123 1"))[0]
        assert runtime._selections.get(result_key(caller, runtime._config), None) is previous
        await capture(runtime, caller, "dota比赛", "第1场")
        assert requests[-1]["variables"] == {"matchId": 1001}
        await runtime.close()

    run_async(check())


def test_hundred_matches_are_bounded_and_last_page_and_absolute_index_are_correct(
    config_path, caller, run_async
):
    requests = []
    client = httpx.AsyncClient(transport=transport_for(raw_matches(100), requests))
    caller = replace(caller, conversation_kind="direct")

    async def check():
        runtime = Runtime(config_path, client_factory=lambda: client)
        messages = await capture(runtime, caller, "dota战绩", "123 100")
        assert len(messages) == 3 and "共 20 页" in messages[-1]
        assert len(requests) == 5
        page = await capture(runtime, caller, "dota战绩", "第20页")
        assert "第 96 场" in page[0] and "第 100 场" in page[0]
        assert len(requests) == 5
        await capture(runtime, caller, "dota比赛", "第100场")
        assert len(requests) == 6 and requests[-1]["variables"] == {"matchId": 1001}
        await runtime.close()

    run_async(check())


def test_dispatch_queue_admission_is_bounded(config_path, caller, run_async):
    requests = []
    client = httpx.AsyncClient(transport=transport_for(raw_matches(1), requests))
    caller = replace(caller, conversation_kind="direct")

    async def check():
        runtime = Runtime(config_path, client_factory=lambda: client)
        entered = asyncio.Event()

        async def stalled(_):
            entered.set()
            await asyncio.Event().wait()

        active = asyncio.create_task(runtime.dispatch(caller, "dota战绩", "123 1", stalled))
        await entered.wait()
        queued = [asyncio.create_task(capture(runtime, caller, "dota帮助", "")) for _ in range(15)]
        await asyncio.sleep(0)
        assert runtime._dispatch_count == 16
        assert "排队请求较多" in (await capture(runtime, caller, "dota帮助", ""))[0]
        assert len(requests) == 1 and runtime._dispatch_count == 16
        await runtime.close()
        with pytest.raises(asyncio.CancelledError):
            await active
        assert await asyncio.gather(*queued) == [[]] * 15
        assert runtime._dispatch_count == 0 and client.is_closed

    run_async(check())


def test_overload_notifications_are_bounded_and_cancelled_on_stop(config_path, caller, run_async):
    requests = []
    client = httpx.AsyncClient(transport=transport_for(raw_matches(1), requests))
    caller = replace(caller, conversation_kind="direct")

    async def check():
        runtime = Runtime(config_path, client_factory=lambda: client)
        entered, busy_entered = asyncio.Event(), asyncio.Event()

        async def stalled(_):
            entered.set()
            await asyncio.Event().wait()

        busy_messages = []

        async def stalled_busy(message):
            assert isinstance(message, TextReply)
            busy_messages.append(message.text)
            busy_entered.set()
            await asyncio.Event().wait()

        active = asyncio.create_task(runtime.dispatch(caller, "dota战绩", "123 1", stalled))
        await entered.wait()
        queued = [asyncio.create_task(capture(runtime, caller, "dota帮助", "")) for _ in range(15)]
        await asyncio.sleep(0)
        busy = asyncio.create_task(runtime.dispatch(caller, "dota帮助", "", stalled_busy))
        await busy_entered.wait()
        try:
            assert await capture(runtime, caller, "dota帮助", "") == []
            assert len(busy_messages) == 1 and "排队请求较多" in busy_messages[0]
            await runtime.close()
            await asyncio.sleep(0)
            assert busy.cancelled() and active.cancelled()
            assert await asyncio.gather(*queued) == [[]] * 15
            assert client.is_closed and runtime._dispatch_count == 0
        finally:
            await runtime.close()
            for task in (active, busy, *queued):
                task.cancel()
            await asyncio.gather(active, busy, *queued, return_exceptions=True)

    run_async(check())


def test_missing_session_allows_id_query_but_never_saves_or_guesses(config_path, caller, run_async):
    requests = []
    client = httpx.AsyncClient(transport=transport_for(raw_matches(), requests))

    async def check():
        runtime = Runtime(config_path, client_factory=lambda: client)
        replies = await capture(runtime, caller, "dota战绩", "123 12")
        assert "无法确认会话" in replies[-1] and not runtime._selections._results
        assert "无法确认会话" in (await capture(runtime, caller, "dota比赛", "第1场"))[0]
        assert "没有返回" in (await capture(runtime, caller, "dota比赛", "1"))[0]
        await runtime.close()

    run_async(check())


def test_concurrent_dispatch_is_ordered_and_latest_delivered_list_wins(
    config_path, caller, run_async
):
    requests = []
    rows = raw_matches(1)
    client = httpx.AsyncClient(transport=transport_for(rows, requests))
    caller = replace(caller, conversation_kind="direct")

    async def check():
        runtime = Runtime(config_path, client_factory=lambda: client)
        entered, release = asyncio.Event(), asyncio.Event()

        async def slow_send(_):
            entered.set()
            await release.wait()

        first = asyncio.create_task(runtime.dispatch(caller, "dota战绩", "123 1", slow_send))
        await entered.wait()
        second = asyncio.create_task(capture(runtime, caller, "dota战绩", "123 1"))
        await asyncio.sleep(0)
        assert len(requests) == 1
        rows[:] = raw_matches(1, base=2000)
        release.set()
        await asyncio.gather(first, second)
        await capture(runtime, caller, "dota比赛", "第1场")
        assert requests[-1]["variables"] == {"matchId": 2001}
        await runtime.close()

    run_async(check())


def test_rebind_away_and_back_while_sending_does_not_commit_candidate(
    config_path, caller, run_async
):
    requests = []
    client = httpx.AsyncClient(transport=transport_for(raw_matches(1), requests))
    caller = replace(caller, conversation_kind="direct")

    async def check():
        runtime = Runtime(config_path, client_factory=lambda: client)
        await runtime.handle(caller, "dota绑定", "123")
        entered, release = asyncio.Event(), asyncio.Event()

        async def slow_send(_):
            entered.set()
            await release.wait()

        sending = asyncio.create_task(runtime.dispatch(caller, "dota战绩", "1", slow_send))
        await entered.wait()
        await runtime.handle(caller, "dota改绑", "456")
        await runtime.handle(caller, "dota改绑", "123")
        release.set()
        await sending
        assert not runtime._selections._results
        await runtime.close()

    run_async(check())


def test_stop_cancels_sender_and_drains_queued_dispatch(config_path, caller, run_async):
    requests = []
    client = httpx.AsyncClient(transport=transport_for(raw_matches(1), requests))
    caller = replace(caller, conversation_kind="direct")

    async def check():
        runtime = Runtime(config_path, client_factory=lambda: client)
        entered = asyncio.Event()

        async def stalled(_):
            entered.set()
            await asyncio.Event().wait()

        active = asyncio.create_task(runtime.dispatch(caller, "dota战绩", "123 1", stalled))
        await entered.wait()
        queued = asyncio.create_task(capture(runtime, caller, "dota战绩", "123 1"))
        await runtime.close()
        with pytest.raises(asyncio.CancelledError):
            await active
        assert await queued == []
        assert await capture(runtime, caller, "dota帮助", "") == []
        assert runtime._dispatch_count == 0 and runtime._sending is None
        assert (
            runtime.state == State.STOPPED and client.is_closed and not runtime._selections._results
        )

    run_async(check())
