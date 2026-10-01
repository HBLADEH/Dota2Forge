"""Synthetic STRATZ match responses; every HTTP request uses MockTransport."""

import asyncio
import copy
import json
from datetime import UTC, datetime

import httpx
import pytest
from dota2forge_core import (
    AccountId,
    DataSource,
    MatchDetail,
    MatchDetailService,
    MatchDetailUnavailable,
    MatchId,
    MatchParseState,
    ProviderError,
    ProviderErrorCode,
    ValidationError,
)
from dota2forge_core.infrastructure.stratz import MATCH_DETAIL_QUERY, StratzProvider


def player_row(index=0):
    return {
        "playerSlot": index,
        "steamAccountId": 123 + index,
        "steamAccount": {"id": 123 + index, "name": "Synthetic Participant"},
        "isRadiant": index < 5,
        "heroId": index + 1,
        "kills": 0,
        "deaths": 0,
        "assists": 0,
        "goldPerMinute": 0,
        "experiencePerMinute": None,
        **{f"item{i}Id": 0 if i % 2 == 0 else None for i in range(6)},
    }


def response():
    return {
        "data": {
            "match": {
                "id": 1,
                "startDateTime": 1700000000,
                "durationSeconds": 0,
                "didRadiantWin": False,
                "gameMode": "RANKED_ALL_PICK",
                "gameVersionId": 0,
                "isStats": False,
                "parsedDateTime": None,
                "players": [player_row(i) for i in range(10)],
            }
        }
    }


async def with_provider(clock, handler, action):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False) as client:
        await action(StratzProvider(client, token="synthetic-token", clock=clock))
    assert client.is_closed


def test_fixed_detail_query_consumes_no_player_or_recent_endpoint(clock, run_async):
    requests = []

    def handle(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert payload == {"query": MATCH_DETAIL_QUERY, "variables": {"matchId": 1}}
        return httpx.Response(200, json=response())

    async def check(provider):
        result = await MatchDetailService(provider).get_match_detail("1")
        assert isinstance(result, MatchDetail)
        assert result.match_id == MatchId(1) and result.metadata.source == DataSource.STRATZ
        assert result.started_at == datetime.fromtimestamp(1700000000, UTC)
        assert result.duration_seconds == 0 and result.did_radiant_win is False
        assert result.game_mode == "RANKED_ALL_PICK" and result.game_version_id == 0
        assert result.has_stats is False and result.parsed_at is None
        assert result.parse_state is MatchParseState.UNPARSED
        assert result.metadata.fetched_at == clock.now() and result.metadata.observed_at is None
        assert result.metadata.patch is None and len(result.players) == 10
        assert result.players[0].kills == 0 and result.players[5].is_radiant is False
        assert result.players[0].item_ids == (0, None, 0, None, 0, None)
        assert result.participant(AccountId(123)) is result.players[0]
        assert result.participant(AccountId(999)) is None
        assert len(requests) == 1

    run_async(with_provider(clock, handle, check))


@pytest.mark.parametrize("raw_account", [0, 4294967295, None])
def test_anonymous_or_unknown_identity_is_not_disclosed(clock, run_async, raw_account):
    raw = response()
    row = raw["data"]["match"]["players"][0]
    row["steamAccountId"] = raw_account
    row["steamAccount"] = {"id": raw_account, "name": "Must Not Disclose"}

    async def check(provider):
        result = await provider.get_match_detail(MatchId(1))
        player = result.players[0]
        assert player.account_id is None and player.display_name is None
        assert player.is_anonymous is (None if raw_account is None else True)
        assert "Must Not Disclose" not in repr(result)

    run_async(with_provider(clock, lambda _: httpx.Response(200, json=raw), check))


@pytest.mark.parametrize("players", [None, [], [player_row()]])
def test_null_empty_partial_players_are_distinct(clock, run_async, players):
    raw = response()
    raw["data"]["match"]["players"] = players

    async def check(provider):
        result = await provider.get_match_detail(MatchId(1))
        assert isinstance(result, MatchDetail)
        assert result.players is None if players is None else len(result.players) == len(players)

    run_async(with_provider(clock, lambda _: httpx.Response(200, json=raw), check))


def test_null_match_is_unknown_cause_no_data_not_notfound_private_or_normal_match(clock, run_async):
    async def check(provider):
        result = await provider.get_match_detail(MatchId(1))
        assert isinstance(result, MatchDetailUnavailable)
        assert result.match_id == MatchId(1) and result.metadata.source == DataSource.STRATZ
        assert result.metadata.fetched_at == clock.now()

    run_async(
        with_provider(clock, lambda _: httpx.Response(200, json={"data": {"match": None}}), check)
    )


def test_all_optional_nulls_and_steam_null_are_valid(clock, run_async):
    raw = response()
    match = raw["data"]["match"]
    for key in match:
        if key not in {"id", "players"}:
            match[key] = None
    player = match["players"][0]
    for key in player:
        player[key] = None
    match["players"] = [player]

    async def check(provider):
        result = await provider.get_match_detail(MatchId(1))
        assert len(result.missing_fields) == 7
        assert result.players[0].item_ids == (None,) * 6
        assert result.players[0].account_id is None and result.players[0].is_anonymous is None

    run_async(with_provider(clock, lambda _: httpx.Response(200, json=raw), check))


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("id",), 2),
        (("id",), True),
        (("startDateTime",), -1),
        (("startDateTime",), 10**100),
        (("parsedDateTime",), -1),
        (("parsedDateTime",), 10**100),
        (("durationSeconds",), -1),
        (("didRadiantWin",), 0),
        (("gameMode",), 1),
        (("gameMode",), "invalid mode"),
        (("gameVersionId",), True),
        (("isStats",), 0),
        (("players",), "bad"),
        (("players",), [None]),
        (("players",), [player_row(i) for i in range(11)]),
        (("players",), [player_row(), player_row()]),
        (("players", 0, "steamAccountId"), -1),
        (("players", 0, "steamAccountId"), 4294967296),
        (("players", 0, "steamAccount", "id"), 456),
        (("players", 0, "steamAccount", "name"), 1),
        (("players", 0, "heroId"), 0),
        (("players", 0, "isRadiant"), 1),
        (("players", 0, "playerSlot"), 256),
        (("players", 0, "kills"), True),
        (("players", 0, "goldPerMinute"), -1),
        (("players", 0, "item5Id"), -1),
    ],
)
def test_malformed_detail_never_becomes_partial_success(clock, run_async, path, value):
    raw = response()
    node = raw["data"]["match"]
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value

    async def check(provider):
        with pytest.raises(ProviderError) as error:
            await provider.get_match_detail(MatchId(1))
        assert error.value.code == ProviderErrorCode.INVALID_RESPONSE

    run_async(with_provider(clock, lambda _: httpx.Response(200, json=raw), check))


