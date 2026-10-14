"""Production-card previews; synthetic observations and original geometric icons."""

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

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
from dota2forge_renderer import PillowRenderer, ReviewDataCard
from dota2forge_renderer.features import feature_cards, feature_text
from PIL import Image, ImageDraw, ImageOps

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tests/core"))


class PreviewRenderer(PillowRenderer):
    def display(self, value):
        return super().display("合成测试 · " + value if value.startswith("来源 ") else value)


def main():
    from test_feature_consumers import sample
    from test_hero_features import META, review_source

    art = HERE / "synthetic-icons"
    (art / "items").mkdir(parents=True, exist_ok=True)
    manifest = {"version": 1, "items": {}, "heroes": {}, "decor": {}}
    ids = (1, 4, 34, 50, 116, 145, 108)
    for i, identifier in enumerate(ids):
        path = art / "items" / f"{identifier}.png"
        with Image.new("RGBA", (88, 64), (60 + i * 20, 180, 140, 255)) as image:
            ImageDraw.Draw(image).polygon(((44, 8), (72, 32), (44, 56), (16, 32)), fill="#ffe199")
            image.save(path)
        manifest["items"][str(identifier)] = {
            "status": "available",
            "file": f"items/{identifier}.png",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "name_loc": "合成图标",
            "source": "original synthetic fixture",
        }
    (art / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    labels = (
        "-1.0秒 剑心效果获得间隔",
        "属性加点",
        "+15% 剑舞致命一击伤害",
        "+40% 剑舞吸血",
        "剑刃风暴期间+45 移动速度",
        "+1秒 无敌斩持续时间",
        "-12秒 治疗守卫冷却",
        "+120 剑刃风暴每秒伤害",
    )
    observed = replace(
        sample(),
        upgrades=tuple(
            SkillUpgrade(1200 + i, i % 4, i * 60 - 90, True, labels[i % 8]) for i in range(24)
        ),
        purchases=tuple(PurchaseEvent(i * 60 - 90, ids[i % len(ids)]) for i in range(32)),
    )
    guide = HeroGuide(
        observed.hero,
        3,
        META,
        None,
        tuple(
            BuildItemBucket(identifier, i, 0, 2000 + i, 1000) for i, identifier in enumerate(ids)
        ),
        None,
        tuple(AbilityChoice(1200 + i, None, 2000, 1000, label) for i, label in enumerate(labels)),
        (observed,),
        ("合成测试：天赋中文名称使用 synthetic.1 常量；统计窗口未核实。",),
    )
    _, detail, analysis = review_source()
    analysis = replace(
        analysis, participants=(replace(analysis.participants[0], purchases=observed.purchases),)
    )
    cases = {
        "overview": feature_cards(guide)[0],
        "skills": feature_cards(observed)[0],
        "purchases": feature_cards(observed)[1],
        "talents": feature_cards(guide, detailed=True)[-1],
        "review-items": ReviewDataCard(
            ReviewEvidence(detail, analysis, 0),
            ReviewChartRequest(ReviewChartKind.ITEMS, -120, 1800),
        ),
        "missing-icons": feature_cards(observed)[1],
    }
    report = {}
    thumbs = []
    engine = PreviewRenderer(illustration_path=art)
    empty = PreviewRenderer()
    try:
        for name, card in cases.items():
            renderer = empty if name == "missing-icons" else engine
            artifact = renderer.render(card)
            (HERE / f"{name}.png").write_bytes(artifact.data)
            if not isinstance(card, ReviewDataCard):
                (HERE / f"{name}.txt").write_text(feature_text(card), encoding="utf-8")
            report[name] = {
                "width": artifact.width,
                "height": artifact.height,
                "bytes": len(artifact.data),
                "synthetic": True,
            }
            with Image.open(HERE / f"{name}.png") as source:
                thumbs.append(ImageOps.contain(source, (390, 890)))
        with Image.new("RGB", (1170, 1780), "#101216") as sheet:
            for i, thumb in enumerate(thumbs):
                sheet.paste(thumb, ((i % 3) * 390, (i // 3) * 890))
            sheet.save(HERE / "contact-sheet.png")
    finally:
        engine.close()
        empty.close()
        for thumb in thumbs:
            thumb.close()
    (HERE / "qa.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
