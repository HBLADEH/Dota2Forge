"""Plain text replies: missing values, source and time stay explicit."""

from datetime import datetime

from dota2forge_core import (
    AccountId,
    DataSource,
    MatchDetail,
    MatchDetailResult,
    MatchDetailUnavailable,
    MatchParseState,
    PlayerProfile,
    ProviderError,
    ProviderErrorCode,
    RecentMatches,
)
from dota2forge_renderer.formatting import (
    duration_text,
)
from dota2forge_renderer.formatting import (
    rank_text as rank_text,
)
from dota2forge_renderer.formatting import (
    safe_name as safe_name,
)
from dota2forge_renderer.formatting import (
    timestamp as timestamp,
)
from dota2forge_renderer.formatting import (
    value_text as value_text,
)

HELP = (
    "Dota2Forge / Dota2UID\n"
    "dota绑定 <Dota账号ID或SteamID64>\n"
    "dota改绑 <ID>：替换自己的绑定\n"
    "dota账号 / dota解绑\n"
    "dota玩家 [ID]\n"
    "dota战绩 [条数] 或 dota战绩 <ID> <条数>\n"
    "dota比赛 <比赛ID>：直接查询历史单局详情\n"
    "dota比赛 第N场 / dota战绩 第N页：使用本会话最后有效列表\n"
    "dota订阅 [比赛|段位|日报] [ID] / dota订阅列表 [游标]\n"
    "dota订阅玩家 <玩家ID> / dota订阅比赛 <比赛ID>：完成后播报详情分析\n"
    "dota取消订阅 <订阅ID> / dota重试推送 <事件ID>\n"
    "订阅默认关闭；群订阅仅限 Bot 管理员。失败推送不自动重发。\n"
    "条数 1–100，默认 10；只绑定自己，不支持 @ 他人。\n"
    "绑定只是查询偏好，不证明 Steam 账号所有权。"
)


def player_source_text(source: DataSource, account: AccountId) -> str:
    label = source.value.upper()
    return (
        f"{label} https://stratz.com/players/{account.value}"
        if source == DataSource.STRATZ
        else label
    )


def player_text(player: PlayerProfile) -> str:
    observed = (
        "未知" if player.metadata.observed_at is None else timestamp(player.metadata.observed_at)
    )
    return (
        f"Dota2Forge 玩家\n昵称：{safe_name(player.display_name)}\n"
        f"段位：{rank_text(player.rank_tier)}\n"
        f"抓取时间：{timestamp(player.metadata.fetched_at)}\n"
        f"数据观测时间：{observed}\n"
        f"来源：{player_source_text(player.metadata.source, player.account_id)}"
    )


def recent_text(recent: RecentMatches) -> list[str]:
    source = player_source_text(recent.metadata.source, recent.account_id)
    observed = detail_timestamp(recent.metadata.observed_at)
    if not recent.matches:
        return [
            f"{recent.metadata.source.value.upper()} 本次返回 0 场比赛"
            "（不代表完整历史无战绩）。\n"
            f"抓取时间：{timestamp(recent.metadata.fetched_at)}\n"
            f"数据观测时间：{observed}\n"
            f"来源：{source}"
        ]
    pages: list[str] = []
    # Keep each plain-text send below common platform limits.
    for offset in range(0, len(recent.matches), 5):
        lines = [f"Dota2Forge 近期战绩 {offset + 1}–{min(offset + 5, len(recent.matches))}"]
        for index, match in enumerate(recent.matches[offset : offset + 5], offset + 1):
            outcome = "未知" if match.is_win is None else "胜" if match.is_win else "负"
            lines.append(
                f"第 {index} 场 | {timestamp(match.started_at)} | {outcome} | "
                f"英雄ID {value_text(match.hero_id)}\n"
                f"K/D/A {value_text(match.kills)}/{value_text(match.deaths)}/"
                f"{value_text(match.assists)}"
                f" | 时长 {detail_duration(match.duration_seconds)}\n"
                f"GPM {value_text(match.gold_per_minute)}"
                f" / XPM {value_text(match.experience_per_minute)}\n"
                f"比赛 ID {match.match_id} | dota比赛 {match.match_id}"
                + (
                    f"\nhttps://stratz.com/matches/{match.match_id}"
                    if match.metadata.source == DataSource.STRATZ
                    else ""
                )
            )
        lines.append(
            f"来源：{source}\n抓取时间 {timestamp(recent.metadata.fetched_at)}\n"
            f"数据观测时间：{observed}\n"
            f"本次返回 {len(recent.matches)} 场，不保证历史完整。"
        )
        pages.append("\n".join(lines))
    return pages


