"""Restricted native-tool arguments and identity-free observation serialization."""

from dataclasses import dataclass

from .domain.errors import ValidationError
from .domain.hero_features import (
    GuideSample,
    HeroGuide,
    HeroMetaRanking,
    MetaRequest,
    MetaSort,
    RankBracket,
)
from .domain.hero_items import normalize_hero_name
from .domain.match_detail import MatchId, parse_match_id
from .domain.review import ReviewChartKind, ReviewChartRequest, ReviewTopic

TOOL_NAMES = (
    "get_dota2_meta",
    "get_dota2_hero_guide",
    "get_dota2_review_context",
    "render_dota2_review_data",
)


def tool_schema(name: str) -> dict[str, object]:
    """Explicit schemas without trusted host fields; runtime validation remains authoritative."""
    match = {"type": "string", "maxLength": 19, "pattern": r"^$|^[1-9][0-9]{0,18}$", "default": ""}
    hero = {"type": "string", "maxLength": 64, "default": ""}
    if name == "get_dota2_meta":
        properties: dict[str, object] = {
            "position": {"type": "integer", "minimum": 0, "maximum": 5, "default": 0},
            "rank": {
                "type": "string",
                "enum": [value.value for value in RankBracket],
                "default": "ALL",
            },
            "days": {"type": "integer", "enum": [7, 14], "default": 7},
            "sort": {"type": "string", "enum": [v.value for v in MetaSort], "default": "reliable"},
        }
        required = []
    elif name == "get_dota2_hero_guide":
        properties = {
            "hero_name": {"type": "string", "minLength": 1, "maxLength": 64},
            "position": {"type": "integer", "minimum": 1, "maximum": 5, "default": 1},
            "match_id": match,
        }
        required = ["hero_name"]
    elif name == "get_dota2_review_context":
        properties = {
            "hero_name": hero,
            "match_id": match,
            "topic": {
                "type": "string",
                "enum": [v.value for v in ReviewTopic],
                "default": "overview",
            },
        }
        required = []
    elif name == "render_dota2_review_data":
        properties = {
            "hero_name": hero,
            "match_id": match,
            "kind": {"type": "string", "enum": [v.value for v in ReviewChartKind]},
            "start_seconds": {"type": "integer", "minimum": -600, "maximum": 21599, "default": 0},
            "end_seconds": {"type": "integer", "minimum": 0, "maximum": 21600, "default": 0},
        }
        required = ["kind"]
    else:
        raise ValidationError("Unknown native tool schema")
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


@dataclass(frozen=True, slots=True)
class ToolRequest:
    name: str
    meta: MetaRequest = MetaRequest()
    hero_name: str | None = None
    position: int = 1
    match_id: MatchId | None = None
    topic: ReviewTopic = ReviewTopic.OVERVIEW
    chart: ReviewChartRequest | None = None


def parse_tool(name: str, args: dict[str, object]) -> ToolRequest:
    allowed = {
        "get_dota2_meta": {"position", "rank", "days", "sort"},
        "get_dota2_hero_guide": {"hero_name", "position", "match_id"},
        "get_dota2_review_context": {"match_id", "hero_name", "topic"},
        "render_dota2_review_data": {
            "match_id",
            "hero_name",
            "kind",
            "start_seconds",
            "end_seconds",
        },
    }
    if name not in allowed or not isinstance(args, dict) or not set(args) <= allowed[name]:
        raise ValidationError("Unknown tool or extra arguments")
    if name == "get_dota2_meta":
        position = args.get("position", 0)
        if type(position) is not int or not 0 <= position <= 5:
            raise ValidationError("Expected position 0-5")
        rank, sort, days = (
            args.get("rank", "ALL"),
            args.get("sort", "reliable"),
            args.get("days", 7),
        )
        if not isinstance(rank, str) or not isinstance(sort, str) or type(days) is not int:
            raise ValidationError("Invalid statistics filters")
        return ToolRequest(
            name, meta=MetaRequest(position or None, RankBracket(rank), days, MetaSort(sort))
        )
    raw_name, raw_match = args.get("hero_name"), args.get("match_id")
    if raw_name is not None and raw_name != "":
        if not isinstance(raw_name, str):
            raise ValidationError("Expected hero name")
        normalize_hero_name(raw_name)
    else:
        raw_name = None
    match = None
    if raw_match not in (None, ""):
        if not isinstance(raw_match, (str, int)) or isinstance(raw_match, bool):
            raise ValidationError("Expected match ID")
        match = parse_match_id(raw_match)
    position = args.get("position", 1)
    if type(position) is not int or not 1 <= position <= 5:
        raise ValidationError("Expected position 1-5")
    if name == "get_dota2_hero_guide" and raw_name is None:
        raise ValidationError("Hero is required")
    topic = args.get("topic", "overview")
    if not isinstance(topic, str):
        raise ValidationError("Invalid review topic")
    chart = None
    if name == "render_dota2_review_data":
        kind = args.get("kind")
        start, end = args.get("start_seconds", 0), args.get("end_seconds", 3600)
        if not isinstance(kind, str) or type(start) is not int or type(end) is not int:
            raise ValidationError("Expected bounded chart arguments")
        chart = ReviewChartRequest(ReviewChartKind(kind), start, end)
    return ToolRequest(
        name,
        hero_name=raw_name,
        position=position,
        match_id=match,
        topic=ReviewTopic(topic),
        chart=chart,
    )


