"""Entirely synthetic REST responses; no player data or OpenDota network calls."""

import asyncio
import json
from contextlib import suppress
from dataclasses import replace
from datetime import timedelta

import httpx
import pytest
from dota2forge_core import (
    AccountId,
    DataSource,
    Dota2Service,
    MatchDetailService,
    MatchDetailUnavailable,
    MatchId,
    MatchParseState,
    ProviderError,
    ProviderErrorCode,
    ValidationError,
)
from dota2forge_core.infrastructure.opendota import OpenDotaProvider

ACCOUNT = AccountId(123)


def player(**fields):
    return {"profile": {"account_id": 123, "personaname": "Synthetic"}, "rank_tier": 51, **fields}


def match(index=1, **fields):
    return {
        "match_id": 1000 + index,
        "start_time": 1700000000 + index,
        "duration": 0,
        "hero_id": 1,
        "kills": 0,
        "deaths": 0,
        "assists": 0,
        "player_slot": 128,
        "radiant_win": False,
        "gold_per_min": 0,
        "xp_per_min": None,
        **fields,
    }


def detail(**fields):
    return {
        "match_id": 1001,
        "start_time": 1700000001,
        "duration": 0,
        "radiant_win": False,
        "version": 21,
        "game_mode": 22,
        "players": [
            {
                "account_id": 123,
                "personaname": "Synthetic",
                "player_slot": 128,
                "hero_id": 1,
                "kills": 0,
                "item_0": 0,
            }
        ],
        **fields,
    }


async def exercise(clock, handler, action, **client_options):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), **client_options
    ) as client:
        result = await action(OpenDotaProvider(client, clock=clock))
        assert not client.is_closed  # The provider does not own the injected client.
    assert client.is_closed
    return result


def test_existing_services_consume_opendota_without_binding_or_source_changes(
    repository, identity, clock, run_async
):
    calls = []

    def respond(request):
        calls.append(request)
        assert request.method == "GET" and request.url.host == "api.opendota.com"
        assert not any(
            name in request.headers for name in ("authorization", "cookie", "proxy-authorization")
        )
        assert "api_key" not in request.url.params
        if request.url.path.endswith("/matches"):
            assert request.url.params["limit"] == "20"
            assert request.url.params["significant"] == "0"
            assert request.url.params["sort"] == "start_time"
            assert set(request.url.params.get_list("project")) >= {"gold_per_min", "xp_per_min"}
            return httpx.Response(200, json=[match(1), match(2)])
        return httpx.Response(200, json=player() if "/players/" in request.url.path else detail())

    async def check(provider):
        service = Dota2Service(repository, provider, provider, clock)
        await service.bind_account(identity, "123")
        profile = await service.get_player(identity)
        recent = await service.get_recent_matches(identity, 20)
        result = await MatchDetailService(provider).get_match_detail("1001")
        assert profile.rank_tier == 51 and profile.display_name == "Synthetic"
        assert [row.match_id for row in recent.matches] == [1002, 1001]
        assert recent.matches[0].is_win is True and recent.matches[0].duration_seconds == 0
        assert recent.matches[0].experience_per_minute is None
        assert result.metadata.source is DataSource.OPENDOTA and result.metadata.observed_at is None
        assert result.game_mode == "OPENDOTA_22" and result.game_version_id is None
        assert result.parse_version == 21 and result.has_stats is None
        assert result.parse_state is MatchParseState.UPSTREAM_PARSED
        assert result.players[0].item_ids == (0, None, None, None, None, None)
        assert (await service.get_binding(identity)).account_id == ACCOUNT
        assert len(calls) == 3

    run_async(
        exercise(
            clock,
            respond,
            check,
            auth=("synthetic", "secret"),
            headers={"Authorization": "Bearer synthetic", "Proxy-Authorization": "synthetic"},
            cookies={"session": "synthetic"},
            params={"api_key": "synthetic"},
        )
    )


@pytest.mark.parametrize(
    "body,missing",
    [
        (player(profile=None, rank_tier=None), ("display_name", "rank_tier")),
        (player(rank_tier=0), ()),
    ],
)
def test_profile_missing_and_zero_are_distinct(clock, run_async, body, missing):
    async def check(provider):
        result = await provider.get_player(ACCOUNT)
        assert result.missing_fields == missing

    run_async(exercise(clock, lambda _: httpx.Response(200, json=body), check))


