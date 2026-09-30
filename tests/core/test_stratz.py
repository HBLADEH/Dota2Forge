"""Raw, entirely synthetic STRATZ responses; these are not recorded player data."""

import asyncio
import copy
import importlib
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from dota2forge_core import (
    AccountId,
    DataSource,
    Dota2Service,
    ProviderError,
    ProviderErrorCode,
    ValidationError,
)
from dota2forge_core.infrastructure.stratz import (
    MAX_PAGES,
    PLAYER_QUERY,
    RECENT_MATCHES_QUERY,
    StratzProvider,
)

TOKEN = "synthetic-token"
ACCOUNT = AccountId(123)


def envelope(**fields):
    return {"data": {"player": {"steamAccountId": ACCOUNT.value, **fields}}}


def player_response(rank=51):
    return envelope(
        steamAccount={"id": ACCOUNT.value, "name": "Synthetic Player", "seasonRank": rank}
    )


def match_row(index=1, **fields):
    return {
        "id": 1000 + index,
        "startDateTime": 1700000000 + index,
        "durationSeconds": 2400,
        "didRadiantWin": False,
        "players": [
            {
                "steamAccountId": ACCOUNT.value,
                "heroId": 1,
                "isRadiant": False,
                "kills": 0,
                "deaths": 0,
                "assists": 0,
                "goldPerMinute": 0,
                "experiencePerMinute": None,
            }
        ],
        **fields,
    }


async def with_provider(clock, handler, action):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await action(StratzProvider(client, token=TOKEN, clock=clock))
    assert client.is_closed
    return result


