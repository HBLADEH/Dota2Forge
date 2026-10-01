"""Bounded local Pillow layouts with explicit unknown and missing-resource semantics."""

import hashlib
import io
import json
import math
from importlib.resources import files
from pathlib import Path
from types import TracebackType

from dota2forge_core import DataMetadata, DataSource, MatchParseState, MatchParticipant
from PIL import Image, ImageDraw, ImageFont

from .cards import (
    MAX_BYTES,
    MAX_HEIGHT,
    PER_PAGE,
    WIDTH,
    Card,
    ImageArtifact,
    MatchDetailCard,
    MenuCard,
    PlayerCard,
    RecentMatchesCard,
    RenderError,
    StatusCard,
)
from .formatting import duration_text, rank_text, safe_name, safe_text, timestamp, value_text

INK, MUTED, PAPER, WHITE = "#202625", "#5b6662", "#f3f5f4", "#ffffff"
GREEN, RED, AMBER, LINE = "#176347", "#a63838", "#8b6619", "#d6deda"
FONT_SHA256 = "2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b"
type Box = tuple[float, float, float, float]


def detail_groups(card: MatchDetailCard) -> tuple[tuple[str, tuple[MatchParticipant, ...]], ...]:
    groups: list[tuple[str, tuple[MatchParticipant, ...]]] = []
    for side, label in ((True, "天辉"), (False, "夜魇"), (None, "阵营未知")):
        team = tuple(player for player in card.detail.players or () if player.is_radiant is side)
        for offset in range(0, len(team), PER_PAGE):
            groups.append((label, team[offset : offset + PER_PAGE]))
    return tuple(groups) or (
        ("参赛者未知" if card.detail.players is None else "本次返回 0 名参赛者", ()),
    )


class _Canvas:
    def __init__(self, engine: "PillowRenderer", height: int) -> None:
        if not 1 <= height <= MAX_HEIGHT:
            raise RenderError()
        self.image = Image.new("RGB", (WIDTH, height), PAPER)
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
        width: int = WIDTH - 72,
    ) -> None:
        value = self.engine.display(value)
        typeface = self.engine.font(max(26, size))
        if self.draw.textlength(value, font=typeface) > width:
            while value and self.draw.textlength(value + "...", font=typeface) > width:
                value = value[:-1]
            value += "..."
        box = self.draw.textbbox((x, y), value, font=typeface, anchor="lt")
        if box[0] < 0 or box[1] < 0 or box[2] > WIDTH or box[3] > self.image.height:
            raise RenderError()
        if any(
            box[0] < old[2] and box[2] > old[0] and box[1] < old[3] and box[3] > old[1]
            for old in self.boxes
        ):
            raise RenderError()
        self.boxes.append(box)
        self.draw.text((x, y), value, font=typeface, anchor="lt", fill=color)

    def line(self, y: int) -> None:
        self.draw.line((36, y, WIDTH - 36, y), fill=LINE, width=2)

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
            self.text(36, y + index * 46, remaining[:end] if index < 2 else remaining)
            remaining = remaining[end:]
            if not remaining:
                break

    def header(self, title: str, subtitle: str) -> None:
        self.draw.rectangle((0, 0, WIDTH, 174), fill=INK)
        self.draw.rectangle((0, 0, 8, 174), fill=RED)
        self.text(36, 28, "Dota2Forge", size=42, color=WHITE)
        self.text(36, 94, title, size=32, color=WHITE, width=350)
        self.text(420, 100, subtitle, size=26, color=WHITE, width=324)

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
            artifact = ImageArtifact(output.getvalue(), WIDTH, self.image.height)
        self.engine.last_layout = tuple(self.boxes)
        return artifact


