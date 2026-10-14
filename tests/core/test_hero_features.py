"""Synthetic hero observations, strict filters, cache cancellation and native evidence."""

import asyncio
import copy
import json
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from dota2forge_core import (
    AccountId,
    DataMetadata,
    DataSource,
    GamePatch,
    HeroFeatureService,
    HeroMetaSnapshot,
    HeroWinBucket,
    MatchAnalysis,
    MatchDetail,
    MatchId,
    MatchParticipant,
    MetaRequest,
    MetaSort,
    MetricSemantic,
    MetricSeries,
    ParticipantAnalysis,
    ProviderError,
    ProviderErrorCode,
    PurchaseEvent,
    RankBracket,
    ReviewChartKind,
    ReviewChartRequest,
    ReviewService,
    ReviewTopic,
    ValidationError,
    chart_data,
    evidence_data,
    rank_heroes,
)
from dota2forge_core.feature_requests import parse_feature
from dota2forge_core.feature_tools import guide_data, meta_data, parse_tool
from dota2forge_core.infrastructure._feature_cache import ObservationCache
from dota2forge_core.infrastructure.hero_catalog import load_hero_catalog
from dota2forge_core.infrastructure.stratz import StratzProvider

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
META = DataMetadata(DataSource.STRATZ, NOW)


def snapshot(request=None):
    request = request or MetaRequest(position=3)
    start, end = NOW.replace(hour=0) - timedelta(days=7), NOW.replace(hour=0)
    buckets = (
        HeroWinBucket(start, 1, 3, 900, 600),
        HeroWinBucket(start + timedelta(days=1), 1, 3, 100, 90),
        HeroWinBucket(start, 2, 3, 1000, 700),
        HeroWinBucket(start, 3, 3, 20, 20),
    )
    return HeroMetaSnapshot(request, META, GamePatch(11, "synthetic.1", start), start, end, buckets)


def raw_match():
    player = {
        "playerSlot": 0,
        "steamAccountId": 321,
        "steamAccount": {"id": 321, "name": "Synthetic Private Label"},
        "isRadiant": True,
        "heroId": 2,
        "position": "POSITION_3",
        "lane": None,
        "kills": 3,
        "deaths": 0,
        "assists": 5,
        "goldPerMinute": 500,
        "experiencePerMinute": None,
        "imp": 0,
        **{f"item{i}Id": 4 if i == 0 else 0 for i in range(6)},
        "abilities": [
            {
                "abilityId": 5007,
                "level": 0,
                "time": -60,
                "isTalent": False,
                "ability": {"id": 5007, "name": "合成技能"},
            }
        ],
        "stats": {"itemPurchases": [{"time": -120, "itemId": 4}, {"time": 100, "itemId": 4}]},
    }
    return {
        "data": {
            "match": {
                "id": 22,
                "startDateTime": int((NOW - timedelta(days=1)).timestamp()),
                "durationSeconds": 1800,
                "didRadiantWin": False,
                "gameMode": "ALL_PICK_RANKED",
                "gameVersionId": 11,
                "isStats": True,
                "parsedDateTime": None,
                "players": [player],
            }
        }
    }