@pytest.mark.parametrize(
    "version,state",
    [
        (0, MatchParseState.PARTIAL),
        (None, MatchParseState.PARTIAL),
        (1, MatchParseState.UPSTREAM_PARSED),
    ],
)
@pytest.mark.parametrize("anonymous", [0, 4294967295, None])
def test_parser_marker_and_anonymous_names(clock, run_async, version, state, anonymous):
    body = detail(
        version=version,
        players=[{"account_id": anonymous, "personaname": "Do not disclose", "player_slot": 0}],
    )

    async def check(provider):
        result = await provider.get_match_detail(MatchId(1001))
        assert result.parse_state is state and result.parse_version == version
        participant = result.players[0]
        assert participant.account_id is None and participant.display_name is None
        assert participant.is_anonymous is (None if anonymous is None else True)
        assert participant.is_radiant is True

    run_async(exercise(clock, lambda _: httpx.Response(200, json=body), check))


@pytest.mark.parametrize(
    "payload", [None, {"match_id": 1001}, detail(players=None), detail(players=[])]
)
def test_null_missing_and_empty_detail_are_not_a_classified_error(clock, run_async, payload):
    async def check(provider):
        result = await provider.get_match_detail(MatchId(1001))
        if payload is None:
            assert isinstance(result, MatchDetailUnavailable)
        else:
            assert result.players == (None if payload.get("players") is None else ())

    run_async(exercise(clock, lambda _: httpx.Response(200, content=json.dumps(payload)), check))


@pytest.mark.parametrize(
    "operation,body",
    [
        ("player", {}),
        ("player", player(profile={"account_id": 124})),
        ("player", player(rank_tier=True)),
        ("player", player(profile=[])),
        ("player", player(profile={"account_id": 123, "personaname": 1})),
        ("recent", None),
        ("recent", [match(start_time=None)]),
        ("recent", [match(start_time=10**30)]),
        ("recent", [match(hero_id=0)]),
        ("recent", [match(player_slot=256)]),
        ("recent", [match(radiant_win=1)]),
        ("recent", [match(account_id=123.0)]),
        ("recent", [match(), match()]),
        ("recent", [match(i) for i in range(11)]),
        ("detail", {}),
        ("detail", detail(match_id=1002)),
        ("detail", detail(players=[{}] * 11)),
        ("detail", detail(players={})),
        ("detail", detail(players=[{"account_id": 123}, {"account_id": 123}])),
        ("detail", detail(players=[{"account_id": 1 << 40}])),
        ("detail", detail(players=[{"player_slot": 128, "isRadiant": True}])),
        ("detail", detail(version=-1)),
        ("detail", detail(version=True)),
        ("detail", detail(start_time=10**30)),
        ("detail", {"error": "synthetic private"}),
    ],
)
def test_malformed_responses_are_fixed_classified_errors(clock, run_async, operation, body):
    async def check(provider):
        with pytest.raises(ProviderError) as caught:
            if operation == "player":
                await provider.get_player(ACCOUNT)
            elif operation == "recent":
                await provider.get_recent_matches(ACCOUNT, 10)
            else:
                await provider.get_match_detail(MatchId(1001))
        assert caught.value.code is ProviderErrorCode.INVALID_RESPONSE
        assert caught.value.source is DataSource.OPENDOTA and "synthetic" not in str(caught.value)

    run_async(exercise(clock, lambda _: httpx.Response(200, json=body), check))


@pytest.mark.parametrize(
    "status,code",
    [
        (401, ProviderErrorCode.AUTHENTICATION),
        (403, ProviderErrorCode.UNAVAILABLE),
        (404, ProviderErrorCode.UNAVAILABLE),
        (500, ProviderErrorCode.UNAVAILABLE),
        (302, ProviderErrorCode.UNAVAILABLE),
        (429, ProviderErrorCode.RATE_LIMITED),
    ],
)
def test_http_failures_do_not_become_empty_or_private(clock, run_async, status, code):
    async def check(provider):
        with pytest.raises(ProviderError) as caught:
            await provider.get_player(ACCOUNT)
        assert caught.value.code is code

    run_async(
        exercise(clock, lambda _: httpx.Response(status, text="not a player response"), check)
    )


@pytest.mark.parametrize(
    "header,value",
    [
        ("Retry-After", "30"),
        ("Retry-After", "Tue, 30 Sep 2026 00:00:30 GMT"),
        ("X-Rate-Limit-Remaining-Minute", "0"),
        ("X-Rate-Limit-Remaining-Minute", "-1"),
        ("X-Rate-Limit-Remaining-Day", "0"),
    ],
)
def test_quota_stops_further_requests_until_reset(clock, run_async, header, value):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            429 if header == "Retry-After" else 200, json=player(), headers={header: value}
        )

    async def check(provider):
        if header == "Retry-After":
            with pytest.raises(ProviderError):
                await provider.get_player(ACCOUNT)
        else:
            await provider.get_player(ACCOUNT)
        with pytest.raises(ProviderError) as caught:
            await provider.get_player(ACCOUNT)
        wait = caught.value.retry_after_seconds
        assert wait is not None and wait > 0 and len(calls) == 1
        clock.instant += timedelta(seconds=wait)
        with suppress(ProviderError):
            await provider.get_player(ACCOUNT)
        assert len(calls) == 2

    run_async(exercise(clock, respond, check))


