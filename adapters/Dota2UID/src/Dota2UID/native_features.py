"""Adapter-owned native conversation orchestration, independent of the host SDK."""

import re
from collections.abc import Callable, Hashable

from dota2forge_core import (
    HeroFeatureService,
    PlayerBinding,
    ReviewChartRequest,
    ReviewService,
    ValidationError,
    chart_data,
)
from dota2forge_core.feature_requests import FeatureRequest
from dota2forge_core.feature_tools import guide_data, meta_data, parse_tool
from dota2forge_core.infrastructure.review_guidance import review_payload, suggested_topic
from dota2forge_core.review import REVIEW_INSTRUCTION
from dota2forge_renderer import AsyncRenderer, ImageArtifact, RenderError, ReviewDataCard
from dota2forge_renderer.features import hero_names
from dota2forge_renderer.hero_items import item_name

from .review_sessions import ReviewSessionStore


def review_related(query: str) -> bool:
    return (
        suggested_topic(query).value != "overview"
        or any(
            word in query.lower()
            for word in (
                "复盘",
                "dota",
                "经济",
                "出装",
                "装备",
                "对线",
                "团战",
                "补刀",
                "净资产",
                "优势",
                "这件",
                "那件",
                "这局",
                "这把",
                "本局",
                "购买",
                "补图",
                "曲线",
                "bkb",
            )
        )
        or (
            re.fullmatch(
                r"(?:为什么|那为什么|那怎么办|有什么问题|哪里有问题|怎么改进|继续|还有呢|能解释一下|画张图)[呢吗啊？?！!。\s]*",
                query.strip(),
            )
            is not None
        )
    )


class NativeFeatures:
    def __init__(
        self,
        heroes: HeroFeatureService,
        review: ReviewService,
        renderer: Callable[[], AsyncRenderer | None],
        sessions: ReviewSessionStore,
    ) -> None:
        self._heroes, self._review, self._renderer, self.sessions = (
            heroes,
            review,
            renderer,
            sessions,
        )

    def hint(
        self, key: Hashable, generation: object, query: str, history_count: int | None = None
    ) -> str | None:
        entry = self.sessions.peek(key, generation, history_count)
        if entry is None or not review_related(query):
            return None
        return (
            REVIEW_INSTRUCTION + f" 当前复盘比赛 {entry.match_id}；"
            f"先调用 get_dota2_review_context(topic='{suggested_topic(query).value}') "
            "获取本轮主题的详细事实，"
            "可省略 match_id 沿用本场和当前英雄。不要仅基于之前回复的短摘要分析。"
            "遵循工具的 analysis_guide 复盘Skill及专题；宿主支持时可加载 dota2-review。"
        )

    async def begin(
        self,
        key: Hashable,
        generation: object,
        binding: PlayerBinding | None,
        request: FeatureRequest,
        match_id: int,
    ) -> dict[str, object]:
        entry = self.sessions.get(key, generation, binding)
        hero = (
            request.hero_name
            if request.hero_name is not None
            else (entry.hero_name if entry is not None and entry.match_id == match_id else None)
        )
        evidence = await self._review.get_context(
            match_id, hero, account=None if binding is None else binding.account_id
        )
        self.sessions.remember(key, generation, binding, match_id, hero, evidence)
        return review_payload(
            evidence, request.topic, hero_labels=hero_names(), item_label=item_name
        )

    async def tool(
        self,
        key: Hashable,
        generation: object,
        binding: PlayerBinding | None,
        name: str,
        args: dict[str, object],
    ) -> tuple[dict[str, object], ImageArtifact | None]:
        request = parse_tool(name, args)
        if name == "get_dota2_meta":
            return meta_data(await self._heroes.get_meta(request.meta)), None
        if name == "get_dota2_hero_guide":
            assert request.hero_name is not None
            result = (
                await self._heroes.get_guide(request.hero_name, request.position)
                if request.match_id is None
                else await self._heroes.get_sample(request.match_id.value, request.hero_name)
            )
            return guide_data(result), None
        entry = self.sessions.get(key, generation, binding)
        match_id = (
            request.match_id.value
            if request.match_id is not None
            else (None if entry is None else entry.match_id)
        )
        if match_id is None:
            raise ValidationError("没有有效复盘定位，请先提供比赛 ID 或执行 do复盘。")
        hero = (
            request.hero_name
            if request.hero_name is not None
            else (entry.hero_name if entry is not None and entry.match_id == match_id else None)
        )
        evidence = (
            self.sessions.evidence(entry)
            if entry is not None and entry.match_id == match_id and entry.hero_name == hero
            else None
        )
        if evidence is None:
            evidence = await self._review.get_context(
                match_id, hero, account=None if binding is None else binding.account_id
            )
        if name == "get_dota2_review_context":
            self.sessions.remember(key, generation, binding, match_id, hero, evidence)
            return review_payload(
                evidence, request.topic, hero_labels=hero_names(), item_label=item_name
            ), None
        assert request.chart is not None
        chart = request.chart
        if "end_seconds" not in args and evidence.detail.duration_seconds is not None:
            chart = ReviewChartRequest(
                chart.kind, chart.start_seconds, evidence.detail.duration_seconds
            )
        payload = chart_data(evidence, chart)
        self.sessions.remember(key, generation, binding, match_id, hero, evidence)
        renderer = self._renderer()
        if renderer is None:
            payload["render_error"] = "unavailable"
            return payload, None
        try:
            return payload, await renderer.render(ReviewDataCard(evidence, chart))
        except RenderError:
            payload["render_error"] = "unavailable"
            return payload, None
