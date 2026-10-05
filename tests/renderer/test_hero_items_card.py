"""Hero item counts and provenance remain readable within the image limit."""

from datetime import UTC, datetime

from dota2forge_core import (
    DataMetadata,
    DataSource,
    Hero,
    HeroItemStatistics,
    ItemPurchaseCount,
    ItemStage,
    StageItemCounts,
)
from dota2forge_renderer import HeroItemsCard, PillowRenderer
from dota2forge_renderer.engine import _Canvas
from dota2forge_renderer.hero_items import hero_items_text


def test_full_card_preserves_sorted_top_five_zero_missing_and_complete_notice(monkeypatch):
    counts = tuple(
        ItemPurchaseCount(item_id, count)
        for item_id, count in ((999999, 0), (1, 10), (44, 8), (45, 5), (48, 3), (50, 1))
    )
    result = HeroItemStatistics(
        Hero(2, "斧王", "Axe"),
        DataMetadata(DataSource.OPENDOTA, datetime(2026, 10, 5, tzinfo=UTC)),
        tuple(StageItemCounts(stage, counts) for stage in ItemStage),
    )
    captured = []
    original = _Canvas.text

    def capture(canvas, x, y, text, **kwargs):
        # Check real bounds and complete labels; this rejects hidden overflow.
        kwargs["truncate"] = False
        captured.append(text)
        return original(canvas, x, y, text, **kwargs)

    monkeypatch.setattr(_Canvas, "text", capture)
    renderer = PillowRenderer()
    try:
        card = renderer.render(HeroItemsCard(result))
        assert card.width == 780 and card.height == 1674
        assert "装备 ID 999999" not in captured
        assert captured.count("闪烁匕首") == 4
        assert "职业比赛购买统计；热门不等于最优出装" in captured
        assert "或购买顺序。" in captured
        assert "位置 / 补丁 / 统计窗口 / 总样本数：未知" in captured
        assert any("来源 OPENDOTA" in text for text in captured)
        assert any("观测时间 未知" in text for text in captured)
    finally:
        renderer.close()
    # Zero inside the selected set remains an observation, distinct from empty/unknown.
    result = HeroItemStatistics(
        result.hero,
        result.metadata,
        (
            StageItemCounts(ItemStage.START, (ItemPurchaseCount(999999, 0),)),
            StageItemCounts(ItemStage.EARLY, ()),
            StageItemCounts(ItemStage.MID, None),
            StageItemCounts(ItemStage.LATE, counts),
        ),
    )
    text = hero_items_text(result)
    assert "装备 ID 999999：0 次" in text
    assert "本次无物品统计" in text and "统计未知（来源未返回）" in text
