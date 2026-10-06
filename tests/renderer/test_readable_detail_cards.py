"""Verify full participant coverage and item artwork with synthetic local resources."""

import io
from dataclasses import replace

from astrbot_plugin_dota2forge.application import detail_text
from dota2forge_core import Hero, HeroItemStatistics, ItemPurchaseCount, ItemStage, StageItemCounts
from dota2forge_renderer import HeroItemsCard, MatchDetailCard, PillowRenderer
from dota2forge_renderer.engine import _Canvas, detail_groups
from Dota2UID.presentation import match_detail_text
from PIL import Image
from test_illustrations import pack as pack
from test_renderer_cards import META, detail


def test_hero_items_render_correct_images_and_unknown_slots(pack):
    path, _ = pack
    statistics = HeroItemStatistics(
        Hero(2, "斧王", "Axe"),
        META,
        tuple(
            StageItemCounts(stage, (ItemPurchaseCount(1, 10), ItemPurchaseCount(999999, 0)))
            for stage in ItemStage
        ),
    )
    renderer = PillowRenderer(illustration_path=path)
    try:
        artifact = renderer.render(HeroItemsCard(statistics))
        with Image.open(io.BytesIO(artifact.data)) as image:
            assert image.getpixel((100, 240)) == (244, 0, 153)
            for stage in range(4):
                assert image.getpixel((100, 390 + stage * 252)) == (32, 255, 74)
                assert image.getpixel((190, 370 + stage * 252)) != (32, 255, 74)
    finally:
        renderer.close()


def test_all_ten_players_stats_equipment_and_text_fallback_are_preserved(monkeypatch):
    match = detail()
    match = replace(
        match,
        players=tuple(
            replace(
                player,
                level=25,
                last_hits=0,
                denies=None,
                net_worth=32100,
                hero_damage=65432,
                tower_damage=4321,
                hero_healing=0,
                item_ids=(1, 63, 36, 0, None, 999999),
            )
            for player in match.players
        ),
    )
    groups = detail_groups(MatchDetailCard(match))
    assert [len(team) for _, team in groups] == [3, 2, 3, 2]
    assert tuple(player for _, team in groups for player in team) == match.players
    captured = []
    original = _Canvas.text

    def capture(canvas, x, y, value, **kwargs):
        captured.append(value)
        return original(canvas, x, y, value, **kwargs)

    monkeypatch.setattr(_Canvas, "text", capture)
    renderer = PillowRenderer()
    try:
        for page in range(1, 5):
            artifact = renderer.render(MatchDetailCard(match, page))
            assert artifact.height <= 1800 and len(artifact.data) <= 2 * 1024 * 1024
        for expected in (
            "等级 25",
            "补刀 0",
            "反补 未知",
            "净资产 32100",
            "英雄伤害 65432",
            "建筑伤害 4321",
            "治疗量 0",
            "999999",
        ):
            assert captured.count(expected) == 10
        for render_text in (detail_text, match_detail_text):
            pages = render_text(match)
            assert len(pages) == 4
            text = "\n".join(pages)
            assert text.count("英雄伤害 65432") == 10
            assert text.count("装备 ID 999999（999999）") == 10
            assert text.count("闪烁匕首（1）") == 10
            assert "补刀 0 / 反补 未知" in text
    finally:
        renderer.close()
