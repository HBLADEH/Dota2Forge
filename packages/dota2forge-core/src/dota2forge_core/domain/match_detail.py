"""Minimal historical match observations, without inferred privacy or identities."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from .errors import DataSource, ValidationError
from .identity import AccountId
from .models import DataMetadata, require_aware_time, require_nonnegative

MAX_MATCH_ID = (1 << 63) - 1


class MatchParseState(StrEnum):
    """Evidence reported by the upstream parser, without claiming completeness."""

    UNKNOWN = "unknown"
    UNPARSED = "unparsed"
    PARTIAL = "partial"
    UPSTREAM_PARSED = "upstream_parsed"
    NO_DATA = "no_data"


@dataclass(frozen=True, slots=True)
class MatchId:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or not 1 <= self.value <= MAX_MATCH_ID:
            raise ValidationError("Expected a positive signed 64-bit match ID")


def parse_match_id(value: int | str) -> MatchId:
    if isinstance(value, str):
        if not re.fullmatch(r"[1-9][0-9]{0,18}", value):
            raise ValidationError("Expected a canonical decimal match ID")
        return MatchId(int(value))
    return MatchId(value)


def require_optional_bool(value: bool | None) -> None:
    if value is not None and type(value) is not bool:
        raise ValidationError("Expected a boolean or missing value")


@dataclass(frozen=True, slots=True)
class MatchParticipant:
    player_slot: int | None = None
    account_id: AccountId | None = field(default=None, repr=False)
    display_name: str | None = field(default=None, repr=False)
    is_anonymous: bool | None = None
    is_radiant: bool | None = None
    hero_id: int | None = None
    kills: int | None = None
    deaths: int | None = None
    assists: int | None = None
    gold_per_minute: int | None = None
    experience_per_minute: int | None = None
    item_ids: tuple[int | None, ...] = (None,) * 6

    level: int | None = None
    last_hits: int | None = None
    denies: int | None = None
    net_worth: int | None = None
    hero_damage: int | None = None
    tower_damage: int | None = None
    hero_healing: int | None = None
    imp: int | None = None
    position: str | None = None
    lane: str | None = None
    backpack_ids: tuple[int | None, ...] = (None,) * 3
    neutral_item_id: int | None = None

    def __post_init__(self) -> None:
        if self.account_id is not None and not isinstance(self.account_id, AccountId):
            raise ValidationError("Expected a validated participant account")
        require_optional_bool(self.is_anonymous)
        require_optional_bool(self.is_radiant)
        if self.account_id is not None and self.is_anonymous is not False:
            raise ValidationError("A known participant account must not be anonymous or unknown")
        if self.account_id is None and self.is_anonymous is False:
            raise ValidationError("A non-anonymous participant requires a known account")
        if self.display_name is not None and (
            not isinstance(self.display_name, str) or self.account_id is None
        ):
            raise ValidationError("A participant name requires a known account")
        for name in (
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
        ):
            require_nonnegative(getattr(self, name))
        if self.player_slot is not None and self.player_slot > 255:
            raise ValidationError("Participant slot exceeds the upstream byte range")
        if self.hero_id == 0:
            raise ValidationError("A missing hero must be None")
        if not isinstance(self.item_ids, tuple) or len(self.item_ids) != 6:
            raise ValidationError("Expected six immutable item slots")
        for item_id in self.item_ids:
            require_nonnegative(item_id)
        if self.imp is not None and (type(self.imp) is not int or not -32768 <= self.imp <= 32767):
            raise ValidationError("Expected a STRATZ signed short IMP observation")
        for value in (self.position, self.lane):
            if value is not None and (
                not isinstance(value, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", value)
            ):
                raise ValidationError("Expected an upstream role or lane enum")
        if not isinstance(self.backpack_ids, tuple) or len(self.backpack_ids) != 3:
            raise ValidationError("Expected three immutable backpack slots")
        for item_id in (*self.backpack_ids, self.neutral_item_id):
            require_nonnegative(item_id)

    @property
    def missing_fields(self) -> tuple[str, ...]:
        missing = tuple(
            name
            for name in (
                "player_slot",
                "account_id",
                "display_name",
                "is_anonymous",
                "is_radiant",
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
                "imp",
                "position",
                "lane",
                "neutral_item_id",
            )
            if getattr(self, name) is None
        )
        return (
            missing
            + tuple(
                f"item_ids[{index}]" for index, item in enumerate(self.item_ids) if item is None
            )
            + tuple(
                f"backpack_ids[{index}]"
                for index, item in enumerate(self.backpack_ids)
                if item is None
            )
        )


@dataclass(frozen=True, slots=True)
class MatchDetail:
    match_id: MatchId
    metadata: DataMetadata
    started_at: datetime | None = None
    duration_seconds: int | None = None
    did_radiant_win: bool | None = None
    game_mode: str | None = None
    game_version_id: int | None = None
    has_stats: bool | None = None
    parsed_at: datetime | None = None
    players: tuple[MatchParticipant, ...] | None = None
    parse_version: int | None = None

    def __post_init__(self) -> None:
        require_match_metadata(self.match_id, self.metadata)
        if self.started_at is not None:
            require_aware_time(self.started_at)
        if self.parsed_at is not None:
            require_aware_time(self.parsed_at)
        require_nonnegative(self.duration_seconds)
        require_nonnegative(self.game_version_id)
        require_nonnegative(self.parse_version)
        require_optional_bool(self.did_radiant_win)
        require_optional_bool(self.has_stats)
        if self.game_mode is not None and (
            not isinstance(self.game_mode, str)
            or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", self.game_mode)
        ):
            raise ValidationError("Expected an upstream game mode enum or missing value")
        if self.players is None:
            return
        if not isinstance(self.players, tuple) or len(self.players) > 10:
            raise ValidationError("Expected up to ten immutable match participants")
        slots: set[int] = set()
        accounts: set[AccountId] = set()
        for player in self.players:
            if not isinstance(player, MatchParticipant):
                raise ValidationError("Expected validated match participants")
            if player.imp is not None and self.metadata.source != DataSource.STRATZ:
                raise ValidationError("IMP is only a STRATZ observation")
            if player.player_slot is not None:
                if player.player_slot in slots:
                    raise ValidationError("Duplicate participant slot")
                slots.add(player.player_slot)
            if player.account_id is not None:
                if player.account_id in accounts:
                    raise ValidationError("Duplicate participant account")
                accounts.add(player.account_id)

    @property
    def missing_fields(self) -> tuple[str, ...]:
        missing = tuple(
            name
            for name in (
                "started_at",
                "duration_seconds",
                "did_radiant_win",
                "game_mode",
                "game_version_id",
                "has_stats",
                "parsed_at",
                "players",
            )
            if getattr(self, name) is None
        )
        if self.metadata.source == DataSource.OPENDOTA and self.parse_version is None:
            return missing + ("parse_version",)
        return missing

    @property
    def parse_state(self) -> MatchParseState:
        """Classify only explicit upstream markers and observed payload shape.

        ``UPSTREAM_PARSED`` records ``isStats=True``; it does not promise that
        every optional field is present. ``UNPARSED`` follows ``isStats=False``
        even when an upstream parse timestamp is present. Without either marker,
        observed fields are conservatively classified as ``PARTIAL``. OpenDota's
        positive parse schema version is independent evidence of an upstream
        parse; zero/null do not prove an unparsed match. It is not a game patch.
        """

        if self.has_stats is False:
            return MatchParseState.UNPARSED
        if self.has_stats is True:
            return MatchParseState.UPSTREAM_PARSED
        if (
            self.metadata.source == DataSource.OPENDOTA
            and self.parse_version is not None
            and self.parse_version > 0
        ):
            return MatchParseState.UPSTREAM_PARSED
        if self.parsed_at is not None or any(
            value is not None
            for value in (
                self.started_at,
                self.duration_seconds,
                self.did_radiant_win,
                self.game_mode,
                self.game_version_id,
                self.players,
            )
        ):
            return MatchParseState.PARTIAL
        return MatchParseState.UNKNOWN

    def participant(self, account_id: AccountId) -> MatchParticipant | None:
        if not isinstance(account_id, AccountId):
            raise ValidationError("Expected a validated account for match perspective")
        return next(
            (player for player in self.players or () if player.account_id == account_id), None
        )


@dataclass(frozen=True, slots=True)
class MatchDetailUnavailable:
    """A successful upstream null: no detail returned, with unknown cause and privacy."""

    match_id: MatchId
    metadata: DataMetadata

    def __post_init__(self) -> None:
        require_match_metadata(self.match_id, self.metadata)

    @property
    def parse_state(self) -> MatchParseState:
        return MatchParseState.NO_DATA


def require_match_metadata(match_id: MatchId, metadata: DataMetadata) -> None:
    if not isinstance(match_id, MatchId) or not isinstance(metadata, DataMetadata):
        raise ValidationError("Expected a validated match ID and metadata")


type MatchDetailResult = MatchDetail | MatchDetailUnavailable
