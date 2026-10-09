"""Source IMP, signed advantage series, derived evidence and storage compatibility."""

import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from dota2forge_core import (
    DataMetadata,
    DataSource,
    MatchAnalysis,
    MatchDetail,
    MatchId,
    MatchParticipant,
    MatchReport,
    MetricSemantic,
    MetricSeries,
    ProviderError,
    ProviderErrorCode,
    ValidationError,
)
from dota2forge_core.infrastructure._analysis_mapping import stratz_analysis
from dota2forge_core.infrastructure._stratz_detail import participant
from dota2forge_core.infrastructure._subscription_codec import (
    analysis_dict,
    decode_analysis,
    decode_detail,
    detail_dict,
)
from dota2forge_core.infrastructure.stratz import MATCH_DETAIL_QUERY
from test_stratz_detail import player_row

META = DataMetadata(DataSource.STRATZ, datetime(2026, 10, 9, tzinfo=UTC))


@pytest.mark.parametrize("value", [None, -32768, -47, 0, 66, 32767])
def test_imp_mapping_preserves_source_short(value):
    row = player_row()
    row["imp"] = value
    result = participant(row)
    assert result.imp == value
    assert ("imp" in result.missing_fields) is (value is None)
    assert "imp" in MATCH_DETAIL_QUERY.split()


@pytest.mark.parametrize("value", [True, 1.5, "-47", -32769, 32768])
def test_invalid_imp_never_becomes_zero(value):
    row = player_row()
    row["imp"] = value
    with pytest.raises(ProviderError) as error:
        participant(row)
    assert error.value.code is ProviderErrorCode.INVALID_RESPONSE
    with pytest.raises(ValidationError):
        MatchParticipant(imp=value)


def test_imp_is_stratz_only_and_equipment_source_fields_roundtrip():
    row = player_row()
    row.update(
        imp=-47,
        position="POSITION_4",
        lane="SAFE_LANE",
        backpack0Id=0,
        backpack1Id=1,
        backpack2Id=None,
        neutral0Id=0,
    )
    player = participant(row)
    assert player.backpack_ids == (0, 1, None) and player.neutral_item_id == 0
    detail = MatchDetail(MatchId(1), META, players=(player,))
    assert decode_detail(json.loads(json.dumps(detail_dict(detail)))) == detail
    with pytest.raises(ValidationError):
        replace(detail, metadata=replace(META, source=DataSource.OPENDOTA))
    legacy = json.loads(json.dumps(detail_dict(detail)))
    for key in ("imp", "position", "lane", "backpack_ids", "neutral_item_id"):
        del legacy["players"][0][key]
    restored = decode_detail(legacy).players[0]
    assert restored.imp is None and restored.backpack_ids == (None,) * 3


@pytest.mark.parametrize(
    "key,value",
    [
        ("position", 1),
        ("lane", False),
        ("backpack0Id", -1),
        ("neutral0Id", True),
    ],
)
def test_new_field_types_remain_strict(key, value):
    row = player_row()
    row[key] = value
    with pytest.raises(ProviderError):
        participant(row)


def test_signed_team_series_keep_source_interval_and_legacy_storage():
    raw = {
        "data": {
            "match": {
                "id": 1,
                "players": [],
                "radiantNetworthLeads": [-200, 0, 300],
                "radiantExperienceLeads": [100, -100, 200],
            }
        }
    }
    result = stratz_analysis(raw, MatchId(1), META)
    assert isinstance(result, MatchAnalysis)
    gold, xp = result.team_metrics
    assert gold.values == (-200, 0, 300) and gold.start_seconds == -60
    assert xp.semantic is MetricSemantic.RADIANT_EXPERIENCE_LEAD
    assert gold.interval_seconds == 60
    encoded = json.loads(json.dumps(analysis_dict(result)))
    assert decode_analysis(encoded) == result
    del encoded["team_metrics"]
    assert decode_analysis(encoded).team_metrics == ()


@pytest.mark.parametrize("values", [[True], [1.5], ["2"], [0] * 361])
def test_team_series_do_not_coerce_malformed_values(values):
    raw = {"data": {"match": {"id": 1, "players": [], "radiantNetworthLeads": values}}}
    with pytest.raises(ProviderError):
        stratz_analysis(raw, MatchId(1), META)


def test_performance_ranking_retains_ties_missing_zero_and_team_evidence():
    players = tuple(
        MatchParticipant(
            player_slot=i,
            is_radiant=i < 5,
            kills=2,
            deaths=0,
            assists=3,
            imp=score,
            hero_damage=1000,
        )
        for i, score in enumerate((66, -47, None, 0, 66, 30, -7, -23, 9, 48))
    )
    detail = MatchDetail(MatchId(1), META, players=players)
    report = MatchReport(MatchId(1), META, None, None, detail, MatchAnalysis(MatchId(1), META, ()))
    assert [player.player_slot for player in report.strong_performers] == [0, 4, 9]
    assert [player.imp for player in report.weak_performers] == [-47, -23, -7]
    assert len(report.imp_ranking) == 9 and report.team_total(True, "kills") == 10
    assert report.participation(players[0]) == 0.5
    incomplete = replace(report, detail=replace(detail, players=players[:4]))
    assert incomplete.team_total(True, "kills") is None
    assert incomplete.participation(players[0]) is None
    with pytest.raises(ValidationError):
        report.team_total(True, "invented")
    series = MetricSeries("lead", MetricSemantic.RADIANT_NETWORTH_LEAD, (-1, 0), -60)
    with pytest.raises(ValidationError):
        MatchAnalysis(MatchId(1), META, (), (series, series))
    with pytest.raises(ValidationError):
        MatchAnalysis(MatchId(1), replace(META, source=DataSource.OPENDOTA), (), (series,))
