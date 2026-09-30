"""Strict decoding of the fixed STRATZ selections; no guessed error semantics."""

from datetime import UTC, datetime
from typing import cast

from ..domain.errors import ProviderErrorCode, ValidationError
from ..domain.identity import AccountId
from ..domain.models import DataMetadata, MatchSummary, PlayerProfile
from ._stratz_http import failure


def object_value(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    return cast(dict[str, object], value)


def field(value: dict[str, object], name: str) -> object:
    if name not in value:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    return value[name]


def integer(value: object, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    return value


def optional_integer(value: object) -> int | None:
    return None if value is None else integer(value)


def optional_bool(value: object) -> bool | None:
    if value is not None and type(value) is not bool:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    return value


def player_data(payload: object, account_id: AccountId) -> dict[str, object]:
    envelope = object_value(payload)
    if "errors" in envelope and envelope["errors"] != []:
        # Even optional resolver failures can mean authentication/privacy or stale data.
        # No verified STRATZ error codes justify silently turning them into missing values.
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    player = object_value(field(object_value(field(envelope, "data")), "player"))
    if integer(field(player, "steamAccountId"), minimum=1) != account_id.value:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    return player


def profile(
    player: dict[str, object], account_id: AccountId, metadata: DataMetadata
) -> PlayerProfile:
    steam = field(player, "steamAccount")
    if steam is None:
        return PlayerProfile(account_id, metadata)
    account = object_value(steam)
    if integer(field(account, "id"), minimum=1) != account_id.value:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    name = field(account, "name")
    if name is not None and not isinstance(name, str):
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    return PlayerProfile(account_id, metadata, name, optional_integer(field(account, "seasonRank")))


def match_page(
    player: dict[str, object], account_id: AccountId, metadata: DataMetadata, take: int
) -> list[MatchSummary]:
    rows = field(player, "matches")
    if not isinstance(rows, list) or len(rows) > take:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    return [_match(row, account_id, metadata) for row in rows]


def _match(raw: object, account_id: AccountId, metadata: DataMetadata) -> MatchSummary:
    row = object_value(raw)
    players = field(row, "players")
    # The query explicitly selects only this account; missing identity isn't a zero-stat player.
    if not isinstance(players, list) or len(players) != 1:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    player = object_value(players[0])
    if integer(field(player, "steamAccountId"), minimum=1) != account_id.value:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    radiant = optional_bool(field(player, "isRadiant"))
    radiant_won = optional_bool(field(row, "didRadiantWin"))
    timestamp = integer(field(row, "startDateTime"))
    try:
        started_at = datetime.fromtimestamp(timestamp, UTC)
        return MatchSummary(
            match_id=integer(field(row, "id"), minimum=1),
            account_id=account_id,
            started_at=started_at,
            metadata=metadata,
            hero_id=optional_integer(field(player, "heroId")),
            duration_seconds=optional_integer(field(row, "durationSeconds")),
            kills=optional_integer(field(player, "kills")),
            deaths=optional_integer(field(player, "deaths")),
            assists=optional_integer(field(player, "assists")),
            gold_per_minute=optional_integer(field(player, "goldPerMinute")),
            experience_per_minute=optional_integer(field(player, "experiencePerMinute")),
            is_win=None if radiant is None or radiant_won is None else radiant == radiant_won,
        )
    except (ValidationError, ValueError, OverflowError, OSError):
        raise failure(ProviderErrorCode.INVALID_RESPONSE) from None
