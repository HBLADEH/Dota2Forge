"""Source selection and progressively loaded review guidance, no model or network."""

import asyncio
import json
from dataclasses import replace

import pytest
from dota2forge_core import (
    DataSource,
    MatchAnalysisUnavailable,
    MatchId,
    MetricSemantic,
    MetricSeries,
    ProviderError,
    ProviderErrorCode,
    ReviewEvidence,
    ReviewService,
    ReviewTopic,
    ValidationError,
    evidence_data,
)
from dota2forge_core.infrastructure.hero_catalog import load_hero_catalog
from dota2forge_core.infrastructure.review_guidance import (
    SKILL_NAME,
    guidance,
    review_payload,
    skill_directory,
    suggested_topic,
)
from test_hero_features import review_source


class Source:
    def __init__(self, source, detail, analysis):
        self.source, self.detail, self.analysis = source, detail, analysis
        self.calls = []

    async def get_match_detail(self, match):
        self.calls.append(("detail", match.value))
        if isinstance(self.detail, BaseException):
            raise self.detail
        return self.detail

    async def get_match_analysis(self, match):
        self.calls.append(("analysis", match.value))
        if isinstance(self.analysis, BaseException):
            raise self.analysis
        return self.analysis


def sources():
    _, detail, analysis = review_source()
    primary = Source(DataSource.STRATZ, detail, analysis)
    metadata = replace(detail.metadata, source=DataSource.OPENDOTA)
    secondary = Source(
        DataSource.OPENDOTA,
        replace(detail, metadata=metadata, game_version_id=None),
        replace(
            analysis,
            metadata=metadata,
            team_metrics=(),
            participants=(
                replace(
                    analysis.participants[0],
                    metrics=(MetricSeries("gold_t", MetricSemantic.COLLECTED_GOLD, (0, 200, 400)),),
                ),
            ),
        ),
    )
    return primary, secondary


def service(primary, secondary):
    catalog = load_hero_catalog()
    return ReviewService(
        primary, primary, catalog, fallback=ReviewService(secondary, secondary, catalog)
    )


def test_available_stratz_remains_primary_without_reading_opendota(run_async):
    primary, secondary = sources()
    result = run_async(service(primary, secondary).get_context(22, "斧王"))
    assert result.detail.metadata.source == DataSource.STRATZ
    assert result.source_attempts == () and not secondary.calls


@pytest.mark.parametrize("stage", ["detail", "analysis", "basic"])
@pytest.mark.parametrize("code", ["not_found", "timeout", "unavailable", "rate_limited"])
def test_read_only_fallback_selects_one_whole_source_and_preserves_reason(run_async, stage, code):
    primary, secondary = sources()
    if stage == "basic":
        primary.analysis = MatchAnalysisUnavailable(MatchId(22), primary.detail.metadata)
    else:
        setattr(primary, stage, ProviderError(ProviderErrorCode(code), DataSource.STRATZ))
    result = run_async(service(primary, secondary).get_context(22, "斧王"))
    assert result.detail.metadata.source == result.analysis.metadata.source == DataSource.OPENDOTA
    assert result.source_attempts == (
        (DataSource.STRATZ, "basic_only" if stage == "basic" else code),
    )
    assert secondary.calls == [("detail", 22), ("analysis", 22)]
    payload = evidence_data(result)
    assert payload["economic_series"][0]["semantic"] == "collected_gold"
    assert payload["team_series"] == []  # Never fills from the other source.
    assert payload["game_version_id"] is None
    assert payload["source_attempts"][0]["source"] == "stratz"


@pytest.mark.parametrize("stage", ["detail", "analysis"])
@pytest.mark.parametrize("code", ["private", "authentication", "invalid_response"])
def test_privacy_credentials_and_invalid_responses_do_not_silently_switch(run_async, stage, code):
    primary, secondary = sources()
    setattr(primary, stage, ProviderError(ProviderErrorCode(code), DataSource.STRATZ))
    if stage == "detail":
        with pytest.raises(ProviderError) as error:
            run_async(service(primary, secondary).get_context(22, "斧王"))
        assert error.value.code.value == code
    else:
        result = run_async(service(primary, secondary).get_context(22, "斧王"))
        assert result.analysis_error == code and result.analysis is None
    assert not secondary.calls


@pytest.mark.parametrize("secondary_state", ["missing", "timeout", "invalid"])
def test_failed_or_equally_basic_fallback_preserves_primary_facts(run_async, secondary_state):
    primary, secondary = sources()
    primary.analysis = MatchAnalysisUnavailable(MatchId(22), primary.detail.metadata)
    if secondary_state == "missing":
        secondary.analysis = MatchAnalysisUnavailable(MatchId(22), secondary.detail.metadata)
    elif secondary_state == "timeout":
        secondary.detail = ProviderError(ProviderErrorCode.TIMEOUT, DataSource.OPENDOTA)
    else:
        secondary.analysis = ProviderError(ProviderErrorCode.INVALID_RESPONSE, DataSource.OPENDOTA)
    result = run_async(service(primary, secondary).get_context(22, "斧王"))
    assert result.detail.metadata.source == DataSource.STRATZ
    assert len(result.source_attempts) == 2
    assert (
        result.source_attempts[-1][1]
        == {"missing": "basic_only", "timeout": "timeout", "invalid": "invalid_response"}[
            secondary_state
        ]
    )


@pytest.mark.parametrize("error", [asyncio.CancelledError, RuntimeError])
def test_cancellation_and_program_errors_never_trigger_fallback(run_async, error):
    primary, secondary = sources()
    primary.detail = error()
    with pytest.raises(error):
        run_async(service(primary, secondary).get_context(22, "斧王"))
    assert not secondary.calls


