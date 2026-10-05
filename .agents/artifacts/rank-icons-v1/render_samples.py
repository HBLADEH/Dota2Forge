"""Synthetic rank-card QA using downloaded local art and the production renderer."""

import argparse
import hashlib
import io
import json
from datetime import datetime
from pathlib import Path

from dota2forge_core import AccountId, DataMetadata, DataSource, PlayerProfile
from dota2forge_renderer import PillowRenderer, PlayerCard
from PIL import Image, ImageDraw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--illustration-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    metadata = DataMetadata(DataSource.FIXTURE, datetime.fromisoformat("2026-10-05T00:00:00+00:00"))
    ranks = [
        0,
        *[tier * 10 + stars for tier in range(1, 8) for stars in range(1, 6)],
        80,
        None,
        16,
        81,
        999,
    ]
    renderer = PillowRenderer(illustration_path=args.illustration_path)
    tiles = []
    report = {}
    try:
        for rank in ranks:
            name = "rank-unknown" if rank is None else f"rank-{rank}"
            player = PlayerProfile(AccountId(123), metadata, "合成玩家", rank)
            artifact = renderer.render(PlayerCard(player))
            (args.output / f"{name}.png").write_bytes(artifact.data)
            with Image.open(io.BytesIO(artifact.data)) as image:
                image.load()
                with image.resize((390, 425), Image.Resampling.LANCZOS) as mobile:
                    mobile.save(args.output / f"{name}-mobile.png")
                with image.crop((24, 348, 756, 594)) as crop:
                    tile = crop.resize((366, 123), Image.Resampling.LANCZOS)
                    tiles.append(tile)
            report[name] = {
                "rank_tier": rank,
                "width": artifact.width,
                "height": artifact.height,
                "png_bytes": len(artifact.data),
                "text_boxes": len(renderer.last_layout),
                "sha256": hashlib.sha256(artifact.data).hexdigest(),
            }
        with Image.new("RGB", (1146, ((len(tiles) + 2) // 3) * 135 + 12), "#090e10") as sheet:
            for index, tile in enumerate(tiles):
                sheet.paste(tile, (12 + index % 3 * 378, 12 + index // 3 * 135))
            sheet.save(args.output / "rank-overview.png")
        with Image.new("RGB", (936, 330), "#10171a") as sheet:
            draw = ImageDraw.Draw(sheet)
            for tier in range(9):
                art = renderer._illustrations.image("ranks", tier)
                assert art is not None
                with art.resize((104, 104), Image.Resampling.LANCZOS) as icon:
                    sheet.paste(icon, (tier * 104, 0), icon)
                draw.text((tier * 104 + 42, 110), str(tier), font=renderer.font(26), fill="white")
            for stars in range(1, 6):
                art = renderer._illustrations.image("rank_stars", stars)
                assert art is not None
                with art.resize((128, 128), Image.Resampling.LANCZOS) as icon:
                    sheet.paste(icon, ((stars - 1) * 156, 172), icon)
                draw.text(
                    ((stars - 1) * 156 + 48, 298), str(stars), font=renderer.font(26), fill="white"
                )
            sheet.save(args.output / "source-icons-overview.png")
    finally:
        renderer.close()
        for tile in tiles:
            tile.close()
    (args.output / "qa.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    print(
        f"Rendered {len(report)} synthetic rank cases and mobile previews; layout bounds checked."
    )


if __name__ == "__main__":
    main()