def meta_data(ranking: HeroMetaRanking) -> dict[str, object]:
    snapshot = ranking.snapshot
    return {
        "schema": "dota2forge.meta.v1",
        "source": snapshot.metadata.source.value,
        "fetched_at": snapshot.metadata.fetched_at.isoformat(),
        "patch": snapshot.patch.name,
        "window_start": snapshot.window_start.isoformat(),
        "window_end_exclusive": snapshot.window_end.isoformat(),
        "rank": snapshot.request.rank.value,
        "position": snapshot.request.position,
        "minimum_matches": snapshot.request.minimum_matches,
        "requested_days": snapshot.request.days,
        "sort": snapshot.request.sort.value,
        "notes": list(snapshot.notes),
        "entries": [
            {
                "hero_id": e.hero_id,
                "position": e.position,
                "matches": e.matches,
                "wins": e.wins,
                "win_rate": e.win_rate,
                "wilson_95_lower": e.reliability,
            }
            for e in ranking.entries
        ],
        "limitations": "观察胜率不证明个人选用后会提升分数；没有可靠分母不计算选用率。",
    }


def sample_data(sample: GuideSample) -> dict[str, object]:
    player = sample.player
    return {
        "match_id": sample.match_id.value,
        "hero_id": sample.hero.hero_id,
        "source": sample.metadata.source.value,
        "fetched_at": sample.metadata.fetched_at.isoformat(),
        "patch": sample.metadata.patch,
        "actual_position": player.position,
        "duration_seconds": sample.duration_seconds,
        "kda": [player.kills, player.deaths, player.assists],
        "imp": player.imp,
        "items_final": list(player.item_ids),
        "backpack_final": list(player.backpack_ids),
        "neutral_final": player.neutral_item_id,
        "label_error": sample.label_error,
        "purchase_event_count": None if sample.purchases is None else len(sample.purchases),
        "purchase_event_limit": 128,
        "upgrade_semantic": "event order, NOT hero level; source_level is zero-based skill rank",
        "upgrades": None
        if sample.upgrades is None
        else [
            {
                "order": i,
                "ability_id": u.ability_id,
                "name": u.name,
                "source_level": u.source_level,
                "time_seconds": u.time_seconds,
                "is_talent": u.is_talent,
            }
            for i, u in enumerate(sample.upgrades, 1)
        ],
        "purchases": None
        if sample.purchases is None
        else [
            {"time_seconds": p.time_seconds, "item_id": p.item_id} for p in sample.purchases[:128]
        ],
    }


def guide_data(guide: HeroGuide | GuideSample) -> dict[str, object]:
    if isinstance(guide, GuideSample):
        return {
            "schema": "dota2forge.guide_sample.v1",
            "sample": sample_data(guide),
            "limitations": "单场观察，非最佳方案；购买不等于库存。",
        }
    return {
        "schema": "dota2forge.guide.v1",
        "hero_id": guide.hero.hero_id,
        "hero_name": guide.hero.display_name,
        "position": guide.position,
        "source": guide.metadata.source.value,
        "fetched_at": guide.metadata.fetched_at.isoformat(),
        "week_index": guide.week_index,
        "notes": list(guide.notes),
        "module_errors": list(guide.module_errors),
        "item_bucket_count": None if guide.items is None else len(guide.items),
        "ability_bucket_count": None if guide.abilities is None else len(guide.abilities),
        "talent_bucket_count": None if guide.talents is None else len(guide.talents),
        "selection": "items最多64桶，abilities最多32桶，talents最多16桶，均按各自观察场次排序",
        "items": None
        if guide.items is None
        else [
            {
                "item_id": i.item_id,
                "minute_bucket": i.minute,
                "instance": i.instance,
                "matches": i.matches,
                "wins": i.wins,
            }
            for i in sorted(guide.items, key=lambda row: (-row.matches, row.minute, row.item_id))[
                :64
            ]
        ],
        "abilities": None
        if guide.abilities is None
        else [
            {
                "ability_id": a.ability_id,
                "source_level": a.level,
                "matches": a.matches,
                "wins": a.wins,
            }
            for a in sorted(guide.abilities, key=lambda row: (-row.matches, row.ability_id))[:32]
        ],
        "talents": None
        if guide.talents is None
        else [
            {"ability_id": a.ability_id, "matches": a.matches, "wins": a.wins}
            for a in sorted(guide.talents, key=lambda row: (-row.matches, row.ability_id))[:16]
        ],
        "samples": [sample_data(s) for s in guide.samples],
        "limitations": "各统计桶分母独立，不合成整套方案胜率。",
    }
