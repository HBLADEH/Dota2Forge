"""Synthetic subscription context, report completeness and render boundaries."""

import io
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from dota2forge_core import (
    AccountId,
    DataMetadata,
    DataSource,
    MatchAnalysis,
    MatchAnalysisUnavailable,
    MatchDetail,
    MatchDetailUnavailable,
    MatchId,
    MatchParticipant,
    MatchReport,
    MatchSummary,
    MetricSemantic,
    MetricSeries,
    ParticipantAnalysis,
    PlatformIdentity,
    PurchaseEvent,
    RankChange,
    SubscriptionEvent,
    SubscriptionKey,
    SubscriptionKind,
)
from dota2forge_renderer import (
    MatchReportCard,
    PillowRenderer,
    RenderError,
    subscription_event_cards,
    subscription_event_text_pages,
)
from dota2forge_renderer.engine import _Canvas
from dota2forge_renderer.reporting import match_report_text, report_groups
from dota2forge_renderer.subscriptions import (
    FINITE_OBSERVATION_NOTICE,
    subscription_event_text,
)
from PIL import Image


def synthetic_subscription_event(*, imp=True, specific=False):
    metadata = DataMetadata(DataSource.STRATZ, datetime(2026, 10, 12, 12, tzinfo=UTC))
    players = tuple(
        MatchParticipant(
            player_slot=index if index < 5 else 128 + index - 5,
            account_id=AccountId(2000 + index),
            display_name=f"合成玩家 {index + 1}" if index % 2 else None,
            is_anonymous=False,
            is_radiant=index < 5,
            hero_id=index + 1,
            kills=index + 2,
            deaths=3,
            assists=4,
            gold_per_minute=300 + index * 20,
            experience_per_minute=400 + index * 20,
            level=20 + index,
            last_hits=100 + index,
            denies=index,
            net_worth=12000 + index * 1000,
            hero_damage=15000 + index * 1000,
            tower_damage=1000 + index * 100,
            hero_healing=0,
            item_ids=(1, 0, None, 63, 0, 0),
            backpack_ids=(0, 1, None),
            neutral_item_id=0,
            imp=(index * 10 - 45) if imp else None,
            position=f"POSITION_{index % 5 + 1}",
            lane="SAFE_LANE",
        )
        for index in range(10)
    )
    detail = MatchDetail(
        MatchId(7001),
        metadata,
        started_at=metadata.fetched_at - timedelta(minutes=45),
        duration_seconds=2100,
        did_radiant_win=False,
        game_mode="ALL_PICK_RANKED",
        game_version_id=190,
        has_stats=True,
        players=players,
    )
    analysis = MatchAnalysis(
        detail.match_id,
        metadata,
        (
            ParticipantAnalysis(
                AccountId(2000),
                0,
                (MetricSeries("networth", MetricSemantic.NETWORTH_LEVEL, (100, 200)),),
                (PurchaseEvent(30, item_id=1),),
            ),
        ),
    )
    report = MatchReport(
        detail.match_id, metadata, None if specific else AccountId(2002), None, detail, analysis
    )
    key = SubscriptionKey(
        PlatformIdentity("synthetic", "offline", "fixture-bot", "fixture-owner"),
        "group:synthetic",
        report.tracked_account_id,
        metadata.source,
        SubscriptionKind.MATCH_REPORT if specific else SubscriptionKind.NEW_MATCH,
        detail.match_id if specific else None,
    )
    return SubscriptionEvent("a" * 32, "b" * 32, key, metadata.fetched_at, report)


@pytest.mark.parametrize("specific", [False, True])
def test_subscription_pages_reuse_complete_report_and_hide_event_in_card_repr(specific):
    event = synthetic_subscription_event(specific=specific)
    cards = subscription_event_cards(event)
    assert len(cards) == 3
    assert tuple(card.page for card in cards) == (1, 2, 3)
    assert all(card.report is event.payload and card.subscription_event is event for card in cards)
    assert event.event_id not in repr(cards[0])
    assert MatchReportCard(event.payload).subscription_event is None
    text_pages = subscription_event_text_pages(event)
    assert all(0 < len(page) <= 1400 for page in text_pages)
    assert all(
        "Dota2Forge 订阅提醒" in page
        and f"事件ID {event.event_id}" in page
        and "来源 STRATZ" in page
        and "比赛对局报告：7001" in page
        and FINITE_OBSERVATION_NOTICE in page
        for page in text_pages
    )
    full = "\n".join(text_pages)
    for original_page in match_report_text(event.payload):
        for line in original_page.splitlines():
            assert line in full
    assert "Dota2Forge 订阅提醒" in full and f"事件ID {event.event_id}" in full
    assert FINITE_OBSERVATION_NOTICE in full
    assert "分析：经济序列 1 项，购买事件 1 条。" in full
    for account in range(2000, 2010):
        assert f"账号 {account}" in full
    assert full.count("背包：") == 10 and full.count("中立装备：") == 10
    if specific:
        assert "比赛 7001" in full and "订阅玩家：" not in full
    else:
        assert "订阅玩家：2002" in full and "[我方]" in full


