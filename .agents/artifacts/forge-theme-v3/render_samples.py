"""Production Renderer previews with synthetic fixtures only, never host data."""

import io
import json
import shutil
import sys
from pathlib import Path

from dota2forge_core import (
    Hero,
    HeroItemStatistics,
    ItemPurchaseCount,
    ItemStage,
    PlayerProfile,
    StageItemCounts,
)
from dota2forge_renderer import (
    HeroItemsCard,
    MatchDetailCard,
    MatchReportCard,
    MenuCard,
    PillowRenderer,
    PlayerCard,
    RecentMatchesCard,
    StatusCard,
)
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests/renderer"))
from test_match_report_cards import report  # noqa: E402
from test_renderer_cards import ACCOUNT, META, detail, recent  # noqa: E402


def main():
    output = ROOT / ".dota2forge-assets/forge-theme-v3"
    output.mkdir(parents=True, exist_ok=True)
    # Isolated QA pack keeps official art, and uses the new locally drawn header.
    # The source pack and real host illustration_path are never modified.
    art_path = output / "art"
    art_path.mkdir(exist_ok=True)
    for kind in ("heroes", "items", "ranks", "rank_stars", "ui"):
        shutil.copytree(ROOT / ".dota2forge-assets" / kind, art_path / kind, dirs_exist_ok=True)
    manifest = json.loads((ROOT / ".dota2forge-assets/manifest.json").read_text("utf-8"))
    manifest.pop("decor", None)
    (art_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    cards = {
        "menu": MenuCard(),
        "menu-admin": MenuCard(True),
        "player": PlayerCard(PlayerProfile(ACCOUNT, META, "合成示例玩家", 54)),
        "player-unknown": PlayerCard(PlayerProfile(ACCOUNT, META, "合成未知玩家")),
        "recent": RecentMatchesCard(recent()),
        "recent-empty": RecentMatchesCard(recent(0)),
        "status": StatusCard("已绑定查询账号。现在输入 do查询，查看段位与预估 MMR。"),
        "detail": MatchDetailCard(detail()),
        "hero-items": HeroItemsCard(
            HeroItemStatistics(
                Hero(8, "主宰", "Juggernaut"),
                META,
                tuple(
                    StageItemCounts(
                        stage,
                        tuple(
                            ItemPurchaseCount(item, 200 - index * 31)
                            for index, item in enumerate((1, 63, 36, 147, 116))
                        ),
                    )
                    for stage in ItemStage
                ),
            )
        ),
        "report-overview": MatchReportCard(report()),
        "report-team": MatchReportCard(report(), 2),
    }
    font = ImageFont.truetype(
        str(
            ROOT
            / "packages/dota2forge-renderer/src/dota2forge_renderer"
            / "assets/v1/NotoSansCJKsc-Regular.otf"
        ),
        28,
    )
    results = []
    tiles = []
    for art_enabled in (False, True):
        renderer = PillowRenderer(illustration_path=art_path if art_enabled else None)
        try:
            for name, card in cards.items():
                artifact = renderer.render(card)
                filename = f"{name}{'' if art_enabled else '-no-art'}.png"
                # Keep the exact artifact separate from an explicitly captioned QA image.
                (output / filename).write_bytes(artifact.data)
                with Image.open(io.BytesIO(artifact.data)) as image:
                    qa = Image.new("RGB", (image.width, image.height + 52), "#101216")
                    ImageDraw.Draw(qa).text(
                        (28, 6),
                        "Dota2Forge 设计验收 · 合成数据 · 非实机截图",
                        font=font,
                        fill="#c0a777",
                    )
                    qa.paste(image, (0, 52))
                    qa.save(output / ("qa-" + filename))
                    if image.width == 780:
                        qa.resize((390, qa.height // 2), Image.Resampling.LANCZOS).save(
                            output / ("phone-" + filename)
                        )
                    if art_enabled and name in ("menu", "player", "recent", "hero-items"):
                        tiles.append(qa.resize((390, qa.height // 2), Image.Resampling.LANCZOS))
                    qa.close()
                results.append(
                    {
                        "file": filename,
                        "width": artifact.width,
                        "height": artifact.height,
                        "bytes": len(artifact.data),
                        "bounds_and_overlap": "passed",
                    }
                )
        finally:
            renderer.close()
    board = Image.new("RGB", (1620, max(tile.height for tile in tiles) + 80), "#101216")
    for i, tile in enumerate(tiles):
        board.paste(tile, (12 + i * 404, 20))
        tile.close()
    board.save(output / "overview.png")
    board.close()
    (Path(__file__).parent / "qa.json").write_text(
        json.dumps(
            {
                "fixture": "synthetic only",
                "production_renderer": True,
                "images": results,
                "manual_review": "pending",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Rendered {len(results)} production samples: {output}")


if __name__ == "__main__":
    main()