def test_both_sources_fail_report_original_error_and_reject_wrong_source_order(run_async):
    primary, secondary = sources()
    primary.detail = ProviderError(ProviderErrorCode.TIMEOUT, DataSource.STRATZ)
    secondary.detail = ProviderError(ProviderErrorCode.UNAVAILABLE, DataSource.OPENDOTA)
    with pytest.raises(ProviderError) as error:
        run_async(service(primary, secondary).get_context(22, "斧王"))
    assert error.value.source == DataSource.STRATZ and error.value.code == ProviderErrorCode.TIMEOUT
    with pytest.raises(ValidationError):
        service(secondary, primary)


def test_invalid_provider_type_does_not_masquerade_as_missing_or_trigger_fallback(run_async):
    primary, secondary = sources()
    primary.detail = object()
    with pytest.raises(ProviderError) as error:
        run_async(service(primary, secondary).get_context(22, "斧王"))
    assert error.value.code == ProviderErrorCode.INVALID_RESPONSE and not secondary.calls
    primary, secondary = sources()
    primary.analysis = object()
    result = run_async(service(primary, secondary).get_context(22, "斧王"))
    assert result.analysis_error == "invalid_response" and not secondary.calls


def test_fallback_cannot_replace_the_valid_primary_perspective_with_a_missing_hero(run_async):
    primary, secondary = sources()
    primary.analysis = MatchAnalysisUnavailable(MatchId(22), primary.detail.metadata)
    secondary.detail = replace(secondary.detail, players=())
    result = run_async(service(primary, secondary).get_context(22, "斧王"))
    assert result.detail.metadata.source == DataSource.STRATZ and result.target_slot == 0
    assert result.source_attempts[-1] == (DataSource.OPENDOTA, "invalid_response")


def test_exact_checkpoints_and_availability_keep_units_sides_and_no_identity():
    primary, _ = sources()
    analysis = replace(
        primary.analysis,
        participants=(
            replace(
                primary.analysis.participants[0],
                metrics=(
                    MetricSeries(
                        "networth",
                        MetricSemantic.NETWORTH_LEVEL,
                        tuple(1000 + i * 100 for i in range(11)),
                    ),
                ),
                purchases=(),
            ),
        ),
        team_metrics=(
            MetricSeries(
                "lead",
                MetricSemantic.RADIANT_NETWORTH_LEAD,
                tuple(-100 * i for i in range(12)),
                -60,
            ),
        ),
    )
    evidence = ReviewEvidence(primary.detail, analysis, 0)
    payload = review_payload(evidence, ReviewTopic.ECONOMY)
    assert payload["checkpoints"] == [
        {"semantic": "networth_level", "time_seconds": 300, "value": 1500, "perspective": "target"},
        {"semantic": "networth_level", "time_seconds": 600, "value": 2000, "perspective": "target"},
        {
            "semantic": "radiant_networth_lead",
            "time_seconds": 300,
            "value": -600,
            "perspective": "radiant",
        },
        {
            "semantic": "radiant_networth_lead",
            "time_seconds": 600,
            "value": -1100,
            "perspective": "radiant",
        },
    ]
    assert payload["availability"]["purchases"] == "empty"
    assert payload["availability"]["teamfight_events"] == "not_integrated"
    assert "Synthetic Private Label" not in json.dumps(payload)
    sparse = replace(
        analysis,
        participants=(
            replace(
                analysis.participants[0],
                metrics=(
                    MetricSeries("networth", MetricSemantic.NETWORTH_LEVEL, (0, 100, 200), 0, 119),
                ),
            ),
        ),
        team_metrics=(),
    )
    assert evidence_data(replace(evidence, analysis=sparse))["checkpoints"] == []


def test_display_labels_do_not_change_evidence_hash_or_fill_unknown_names():
    primary, _ = sources()
    evidence = ReviewEvidence(primary.detail, primary.analysis, 0)
    plain = review_payload(evidence, ReviewTopic.ITEMS)
    labeled = review_payload(
        evidence,
        ReviewTopic.ITEMS,
        hero_labels={2: "斧王"},
        item_label=lambda identifier: "合成装备" if identifier == 4 else f"装备 ID {identifier}",
    )
    assert labeled["display_names"]["heroes"] == {"2": "斧王"}
    assert labeled["display_names"]["items"]["4"] == "合成装备"
    assert labeled["evidence_id"] == plain["evidence_id"]
    assert labeled["purchases"] == plain["purchases"]
    unknown = review_payload(evidence, ReviewTopic.ITEMS, hero_labels={})
    assert unknown["display_names"]["heroes"] == {"2": "英雄 ID 2"}


@pytest.mark.parametrize(
    "query,topic",
    [
        ("出装顺序怎么改", "items"),
        ("10分钟经济", "economy"),
        ("对线补刀", "laning"),
        ("团战是谁的锅", "team"),
        ("这局有什么问题", "overview"),
    ],
)
def test_guide_is_progressive_and_resource_paths_are_fixed(query, topic):
    selected = suggested_topic(query)
    assert selected == ReviewTopic(topic)
    result = guidance(selected)
    assert result["name"] == SKILL_NAME and result["topic"] == topic
    assert (skill_directory() / SKILL_NAME / result["resource"]).is_file()
    assert len(result["instructions"] + result["topic_guide"]) < 5000
    with pytest.raises(ValueError):
        guidance("../../private")


@pytest.mark.parametrize(
    "attempts", [[("stratz", "timeout")], ((DataSource.STRATZ, "raw exception"),)]
)
def test_source_attempts_are_bounded_typed_codes(attempts):
    primary, _ = sources()
    with pytest.raises(ValidationError):
        ReviewEvidence(primary.detail, None, source_attempts=attempts)
