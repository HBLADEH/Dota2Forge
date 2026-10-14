"""Offline planning layouts; synthetic content, no new production card or API."""

from __future__ import annotations

import io
import json
from pathlib import Path

from dota2forge_renderer import PillowRenderer
from dota2forge_renderer.engine import _Canvas
from dota2forge_renderer.theme import GOLD, GREEN, INSET, LINE, MUTED, PAPER, RED
from PIL import Image, ImageDraw

OUTPUT = Path(__file__).resolve().parent
HEIGHT = 1680
QA: dict[str, dict[str, object]] = {}


def text(canvas: _Canvas, x: int, y: int, value: str, **kwargs: object) -> None:
    canvas.text(x, y, value, truncate=False, **kwargs)


def shell(canvas: _Canvas, title: str, command: str) -> None:
    canvas.header(title, "规划草案 · 所有内容合成 · 功能尚未实现")
    canvas.command(208, command)


def footer(canvas: _Canvas, page: str) -> None:
    canvas.line(1504)
    text(canvas, 36, 1526, "布局示意 · 非实时统计 / 非真实比赛", color=GOLD, size=28)
    text(canvas, 36, 1570, "正式结果保留来源、版本、窗口与抓取时间", color=MUTED, size=26)
    text(canvas, 36, 1614, page, color=MUTED, size=26)