def mock_reply(request, *, mismatch=False):
    query = json.loads(request.content)["query"]
    if "a0:ability" in query:
        return {
            "data": {
                "constants": {
                    alias: {"id": int(identifier), "language": {"displayName": "合成技能"}}
                    for alias, identifier in re.findall(r"(a\d+):ability\(id:(\d+),", query)
                }
            }
        }
    if "gameVersions" in query:
        return {
            "data": {
                "constants": {
                    "gameVersions": [
                        {
                            "id": 11,
                            "name": "synthetic.1",
                            "asOfDateTime": int((NOW - timedelta(days=5)).timestamp()),
                        }
                    ]
                }
            }
        }
    if "winDay" in query:
        return {
            "data": {
                "heroStats": {
                    f"p{p}": [
                        {
                            "day": int((NOW.replace(hour=0) - timedelta(days=1)).timestamp()),
                            "heroId": 2,
                            "matchCount": 2000,
                            "winCount": 1200,
                        }
                    ]
                    for p in range(1, 6)
                    if f"p{p}:winDay" in query
                }
            }
        }
    if "itemFullPurchase" in query:
        shared = {
            "heroId": 2,
            "position": "POSITION_1" if mismatch else "POSITION_3",
            "week": 2000,
            "matchCount": 20,
            "winCount": 11,
        }
        return {
            "data": {
                "heroStats": {
                    "items": [{**shared, "itemId": 4, "time": 0, "instance": 0}],
                    "skills": [{**shared, "abilityId": 5007, "level": 0}],
                    "talents": [{**shared, "abilityId": 9999}],
                }
            }
        }
    if "guide(" in query:
        return {
            "data": {
                "heroStats": {
                    "guide": [
                        {
                            "heroId": 2,
                            "guides": [{"heroId": 2, "matchId": 22, "steamAccountId": 321}],
                        }
                    ]
                }
            }
        }
    return raw_match()


def test_ranking_uses_weighted_counts_lower_bound_and_minimum_sample():
    ranked = rank_heroes(snapshot())
    assert [r.hero_id for r in ranked.entries] == [2, 1]
    assert ranked.entries[1].win_rate == 0.69  # Not the mean 0.7833 of daily rates.
    assert 0 < ranked.entries[0].reliability < 0.70
    assert ranked.observing == 1
    data = meta_data(ranked)
    assert data["minimum_matches"] == 1000 and data["source"] == "stratz"
    base = snapshot(MetaRequest(sort=MetaSort.WIN_RATE))
    rows = tuple(replace(r, position=p) for p in range(1, 6) for r in base.buckets)
    assert len(rank_heroes(replace(base, buckets=rows)).entries) == 10


@pytest.mark.parametrize(
    "change",
    [{"days": 8}, {"position": True}, {"position": 0}, {"rank": "ALL"}, {"minimum_matches": 999}],
)
def test_meta_filters_reject_guessed_or_small_samples(change):
    with pytest.raises(ValidationError):
        MetaRequest(**change)


def test_duplicate_buckets_cannot_double_count_and_missing_is_not_zero():
    source = snapshot()
    with pytest.raises(ValidationError):
        replace(source, buckets=source.buckets + source.buckets[:1])
    with pytest.raises(ValidationError):
        replace(source.buckets[0], wins=901)
    empty = rank_heroes(replace(source, buckets=()))
    assert empty.entries == ()


@pytest.mark.parametrize(
    "keyword,text",
    [
        ("do强势", "3号位 段位=传奇 14天 胜率"),
        ("do主宰攻略", "1号位 详细"),
        ("do攻略样例", "22 斧王"),
        ("do复盘", "第2场 斧王 报告"),
        ("do复盘", "最近"),
        ("do复盘", "经济"),
    ],
)
def test_command_features_have_shared_strict_arguments(keyword, text):
    request = parse_feature(keyword, text)
    assert request.keyword in {"do强势", "do攻略", "do攻略样例", "do复盘"}
    if request.keyword == "do强势":
        assert request.meta.rank == RankBracket.LEGEND and request.meta.days == 14


@pytest.mark.parametrize(
    "keyword,text",
    [
        ("do强势", "3号位 3号位"),
        ("do强势", "30天"),
        ("do强势", "段位=xyz"),
        ("do攻略", ""),
        ("do攻略", "斧王 0号位"),
        ("do攻略样例", "01 斧王"),
        ("do复盘", "https://host/path"),
        ("do复盘", "22 详细"),
    ],
)
def test_command_features_reject_extra_filters_and_urls(keyword, text):
    with pytest.raises(ValueError):
        request = parse_feature(keyword, text)
        if request.hero_name:
            load_hero_catalog().resolve(request.hero_name)