def test_service_consumes_real_provider_with_synthetic_transport(
    repository, identity, clock, run_async
):
    requests = []

    def respond(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert "123" not in payload["query"]
        if payload["query"] == PLAYER_QUERY:
            assert payload["variables"] == {"accountId": 123}
            return httpx.Response(200, json=player_response())
        assert payload["query"] == RECENT_MATCHES_QUERY
        assert payload["variables"] == {"accountId": 123, "take": 10, "skip": 0}
        return httpx.Response(200, json=envelope(matches=[match_row(i) for i in range(10)]))

    async def check(provider):
        service = Dota2Service(repository, provider, provider, clock)
        await service.bind_account(identity, "123")
        player = await service.get_player(identity)
        assert player.rank_tier == 51 and player.display_name == "Synthetic Player"
        assert player.account_id == ACCOUNT
        assert player.metadata.source == DataSource.STRATZ
        assert player.metadata.fetched_at == clock.now()
        assert player.metadata.observed_at is None and player.metadata.patch is None
        matches = await service.get_recent_matches(identity)
        assert len(matches.matches) == 10
        newest = matches.matches[0]
        assert newest.match_id == 1009
        assert newest.started_at == datetime.fromtimestamp(1700000009, UTC)
        assert newest.duration_seconds == 2400 and newest.hero_id == 1
        assert newest.is_win is True  # Dire player + Dire victory.
        assert (newest.kills, newest.deaths, newest.assists, newest.gold_per_minute) == (0, 0, 0, 0)
        assert newest.missing_fields == ("experience_per_minute",)
        assert len(requests) == 2
        assert (await service.get_binding(identity)).account_id == ACCOUNT

    run_async(with_provider(clock, respond, check))


def test_rank_can_decrease_and_public_flag_does_not_deny_player(clock, run_async):
    responses = iter([player_response(52), player_response(51)])

    def respond(_):
        value = next(responses)
        value["data"]["player"]["steamAccount"]["isStratzPublic"] = False
        return httpx.Response(200, json=value)

    async def check(p):
        assert (await p.get_player(ACCOUNT)).rank_tier == 52
        assert (await p.get_player(ACCOUNT)).rank_tier == 51

    run_async(with_provider(clock, respond, check))


@pytest.mark.parametrize("steam", [None, {"id": 123, "name": None, "seasonRank": None}])
def test_explicit_optional_nulls_preserve_missing_fields(clock, run_async, steam):
    async def check(p):
        profile = await p.get_player(ACCOUNT)
        assert profile.missing_fields == ("display_name", "rank_tier")

    run_async(
        with_provider(
            clock, lambda _: httpx.Response(200, json=envelope(steamAccount=steam)), check
        )
    )


def test_zero_rank_and_empty_name_are_not_missing(clock, run_async):
    raw = player_response(0)
    raw["data"]["player"]["steamAccount"]["name"] = ""

    async def check(p):
        result = await p.get_player(ACCOUNT)
        assert result.rank_tier == 0 and result.display_name == "" and result.missing_fields == ()

    run_async(with_provider(clock, lambda _: httpx.Response(200, json=raw), check))


@pytest.mark.parametrize("limit", [1, 10, 20, 21, 100])
def test_bounded_pagination_supports_contract_limits(clock, run_async, limit):
    rows = [match_row(i) for i in range(100, 0, -1)]
    calls = []

    def respond(request):
        variables = json.loads(request.content)["variables"]
        calls.append(variables)
        assert 1 <= variables["take"] <= 20
        start = variables["skip"]
        clock.instant += timedelta(seconds=1)
        return httpx.Response(200, json=envelope(matches=rows[start : start + variables["take"]]))

    async def check(p):
        result = await p.get_recent_matches(ACCOUNT, limit)
        assert len(result.matches) == limit
        assert [m.match_id for m in result.matches] == list(range(1100, 1100 - limit, -1))
        assert result.metadata.fetched_at == clock.now()
        assert result.matches[0].metadata.fetched_at <= result.metadata.fetched_at
        assert all(
            m.account_id == ACCOUNT and m.metadata.source == DataSource.STRATZ
            for m in result.matches
        )
        assert len(calls) == (limit + 19) // 20

    run_async(with_provider(clock, respond, check))


def test_remote_take_cap_does_not_pretend_a_short_page_is_complete(clock, run_async):
    rows = [match_row(i) for i in range(12, 0, -1)]
    skips = []

    def respond(request):
        v = json.loads(request.content)["variables"]
        skips.append(v["skip"])
        return httpx.Response(
            200, json=envelope(matches=rows[v["skip"] : v["skip"] + min(3, v["take"])])
        )

    async def check(p):
        result = await p.get_recent_matches(ACCOUNT, 10)
        assert len(result.matches) == 10
        assert skips == [0, 3, 6, 9]

    run_async(with_provider(clock, respond, check))


@pytest.mark.parametrize("rows", [[], [match_row()]])
def test_fewer_matches_and_empty_result_are_valid(clock, run_async, rows):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json=envelope(matches=rows if len(calls) == 1 else []))

    async def check(p):
        result = await p.get_recent_matches(ACCOUNT)
        assert len(result.matches) == len(rows)
        assert result.metadata.source == DataSource.STRATZ
        assert result.metadata.observed_at is None
        assert len(calls) == (1 if not rows else 2)

    run_async(with_provider(clock, respond, check))


def test_duplicate_rows_are_deduplicated_and_out_of_order_rows_sorted(clock, run_async):
    pages = iter([[match_row(1), match_row(2), match_row(2)], [match_row(3)]])

    async def check(p):
        result = await p.get_recent_matches(ACCOUNT, 3)
        assert [m.match_id for m in result.matches] == [1003, 1002, 1001]

    run_async(
        with_provider(
            clock, lambda _: httpx.Response(200, json=envelope(matches=next(pages))), check
        )
    )


@pytest.mark.parametrize("conflict", [False, True])
def test_repeated_page_stops_and_conflicting_duplicate_fails(clock, run_async, conflict):
    calls = []

    def respond(request):
        calls.append(request)
        row = match_row()
        if conflict and len(calls) > 1:
            row["durationSeconds"] += 1
        return httpx.Response(200, json=envelope(matches=[row]))

    async def check(p):
        if conflict:
            with pytest.raises(ProviderError) as error:
                await p.get_recent_matches(ACCOUNT)
            assert error.value.code == ProviderErrorCode.INVALID_RESPONSE
        else:
            assert len((await p.get_recent_matches(ACCOUNT)).matches) == 1
        assert len(calls) == 2

    run_async(with_provider(clock, respond, check))


def test_page_budget_returns_bounded_partial_history(clock, run_async):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json=envelope(matches=[match_row(100 - len(calls))]))

    async def check(p):
        result = await p.get_recent_matches(ACCOUNT, 100)
        assert len(calls) == MAX_PAGES
        assert len(result.matches) == MAX_PAGES

    run_async(with_provider(clock, respond, check))


