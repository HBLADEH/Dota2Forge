"""Bounded local Pillow layouts with explicit unknown and missing-resource semantics."""

import hashlib
import io
import json
import math
from importlib.resources import files
from pathlib import Path
from types import TracebackType

from dota2forge_core import DataMetadata, DataSource, MatchParseState, MatchParticipant
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from .cards import (
    DETAIL_PER_PAGE,
    MAX_BYTES,
    MAX_HEIGHT,
    MAX_REPORT_HEIGHT,
    PER_PAGE,
    REPORT_WIDTH,
    WIDTH,
    Card,
    HeroItemsCard,
    ImageArtifact,
    MatchDetailCard,
    MatchReportCard,
    MenuCard,
    PlayerCard,
    RecentMatchesCard,
    RenderError,
    StatusCard,
)
from .formatting import (
    duration_text,
    game_mode_text,
    mmr_estimate_text,
    rank_text,
    safe_name,
    safe_text,
    timestamp,
    value_text,
)
from .hero_items import STAGE_LABELS, item_card_name
from .illustrations import Illustrations
from .theme import (
    AMBER as AMBER,
)
from .theme import (
    GOLD as GOLD,
)
from .theme import (
    GREEN as GREEN,
)
from .theme import (
    INK as INK,
)
from .theme import (
    INSET,
)
from .theme import (
    LINE as LINE,
)
from .theme import (
    MUTED as MUTED,
)
from .theme import (
    PANEL as PANEL,
)
from .theme import (
    PAPER as PAPER,
)
from .theme import (
    RED as RED,
)
from .theme import (
    WHITE as WHITE,
)

FONT_SHA256 = "2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b"
type Box = tuple[float, float, float, float]


def detail_groups(card: MatchDetailCard) -> tuple[tuple[str, tuple[MatchParticipant, ...]], ...]:
    groups: list[tuple[str, tuple[MatchParticipant, ...]]] = []
    for side, label in ((True, "天辉"), (False, "夜魇"), (None, "阵营未知")):
        team = tuple(player for player in card.detail.players or () if player.is_radiant is side)
        for offset in range(0, len(team), DETAIL_PER_PAGE):
            groups.append((label, team[offset : offset + DETAIL_PER_PAGE]))
    return tuple(groups) or (
        ("参赛者未知" if card.detail.players is None else "本次返回 0 名参赛者", ()),
    )