@pytest.mark.parametrize(
    "name,args",
    [
        ("get_dota2_meta", {"position": True}),
        ("get_dota2_meta", {"days": 14.0}),
        ("get_dota2_meta", {"url": "https://x"}),
        ("get_dota2_hero_guide", {}),
        ("get_dota2_review_context", {"user_id": "other"}),
        ("render_dota2_review_data", {"kind": "anything"}),
        ("render_dota2_review_data", {"kind": "items", "start_seconds": 1, "end_seconds": 1}),
        ("get_dota2_review_context", {"match_id": True}),
    ],
)
def test_tools_cannot_choose_identity_target_sql_path_or_arbitrary_chart(name, args):
    with pytest.raises(ValueError):
        parse_tool(name, args)


def test_live_schema_shapes_mapped_offline_and_cached(run_async):
    seen = []

    async def check():
        def handler(request):
            seen.append(json.loads(request.content))
            return httpx.Response(200, json=mock_reply(request))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            clock = type("Clock", (), {"now": lambda _: NOW})()
            provider = StratzProvider(client, token="synthetic", clock=clock)
            service = HeroFeatureService(provider, provider, load_hero_catalog())
            meta = await service.get_meta(MetaRequest(position=3, rank=RankBracket.LEGEND, days=14))
            assert meta.snapshot.patch.name == "synthetic.1"
            assert any("缺日" in note for note in meta.snapshot.notes)
            assert len(meta.entries) == 1
            guide = await service.get_guide("斧王", 3)
            assert guide.items[0].minute == 0 and guide.abilities[0].level == 0
            assert guide.samples[0].upgrades[0].source_level == 0
            assert [p.item_id for p in guide.samples[0].purchases] == [4, 4]
            assert guide.samples[0].purchases[0].time_seconds == -120
            assert guide is await service.get_guide("斧王", 3)
            payload = json.dumps(guide_data(guide), ensure_ascii=False)
            assert "steamAccount" not in payload and "Synthetic Private Label" not in payload
            assert "NOT hero level" in payload
            sample = await service.get_sample("22", "斧王")
            assert sample.player.position == "POSITION_3"
            await provider.close()
        assert client.is_closed

    run_async(check())
    assert any("bracketIds:[LEGEND]" in v["query"] for v in seen)


def test_wrong_position_statistics_are_disabled_but_sample_remains(run_async):
    async def check():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json=mock_reply(r, mismatch=True))
            )
        ) as client:
            provider = StratzProvider(
                client, token="synthetic", clock=type("Clock", (), {"now": lambda _: NOW})()
            )
            guide = await provider.get_hero_guide(load_hero_catalog().resolve("斧王"), 3)
            assert guide.items is None and guide.abilities is None and guide.talents is None
            assert ("statistics", "scope_mismatch") in guide.module_errors
            assert guide.samples[0].player.position == "POSITION_3"
            await provider.close()

    run_async(check())


@pytest.mark.parametrize("failure", [None, "missing", "identity", "length", "resolver"])
def test_talent_labels_use_explicit_versions_and_fail_without_discarding_statistics(
    run_async, failure
):
    seen = []

    def handler(request):
        body = json.loads(request.content)
        query = body["query"]
        payload = mock_reply(request)
        if "gameVersions" in query:
            payload["data"]["constants"]["gameVersions"].append(
                {
                    "id": 12,
                    "name": "synthetic.old",
                    "asOfDateTime": int((NOW - timedelta(days=30)).timestamp()),
                }
            )
        if "players(steamAccountId" in query:
            payload["data"]["match"]["gameVersionId"] = 12
        if "a0:ability" in query:
            seen.append(body["variables"]["version"])
            for row in payload["data"]["constants"].values():
                if row["id"] == 9999:
                    row["name"] = "special_bonus_attributes"
                    row["language"]["displayName"] = None
                    if failure == "missing":
                        row["name"] = "untranslated_synthetic"
                    elif failure == "identity":
                        row["id"] = 9998
                    elif failure == "length":
                        row["language"]["displayName"] = "天" * 161
                    elif failure == "resolver":
                        payload["errors"] = [{"message": "synthetic failure"}]
                else:
                    row["language"]["displayName"] = "本场旧版技能"
        return httpx.Response(200, json=payload)

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = StratzProvider(
                client, token="synthetic", clock=type("Clock", (), {"now": lambda _: NOW})()
            )
            try:
                guide = await provider.get_hero_guide(load_hero_catalog().resolve("斧王"), 3)
                assert guide.items and guide.talents and guide.abilities and guide.samples
                assert not guide.module_errors
                assert guide.metadata.patch is None  # Names don't prove a statistics patch.
                assert guide.samples[0].upgrades[0].name == "本场旧版技能"
                assert guide.samples[0].patch.version_id == 12
                assert guide.talents[0].name == ("属性加点" if failure is None else None)
                serialized = guide_data(guide)
                assert serialized["talents"][0]["name"] == guide.talents[0].name
                assert any("天赋中文名称" in note for note in guide.notes)
                if failure in (None, "missing"):
                    assert any("synthetic.1 常量" in note for note in guide.notes)
                else:
                    assert any("获取失败" in note for note in guide.notes)
            finally:
                await provider.close()
        assert seen == [12, 11]

    run_async(check())


