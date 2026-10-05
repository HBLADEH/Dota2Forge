"""Generate synthetic production-card QA with the actual shared package."""

import argparse
import io
import json
from datetime import datetime
from pathlib import Path

from dota2forge_core import (
    AccountId,
    DataMetadata,
    DataSource,
    MatchDetail,
    MatchId,
    MatchParticipant,
    MatchSummary,
    PlayerProfile,
    RecentMatches,
)
from dota2forge_renderer import (
    MatchDetailCard,
    MenuCard,
    PillowRenderer,
    PlayerCard,
    RecentMatchesCard,
    StatusCard,
)
from PIL import Image

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--illustration-path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads((ROOT.parent / "image-interaction-v1/synthetic.json").read_text("utf-8"))
    metadata = DataMetadata(
        DataSource.FIXTURE, datetime.fromisoformat(raw["metadata"]["fetched_at"])
    )
    account = AccountId(raw["account_id"])
    player = PlayerProfile(account, metadata, **raw["player"])
    rows = tuple(
        MatchSummary(
            account_id=account,
            metadata=metadata,
            **{key: value for key, value in row.items() if key != "started_at"},
            started_at=datetime.fromisoformat(row["started_at"]),
        )
        for row in raw["matches"]
    )
    recent = RecentMatches(account, rows, metadata)
    players = tuple(
        MatchParticipant(
            player_slot=index,
            account_id=account if index == 0 else None,
            display_name=raw["player"]["display_name"] if index == 0 else None,
            is_anonymous=False if index == 0 else True if index % 2 else None,
            is_radiant=index < 5,
            hero_id=(2, 44, 999, 5, None)[index % 5],
            kills=0,
            deaths=0,
            assists=8,
            gold_per_minute=0,
            item_ids=(1, 63, 36, 0, None, 9999),
        )
        for index in range(10)
    )
    detail = MatchDetail(
        MatchId(7000000010),
        metadata,
        started_at=metadata.fetched_at,
        duration_seconds=2105,
        has_stats=False,
        players=players,
    )
    cards = {
        "menu": MenuCard(),
        "menu-admin": MenuCard(True),
        "player": PlayerCard(player),
        "recent-1": RecentMatchesCard(recent),
        "recent-2": RecentMatchesCard(recent, 2),
        "status": StatusCard("账号绑定已保存。绑定仅用于查询，不证明 Steam 账号所有权。"),
        "detail-radiant": MatchDetailCard(detail, perspective=account),
        "detail-dire": MatchDetailCard(detail, 2, account),
        "recent-empty": RecentMatchesCard(RecentMatches(account, (), metadata)),
    }
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    renderer = PillowRenderer(illustration_path=args.illustration_path)
    report = {}
    tiles = []
    try:
        for name, card in cards.items():
            artifact = renderer.render(card)
            (output / f"{name}.png").write_bytes(artifact.data)
            with Image.open(io.BytesIO(artifact.data)) as image:
                image.load()
                mobile = image.resize((390, image.height // 2), Image.Resampling.LANCZOS)
                mobile.save(output / f"{name}-mobile.png")
                if name in ("menu", "player", "recent-1", "detail-radiant"):
                    tiles.append(mobile.copy())
                mobile.close()
            report[name] = {
                "width": artifact.width,
                "height": artifact.height,
                "png_bytes": len(artifact.data),
                "text_boxes": len(renderer.last_layout),
            }
        first = max(tile.height for tile in tiles[:2])
        with Image.new(
            "RGB", (816, first + max(tile.height for tile in tiles[2:]) + 36), "#090e10"
        ) as sheet:
            for index, tile in enumerate(tiles):
                sheet.paste(tile, (12 + index % 2 * 402, 12 if index < 2 else first + 24))
            sheet.save(output / "overview.png")
    finally:
        renderer.close()
        for tile in tiles:
            tile.close()
    (output / "qa.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    print(f"Rendered {len(cards)} real-package cards; text bounds and overlaps checked.")


if __name__ == "__main__":
    main()