class _Canvas:
    def __init__(self, engine: "PillowRenderer", height: int, *, width: int = WIDTH) -> None:
        if width not in (WIDTH, REPORT_WIDTH) or not 1 <= height <= (
            MAX_HEIGHT if width == WIDTH else MAX_REPORT_HEIGHT
        ):
            raise RenderError()
        self.width = width
        self.image = Image.new("RGB", (width, height), PAPER)
        self.draw = ImageDraw.Draw(self.image)
        self.engine = engine
        self.boxes: list[Box] = []

    def __enter__(self) -> "_Canvas":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.image.close()

    def text(
        self,
        x: int,
        y: int,
        value: str,
        *,
        size: int = 28,
        color: str = INK,
        width: int | None = None,
        truncate: bool = True,
    ) -> None:
        value = self.engine.display(value)
        width = self.width - 72 if width is None else width
        typeface = self.engine.font(max(26, size))
        if self.draw.textlength(value, font=typeface) > width:
            if not truncate:
                raise RenderError()
            while value and self.draw.textlength(value + "...", font=typeface) > width:
                value = value[:-1]
            value += "..."
        box = self.draw.textbbox((x, y), value, font=typeface, anchor="lt")
        if box[0] < 0 or box[1] < 0 or box[2] > self.width or box[3] > self.image.height:
            raise RenderError()
        if any(
            box[0] < old[2] and box[2] > old[0] and box[1] < old[3] and box[3] > old[1]
            for old in self.boxes
        ):
            raise RenderError()
        self.boxes.append(box)
        self.draw.text((x, y), value, font=typeface, anchor="lt", fill=color)

    def line(self, y: int) -> None:
        self.draw.line((36, y, self.width - 36, y), fill=LINE, width=1)

    def panel(self, x: int, y: int, width: int, height: int, accent: str | None = None) -> None:
        self.draw.polygon(
            (
                (x + 6, y),
                (x + width, y),
                (x + width, y + height - 6),
                (x + width - 6, y + height),
                (x, y + height),
                (x, y + 6),
            ),
            fill=PANEL,
        )
        if accent is not None:
            self.draw.rectangle((x, y + 6, x + 3, y + height - 6), fill=accent)

    def command(self, y: int, value: str) -> None:
        self.panel(28, y - 14, self.width - 56, 60)
        self.text(44, y, value, size=28, color=GOLD, truncate=False)

    def paragraph(self, y: int, value: str) -> None:
        remaining = safe_text(value)
        font = self.engine.font(28)
        for index in range(3):
            end = 0
            while (
                end < len(remaining)
                and self.draw.textlength(remaining[: end + 1], font=font) <= 708
            ):
                end += 1
            # Keep short Latin terms such as MMR intact at a Chinese line boundary.
            if 0 < end < len(remaining):
                word_start = end
                if remaining[end].isascii() and remaining[end].isalnum():
                    while (
                        word_start > 0
                        and remaining[word_start - 1].isascii()
                        and remaining[word_start - 1].isalnum()
                    ):
                        word_start -= 1
                    if word_start > 0:
                        end = word_start
            self.text(36, y + index * 46, remaining[:end] if index < 2 else remaining)
            remaining = remaining[end:]
            if not remaining:
                break

    def header(self, title: str, subtitle: str) -> None:
        art = self.engine._illustrations.image("decor", "header")
        if art is None:
            self._forge_header()
        else:
            self._header_art(art)
        self.draw.line((36, 172, self.width - 36, 172), fill=GOLD, width=1)
        self.draw.rectangle((0, 0, 7, 174), fill=RED)
        self.text(36, 20, "Dota2Forge", size=30, color=GOLD)
        self.text(36, 70, title, size=40, color=WHITE)
        self.text(36, 134, subtitle, size=26, color=MUTED)

    def _forge_header(self) -> None:
        """Draw original ruin planes locally; runtime wheels contain no bitmap art."""
        for y in range(174):
            shade = round(7 * (1 - y / 174))
            self.draw.line((0, y, self.width, y), fill=(16 + shade, 18 + shade, 22 + shade))
        with Image.new("RGBA", (self.width, 174)) as glow:
            painter = ImageDraw.Draw(glow)
            painter.ellipse((self.width * 0.68, 84, self.width * 1.02, 246), fill=(151, 75, 38, 64))
            painter.ellipse((self.width * 0.63, -80, self.width * 0.86, 72), fill=(58, 86, 102, 32))
            with glow.filter(ImageFilter.GaussianBlur(32)) as haze:
                self.image.paste(haze, (0, 0), haze)

        def plane(points: tuple[tuple[float, int], ...], fill: str) -> None:
            self.draw.polygon(tuple((round(x * self.width), y) for x, y in points), fill=fill)

        plane(((0.65, 174), (0.68, 67), (0.71, 58), (0.74, 174)), "#1B2025")
        plane(((0.68, 67), (0.70, 60), (0.71, 156), (0.69, 174)), "#242B30")
        plane(((0.74, 174), (0.78, 8), (0.80, -6), (0.85, 15), (0.83, 174)), "#252B30")
        plane(((0.80, -6), (0.85, 15), (0.83, 174), (0.81, 131)), "#1A2025")
        plane(((0.78, 8), (0.80, -6), (0.81, 131), (0.79, 166)), "#30353A")
        plane(((0.86, 174), (0.88, 51), (0.93, 27), (0.99, 174)), "#232629")
        plane(((0.93, 27), (0.95, 65), (0.94, 174), (0.90, 174)), "#2B2B29")
        plane(((0.95, 174), (0.98, -8), (1.04, 15), (1.04, 174)), "#191E23")
        plane(((0.58, 160), (0.75, 147), (0.78, 174), (0.58, 174)), "#1C2023")
        plane(((0.74, 172), (0.83, 145), (0.97, 160), (1.0, 174)), "#302A25")
        # Sparse seams and embers stay at the right, clear of the text column.
        for x1, y1, x2, y2, color in (
            (0.78, 8, 0.795, 86, "#494B46"),
            (0.795, 86, 0.79, 129, "#353C40"),
            (0.88, 118, 0.927, 96, "#4E3C2B"),
            (0.828, 152, 0.87, 164, "#704B32"),
            (0.82, 158, 0.825, 141, "#87513A"),
        ):
            self.draw.line(
                (round(x1 * self.width), y1, round(x2 * self.width), y2), fill=color, width=1
            )

    def _header_art(self, art: Image.Image) -> None:
        if art.width > 2048 or art.height > 2048:
            raise RenderError()
        with ImageOps.fit(art, (self.width, 174)) as banner:
            self.image.paste(banner, (0, 0), banner)
        with (
            Image.new("RGB", (self.width, 174), PAPER) as shade,
            self.image.crop((0, 0, self.width, 174)) as banner,
            Image.blend(banner, shade, 0.46) as shaded,
        ):
            self.image.paste(shaded, (0, 0))

    def illustration(
        self, kind: str, identifier: int | None, x: int, y: int, size: tuple[int, int]
    ) -> None:
        width, height = size
        self.draw.rectangle((x, y, x + width, y + height), fill=INSET)
        image = self.engine._illustrations.image(kind, identifier)
        if image is not None:
            resize = ImageOps.contain if kind == "items" else ImageOps.fit
            with resize(image, (width - 2, height - 2)) as thumbnail:
                offset = (x + (width - thumbnail.width) // 2, y + (height - thumbnail.height) // 2)
                self.image.paste(thumbnail, offset, thumbnail)
        elif not (kind == "items" and identifier in (None, 0)):
            self.text(x + width // 2 - 13, y + (height - 28) // 2, "?", color=MUTED, width=30)

    def icon(self, kind: str, identifier: int | str, x: int, y: int, size: tuple[int, int]) -> bool:
        image = self.engine._illustrations.image(kind, identifier)
        if image is None:
            return False
        with ImageOps.contain(image, size) as thumbnail:
            offset = (x + (size[0] - thumbnail.width) // 2, y + (size[1] - thumbnail.height) // 2)
            self.image.paste(thumbnail, offset, thumbnail)
        return True

    def rank(self, rank: int | None) -> None:
        if rank is None:
            return
        tier, stars = divmod(rank, 10)
        if rank not in (0, 80) and not (1 <= tier <= 7 and 1 <= stars <= 5):
            return
        if self.icon("ranks", tier, 548, 352, (184, 184)) and 1 <= tier <= 7:
            self.icon("rank_stars", stars, 548, 352, (184, 184))

    def metadata(self, y: int, metadata: DataMetadata) -> None:
        source = metadata.source.value.upper()
        if metadata.source == DataSource.STRATZ:
            source += " · stratz.com"
        self.line(y)
        self.text(36, y + 20, f"来源 {source}", size=26, color=MUTED)
        self.text(36, y + 59, f"抓取 {timestamp(metadata.fetched_at)}", size=26, color=MUTED)
        self.text(
            36, y + 98, f"数据观测时间 {timestamp(metadata.observed_at)}", size=26, color=MUTED
        )

    def encode(self) -> ImageArtifact:
        with io.BytesIO() as output:
            self.image.save(output, format="PNG", optimize=True)
            if output.tell() > MAX_BYTES:
                raise RenderError()
            artifact = ImageArtifact(output.getvalue(), self.width, self.image.height)
        self.engine.last_layout = tuple(self.boxes)
        return artifact


class PillowRenderer:
    """Resource loading is lazy and local. The caller serializes access and calls close."""

    def __init__(
        self, assets_path: Path | None = None, *, illustration_path: Path | None = None
    ) -> None:
        self._assets_path = assets_path
        self._illustrations = Illustrations(illustration_path)
        self._font_data: bytes | None = None
        self._glyphs: frozenset[int] = frozenset()
        self._heroes: dict[int, str] = {}
        self._fonts: dict[int, ImageFont.FreeTypeFont] = {}
        self._closed = False
        self.last_layout: tuple[Box, ...] = ()

    def _read(self, name: str) -> bytes:
        if self._assets_path is not None:
            return (self._assets_path / name).read_bytes()
        return files("dota2forge_renderer").joinpath("assets", "v1", name).read_bytes()

    def _load(self) -> None:
        if self._font_data is not None:
            return
        font_data = self._read("NotoSansCJKsc-Regular.otf")
        if hashlib.sha256(font_data).hexdigest() != FONT_SHA256:
            raise RenderError()
        glyphs = json.loads(self._read("glyphs.json"))
        heroes = json.loads(self._read("heroes.json"))
        if (
            not isinstance(glyphs, list)
            or any(type(code) is not int for code in glyphs)
            or not isinstance(heroes, dict)
            or not isinstance(heroes.get("heroes"), list)
        ):
            raise RenderError()
        self._heroes = {
            row["id"]: row["name_loc"]
            for row in heroes["heroes"]
            if isinstance(row, dict)
            and type(row.get("id")) is int
            and isinstance(row.get("name_loc"), str)
        }
        self._glyphs = frozenset(glyphs)
        self._illustrations.load()
        self._font_data = font_data

    def display(self, text: str) -> str:
        return "".join(
            char if ord(char) in self._glyphs else f"U+{ord(char):04X}" for char in text[:512]
        )

    def font(self, size: int) -> ImageFont.FreeTypeFont:
        if size not in self._fonts:
            assert self._font_data is not None
            with io.BytesIO(self._font_data) as stream:
                self._fonts[size] = ImageFont.truetype(stream, size)
        return self._fonts[size]

    def hero(self, hero_id: int | None) -> str:
        return (
            self._illustrations.name("heroes", hero_id)
            or self._heroes.get(hero_id, f"英雄 ID {value_text(hero_id)}")
            if hero_id is not None
            else "英雄未知"
        )

    def render(self, card: Card) -> ImageArtifact:
        if self._closed:
            raise RenderError()
        try:
            self._load()
            if isinstance(card, MenuCard):
                return self._menu(card)
            if isinstance(card, PlayerCard):
                return self._player(card)
            if isinstance(card, HeroItemsCard):
                return self._hero_items(card)
            if isinstance(card, RecentMatchesCard):
                return self._recent(card)
            if isinstance(card, StatusCard):
                return self._status(card)
            if isinstance(card, MatchDetailCard):
                return self._detail(card)
            if isinstance(card, MatchReportCard):
                from .match_report_layout import render_report

                return render_report(self, card)
            raise TypeError("Unsupported Dota2Forge card input")
        except (OSError, ValueError, KeyError, Image.DecompressionBombError):
            raise RenderError() from None

    def _menu(self, card: MenuCard) -> ImageArtifact:
        with _Canvas(self, 1780) as canvas:
            canvas.header("今天，先查哪一项？", card.adapter_label + " · 输入命令即可")
            actions = (
                ("查段位", "段位徽章与预估 MMR", "do查询 [ID]"),
                ("查最近战绩", "默认 10 场，可选 1–100 场", "do战绩 [条数] / do战绩 <ID> <条数>"),
                ("看一场比赛", "双方数据、装备、优势曲线与 IMP", "do比赛 <比赛ID> / do比赛 第N场"),
                ("找热门出装", "四阶段购买统计，支持英雄全名与简称", "do主宰出装 / doAM出装"),
            )
            for index, (title, description, command) in enumerate(actions):
                y = 210 + index * 174
                canvas.panel(28, y, 724, 154)
                canvas.text(44, y + 16, f"0{index + 1}", size=26, color=GOLD, width=54)
                canvas.text(110, y + 16, title, size=34, width=610)
                canvas.text(110, y + 66, description, size=26, color=MUTED, width=610)
                canvas.text(44, y + 112, command, size=28, color=GOLD, truncate=False)
            canvas.text(36, 930, "第一次使用：do绑定 <ID>", size=30, color=GOLD)
            canvas.text(36, 985, "账号管理：do账号 / do改绑 <ID> / do解绑", size=26)
            canvas.text(36, 1030, "翻页：do战绩 第N页（同次列表）", size=26)
            canvas.line(1090)
            canvas.text(36, 1116, "自动播报 · 默认关闭", size=30, color=GOLD)
            rows = (
                "do订阅玩家 <ID> / do订阅比赛 <比赛ID>",
                "do订阅 [比赛|段位|日报] [ID]",
                "do订阅列表 [游标] / do取消订阅 <订阅ID>",
                "do重试推送 <事件ID>：先核实送达，可能重复",
            )
            for index, command in enumerate(rows):
                canvas.text(36, 1170 + index * 46, command, size=26, truncate=False)
            canvas.text(
                36,
                1380,
                "素材：do素材状态 / do下载素材 / do更新素材",
                size=26,
                color=GOLD,
                truncate=False,
            )
            if card.include_admin:
                canvas.text(36, 1436, "管理员：do停用", size=26, color=GOLD, width=220)
            canvas.text(
                258 if card.include_admin else 36,
                1436,
                "素材下载与更新限管理员",
                size=26,
                color=MUTED,
                width=490,
            )
            canvas.line(1480)
            for index, notice in enumerate(
                (
                    "ID：Dota 账号 ID 或 SteamID64；比赛 ID 独立。",
                    "绑定只是查询偏好，不证明账号所有权。",
                    "群订阅仅限 Bot 管理员；日报为有限观察。",
                    "图片菜单是命令说明；无需点击，直接输入。",
                    "帮助：do菜单 / do帮助",
                )
            ):
                canvas.text(36, 1506 + index * 46, notice, size=26, color=MUTED)
            return canvas.encode()

    def _player(self, card: PlayerCard) -> ImageArtifact:
        player = card.player
        with _Canvas(self, 960) as canvas:
            canvas.header("玩家概况", "北京时间 UTC+8")
            canvas.text(36, 218, "昵称", size=24, color=MUTED)
            canvas.text(36, 270, safe_name(player.display_name), size=40)
            canvas.panel(28, 352, 724, 272)
            canvas.text(36, 380, "当前段位", size=24, color=MUTED)
            canvas.text(36, 434, rank_text(player.rank_tier), size=40, width=488)
            canvas.rank(player.rank_tier)
            canvas.text(36, 574, f"预估 MMR：{mmr_estimate_text(player.rank_tier)}", size=32)
            canvas.text(
                36,
                632,
                f"账号 {player.account_id.value} · 段位编码 {value_text(player.rank_tier)}",
                size=24,
                color=MUTED,
            )
            canvas.metadata(686, player.metadata)
            canvas.command(836, "查最近比赛：do战绩")
            canvas.text(36, 884, "按段位区间估算，非精确分数；段位可能滞后。", size=24, color=MUTED)
            return canvas.encode()

    def _hero_items(self, card: HeroItemsCard) -> ImageArtifact:
        result = card.statistics
        with _Canvas(self, 1674) as canvas:
            canvas.header("英雄热门出装", "职业比赛购买统计")
            canvas.illustration("heroes", result.hero.hero_id, 36, 206, (132, 76))
            canvas.text(192, 212, result.hero.display_name, size=34, width=552)
            canvas.text(192, 262, "每阶段前 5 项 · 按购买次数排序", size=26, color=MUTED, width=552)
            y = 320
            for stage in result.stages:
                canvas.panel(28, y - 8, 724, 238)
                canvas.text(44, y + 4, STAGE_LABELS[stage.stage], size=28, color=AMBER)
                selected = sorted(stage.items or (), key=lambda item: (-item.count, item.item_id))[
                    :5
                ]
                if not selected:
                    canvas.text(
                        44,
                        y + 84,
                        "统计未知（未返回）" if stage.items is None else "本次无物品统计",
                        color=MUTED,
                    )
                for index, item in enumerate(selected):
                    x = 44 + index * 140
                    canvas.illustration("items", item.item_id, x, y + 46, (124, 66))
                    self._item_label(canvas, item.item_id, x, y + 122, 124)
                    canvas.text(
                        x,
                        y + 190,
                        f"{item.count} 次",
                        size=26,
                        color=AMBER,
                        width=124,
                        truncate=False,
                    )
                y += 252
            canvas.text(36, 1358, "位置 / 补丁 / 统计窗口 / 总样本数：未知", size=26, color=MUTED)
            canvas.metadata(1400, result.metadata)
            canvas.text(36, 1544, "职业比赛购买统计；热门不等于最优出装", size=26, color=MUTED)
            canvas.text(36, 1578, "或购买顺序。", size=26, color=MUTED)
            canvas.text(
                36, 1616, f"opendota.com/heroes/{result.hero.hero_id}", size=26, color=MUTED
            )
            return canvas.encode()

    def _item_label(self, canvas: _Canvas, item_id: int | None, x: int, y: int, width: int) -> None:
        if item_id is None or item_id == 0:
            return
        label = item_card_name(item_id)
        if label.startswith("装备 ID"):
            canvas.text(x, y, "装备 ID", size=26, width=width, truncate=False)
            canvas.text(x, y + 28, str(item_id), size=26, width=width, truncate=False)
            return
        # Wrap names over two lines, retaining an unknown ID in full or falling back to text.
        remaining = self.display(label)
        font = self.font(26)
        end = 0
        while (
            end < len(remaining)
            and canvas.draw.textlength(remaining[: end + 1], font=font) <= width
        ):
            end += 1
        canvas.text(x, y, remaining[:end], size=26, width=width, truncate=False)
        if remaining[end:]:
            canvas.text(
                x,
                y + 28,
                remaining[end:],
                size=26,
                width=width,
                truncate=False,
            )

    def _recent(self, card: RecentMatchesCard) -> ImageArtifact:
        recent = card.recent
        pages = max(1, math.ceil(len(recent.matches) / PER_PAGE))
        if len(recent.matches) > 100 or type(card.page) is not int or not 1 <= card.page <= pages:
            raise RenderError()
        start = (card.page - 1) * PER_PAGE
        selected = recent.matches[start : start + PER_PAGE]
        with _Canvas(self, 520 + max(1, len(selected)) * 208) as canvas:
            canvas.header("近期战绩", f"第 {card.page} / {pages} 页")
            canvas.text(
                36,
                212,
                f"账号 {recent.account_id.value} · 本次返回 {len(recent.matches)} 场",
                size=26,
                color=MUTED,
            )
            y = 276
            if not selected:
                canvas.text(36, y + 36, "本次返回 0 场比赛", size=36)
                canvas.text(36, y + 110, "不代表完整历史没有战绩。", color=MUTED)
                y += 208
            for index, match in enumerate(selected, start + 1):
                color = AMBER if match.is_win is None else GREEN if match.is_win else RED
                canvas.panel(28, y - 14, WIDTH - 56, 198, color)
                canvas.illustration("heroes", match.hero_id, 36, y, (112, 64))
                canvas.text(172, y, f"{index:02d}  {self.hero(match.hero_id)}", size=30, width=450)
                outcome = "未知" if match.is_win is None else "胜" if match.is_win else "负"
                color = AMBER if match.is_win is None else GREEN if match.is_win else RED
                canvas.text(650, y, outcome, size=30, color=color, width=94)
                canvas.text(
                    172, y + 48, timestamp(match.started_at)[:16], size=24, color=MUTED, width=280
                )
                canvas.text(
                    474,
                    y + 48,
                    duration_text(match.duration_seconds),
                    size=24,
                    color=MUTED,
                    width=270,
                )
                canvas.text(
                    36,
                    y + 100,
                    f"K/D/A {value_text(match.kills)}/{value_text(match.deaths)}/"
                    f"{value_text(match.assists)}",
                    size=26,
                    width=356,
                )
                has_gold = canvas.icon("ui", "gold", 414, y + 99, (30, 30))
                canvas.text(
                    452 if has_gold else 414,
                    y + 100,
                    f"GPM {value_text(match.gold_per_minute)} · "
                    f"XPM {value_text(match.experience_per_minute)}",
                    size=24,
                    width=292 if has_gold else 330,
                )
                canvas.text(36, y + 150, f"比赛 ID {match.match_id}", size=24, color=MUTED)
                y += 208
            canvas.metadata(y + 8, recent.metadata)
            canvas.command(y + 158, "看详情：do比赛 <比赛ID> / 第N场")
            canvas.text(
                36, y + 196, "近期列表不保证完整历史 · 北京时间 UTC+8", size=24, color=MUTED
            )
            return canvas.encode()

    def _status(self, card: StatusCard) -> ImageArtifact:
        with _Canvas(self, 650) as canvas:
            canvas.header("账号状态", card.adapter_label)
            canvas.panel(28, 206, 724, 160, GOLD)
            canvas.paragraph(238, card.message)
            canvas.line(386)
            canvas.text(36, 420, "绑定仅是查询偏好，不证明账号所有权。", size=24, color=MUTED)
            canvas.text(36, 520, "状态来自本次本地操作。", size=24, color=MUTED)
            canvas.command(570, "查看账号：do账号 · 查段位：do查询")
            return canvas.encode()

    def _detail(self, card: MatchDetailCard) -> ImageArtifact:
        detail = card.detail
        groups = detail_groups(card)
        if type(card.page) is not int or not 1 <= card.page <= len(groups):
            raise RenderError()
        team_label, team = groups[card.page - 1]
        own = None if card.perspective is None else detail.participant(card.perspective)
        with _Canvas(self, 686 + len(team) * 340) as canvas:
            canvas.header("比赛详情", f"第 {card.page} / {len(groups)} 页")
            canvas.text(36, 206, f"比赛 ID {detail.match_id.value}", size=32)
            canvas.text(36, 252, f"开始 {timestamp(detail.started_at)}", size=26)
            winner = (
                "未知"
                if detail.did_radiant_win is None
                else "天辉"
                if detail.did_radiant_win
                else "夜魇"
            )
            canvas.text(
                36, 294, f"时长 {duration_text(detail.duration_seconds)}", size=26, width=350
            )
            canvas.text(
                420,
                294,
                f"胜方 {winner}",
                color=GREEN
                if detail.did_radiant_win
                else RED
                if detail.did_radiant_win is False
                else AMBER,
                width=324,
            )
            canvas.text(
                36,
                336,
                f"模式 {game_mode_text(detail.game_mode)} · "
                f"版本 ID {value_text(detail.game_version_id)}",
                size=26,
            )
            team_color = GREEN if team_label == "天辉" else RED if team_label == "夜魇" else AMBER
            canvas.text(36, 380, team_label, size=28, color=team_color)
            y = 424
            for player in team:
                name = (
                    "匿名参赛者"
                    if player.is_anonymous is True
                    else "身份未知"
                    if player.account_id is None
                    else safe_name(player.display_name)
                )
                if own is player:
                    name = "[我方] " + name
                canvas.panel(28, y - 8, 724, 320, team_color)
                canvas.draw.rectangle((28, y + 6, 32, y + 64), fill=team_color)
                canvas.illustration("heroes", player.hero_id, 44, y, (112, 64))
                canvas.text(176, y, name, size=28, width=568)
                canvas.text(176, y + 38, self.hero(player.hero_id), size=26, width=248)
                canvas.text(
                    440,
                    y + 38,
                    f"K/D/A {value_text(player.kills)}/{value_text(player.deaths)}/"
                    f"{value_text(player.assists)}",
                    size=26,
                    width=304,
                )
                rows = (
                    (
                        ("GPM", player.gold_per_minute),
                        ("XPM", player.experience_per_minute),
                        ("净资产", player.net_worth),
                    ),
                    (("等级", player.level), ("补刀", player.last_hits), ("反补", player.denies)),
                    (
                        ("英雄伤害", player.hero_damage),
                        ("建筑伤害", player.tower_damage),
                        ("治疗量", player.hero_healing),
                    ),
                )
                for row_index, row in enumerate(rows):
                    for column, (label, value) in enumerate(row):
                        has_gold = (
                            row_index == 0
                            and column == 0
                            and canvas.icon("ui", "gold", 44, y + 80, (30, 30))
                        )
                        canvas.text(
                            44 + column * 234 + (38 if has_gold else 0),
                            y + 82 + row_index * 36,
                            f"{label} {value_text(value)}",
                            size=26,
                            width=188 if has_gold else 226,
                            truncate=False,
                        )
                for slot, item_id in enumerate(player.item_ids):
                    x = 44 + slot * 116
                    canvas.illustration("items", item_id, x, y + 192, (108, 48))
                    self._item_label(canvas, item_id, x, y + 246, 108)
                y += 340
            canvas.metadata(y + 4, detail.metadata)
            stats = "未知" if detail.has_stats is None else "是" if detail.has_stats else "否"
            marker = (
                f"version {value_text(detail.parse_version)}"
                if detail.metadata.source == DataSource.OPENDOTA
                else f"isStats {stats}"
            )
            parse_state = {
                MatchParseState.UNKNOWN: "未知",
                MatchParseState.UNPARSED: "未解析",
                MatchParseState.PARTIAL: "部分解析",
                MatchParseState.UPSTREAM_PARSED: "上游已标记解析",
                MatchParseState.NO_DATA: "未返回",
            }[detail.parse_state]
            canvas.text(36, y + 140, f"{marker} · 状态 {parse_state}", size=26, color=MUTED)
            canvas.text(
                36, y + 174, f"解析时间 {timestamp(detail.parsed_at)}", size=26, color=MUTED
            )
            canvas.text(
                36, y + 208, "解析标记不证明字段完整 · 不保证历史覆盖", size=26, color=MUTED
            )
            return canvas.encode()

    def close(self) -> None:
        self._closed = True
        self._fonts.clear()
        self._heroes.clear()
        self._glyphs = frozenset()
        self._font_data = None
        self._illustrations.close()
        self.last_layout = ()
