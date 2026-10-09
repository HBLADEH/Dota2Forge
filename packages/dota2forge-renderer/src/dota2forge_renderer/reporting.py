"""Shared match report labels and complete text observations."""

import json
from functools import lru_cache
from importlib.resources import files

from dota2forge_core import MatchAnalysis, MatchDetail, MatchParticipant, MatchReport

from .formatting import duration_text, game_mode_text, safe_name, timestamp, value_text
from .hero_items import item_name
from .match_details import participant_items_text, participant_stats_text


def report_groups(report: MatchReport) -> tuple[tuple[str, tuple[MatchParticipant, ...]], ...]:
    if not isinstance(report.detail, MatchDetail):
        return ()
    groups = []
    for side, label in ((True, "天辉"), (False, "夜魇"), (None, "阵营未知")):
        positions = {f"POSITION_{index}": index for index in range(1, 6)}
        team = tuple(
            sorted(
                (player for player in report.detail.players or () if player.is_radiant is side),
                key=lambda player: (
                    positions.get(player.position or "", 6),
                    player.player_slot if player.player_slot is not None else 256,
                ),
            )
        )
        for offset in range(0, len(team), 5):
            groups.append((label, team[offset : offset + 5]))
    return tuple(groups)


def participant_name(player: MatchParticipant) -> str:
    if player.is_anonymous is True:
        return "匿名参赛者"
    if player.account_id is None:
        return "身份未知"
    return safe_name(player.display_name)


@lru_cache(maxsize=1)
def hero_names() -> dict[int, str]:
    data = json.loads(
        files("dota2forge_renderer").joinpath("assets/v1/heroes.json").read_text("utf-8")
    )
    return {row["id"]: row["name_loc"] for row in data["heroes"]}


def hero_name(player: MatchParticipant) -> str:
    return hero_names().get(player.hero_id or 0, f"英雄 ID {value_text(player.hero_id)}")


def position_text(value: str | None) -> str:
    return {
        "POSITION_1": "1号位",
        "POSITION_2": "2号位",
        "POSITION_3": "3号位",
        "POSITION_4": "4号位",
        "POSITION_5": "5号位",
        "UNKNOWN": "未知",
        "FILTERED": "未知",
        "ALL": "未知",
    }.get(value or "", value or "未知")


def lane_text(value: str | None) -> str:
    return {
        "SAFE_LANE": "优势路",
        "MID_LANE": "中路",
        "OFF_LANE": "劣势路",
        "ROAMING": "游走",
        "JUNGLE": "野区",
        "UNKNOWN": "未知",
    }.get(value or "", value or "未知")


def imp_text(player: MatchParticipant) -> str:
    return "未知" if player.imp is None else f"{player.imp:+d}"


def participation_text(report: MatchReport, player: MatchParticipant) -> str:
    value = report.participation(player)
    return "未知" if value is None else f"{value:.1%}"


def performance_evidence(report: MatchReport, player: MatchParticipant) -> str:
    kda = "/".join(value_text(value) for value in (player.kills, player.deaths, player.assists))
    return (
        f"K/D/A {kda} · 参战 {participation_text(report, player)} · "
        f"GPM {value_text(player.gold_per_minute)}\n"
        f"伤害 {value_text(player.hero_damage)} · 建筑 {value_text(player.tower_damage)} · "
        f"治疗 {value_text(player.hero_healing)}"
    )


def performance_lines(report: MatchReport) -> list[str]:
    lines = ["STRATZ IMP 评分（来源模型，非官方 MVP；统计依据不等于评分公式）"]
    for label, players in (
        ("表现突出", report.strong_performers),
        ("表现偏弱", report.weak_performers),
    ):
        lines.append(label + "：")
        for player in players:
            lines.append(
                f"{hero_name(player)} · {participant_name(player)} · IMP {imp_text(player)}"
            )
            lines.append(performance_evidence(report, player))
        if not players:
            lines.append("没有可用的对应正/负分数，不推断。")
    count = len(report.detail.players or ()) if isinstance(report.detail, MatchDetail) else 0
    lines.append(f"IMP 可用 {len(report.imp_ranking)} / {count} 人；仅比较本局可用分数。")
    return lines


