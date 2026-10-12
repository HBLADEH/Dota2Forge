"""Shared text presentation of immutable subscription observations."""

from dota2forge_core import (
    DailyCoverage,
    DailyReport,
    MatchReport,
    MatchSummary,
    RankChange,
    SubscriptionEvent,
)
from dota2forge_core.domain.match_detail import MatchDetail

from .cards import MatchReportCard
from .formatting import rank_text, timestamp, value_text
from .reporting import (
    analysis_lines,
    match_report_text,
    performance_lines,
    report_groups,
    split_report_text,
)

FINITE_OBSERVATION_NOTICE = "这是有限来源观察，不代表完整战绩或精确MMR。"


def subscription_event_cards(event: SubscriptionEvent) -> tuple[MatchReportCard, ...]:
    """Prepare every report page from the persisted observation, without I/O."""
    report = event.payload
    if not isinstance(report, MatchReport) or not isinstance(report.detail, MatchDetail):
        return ()
    return tuple(
        MatchReportCard(report, page, subscription_event=event)
        for page in range(1, 2 + len(report_groups(report)))
    )


def subscription_event_text_pages(event: SubscriptionEvent) -> tuple[str, ...]:
    """Preserve complete report fields in bounded, same-observation fallback pages."""
    payload = event.payload
    if not isinstance(payload, MatchReport) or not isinstance(payload.detail, MatchDetail):
        return tuple(split_report_text([subscription_event_text(event)]))
    header: tuple[str, ...] = (
        "Dota2Forge 订阅提醒",
        _account_label(event),
        f"比赛对局报告：{payload.match_id.value}",
    )
    if payload.tracked_account_id is not None:
        header += (f"订阅玩家：{payload.tracked_account_id.value}",)
    source = (
        f"来源 {payload.metadata.source.value.upper()} | "
        f"抓取 {timestamp(payload.metadata.fetched_at)}"
    )
    prefix = "\n".join(header)
    metadata_lines = [source]
    if payload.detail.metadata.fetched_at != payload.metadata.fetched_at:
        metadata_lines.append(
            f"详情来源 {payload.detail.metadata.source.value.upper()} | "
            f"抓取 {timestamp(payload.detail.metadata.fetched_at)}"
        )
    metadata_lines.extend(
        (
            f"数据观测时间 {timestamp(payload.detail.metadata.observed_at)}",
            f"分析抓取 {timestamp(payload.analysis.metadata.fetched_at)}",
        )
    )
    suffix = "\n".join((*metadata_lines, FINITE_OBSERVATION_NOTICE, f"事件ID {event.event_id}"))
    body_pages = [
        "\n".join(line for line in text.splitlines() if line != source)
        for text in match_report_text(payload)
    ]
    body_limit = 1400 - len(prefix) - len(suffix) - 2
    return tuple(
        "\n".join((prefix, body, suffix)) for body in split_report_text(body_pages, body_limit)
    )


def _account_label(event: SubscriptionEvent) -> str:
    return (
        f"账号 {event.key.account_id.value}"
        if event.key.account_id is not None
        else f"比赛 {event.key.match_id.value if event.key.match_id else '未知'}"
    )


def subscription_event_text(event: SubscriptionEvent) -> str:
    payload = event.payload
    lines = ["Dota2Forge 订阅提醒", _account_label(event)]
    if isinstance(payload, MatchReport):
        lines.extend(match_report_lines(payload))
    elif isinstance(payload, MatchSummary):
        outcome = "未知" if payload.is_win is None else "胜" if payload.is_win else "负"
        lines.extend(
            [
                f"新比赛 {payload.match_id} | {outcome}",
                f"开始时间：{timestamp(payload.started_at)}",
                f"英雄ID {value_text(payload.hero_id)} | K/D/A "
                f"{value_text(payload.kills)}/{value_text(payload.deaths)}/{value_text(payload.assists)}",
                f"详情：do比赛 {payload.match_id}",
            ]
        )
    elif isinstance(payload, RankChange):
        lines.append(
            f"段位变化：{rank_text(payload.previous_rank)} → {rank_text(payload.current_rank)}"
        )
    elif isinstance(payload, DailyReport):
        lines.extend(
            [
                f"每日观察战报 {payload.report_date.isoformat()}（北京时间 UTC+8）",
                f"按比赛开始时间归属：观察到 {len(payload.matches)} 场；"
                f"胜 {payload.wins} / 负 {payload.losses} / 胜负未知 {payload.unknown_outcomes}",
                {
                    DailyCoverage.EMPTY: "来源返回空列表，不能判定当天没有比赛。",
                    DailyCoverage.BOUNDED: "未观察到完整日窗口边界，统计可能不完整。",
                    DailyCoverage.TRUNCATED: "近期窗口已达上限，可能遗漏当天比赛。",
                    DailyCoverage.WINDOW_SPANNED: "已观察到日窗口边界，仍不保证来源覆盖完整。",
                }[payload.coverage],
            ]
        )
    source_line = (
        f"来源：{payload.metadata.source.value.upper()} | "
        f"抓取 {timestamp(payload.metadata.fetched_at)}"
    )
    if source_line not in lines:
        lines.append(source_line)
    lines.extend((FINITE_OBSERVATION_NOTICE, f"事件ID {event.event_id}"))
    return "\n".join(lines)


def match_report_lines(report: MatchReport) -> list[str]:
    lines = [f"比赛对局报告：{report.match_id.value}"]
    if report.tracked_account_id is not None:
        lines.append(f"订阅玩家：{report.tracked_account_id.value}")
    detail = report.detail
    if not isinstance(detail, MatchDetail):
        lines.append("详情：数据源未返回，原因和隐私状态未知。")
        return lines
    winner = (
        "未知" if detail.did_radiant_win is None else "天辉" if detail.did_radiant_win else "夜魇"
    )
    lines.append(
        f"结果：{winner} | 时长：{value_text(detail.duration_seconds)}秒 | "
        f"模式：{detail.game_mode or '未知'}"
    )
    candidate = report.performance_candidate
    if report.imp_ranking:
        lines.extend(performance_lines(report))
    elif candidate is None:
        lines.append("表现候选：未知（参赛者胜负或 K/D/A 数据不足；Provider 未提供官方 MVP）。")
    else:
        account, slot = candidate
        lines.append(
            f"表现候选（非官方MVP）：账号 {value_text(None if account is None else account.value)} "
            f"| 槽位 {value_text(slot)}"
        )
    if detail.players:
        lines.append("参赛者：")
        for player in detail.players:
            participant_account = (
                "匿名/未知" if player.account_id is None else str(player.account_id.value)
            )
            lines.append(
                f"{participant_account} K/D/A "
                f"{value_text(player.kills)}/{value_text(player.deaths)}/"
                f"{value_text(player.assists)} GPM {value_text(player.gold_per_minute)}"
            )
    lines.append(analysis_lines(report)[-1])
    lines.append(
        f"来源：{detail.metadata.source.value.upper()} | "
        f"抓取 {timestamp(detail.metadata.fetched_at)}"
    )
    return lines