def provider_error_text(error: ProviderError, *, subject: str = "玩家") -> str:
    source = error.source.value.upper()
    if error.code == ProviderErrorCode.RATE_LIMITED:
        wait = (
            "等待时间未知，请联系管理员核实额度。"
            if error.retry_after_seconds is None
            else f"请至少等待 {error.retry_after_seconds} 秒后再试。"
        )
        return f"{source} 请求额度已用尽。{wait}"
    return {
        ProviderErrorCode.AUTHENTICATION: f"{source} 认证失败，请管理员检查数据源凭据。",
        ProviderErrorCode.TIMEOUT: f"{source} 查询超时，请稍后手动重试。",
        ProviderErrorCode.UNAVAILABLE: f"{source} 服务暂不可用或访问被拦截。",
        ProviderErrorCode.INVALID_RESPONSE: f"{source} 返回的数据不完整或无法解析，本次查询失败。",
        ProviderErrorCode.PRIVATE: f"{source} 数据源明确拒绝访问该{subject}的私密数据。",
        ProviderErrorCode.NOT_FOUND: f"{source} 数据源明确表示未找到该{subject}。",
    }[error.code]


def detail_timestamp(value: datetime | None) -> str:
    if value is None:
        return "未知"
    return timestamp(value)


def detail_duration(value: int | None) -> str:
    return duration_text(value)


def detail_footer(result: MatchDetailResult) -> str:
    source_link = (
        f"https://stratz.com/matches/{result.match_id.value}\n"
        if result.metadata.source == DataSource.STRATZ
        else ""
    )
    return (
        f"来源：{result.metadata.source.value}\n"
        + source_link
        + f"抓取时间：{detail_timestamp(result.metadata.fetched_at)}\n"
        f"数据观测时间：{detail_timestamp(result.metadata.observed_at)}\n"
        "不保证历史覆盖或详情字段完整。"
    )


def parse_state_text(result: MatchDetailResult) -> str:
    labels = {
        MatchParseState.NO_DATA: "未返回（原因和隐私状态未知）",
        MatchParseState.UNKNOWN: "未知（没有解析标记）",
        MatchParseState.UNPARSED: "未解析（上游 isStats=False）",
        MatchParseState.PARTIAL: "部分解析（字段可能缺失）",
        MatchParseState.UPSTREAM_PARSED: "上游已标记解析（不代表字段完整）",
    }
    return labels[result.parse_state]


def match_detail_text(result: MatchDetailResult, perspective: AccountId | None = None) -> list[str]:
    if isinstance(result, MatchDetailUnavailable):
        return [
            f"{result.metadata.source.value.upper()} 本次没有返回该比赛详情，原因和隐私状态未知。\n"
            "详情状态：未返回（原因和隐私状态未知）。\n"
            "不能据此判定比赛不存在或为私密。\n" + detail_footer(result)
        ]
    assert isinstance(result, MatchDetail)
    winner = (
        "未知" if result.did_radiant_win is None else "天辉" if result.did_radiant_win else "夜魇"
    )
    stats = "未知" if result.has_stats is None else "是" if result.has_stats else "否"
    marker = (
        f"version：{value_text(result.parse_version)}"
        if result.metadata.source == DataSource.OPENDOTA
        else f"isStats：{stats}"
    )
    own = None if perspective is None else result.participant(perspective)
    header = (
        f"Dota2Forge 比赛 {result.match_id.value}\n"
        f"开始：{detail_timestamp(result.started_at)}"
        f" | 时长：{detail_duration(result.duration_seconds)}\n"
        f"模式：{result.game_mode or '未知'} | 上游版本 ID：{value_text(result.game_version_id)}\n"
        f"胜方：{winner}\n"
        f"{result.metadata.source.value.upper()} {marker}"
        f" | 解析时间：{detail_timestamp(result.parsed_at)}\n"
        f"详情状态：{parse_state_text(result)}\n"
        "解析标记与解析时间不证明详情字段完整。"
    )
    players = result.players
    if players is None or not players:
        return [
            header
            + ("\n参赛者数据未知。\n" if players is None else "\n本次返回 0 名参赛者。\n")
            + detail_footer(result)
        ]
    pages: list[str] = []
    for side, label in ((True, "天辉"), (False, "夜魇"), (None, "阵营未知")):
        team = tuple(player for player in players if player.is_radiant is side)
        for offset in range(0, len(team), 5):
            lines = [header, label]
            for player in team[offset : offset + 5]:
                name = (
                    "匿名参赛者"
                    if player.is_anonymous is True
                    else "身份未知"
                    if player.account_id is None
                    else safe_name(player.display_name)
                )
                marker = " [我方]" if own is player else ""
                kda = "/".join(
                    value_text(value) for value in (player.kills, player.deaths, player.assists)
                )
                items = "/".join(
                    "未知" if item is None else "空" if item == 0 else str(item)
                    for item in player.item_ids
                )
                lines.append(
                    f"{name}{marker} | 英雄 ID {value_text(player.hero_id)}\n"
                    f"K/D/A {kda} | GPM {value_text(player.gold_per_minute)}"
                    f" / XPM {value_text(player.experience_per_minute)}\n装备 ID {items}"
                )
            lines.append(detail_footer(result))
            pages.append("\n".join(lines))
    return pages
