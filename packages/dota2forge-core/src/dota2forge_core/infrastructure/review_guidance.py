"""Versioned read-only review guidance shared by native adapter consumers."""

from collections.abc import Callable, Mapping
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from ..domain.review import ReviewEvidence, ReviewTopic
from ..review import evidence_data, participant_analysis

SKILL_NAME = "dota2-review"
SKILL_VERSION = "1.0.0"
TOPIC_RESOURCES = {
    ReviewTopic.OVERVIEW: "overview.md",
    ReviewTopic.ECONOMY: "economy.md",
    ReviewTopic.LANING: "economy.md",
    ReviewTopic.ITEMS: "items.md",
    ReviewTopic.TEAM: "team.md",
}


def skill_directory() -> Path:
    """An installed wheel's owned resource directory; no caller-selected paths."""
    return Path(str(files("dota2forge_core").joinpath("infrastructure/review_skills")))


@lru_cache(maxsize=5)
def _read(relative: str) -> str:
    return (
        files("dota2forge_core")
        .joinpath("infrastructure/review_skills/dota2-review/" + relative)
        .read_text("utf-8")
    )


def guidance(topic: ReviewTopic) -> dict[str, str]:
    if not isinstance(topic, ReviewTopic):
        raise ValueError("Unknown review topic")
    resource = "references/" + TOPIC_RESOURCES[topic]
    return {
        "name": SKILL_NAME,
        "version": SKILL_VERSION,
        "topic": topic.value,
        "instructions": _read("SKILL.md"),
        "resource": resource,
        "topic_guide": _read(resource),
    }


def review_payload(
    evidence: ReviewEvidence,
    topic: ReviewTopic,
    *,
    hero_labels: Mapping[int, str] | None = None,
    item_label: Callable[[int], str] | None = None,
) -> dict[str, object]:
    result = evidence_data(evidence, topic)
    result["analysis_guide"] = guidance(topic)
    players = tuple(
        p
        for p in evidence.detail.players or ()
        if evidence.target_slot is None
        or p.player_slot == evidence.target_slot
        or topic == ReviewTopic.TEAM
    )
    economics = participant_analysis(evidence)
    item_ids = {
        item for p in players for item in (*p.item_ids, *p.backpack_ids, p.neutral_item_id) if item
    }
    item_ids.update(
        p.item_id for p in (() if economics is None else economics.purchases or ()) if p.item_id
    )
    result["display_names"] = {
        "heroes": {}
        if hero_labels is None
        else {
            str(p.hero_id): hero_labels.get(p.hero_id, f"英雄 ID {p.hero_id}")
            for p in evidence.detail.players or ()
            if p.hero_id is not None
        },
        "items": {}
        if item_label is None
        else {str(item): item_label(item) for item in sorted(item_ids)},
        "scope": "本地名称快照，仅解释标识，不证明本场补丁数值或装备效果。",
    }
    return result


def suggested_topic(query: str) -> ReviewTopic:
    value = query.lower()
    if any(word in value for word in ("出装", "装备", "购买", "bkb", "那件", "这件")):
        return ReviewTopic.ITEMS
    if any(word in value for word in ("对线", "补刀", "补给", "等级")):
        return ReviewTopic.LANING
    if any(word in value for word in ("经济", "净资产", "发育", "打钱", "曲线")):
        return ReviewTopic.ECONOMY
    if any(
        word in value
        for word in ("团战", "视野", "节奏", "肉山", "推塔", "背锅", "谁的锅", "救人", "保护")
    ):
        return ReviewTopic.TEAM
    return ReviewTopic.OVERVIEW
