# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow==12.3.0", "fonttools==4.60.1"]
# ///
"""Offline, synthetic design previews; no application or host imports."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
WIDTH = 780
MARGIN = 36
PER_PAGE = 5
BEIJING = timezone(timedelta(hours=8))
COLORS = {
    "paper": "#f3f5f4",
    "white": "#ffffff",
    "ink": "#202625",
    "muted": "#5b6662",
    "line": "#d6deda",
    "green": "#176347",
    "red": "#a63838",
    "amber": "#8b6619",
}
HEROES = {1: "敌法师", 2: "斧王", 5: "水晶室女", 21: "风行者", 44: "幻影刺客"}


def prepare_font(original: Path, destination: Path) -> None:
    # Only the known preview corpus is bundled, not a production nickname font.
    corpus = Path(__file__).read_text("utf-8") + (ROOT / "synthetic.json").read_text("utf-8")
    options = subset.Options()
    options.recalc_timestamp = False
    options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14]
    with TTFont(original, recalcTimestamp=False) as typeface:
        sub = subset.Subsetter(options=options)
        sub.populate(unicodes=set(map(ord, corpus)) | set(range(32, 127)))
        sub.subset(typeface)
        names = typeface["name"]
        for record in names.names:
            replacements = {
                1: "Dota2Forge Preview CJK",
                3: "Dota2Forge Preview CJK Regular v1",
                4: "Dota2Forge Preview CJK Regular",
                6: "Dota2ForgePreviewCJK-Regular",
            }
            if record.nameID in replacements:
                record.string = replacements[record.nameID].encode(record.getEncoding())
        destination.parent.mkdir(parents=True, exist_ok=True)
        typeface.save(destination)


def clean(value: str | None) -> str:
    if value is None:
        return "未知"
    return (
        " ".join(
            "".join(
                char for char in value if not unicodedata.category(char).startswith("C")
            ).split()
        )
        or "（空昵称）"
    )


def number(value: int | None) -> str:
    return "未知" if value is None else str(value)


def instant(value: str | None) -> str:
    if value is None:
        return "未知"
    return datetime.fromisoformat(value).astimezone(BEIJING).strftime("%Y-%m-%d %H:%M")


def duration(value: int | None) -> str:
    if value is None:
        return "未知"
    minutes, seconds = divmod(value, 60)
    return f"{minutes}分{seconds:02d}秒"


class Canvas:
    def __init__(self, height: int, font_path: Path) -> None:
        self.image = Image.new("RGB", (WIDTH, height), COLORS["paper"])
        self.draw = ImageDraw.Draw(self.image)
        self.font_path = font_path
        self.fonts: dict[int, ImageFont.FreeTypeFont] = {}
        self.boxes: list[tuple[int, int, int, int]] = []
        self.truncations = 0

    def font(self, size: int) -> ImageFont.FreeTypeFont:
        if size not in self.fonts:
            self.fonts[size] = ImageFont.truetype(str(self.font_path), size)
        return self.fonts[size]

    def text(
        self, x: int, y: int, value: str, *, size: int = 30, color: str = "ink", width: int = 708
    ) -> None:
        typeface = self.font(size)
        if self.draw.textlength(value, font=typeface) > width:
            self.truncations += 1
            while value and self.draw.textlength(value + "...", font=typeface) > width:
                value = value[:-1]
            value += "..."
        box = self.draw.textbbox((x, y), value, font=typeface, anchor="lt")
        if box[0] < 0 or box[1] < 0 or box[2] > WIDTH or box[3] > self.image.height:
            raise ValueError(f"Text outside canvas: {box}")
        if any(
            box[0] < other[2] and box[2] > other[0] and box[1] < other[3] and box[3] > other[1]
            for other in self.boxes
        ):
            raise ValueError(f"Overlapping text: {box}")
        self.boxes.append(box)
        self.draw.text((x, y), value, font=typeface, anchor="lt", fill=COLORS[color])

    def line(self, y: int) -> None:
        self.draw.line((MARGIN, y, WIDTH - MARGIN, y), fill=COLORS["line"], width=2)

    def header(self, title: str, subtitle: str) -> None:
        self.draw.rectangle((0, 0, WIDTH, 174), fill=COLORS["ink"])
        self.draw.rectangle((0, 0, 8, 174), fill=COLORS["red"])
        self.text(MARGIN, 28, "Dota2Forge", size=42, color="white")
        self.text(MARGIN, 94, title, size=32, color="white", width=350)
        self.text(420, 100, subtitle, size=26, color="white", width=324)

    def metadata(self, y: int, metadata: dict[str, object]) -> None:
        self.line(y)
        self.text(MARGIN, y + 24, f"来源 {metadata['source']} · 合成样图", size=26, color="muted")
        self.text(
            MARGIN,
            y + 67,
            f"抓取 {instant(metadata['fetched_at'])} · 北京时间 UTC+8",
            size=26,
            color="muted",
        )
        self.text(
            MARGIN,
            y + 110,
            f"数据观测时间 {instant(metadata['observed_at'])}",
            size=26,
            color="muted",
        )


def menu(font_path: Path) -> Canvas:
    card = Canvas(1040, font_path)
    card.header("命令菜单", "Dota2UID")
    card.text(MARGIN, 214, "账号", color="red")
    rows = [
        ("dota绑定 <ID>", "绑定查询账号"),
        ("dota改绑 <ID>", "替换已有绑定"),
        ("dota账号 / dota解绑", "查看绑定 / 解除绑定"),
        ("dota玩家 [ID]", "玩家概况"),
        ("dota战绩 [条数]", "最近比赛 · 默认 10 场"),
        ("dota战绩 <ID> <条数>", "显式查询 · 1 至 100 场"),
    ]
    for index, (command, label) in enumerate(rows):
        y = 280 + index * 96
        if index == 3:
            card.text(MARGIN, y - 38, "查询", color="red")
        card.text(MARGIN, y, command, size=30, width=412)
        card.text(464, y + 2, label, size=26, color="muted", width=280)
        card.line(y + 54)
    card.text(MARGIN, 905, "ID：Dota 账号 ID 或 SteamID64", size=26, color="muted")
    card.text(MARGIN, 950, "绑定仅是查询偏好，不证明账号所有权。", size=26, color="muted")
    return card


def player(font_path: Path, data: dict[str, object], *, missing: bool = False) -> Canvas:
    card = Canvas(804, font_path)
    card.header("玩家概况", "北京时间 UTC+8")
    card.text(MARGIN, 218, "昵称", size=26, color="muted")
    name = None if missing else data["player"]["display_name"]
    card.text(MARGIN, 270, clean(name), size=40)
    card.line(340)
    card.text(MARGIN, 380, "当前段位", size=26, color="muted")
    card.text(MARGIN, 434, "未知" if missing else "传奇 1 星", size=40)
    card.text(
        MARGIN, 514, "账号 123 · 段位编码 " + ("未知" if missing else "51"), size=26, color="muted"
    )
    card.metadata(606, data["metadata"])
    return card


def recent(font_path: Path, data: dict[str, object], page: int, *, count: int = 10) -> Canvas:
    rows = data["matches"]
    start = (page - 1) * PER_PAGE
    selected = rows[start : start + PER_PAGE]
    height = 296 + max(len(selected), 1) * 208 + 232
    card = Canvas(height, font_path)
    card.header("近期战绩", f"第 {page} / {max(1, math.ceil(count / PER_PAGE))} 页")
    card.text(MARGIN, 212, f"账号 123 · 本次返回 {count} 场", size=28, color="muted")
    y = 276
    if not selected:
        card.text(MARGIN, y + 36, "本次返回 0 场比赛", size=36)
        card.text(MARGIN, y + 110, "不代表完整历史没有战绩。", size=28, color="muted")
        y += 208
    for index, row in enumerate(selected, start + 1):
        card.draw.rectangle((0, y - 14, WIDTH, y + 184), fill=COLORS["white"])
        outcome = row["is_win"]
        label = "未知" if outcome is None else "胜" if outcome else "负"
        color = "amber" if outcome is None else "green" if outcome else "red"
        hero = HEROES.get(row["hero_id"], "英雄 ID " + number(row["hero_id"]))
        card.draw.rectangle((MARGIN, y, 100, y + 64), fill=COLORS["line"])
        card.text(MARGIN + 15, y + 17, "?", size=34, width=40, color="muted")
        card.text(124, y, f"{index:02d}  {hero}", size=32, width=390)
        card.text(650, y, label, size=32, color=color, width=94)
        card.text(124, y + 48, instant(row["started_at"]), size=26, color="muted", width=300)
        card.text(474, y + 48, duration(row["duration_seconds"]), size=26, color="muted", width=270)
        kda = "/".join(number(row[key]) for key in ("kills", "deaths", "assists"))
        card.text(MARGIN, y + 100, f"K/D/A  {kda}", size=28, width=356)
        card.text(
            414,
            y + 100,
            f"GPM {number(row['gold_per_minute'])} · XPM {number(row['experience_per_minute'])}",
            size=26,
            width=330,
        )
        card.text(MARGIN, y + 150, f"比赛 ID  {row['match_id']}", size=26, color="muted")
        y += 208
    card.metadata(y + 8, data["metadata"])
    card.text(MARGIN, y + 178, "近期列表不保证完整历史。", size=26, color="muted")
    return card


def status(font_path: Path) -> Canvas:
    card = Canvas(740, font_path)
    card.header("账号状态", "Dota2UID")
    card.text(MARGIN, 230, "已绑定 Dota 账号", size=40, color="green")
    card.text(MARGIN, 310, "账号 ID 123", size=32)
    card.line(386)
    card.text(MARGIN, 426, "dota玩家 / dota战绩", size=32)
    card.text(MARGIN, 492, "dota改绑 <ID> / dota解绑", size=28, color="muted")
    card.text(MARGIN, 576, "查询偏好，不证明 Steam 账号所有权。", size=26, color="muted")
    card.text(MARGIN, 652, "来源 fixture · 合成绑定状态", size=26, color="muted")
    return card


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-font", type=Path)
    parser.add_argument("--font", type=Path, default=ROOT / "assets/preview-cjk.otf")
    parser.add_argument("--output", type=Path, default=ROOT / "samples")
    args = parser.parse_args()
    if args.prepare_font:
        prepare_font(args.prepare_font, args.font)
    data = json.loads((ROOT / "synthetic.json").read_text("utf-8"))
    cards = {
        "menu": menu(args.font),
        "player": player(args.font, data),
        "recent-1": recent(args.font, data, 1),
        "recent-2": recent(args.font, data, 2),
        "status": status(args.font),
        "player-missing": player(args.font, data, missing=True),
        "recent-empty": recent(args.font, {**data, "matches": []}, 1, count=0),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, card in cards.items():
        path = args.output / f"{name}.png"
        card.image.save(path, optimize=True)
        mobile = card.image.resize((390, card.image.height // 2), Image.Resampling.LANCZOS)
        mobile.save(args.output / f"{name}-mobile.png", optimize=True)
        report[name] = {
            "width": WIDTH,
            "height": card.image.height,
            "png_bytes": path.stat().st_size,
            "text_boxes": len(card.boxes),
            "truncations": card.truncations,
        }
    tiles = [
        cards[name].image.resize((390, cards[name].image.height // 2), Image.Resampling.LANCZOS)
        for name in ("menu", "player", "recent-1", "status")
    ]
    first_row = max(tile.height for tile in tiles[:2])
    second_row = max(tile.height for tile in tiles[2:])
    sheet = Image.new("RGB", (816, first_row + second_row + 36), "#d6deda")
    for index, tile in enumerate(tiles):
        sheet.paste(tile, (12 + (index % 2) * 402, 12 if index < 2 else first_row + 24))
    sheet.save(args.output / "overview.png", optimize=True)
    with TTFont(args.font) as typeface:
        glyphs = set(typeface.getBestCmap())
    corpus = Path(__file__).read_text("utf-8") + (ROOT / "synthetic.json").read_text("utf-8")
    missing_glyphs = sorted(
        {char for char in corpus if not char.isspace() and ord(char) not in glyphs}
    )
    if missing_glyphs:
        raise ValueError(f"Missing preview glyphs: {missing_glyphs}")
    report["font"] = {
        "sha256": hashlib.sha256(args.font.read_bytes()).hexdigest(),
        "missing_preview_glyphs": missing_glyphs,
    }
    large = {
        **data,
        "matches": [
            {**data["matches"][index % 10], "match_id": 7000000100 - index} for index in range(100)
        ],
    }
    large_pages = [recent(args.font, large, page, count=100) for page in range(1, 21)]
    report["pagination"] = {
        "matches": 100,
        "per_page": PER_PAGE,
        "pages": len(large_pages),
        "maximum_height": max(card.image.height for card in large_pages),
        "unexpected_truncations": sum(card.truncations for card in large_pages),
        "scope": "offline layout only; no host paging or message sends",
    }
    for card in large_pages:
        card.image.close()
    (args.output / "qa.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    for card in cards.values():
        card.image.close()
    for tile in tiles:
        tile.close()
    sheet.close()
    print(f"Generated {len(cards)} synthetic cards and 390px mobile previews; text bounds checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
