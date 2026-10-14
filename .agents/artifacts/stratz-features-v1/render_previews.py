"""Production renderer QA using explicitly labeled synthetic observations only."""

import json
import sys
from dataclasses import replace
from pathlib import Path

from dota2forge_core import (
    HeroGuide,
    HeroWinBucket,
    MetaRequest,
    ReviewChartKind,
    ReviewChartRequest,
    ReviewEvidence,
    rank_heroes,
)
from dota2forge_renderer import PillowRenderer, ReviewDataCard
from dota2forge_renderer.features import feature_cards, feature_text
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tests/core"))


class PreviewRenderer(PillowRenderer):
    def display(self, value):
        if value.startswith("来源 "):
            value = "合成测试 · 模拟" + value
        return super().display(value)


def main():
    from test_feature_consumers import sample
    from test_hero_features import META, review_source, snapshot

    base = snapshot(MetaRequest())
    buckets = tuple(
        HeroWinBucket(row.day, row.hero_id, position, row.matches, row.wins)
        for position in range(1, 6)
        for row in base.buckets
    )
    ranking = rank_heroes(replace(base, buckets=buckets))
    observed = sample()
    guide = HeroGuide(
        observed.hero,
        3,
        META,
        None,
        None,
        None,
        None,
        (observed,),
        ("合成测试，统计位置不一致，单场样例单列。",),
        (("statistics", "scope_mismatch"),),
    )
    _, detail, analysis = review_source()
    evidence = ReviewEvidence(detail, analysis, 0)
    cases = {
        "meta": feature_cards(ranking)[0],
        "guide-overview": feature_cards(guide)[0],
        "guide-skills": feature_cards(observed)[0],
        "guide-items": feature_cards(observed)[1],
        "review-economy": ReviewDataCard(
            evidence, ReviewChartRequest(ReviewChartKind.ECONOMY, 0, 1800)
        ),
        "review-advantage": ReviewDataCard(
            evidence, ReviewChartRequest(ReviewChartKind.TEAM_ADVANTAGE, -60, 1800)
        ),
    }
    qa = {}
    thumbs = []
    engine = PreviewRenderer()
    try:
        for name, card in cases.items():
            artifact = engine.render(card)
            path = HERE / (name + ".png")
            path.write_bytes(artifact.data)
            if not isinstance(card, ReviewDataCard):
                (HERE / (name + ".txt")).write_text(feature_text(card), encoding="utf-8")
            qa[name] = {
                "width": artifact.width,
                "height": artifact.height,
                "bytes": len(artifact.data),
                "text_boxes": len(engine.last_layout),
                "synthetic": True,
            }
            with Image.open(path) as source:
                thumb = ImageOps.contain(source, (390, 890))
                thumbs.append(thumb.copy())
        with Image.new("RGB", (1170, 1780), "#101216") as sheet:
            for i, thumb in enumerate(thumbs):
                sheet.paste(thumb, ((i % 3) * 390, (i // 3) * 890))
            sheet.save(HERE / "contact-sheet.png")
    finally:
        engine.close()
        for thumb in thumbs:
            thumb.close()
    (HERE / "qa.json").write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa))


if __name__ == "__main__":
    main()