@pytest.mark.parametrize("broken", [False, True])
def test_unidentified_skill_keeps_samples_and_statistics_modules_fail_independently(
    broken, run_async
):
    seen = []

    def handler(request):
        query = json.loads(request.content)["query"]
        seen.append(query)
        payload = mock_reply(request)
        if "itemFullPurchase" in query:
            skills = payload["data"]["heroStats"]["skills"]
            extra = {**skills[0], "abilityId": 0, "level": 1}
            if broken:
                extra["winCount"] = extra["matchCount"] + 1
            skills.append(extra)
        if "players(steamAccountId" in query:
            player = payload["data"]["match"]["players"][0]
            player["abilities"].append({"abilityId": 0, "level": 1, "time": 600, "isTalent": False})
        return httpx.Response(200, json=payload)

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = StratzProvider(
                client, token="synthetic", clock=type("Clock", (), {"now": lambda _: NOW})()
            )
            guide = await provider.get_hero_guide(load_hero_catalog().resolve("斧王"), 3)
            assert guide.items and guide.talents and guide.samples
            assert guide.samples[0].upgrades[-1].ability_id == 0
            assert guide.samples[0].upgrades[-1].name is None
            if broken:
                assert guide.abilities is None
                assert guide.module_errors == (("abilities", "invalid_response"),)
            else:
                assert guide.abilities[-1].ability_id == 0
                assert not guide.module_errors
            await provider.close()
        assert not any("ability(id:0," in query for query in seen)

    run_async(check())


@pytest.mark.parametrize("mutation", ["errors", "duplicate", "wrong_hero", "wrong_ability", "wins"])
def test_invalid_provider_evidence_is_not_silently_joined_or_ranked(run_async, mutation):
    async def check():
        def handler(request):
            payload = copy.deepcopy(mock_reply(request))
            query = json.loads(request.content)["query"]
            if mutation == "errors":
                payload["errors"] = [{"message": "Synthetic upstream resolver failure"}]
            elif "winDay" in query:
                row = payload["data"]["heroStats"]["p3"][0]
                if mutation == "duplicate":
                    payload["data"]["heroStats"]["p3"].append(row)
                elif mutation == "wins":
                    row["winCount"] = 3000
            elif "match(id:" in query:
                player = payload["data"]["match"]["players"][0]
                if mutation == "wrong_hero":
                    player["heroId"] = 1
                elif mutation == "wrong_ability":
                    player["abilities"][0]["ability"]["id"] = 77
            return httpx.Response(200, json=payload)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = StratzProvider(
                client, token="synthetic", clock=type("Clock", (), {"now": lambda _: NOW})()
            )
            with pytest.raises(ProviderError):
                if mutation in {"wrong_hero", "wrong_ability"}:
                    await provider.get_guide_sample(
                        MatchId(22), load_hero_catalog().resolve("斧王")
                    )
                else:
                    await provider.get_hero_meta(MetaRequest(position=3))
            await provider.close()

    run_async(check())