def test_unknown_429_reset_does_not_guess_or_retry(clock, run_async):
    calls = []

    async def check(provider):
        for _ in range(2):
            with pytest.raises(ProviderError) as caught:
                await provider.get_player(ACCOUNT)
            assert caught.value.retry_after_seconds is None
        assert len(calls) == 1

    def respond(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "invalid", "Date": "invalid"})

    run_async(exercise(clock, respond, check))


@pytest.mark.parametrize(
    "failure",
    [
        httpx.ReadTimeout("synthetic secret"),
        httpx.ConnectError("synthetic secret"),
        RuntimeError("program error"),
        asyncio.CancelledError(),
    ],
)
def test_transport_failure_cancel_and_program_errors(clock, run_async, failure):
    async def respond(_):
        raise failure

    async def check(provider):
        expected = ProviderError if isinstance(failure, httpx.RequestError) else type(failure)
        with pytest.raises(expected) as caught:
            await provider.get_player(ACCOUNT)
        if expected is ProviderError:
            assert "secret" not in str(caught.value) and caught.value.__cause__ is None

    run_async(exercise(clock, respond, check))


def test_timeout_closed_client_and_invalid_inputs_make_no_hidden_calls(clock, run_async):
    async def check():
        async def slow(_):
            await asyncio.Event().wait()

        async with httpx.AsyncClient(transport=httpx.MockTransport(slow)) as client:
            provider = OpenDotaProvider(client, clock=clock, timeout_seconds=0.01)
            with pytest.raises(ProviderError) as caught:
                await provider.get_player(ACCOUNT)
            assert caught.value.code is ProviderErrorCode.TIMEOUT
        with pytest.raises(ProviderError) as caught:
            await provider.get_player(ACCOUNT)
        assert caught.value.code is ProviderErrorCode.UNAVAILABLE
        with pytest.raises(ValidationError):
            await provider.get_player("123")
        with pytest.raises(ValidationError):
            await provider.get_match_detail(1001)
        for limit in (True, 0, 101, 1.0):
            with pytest.raises(ValidationError):
                await provider.get_recent_matches(ACCOUNT, limit)
        for timeout in (0, -1, 61, float("inf"), True):
            with pytest.raises(ValidationError):
                OpenDotaProvider(client, clock=clock, timeout_seconds=timeout)

    run_async(check())


def test_invalid_json_and_empty_recent(clock, run_async):
    responses = iter([httpx.Response(200, text="invalid"), httpx.Response(200, json=[])])

    async def check(provider):
        with pytest.raises(ProviderError) as caught:
            await provider.get_player(ACCOUNT)
        assert caught.value.code is ProviderErrorCode.INVALID_RESPONSE
        assert (await provider.get_recent_matches(ACCOUNT, 10)).matches == ()

    run_async(exercise(clock, lambda _: next(responses), check))


@pytest.mark.parametrize("parse_version", [0, 21])
def test_both_adapters_and_renderer_preserve_opendota_marker(
    repository, identity, clock, run_async, parse_version
):
    from astrbot_plugin_dota2forge.application import AstrApplication, AstrTextReply
    from dota2forge_renderer import MatchDetailCard, PillowRenderer
    from Dota2UID.presentation import match_detail_text

    async def check(provider):
        value = await provider.get_match_detail(MatchId(1001))
        assert (
            f"version：{parse_version}" in match_detail_text(value)[0]
            and "isStats" not in match_detail_text(value)[0]
        )
        application = AstrApplication(
            Dota2Service(repository, provider, provider, clock),
            MatchDetailService(provider),
            image_mode=False,
        )
        replies = await application.handle(identity, "dota比赛", "1001")
        assert (
            isinstance(replies[0], AstrTextReply) and f"version {parse_version}" in replies[0].text
        )
        renderer = PillowRenderer()
        try:
            assert renderer.render(MatchDetailCard(value)).data.startswith(b"\x89PNG")
        finally:
            renderer.close()
            await application.close()
        assert replace(value, parse_version=None).parse_state is MatchParseState.PARTIAL

    run_async(
        exercise(clock, lambda _: httpx.Response(200, json=detail(version=parse_version)), check)
    )
