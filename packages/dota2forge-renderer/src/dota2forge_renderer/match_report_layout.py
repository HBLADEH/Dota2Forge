"""Wide match overview, source advantage plots and complete team sheets."""

from typing import TYPE_CHECKING

from dota2forge_core import (
    MatchAnalysis,
    MatchDetail,
    MatchParseState,
    MatchParticipant,
    MatchReport,
    MetricSeries,
)

from .cards import REPORT_WIDTH, ImageArtifact, MatchReportCard, RenderError
from .engine import AMBER, GREEN, LINE, MUTED, PANEL, RED, WHITE, _Canvas
from .formatting import duration_text, game_mode_text, timestamp, value_text
from .reporting import (
    imp_text,
    lane_text,
    participant_name,
    participation_text,
    performance_evidence,
    position_text,
    report_groups,
)

if TYPE_CHECKING:
    from .engine import PillowRenderer


def kda(player: MatchParticipant) -> str:
    return "/".join(
        "?" if value is None else str(value)
        for value in (player.kills, player.deaths, player.assists)
    )


def report_header(canvas: _Canvas, report: MatchReport, label: str, page: int, pages: int) -> None:
    detail = report.detail
    assert isinstance(detail, MatchDetail)
    canvas.header(label, f"第 {page} / {pages} 页")
    canvas.text(38, 206, f"比赛 {report.match_id.value}", size=38, color=WHITE, width=570)
    canvas.text(
        640,
        214,
        f"{game_mode_text(detail.game_mode)} · {duration_text(detail.duration_seconds)}",
        width=920,
    )
    winner = (
        "胜方未知"
        if detail.did_radiant_win is None
        else "天辉胜利"
        if detail.did_radiant_win
        else "夜魇胜利"
    )
    canvas.text(38, 266, winner, size=34, color=GREEN if detail.did_radiant_win else RED, width=230)
    canvas.text(
        286,
        274,
        f"击杀 {value_text(report.team_total(True, 'kills'))} : "
        f"{value_text(report.team_total(False, 'kills'))}",
        width=330,
    )
    canvas.text(
        640,
        274,
        f"开始 {timestamp(detail.started_at)} · 版本 ID {value_text(detail.game_version_id)}",
        color=MUTED,
        width=920,
    )
    canvas.line(324)


def footer(canvas: _Canvas, report: MatchReport, y: int) -> None:
    detail = report.detail
    assert isinstance(detail, MatchDetail)
    canvas.metadata(y, detail.metadata)
    state = {
        MatchParseState.UNKNOWN: "未知",
        MatchParseState.UNPARSED: "未解析",
        MatchParseState.PARTIAL: "部分解析",
        MatchParseState.UPSTREAM_PARSED: "上游已标记解析",
    }.get(detail.parse_state, "未返回")
    marker = (
        f"OpenDota version {value_text(detail.parse_version)}"
        if report.metadata.source.value == "opendota"
        else f"isStats {'未知' if detail.has_stats is None else '是' if detail.has_stats else '否'}"
    )
    canvas.text(
        38,
        y + 138,
        f"{state} · {marker} · 解析时间 {timestamp(detail.parsed_at)}",
        color=MUTED,
    )
    canvas.text(
        38,
        y + 182,
        "STRATZ IMP：来源模型评分，非官方 MVP；无公开模型版本，统计依据不等于评分公式。",
        size=26,
        color=MUTED,
    )
    link = (
        f" · stratz.com/matches/{report.match_id.value}"
        if report.metadata.source.value == "stratz"
        else ""
    )
    canvas.text(38, y + 224, "仅比较本局可用分数 · 不推断缺失数据" + link, size=26, color=MUTED)
    canvas.text(
        38, y + 266, "空白装备槽：无装备或来源未提供；未知字段不补零。", size=26, color=MUTED
    )
    canvas.text(
        38,
        y + 308,
        f"分析抓取 {timestamp(report.analysis.metadata.fetched_at)} · 解析标记不证明字段完整。",
        size=26,
        color=MUTED,
    )


