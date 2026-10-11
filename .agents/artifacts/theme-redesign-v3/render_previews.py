"""Render proposed UI layouts with synthetic values and local, existing art only.

This is a design preview, independent of the production Renderer. Output remains
under ignored .dota2forge-assets because it includes Valve artwork. No network,
credentials, host configuration, real player identity, or provider calls are used.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / ".dota2forge-assets"
OUT = ART / "previews-theme-v3"
FONT = (
    ROOT
    / "packages/dota2forge-renderer/src/dota2forge_renderer/assets/v1/NotoSansCJKsc-Regular.otf"
)
SERIF = Path("C:/Windows/Fonts/georgiab.ttf")
CATALOG = json.loads((FONT.parent / "items.json").read_text(encoding="utf-8"))["items"]

BG = "#101216"
PANEL = "#1B2025"
INSET = "#242A30"
TEXT = "#E8E3D8"
MUTED = "#ADB1B6"
GOLD = "#C0A777"
RED = "#ED7865"
GREEN = "#92C6A2"
LINE = "#3B4148"
BLUE = "#9AB9D1"
PREVIEW = "设计预览 · 合成数据"
CHECKS: list[dict[str, object]] = []


class Canvas:
    def __init__(self, width: int, height: int, name: str):
        self.image = Image.new("RGB", (width, height), BG)
        self.draw = ImageDraw.Draw(self.image)
        self.width, self.height, self.name = width, height, name
        self.boxes: list[tuple[int, int, int, int]] = []

    def text(self, x, y, text, size=28, color=TEXT, width=None, serif=False):
        font = ImageFont.truetype(str(SERIF if serif and SERIF.exists() else FONT), size)
        box = self.draw.textbbox((x, y), text, font=font, anchor="lt")
        if width is not None and box[2] - x > width:
            raise ValueError(f"{self.name}: text wider than {width}: {text}")
        if box[0] < 0 or box[1] < 0 or box[2] > self.width or box[3] > self.height:
            raise ValueError(f"{self.name}: text outside image: {text}, {box}")
        self.draw.text((x, y), text, font=font, fill=color, anchor="lt")
        self.boxes.append(box)

    def rect(self, x, y, width, height, fill=PANEL, outline=None):
        self.draw.rectangle((x, y, x + width, y + height), fill=fill, outline=outline)

    def rule(self, y, x=36, width=None):
        self.draw.line((x, y, x + (width or self.width - 2 * x), y), fill=LINE, width=1)

    def art(self, kind, identifier, x, y, width, height, crop=False):
        path = ART / kind / f"{identifier}.png"
        self.rect(x, y, width, height, INSET)
        if not path.is_file():
            self.text(x + 8, y + 8, "?", min(height - 12, 30), MUTED)
            return
        with Image.open(path) as source:
            original = source.convert("RGBA")
            fitted = (
                ImageOps.fit(original, (width, height), method=Image.Resampling.LANCZOS)
                if crop
                else ImageOps.contain(original, (width, height), method=Image.Resampling.LANCZOS)
            )
            self.image.paste(
                fitted, (x + (width - fitted.width) // 2, y + (height - fitted.height) // 2), fitted
            )

    def header(self, title, subtitle, wide=False):
        h = 230 if wide else 240
        path = OUT / "forge-atmosphere.png"
        if path.is_file():
            with Image.open(path) as original:
                banner = ImageOps.fit(
                    original.convert("RGB"), (self.width, h), method=Image.Resampling.LANCZOS
                )
                banner = Image.blend(banner, Image.new("RGB", banner.size, BG), 0.46)
                self.image.paste(banner, (0, 0))
        self.rect(0, 0, 8, h, RED)
        self.text(36, 28, "Dota2Forge", 30, GOLD, serif=True)
        self.text(36, 90, title, 54 if wide else 46)
        self.text(36, 161 if wide else 163, subtitle, 28, MUTED)
        self.text(self.width - 304, 32, PREVIEW, 24, GOLD, width=280)
        self.draw.line((36, h - 1, self.width - 36, h - 1), fill=GOLD, width=1)

    def section(self, y, title, caption=None, color=GOLD):
        self.text(36, y, title, 30, color)
        if caption:
            self.text(36, y + 47, caption, 26, MUTED)

    def footer(self, y, source="STRATZ", note="未知字段保留未知；不保证历史完整。"):
        self.rule(y)
        self.text(36, y + 24, f"来源 {source} · 此页统计为合成示例", 24, MUTED)
        self.text(36, y + 66, "抓取 2026-10-11 17:00 UTC+8 · 示例时间", 24, MUTED)
        self.text(36, y + 108, "数据观测时间：未知", 24, MUTED)
        self.text(36, y + 150, note, 24, MUTED)

    def command(self, y, command, explanation=None, color=GOLD):
        self.rect(36, y, self.width - 72, 66 if not explanation else 106, INSET)
        self.text(56, y + 18, command, 28, color, width=self.width - 112)
        if explanation:
            self.text(56, y + 63, explanation, 24, MUTED, width=self.width - 112)

    def save(self):
        for i, first in enumerate(self.boxes):
            for second in self.boxes[i + 1 :]:
                if min(first[2], second[2]) > max(first[0], second[0]) and min(
                    first[3], second[3]
                ) > max(first[1], second[1]):
                    raise ValueError(f"{self.name}: overlapping text {first}, {second}")
        path = OUT / f"{self.name}.png"
        self.image.save(path, optimize=True)
        if path.stat().st_size > 2 * 1024 * 1024:
            raise ValueError(f"{self.name}: PNG larger than 2 MiB")
        if self.width in (780, 1600):
            ceiling = 1800 if self.width == 780 else 3200
            if self.height > ceiling:
                raise ValueError(f"{self.name}: exceeds existing card dimensions")
        CHECKS.append(
            {
                "name": self.name,
                "width": self.width,
                "height": self.height,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "text_boxes": len(self.boxes),
                "text_bounds": "passed",
                "text_overlap": "passed",
            }
        )
        if self.width == 780:
            self.image.resize((390, self.height // 2), Image.Resampling.LANCZOS).save(
                OUT / f"{self.name}-390.png"
            )
        return self.image


def menu():
    c = Canvas(780, 1770, "menu")
    c.header("今天，先查哪一项？", "输入下方命令即可 · 图片菜单无需点击")
    actions = [
        ("01", "查我的段位", "段位徽章与预估 MMR", "do查询"),
        ("02", "查最近战绩", "默认 10 场，可指定 1–100 场", "do战绩    /    do战绩 20"),
        (
            "03",
            "看一场比赛",
            "双方数据、装备、优势曲线与 IMP",
            "do比赛 第1场    /    do比赛 <比赛ID>",
        ),
        ("04", "找英雄热门出装", "出门、前期、中期、后期购买次数", "do主宰出装    /    doAM出装"),
    ]
    for i, (number, title, description, command) in enumerate(actions):
        y = 276 + i * 192
        c.rect(36, y, 708, 170)
        c.text(56, y + 21, number, 25, GOLD, serif=True)
        c.text(114, y + 20, title, 34)
        c.text(114, y + 73, description, 25, MUTED, width=598)
        c.text(56, y + 125, command, 28, GOLD, width=650)
    c.section(1070, "第一次使用", "绑定后，查自己不用再输入账号 ID")
    c.command(1160, "do绑定 <ID>")
    c.text(36, 1255, "查别人：do查询 <ID> · 翻页：do战绩 第3页", 25, MUTED)
    c.rule(1312)
    c.text(36, 1342, "账号管理", 28)
    c.text(36, 1390, "do账号 · do改绑 <ID> · do解绑", 26, GOLD)
    c.text(36, 1452, "自动播报 · 默认关闭", 28)
    c.text(36, 1500, "do订阅玩家 <ID> · do订阅比赛 <比赛ID>", 26, GOLD)
    c.text(36, 1550, "do订阅列表 · do取消订阅 <订阅ID>", 25, MUTED)
    c.rule(1610)
    c.text(36, 1635, "群订阅仅限 Bot 管理员；具体启用状态看实例。", 24, MUTED)
    c.text(36, 1675, "ID 支持 Dota 账号 ID 或 SteamID64。", 24, MUTED)
    c.text(36, 1715, "绑定是查询偏好，不证明账号所有权。", 24, MUTED)
    return c.save()


def player():
    c = Canvas(780, 1060, "player")
    c.header("玩家概况", "do查询 · 段位与预估 MMR")
    c.text(36, 283, "示例玩家", 42)
    c.text(36, 348, "账号 ID：示例隐藏 · 段位编码 54", 25, MUTED)
    c.rect(36, 414, 708, 225)
    c.text(58, 443, "当前段位", 26, MUTED)
    c.text(58, 497, "万古流芳 IV", 39, width=420)
    c.text(58, 565, "预估 MMR  3542–3695", 30, GOLD)
    c.art("ranks", 5, 520, 427, 200, 194)
    with Image.open(ART / "rank_stars/4.png") as original:
        star = ImageOps.contain(original.convert("RGBA"), (200, 194))
        c.image.paste(star, (520, 427), star)
    c.text(36, 680, "按段位区间估算；不是精确 MMR。", 26, MUTED)
    c.command(739, "下一步：do战绩", "查看该账号最近的比赛")
    c.footer(870, note="段位可能滞后；未定级或未知时不估算。")
    return c.save()


RECENT = [
    (8, "主宰", True, "12 / 3 / 9", "684", (63, 145, 116, 147, 137, 24)),
    (1, "敌法师", False, "5 / 7 / 4", "520", (63, 145, 116, 147, 24, 0)),
    (2, "斧王", True, "8 / 6 / 17", "438", (1, 36, 63, 119, 0, None)),
    (21, "风行者", None, "? / 4 / 11", "未知", (63, 1, 116, None, 0, 0)),
    (5, "水晶室女", True, "2 / 8 / 23", "286", (36, 1, 63, 0, 0, None)),
]


def recent():
    c = Canvas(780, 1610, "recent")
    c.header("最近战绩", "本次返回 10 场 · 第 1 / 2 页 · 每页 5 场")
    for i, (hid, hero, win, kda, gpm, items) in enumerate(RECENT):
        y = 273 + i * 201
        color = GREEN if win is True else RED if win is False else MUTED
        c.rect(36, y, 708, 179)
        c.rect(36, y, 4, 179, color)
        c.art("heroes", hid, 54, y + 18, 110, 64, True)
        c.text(184, y + 17, f"{i + 1:02d}  {hero}", 30)
        c.text(
            574,
            y + 19,
            "胜利" if win is True else "失利" if win is False else "胜负未知",
            27,
            color,
        )
        c.text(184, y + 65, f"K/D/A  {kda}   ·   GPM {gpm}", 25, MUTED, width=535)
        c.text(54, y + 121, "装备", 24, MUTED)
        for j, item in enumerate(items):
            x = 147 + j * 92
            c.rect(x, y + 105, 78, 58, INSET)
            if item:
                c.art("items", item, x + 2, y + 107, 74, 54)
    c.command(1300, "翻页：do战绩 第2页", "看详情：do比赛 第1场")
    c.footer(1420, note="空装备槽可能无装备或未提供；未知不补零。")
    return c.save()


STAGES = [
    ("出门", (44, 16, 42, 182, 38)),
    ("前期", (63, 26, 11, 36, 50)),
    ("中期", (145, 147, 116, 1, 24)),
    ("后期", (137, 135, 139, 147, 116)),
]


def item_name(identifier):
    return CATALOG.get(str(identifier), {}).get("name_loc", f"物品 {identifier}")


def items():
    c = Canvas(780, 1670, "hero-items")
    c.header("主宰 · 热门出装", "do主宰出装 · OpenDota 职业比赛购买统计")
    c.art("heroes", 8, 36, 269, 168, 98, True)
    c.text(230, 278, "看热门选择", 34)
    c.text(230, 335, "购买次数排序，不代表购买顺序", 25, MUTED)
    for stage, (title, ids) in enumerate(STAGES):
        y = 413 + stage * 230
        c.text(36, y, f"0{stage + 1}  {title}", 30, GOLD)
        c.text(420, y + 3, "购买次数 · 合成示例", 25, MUTED)
        for j, identifier in enumerate(ids):
            x = 36 + j * 144
            c.rect(x, y + 54, 132, 152)
            c.art("items", identifier, x + 13, y + 67, 106, 76)
            name = item_name(identifier)
            for line, part in enumerate((name[:5], name[5:10])):
                if part:
                    c.text(x + 9, y + 151 + line * 25, part, 22, width=116)
            c.rect(x + 13, y + 118, 106, 26, BG)
            c.text(x + 20, y + 119, str(540 - stage * 78 - j * 41), 22, TEXT)
    c.text(36, 1356, "位置、补丁、统计窗口、总样本：未知", 25, MUTED)
    c.text(36, 1402, "热门不等于最优；次数不能换算胜率。", 25, TEXT)
    c.footer(1475, "OpenDota", "每阶段前 5 项；无统计与请求失败分别提示。")
    return c.save()


TEAM = [
    (8, "主宰", 34, "12/3/9", "64%", 26100, 684, 24120, 6350, 0),
    (1, "敌法师", 18, "5/7/4", "27%", 22100, 520, 18320, 2210, 0),
    (2, "斧王", 52, "8/6/17", "76%", 19400, 438, 26930, 1680, 145),
    (21, "风行者", None, "6/4/11", "52%", 17800, 410, 19120, 310, 0),
    (5, "水晶室女", 7, "2/8/23", "76%", 10300, 286, 11200, 40, 2150),
]
DIRE = [
    (11, "影魔", -12, "8/5/6", "52%", 24200, 625, 29800, 3540, 0),
    (44, "幻影刺客", 11, "11/5/7", "67%", 23900, 598, 22420, 2110, 0),
    (3, "祸乱之源", -20, "2/7/15", "63%", 13900, 354, 14670, 0, 1520),
    (4, "嗜血狂魔", 0, "4/7/12", "59%", 18200, 449, 21890, 1020, 0),
    (9, "米拉娜", -8, "2/9/14", "59%", 15300, 372, 13640, 220, 0),
]


def table(c, y, title, rows, color):
    c.text(36, y, title, 35, color)
    headings = [
        (36, "英雄 / 玩家"),
        (355, "位置"),
        (451, "IMP"),
        (572, "K/D/A"),
        (744, "参战"),
        (878, "净资产"),
        (1034, "GPM"),
        (1155, "伤害"),
        (1303, "建筑"),
        (1440, "治疗"),
    ]
    for x, title in headings:
        c.text(x, y + 69, title, 26, MUTED)
    for i, row in enumerate(rows):
        yy = y + 119 + i * 101
        hid, name, imp, kda, participation, net, gpm, damage, tower, healing = row
        c.rect(36, yy, 1528, 88)
        c.rect(36, yy, 4, 88, color)
        c.art("heroes", hid, 53, yy + 15, 84, 49, True)
        c.text(155, yy + 13, name, 28)
        c.text(155, yy + 55, f"示例玩家 {i + 1:02d}", 23, MUTED)
        values = [
            (355, f"{i + 1}号位", MUTED),
            (
                451,
                "未知" if imp is None else f"{imp:+d}",
                MUTED if imp is None or imp == 0 else GREEN if imp > 0 else RED,
            ),
            (572, kda, TEXT),
            (744, participation, TEXT),
            (878, f"{net:,}", GOLD),
            (1034, str(gpm), TEXT),
            (1155, f"{damage:,}", TEXT),
            (1303, str(tower), TEXT),
            (1440, str(healing), TEXT),
        ]
        for x, value, col in values:
            c.text(x, yy + 28, value, 27, col)


def report():
    c = Canvas(1600, 2630, "match-overview")
    c.header("天辉胜利", "比赛报告 · 合成比赛 · 总览 / 天辉详情 / 夜魇详情", True)
    c.text(36, 278, "33 : 27", 66, serif=True)
    c.text(421, 301, "39分34秒  ·  全英雄选择（天梯）", 34, MUTED)
    c.text(1140, 299, "第 1 / 3 页", 34, GOLD)
    table(c, 421, "天辉 RADIANT", TEAM, GREEN)
    table(c, 1090, "夜魇 DIRE", DIRE, RED)
    c.text(36, 1765, "比赛走势", 36)
    series = [(-2, -1, 1, -1, 2, 3, 2, 4, 3, 2, 1, 0.2), (0, -1, -1, 0, 1, 1, 3, 2, 4, 5, 6, 9)]
    for j, values in enumerate(series):
        x, y, w, h = 36 + j * 786, 1836, 742, 250
        c.rect(x, y, w, h)
        c.text(x + 22, y + 22, "团队净资产优势" if j == 0 else "团队经验优势", 28)
        c.text(x + 490, y + 22, "合成示例", 24, GOLD)
        c.text(x + 22, y + 66, "+200 金钱" if j == 0 else "+9,000 经验", 24, GREEN)
        baseline = y + 176
        c.draw.line((x + 90, baseline, x + w - 30, baseline), fill=LINE)
        c.text(x + 18, baseline - 12, "0", 22, MUTED)
        c.text(x + 18, y + 115, "8k", 22, MUTED)
        points = [
            (x + 90 + i * (w - 125) / 11, baseline - value * 7) for i, value in enumerate(values)
        ]
        for i in range(len(points) - 1):
            c.draw.line(
                (points[i], points[i + 1]), fill=GREEN if values[i + 1] >= 0 else RED, width=3
            )
        c.text(x + 20, y + 211, "-1:00", 22, MUTED)
        c.text(x + w - 85, y + 211, "39:00", 22, MUTED)
    c.text(36, 2120, "IMP 较高", 29, GREEN)
    c.text(310, 2120, "斧王 +52 · 主宰 +34 · 敌法师 +18", 29)
    c.text(36, 2180, "IMP 较低", 29, RED)
    c.text(310, 2180, "祸乱之源 -20 · 影魔 -12 · 米拉娜 -8", 29)
    c.text(36, 2244, "仅比较本局已提供的 IMP；0 与未知不参加突出/偏弱排序。", 26, MUTED)
    c.footer(2315, note="IMP 是 STRATZ 来源模型评分，非官方 MVP；统计不等于评分公式。")
    c.text(
        36,
        2510,
        "解析：上游已标记 · isStats 是 · 解析时间未知；解析标记不保证字段完整。",
        25,
        MUTED,
    )
    c.text(
        36, 2555, "分析抓取：示例时间 · 优势首样本为 -60～0 秒；正值天辉 / 负值夜魇。", 25, MUTED
    )
    return c.save()


def team_detail():
    c = Canvas(1600, 3140, "match-team")
    c.header("天辉 · 完整数据", "第 2 / 3 页 · 合成比赛 · 五名参赛者与装备槽", True)
    for i, row in enumerate(TEAM):
        hid, name, imp, kda, participation, net, gpm, damage, tower, healing = row
        y = 276 + i * 493
        c.rect(36, y, 1528, 463)
        c.rect(36, y, 4, 463, GREEN)
        c.art("heroes", hid, 56, y + 22, 142, 84, True)
        c.text(224, y + 22, name, 37)
        c.text(224, y + 81, f"示例玩家 {i + 1:02d} · {i + 1}号位 · 分路未知", 27, MUTED)
        c.text(1020, y + 31, f"K/D/A  {kda}", 36)
        c.text(
            1360,
            y + 91,
            "IMP " + ("未知" if imp is None else f"{imp:+d}"),
            28,
            GREEN if imp is not None and imp > 0 else MUTED,
        )
        metrics = [
            ("等级", "25"),
            ("参战率", participation),
            ("补刀 / 反补", "248 / 16"),
            ("净资产", f"{net:,}"),
            ("GPM / XPM", f"{gpm} / 未知"),
            ("英雄伤害", f"{damage:,}"),
            ("建筑伤害", str(tower)),
            ("治疗", str(healing)),
        ]
        for j, (label, value) in enumerate(metrics):
            x = 57 + j * 187
            c.text(x, y + 156, label, 24, MUTED, width=177)
            c.text(x, y + 201, value, 27, GOLD if label == "净资产" else TEXT, width=177)
        c.text(56, y + 270, "装备", 23, MUTED)
        items = RECENT[i][5]
        for j, item in enumerate(items):
            x = 57 + j * 145
            c.rect(x, y + 317, 123, 83, INSET)
            if item:
                c.art("items", item, x + 2, y + 319, 119, 79)
                full = item_name(item)
                c.text(x + 2, y + 413, full[:5], 21, width=120)
                if len(full) > 5:
                    c.text(x + 2, y + 440, full[5:10], 21, width=120)
        c.text(955, y + 270, "背包", 23, MUTED)
        for j in range(3):
            c.rect(955 + j * 120, y + 317, 104, 83, INSET)
        c.text(1370, y + 270, "中立装备", 23, MUTED)
        c.rect(1370, y + 317, 154, 83, INSET)
    c.footer(2800, note="空白槽可能无装备或未提供；未知物品仍保留名称 / ID。")
    c.text(36, 3000, "IMP 来源评分，非官方 MVP · 解析时间未知 · 分析抓取为示例时间。", 25, MUTED)
    c.text(36, 3047, "匿名玩家保持匿名；已解析不代表完整。夜魇页使用相同结构。", 25, MUTED)
    return c.save()


def states():
    c = Canvas(1600, 1480, "components")
    c.header("统一组件与提示", "所有提示先说结果，再给下一步 · 以下为设计文案示例", True)
    samples = [
        ("已绑定查询账号", "现在输入 do查询，查看你的段位。", GREEN),
        ("你还没有绑定账号", "输入 do绑定 <ID>；也可直接 do查询 <ID>。", GOLD),
        ("这次没有返回比赛记录", "来源返回空列表，不能据此判断从未对战。", MUTED),
        ("STRATZ 查询超时", "稍后重新输入 do战绩；本次查询失败。", RED),
        ("数据源额度已用尽", "等待时间未知，请联系管理员核实额度。", RED),
        ("这项数据尚未提供", "来源未提供该字段，其余已知统计仍可查看。", BLUE),
    ]
    for i, (title, description, color) in enumerate(samples):
        x, y = 36 + (i % 2) * 786, 278 + (i // 2) * 208
        c.rect(x, y, 742, 179)
        c.rect(x, y, 4, 179, color)
        c.text(x + 24, y + 25, title, 32, color)
        # Split at punctuation so essential information stays visible.
        parts = description.split("；") if "；" in description else [description]
        for j, part in enumerate(parts):
            c.text(x + 24, y + 83 + j * 39, part, 25, MUTED, width=692)
    c.text(36, 937, "素材语义", 32, GOLD)
    c.art("items", 1, 36, 1000, 110, 80)
    c.text(169, 1015, "已知装备：图标 + 名称", 27)
    c.rect(565, 1000, 110, 80, INSET)
    c.text(695, 1015, "空白：无装备或未提供", 27)
    c.rect(1093, 1000, 110, 80, INSET)
    c.text(1124, 1020, "?", 31, MUTED)
    c.text(1218, 1015, "缺图：保留 ID", 27)
    c.rule(1130)
    c.text(36, 1170, "管理与配置 · 沿用宿主现有配置入口", 32)
    c.text(36, 1238, "数据连接", 27, GOLD)
    c.text(310, 1238, "配置凭据 → 检查状态 → 查询一次", 27, MUTED)
    c.text(36, 1300, "图片与素材", 27, GOLD)
    c.text(310, 1300, "选择图片 / 文字 → 查看素材准备状态", 27, MUTED)
    c.text(36, 1362, "订阅播报", 27, GOLD)
    c.text(310, 1362, "默认关闭 → 管理员启用 → 用户创建订阅", 27, MUTED)
    return c.save()


def board(cards, name, title, subtitle, labels, height):
    c = Canvas(1720, height, name)
    c.text(44, 38, "Dota2Forge", 48, GOLD, serif=True)
    c.text(44, 116, title, 48)
    c.text(44, 190, subtitle, 28, MUTED)
    w = (1632 - 34 * (len(cards) - 1)) // len(cards)
    for i, (card, label) in enumerate(zip(cards, labels, strict=True)):
        x = 44 + i * (w + 34)
        c.text(x, 268, label, 29, GOLD)
        fitted = ImageOps.contain(card, (w, height - 400), Image.Resampling.LANCZOS)
        c.image.paste(fitted, (x, 330))
    c.text(
        44,
        height - 52,
        "设计提案 · 2026-10-11 · 全部统计为合成数据 · 尚未应用到运行插件",
        25,
        MUTED,
    )
    return c.save()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    menu_image = menu()
    player_image = player()
    recent_image = recent()
    items_image = items()
    report_image = report()
    team_image = team_detail()
    components_image = states()
    board(
        [menu_image, player_image, recent_image],
        "proposal-main",
        "远古锻炉 · 命令直达，结果优先",
        "石材与暗金属只承担氛围；大字、留白和明确命令承担阅读。",
        ["菜单 · 从目的开始", "玩家 · 先看段位", "战绩 · 一场一行"],
        1550,
    )
    board(
        [items_image, components_image],
        "proposal-components",
        "同一套视觉，覆盖所有回复",
        "装备使用真实本地素材；错误、缺失、配置与管理说明保持直接。",
        ["热门出装 · 统计分阶段", "状态与配置 · 结果 + 下一步"],
        1600,
    )
    board(
        [report_image, team_image],
        "proposal-reports",
        "比赛报告 · 保留全量，强化主次",
        "宽幅完整报告继续保留十人、全部指标与装备槽；不按手机比例删减。",
        ["总览 · 双方比较与走势", "队伍详情 · 五人完整数据"],
        2020,
    )
    record = {
        "purpose": "design preview only",
        "fixture": "synthetic; no real account or match identities",
        "network": "none in rendering",
        "production_code_changed": False,
        "manual_visual_review": "pending",
        "cards": CHECKS,
    }
    (ROOT / ".agents/artifacts/theme-redesign-v3/render-checks.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"output": str(OUT), "files": len(CHECKS), "bounds": "passed", "overlaps": "passed"},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