def analysis_lines(report: MatchReport) -> list[str]:
    if not isinstance(report.analysis, MatchAnalysis):
        return ["分析数据未提供；经济与购买事件未知。"]
    lines = []
    for series in report.analysis.team_metrics:
        label = "净资产优势" if "networth" in series.semantic.value else "经验优势"
        if series.values:
            lines.append(
                f"最后样本天辉{label} {series.values[-1]:+d}；{len(series.values)} 个来源分钟区间"
            )
        else:
            lines.append(f"{label}：来源返回空序列")
    purchases = sum(len(player.purchases or ()) for player in report.analysis.participants or ())
    metrics = sum(len(player.metrics) for player in report.analysis.participants or ())
    lines.append(f"分析：经济序列 {metrics} 项，购买事件 {purchases} 条。")
    return lines


def match_report_text(report: MatchReport) -> list[str]:
    detail = report.detail
    if not isinstance(detail, MatchDetail):
        return ["来源未返回该比赛详情，原因和隐私状态未知。"]
    winner = (
        "未知" if detail.did_radiant_win is None else "天辉" if detail.did_radiant_win else "夜魇"
    )
    intro = [
        f"Dota2Forge 比赛 {report.match_id.value} · 对局总览",
        f"开始 {timestamp(detail.started_at)} | "
        f"时长 {duration_text(detail.duration_seconds)} | 胜方 {winner}",
        f"模式 {game_mode_text(detail.game_mode)} | 版本 ID {value_text(detail.game_version_id)}",
        (
            f"OpenDota version {value_text(detail.parse_version)}"
            if detail.metadata.source.value == "opendota"
            else "STRATZ isStats "
            + ("未知" if detail.has_stats is None else "是" if detail.has_stats else "否")
        ),
        f"击杀 天辉 {value_text(report.team_total(True, 'kills'))} : "
        f"{value_text(report.team_total(False, 'kills'))} 夜魇",
        *performance_lines(report),
        *analysis_lines(report),
    ]
    footer = (
        f"来源 {report.metadata.source.value.upper()} | "
        f"抓取 {timestamp(report.metadata.fetched_at)}\n"
        f"详情状态 {detail.parse_state.value} | 解析时间 {timestamp(detail.parsed_at)}\n"
        "IMP 无公开模型版本；不跨比赛/来源比较，解析标记不证明字段完整。\n"
        "空白装备槽：无装备或来源未提供；未知字段不补零。"
    )
    pages = ["\n".join((*intro, footer))]
    for label, team in report_groups(report):
        lines = [f"比赛 {report.match_id.value} · {label}详细数据"]
        for player in team:
            own = (
                " [我方]"
                if report.tracked_account_id is not None
                and player.account_id == report.tracked_account_id
                else ""
            )
            lines.extend(
                (
                    f"{hero_name(player)} · {participant_name(player)}{own}",
                    f"{position_text(player.position)} / {lane_text(player.lane)} · "
                    f"IMP {imp_text(player)}",
                    performance_evidence(report, player),
                    f"XPM {value_text(player.experience_per_minute)}",
                    participant_stats_text(player),
                    participant_items_text(player),
                    "背包："
                    + " / ".join(
                        "未知" if item is None else "" if item == 0 else item_name(item)
                        for item in player.backpack_ids
                    ),
                    "中立装备："
                    + (
                        "未知"
                        if player.neutral_item_id is None
                        else ""
                        if player.neutral_item_id == 0
                        else item_name(player.neutral_item_id)
                    ),
                )
            )
        pages.append("\n".join((*lines, footer)))
    return pages


def split_report_text(pages: list[str], limit: int = 1400) -> list[str]:
    chunks: list[str] = []
    for page in pages:
        current = ""
        for line in page.splitlines():
            while len(line) > limit:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.append(line[:limit])
                line = line[limit:]
            candidate = current + ("\n" if current else "") + line
            if len(candidate) > limit:
                chunks.append(current)
                current = line
            else:
                current = candidate
        if current:
            chunks.append(current)
    return chunks
