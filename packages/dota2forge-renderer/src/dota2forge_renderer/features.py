"""Source-faithful text equivalents and bounded feature card batches."""

import json
from functools import lru_cache
from importlib.resources import files

from dota2forge_core import GuideSample, HeroGuide, HeroMetaRanking, RankBracket, ReviewEvidence

from .cards import Card, GuideSampleCard, HeroGuideCard, HeroMetaCard, RenderError
from .formatting import duration_text, timestamp, value_text
from .hero_items import item_name
from .reporting import position_text

SOURCE_STATUS = {
    "scope_mismatch": "来源统计位置与所选位置不一致，暂不推荐",
    "not_found": "来源未找到数据",
    "private": "来源数据未公开",
    "rate_limited": "来源请求额度受限",
    "timeout": "来源请求超时",
    "unavailable": "来源暂不可用",
    "authentication": "来源授权失败",
    "invalid_response": "来源返回的数据无法核实",
}

RANK_LABELS = dict(
    zip(
        RankBracket,
        ("全部", "未定级", "先锋", "卫士", "中军", "统帅", "传奇", "万古", "超凡", "冠绝"),
        strict=True,
    )
)


@lru_cache(maxsize=1)
def hero_names() -> dict[int, str]:
    raw = json.loads(
        files("dota2forge_renderer").joinpath("assets/v1/heroes.json").read_text("utf-8")
    )
    return {row["id"]: row["name_loc"] for row in raw["heroes"]}


def clock_text(seconds: int) -> str:
    return ("-" if seconds < 0 else "") + f"{abs(seconds) // 60:02}:{abs(seconds) % 60:02}"