def review_source():
    player = MatchParticipant(
        player_slot=0,
        account_id=AccountId(321),
        is_anonymous=False,
        display_name="Synthetic Private Label",
        hero_id=2,
        is_radiant=False,
        position="POSITION_3",
        kills=0,
        deaths=0,
        assists=0,
        last_hits=0,
    )
    detail = MatchDetail(
        MatchId(22), META, duration_seconds=1800, players=(player,), game_version_id=11
    )
    analysis = MatchAnalysis(
        MatchId(22),
        META,
        (
            ParticipantAnalysis(
                AccountId(321),
                0,
                (MetricSeries("networth", MetricSemantic.NETWORTH_LEVEL, (0, 100, 220)),),
                (PurchaseEvent(-120, 4), PurchaseEvent(0, 4)),
            ),
        ),
        (MetricSeries("team", MetricSemantic.RADIANT_NETWORTH_LEAD, (-200, 0, 400), -60),),
    )

    class Source:
        source = DataSource.STRATZ

        async def get_match_detail(self, _):
            return detail

        async def get_match_analysis(self, _):
            return analysis

    return Source(), detail, analysis


def test_review_preserves_source_units_offsets_zeros_and_privacy(run_async):
    source, _, _ = review_source()
    evidence = run_async(ReviewService(source, source, load_hero_catalog()).get_context(22, "斧王"))
    payload = evidence_data(evidence, ReviewTopic.LANING)
    assert payload["players"][0]["last_hits_final"] == 0
    assert payload["team_series"][0]["points"][0] == [-60, -200]
    assert payload["economic_series"][0]["semantic"] == "networth_level"
    text = json.dumps(payload)
    assert "Synthetic Private Label" not in text and "321" not in text
    chart = chart_data(evidence, ReviewChartRequest(ReviewChartKind.ITEMS, -120, 200))
    assert len(chart["chart_purchases"]) == 2
    with pytest.raises(ValidationError):
        chart_data(evidence, ReviewChartRequest(ReviewChartKind.ECONOMY, 0, 1801))


def test_review_rejects_cross_account_join_but_keeps_base_fact_failure(run_async):
    source, _, analysis = review_source()

    async def wrong(_):
        return replace(
            analysis, participants=(replace(analysis.participants[0], account_id=AccountId(123)),)
        )

    source.get_match_analysis = wrong
    evidence = run_async(ReviewService(source, source, load_hero_catalog()).get_context(22))
    assert evidence.analysis is None and evidence.analysis_error == "invalid_response"

    async def limited(_):
        raise ProviderError(
            ProviderErrorCode.RATE_LIMITED, DataSource.STRATZ, retry_after_seconds=10
        )

    source.get_match_analysis = limited
    evidence = run_async(ReviewService(source, source, load_hero_catalog()).get_context(22))
    assert evidence.analysis is None and evidence.analysis_error == "rate_limited"


def test_cache_coalesces_waiters_cancels_last_owner_and_does_not_cache_failures(run_async):
    async def check():
        cache = ObservationCache(ttl=10, capacity=1)
        begun, gate = asyncio.Event(), asyncio.Event()
        loads = 0

        async def load():
            nonlocal loads
            loads += 1
            begun.set()
            await gate.wait()
            return 7

        a = asyncio.create_task(cache.get("same", load))
        await begun.wait()
        b = asyncio.create_task(cache.get("same", load))
        await asyncio.sleep(0)
        a.cancel()
        await asyncio.gather(a, return_exceptions=True)
        gate.set()
        assert await b == 7 and loads == 1
        assert await cache.get("same", load) == 7
        gate.clear()
        cancelled = asyncio.create_task(cache.get("new", load))
        await asyncio.sleep(0)
        cancelled.cancel()
        await asyncio.gather(cancelled, return_exceptions=True)
        await cache.close()
        assert not cache._flights and not cache._values
        with pytest.raises(ProviderError):
            await cache.get("same", load)

    run_async(check())