def table(
    canvas: _Canvas, report: MatchReport, label: str, team: tuple[MatchParticipant, ...], y: int
) -> int:
    color = GREEN if label == "天辉" else RED if label == "夜魇" else AMBER
    canvas.text(38, y, label, size=32, color=color, width=130)
    radiant = label == "天辉"
    summary = (
        f"净资产 {value_text(report.team_total(radiant, 'net_worth'))} · "
        f"英雄伤害 {value_text(report.team_total(radiant, 'hero_damage'))} · "
        f"建筑伤害 {value_text(report.team_total(radiant, 'tower_damage'))}"
        if label in {"天辉", "夜魇"}
        else "来源未提供阵营，团队合计未知"
    )
    canvas.text(190, y + 4, summary, color=MUTED)
    headings = (
        (38, "英雄 / 玩家", 308),
        (364, "位置", 104),
        (470, "IMP", 84),
        (560, "K/D/A", 132),
        (710, "参战率", 112),
        (836, "净资产", 130),
        (980, "GPM", 100),
        (1092, "伤害", 142),
        (1250, "建筑", 142),
        (1408, "治疗", 142),
    )
    y += 54
    for x, heading, width in headings:
        canvas.text(x, y, heading, size=26, color=MUTED, width=width)
    y += 42
    for player in team:
        canvas.draw.rectangle((28, y - 8, REPORT_WIDTH - 28, y + 78), fill=PANEL)
        canvas.draw.rectangle((28, y - 8, 32, y + 78), fill=color)
        canvas.illustration("heroes", player.hero_id, 38, y + 7, (74, 44))
        canvas.text(128, y, canvas.engine.hero(player.hero_id), size=26, width=218)
        name = participant_name(player)
        if report.tracked_account_id is not None and player.account_id == report.tracked_account_id:
            name = "[我方] " + name
        canvas.text(128, y + 38, name, size=26, color=MUTED, width=218)
        values = (
            (364, position_text(player.position), 104, MUTED),
            (
                470,
                imp_text(player),
                84,
                GREEN
                if player.imp is not None and player.imp > 0
                else RED
                if player.imp is not None and player.imp < 0
                else MUTED,
            ),
            (560, kda(player), 132, WHITE),
            (710, participation_text(report, player), 112, WHITE),
            (836, value_text(player.net_worth), 130, AMBER),
            (980, value_text(player.gold_per_minute), 100, AMBER),
            (1092, value_text(player.hero_damage), 142, WHITE),
            (1250, value_text(player.tower_damage), 142, WHITE),
            (1408, value_text(player.hero_healing), 142, WHITE),
        )
        for x, value, width, text_color in values:
            canvas.text(x, y + 20, value, size=26, color=text_color, width=width, truncate=False)
        y += 92
    return y + 24


def plot(
    canvas: _Canvas, series: MetricSeries | None, title: str, x: int, y: int, width: int
) -> None:
    canvas.text(x, y, title, size=30, width=width)
    if series is None or len(series.values) < 2:
        canvas.text(x, y + 100, "来源未提供足够的优势序列", color=MUTED, width=width)
        return
    values = series.values
    left, right, top, bottom = x + 90, x + width - 12, y + 102, y + 342
    scale = max(1, max(abs(value) for value in values))
    middle = (top + bottom) / 2
    for fraction in (-1, 0, 1):
        ordinate = middle - fraction * (bottom - top) / 2
        canvas.draw.line((left, ordinate, right, ordinate), fill=LINE, width=1)
        canvas.text(
            x, int(ordinate) - 12, f"{fraction * scale / 1000:.1f}k", size=26, color=MUTED, width=82
        )
    points = [
        (
            left + i * (right - left) / (len(values) - 1),
            middle - value * (bottom - top) / (2 * scale),
        )
        for i, value in enumerate(values)
    ]
    for before, after, value in zip(points, points[1:], values[1:], strict=False):
        canvas.draw.polygon(
            (before, after, (after[0], middle), (before[0], middle)),
            fill="#244437" if value >= 0 else "#492f2e",
        )
        canvas.draw.line((before, after), fill=GREEN if value >= 0 else RED, width=3)
    last = values[-1]
    end_minutes = (series.start_seconds + (len(values) - 1) * series.interval_seconds) / 60
    canvas.text(
        x,
        y + 42,
        f"最后区间 天辉 {last:+,} · 正值天辉 / 负值夜魇",
        color=GREEN if last >= 0 else RED,
        width=width,
    )
    canvas.text(left, y + 344, "-1:00", size=26, color=MUTED, width=160)
    canvas.text(right - 176, y + 344, f"{end_minutes:.0f}:00", size=26, color=MUTED, width=176)
    canvas.text(x, y + 390, "来源分钟区间；首样本为 -60～0 秒", size=26, color=MUTED, width=width)


def highlights(canvas: _Canvas, report: MatchReport, y: int) -> int:
    for x, title, selected, color in (
        (38, "表现突出 · IMP 最高正分", report.strong_performers, GREEN),
        (812, "表现偏弱 · IMP 最低负分", report.weak_performers, RED),
    ):
        canvas.text(x, y, title, size=30, color=color, width=746)
        if not selected:
            canvas.text(x, y + 64, "无对应可用分数，不推断", color=MUTED, width=746)
        for index, player in enumerate(selected):
            row_y = y + 62 + index * 130
            canvas.text(
                x,
                row_y,
                f"{canvas.engine.hero(player.hero_id)} · IMP {imp_text(player)}",
                size=30,
                color=color,
                width=360,
            )
            canvas.text(
                x + 376, row_y + 3, participant_name(player), size=26, color=MUTED, width=370
            )
            for line_index, line in enumerate(performance_evidence(report, player).splitlines()):
                canvas.text(x, row_y + 42 + line_index * 34, line, size=26, width=746)
    return y + 464