def test_subscription_grouping_keeps_unknown_side_and_more_than_five_players():
    event = synthetic_subscription_event()
    players = tuple(replace(player, is_radiant=None) for player in event.payload.detail.players)
    report = replace(event.payload, detail=replace(event.payload.detail, players=players))
    event = replace(event, payload=report)
    assert tuple(len(team) for _, team in report_groups(report)) == (5, 5)
    assert len(subscription_event_cards(event)) == 3
    assert "阵营未知详细数据" in "\n".join(subscription_event_text_pages(event))


@pytest.mark.parametrize("imp", [True, False])
def test_subscription_card_renders_all_pages_with_context_sources_and_complete_event_id(
    monkeypatch, imp
):
    event = synthetic_subscription_event(imp=imp)
    captured = []
    original = _Canvas.text

    def capture(canvas, x, y, value, **kwargs):
        captured.append(value)
        return original(canvas, x, y, value, **kwargs)

    monkeypatch.setattr(_Canvas, "text", capture)
    renderer = PillowRenderer()
    try:
        for card in subscription_event_cards(event):
            captured.clear()
            image = renderer.render(card)
            assert image.width == 1600 and image.height <= 3200
            assert len(image.data) < 2 * 1024 * 1024
            with Image.open(io.BytesIO(image.data)) as decoded:
                assert decoded.size == (image.width, image.height)
            assert "订阅比赛报告" in captured
            assert any("订阅玩家账号 2002" in line for line in captured)
            assert f"事件ID {event.event_id}" in captured
            assert FINITE_OBSERVATION_NOTICE in captured
            assert "分析：经济序列 1 项，购买事件 1 条。" in captured
            assert any("来源 STRATZ" in line for line in captured)
            assert any("抓取 2026-10-12 20:00:00 UTC+8" in line for line in captured)
            if not imp and card.page == 1:
                assert any("表现候选（非官方 MVP）：账号 2009" in line for line in captured)
                assert any("没有可用 IMP" in line for line in captured)
    finally:
        renderer.close()


def test_missing_imp_keeps_non_official_candidate_in_complete_text_fallback():
    event = synthetic_subscription_event(imp=False)
    text = "\n".join(subscription_event_text_pages(event))
    assert "表现候选（非官方 MVP）：账号 2009 · 槽位 132" in text
    assert "没有可用 IMP" in text and "不是官方评分" in text
    assert "IMP +0" not in text


def test_missing_subscription_advantage_plots_compact_without_changing_query_spacing(monkeypatch):
    event = synthetic_subscription_event(imp=False)
    positions = {}
    original = _Canvas.text

    def capture(canvas, x, y, value, **kwargs):
        positions[value] = y
        return original(canvas, x, y, value, **kwargs)

    monkeypatch.setattr(_Canvas, "text", capture)
    renderer = PillowRenderer()
    try:
        renderer.render(subscription_event_cards(event)[0])
        assert "来源未提供足够的优势序列" in positions
        assert positions["表现候选 · 非官方 MVP"] - positions["团队净资产优势"] < 200
        assert "IMP 可用 0 人 · 来源未提供评分，不进行表现排序。" in positions
        positions.clear()
        renderer.render(MatchReportCard(event.payload))
        assert positions["表现候选 · 非官方 MVP"] - positions["团队净资产优势"] > 400
    finally:
        renderer.close()


def test_card_rejects_context_from_a_different_observation():
    event = synthetic_subscription_event()
    other = replace(
        event,
        payload=replace(
            event.payload,
            analysis=MatchAnalysisUnavailable(event.payload.match_id, event.payload.metadata),
        ),
    )
    renderer = PillowRenderer()
    try:
        with pytest.raises(RenderError):
            renderer.render(MatchReportCard(event.payload, subscription_event=other))
    finally:
        renderer.close()


