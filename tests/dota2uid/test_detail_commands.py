"""Direct-ID adapter consumption and same-data detail text; all data is synthetic."""

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime

import httpx
import pytest
from dota2forge_core import (
    AccountId,
    DataMetadata,
    DataSource,
    MatchDetail,
    MatchDetailUnavailable,
    MatchId,
    MatchParticipant,
    ProviderError,
    ProviderErrorCode,
)
from dota2forge_core.infrastructure.stratz import MATCH_ANALYSIS_QUERY, MATCH_DETAIL_QUERY
from Dota2UID.commands import Action, CommandError, parse_command
from Dota2UID.presentation import match_detail_text, provider_error_text
from Dota2UID.runtime import Runtime, State

META = DataMetadata(DataSource.STRATZ, datetime(2026, 10, 1, tzinfo=UTC))


def detail_data():
    return {
        "data": {
            "match": {
                "id": 7000000001,
                "startDateTime": 1700000000,
                "durationSeconds": 2105,
                "didRadiantWin": False,
                "gameMode": "ALL_PICK",
                "gameVersionId": 0,
                "isStats": False,
                "parsedDateTime": None,
                "players": [
                    {
                        "playerSlot": 0,
                        "steamAccountId": 123,
                        "steamAccount": {"id": 123, "name": "Synthetic Player"},
                        "isRadiant": False,
                        "heroId": 2,
                        "kills": 0,
                        "deaths": 0,
                        "assists": 8,
                        "goldPerMinute": 0,
                        "experiencePerMinute": None,
                        **{f"item{i}Id": 0 for i in range(6)},
                    }
                ],
            }
        }
    }


@pytest.mark.parametrize("value", ["1", "7000000001", "9223372036854775807"])
def test_exact_direct_match_command(value):
    command = parse_command("dota比赛", value)
    assert command.action == Action.MATCH and command.match_id == MatchId(int(value))
    assert command.account is None


@pytest.mark.parametrize(
    "value",
    [
        "",
        "1 2",
        "01",
        "+1",
        "0",
        "-1",
        "１",
        "1.0",
        "第01场",
        "9223372036854775808",
        "https://stratz.com/matches/1",
    ],
)
def test_invalid_match_command_is_not_account_or_recent_query(value):
    with pytest.raises(CommandError):
        parse_command("dota比赛", value)


def test_detail_text_preserves_anonymity_zero_false_and_proven_perspective():
    known = MatchParticipant(
        player_slot=0,
        account_id=AccountId(123),
        display_name="[Synthetic]\nName",
        is_anonymous=False,
        is_radiant=False,
        hero_id=2,
        kills=0,
        deaths=0,
        assists=8,
        gold_per_minute=0,
        item_ids=(0, 1, None, 0, 0, 0),
    )
    anonymous = MatchParticipant(player_slot=1, is_anonymous=True, is_radiant=True)
    unknown = MatchParticipant(player_slot=2)
    detail = MatchDetail(
        MatchId(1),
        META,
        duration_seconds=0,
        did_radiant_win=False,
        has_stats=False,
        game_version_id=0,
        players=(known, anonymous, unknown),
    )
    replies = match_detail_text(detail, AccountId(123))
    text = "\n".join(replies)
    assert len(replies) == 3 and all(len(page) < 1600 for page in replies)
    assert "[我方]" in text and "Synthetic Name" in text and "123" not in text
    assert "匿名参赛者" in text and "身份未知" in text and "阵营未知" in text
    assert "0分00秒" in text and "胜方：夜魇" in text and "isStats：否" in text
    assert "K/D/A 0/0/8" in text and "GPM 0 / XPM 未知" in text
    assert "装备 ID 空/1/未知" in text and "UTC+8" in text
    assert "详情状态：未解析（上游 isStats=False）" in text
    assert "[我方]" not in "\n".join(match_detail_text(detail, AccountId(456)))
    assert "[我方]" not in "\n".join(match_detail_text(detail))


@pytest.mark.parametrize("players", [None, ()])
def test_null_and_empty_participants_remain_distinct(players):
    text = match_detail_text(MatchDetail(MatchId(1), META, players=players))[0]
    assert ("参赛者数据未知" if players is None else "0 名参赛者") in text
    assert "数据观测时间：未知" in text and "来源：stratz" in text


