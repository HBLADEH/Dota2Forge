"""Historical detail contracts use entirely synthetic observations and providers."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from dota2forge_core import (
    AccountId,
    DataMetadata,
    DataSource,
    MatchDetail,
    MatchDetailService,
    MatchDetailUnavailable,
    MatchId,
    MatchParseState,
    MatchParticipant,
    ProviderError,
    ProviderErrorCode,
    ValidationError,
    parse_match_id,
)
from dota2forge_core.domain.match_detail import MAX_MATCH_ID


@pytest.mark.parametrize(
    "value", [1, "1", 7000000000, "7000000000", MAX_MATCH_ID, str(MAX_MATCH_ID)]
)
def test_match_id_accepts_canonical_positive_long(value):
    assert parse_match_id(value) == MatchId(int(value))


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        True,
        False,
        1.5,
        None,
        "",
        "0",
        "01",
        "+1",
        "-1",
        " 1",
        "1 ",
        "１",
        "1.0",
        "https://stratz.com/matches/1",
        "第1场",
        MAX_MATCH_ID + 1,
        str(MAX_MATCH_ID + 1),
        "9" * 100,
    ],
)
def test_match_id_does_not_guess_or_coerce(value):
    with pytest.raises(ValidationError):
        parse_match_id(value)


def test_participant_preserves_zero_false_unknown_and_six_slots():
    player = MatchParticipant(
        player_slot=0,
        account_id=AccountId(123),
        display_name="Synthetic",
        is_anonymous=False,
        is_radiant=False,
        hero_id=1,
        kills=0,
        deaths=0,
        assists=0,
        gold_per_minute=0,
        item_ids=(0, 1, None, 0, None, 0),
    )
    assert player.kills == 0 and player.is_radiant is False
    assert player.item_ids[0] == 0 and player.item_ids[2] is None
    assert player.missing_fields == (
        "experience_per_minute",
        "level",
        "last_hits",
        "denies",
        "net_worth",
        "hero_damage",
        "tower_damage",
        "hero_healing",
        "imp",
        "position",
        "lane",
        "neutral_item_id",
        "item_ids[2]",
        "item_ids[4]",
        "backpack_ids[0]",
        "backpack_ids[1]",
        "backpack_ids[2]",
    )
    assert "Synthetic" not in repr(player) and "123" not in repr(player)


@pytest.mark.parametrize(
    "field",
    [
        "player_slot",
        "hero_id",
        "kills",
        "deaths",
        "assists",
        "gold_per_minute",
        "experience_per_minute",
        "level",
        "last_hits",
        "denies",
        "net_worth",
        "hero_damage",
        "tower_damage",
        "hero_healing",
    ],
)
@pytest.mark.parametrize("invalid", [-1, True, 1.5, "1"])
def test_participant_numeric_fields_are_strict(field, invalid):
    with pytest.raises(ValidationError):
        MatchParticipant(**{field: invalid})


@pytest.mark.parametrize(
    "changes",
    [
        {"account_id": 123},
        {"account_id": AccountId(123)},
        {"account_id": AccountId(123), "is_anonymous": True},
        {"is_anonymous": False},
        {"is_anonymous": 1},
        {"is_radiant": 1},
        {"display_name": "Anonymous Name"},
        {"player_slot": 256},
        {"hero_id": 0},
        {"item_ids": []},
        {"item_ids": ()},
        {"item_ids": (0,) * 7},
        {"item_ids": (0, 0, 0, 0, 0, -1)},
        {"item_ids": (0, 0, 0, 0, 0, True)},
        {"account_id": AccountId(123), "is_anonymous": False, "display_name": 0},
    ],
)
def test_participant_rejects_identity_inference_and_invalid_slots(changes):
    with pytest.raises(ValidationError):
        MatchParticipant(**changes)


def test_anonymous_unknown_and_nonparticipating_perspectives(metadata):
    anonymous = MatchParticipant(player_slot=0, is_anonymous=True, is_radiant=True)
    unknown = MatchParticipant(player_slot=1)
    known = MatchParticipant(player_slot=2, account_id=AccountId(123), is_anonymous=False)
    detail = MatchDetail(MatchId(1), metadata, players=(anonymous, unknown, known))
    assert detail.participant(AccountId(123)) is known
    assert detail.participant(AccountId(456)) is None
    assert anonymous.is_anonymous is True and unknown.is_anonymous is None
    assert "account_id" in anonymous.missing_fields
    with pytest.raises(ValidationError):
        detail.participant(123)


@pytest.mark.parametrize(
    "changes",
    [
        {"match_id": 1},
        {"metadata": None},
        {"started_at": datetime(2026, 1, 1)},
        {"parsed_at": datetime(2026, 1, 1)},
        {"duration_seconds": -1},
        {"duration_seconds": True},
        {"game_version_id": -1},
        {"has_stats": 1},
        {"did_radiant_win": 0},
        {"game_mode": 1},
        {"game_mode": ""},
        {"game_mode": "ranked all pick"},
        {"game_mode": "X" * 65},
        {"players": []},
        {"players": (None,)},
        {"players": tuple(MatchParticipant(player_slot=i) for i in range(11))},
        {"players": (MatchParticipant(player_slot=0),) * 2},
        {
            "players": tuple(
                MatchParticipant(player_slot=i, account_id=AccountId(123), is_anonymous=False)
                for i in range(2)
            )
        },
    ],
)
def test_detail_rejects_malformed_metadata_collections_and_values(metadata, changes):
    with pytest.raises(ValidationError):
        replace(MatchDetail(MatchId(1), metadata), **changes)


def test_partial_detail_never_claims_parsing_or_player_completeness(metadata):
    minimal = MatchDetail(MatchId(1), metadata)
    assert len(minimal.missing_fields) == 8 and minimal.players is None
    no_players = replace(
        minimal,
        players=(),
        has_stats=False,
        duration_seconds=0,
        did_radiant_win=False,
        game_version_id=0,
    )
    assert "players" not in no_players.missing_fields
    assert no_players.players == () and no_players.has_stats is False
    assert no_players.duration_seconds == 0 and no_players.did_radiant_win is False
    instant = datetime(2026, 1, 1, tzinfo=UTC)
    parsed = replace(no_players, parsed_at=instant, started_at=instant, game_mode="RANKED_ALL_PICK")
    assert parsed.parsed_at == instant and parsed.metadata.observed_at is None


def test_parse_state_only_uses_upstream_markers_and_observed_shape(metadata):
    assert MatchDetail(MatchId(1), metadata).parse_state is MatchParseState.UNKNOWN
    assert (
        replace(MatchDetail(MatchId(1), metadata), has_stats=False).parse_state
        is MatchParseState.UNPARSED
    )
    assert (
        replace(MatchDetail(MatchId(1), metadata), has_stats=True).parse_state
        is MatchParseState.UPSTREAM_PARSED
    )
    assert (
        replace(MatchDetail(MatchId(1), metadata), players=()).parse_state
        is MatchParseState.PARTIAL
    )
    assert MatchDetailUnavailable(MatchId(1), metadata).parse_state is MatchParseState.NO_DATA


@pytest.mark.parametrize("changes", [{"match_id": 1}, {"metadata": None}])
def test_unavailable_detail_requires_metadata_and_strict_id(metadata, changes):
    with pytest.raises(ValidationError):
        replace(MatchDetailUnavailable(MatchId(1), metadata), **changes)


class SyntheticDetailProvider:
    source = DataSource.FIXTURE

    def __init__(self, result):
        self.result = result
        self.calls = []
        self.failure = None

    async def get_match_detail(self, match_id):
        self.calls.append(match_id)
        if self.failure is not None:
            raise self.failure
        return self.result


def test_historical_service_uses_only_direct_detail_port(metadata, run_async):
    detail = MatchDetail(MatchId(1), metadata)
    provider = SyntheticDetailProvider(detail)
    service = MatchDetailService(provider)
    assert run_async(service.get_match_detail("1")) is detail
    assert provider.calls == [MatchId(1)]
    provider.result = MatchDetailUnavailable(MatchId(1), metadata)
    assert run_async(service.get_match_detail(1)) is provider.result


@pytest.mark.parametrize("value", [True, "01", "第1场", 0, MAX_MATCH_ID + 1])
def test_service_invalid_ids_never_call_provider(metadata, run_async, value):
    provider = SyntheticDetailProvider(MatchDetail(MatchId(1), metadata))
    with pytest.raises(ValidationError):
        run_async(MatchDetailService(provider).get_match_detail(value))
    assert provider.calls == []


@pytest.mark.parametrize("unavailable", [False, True])
def test_service_rejects_wrong_id_source_and_type(metadata, run_async, unavailable):
    result = (
        MatchDetailUnavailable(MatchId(1), metadata)
        if unavailable
        else MatchDetail(MatchId(1), metadata)
    )
    for malformed in (
        None,
        replace(result, match_id=MatchId(2)),
        replace(result, metadata=DataMetadata(DataSource.STRATZ, metadata.fetched_at)),
    ):
        provider = SyntheticDetailProvider(malformed)
        with pytest.raises(ProviderError) as error:
            run_async(MatchDetailService(provider).get_match_detail(1))
        assert error.value.code == ProviderErrorCode.INVALID_RESPONSE
        assert provider.calls == [MatchId(1)]


@pytest.mark.parametrize("code", list(ProviderErrorCode))
def test_detail_service_keeps_classified_failure_and_no_retry(metadata, run_async, code):
    provider = SyntheticDetailProvider(None)
    provider.failure = ProviderError(code, DataSource.FIXTURE)
    with pytest.raises(ProviderError) as error:
        run_async(MatchDetailService(provider).get_match_detail(1))
    assert error.value is provider.failure and len(provider.calls) == 1


def test_detail_service_cancellation_and_bugs_propagate(run_async):
    provider = SyntheticDetailProvider(None)
    for failure in (asyncio.CancelledError(), RuntimeError("synthetic bug")):
        provider.failure = failure
        with pytest.raises(type(failure)) as error:
            run_async(MatchDetailService(provider).get_match_detail(1))
        assert error.value is failure