def test_unavailable_detail_has_no_cards_and_preserves_unknown_text():
    event = synthetic_subscription_event()
    report = replace(
        event.payload,
        detail=MatchDetailUnavailable(event.payload.match_id, event.payload.metadata),
    )
    event = replace(event, payload=report)
    assert subscription_event_cards(event) == ()
    text = "\n".join(subscription_event_text_pages(event))
    assert "数据源未返回，原因和隐私状态未知" in text
    assert event.event_id in text and "STRATZ" in text
    assert "参赛者：" not in text


@pytest.mark.parametrize("kind", [SubscriptionKind.RANK_CHANGE, SubscriptionKind.NEW_MATCH])
def test_legacy_non_report_payloads_remain_bounded_text_only(kind):
    original = synthetic_subscription_event()
    metadata = original.payload.metadata
    payload = (
        RankChange(40, 41, metadata)
        if kind == SubscriptionKind.RANK_CHANGE
        else MatchSummary(7001, AccountId(2002), metadata.fetched_at, metadata, is_win=True)
    )
    event = replace(original, key=replace(original.key, kind=kind), payload=payload)
    assert subscription_event_cards(event) == ()
    pages = subscription_event_text_pages(event)
    assert pages == (subscription_event_text(event),)
    assert all(len(page) <= 1400 for page in pages)
    assert event.event_id in pages[0] and FINITE_OBSERVATION_NOTICE in pages[0]


def test_legacy_report_source_deduplicates_only_identical_source_and_fetch():
    event = synthetic_subscription_event()
    assert subscription_event_text(event).count("来源：STRATZ") == 1
    different_fetch = replace(
        event.payload.metadata, fetched_at=event.detected_at + timedelta(seconds=1)
    )
    event = replace(event, payload=replace(event.payload, metadata=different_fetch))
    assert subscription_event_text(event).count("来源：STRATZ") == 2


def test_complete_fallback_distinguishes_report_detail_and_analysis_fetch_times():
    event = synthetic_subscription_event()
    original = event.payload
    report = replace(
        original,
        metadata=replace(original.metadata, fetched_at=event.detected_at + timedelta(seconds=2)),
        analysis=replace(
            original.analysis,
            metadata=replace(
                original.metadata, fetched_at=event.detected_at + timedelta(seconds=1)
            ),
        ),
    )
    pages = subscription_event_text_pages(replace(event, payload=report))
    assert all(
        "来源 STRATZ | 抓取 2026-10-12 20:00:02 UTC+8" in page
        and "详情来源 STRATZ | 抓取 2026-10-12 20:00:00 UTC+8" in page
        and "分析抓取 2026-10-12 20:00:01 UTC+8" in page
        for page in pages
    )
    assert all(len(page) <= 1400 for page in pages)


def test_unavailable_analysis_does_not_become_empty_observation():
    event = synthetic_subscription_event()
    report = replace(
        event.payload,
        analysis=MatchAnalysisUnavailable(event.payload.match_id, event.payload.metadata),
    )
    event = replace(event, payload=report)
    text = "\n".join(subscription_event_text_pages(event))
    assert "分析数据未提供；经济与购买事件未知。" in text
    assert "经济序列 0 项" not in text


@pytest.mark.parametrize("participants", [None, ()])
def test_missing_participant_analysis_is_distinct_from_known_empty_observation(participants):
    event = synthetic_subscription_event()
    report = replace(
        event.payload, analysis=replace(event.payload.analysis, participants=participants)
    )
    event = replace(event, payload=report)
    full = "\n".join(subscription_event_text_pages(event))
    legacy = subscription_event_text(event)
    if participants is None:
        marker = "分析：参赛者分析未知；经济序列和购买事件未提供。"
        assert "经济序列 0 项" not in full and "经济序列 0 项" not in legacy
    else:
        marker = "分析：经济序列 0 项，购买事件 0 条。"
    assert marker in full and marker in legacy


def test_partial_purchase_observation_is_not_presented_as_complete_count():
    event = synthetic_subscription_event()
    known = event.payload.analysis.participants[0]
    missing = replace(known, account_id=AccountId(2001), player_slot=1, metrics=(), purchases=None)
    report = replace(
        event.payload,
        analysis=replace(event.payload.analysis, participants=(known, missing)),
    )
    event = replace(event, payload=report)
    marker = "购买事件观察到 1 条（部分玩家购买事件未提供）"
    assert marker in "\n".join(subscription_event_text_pages(event))
    assert marker in subscription_event_text(event)