def test_detail_text_has_observed_and_parsed_time_without_completeness_claim():
    detail = MatchDetail(
        MatchId(1),
        replace(META, observed_at=META.fetched_at),
        started_at=META.fetched_at,
        parsed_at=META.fetched_at,
        game_mode="ALL_PICK",
        has_stats=True,
    )
    text = match_detail_text(detail)[0]
    assert "数据观测时间：2026-10-01 08:00:00 UTC+8" in text
    assert "解析时间：2026-10-01 08:00:00 UTC+8" in text
    assert "isStats：是" in text and "不证明详情字段完整" in text
    assert "详情状态：上游已标记解析（不代表字段完整）" in text


def test_unavailable_result_does_not_become_notfound_private_or_normal_match():
    text = match_detail_text(MatchDetailUnavailable(MatchId(1), META))[0]
    assert "没有返回该比赛详情" in text and "原因和隐私状态未知" in text
    assert "不能据此判定" in text and "胜方" not in text
    assert "详情状态：未返回（原因和隐私状态未知）" in text


def test_fixture_detail_never_links_or_labels_itself_as_live_stratz():
    metadata = replace(META, source=DataSource.FIXTURE)
    for result in (MatchDetail(MatchId(1), metadata), MatchDetailUnavailable(MatchId(1), metadata)):
        text = "\n".join(match_detail_text(result))
        assert "来源：fixture" in text and "stratz.com" not in text and "STRATZ 本次" not in text


@pytest.mark.parametrize("code", [ProviderErrorCode.PRIVATE, ProviderErrorCode.NOT_FOUND])
def test_classified_detail_errors_name_match_subject(code):
    text = provider_error_text(ProviderError(code, DataSource.STRATZ), subject="比赛")
    assert "比赛" in text and "玩家" not in text


def test_runtime_direct_lookup_does_not_bind_fetch_player_or_recent(config_path, caller, run_async):
    requests = []

    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        if "Dota2ForgeMatchDetail" in payload["query"]:
            assert payload == {"query": MATCH_DETAIL_QUERY, "variables": {"matchId": 7000000001}}
            return httpx.Response(200, json=detail_data())
        assert payload == {"query": MATCH_ANALYSIS_QUERY, "variables": {"matchId": 7000000001}}
        return httpx.Response(
            200,
            json={
                "data": {
                    "match": {
                        "id": 7000000001,
                        "players": [
                            {
                                "playerSlot": 0,
                                "steamAccountId": 123,
                                "stats": {
                                    "networthPerMinute": [100],
                                    "itemPurchases": [],
                                },
                            }
                        ],
                    }
                }
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def check():
        runtime = Runtime(config_path, client_factory=lambda: client)
        direct = await runtime.handle(caller, "dota比赛", "7000000001")
        assert "比赛 7000000001" in direct[0] and "[我方]" not in "\n".join(direct)
        assert "尚未绑定" in (await runtime.handle(caller, "dota账号", ""))[0]
        await runtime.handle(caller, "dota绑定", "123")
        own = await runtime.handle(caller, "dota比赛", "7000000001")
        assert "[我方]" in "\n".join(own)
        await runtime.handle(caller, "dota改绑", "456")
        other = await runtime.handle(caller, "dota比赛", "7000000001")
        assert "[我方]" not in "\n".join(other)
        before = len(requests)
        assert "参数不正确" in (await runtime.handle(caller, "dota比赛", "01"))[0]
        assert len(requests) == before == 6
        await runtime.close()
        assert runtime.state == State.STOPPED and client.is_closed and runtime._details is None

    run_async(check())


def test_runtime_null_detail_uses_unavailable_text_and_closes(config_path, caller, run_async):
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"data": {"match": None}}))
    )

    async def check():
        runtime = Runtime(config_path, client_factory=lambda: client)
        text = (await runtime.handle(caller, "dota比赛", "1"))[0]
        assert "没有返回" in text and "隐私状态未知" in text
        await runtime.close()
        assert client.is_closed

    run_async(check())


def test_runtime_detail_quota_failure_is_not_retried(config_path, caller, run_async):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "600"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def check():
        runtime = Runtime(config_path, client_factory=lambda: client)
        for _ in range(2):
            assert "额度已用尽" in (await runtime.handle(caller, "dota比赛", "1"))[0]
        assert len(calls) == 1
        await runtime.close()
        assert client.is_closed

    run_async(check())


def test_runtime_stop_cancels_detail_and_retains_client_ownership(config_path, caller, run_async):
    async def check():
        started = asyncio.Event()

        async def handler(_):
            started.set()
            await asyncio.Event().wait()

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        runtime = Runtime(config_path, client_factory=lambda: client)
        query = asyncio.create_task(runtime.handle(caller, "dota比赛", "1"))
        await started.wait()
        await runtime.close()
        with pytest.raises(asyncio.CancelledError):
            await query
        assert runtime.state == State.STOPPED and client.is_closed

    run_async(check())
