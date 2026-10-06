"""Extended match observations keep zero, unknown, invalid and stored values distinct."""

import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from dota2forge_core import DataMetadata, DataSource, MatchDetail, MatchId, ProviderError
from dota2forge_core.infrastructure._opendota_mapping import participant as opendota_player
from dota2forge_core.infrastructure._stratz_detail import participant as stratz_player
from dota2forge_core.infrastructure._subscription_codec import decode_detail, detail_dict
from dota2forge_core.infrastructure.stratz import MATCH_DETAIL_QUERY
from test_stratz_detail import player_row

FIELDS = {
    "level": ("level", "level"),
    "last_hits": ("numLastHits", "last_hits"),
    "denies": ("numDenies", "denies"),
    "net_worth": ("networth", "net_worth"),
    "hero_damage": ("heroDamage", "hero_damage"),
    "tower_damage": ("towerDamage", "tower_damage"),
    "hero_healing": ("heroHealing", "hero_healing"),
}


@pytest.mark.parametrize("field,names", FIELDS.items())
@pytest.mark.parametrize("source", [0, 1])
@pytest.mark.parametrize("value", [None, 0, 43210])
def test_providers_keep_detail_stats(field, names, source, value):
    row = player_row() if source == 0 else {"account_id": 123, "player_slot": 0}
    row[names[source]] = value
    result = stratz_player(row) if source == 0 else opendota_player(row, MatchId(1))
    assert getattr(result, field) == value
    assert (field in result.missing_fields) is (value is None)
    assert names[0] in MATCH_DETAIL_QUERY.split()


@pytest.mark.parametrize("field,names", FIELDS.items())
@pytest.mark.parametrize("source", [0, 1])
@pytest.mark.parametrize("invalid", [True, -1, 1.5, "3"])
def test_providers_reject_invalid_extended_stats(field, names, source, invalid):
    row = player_row() if source == 0 else {}
    row[names[source]] = invalid
    with pytest.raises(ProviderError):
        stratz_player(row) if source == 0 else opendota_player(row, MatchId(1))


def test_detail_storage_roundtrip_and_old_payload_compatibility():
    player = replace(stratz_player(player_row()), **dict.fromkeys(FIELDS, 0))
    detail = MatchDetail(
        MatchId(1),
        DataMetadata(DataSource.FIXTURE, datetime(2026, 10, 6, tzinfo=UTC)),
        players=(player,),
    )
    payload = json.loads(json.dumps(detail_dict(detail)))
    assert decode_detail(payload) == detail
    for field in FIELDS:
        del payload["players"][0][field]
    restored = decode_detail(payload).players[0]
    assert all(getattr(restored, field) is None for field in FIELDS)
    assert restored.kills == 0 and restored.item_ids == player.item_ids
