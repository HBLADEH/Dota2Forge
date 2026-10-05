"""Render synthetic card previews with an explicitly provided local artwork pack."""

import argparse
import io
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from dota2forge_core import (
    AccountId,
    DataMetadata,
    DataSource,
    Hero,
    HeroItemStatistics,
    ItemPurchaseCount,
    ItemStage,
    MatchDetail,
    MatchId,
    MatchParticipant,
    StageItemCounts,
)
from dota2forge_renderer import HeroItemsCard, MatchDetailCard, PillowRenderer
from PIL import Image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--illustration-path", type=Path, required=True)
    args = parser.parse_args()
    output = Path(__file__).resolve().parent
    meta = DataMetadata(DataSource.FIXTURE, datetime(2026, 10, 6, 4, 0, tzinfo=UTC))
    stages = (
        (44, 16, 20, 27, 42),
        (63, 145, 50, 11, 25),
        (1, 36, 135, 147, 151),
        (108, 116, 137, 139, 133),
    )
    statistics = HeroItemStatistics(
        Hero(8, "主宰", "Juggernaut"),
        meta,
        tuple(
            StageItemCounts(
                stage,
                tuple(ItemPurchaseCount(item, 1500 - i * 234) for i, item in enumerate(items)),
            )
            for stage, items in zip(ItemStage, stages, strict=True)
        ),
    )
    players = tuple(
        MatchParticipant(
            player_slot=i,
            account_id=AccountId(100 + i),
            display_name=f"合成玩家 {i + 1}",
            is_anonymous=False,
            is_radiant=i < 5,
            hero_id=(8, 2, 5, 44, 74, 1, 14, 21, 22, 35)[i],
            kills=12 - i,
            deaths=i,
            assists=6 + i,
            gold_per_minute=650 - i * 30,
            experience_per_minute=750 - i * 25,
            item_ids=(63, 145, 1, 116, 36, 108),
            level=25 - i,
            last_hits=310 - i * 21,
            denies=12,
            net_worth=28000 - i * 1700,
            hero_damage=42500 - i * 3000,
            tower_damage=5200 - i * 410,
            hero_healing=0,
        )
        for i in range(10)
    )
    match = MatchDetail(
        MatchId(7000000001),
        meta,
        started_at=meta.fetched_at,
        duration_seconds=2435,
        did_radiant_win=True,
        game_mode="ALL_PICK",
        game_version_id=181,
        has_stats=True,
        players=players,
    )
    cards = {"hero-items": HeroItemsCard(statistics)}
    cards.update(
        {f"match-{page}": MatchDetailCard(match, page, AccountId(100)) for page in range(1, 5)}
    )
    cards["match-missing"] = MatchDetailCard(
        replace(
            match,
            has_stats=None,
            players=(
                MatchParticipant(
                    is_radiant=None, hero_id=999999, kills=0, item_ids=(1, 0, None, 999999, 0, None)
                ),
            ),
        )
    )
    report = {}
    for use_art in (True, False):
        renderer = PillowRenderer(illustration_path=args.illustration_path if use_art else None)
        try:
            for name, card in cards.items():
                artifact = renderer.render(card)
                key = name if use_art else name + "-no-art"
                (output / f"{key}.png").write_bytes(artifact.data)
                with Image.open(io.BytesIO(artifact.data)) as image:
                    image.resize((390, artifact.height // 2), Image.Resampling.LANCZOS).save(
                        output / f"{key}-phone.png"
                    )
                report[key] = {
                    "width": artifact.width,
                    "height": artifact.height,
                    "bytes": len(artifact.data),
                    "text_boxes": len(renderer.last_layout),
                }
        finally:
            renderer.close()
    (output / "render-checks.json").write_text(json.dumps(report, indent=2), "utf-8")


if __name__ == "__main__":
    main()
