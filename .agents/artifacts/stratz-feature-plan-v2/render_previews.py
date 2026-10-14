"""Synthetic offline drafts for guide samples and conversational review."""

from __future__ import annotations

import io
import json
from pathlib import Path

from dota2forge_renderer import PillowRenderer
from dota2forge_renderer.engine import _Canvas
from dota2forge_renderer.theme import GOLD, GREEN, INSET, LINE, MUTED, PAPER, RED
from PIL import Image, ImageDraw

OUTPUT = Path(__file__).resolve().parent
QA: dict[str, dict[str, object]] = {}


def text(canvas: _Canvas, x: int, y: int, value: str, **kwargs: object) -> None:
    canvas.text(x, y, value, truncate=False, **kwargs)


def shell(canvas: _Canvas, title: str, prompt: str) -> None:
    canvas.header(title, "规划草案 · 全部内容合成 · 功能尚未实现")
    canvas.command(208, prompt)


def footer(canvas: _Canvas, note: str) -> None:
    y = canvas.image.height - 176
    canvas.line(y)
    text(canvas, 36, y + 22, "合成布局示例 · 非真实战绩 / 非已实现功能", size=26, color=GOLD)
    text(canvas, 36, y + 66, note, size=26, color=MUTED)
    text(canvas, 36, y + 110, "正式卡保留对象、来源、版本与字段缺口", size=26, color=MUTED)


