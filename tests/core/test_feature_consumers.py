"""Shared renderer, independent adapters and five-round native conversation checks."""

import importlib
import json
from dataclasses import replace
from datetime import timedelta

import httpx
import pytest
from dota2forge_core import (
    AbilityChoice,
    GamePatch,
    GuideSample,
    HeroGuide,
    MatchId,
    ReviewChartKind,
    ReviewChartRequest,
    ReviewEvidence,
    ReviewService,
    SkillUpgrade,
    ValidationError,
    rank_heroes,
)
from dota2forge_core.infrastructure._stratz_detail import match_detail
from dota2forge_core.infrastructure.hero_catalog import load_hero_catalog
from dota2forge_renderer import PillowRenderer, ReviewDataCard
from dota2forge_renderer.features import feature_cards, feature_text
from test_hero_features import META, NOW, mock_reply, raw_match, review_source, snapshot


def sample():
    detail = match_detail(raw_match(), MatchId(22), META)
    source, _, analysis = review_source()
    return GuideSample(
        load_hero_catalog().resolve("斧王"),
        MatchId(22),
        META,
        detail.players[0],
        GamePatch(11, "synthetic.1", NOW - timedelta(days=7)),
        NOW,
        1800,
        False,
        tuple(
            SkillUpgrade(5007 + i % 4, i % 4, i * 60 - 100, i % 5 == 0, f"合成技能{i % 4}")
            for i in range(30)
        ),
        analysis.participants[0].purchases,
    )


def test_feature_cards_render_all_pages_and_bounds_with_readable_source_status():
    observation = sample()
    guide = HeroGuide(
        observation.hero,
        3,
        META,
        None,
        None,
        None,
        None,
        (observation,),
        ("位置统计暂不可用，实际位置样例单列。",),
        (("statistics", "scope_mismatch"),),
    )
    source, detail, analysis = review_source()
    cards = (
        *feature_cards(rank_heroes(snapshot())),
        *feature_cards(guide, detailed=True),
        *feature_cards(observation),
        *(
            ReviewDataCard(
                ReviewEvidence(detail, analysis, 0), ReviewChartRequest(kind, -120, 1800)
            )
            for kind in ReviewChartKind
        ),
    )
    engine = PillowRenderer()
    try:
        for card in cards:
            artifact = engine.render(card)
            assert artifact.width == 780 and artifact.height <= 1800
            assert len(artifact.data) < 2 * 1024 * 1024
            assert engine.last_layout and all(
                box[2] <= 780 and box[3] <= artifact.height for box in engine.last_layout
            )
        text = feature_text(feature_cards(observation)[0])
        assert "不是英雄等级" in text and "展示 24/30" in text
        assert "源阶数 0" in text
        assert "来源统计位置与所选位置不一致" in feature_text(feature_cards(guide)[0])
        assert "实际位置 3号位" in text
    finally:
        engine.close()


def test_missing_guide_modules_do_not_send_blank_pages_or_keep_fixed_page_numbers():
    observed = sample()
    missing = HeroGuide(
        observed.hero,
        3,
        META,
        None,
        None,
        None,
        None,
        (),
        module_errors=(("samples", "invalid_response"),),
    )
    cards = feature_cards(missing, detailed=True)
    assert [card.page for card in cards] == [1]
    assert "do攻略样例" in feature_text(cards[0])
    engine = PillowRenderer()
    try:
        assert engine.render(cards[0]).height < 1000
        partial = HeroGuide(
            observed.hero, 3, META, None, None, None, (AbilityChoice(5007, None, 1000, 500),), ()
        )
        pages = feature_cards(partial, detailed=True)
        assert [card.page for card in pages] == [1, 4]
        assert "攻略 2/2" in feature_text(pages[1])
        assert engine.render(pages[1]).height < 1000
        unidentified = replace(observed, upgrades=(SkillUpgrade(0, 1, 600, False),))
        assert "未标识技能 ID 0" in feature_text(feature_cards(unidentified)[0])
        assert engine.render(feature_cards(unidentified)[0]).width == 780
    finally:
        engine.close()