def export(canvas: _Canvas, name: str) -> None:
    artifact = canvas.encode()
    (OUTPUT / f"{name}.png").write_bytes(artifact.data)
    with (
        Image.open(io.BytesIO(artifact.data)) as source,
        source.resize((390, HEIGHT // 2), Image.Resampling.LANCZOS) as phone,
    ):
        phone.save(OUTPUT / f"{name}-phone.png")
    QA[name] = {
        "width": artifact.width,
        "height": artifact.height,
        "bytes": len(artifact.data),
        "text_boxes": len(canvas.boxes),
        "bounds_and_overlap_checked_by_canvas": True,
        "synthetic": True,
        "production_card_implemented": False,
    }


def meta(renderer: PillowRenderer) -> None:
    with _Canvas(renderer, HEIGHT) as canvas:
        shell(canvas, "版本强势英雄", "do强势 3号位 段位=传奇")
        canvas.panel(28, 274, 724, 146, GOLD)
        text(canvas, 48, 294, "补丁 X.Y · 3号位 · 传奇 · 全球", size=30)
        text(canvas, 48, 340, "当前补丁内近7天 · 模式与范围正式核实后显示", size=26, color=MUTED)
        text(canvas, 48, 380, "可靠胜率排序 · 至少1,000场（规则示意）", size=26, color=GOLD)

        rows = (
            ("斧王", "55.8%", "12,000场", "稳健样本"),
            ("半人马战行者", "54.9%", "9,800场", "稳健样本"),
            ("潮汐猎人", "54.2%", "8,400场", "稳健样本"),
            ("伐木机", "53.8%", "7,200场", "稳健样本"),
            ("玛尔斯", "53.1%", "6,000场", "稳健样本"),
        )
        for index, (hero, rate, matches, status) in enumerate(rows):
            y = 456 + index * 174
            canvas.panel(28, y, 724, 150, GREEN)
            canvas.draw.rectangle((48, y + 22, 96, y + 70), fill=INSET)
            text(canvas, 59, y + 28, str(index + 1), color=GOLD, size=32, width=30)
            text(canvas, 116, y + 24, hero, size=32, width=358)
            text(canvas, 540, y + 24, rate, size=38, color=GREEN, width=185)
            text(canvas, 116, y + 72, f"{matches} · {status} · 数值合成", size=26, color=MUTED)
            canvas.draw.rectangle((116, y + 124, 712, y + 130), fill=LINE)
            fill = float(rate.removesuffix("%")) / 100
            canvas.draw.rectangle((116, y + 124, 116 + round(596 * fill), y + 130), fill=GOLD)

        text(canvas, 36, 1354, "低样本单列观察；选择率无分母时不显示", size=28, color=MUTED)
        canvas.command(1426, "继续看构筑：do斧王攻略 3号位")
        footer(canvas, "第1页示意 · 正式榜单按同一筛选分页")
        export(canvas, "hero-meta")


def guide(renderer: PillowRenderer) -> None:
    with _Canvas(renderer, HEIGHT) as canvas:
        shell(canvas, "英雄数据攻略", "do主宰攻略 1号位")
        canvas.panel(28, 274, 724, 124, GOLD)
        text(canvas, 48, 294, "主宰 · 1号位 · 补丁 X.Y（示意）", size=34)
        text(canvas, 48, 348, "统计构筑与单场样例分开展示，分母各自保留", size=26, color=MUTED)

        sections = (
            ("出门 / 早期", ("补给", "魔棒", "动力鞋")),
            ("核心物品带（仅布局示例）", ("狂战斧", "幻影斧", "蝴蝶")),
        )
        for index, (title, items) in enumerate(sections):
            y = 436 + index * 240
            canvas.panel(28, y, 724, 212, GOLD)
            text(canvas, 48, y + 20, title, size=30, color=GOLD)
            for column, item in enumerate(items):
                x = 48 + column * 232
                canvas.draw.rectangle((x, y + 76, x + 206, y + 164), fill=INSET)
                text(canvas, x + 16, y + 94, item, size=30, width=182)
            text(
                canvas, 48, y + 174, "正式展示图标、购买计数与已核实相关统计", size=26, color=MUTED
            )

        canvas.panel(28, 942, 724, 212, GREEN)
        text(canvas, 48, 962, "样例加点 · 完整顺序与统计独立", size=30, color=GOLD)
        skills = ("Q", "W", "Q", "E", "Q", "R", "Q", "E", "E")
        for index, skill in enumerate(skills):
            x = 48 + index * 76
            text(canvas, x + 15, 1013, str(index + 1), size=26, color=MUTED, width=52)
            canvas.draw.rectangle((x, 1056, x + 60, 1109), fill=INSET)
            text(canvas, x + 15, 1066, skill, size=30, color=GREEN, width=44)

        canvas.panel(28, 1184, 724, 166, GOLD)
        text(canvas, 48, 1204, "天赋 / 命石 / 备选构筑", size=30, color=GOLD)
        text(canvas, 48, 1256, "天赋按实际选择及独立样本展示", size=28)
        text(canvas, 48, 1300, "命石未核实就标缺失，不按装备猜分支", size=26, color=MUTED)
        canvas.command(1426, "展开统计与单场样例：do主宰攻略 1号位 详细")
        footer(canvas, "信息层次合成示意 · 正式摘要分构筑 / 加点两页")
        export(canvas, "hero-guide")


def review(renderer: PillowRenderer) -> None:
    with _Canvas(renderer, HEIGHT) as canvas:
        shell(canvas, "AI 比赛复盘", "do复盘 <比赛ID> 拉比克")
        canvas.panel(28, 274, 724, 154, GOLD)
        text(canvas, 48, 294, "拉比克 · 4号位 · 合成比赛", size=34)
        text(canvas, 48, 350, "结算 / 购买 / 分钟经济可用", size=28, color=GREEN)
        text(canvas, 48, 392, "团战与死亡事件未提供，不推断具体过程", size=26, color=MUTED)

        canvas.panel(28, 466, 724, 260, GREEN)
        text(canvas, 48, 488, "数据事实", size=30, color=GREEN)
        text(canvas, 48, 544, "10:00  净资产 3,180 · 分钟快照 [E1]", size=28)
        text(canvas, 48, 600, "14:00  购买原力法杖 · 购买记录 [E2]", size=28)
        text(canvas, 48, 656, "20:00  净资产 6,240 · 分钟快照 [E3]", size=28)

        canvas.panel(28, 758, 724, 246, GOLD)
        text(canvas, 48, 780, "经济走势（数值全部合成）", size=30, color=GOLD)
        points = [
            (58, 953),
            (140, 937),
            (222, 913),
            (304, 900),
            (386, 873),
            (468, 857),
            (550, 846),
            (680, 834),
        ]
        canvas.draw.line((58, 958, 708, 958), fill=LINE, width=2)
        canvas.draw.line(points, fill=GREEN, width=4)
        for x, y in (points[0], points[3], points[-1]):
            canvas.draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=GOLD)
        text(canvas, 48, 964, "正式曲线保留来源、单位与采样区间", size=26, color=MUTED)

        canvas.panel(28, 1036, 724, 176, GOLD)
        text(canvas, 48, 1058, "AI 判断 · 推断 [E1 / E2 / E3]", size=30, color=GOLD)
        text(canvas, 48, 1112, "结合功能装购入节点检查中期节奏。", size=28)
        text(canvas, 48, 1164, "缺少事件记录，不能确认团战或站位原因。", size=26, color=MUTED)

        canvas.panel(28, 1244, 724, 148, RED)
        text(canvas, 48, 1266, "下一局 · 有触发条件的行动建议", size=30, color=GOLD)
        text(canvas, 48, 1324, "威胁上升时，先检查保命 / 功能装需求。", size=28)
        text(canvas, 36, 1432, "可继续问：展开出装依据 / 解释经济变化", size=28, color=MUTED)
        footer(canvas, "摘要示意 · 详细版分事实 / 判断 / 建议多页")
        export(canvas, "match-review")


def overview(renderer: PillowRenderer) -> None:
    with Image.new("RGB", (1226, 974), PAPER) as combined:
        draw = ImageDraw.Draw(combined)
        draw.text((16, 18), "Dota2Forge · 三项功能卡片布局草案", font=renderer.font(30), fill=GOLD)
        draw.text(
            (16, 66),
            "全部内容合成，功能尚未实现；完整图见同目录。",
            font=renderer.font(26),
            fill=MUTED,
        )
        for index, name in enumerate(("hero-meta", "hero-guide", "match-review")):
            with Image.open(OUTPUT / f"{name}-phone.png") as sample:
                combined.paste(sample, (16 + index * 402, 118))
        combined.save(OUTPUT / "overview.png", optimize=True)


def main() -> None:
    renderer = PillowRenderer()
    try:
        renderer._load()
        meta(renderer)
        guide(renderer)
        review(renderer)
        overview(renderer)
    finally:
        renderer.close()
    (OUTPUT / "qa.json").write_text(
        json.dumps(QA, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(QA, ensure_ascii=False))


if __name__ == "__main__":
    main()
