"""Forge cards for hero observations and focused review figures, all local."""

from typing import TYPE_CHECKING

from dota2forge_core import ReviewChartKind, chart_data
from dota2forge_core.review import participant_analysis

from .cards import (
    GuideSampleCard,
    HeroGuideCard,
    HeroMetaCard,
    ImageArtifact,
    RenderError,
    ReviewDataCard,
)
from .engine import _Canvas
from .features import (
    RANK_LABELS,
    clock_text,
    feature_text,
    guide_pages,
    item_bucket_text,
    popular_items,
    sample_summary,
)
from .formatting import duration_text
from .hero_items import item_card_name
from .theme import GOLD, GREEN, LINE, MUTED, RED, WHITE

if TYPE_CHECKING:
    from .engine import PillowRenderer


def wrapped_lines(engine: "PillowRenderer", values: list[str], width: int, size: int) -> list[str]:
    lines = []
    font = engine.font(size)
    for value in values:
        line = ""
        for char in engine.display(value):
            if line and font.getlength(line + char) > width:
                lines.append(line)
                line = ""
            line += char
        lines.append(line)
    return lines


def render_feature(
    engine: "PillowRenderer", card: HeroMetaCard | HeroGuideCard | GuideSampleCard
) -> ImageArtifact:
    text = feature_text(card)  # Validates page before any drawing.
    if isinstance(card, HeroMetaCard):
        ranking = card.ranking
        snap = ranking.snapshot
        notes = wrapped_lines(engine, list(snap.notes), 708, 26)
        footer_y = 1182 + len(notes) * 34 + 16
        with _Canvas(engine, footer_y + 170) as c:
            c.header(
                "版本强势英雄",
                f"版本 {snap.patch.name} · {RANK_LABELS[snap.request.rank]} · 第{card.page}页",
            )
            c.text(
                36,
                210,
                f"{snap.window_start:%m-%d}–{snap.window_end:%m-%d} UTC · 天梯全选",
                color=GOLD,
            )
            c.text(36, 258, "胜率 / 95%保守胜率 / 观察场次", color=MUTED)
            entries = ranking.entries[(card.page - 1) * 5 : card.page * 5]
            for i, row in enumerate(entries):
                y = 320 + i * 150
                c.panel(28, y, 724, 130, GOLD)
                c.icon("heroes", row.hero_id, 44, y + 18, (76, 76))
                c.text(
                    134,
                    y + 16,
                    f"{row.position}号位 · {engine.hero(row.hero_id)}",
                    size=32,
                    width=590,
                )
                c.text(
                    134,
                    y + 70,
                    f"{(row.win_rate or 0):.1%} / {row.reliability:.1%} / {row.matches:,} 场",
                    color=GREEN,
                    width=590,
                )
            if not entries:
                c.paragraph(340, "没有达到最低样本量的可用英雄，暂不能给出强势榜。")
            c.text(
                36,
                1090,
                f"最低 {snap.request.minimum_matches} 场 · {ranking.observing} 项继续观察",
                color=GOLD,
            )
            c.text(36, 1134, "默认按 Wilson 95%下界；不保证个人上分。", color=MUTED)
            for i, note in enumerate(notes):
                c.text(36, 1182 + i * 34, note, size=26, color=MUTED, truncate=False)
            c.metadata(footer_y, snap.metadata)
            return c.encode()
    sample = (
        card.sample
        if isinstance(card, GuideSampleCard)
        else (card.guide.samples[0] if card.guide.samples else None)
    )
    page = card.page if isinstance(card, GuideSampleCard) else (1 if card.page == 2 else 2)
    if isinstance(card, HeroGuideCard) and card.page in (1, 4):
        lines = text.splitlines()
        icons = (
            {item_bucket_text(v): v.item_id for v in popular_items(card.guide)}
            if card.page == 1
            else {}
        )
        rows = [
            (row, icons.get(line) if index == 0 else None, bool(icons.get(line)))
            for line in lines[1:-2]
            for index, row in enumerate(
                wrapped_lines(engine, [line], 600 if line in icons else 660, 28)
            )
        ]
        panel_height = max(170, 40 * len(rows) + 44)
        footer_y = 204 + panel_height + 16
        pages = guide_pages(card.guide, card.detailed)
        ordinal = pages.index(card.page) + 1 if card.page in pages else card.page
        with _Canvas(engine, footer_y + 170) as c:
            c.header(
                card.guide.hero.display_name + "攻略",
                f"{card.guide.position}号位 · 第 {ordinal}/{len(pages)} 页",
            )
            c.panel(28, 204, 724, panel_height)
            # All source status is also present in the complete text fallback.
            for i, (line, icon, inset) in enumerate(rows):
                if icon:
                    c.icon("items", icon, 44, 226 + i * 40, (48, 36))
                c.text(
                    104 if inset else 44,
                    226 + i * 40,
                    line,
                    color=GOLD if i == 0 else WHITE,
                    width=600 if inset else 660,
                    truncate=False,
                )
            c.metadata(footer_y, card.guide.metadata)
            return c.encode()
    if sample is None:
        assert isinstance(card, HeroGuideCard)
        with _Canvas(engine, 560) as c:
            c.header("攻略样例暂不可用", "来源本次未返回可用样例")
            c.paragraph(
                230, "可用 do攻略样例 <比赛ID> <英雄> 查询指定比赛；不生成未知加点或出装顺序。"
            )
            c.metadata(390, card.guide.metadata)
            return c.encode()
    with _Canvas(engine, 1780) as c:
        c.header("真实攻略样例", "升级顺序与购买时间 · 单场观察")
        for i, line in enumerate(sample_summary(sample)[:3]):
            c.text(36, 210 + i * 44, line, color=GOLD if i == 0 else WHITE)
        if page == 1:
            c.text(36, 354, "记录序号 ≠ 英雄等级；阶数从 0 起。", color=GOLD)
            events = sample.upgrades
            if events is None:
                c.text(36, 420, "技能升级记录未知", color=MUTED)
            else:
                # Three columns allow complete localized talent names on two lines.
                for i, event in enumerate(events[:24]):
                    x, y = 28 + (i % 3) * 244, 414 + (i // 3) * 120
                    c.panel(x, y, 236, 112)
                    c.text(
                        x + 9,
                        y + 10,
                        f"#{i + 1} 阶{event.source_level}",
                        size=26,
                        color=GOLD,
                        width=126,
                    )
                    c.text(
                        x + 132,
                        y + 10,
                        clock_text(event.time_seconds),
                        size=26,
                        color=MUTED,
                        width=94,
                    )
                    label = ("天赋：" if event.is_talent else "") + (
                        event.name
                        or ("未标识技能" if event.ability_id == 0 else f"ID {event.ability_id}")
                    )
                    name_rows = wrapped_lines(engine, [label], 218, 26)
                    if len(name_rows) > 2:
                        raise RenderError()
                    for index, skill_row in enumerate(name_rows):
                        c.text(
                            x + 9,
                            y + 46 + index * 30,
                            skill_row,
                            size=26,
                            width=218,
                            truncate=False,
                        )
                c.text(
                    36,
                    1370,
                    f"展示 {min(len(events), 24)}/{len(events)} 条；技能阶数保留源值。",
                    color=MUTED,
                )
            c.text(36, 1420, "本局最终装备 · 来源快照", color=GOLD)
            for i, item in enumerate(sample.player.item_ids):
                x = 36 + i * 120
                if item:
                    c.icon("items", item, x, 1470, (56, 56))
                c.text(
                    x,
                    1530,
                    "未知" if item is None else "空槽" if item == 0 else item_card_name(item),
                    size=26,
                    width=108,
                )
        else:
            c.text(36, 354, "购买记录：赛前负时间，重复与组件均保留", color=GOLD)
            if sample.purchases is None:
                c.text(36, 420, "购买记录未知", color=MUTED)
            else:
                for i, purchase in enumerate(sample.purchases[:32]):
                    x, y = 28 + (i % 2) * 369, 414 + (i // 2) * 62
                    c.panel(x, y, 354, 54)
                    c.text(
                        x + 10,
                        y + 10,
                        clock_text(purchase.time_seconds),
                        size=26,
                        color=GOLD,
                        width=86,
                    )
                    c.text(
                        x + 154,
                        y + 10,
                        item_card_name(purchase.item_id)
                        if purchase.item_id
                        else purchase.item_key or "未知",
                        size=26,
                        width=190,
                    )
                    if purchase.item_id:
                        c.icon("items", purchase.item_id, x + 104, y + 9, (42, 36))
                c.text(
                    36,
                    1426,
                    f"展示 {min(32, len(sample.purchases))}/{len(sample.purchases)} 条购买记录。",
                    color=MUTED,
                )
            c.text(
                36,
                1480,
                "中立快照："
                + (
                    "未知"
                    if sample.player.neutral_item_id is None
                    else "空槽"
                    if sample.player.neutral_item_id == 0
                    else item_card_name(sample.player.neutral_item_id)
                ),
                color=GOLD,
            )
            c.text(36, 1525, "购买记录不能重建任意时刻库存。", color=MUTED)
        c.metadata(1600, sample.metadata)
        return c.encode()


def render_review_data(engine: "PillowRenderer", card: ReviewDataCard) -> ImageArtifact:
    chart_data(card.evidence, card.request)  # Validate duration and whitelisted semantics.
    evidence, request = card.evidence, card.request
    player = participant_analysis(evidence)
    with _Canvas(engine, 1180) as c:
        label = {
            ReviewChartKind.ECONOMY: "个人经济走势",
            ReviewChartKind.TEAM_ADVANTAGE: "双方优势走势",
            ReviewChartKind.ITEMS: "装备购买记录",
        }[request.kind]
        c.header(label, f"比赛 {evidence.detail.match_id.value} · 数据补充")
        c.text(
            36,
            210,
            f"{clock_text(request.start_seconds)}–{clock_text(request.end_seconds)} · "
            f"时长 {duration_text(evidence.detail.duration_seconds)}",
            color=GOLD,
        )
        c.panel(28, 280, 724, 660)
        if request.kind == ReviewChartKind.ITEMS:
            purchases = (
                ()
                if player is None
                else tuple(
                    p
                    for p in player.purchases or ()
                    if request.start_seconds <= p.time_seconds <= request.end_seconds
                )
            )
            for i, p in enumerate(purchases[:12]):
                if p.item_id:
                    c.icon("items", p.item_id, 150, 304 + i * 46, (42, 36))
                c.text(
                    44,
                    308 + i * 46,
                    clock_text(p.time_seconds),
                    width=96,
                    color=GOLD,
                )
                c.text(
                    206,
                    308 + i * 46,
                    item_card_name(p.item_id) if p.item_id else p.item_key or "未知",
                    width=518,
                )
            c.text(
                36,
                965,
                f"展示 {min(12, len(purchases))}/{len(purchases)} 条；购买不等于库存。",
                color=MUTED,
            )
            if not purchases:
                c.text(44, 310, "该区间没有可用购买记录（不补造）。", color=MUTED)
        else:
            series = (
                (() if player is None else player.metrics)
                if request.kind == ReviewChartKind.ECONOMY
                else (() if evidence.analysis is None else evidence.analysis.team_metrics)
            )
            for index, metric in enumerate(series[:2]):
                points = [
                    (metric.start_seconds + i * metric.interval_seconds, v)
                    for i, v in enumerate(metric.values)
                    if request.start_seconds
                    <= metric.start_seconds + i * metric.interval_seconds
                    <= request.end_seconds
                ]
                y = 310 + index * 304
                if not points:
                    continue
                low, high = min(v for _, v in points), max(v for _, v in points)
                semantic = {
                    "networth_level": "个人净资产（金）",
                    "collected_gold": "累计获得金币",
                    "experience_total": "累计经验",
                    "radiant_networth_lead": "天辉净资产优势（金）",
                    "radiant_experience_lead": "天辉经验优势（经验）",
                }[metric.semantic.value]
                c.text(44, y, semantic, color=GOLD, width=500)
                c.text(540, y, f"{low}..{high}", size=26, color=MUTED, width=190)
                coordinates = [
                    (
                        56
                        + (t - request.start_seconds)
                        / (request.end_seconds - request.start_seconds)
                        * 660,
                        y + 240 - (v - low) / max(1, high - low) * 180,
                    )
                    for t, v in points
                ]
                c.draw.line((56, y + 244, 716, y + 244), fill=LINE, width=2)
                if len(coordinates) > 1:
                    c.draw.line(coordinates, fill=GREEN if index == 0 else RED, width=4)
                else:
                    x, point_y = coordinates[0]
                    c.draw.ellipse((x - 4, point_y - 4, x + 4, point_y + 4), fill=GREEN)
                c.text(44, y + 256, clock_text(points[0][0]), size=26, color=MUTED, width=170)
                c.text(540, y + 256, clock_text(points[-1][0]), size=26, color=MUTED, width=170)
            if not series:
                c.text(44, 310, "所需曲线未返回；继续使用文字事实。", color=MUTED)
            c.text(36, 965, "曲线仅为来源观察，不证明操作或因果。", color=MUTED)
        c.metadata(1010, evidence.detail.metadata)
        return c.encode()