def test_missing_selected_fields_are_schema_failures(clock, run_async):
    raws = [{}, {"data": {}}, {"data": None}, {"data": {"match": []}}]
    for key in response()["data"]["match"]:
        raw = response()
        del raw["data"]["match"][key]
        raws.append(raw)
    for key in player_row():
        raw = response()
        del raw["data"]["match"]["players"][0][key]
        raws.append(raw)
    for raw in raws:

        async def check(provider):
            with pytest.raises(ProviderError) as error:
                await provider.get_match_detail(MatchId(1))
            assert error.value.code == ProviderErrorCode.INVALID_RESPONSE

        run_async(with_provider(clock, lambda _, raw=raw: httpx.Response(200, json=raw), check))


@pytest.mark.parametrize("base", [response(), {"data": {"match": None}}])
def test_graphql_errors_fail_even_with_partial_or_null_data(clock, run_async, base):
    raw = copy.deepcopy(base)
    raw["errors"] = [{"message": "synthetic resolver failure"}]

    async def check(provider):
        with pytest.raises(ProviderError) as error:
            await provider.get_match_detail(MatchId(1))
        assert error.value.code == ProviderErrorCode.INVALID_RESPONSE

    run_async(with_provider(clock, lambda _: httpx.Response(200, json=raw), check))


def test_known_account_can_have_missing_name_and_parsed_time(clock, run_async):
    raw = response()
    raw["data"]["match"]["players"][0]["steamAccount"] = None
    raw["data"]["match"]["parsedDateTime"] = 1700001000
    raw["errors"] = []

    async def check(provider):
        result = await provider.get_match_detail(MatchId(1))
        assert result.players[0].account_id == AccountId(123)
        assert result.players[0].display_name is None
        assert result.parsed_at == datetime.fromtimestamp(1700001000, UTC)
        assert result.metadata.observed_at is None

    run_async(with_provider(clock, lambda _: httpx.Response(200, json=raw), check))


def test_provider_rejects_untyped_match_id_without_sending(clock, run_async):
    async def check(provider):
        with pytest.raises(ValidationError):
            await provider.get_match_detail(1)

    run_async(with_provider(clock, lambda _: pytest.fail("Invalid ID sent HTTP"), check))


def test_detail_quota_is_shared_with_recent_and_player_queries(clock, run_async):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=response(), headers={"X-RateLimit-Remaining-Day": "0"})

    async def check(provider):
        await provider.get_match_detail(MatchId(1))
        for operation in (
            provider.get_player(AccountId(123)),
            provider.get_recent_matches(AccountId(123)),
        ):
            with pytest.raises(ProviderError) as error:
                await operation
            assert error.value.code == ProviderErrorCode.RATE_LIMITED
        assert len(calls) == 1

    run_async(with_provider(clock, handle, check))


def test_detail_cancel_unblocks_shared_client_and_has_no_retry(clock, run_async):
    async def check():
        started = asyncio.Event()
        calls = []

        async def handler(request):
            calls.append(request)
            if len(calls) == 1:
                started.set()
                await asyncio.Event().wait()
            return httpx.Response(200, json=response())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = StratzProvider(client, token="synthetic-token", clock=clock)
            task = asyncio.create_task(provider.get_match_detail(MatchId(1)))
            await started.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert isinstance(await provider.get_match_detail(MatchId(1)), MatchDetail)
        assert client.is_closed and len(calls) == 2

    run_async(check())
