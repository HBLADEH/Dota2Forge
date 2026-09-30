"""Plain text replies: missing values, source and time stay explicit."""

import unicodedata
from datetime import datetime

from dota2forge_core import PlayerProfile, ProviderError, ProviderErrorCode, RecentMatches

HELP = (
    "Dota2Forge / Dota2UID\n"
    "dota绑定 <Dota账号ID或SteamID64>\n"
    "dota改绑 <ID>：替换自己的绑定\n"
    "dota账号 / dota解绑\n"
    "dota玩家 [ID]\n"
    "dota战绩 [条数] 或 dota战绩 <ID> <条数>\n"
    "条数 1–100，默认 10；只绑定自己，不支持 @ 他人。\n"
    "绑定只是查询偏好，不证明 Steam 账号所有权。"
)


def safe_name(value: str | None) -> str:
    if value is None:
        return "未知"
    # Prevent control sequences, newlines and bracket-based chat markup in nicknames.
    cleaned = "".join(
        char
        for char in value
        if not unicodedata.category(char).startswith("C") and char not in "[]<>"
    )
    return " ".join(cleaned.split())[:48] or "（空昵称）"


def value_text(value: int | None) -> str:
    return "未知" if value is None else str(value)


def timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def rank_text(rank: int | None) -> str:
    if rank is None:
        return "未知"
    if rank == 0:
        return "未定级（编码 0）"
    tiers = ("", "先锋", "卫士", "中军", "统帅", "传奇", "万古流芳", "超凡入圣")
    tier, stars = divmod(rank, 10)
    if 1 <= tier <= 7 and 1 <= stars <= 5:
        return f"{tiers[tier]} {stars} 星"
    if rank == 80:
        return "冠绝一世"
    return f"未知段位编码 {rank}"


def player_text(player: PlayerProfile) -> str:
    observed = (
        "未知" if player.metadata.observed_at is None else timestamp(player.metadata.observed_at)
    )
    return (
        f"Dota2Forge 玩家\n昵称：{safe_name(player.display_name)}\n"
        f"段位：{rank_text(player.rank_tier)}\n"
        f"抓取时间：{timestamp(player.metadata.fetched_at)}\n"
        f"数据观测时间：{observed}\n"
        f"来源：STRATZ https://stratz.com/players/{player.account_id.value}"
    )


def recent_text(recent: RecentMatches) -> list[str]:
    if not recent.matches:
        return [
            "STRATZ 本次返回 0 场比赛（不代表完整历史无战绩）。\n"
            f"抓取时间：{timestamp(recent.metadata.fetched_at)}\n"
            f"来源：https://stratz.com/players/{recent.account_id.value}"
        ]
    pages: list[str] = []
    # Keep each plain-text send below common platform limits.
    for offset in range(0, len(recent.matches), 5):
        lines = [f"Dota2Forge 近期战绩 {offset + 1}–{min(offset + 5, len(recent.matches))}"]
        for match in recent.matches[offset : offset + 5]:
            outcome = "未知" if match.is_win is None else "胜" if match.is_win else "负"
            lines.append(
                f"{timestamp(match.started_at)} | {outcome} | 英雄ID {value_text(match.hero_id)}\n"
                f"K/D/A {value_text(match.kills)}/{value_text(match.deaths)}/"
                f"{value_text(match.assists)}"
                f" | 时长 {value_text(match.duration_seconds)} 秒\n"
                f"GPM {value_text(match.gold_per_minute)}"
                f" / XPM {value_text(match.experience_per_minute)}\n"
                f"https://stratz.com/matches/{match.match_id}"
            )
        lines.append(
            f"来源：STRATZ；抓取时间 {timestamp(recent.metadata.fetched_at)}\n"
            f"本次返回 {len(recent.matches)} 场，不保证历史完整。"
        )
        pages.append("\n".join(lines))
    return pages


def provider_error_text(error: ProviderError) -> str:
    if error.code == ProviderErrorCode.RATE_LIMITED:
        wait = (
            "等待时间未知，请联系管理员核实额度。"
            if error.retry_after_seconds is None
            else f"请至少等待 {error.retry_after_seconds} 秒后再试。"
        )
        return f"STRATZ 请求额度已用尽。{wait}"
    return {
        ProviderErrorCode.AUTHENTICATION: "STRATZ 认证失败，请管理员检查 Token。",
        ProviderErrorCode.TIMEOUT: "STRATZ 查询超时，请稍后手动重试。",
        ProviderErrorCode.UNAVAILABLE: "STRATZ 服务暂不可用或访问被拦截。",
        ProviderErrorCode.INVALID_RESPONSE: "STRATZ 返回的数据不完整或无法解析，本次查询失败。",
        ProviderErrorCode.PRIVATE: "数据源明确拒绝访问该玩家的私密数据。",
        ProviderErrorCode.NOT_FOUND: "数据源明确表示未找到该玩家。",
    }[error.code]
