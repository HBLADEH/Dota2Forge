"""Map REST observations without copying STRATZ's field or parser meanings."""

from datetime import UTC, datetime
from typing import cast

from ..domain.errors import ProviderErrorCode, ValidationError
from ..domain.identity import MAX_ACCOUNT_ID, AccountId
from ..domain.match_detail import (
    MatchDetail,
    MatchDetailResult,
    MatchDetailUnavailable,
    MatchId,
    MatchParticipant,
)
from ..domain.models import DataMetadata, MatchSummary, PlayerProfile
from ._opendota_http import failure


def object_value(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    result = cast(dict[str, object], value)
    if "error" in result:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    return result


def integer(value: object, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    return value


def optional_integer(value: object) -> int | None:
    return None if value is None else integer(value)


def optional_bool(value: object) -> bool | None:
    if value is not None and type(value) is not bool:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    return value


def optional_time(value: object) -> datetime | None:
    return None if value is None else datetime.fromtimestamp(integer(value), UTC)


def radiant_slot(value: object) -> tuple[int | None, bool | None]:
    slot = optional_integer(value)
    if slot is not None and slot > 255:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    return slot, None if slot is None else slot < 128


def profile(payload: object, account_id: AccountId, metadata: DataMetadata) -> PlayerProfile:
    row = object_value(payload)
    if "profile" not in row:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    raw = row["profile"]
    name: str | None = None
    if raw is not None:
        player = object_value(raw)
        if integer(player.get("account_id"), 1) != account_id.value:
            raise failure(ProviderErrorCode.INVALID_RESPONSE)
        raw_name = player.get("personaname")
        if raw_name is not None and not isinstance(raw_name, str):
            raise failure(ProviderErrorCode.INVALID_RESPONSE)
        name = raw_name
    # A null profile or fh_unavailable flag does not deny all available rank data.
    return PlayerProfile(account_id, metadata, name, optional_integer(row.get("rank_tier")))


def match_rows(
    payload: object, account_id: AccountId, metadata: DataMetadata, limit: int
) -> tuple[MatchSummary, ...]:
    if not isinstance(payload, list) or len(payload) > limit:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    results = []
    for raw in payload:
        row = object_value(raw)
        if "account_id" in row and integer(row["account_id"], 1) != account_id.value:
            raise failure(ProviderErrorCode.INVALID_RESPONSE)
        _, radiant = radiant_slot(row.get("player_slot"))
        won = optional_bool(row.get("radiant_win"))
        started_at = datetime.fromtimestamp(integer(row.get("start_time")), UTC)
        results.append(
            MatchSummary(
                match_id=MatchId(integer(row.get("match_id"), 1)).value,
                account_id=account_id,
                started_at=started_at,
                metadata=metadata,
                hero_id=optional_integer(row.get("hero_id")),
                duration_seconds=optional_integer(row.get("duration")),
                kills=optional_integer(row.get("kills")),
                deaths=optional_integer(row.get("deaths")),
                assists=optional_integer(row.get("assists")),
                gold_per_minute=optional_integer(row.get("gold_per_min")),
                experience_per_minute=optional_integer(row.get("xp_per_min")),
                is_win=None if radiant is None or won is None else radiant == won,
            )
        )
    return tuple(
        sorted(results, key=lambda match: (match.started_at, match.match_id), reverse=True)
    )


def participant(raw: object, match_id: MatchId) -> MatchParticipant:
    row = object_value(raw)
    if "match_id" in row and integer(row["match_id"], 1) != match_id.value:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    account_number = optional_integer(row.get("account_id"))
    anonymous = None if account_number is None else account_number in {0, MAX_ACCOUNT_ID + 1}
    account = None if account_number is None or anonymous else AccountId(account_number)
    name = row.get("personaname")
    if name is not None and not isinstance(name, str):
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    slot, radiant = radiant_slot(row.get("player_slot"))
    if "isRadiant" in row and optional_bool(row["isRadiant"]) != radiant:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    return MatchParticipant(
        player_slot=slot,
        account_id=account,
        display_name=name if account is not None else None,
        is_anonymous=anonymous,
        is_radiant=radiant,
        hero_id=optional_integer(row.get("hero_id")),
        kills=optional_integer(row.get("kills")),
        deaths=optional_integer(row.get("deaths")),
        assists=optional_integer(row.get("assists")),
        gold_per_minute=optional_integer(row.get("gold_per_min")),
        experience_per_minute=optional_integer(row.get("xp_per_min")),
        level=optional_integer(row.get("level")),
        last_hits=optional_integer(row.get("last_hits")),
        denies=optional_integer(row.get("denies")),
        net_worth=optional_integer(row.get("net_worth")),
        hero_damage=optional_integer(row.get("hero_damage")),
        tower_damage=optional_integer(row.get("tower_damage")),
        hero_healing=optional_integer(row.get("hero_healing")),
        item_ids=tuple(optional_integer(row.get(f"item_{index}")) for index in range(6)),
    )


def detail(payload: object, match_id: MatchId, metadata: DataMetadata) -> MatchDetailResult:
    if payload is None:
        return MatchDetailUnavailable(match_id, metadata)
    row = object_value(payload)
    if integer(row.get("match_id"), 1) != match_id.value:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    players = row.get("players")
    if players is not None and (not isinstance(players, list) or len(players) > 10):
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    mode = optional_integer(row.get("game_mode"))
    try:
        return MatchDetail(
            match_id=match_id,
            metadata=metadata,
            started_at=optional_time(row.get("start_time")),
            duration_seconds=optional_integer(row.get("duration")),
            did_radiant_win=optional_bool(row.get("radiant_win")),
            game_mode=None if mode is None else f"OPENDOTA_{mode}",
            players=None
            if players is None
            else tuple(participant(raw, match_id) for raw in players),
            parse_version=optional_integer(row.get("version")),
        )
    except (ValidationError, ValueError, OverflowError, OSError):
        raise failure(ProviderErrorCode.INVALID_RESPONSE) from None