def overview(engine: "PillowRenderer", card: MatchReportCard, pages: int) -> ImageArtifact:
    report = card.report
    groups = report_groups(report)
    table_height = sum(120 + 92 * len(team) for _, team in groups)
    with _Canvas(engine, min(3200, 350 + table_height + 1480), width=REPORT_WIDTH) as canvas:
        report_header(canvas, report, "比赛全局分析", 1, pages)
        y = 352
        if not groups:
            canvas.text(
                38,
                y,
                "参赛者数据未知"
                if isinstance(report.detail, MatchDetail) and report.detail.players is None
                else "来源返回 0 名参赛者",
                color=MUTED,
            )
            y += 130
        for label, team in groups:
            y = table(canvas, report, label, team, y)
        metrics = (
            card.report.analysis.team_metrics
            if isinstance(card.report.analysis, MatchAnalysis)
            else ()
        )
        networth = next((metric for metric in metrics if "networth" in metric.semantic.value), None)
        experience = next(
            (metric for metric in metrics if "experience" in metric.semantic.value), None
        )
        plot(canvas, networth, "团队净资产优势", 38, y + 6, 746)
        plot(canvas, experience, "团队经验优势", 812, y + 6, 746)
        y = highlights(canvas, report, y + 460)
        canvas.text(
            38,
            y,
            f"IMP 可用 {len(report.imp_ranking)} 人 · 本局正/负分相对表现排序，缺失不补零。",
            color=MUTED,
        )
        footer(canvas, report, y + 56)
        return canvas.encode()


def team_sheet(engine: "PillowRenderer", card: MatchReportCard, pages: int) -> ImageArtifact:
    report = card.report
    label, team = report_groups(report)[card.page - 2]
    with _Canvas(engine, 720 + 430 * len(team), width=REPORT_WIDTH) as canvas:
        report_header(canvas, report, f"{label}详细数据", card.page, pages)
        y = 356
        for player in team:
            color = GREEN if player.is_radiant else RED
            canvas.line(y - 12)
            canvas.illustration("heroes", player.hero_id, 38, y + 4, (150, 86))
            own = (
                " [我方]"
                if report.tracked_account_id is not None
                and player.account_id == report.tracked_account_id
                else ""
            )
            canvas.text(
                212, y + 2, engine.hero(player.hero_id) + own, size=36, color=color, width=610
            )
            canvas.text(212, y + 50, participant_name(player), size=28, width=610)
            canvas.text(
                860,
                y + 2,
                f"STRATZ IMP {imp_text(player)}",
                size=36,
                color=GREEN
                if player.imp is not None and player.imp > 0
                else RED
                if player.imp is not None and player.imp < 0
                else MUTED,
                width=702,
            )
            canvas.text(
                860,
                y + 56,
                f"{position_text(player.position)} · {lane_text(player.lane)} · "
                f"K/D/A {kda(player)}",
                width=702,
            )
            metrics = (
                ("等级", value_text(player.level)),
                ("参战率", participation_text(report, player)),
                ("GPM", value_text(player.gold_per_minute)),
                ("XPM", value_text(player.experience_per_minute)),
                ("净资产", value_text(player.net_worth)),
                ("补刀 / 反补", f"{value_text(player.last_hits)} / {value_text(player.denies)}"),
                ("英雄伤害", value_text(player.hero_damage)),
                ("建筑伤害", value_text(player.tower_damage)),
                ("治疗量", value_text(player.hero_healing)),
            )
            for index, (name, value) in enumerate(metrics):
                x = 38 + index * 171
                canvas.text(x, y + 120, name, size=26, color=MUTED, width=163)
                canvas.text(
                    x,
                    y + 158,
                    value,
                    size=30,
                    color=AMBER if index in (2, 4) else WHITE,
                    width=163,
                    truncate=False,
                )
            canvas.text(38, y + 214, "装备", color=MUTED, width=104)
            canvas.text(956, y + 214, "背包", color=MUTED, width=104)
            canvas.text(1418, y + 214, "中立", color=MUTED, width=142)
            for slot, item_id in enumerate(
                (*player.item_ids, *player.backpack_ids, player.neutral_item_id)
            ):
                x = 38 + slot * 154
                canvas.illustration("items", item_id, x, y + 258, (136, 72))
                engine._item_label(canvas, item_id, x, y + 338, 136)
            y += 430
        footer(canvas, report, y + 16)
        return canvas.encode()


def render_report(engine: "PillowRenderer", card: MatchReportCard) -> ImageArtifact:
    pages = 1 + len(report_groups(card.report))
    if (
        not isinstance(card.report.detail, MatchDetail)
        or type(card.page) is not int
        or not 1 <= card.page <= pages
    ):
        raise RenderError()
    return overview(engine, card, pages) if card.page == 1 else team_sheet(engine, card, pages)