def export(canvas: _Canvas, name: str) -> None:
    artifact = canvas.encode()
    (OUTPUT / f"{name}.png").write_bytes(artifact.data)
    with (
        Image.open(io.BytesIO(artifact.data)) as source,
        source.resize((390, artifact.height // 2), Image.Resampling.LANCZOS) as phone,
    ):
        phone.save(OUTPUT / f"{name}-phone.png")
    QA[name] = {
        "width": artifact.width,
        "height": artifact.height,
        "bytes": len(artifact.data),
        "text_boxes": len(canvas.boxes),
        "bounds_and_overlap_checked_by_canvas": True,
        "synthetic": True,
        "production_feature_implemented": False,
    }


def sample_header(canvas: _Canvas) -> None:
    canvas.panel(28, 274, 724, 132, GOLD)
    text(canvas, 48, 294, "拉比克 · 2号位 · 天辉（合成样例）", size=32)
    text(canvas, 48, 344, "KDA 8 / 4 / 14 · IMP +12 · 时长35:00", size=28)
    text(canvas, 48, 382, "单场实际行为与聚合攻略分开，补丁 X.Y 为示意", size=26, color=MUTED)


def skill_grid(canvas: _Canvas, y: int, first: int, last: int) -> None:
    canvas.panel(28, y, 724, 408, GOLD)
    text(canvas, 48, y + 20, f"{first}-{last}级 · 实际升级记录网格的布局示意", size=28, color=GOLD)
    rows = (
        ("技能 Q", "Q", (1, 3, 5, 7)),
        ("技能 W", "W", (2, 4, 8, 9)),
        ("技能 E", "E", (11, 13, 14, 16)),
        ("大招 R", "R", (6, 12, 18)),
        ("天赋", "T", (10, 15, 20, 25)),
        ("属性", "+", (17, 19, 21, 22, 23, 24)),
    )
    for level in range(first, last + 1):
        x = 184 + (level - first) * 42
        value = str(level)
        label_width = canvas.draw.textlength(value, font=canvas.engine.font(26))
        text(canvas, x + round((36 - label_width) / 2), y + 70, value, size=26, width=38)
    for index, (label, symbol, levels) in enumerate(rows):
        row_y = y + 116 + index * 46
        text(canvas, 48, row_y + 4, label, size=26, color=MUTED, width=116)
        for level in range(first, last + 1):
            x = 184 + (level - first) * 42
            canvas.draw.rectangle((x, row_y, x + 36, row_y + 36), fill=INSET)
            if level in levels:
                text(canvas, x + 6, row_y + 4, symbol, size=26, color=GREEN, width=30)


def guide_skills(renderer: PillowRenderer) -> None:
    with _Canvas(renderer, 1680) as canvas:
        shell(canvas, "单场攻略样例 · 加点", "do攻略样例 <比赛ID> 拉比克")
        sample_header(canvas)
        skill_grid(canvas, 436, 1, 13)
        skill_grid(canvas, 878, 14, 25)
        text(canvas, 36, 1322, "等级语义核实后才排网格；特殊技能按实际行扩展", size=26, color=MUTED)
        text(canvas, 36, 1370, "本图字母代替图标，全部升级选择为合成示例", size=26, color=MUTED)
        canvas.command(1438, "下一页：分组购买时间线与来源装备快照")
        footer(canvas, "样例第1页 · 26-30级 / 特殊记录可在详细页扩展")
        export(canvas, "guide-sample-skills")


def item_strip(canvas: _Canvas, y: int, pairs: tuple[tuple[str, str], ...]) -> None:
    for index, (name, when) in enumerate(pairs):
        x = 48 + index * 232
        canvas.draw.rectangle((x, y, x + 206, y + 78), fill=INSET)
        text(canvas, x + 14, y + 20, name, size=28, width=180)
        text(canvas, x + 14, y + 92, when, size=28, color=GREEN, width=180)


def guide_items(renderer: PillowRenderer) -> None:
    with _Canvas(renderer, 1680) as canvas:
        shell(canvas, "单场攻略样例 · 装备", "来源装备快照 + 实际事件时间线")
        sample_header(canvas)
        canvas.panel(28, 436, 724, 234, GOLD)
        text(canvas, 48, 456, "来源装备快照（合成）", size=30, color=GOLD)
        for index, item in enumerate(("秘法鞋", "魔棒", "闪烁匕首", "原力法杖", "以太之镜", "A杖")):
            x = 48 + (index % 3) * 232
            y = 516 + (index // 3) * 64
            canvas.draw.rectangle((x, y, x + 206, y + 50), fill=INSET)
            text(canvas, x + 14, y + 12, item, size=28, width=180)
        text(canvas, 48, 634, "背包 / 中立槽按来源返回值展示", size=26, color=MUTED)

        canvas.panel(28, 702, 724, 220, GOLD)
        text(canvas, 48, 722, "主要装备 · 购买事件示意节选", size=30, color=GOLD)
        item_strip(canvas, 780, (("闪烁匕首", "12:00"), ("原力法杖", "18:00"), ("A杖", "31:00")))

        canvas.panel(28, 954, 724, 220, GREEN)
        text(canvas, 48, 974, "补给 · 保留负数赛前时间与重复购买", size=28, color=GOLD)
        item_strip(
            canvas, 1032, (("补给", "赛前 -01:00"), ("侦查守卫", "05:00"), ("回城卷轴", "15:00"))
        )

        canvas.panel(28, 1206, 724, 158, RED)
        text(canvas, 48, 1228, "中立物品 · 获得事件未提供（示意）", size=28, color=GOLD)
        text(canvas, 48, 1284, "最终中立槽不能证明获得时刻。", size=28)
        text(canvas, 48, 1328, "缺项如实显示；不补成购买事件。", size=26, color=MUTED)
        text(canvas, 36, 1428, "购买列表不能还原出售 / 合成 / 消耗后的库存", size=26, color=MUTED)
        footer(canvas, "样例第2页 · 任意时刻库存需额外数据，图片无滑块")
        export(canvas, "guide-sample-items")


def review_data(renderer: PillowRenderer) -> None:
    with _Canvas(renderer, 1120) as canvas:
        shell(canvas, "经济数据补图", "对话中按需：画出10-20分钟经济")
        canvas.panel(28, 274, 724, 142, GOLD)
        text(canvas, 48, 294, "当前复盘 · 拉比克 · 2号位（合成）", size=30)
        text(canvas, 48, 348, "分钟净资产快照 · 单位：金币", size=28, color=GREEN)
        text(canvas, 48, 390, "仅补充数据，解释与建议继续在聊天里", size=26, color=MUTED)

        canvas.panel(28, 448, 724, 384, GOLD)
        text(canvas, 48, 464, "净资产变化（全部数值合成）", size=28, color=GOLD)
        for value in (3000, 5000, 7000):
            y = 770 - round((value - 3000) / 4000 * 250)
            text(canvas, 48, y - 12, f"{value // 1000}k", size=26, color=MUTED, width=48)
            canvas.draw.line((104, y, 714, y), fill=LINE, width=1)
        values = (3400, 3520, 3900, 4270, 4570, 4850, 5080, 5290, 5550, 6100, 6450)
        points = [
            (104 + index * 61, 770 - round((value - 3000) / 4000 * 250))
            for index, value in enumerate(values)
        ]
        canvas.draw.line(points, fill=GREEN, width=4)
        for x, y in points:
            canvas.draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=GOLD)
        for x, label in ((104, "10分"), (409, "15分"), (670, "20分")):
            text(canvas, x, 792, label, size=26, color=MUTED, width=70)
        text(canvas, 36, 872, "同一比赛 / 主题 / 区间默认不重复发图", size=28, color=MUTED)
        footer(canvas, "单张按需补图示意 · 缺序列时只说明缺口，不作图")
        export(canvas, "review-data")


def bubble(canvas: _Canvas, y: int, value: str, *, user: bool) -> None:
    x = 156 if user else 28
    width = 596 if user else 724
    canvas.panel(x, y, width, 66, GOLD if user else GREEN)
    text(canvas, x + 20, y + 20, value, size=28, width=width - 40)


def conversation(renderer: PillowRenderer) -> None:
    with _Canvas(renderer, 1680) as canvas:
        shell(canvas, "一场比赛，连续聊下去", "文字为主 · 追问沿用对象 · 需要时才补图")
        bubble(canvas, 284, "复盘 <比赛ID>，我是拉比克。", user=True)
        canvas.panel(28, 380, 724, 108, GREEN)
        text(canvas, 48, 400, "已核实当前比赛和英雄，先给简短发现。", size=28)
        text(canvas, 48, 446, "数据缺口说明后，围绕你想看的部分展开。", size=26, color=MUTED)

        bubble(canvas, 520, "我对线的问题在哪里？", user=True)
        bubble(canvas, 616, "沿用同局证据，只展开对线，不重输ID。", user=False)
        bubble(canvas, 712, "先跳刀还是先推推？", user=True)
        bubble(canvas, 808, "结合这局威胁和实际购买解释选择。", user=False)
        bubble(canvas, 904, "把10到20分钟经济画出来。", user=True)

        canvas.panel(28, 1000, 724, 226, GREEN)
        text(canvas, 48, 1020, "按需补一张图，再继续用文字解释。", size=28)
        text(canvas, 48, 1064, "净资产 · 分钟快照 · 曲线合成示意", size=26, color=MUTED)
        canvas.draw.line((56, 1198, 710, 1198), fill=LINE, width=1)
        canvas.draw.line(
            ((56, 1184), (170, 1174), (284, 1152), (398, 1136), (512, 1128), (710, 1108)),
            fill=GREEN,
            width=4,
        )

        bubble(canvas, 1258, "结合图，我下一局怎么改？", user=True)
        canvas.panel(28, 1354, 724, 108, GREEN)
        text(canvas, 48, 1374, "继续解释当前问题，给有触发条件的建议。", size=28)
        text(canvas, 48, 1420, "保留比赛定位；不重发图或输出整篇报告。", size=26, color=MUTED)
        footer(canvas, "交互顺序合成示意 · 首选宿主原生会话，报告可选")
        export(canvas, "conversation")


def overview(renderer: PillowRenderer) -> None:
    with Image.new("RGB", (1226, 974), PAPER) as combined:
        draw = ImageDraw.Draw(combined)
        draw.text(
            (16, 18), "Dota2Forge · 攻略样例与多轮复盘补充草案", font=renderer.font(30), fill=GOLD
        )
        draw.text(
            (16, 66),
            "全部内容合成，功能尚未实现；补图详情另附。",
            font=renderer.font(26),
            fill=MUTED,
        )
        for index, name in enumerate(("guide-sample-skills", "guide-sample-items", "conversation")):
            with Image.open(OUTPUT / f"{name}-phone.png") as sample:
                combined.paste(sample, (16 + index * 402, 118))
        combined.save(OUTPUT / "overview.png", optimize=True)


def main() -> None:
    renderer = PillowRenderer()
    try:
        renderer._load()
        guide_skills(renderer)
        guide_items(renderer)
        review_data(renderer)
        conversation(renderer)
        overview(renderer)
    finally:
        renderer.close()
    (OUTPUT / "qa.json").write_text(
        json.dumps(QA, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(QA, ensure_ascii=False))


if __name__ == "__main__":
    main()
