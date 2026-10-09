"""Wide report content, bounded images, no empty-slot labels and complete fallback."""

import io
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from dota2forge_core import (
    DataMetadata,
    DataSource,
    MatchAnalysis,
    MatchDetail,
    MatchId,
    MatchParticipant,
    MatchReport,
    MetricSemantic,
    MetricSeries,
)
from dota2forge_renderer import MatchReportCard, PillowRenderer, RenderError
from dota2forge_renderer.engine import _Canvas
from dota2forge_renderer.reporting import match_report_text, split_report_text
from PIL import Image


def report():
    metadata = DataMetadata(DataSource.STRATZ, datetime(2026, 10, 9, tzinfo=UTC))
    players = tuple(
        MatchParticipant(
            player_slot=i,
            is_anonymous=True,
            is_radiant=i < 5,
            hero_id=(40 if i == 0 else 53 if i == 1 else 2),
            kills=2,
            deaths=1,
            assists=3,
            gold_per_minute=500,
            experience_per_minute=600,
            level=25,
            last_hits=123,
            denies=0,
            net_worth=20000,
            hero_damage=40000,
            tower_damage=1000,
            hero_healing=0,
            item_ids=(1, 0, None, 0, 63, 0),
            backpack_ids=(0, 1, None),
            neutral_item_id=0,
            imp=(66, -47, 48, -23, 0, 30, -7, 9, 59, None)[i],
            position=f"POSITION_{i % 5 + 1}",
            lane="SAFE_LANE",
        )
        for i in range(10)
    )
    detail = MatchDetail(
        MatchId(1001),
        metadata,
        metadata.fetched_at,
        2374,
        True,
        "ALL_PICK",
        190,
        True,
        metadata.fetched_at,
        players,
    )
    analysis = MatchAnalysis(
        MatchId(1001),
        metadata,
        (),
        (
            MetricSeries(
                "radiantNetworthLeads", MetricSemantic.RADIANT_NETWORTH_LEAD, (-500, 0, 13500), -60
            ),
            MetricSeries(
                "radiantExperienceLeads",
                MetricSemantic.RADIANT_EXPERIENCE_LEAD,
                (-200, 500, 26500),
                -60,
            ),
        ),
    )
    return MatchReport(MatchId(1001), metadata, None, None, detail, analysis)


def test_wide_report_preserves_all_ten_players_scores_stats_and_equipment(monkeypatch):
    captured = []
    original = _Canvas.text

    def capture(canvas, x, y, value, **kwargs):
        captured.append(value)
        return original(canvas, x, y, value, **kwargs)

    monkeypatch.setattr(_Canvas, "text", capture)
    result = report()
    texts = match_report_text(result)
    assert len(texts) == 3
    renderer = PillowRenderer()
    try:
        for page in (1, 2, 3):
            artifact = renderer.render(MatchReportCard(result, page))
            assert artifact.width == 1600 and 1800 < artifact.height <= 3200
            assert len(artifact.data) <= 2 * 1024 * 1024
            with Image.open(io.BytesIO(artifact.data)) as image:
                assert image.size == (artifact.width, artifact.height)
                assert any(low < high for low, high in image.getextrema())
        assert "空槽" not in captured and "空" not in captured
        assert captured.count("背包") == 10 and captured.count("中立") == 10
        assert any("IMP -47" in line for line in captured)
        assert any("表现突出" in line for line in captured)
        assert any("表现偏弱" in line for line in captured)
        full = "\n".join(texts)
        assert full.count("等级 25") == 10 and full.count("净资产 20000") == 10
        assert "参战 50.0%" in full and "伤害 40000" in full
        assert " /  / " in full and "空槽" not in full
        assert "背包：" in full and "中立装备：" in full
        assert all(len(text) <= 1400 for text in split_report_text(texts))
        for marker in ("IMP +66", "IMP -47", "建筑伤害 1000", "背包："):
            assert marker in "\n".join(split_report_text(texts))
    finally:
        renderer.close()


@pytest.mark.parametrize("players", [None, (), (MatchParticipant(player_slot=0, is_radiant=None),)])
def test_partial_report_does_not_invent_team_totals_or_scores(players):
    base = report()
    value = replace(base, detail=replace(base.detail, players=players))
    renderer = PillowRenderer()
    try:
        artifact = renderer.render(MatchReportCard(value))
        assert artifact.width == 1600
        text = "\n".join(match_report_text(value))
        assert "击杀 天辉 未知 : 未知" in text
        assert "没有可用" in text
    finally:
        renderer.close()


@pytest.mark.parametrize("page", [0, 4, True])
def test_report_pages_are_bounded(page):
    renderer = PillowRenderer()
    try:
        with pytest.raises(RenderError):
            renderer.render(MatchReportCard(report(), page))
    finally:
        renderer.close()
