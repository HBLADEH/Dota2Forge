"""Strict mapping of the verified, fixed historical-match selection."""

from datetime import UTC, datetime

from ..domain.errors import ProviderErrorCode, ValidationError
from ..domain.identity import MAX_ACCOUNT_ID, AccountId
from ..domain.match_detail import (
    MatchDetail,
    MatchDetailResult,
    MatchDetailUnavailable,
    MatchId,
    MatchParticipant,
)
from ..domain.models import DataMetadata
from ._stratz_http import failure
from ._stratz_mapping import field, integer, object_value, optional_bool, optional_integer


def optional_time(value: object) -> datetime | None:
    return None if value is None else datetime.fromtimestamp(integer(value), UTC)


def participant(raw: object) -> MatchParticipant:
    row = object_value(raw)
    raw_account = field(row, "steamAccountId")
    account_number = optional_integer(raw_account)
    anonymous = None if account_number is None else account_number in {0, MAX_ACCOUNT_ID + 1}
    account = None if account_number is None or anonymous else AccountId(account_number)
    raw_steam = field(row, "steamAccount")
    name: str | None = None
    if raw_steam is not None:
        steam = object_value(raw_steam)
        # Names must not disclose an identity when the participant is anonymous/unknown.
        steam_id = optional_integer(field(steam, "id"))
        raw_name = field(steam, "name")
        if raw_name is not None and not isinstance(raw_name, str):
            raise failure(ProviderErrorCode.INVALID_RESPONSE)
        if steam_id != account_number:
            raise failure(ProviderErrorCode.INVALID_RESPONSE)
        if account is not None:
            name = raw_name
    return MatchParticipant(
        player_slot=optional_integer(field(row, "playerSlot")),
        account_id=account,
        display_name=name,
        is_anonymous=anonymous,
        is_radiant=optional_bool(field(row, "isRadiant")),
        hero_id=optional_integer(field(row, "heroId")),
        kills=optional_integer(field(row, "kills")),
        deaths=optional_integer(field(row, "deaths")),
        assists=optional_integer(field(row, "assists")),
        gold_per_minute=optional_integer(field(row, "goldPerMinute")),
        experience_per_minute=optional_integer(field(row, "experiencePerMinute")),
        item_ids=tuple(optional_integer(field(row, f"item{index}Id")) for index in range(6)),
    )


def match_detail(payload: object, match_id: MatchId, metadata: DataMetadata) -> MatchDetailResult:
    envelope = object_value(payload)
    if "errors" in envelope and envelope["errors"] != []:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    raw = field(object_value(field(envelope, "data")), "match")
    if raw is None:
        return MatchDetailUnavailable(match_id, metadata)
    row = object_value(raw)
    if integer(field(row, "id"), minimum=1) != match_id.value:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    players = field(row, "players")
    if players is not None and (not isinstance(players, list) or len(players) > 10):
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    mode = field(row, "gameMode")
    if mode is not None and not isinstance(mode, str):
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    try:
        return MatchDetail(
            match_id=match_id,
            metadata=metadata,
            started_at=optional_time(field(row, "startDateTime")),
            duration_seconds=optional_integer(field(row, "durationSeconds")),
            did_radiant_win=optional_bool(field(row, "didRadiantWin")),
            game_mode=mode,
            game_version_id=optional_integer(field(row, "gameVersionId")),
            has_stats=optional_bool(field(row, "isStats")),
            parsed_at=optional_time(field(row, "parsedDateTime")),
            players=None if players is None else tuple(participant(player) for player in players),
        )
    except (ValidationError, ValueError, OverflowError, OSError):
        raise failure(ProviderErrorCode.INVALID_RESPONSE) from None