@pytest.mark.parametrize(
    ("radiant", "won", "expected"),
    [
        (True, True, True),
        (True, False, False),
        (False, True, False),
        (False, False, True),
        (None, True, None),
        (False, None, None),
        (None, None, None),
    ],
)
def test_win_uses_both_sides_and_preserves_unknown(clock, run_async, radiant, won, expected):
    row = match_row(didRadiantWin=won)
    row["players"][0]["isRadiant"] = radiant

    async def check(p):
        assert (await p.get_recent_matches(ACCOUNT, 1)).matches[0].is_win is expected

    run_async(
        with_provider(clock, lambda _: httpx.Response(200, json=envelope(matches=[row])), check)
    )


def test_all_nullable_match_stats_remain_unknown(clock, run_async):
    row = match_row(durationSeconds=None, didRadiantWin=None)
    row["players"][0].update({key: None for key in row["players"][0] if key != "steamAccountId"})

    async def check(p):
        result = (await p.get_recent_matches(ACCOUNT, 1)).matches[0]
        assert result.missing_fields == (
            "hero_id",
            "duration_seconds",
            "kills",
            "deaths",
            "assists",
            "gold_per_minute",
            "experience_per_minute",
            "is_win",
        )

    run_async(
        with_provider(clock, lambda _: httpx.Response(200, json=envelope(matches=[row])), check)
    )


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        0,
        {},
        {"data": None},
        {"data": {}},
        {"data": {"player": None}},
        {"data": {"player": []}},
        {"data": {"player": {"steamAccountId": 456}}},
        envelope(steamAccount={"id": 456, "name": None, "seasonRank": None}),
        envelope(steamAccount={"id": 123, "name": 1, "seasonRank": 51}),
        envelope(steamAccount={"id": 123, "name": "Synthetic", "seasonRank": True}),
        envelope(steamAccount={"id": 123, "name": "Synthetic", "seasonRank": -1}),
        envelope(steamAccount={"id": 123, "name": "Synthetic"}),
        envelope(steamAccount={}),
        envelope(steamAccount=[]),
        {"data": {"player": {"steamAccountId": True, "steamAccount": None}}},
    ],
)
def test_invalid_player_shape_is_never_private_or_not_found(clock, run_async, payload):
    async def check(p):
        with pytest.raises(ProviderError) as error:
            await p.get_player(ACCOUNT)
        assert error.value.code == ProviderErrorCode.INVALID_RESPONSE

    run_async(with_provider(clock, lambda _: httpx.Response(200, json=payload), check))