def feature_cards(
    result: HeroMetaRanking | HeroGuide | GuideSample, *, detailed: bool = False
) -> tuple[Card, ...]:
    if isinstance(result, HeroMetaRanking):
        return tuple(
            HeroMetaCard(result, p + 1) for p in range(max(1, (len(result.entries) + 4) // 5))
        )
    if isinstance(result, HeroGuide):
        return tuple(HeroGuideCard(result, p + 1, detailed) for p in range(4 if detailed else 2))
    return (GuideSampleCard(result), GuideSampleCard(result, 2))


def sample_summary(sample: GuideSample) -> list[str]:
    player = sample.player
    return [
        f"{sample.hero.display_name} · 单场样例 {sample.match_id.value}",
        f"实际位置 {position_text(player.position)} · 版本 {sample.metadata.patch or '未知'}",
        f"K/D/A {'/'.join(value_text(v) for v in (player.kills, player.deaths, player.assists))}"
        f" · IMP {value_text(player.imp)} · 时长 {duration_text(sample.duration_seconds)}",
        "单场观察，不是聚合推荐或最佳方案。",
        *(
            []
            if sample.label_error is None
            else [f"技能中文名获取失败：{SOURCE_STATUS[sample.label_error]}；保留来源名/ID。"]
        ),
    ]


def feature_text(card: Card) -> str:
    if isinstance(card, HeroMetaCard):
        ranking = card.ranking
        snap = ranking.snapshot
        if type(card.page) is not int or not 1 <= card.page <= max(
            1, (len(ranking.entries) + 4) // 5
        ):
            raise RenderError()
        lines = [
            f"Dota2Forge · 版本强势 {snap.patch.name}",
            f"{RANK_LABELS[snap.request.rank]} · 请求近 {snap.request.days} 日 · 天梯全选",
            f"窗口 {snap.window_start:%Y-%m-%d}–{snap.window_end:%Y-%m-%d} UTC（右端不含）",
        ]
        for entry in ranking.entries[(card.page - 1) * 5 : card.page * 5]:
            hero = hero_names().get(entry.hero_id, f"英雄 ID {entry.hero_id}")
            lines.append(
                f"{entry.position}号位 {hero}"
                f" · 胜率 {(entry.win_rate or 0):.1%} · {entry.matches} 场"
                f" · 95%保守胜率 {entry.reliability:.1%}"
            )
        if not ranking.entries:
            lines.append("没有达到最低样本量的可用英雄；不能据此推断版本强弱。")
        lines.extend(
            [
                f"最低样本 {snap.request.minimum_matches} 场；"
                f"{ranking.observing} 个英雄/位置仍在观察。",
                "可靠度排序使用 Wilson 95% 下界；胜率不证明选择该英雄能提升个人分数。",
                *snap.notes,
            ]
        )
        metadata = snap.metadata
    elif isinstance(card, HeroGuideCard):
        guide = card.guide
        maximum = 4 if card.detailed else 2
        if type(card.page) is not int or not 1 <= card.page <= maximum:
            raise RenderError()
        lines = [
            f"Dota2Forge · {guide.hero.display_name} {guide.position}号位攻略 {card.page}/{maximum}"
        ]
        if card.page == 1:
            lines.extend(["统计窗口尚未核实，不作为当前版本推荐。", *guide.notes])
            if guide.items is None:
                lines.append("出装统计未启用/未返回；原因见模块状态。")
            else:
                best = sorted(guide.items, key=lambda v: (-v.matches, v.minute, v.item_id))[:10]
                lines.extend(
                    f"{item_name(v.item_id)} · {v.minute}分钟桶 · {v.matches}场 / {v.wins}胜"
                    for v in best
                )
                lines.append(f"共 {len(guide.items)} 个装备时间桶，本页展示最多10个热门桶。")
            modules = {"statistics": "构筑统计", "samples": "比赛样例", "abilities": "技能统计"}
            lines.extend(
                f"{modules[key]}：{SOURCE_STATUS[value]}" for key, value in guide.module_errors
            )
            lines.append(f"本次有 {len(guide.samples)} 个实际位置校验过的单场样例。")
        elif card.page in (2, 3):
            if not guide.samples:
                lines.append("单场样例未返回；不生成加点或购买顺序。")
            else:
                lines.extend(sample_summary(guide.samples[0]))
                lines.extend(sample_events(guide.samples[0], 1 if card.page == 2 else 2))
        else:
            lines.append("天赋选择桶（不拼接成最佳加点顺序）")
            if guide.talents is None:
                lines.append("天赋统计未返回或位置不一致。")
            else:
                lines.extend(
                    f"技能 ID {v.ability_id} · {v.matches}场 / {v.wins}胜"
                    for v in sorted(guide.talents, key=lambda v: (-v.matches, v.ability_id))[:8]
                )
            for sample in guide.samples:
                lines.extend(sample_summary(sample))
        metadata = guide.metadata
    elif isinstance(card, GuideSampleCard):
        if type(card.page) is not int or card.page not in (1, 2):
            raise RenderError()
        lines = [
            "Dota2Forge · 攻略样例",
            *sample_summary(card.sample),
            *sample_events(card.sample, card.page),
        ]
        metadata = card.sample.metadata
    else:
        raise TypeError("Expected a hero feature card")
    lines.extend(
        [
            f"来源 {metadata.source.value.upper()} · 抓取 {timestamp(metadata.fetched_at)}",
            f"观测 {timestamp(metadata.observed_at)}",
        ]
    )
    return "\n".join(lines)


def sample_events(sample: GuideSample, page: int) -> list[str]:
    if page == 1:
        lines = ["真实升级记录：序号不是英雄等级；技能阶数保留源值（从0起）。"]
        if sample.upgrades is None:
            lines.append("升级记录未知。")
        else:
            lines.extend(
                f"#{i} {clock_text(v.time_seconds)} · {v.name or f'技能 ID {v.ability_id}'}"
                f" · 源阶数 {v.source_level}{' · 天赋' if v.is_talent else ''}"
                for i, v in enumerate(sample.upgrades[:24], 1)
            )
            lines.append(
                f"展示 {min(24, len(sample.upgrades))}/{len(sample.upgrades)} 条升级记录。"
            )
    else:
        lines = ["真实购买时间线；负时间为赛前，保留组件和重复购买。"]
        if sample.purchases is None:
            lines.append("购买记录未知。")
        else:
            lines.extend(
                f"{clock_text(v.time_seconds)} · "
                f"{item_name(v.item_id) if v.item_id is not None else v.item_key}"
                for v in sample.purchases[:32]
            )
            lines.append(
                f"展示 {min(32, len(sample.purchases))}/{len(sample.purchases)} 条购买记录。"
            )
        player = sample.player
        lines.extend(
            [
                "最终装备（来源快照，不重建任意时刻库存）",
                " / ".join(
                    "未知" if v is None else "空槽" if v == 0 else item_name(v)
                    for v in player.item_ids
                ),
                "背包："
                + " / ".join(
                    "未知" if v is None else "空槽" if v == 0 else item_name(v)
                    for v in player.backpack_ids
                ),
                "中立："
                + (
                    "未知"
                    if player.neutral_item_id is None
                    else "空槽"
                    if player.neutral_item_id == 0
                    else item_name(player.neutral_item_id)
                ),
            ]
        )
    return lines


def review_brief(evidence: ReviewEvidence) -> str:
    detail = evidence.detail
    lines = [
        f"Dota2Forge · 比赛 {detail.match_id.value} 复盘事实",
        f"时长 {duration_text(detail.duration_seconds)} · "
        f"版本ID {value_text(detail.game_version_id)}",
    ]
    for player in detail.players or ():
        if evidence.target_slot is None or player.player_slot == evidence.target_slot:
            kda = "/".join(value_text(v) for v in (player.kills, player.deaths, player.assists))
            lines.append(
                f"{hero_names().get(player.hero_id or 0, '英雄未知')} · "
                f"K/D/A {kda} · GPM {value_text(player.gold_per_minute)}"
                f" / XPM {value_text(player.experience_per_minute)}"
            )
    lines.extend(
        [
            "可继续问经济走势、装备购买或双方优势；判断需由宿主 AI 结合这些事实给出。",
            "未接入死亡/团战/视野事件，不能确定具体操作原因。",
            f"来源 {detail.metadata.source.value.upper()} · "
            f"抓取 {timestamp(detail.metadata.fetched_at)}",
        ]
    )
    if evidence.analysis_error:
        lines.append(
            f"经济/购买数据获取失败：{SOURCE_STATUS[evidence.analysis_error]}；基础事实仍可用。"
        )
    return "\n".join(lines)
