"""Restricted feature arguments shared by command and native-tool consumers."""

import re
from dataclasses import dataclass

from .domain.errors import ValidationError
from .domain.hero_features import MetaRequest, MetaSort, RankBracket
from .domain.hero_items import normalize_hero_name
from .domain.match_detail import MatchId, parse_match_id
from .domain.review import ReviewTopic

FEATURE_COMMANDS = frozenset({"do强势", "do攻略", "do攻略样例", "do复盘"})
RANK_INPUTS = dict(
    zip(
        ("全部", "未定级", "先锋", "卫士", "中军", "统帅", "传奇", "万古", "超凡", "冠绝"),
        RankBracket,
        strict=True,
    )
)
TOPIC_INPUTS = {
    "概览": ReviewTopic.OVERVIEW,
    "经济": ReviewTopic.ECONOMY,
    "装备": ReviewTopic.ITEMS,
    "对线": ReviewTopic.LANING,
    "团队": ReviewTopic.TEAM,
}


@dataclass(frozen=True, slots=True)
class FeatureRequest:
    keyword: str
    meta: MetaRequest = MetaRequest()
    hero_name: str | None = None
    position: int = 1
    match_id: MatchId | None = None
    match_index: int | None = None
    latest: bool = False
    detailed: bool = False
    report: bool = False
    topic: ReviewTopic = ReviewTopic.OVERVIEW


def parse_feature(keyword: str, text: str) -> FeatureRequest:
    if (
        not isinstance(text, str)
        or len(text) > 160
        or any(ord(c) < 32 and c not in "\r\n\t" for c in text)
    ):
        raise ValidationError("Invalid feature arguments")
    if keyword.startswith("do") and keyword.endswith("攻略") and keyword != "do攻略":
        text, keyword = keyword[2:-2] + " " + text, "do攻略"
    if keyword not in FEATURE_COMMANDS:
        raise ValidationError("Unknown feature command")
    tokens = text.split()
    if keyword == "do强势":
        position = None
        rank = RankBracket.ALL
        days = 7
        sort = MetaSort.RELIABLE
        seen: set[str] = set()
        for token in tokens:
            if re.fullmatch("[1-5]号位", token):
                key, position = "position", int(token[0])
            elif token.startswith("段位=") and token[3:] in RANK_INPUTS:
                key, rank = "rank", RANK_INPUTS[token[3:]]
            elif token in {"7天", "14天"}:
                key, days = "days", int(token[:-1])
            elif token in {"可靠度", "胜率"}:
                key, sort = "sort", MetaSort.RELIABLE if token == "可靠度" else MetaSort.WIN_RATE
            else:
                raise ValidationError("Invalid meta filter")
            if key in seen:
                raise ValidationError("Duplicate filter")
            seen.add(key)
        return FeatureRequest(keyword, meta=MetaRequest(position, rank, days, sort))
    detailed = "详细" in tokens
    report = "报告" in tokens
    if tokens.count("详细") > 1 or tokens.count("报告") > 1:
        raise ValidationError("Duplicate output option")
    tokens = [v for v in tokens if v not in {"详细", "报告"}]
    if keyword == "do攻略":
        if report:
            raise ValidationError("Unexpected guide option")
        positions = [v for v in tokens if re.fullmatch("[1-5]号位", v)]
        if len(positions) > 1:
            raise ValidationError("Duplicate position")
        name = " ".join(v for v in tokens if v not in positions)
        normalize_hero_name(name)
        return FeatureRequest(
            keyword,
            hero_name=name,
            position=int(positions[0][0]) if positions else 1,
            detailed=detailed,
        )
    if keyword == "do攻略样例":
        if not tokens or report or detailed:
            raise ValidationError("Expected sample match and hero")
        match_id = parse_match_id(tokens[0])
        name = " ".join(tokens[1:])
        normalize_hero_name(name)
        return FeatureRequest(keyword, hero_name=name, match_id=match_id)
    if detailed:
        raise ValidationError("Use report for an optional full review")
    match = None
    index = None
    latest = False
    topic = ReviewTopic.OVERVIEW
    if tokens:
        first = tokens.pop(0)
        if first == "最近":
            latest = True
        elif selected := re.fullmatch(r"第([1-9][0-9]?)场", first):
            index = int(selected[1])
        elif first in TOPIC_INPUTS:
            topic = TOPIC_INPUTS[first]
        else:
            match = parse_match_id(first)
    review_hero = " ".join(tokens) or None
    if review_hero is not None:
        normalize_hero_name(review_hero)
    return FeatureRequest(
        keyword,
        hero_name=review_hero,
        match_id=match,
        match_index=index,
        latest=latest,
        report=report,
        topic=topic,
    )
