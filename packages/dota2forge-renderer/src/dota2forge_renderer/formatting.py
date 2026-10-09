"""Display semantics shared by Pillow cards and adapter text fallback."""

import unicodedata
from datetime import datetime, timedelta, timezone

from dota2forge_core import estimate_rank_mmr

BEIJING = timezone(timedelta(hours=8))


def safe_name(value: str | None) -> str:
    if value is None:
        return "未知"
    return safe_text(value, limit=48)


def safe_text(value: str, *, limit: int = 512) -> str:
    cleaned = "".join(
        " " if char.isspace() else char
        for char in value
        if char.isspace() or (not unicodedata.category(char).startswith("C") and char not in "[]<>")
    )
    return " ".join(cleaned.split())[:limit] or "（空昵称）"


def value_text(value: int | None) -> str:
    return "未知" if value is None else str(value)


def timestamp(value: datetime | None) -> str:
    return (
        "未知" if value is None else value.astimezone(BEIJING).strftime("%Y-%m-%d %H:%M:%S UTC+8")
    )


def duration_text(value: int | None) -> str:
    if value is None:
        return "未知"
    minutes, seconds = divmod(value, 60)
    return f"{minutes}分{seconds:02d}秒"


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


def mmr_estimate_text(rank: int | None) -> str:
    estimate = estimate_rank_mmr(rank)
    if estimate is None:
        return "无法估算（未定级）" if rank == 0 else "未知（无有效段位）"
    if estimate.upper_bound is None:
        return f"{estimate.lower_bound}+ 分（仅下界）"
    return f"{estimate.lower_bound}–{estimate.upper_bound} 分"


def game_mode_text(mode: str | None) -> str:
    return {
        "ALL_PICK": "全英雄选择",
        "RANKED_ALL_PICK": "全英雄选择（天梯）",
        "ALL_PICK_RANKED": "全英雄选择（天梯）",
        "CAPTAINS_MODE": "队长模式",
        "TURBO": "加速模式",
        "OPENDOTA_1": "全英雄选择",
        "OPENDOTA_2": "队长模式",
        "OPENDOTA_22": "全英雄选择（天梯）",
        "OPENDOTA_23": "加速模式",
    }.get(mode or "", mode or "未知")
