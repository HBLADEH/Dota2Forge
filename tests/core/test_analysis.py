"""Synthetic economics and purchase observations; IMP is intentionally absent."""

import json
from datetime import UTC, datetime

import httpx
import pytest
from dota2forge_core import (
    AccountId,
    DataMetadata,
    DataSource,
    MatchAnalysis,
    MatchAnalysisService,
    MatchAnalysisUnavailable,
    MatchId,
    MetricSemantic,
    MetricSeries,
    ParticipantAnalysis,
    ProviderError,
    ProviderErrorCode,
    PurchaseEvent,
    ValidationError,
)
from dota2forge_core.infrastructure._analysis_mapping import opendota_analysis, stratz_analysis
from dota2forge_core.infrastructure.opendota import OpenDotaProvider
from dota2forge_core.infrastructure.stratz import MATCH_ANALYSIS_QUERY, StratzProvider

META_STRATZ = DataMetadata(DataSource.STRATZ, datetime(2026, 10, 2, tzinfo=UTC))
META_OPENDOTA = DataMetadata(DataSource.OPENDOTA, datetime(2026, 10, 2, tzinfo=UTC))
MATCH = MatchId(1001)


def stratz_payload(**overrides):
    row = {
        "playerSlot": 0,
        "steamAccountId": 123,
        "stats": {
            "networthPerMinute": [600, 720, 650],
            "itemPurchases": [{"time": 35, "itemId": 1}, {"time": 120, "itemId": 2}],
        },
        **overrides,
    }
    return {"data": {"match": {"id": 1001, "players": [row]}}}


def opendota_payload(**overrides):
    row = {
        "account_id": 123,
        "player_slot": 128,
        "gold_t": [0, 500, 800],
        "xp_t": [0, 100, 260],
        "purchase_log": [{"time": 15, "key": "item_blink", "charges": 1}],
        **overrides,
    }
    return {"match_id": 1001, "players": [row]}


def test_source_mappings_keep_metric_semantics_missing_and_anonymous():
    stratz = stratz_analysis(stratz_payload(), MATCH, META_STRATZ)
    assert isinstance(stratz, MatchAnalysis)
    participant = stratz.participants[0]
    assert participant.account_id == AccountId(123)
    assert participant.metrics[0].semantic is MetricSemantic.NETWORTH_LEVEL
    assert participant.metrics[0].values == (600, 720, 650)
    assert participant.purchases[0] == PurchaseEvent(35, 1)

    opendota = opendota_analysis(opendota_payload(), MATCH, META_OPENDOTA)
    assert isinstance(opendota, MatchAnalysis)
    participant = opendota.participants[0]
    assert {series.semantic for series in participant.metrics} == {
        MetricSemantic.COLLECTED_GOLD,
        MetricSemantic.EXPERIENCE_TOTAL,
    }
    assert participant.purchases[0].item_key == "item_blink"

    anonymous = opendota_analysis(
        opendota_payload(account_id=4294967295, personaname="must not be copied"),
        MATCH,
        META_OPENDOTA,
    )
    assert anonymous.participants[0].account_id is None


def test_source_null_and_missing_analysis_are_distinct():
    assert isinstance(
        stratz_analysis({"data": {"match": None}}, MATCH, META_STRATZ), MatchAnalysisUnavailable
    )
    missing = stratz_analysis(
        {"data": {"match": {"id": 1001, "players": None}}}, MATCH, META_STRATZ
    )
    assert isinstance(missing, MatchAnalysis) and missing.participants is None
    empty = opendota_analysis({"match_id": 1001, "players": []}, MATCH, META_OPENDOTA)
    assert isinstance(empty, MatchAnalysis) and empty.participants == ()


@pytest.mark.parametrize(
    "payload, source",
    [
        ({"data": {"match": {"id": 1002, "players": []}}}, DataSource.STRATZ),
        (
            {
                "data": {
                    "match": {
                        "id": 1001,
                        "players": [
                            {
                                "playerSlot": 0,
                                "steamAccountId": 123,
                                "stats": {"networthPerMinute": [-1]},
                            }
                        ],
                    }
                }
            },
            DataSource.STRATZ,
        ),
        (
            {"match_id": 1001, "players": [{"account_id": 123, "player_slot": 256}]},
            DataSource.OPENDOTA,
        ),
        (
            {
                "match_id": 1001,
                "players": [{"account_id": 123, "player_slot": 0, "gold_t": [1, "bad"]}],
            },
            DataSource.OPENDOTA,
        ),
        (
            {
                "match_id": 1001,
                "players": [
                    {
                        "account_id": 123,
                        "player_slot": 0,
                        "purchase_log": [{"time": -1, "key": "item"}],
                    }
                ],
            },
            DataSource.OPENDOTA,
        ),
    ],
)
def test_malformed_analysis_is_fixed_source_error(payload, source):
    mapper = stratz_analysis if source is DataSource.STRATZ else opendota_analysis
    metadata = META_STRATZ if source is DataSource.STRATZ else META_OPENDOTA
    with pytest.raises(ProviderError) as error:
        mapper(payload, MATCH, metadata)
    assert error.value.code is ProviderErrorCode.INVALID_RESPONSE
    assert error.value.source is source


def test_provider_analysis_queries_are_independent_and_do_not_request_imp(clock, run_async):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=stratz_payload())

    async def check(provider):
        result = await provider.get_match_analysis(MATCH)
        assert isinstance(result, MatchAnalysis)
        assert "imp" not in MATCH_ANALYSIS_QUERY.lower()
        assert "networthPerMinute" in MATCH_ANALYSIS_QUERY
        body = json.loads(requests[0].content)
        assert body["variables"] == {"matchId": 1001}
        assert "1001" not in body["query"]

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            await check(StratzProvider(client, token="synthetic", clock=clock))

    run_async(run())


def test_opendota_provider_analysis_and_service_validate_source(clock, run_async):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=opendota_payload()))
        ) as client:
            provider = OpenDotaProvider(client, clock=clock)
            result = await MatchAnalysisService(provider).get_match_analysis("1001")
            assert isinstance(result, MatchAnalysis)
            assert result.metadata.source is DataSource.OPENDOTA
            with pytest.raises(ValidationError):
                await MatchAnalysisService(provider).get_match_analysis("01")

    run_async(run())


def test_analysis_domain_rejects_duplicate_or_invalid_values():
    with pytest.raises(ValidationError):
        MetricSeries("gold", MetricSemantic.COLLECTED_GOLD, (1,), interval_seconds=0)
    with pytest.raises(ValidationError):
        PurchaseEvent(1)
    with pytest.raises(ValidationError):
        MatchAnalysis(
            MATCH,
            META_STRATZ,
            (ParticipantAnalysis(None, 0), ParticipantAnalysis(None, 0)),
        )
