"""Shared offline item names and source-faithful hero item statistics text."""

import json
from functools import lru_cache
from importlib.resources import files

from dota2forge_core import HeroItemStatistics, HeroResolutionError, ItemStage

from .formatting import timestamp

STAGE_LABELS = {
    ItemStage.START: "出门",
    ItemStage.EARLY: "前期",
    ItemStage.MID: "中期",
    ItemStage.LATE: "后期",
}
ITEM_STATISTICS_NOTICE = "职业比赛购买统计；热门不等于最优出装或购买顺序。"


@lru_cache(maxsize=1)
def item_names() -> dict[int, str]:
    payload = json.loads(
        files("dota2forge_renderer").joinpath("assets/v1/items.json").read_text("utf-8")
    )
    return {int(key): row["name_loc"] for key, row in payload["items"].items()}


def item_name(item_id: int) -> str:
    return item_names().get(item_id, f"装备 ID {item_id}")


def item_card_name(item_id: int) -> str:
    """Reviewed compact labels for pictures; text replies retain the source name."""
    name = item_name(item_id)
    aliases = {
        "阿哈利姆神杖": "A杖",
        "阿哈利姆福佑": "A杖福佑",
        "阿哈利姆福佑 - 肉山": "A杖福佑·肉山",
        "阿哈利姆魔晶 - 消耗品": "魔晶·消耗品",
        "弗拉迪米尔的祭品": "祭品",
        "Eul的神圣法杖": "风杖",
        "莫尔迪基安的臂章": "臂章",
        "代达罗斯之殇": "大炮",
        "Black Grimoire\n(Warlock)": "术士魔典",
    }
    if name.startswith("图纸（") and name.endswith("）"):
        base = name[3:-1]
        return aliases.get(base, base) + "图纸"
    return aliases.get(name, name)


def hero_resolution_text(error: HeroResolutionError) -> str:
    if error.candidates:
        names = " / ".join(hero.display_name for hero in error.candidates)
        return (
            f"英雄简称有歧义：{names}。请用完整英雄名，例如 "
            f"do{error.candidates[0].display_name}出装。"
        )
    return "未识别该英雄，请使用中文名、英文名或常用简称，例如 do斧王出装 / doAM出装。"


def hero_items_text(result: HeroItemStatistics) -> str:
    lines = [
        f"Dota2Forge · {result.hero.display_name}热门出装",
        "各阶段按购买统计次数列出前5项（0保留）。",
    ]
    for stage in result.stages:
        lines.append(STAGE_LABELS[stage.stage])
        if stage.items is None:
            lines.append("统计未知（来源未返回）")
        elif not stage.items:
            lines.append("本次无物品统计")
        else:
            items = sorted(stage.items, key=lambda item: (-item.count, item.item_id))[:5]
            lines.extend(f"{item_name(item.item_id)}：{item.count} 次" for item in items)
    lines.extend(
        [
            ITEM_STATISTICS_NOTICE,
            "位置、补丁、统计窗口与总样本数未知；不计算胜率/出场率。",
            f"来源：{result.metadata.source.value.upper()}",
            f"抓取时间：{timestamp(result.metadata.fetched_at)}",
            f"数据观测时间：{timestamp(result.metadata.observed_at)}",
            f"https://www.opendota.com/heroes/{result.hero.hero_id}/itemPopularity",
        ]
    )
    return "\n".join(lines)
