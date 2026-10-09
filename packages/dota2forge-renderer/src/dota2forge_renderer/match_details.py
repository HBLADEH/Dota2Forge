"""Shared participant details for both adapters' text fallback."""

from dota2forge_core import MatchParticipant

from .formatting import value_text
from .hero_items import item_name


def participant_stats_text(player: MatchParticipant) -> str:
    return (
        f"等级 {value_text(player.level)} | 补刀 {value_text(player.last_hits)}"
        f" / 反补 {value_text(player.denies)} | 净资产 {value_text(player.net_worth)}\n"
        f"英雄伤害 {value_text(player.hero_damage)}"
        f" | 建筑伤害 {value_text(player.tower_damage)}"
        f" | 治疗量 {value_text(player.hero_healing)}"
    )


def participant_items_text(player: MatchParticipant) -> str:
    return "装备：" + " / ".join(
        "未知" if item is None else "" if item == 0 else f"{item_name(item)}（{item}）"
        for item in player.item_ids
    )
