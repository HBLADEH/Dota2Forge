"""Offline synthetic card/layout QA; all counts below are invented fixtures."""

import json
from datetime import UTC, datetime
from pathlib import Path

from dota2forge_core import (
    DataMetadata,
    DataSource,
    Hero,
    HeroItemStatistics,
    ItemPurchaseCount,
    ItemStage,
    StageItemCounts,
)
from dota2forge_renderer import HeroItemsCard, MenuCard, PillowRenderer
from PIL import Image


def main():
    output = Path(".agents/artifacts/hero-builds-v1")
    metadata = DataMetadata(DataSource.FIXTURE, datetime(2026, 10, 5, tzinfo=UTC))
    counts = tuple(
        ItemPurchaseCount(item_id, count)
        for item_id, count in ((1, 80), (44, 40), (45, 21), (48, 12), (999999, 0))
    )
    full = HeroItemStatistics(
        Hero(2, "斧王", "Axe"),
        metadata,
        tuple(StageItemCounts(stage, counts) for stage in ItemStage),
    )
    partial = HeroItemStatistics(
        full.hero,
        metadata,
        (
            StageItemCounts(ItemStage.START, counts),
            StageItemCounts(ItemStage.EARLY, ()),
            StageItemCounts(ItemStage.MID, None),
            StageItemCounts(ItemStage.LATE, counts),
        ),
    )
    cards = {
        "items-full": HeroItemsCard(full),
        "items-partial": HeroItemsCard(partial),
        "menu": MenuCard(),
        "menu-admin": MenuCard(include_admin=True),
    }
    renderer = PillowRenderer()
    report = []
    try:
        for label, card in cards.items():
            artifact = renderer.render(card)
            assert artifact.height <= 1600 and artifact.width == 780
            assert all(
                0 <= box[0] <= box[2] <= 780 and 0 <= box[1] <= box[3] <= artifact.height
                for box in renderer.last_layout
            )
            path = output / (label + ".png")
            path.write_bytes(artifact.data)
            with Image.open(path) as image:
                image.resize((390, artifact.height // 2)).save(output / (label + "-mobile.png"))
            report.append(
                {
                    "label": label,
                    "width": artifact.width,
                    "height": artifact.height,
                    "bytes": len(artifact.data),
                    "all_boxes_inside": True,
                }
            )
    finally:
        renderer.close()
    (output / "render-qa.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
