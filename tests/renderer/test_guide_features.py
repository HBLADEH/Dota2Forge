"""Guide icons and complete talent labels with synthetic local artwork only."""

import io
from dataclasses import replace

import pytest
from dota2forge_core import (
    AbilityChoice,
    BuildItemBucket,
    HeroGuide,
    PurchaseEvent,
    ReviewChartKind,
    ReviewChartRequest,
    ReviewEvidence,
    SkillUpgrade,
)
from dota2forge_renderer import PillowRenderer, RenderError, ReviewDataCard
from dota2forge_renderer.features import feature_cards, feature_text
from PIL import Image
from test_feature_consumers import sample
from test_hero_features import META, review_source
from test_illustrations import pack as pack


def test_equipment_statistics_purchase_and_review_cards_draw_local_icons(pack):
    path, _ = pack
    observed = replace(sample(), purchases=(PurchaseEvent(-90, 1), PurchaseEvent(100, 999999)))
    guide = HeroGuide(
        observed.hero, 3, META, None, (BuildItemBucket(1, 1, 0, 1000, 500),), None, None, ()
    )
    _, detail, analysis = review_source()
    player = replace(analysis.participants[0], purchases=observed.purchases)
    analysis = replace(analysis, participants=(player,))
    cards = (
        feature_cards(guide)[0],
        feature_cards(observed)[1],
        ReviewDataCard(
            ReviewEvidence(detail, analysis, 0),
            ReviewChartRequest(ReviewChartKind.ITEMS, -120, 1800),
        ),
    )
    engine = PillowRenderer(illustration_path=path)
    empty = PillowRenderer()
    try:
        for card in cards:
            artifact = engine.render(card)
            with Image.open(io.BytesIO(artifact.data)) as image:
                assert (
                    sum(
                        count
                        for count, color in image.getcolors(image.width * image.height)
                        if color == (32, 255, 74)
                    )
                    > 800
                )
            assert empty.render(card).width == 780  # Missing art preserves readable data.
        text = feature_text(cards[1])
        assert "-01:30" in text and "装备 ID 999999" in text
    finally:
        engine.close()
        empty.close()


def test_talent_text_is_complete_and_long_skill_labels_fall_back_instead_of_cropping():
    name = "剑刃风暴期间+45 移动速度"
    observed = replace(sample(), upgrades=(SkillUpgrade(1234, 0, 600, True, name),))
    guide = HeroGuide(
        observed.hero, 3, META, None, None, None, (AbilityChoice(1234, None, 1000, 500, name),), ()
    )
    engine = PillowRenderer()
    try:
        talent_card = feature_cards(guide, detailed=True)[-1]
        assert name in feature_text(talent_card) and "技能 ID 1234" not in feature_text(talent_card)
        assert engine.render(talent_card).height < 1000
        assert engine.render(feature_cards(observed)[0]).height <= 1800
        long_name = "合成完整天赋说明" * 15
        long_sample = replace(observed, upgrades=(SkillUpgrade(1234, 0, 600, True, long_name),))
        card = feature_cards(long_sample)[0]
        with pytest.raises(RenderError):
            engine.render(card)
        assert long_name in feature_text(card)
    finally:
        engine.close()