@pytest.mark.parametrize("package", ["Dota2UID", "astrbot_plugin_dota2forge"])
def test_anchor_scope_ttl_reset_binding_invalidation_and_bound(package):
    Store = importlib.import_module(package + ".review_sessions").ReviewSessionStore
    now = [0.0]
    store = Store(lambda: now[0])
    _, detail, analysis = review_source()
    evidence = ReviewEvidence(detail, analysis, 0)
    key = ("synthetic-owner", "connection/group", "native-one")
    generation = object()
    entry = store.remember(key, generation, None, 22, "斧王", evidence)
    assert store.peek(key, generation, 2) is entry
    now[0] = 590
    store.remember(key, generation, None, 22, "斧王", evidence)
    now[0] = 601
    entry = store.get(key, generation, None)
    assert entry is not None and store.evidence(entry) is None  # Read did not extend evidence TTL.
    assert store.peek(key, generation, 0) is None  # Same native ID, history reset.
    store.remember(key, generation, None, 22, None, evidence)
    assert store.peek(key, object()) is None  # Same ID, host instance replaced.
    for i in range(129):
        store.remember((f"owner-{i}", "group", "native"), generation, None, 22, None, evidence)
    assert len(store._values) == 128
    store.invalidate("owner-128")
    assert len(store._values) == 127
    store.remember(key, generation, None, 22, None, evidence)
    assert store.peek((key[0], key[1], "native-two"), generation) is None
    assert key not in store._values
    store.remember(key, generation, None, 22, None, evidence)
    now[0] += 1800
    assert store.get(key, generation, None) is None
    store.clear()
    assert not store._values
    clock_start = now[0]
    store.remember(key, generation, None, 22, None, evidence)
    for step in range(1, 12):
        now[0] = clock_start + step * 600
        store.remember(key, generation, None, 22, None, evidence)
    now[0] = clock_start + 7200
    assert store.get(key, generation, None) is None  # Activity cannot extend the absolute limit.


@pytest.mark.parametrize("package", ["Dota2UID", "astrbot_plugin_dota2forge"])
def test_native_five_rounds_retain_target_refresh_expired_evidence_and_keep_figures_optional(
    package, run_async
):
    Native = importlib.import_module(package + ".native_features").NativeFeatures
    Store = importlib.import_module(package + ".review_sessions").ReviewSessionStore
    source, detail, analysis = review_source()
    calls = []

    async def details(_):
        calls.append("detail")
        return detail

    source.get_match_detail = details
    clock = [0.0]
    store = Store(lambda: clock[0])
    native = Native(None, ReviewService(source, source, load_hero_catalog()), lambda: None, store)
    key, generation = ("user", "group", "native"), object()

    async def check():
        first, image = await native.tool(
            key,
            generation,
            None,
            "get_dota2_review_context",
            {"match_id": "22", "hero_name": "斧王"},
        )
        assert image is None and first["target_slot"] == 0
        assert native.hint(key, generation, "为什么", 2)
        assert "先调用 get_dota2_review_context" in native.hint(
            key, generation, "这把有什么问题？", 2
        )
        assert native.hint(key, generation, "怎么改进？", 2)
        assert native.hint(key, generation, "今天的天气如何", 2) is None
        for topic in ("items", "economy", "laning", "team"):
            reply, image = await native.tool(
                key, generation, None, "get_dota2_review_context", {"topic": topic}
            )
            assert reply["match_id"] == 22 and reply["target_slot"] == 0 and image is None
        assert calls == ["detail"]
        clock[0] = 661
        reply, _ = await native.tool(key, generation, None, "get_dota2_review_context", {})
        assert reply["match_id"] == 22 and calls == ["detail", "detail"]
        chart, image = await native.tool(
            key,
            generation,
            None,
            "render_dota2_review_data",
            {"kind": "items", "start_seconds": -120},
        )
        assert image is None and chart["render_error"] == "unavailable"
        assert chart["chart_purchases"][0]["time_seconds"] == -120
        entry = store.get(key, generation, None)
        active = entry.active
        clock[0] += 10
        with pytest.raises(ValidationError):
            await native.tool(
                key,
                generation,
                None,
                "render_dota2_review_data",
                {"kind": "items", "end_seconds": 1801},
            )
        assert store.get(key, generation, None).active == active
        with pytest.raises(ValidationError):
            await native.tool(
                ("other", "group", "native"), generation, None, "get_dota2_review_context", {}
            )

    run_async(check())