@pytest.mark.parametrize(
    "errors",
    [
        None,
        {},
        "bad",
        [{"message": "synthetic-token private not found"}],
        [{"message": "synthetic-token", "path": ["player", "steamAccountId"]}],
        [{"message": "synthetic-token", "path": ["player", "steamAccount", "seasonRank"]}],
        [{"message": "synthetic-token", "extensions": {"code": "FORBIDDEN"}}],
    ],
)
@pytest.mark.parametrize("operation", ["get_player", "get_recent_matches"])
def test_graphql_errors_including_partial_data_fail_closed(clock, run_async, errors, operation):
    raw = player_response()
    raw["data"]["player"]["matches"] = []
    raw["errors"] = errors

    async def check(p):
        with pytest.raises(ProviderError) as error:
            await getattr(p, operation)(ACCOUNT)
        assert error.value.code == ProviderErrorCode.INVALID_RESPONSE
        assert TOKEN not in str(error.value)

    run_async(with_provider(clock, lambda _: httpx.Response(200, json=raw), check))


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("matches",), None),
        (("matches",), {}),
        (("matches",), [None]),
        (("matches", 0, "id"), 0),
        (("matches", 0, "id"), "1001"),
        (("matches", 0, "startDateTime"), True),
        (("matches", 0, "startDateTime"), -1),
        (("matches", 0, "startDateTime"), 10**100),
        (("matches", 0, "durationSeconds"), -1),
        (("matches", 0, "durationSeconds"), 2.5),
        (("matches", 0, "players"), None),
        (("matches", 0, "players"), []),
        (("matches", 0, "players"), [None]),
        (("matches", 0, "players", 0, "steamAccountId"), 456),
        (("matches", 0, "players", 0, "steamAccountId"), None),
        (("matches", 0, "players", 0, "heroId"), 0),
        (("matches", 0, "players", 0, "isRadiant"), 0),
        (("matches", 0, "players", 0, "kills"), True),
        (("matches", 0, "players", 0, "goldPerMinute"), "500"),
        (("matches", 0, "didRadiantWin"), 1),
    ],
)
def test_invalid_match_fields_are_rejected(clock, run_async, path, value):
    raw = envelope(matches=[match_row()])
    target = raw["data"]["player"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    async def check(p):
        with pytest.raises(ProviderError) as error:
            await p.get_recent_matches(ACCOUNT, 1)
        assert error.value.code == ProviderErrorCode.INVALID_RESPONSE

    run_async(with_provider(clock, lambda _: httpx.Response(200, json=raw), check))


def test_missing_selected_fields_and_excess_rows_fail(clock, run_async):
    raws = [envelope(), envelope(matches=[match_row(), match_row(2)])]
    for key in match_row():
        row = match_row()
        del row[key]
        raws.append(envelope(matches=[row]))
    for key in match_row()["players"][0]:
        row = match_row()
        del row["players"][0][key]
        raws.append(envelope(matches=[row]))
    for raw in raws:

        async def check(p):
            with pytest.raises(ProviderError) as error:
                await p.get_recent_matches(ACCOUNT, 1)
            assert error.value.code == ProviderErrorCode.INVALID_RESPONSE

        run_async(with_provider(clock, lambda _, raw=raw: httpx.Response(200, json=raw), check))


@pytest.mark.parametrize("limit", [0, -1, 101, True, 1.5, "10", None])
def test_invalid_provider_limits_never_send(clock, run_async, limit):
    async def check(p):
        with pytest.raises(ValidationError):
            await p.get_recent_matches(ACCOUNT, limit)

    def unexpected(_):
        pytest.fail("Invalid input must not send an HTTP request")

    run_async(with_provider(clock, unexpected, check))


@pytest.mark.parametrize("operation", ["get_player", "get_recent_matches"])
def test_invalid_account_never_sends(clock, run_async, operation):
    async def check(p):
        with pytest.raises(ValidationError):
            await getattr(p, operation)(123)

    run_async(with_provider(clock, lambda _: pytest.fail("Unexpected request"), check))


def test_second_page_failure_never_returns_partial_success(clock, run_async):
    calls = []

    def respond(request):
        calls.append(request)
        return (
            httpx.Response(200, json=envelope(matches=[match_row()]))
            if len(calls) == 1
            else httpx.Response(503)
        )

    async def check(p):
        with pytest.raises(ProviderError) as error:
            await p.get_recent_matches(ACCOUNT)
        assert error.value.code == ProviderErrorCode.UNAVAILABLE
        assert len(calls) == 2

    run_async(with_provider(clock, respond, check))


def test_exhausted_quota_stops_pagination(clock, run_async):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            200, json=envelope(matches=[match_row()]), headers={"X-RateLimit-Remaining-Day": "0"}
        )

    async def check(p):
        with pytest.raises(ProviderError) as error:
            await p.get_recent_matches(ACCOUNT)
        assert error.value.code == ProviderErrorCode.RATE_LIMITED
        assert len(calls) == 1

    run_async(with_provider(clock, respond, check))


def test_import_has_no_http_or_environment_side_effects(monkeypatch):
    import os

    import dota2forge_core.infrastructure.stratz as module

    def forbidden(*args, **kwargs):
        pytest.fail("Import must be inert")

    monkeypatch.setattr(os, "getenv", forbidden)
    monkeypatch.setattr(httpx.AsyncClient, "__init__", forbidden)
    monkeypatch.setattr(asyncio, "create_task", forbidden)
    importlib.reload(module)


def test_empty_error_list_is_allowed(clock, run_async):
    raw = copy.deepcopy(player_response())
    raw["errors"] = []

    async def check(p):
        assert (await p.get_player(ACCOUNT)).rank_tier == 51

    run_async(with_provider(clock, lambda _: httpx.Response(200, json=raw), check))