class PillowRenderer:
    """Resource loading is lazy and local. The caller serializes access and calls close."""

    def __init__(self, assets_path: Path | None = None) -> None:
        self._assets_path = assets_path
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
            self._heroes.get(hero_id, f"英雄 ID {value_text(hero_id)}")
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
            if isinstance(card, RecentMatchesCard):
                return self._recent(card)
            if isinstance(card, StatusCard):
                return self._status(card)
            if isinstance(card, MatchDetailCard):
                return self._detail(card)
            raise TypeError("Unsupported Dota2Forge card input")
        except (OSError, ValueError, KeyError):
            raise RenderError() from None

    def _menu(self, card: MenuCard) -> ImageArtifact:
        with _Canvas(self, 1180 if card.include_admin else 1050) as canvas:
            canvas.header("命令菜单", "Dota2UID")
            groups = (
                (
                    "账号",
                    (
                        ("dota绑定 <ID>", "绑定查询账号"),
                        ("dota改绑 <ID>", "替换已有绑定"),
                        ("dota账号 / dota解绑", "查看 / 解除绑定"),
                    ),
                ),
                (
                    "查询",
                    (
                        ("dota玩家 [ID]", "玩家概况"),
                        ("dota战绩 [条数]", "默认 10 · 1–100 场"),
                        ("dota战绩 <ID> <条数>", "显式查询账号"),
                        ("dota比赛 <ID> / 第N场", "历史单局详情"),
                        ("dota战绩 第N页", "查看同次列表"),
                    ),
                ),
            )
            y = 210
            for label, rows in groups:
                canvas.text(36, y, label, color=RED)
                y += 54
                for command, description in rows:
                    canvas.text(36, y, command, size=28, width=420)
                    canvas.text(464, y + 2, description, size=24, color=MUTED, width=280)
                    canvas.line(y + 42)
                    y += 68
            if card.include_admin:
                canvas.text(36, y + 4, "管理员", color=RED)
                canvas.text(36, y + 54, "dota停用", size=28)
                y += 140
            canvas.text(
                36, y + 24, "ID：Dota 账号 ID 或 SteamID64；比赛 ID 独立。", size=24, color=MUTED
            )
            canvas.text(36, y + 64, "绑定只是查询偏好，不证明账号所有权。", size=24, color=MUTED)
            return canvas.encode()

    def _player(self, card: PlayerCard) -> ImageArtifact:
        player = card.player
        with _Canvas(self, 850) as canvas:
            canvas.header("玩家概况", "北京时间 UTC+8")
            canvas.text(36, 218, "昵称", size=24, color=MUTED)
            canvas.text(36, 270, safe_name(player.display_name), size=40)
            canvas.line(340)
            canvas.text(36, 380, "当前段位", size=24, color=MUTED)
            canvas.text(36, 434, rank_text(player.rank_tier), size=40)
            canvas.text(
                36,
                514,
                f"账号 {player.account_id.value} · 段位编码 {value_text(player.rank_tier)}",
                size=24,
                color=MUTED,
            )
            canvas.metadata(606, player.metadata)
            canvas.text(36, 780, "段位不代表精确 MMR。", size=24, color=MUTED)
            return canvas.encode()

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
                canvas.draw.rectangle((0, y - 14, WIDTH, y + 184), fill=WHITE)
                canvas.draw.rectangle((36, y, 100, y + 64), fill=LINE)
                canvas.text(51, y + 17, "?", size=34, color=MUTED, width=40)
                canvas.text(124, y, f"{index:02d}  {self.hero(match.hero_id)}", size=30, width=390)
                outcome = "未知" if match.is_win is None else "胜" if match.is_win else "负"
                color = AMBER if match.is_win is None else GREEN if match.is_win else RED
                canvas.text(650, y, outcome, size=30, color=color, width=94)
                canvas.text(
                    124, y + 48, timestamp(match.started_at)[:16], size=24, color=MUTED, width=300
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
                canvas.text(
                    414,
                    y + 100,
                    f"GPM {value_text(match.gold_per_minute)} · "
                    f"XPM {value_text(match.experience_per_minute)}",
                    size=24,
                    width=330,
                )
                canvas.text(36, y + 150, f"比赛 ID {match.match_id}", size=24, color=MUTED)
                y += 208
            canvas.metadata(y + 8, recent.metadata)
            canvas.text(36, y + 158, "dota比赛 <比赛ID> / 第N场", size=24, color=MUTED)
            canvas.text(
                36, y + 196, "近期列表不保证完整历史 · 北京时间 UTC+8", size=24, color=MUTED
            )
            return canvas.encode()

    def _status(self, card: StatusCard) -> ImageArtifact:
        with _Canvas(self, 650) as canvas:
            canvas.header("账号状态", "Dota2UID")
            canvas.paragraph(238, card.message)
            canvas.line(386)
            canvas.text(36, 420, "绑定仅是查询偏好，不证明账号所有权。", size=24, color=MUTED)
            canvas.text(36, 520, "状态来自本次本地操作。", size=24, color=MUTED)
            return canvas.encode()

    def _detail(self, card: MatchDetailCard) -> ImageArtifact:
        detail = card.detail
        groups = detail_groups(card)
        if type(card.page) is not int or not 1 <= card.page <= len(groups):
            raise RenderError()
        label, team = groups[card.page - 1]
        own = None if card.perspective is None else detail.participant(card.perspective)
        with _Canvas(self, 740 + len(team) * 160) as canvas:
            canvas.header("比赛详情", f"第 {card.page} / {len(groups)} 页")
            canvas.text(36, 210, f"比赛 ID {detail.match_id.value}", size=32)
            canvas.text(36, 264, f"开始 {timestamp(detail.started_at)}", size=24)
            winner = (
                "未知"
                if detail.did_radiant_win is None
                else "天辉"
                if detail.did_radiant_win
                else "夜魇"
            )
            canvas.text(
                36, 309, f"时长 {duration_text(detail.duration_seconds)}", size=26, width=330
            )
            canvas.text(420, 309, f"胜方 {winner}", size=26, width=324)
            canvas.text(
                36,
                352,
                f"模式 {detail.game_mode or '未知'} · 版本 ID {value_text(detail.game_version_id)}",
                size=24,
            )
            stats = "未知" if detail.has_stats is None else "是" if detail.has_stats else "否"
            parse_state = {
                MatchParseState.UNKNOWN: "未知",
                MatchParseState.UNPARSED: "未解析",
                MatchParseState.PARTIAL: "部分解析",
                MatchParseState.UPSTREAM_PARSED: "上游已标记解析",
                MatchParseState.NO_DATA: "未返回",
            }[detail.parse_state]
            canvas.text(
                36,
                395,
                f"{detail.metadata.source.value.upper()} isStats {stats} · 状态 {parse_state}",
                size=24,
            )
            canvas.text(36, 438, f"解析时间 {timestamp(detail.parsed_at)}", size=26)
            canvas.text(36, 486, label, size=28, color=RED)
            y = 546
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
                canvas.text(36, y, name, size=28, width=356)
                canvas.text(420, y + 2, "?  " + self.hero(player.hero_id), size=26, width=324)
                canvas.text(
                    36,
                    y + 50,
                    f"K/D/A {value_text(player.kills)}/{value_text(player.deaths)}/"
                    f"{value_text(player.assists)}",
                    size=24,
                    width=356,
                )
                canvas.text(
                    420,
                    y + 50,
                    f"GPM {value_text(player.gold_per_minute)} · "
                    f"XPM {value_text(player.experience_per_minute)}",
                    size=24,
                    width=324,
                )
                items = "/".join(
                    "未知" if item is None else "空" if item == 0 else str(item)
                    for item in player.item_ids
                )
                canvas.text(36, y + 100, "装备 ID " + items, size=24)
                canvas.line(y + 138)
                y += 160
            canvas.metadata(y + 6, detail.metadata)
            canvas.text(
                36, y + 161, "解析标记不证明字段完整 · 不保证历史覆盖", size=24, color=MUTED
            )
            return canvas.encode()

    def close(self) -> None:
        self._closed = True
        self._fonts.clear()
        self._heroes.clear()
        self._glyphs = frozenset()
        self._font_data = None
        self.last_layout = ()