def test_both_command_consumers_invoke_shared_features_and_keep_old_items_distinct(run_async):
    from astrbot_plugin_dota2forge.commands import parse_command as astr_parse
    from Dota2UID.commands import parse_command as gs_parse

    for keyword, text in (
        ("do强势", "3号位 段位=传奇"),
        ("do斧王攻略", "3号位 详细"),
        ("do攻略样例", "22 斧王"),
        ("do复盘", "最近 斧王"),
    ):
        assert gs_parse(keyword, text).feature == astr_parse(keyword, text).feature
    assert gs_parse("doAM出装", "").feature is None
    assert astr_parse("doAM出装", "").feature is None


@pytest.mark.parametrize("package", ["Dota2UID", "astrbot_plugin_dota2forge"])
def test_runtimes_execute_real_feature_consumers_native_tools_and_cleanup(
    package, tmp_path, run_async
):
    sent, requests = [], []

    def handler(request):
        requests.append(json.loads(request.content)["query"])
        return httpx.Response(200, json=mock_reply(request))

    def factory():
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def send(reply):
        sent.append(reply.text)

    async def check():
        if package == "Dota2UID":
            from Dota2UID.commands import Caller
            from Dota2UID.runtime import Runtime

            config = tmp_path / "config.toml"
            config.write_text(
                'namespace="synthetic"\nstratz_token="synthetic"\ntimeout_seconds=2\n'
                'reply_mode="text"\nasset_download_mode="manual"\n[platforms]\nonebot="qq"\n',
                "utf-8",
            )
            runtime = Runtime(config, client_factory=factory)
            caller = Caller("onebot", "bot", "user", "connection", conversation_kind="direct")
        else:
            from astrbot_plugin_dota2forge.identity import Caller
            from astrbot_plugin_dota2forge.runtime import Runtime

            runtime = Runtime(
                {
                    "namespace": "synthetic",
                    "stratz_token": "synthetic",
                    "reply_mode": "text",
                    "asset_download_mode": "manual",
                },
                tmp_path / "astr",
                client_factory=factory,
            )
            caller = Caller("qq", "connection", "bot", "user", conversation_kind="FriendMessage")
        await runtime.dispatch(caller, "do强势", "3号位", send)
        assert "版本强势" in sent[0] and "STRATZ" in sent[0]
        await runtime.dispatch(caller, "do攻略", "斧王 3号位 详细", send)
        assert len(sent) == 5 and "攻略" in sent[1]
        await runtime.dispatch(caller, "do攻略样例", "22 斧王", send)
        assert len(sent) == 7 and "真实升级" in sent[5]
        native = object()
        first = await runtime.begin_review(caller, "native", native, "22 斧王")
        second, image = await runtime.ai_tool(
            caller, "native", native, "get_dota2_review_context", {"topic": "items"}
        )
        assert first["match_id"] == second["match_id"] == 22 and image is None
        with pytest.raises(ValidationError):
            await runtime.ai_tool(
                caller, "native", native, "get_dota2_review_context", {"target": "other"}
            )
        await runtime.dispatch(caller, "do解绑", "", send)
        with pytest.raises(ValidationError):
            await runtime.ai_tool(caller, "native", native, "get_dota2_review_context", {})
        await runtime.close()
        assert runtime.client_closed

    run_async(check())
