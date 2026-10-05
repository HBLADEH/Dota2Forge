"""Synthetic command-menu and rank-estimate cards using production local resources."""

import io
import json
from datetime import UTC, datetime
from pathlib import Path

from dota2forge_core import AccountId, DataMetadata, DataSource, PlayerProfile
from dota2forge_renderer import MenuCard, PillowRenderer, PlayerCard
from PIL import Image


def main() -> None:
    output = Path(".dota2forge-assets/previews-command-mmr-v1")
    output.mkdir(parents=True, exist_ok=True)
    metadata = DataMetadata(DataSource.FIXTURE, datetime(2026, 10, 5, tzinfo=UTC))
    renderer = PillowRenderer(illustration_path=Path(".dota2forge-assets"))
    ranks = [
        None,
        0,
        *[tier * 10 + stars for tier in range(1, 8) for stars in range(1, 6)],
        80,
        16,
        81,
        999,
    ]
    cards = {"menu": MenuCard(), "menu-admin": MenuCard(True)}
    cards.update(
        {
            f"player-{rank}": PlayerCard(PlayerProfile(AccountId(123), metadata, "合成玩家", rank))
            for rank in ranks
        }
    )
    report = {}
    try:
        for name, card in cards.items():
            artifact = renderer.render(card)
            (output / f"{name}.png").write_bytes(artifact.data)
            with Image.open(io.BytesIO(artifact.data)) as image:
                image.load()
                with image.resize((390, artifact.height // 2), Image.Resampling.LANCZOS) as mobile:
                    mobile.save(output / f"{name}-mobile.png")
            report[name] = {
                "width": artifact.width,
                "height": artifact.height,
                "bytes": len(artifact.data),
                "text_boxes": len(renderer.last_layout),
            }
    finally:
        renderer.close()
    Path(".agents/artifacts/command-mmr-guide-v1/qa.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    print(f"Rendered {len(report)} synthetic cards with bounded text and 390px previews.")


if __name__ == "__main__":
    main()
