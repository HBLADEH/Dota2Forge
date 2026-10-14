"""Immutable hero statistics and single-match build observations."""

import math
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .analysis import PurchaseEvent
from .errors import ProviderErrorCode, ValidationError
from .hero_items import Hero
from .match_detail import MatchId, MatchParticipant
from .models import DataMetadata, require_aware_time, require_nonnegative


class RankBracket(StrEnum):
    ALL = "ALL"
    UNCALIBRATED = "UNCALIBRATED"
    HERALD = "HERALD"
    GUARDIAN = "GUARDIAN"
    CRUSADER = "CRUSADER"
    ARCHON = "ARCHON"
    LEGEND = "LEGEND"
    ANCIENT = "ANCIENT"
    DIVINE = "DIVINE"
    IMMORTAL = "IMMORTAL"


class MetaSort(StrEnum):
    RELIABLE = "reliable"
    WIN_RATE = "win_rate"


def require_position(value: int | None) -> None:
    if value is not None and (type(value) is not int or not 1 <= value <= 5):
        raise ValidationError("Expected position 1-5 or unspecified")


def require_counts(matches: int, wins: int) -> None:
    require_nonnegative(matches)
    require_nonnegative(wins)
    if type(matches) is not int or type(wins) is not int or wins > matches:
        raise ValidationError("Invalid observed win/match counts")


def wilson_lower(wins: int, matches: int) -> float:
    require_counts(matches, wins)
    if matches == 0:
        return 0.0
    z = 1.96
    p = wins / matches
    return (
        p + z * z / (2 * matches) - z * math.sqrt((p * (1 - p) + z * z / (4 * matches)) / matches)
    ) / (1 + z * z / matches)


@dataclass(frozen=True, slots=True)
class MetaRequest:
    position: int | None = None
    rank: RankBracket = RankBracket.ALL
    days: int = 7
    sort: MetaSort = MetaSort.RELIABLE
    minimum_matches: int = 1000

    def __post_init__(self) -> None:
        require_position(self.position)
        if not isinstance(self.rank, RankBracket) or not isinstance(self.sort, MetaSort):
            raise ValidationError("Unknown hero statistics filter")
        if type(self.days) is not int or self.days not in (7, 14):
            raise ValidationError("Expected a 7 or 14 day window")
        if type(self.minimum_matches) is not int or not 1000 <= self.minimum_matches <= 1000000:
            raise ValidationError("Invalid minimum sample threshold")


@dataclass(frozen=True, slots=True)
class GamePatch:
    version_id: int
    name: str
    effective_at: datetime

    def __post_init__(self) -> None:
        if type(self.version_id) is not int or not 1 <= self.version_id <= 32767:
            raise ValidationError("Invalid game version ID")
        if (
            not isinstance(self.name, str)
            or not 1 <= len(self.name) <= 32
            or any(ord(c) < 32 for c in self.name)
        ):
            raise ValidationError("Invalid patch label")
        require_aware_time(self.effective_at)


@dataclass(frozen=True, slots=True)
class HeroWinBucket:
    day: datetime
    hero_id: int
    position: int
    matches: int
    wins: int

    def __post_init__(self) -> None:
        require_aware_time(self.day)
        require_position(self.position)
        if self.position is None:
            raise ValidationError("A bucket requires an observed position")
        if type(self.hero_id) is not int or not 1 <= self.hero_id <= 32767:
            raise ValidationError("Invalid hero ID")
        require_counts(self.matches, self.wins)


@dataclass(frozen=True, slots=True)
class HeroMetaSnapshot:
    request: MetaRequest
    metadata: DataMetadata
    patch: GamePatch
    window_start: datetime
    window_end: datetime
    buckets: tuple[HeroWinBucket, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.request, MetaRequest)
            or not isinstance(self.metadata, DataMetadata)
            or not isinstance(self.patch, GamePatch)
        ):
            raise ValidationError("Invalid hero meta metadata")
        for value in (self.window_start, self.window_end):
            require_aware_time(value)
        if (
            self.window_start > self.window_end
            or not isinstance(self.buckets, tuple)
            or len(self.buckets) > 15000
        ):
            raise ValidationError("Invalid statistics window or size")
        keys: set[tuple[datetime, int, int]] = set()
        for row in self.buckets:
            if (
                not isinstance(row, HeroWinBucket)
                or not self.window_start <= row.day < self.window_end
                or (self.request.position is not None and row.position != self.request.position)
            ):
                raise ValidationError("Inconsistent hero meta bucket")
            key = row.day, row.hero_id, row.position
            if key in keys:
                raise ValidationError("Duplicate hero meta bucket")
            keys.add(key)
        if not isinstance(self.notes, tuple) or any(
            not isinstance(note, str) or len(note) > 240 for note in self.notes
        ):
            raise ValidationError("Invalid metadata notes")


@dataclass(frozen=True, slots=True)
class HeroMetaEntry:
    hero_id: int
    position: int
    matches: int
    wins: int

    def __post_init__(self) -> None:
        require_position(self.position)
        if self.position is None:
            raise ValidationError("A ranking entry requires a position")
        require_counts(self.matches, self.wins)
        if type(self.hero_id) is not int or not 1 <= self.hero_id <= 32767:
            raise ValidationError("Invalid hero ID")

    @property
    def win_rate(self) -> float | None:
        return None if self.matches == 0 else self.wins / self.matches

    @property
    def reliability(self) -> float:
        return wilson_lower(self.wins, self.matches)


@dataclass(frozen=True, slots=True)
class HeroMetaRanking:
    snapshot: HeroMetaSnapshot
    entries: tuple[HeroMetaEntry, ...]
    observing: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, HeroMetaSnapshot) or (
            not isinstance(self.entries, tuple)
            or len(self.entries) > 10
            or any(not isinstance(row, HeroMetaEntry) for row in self.entries)
        ):
            raise ValidationError("Invalid hero ranking")
        require_nonnegative(self.observing)


@dataclass(frozen=True, slots=True)
class BuildItemBucket:
    item_id: int
    minute: int
    instance: int
    matches: int
    wins: int

    def __post_init__(self) -> None:
        if type(self.item_id) is not int or not 1 <= self.item_id <= 2147483647:
            raise ValidationError("Invalid item ID")
        for value in (self.minute, self.instance):
            require_nonnegative(value)
        if (
            type(self.minute) is not int
            or self.minute > 75
            or type(self.instance) is not int
            or self.instance > 1024
        ):
            raise ValidationError("Invalid item timing bucket")
        require_counts(self.matches, self.wins)


@dataclass(frozen=True, slots=True)
class AbilityChoice:
    ability_id: int
    level: int | None
    matches: int
    wins: int
    name: str | None = None

    def __post_init__(self) -> None:
        if type(self.ability_id) is not int or not 0 <= self.ability_id <= 2147483647:
            raise ValidationError("Invalid ability ID")
        require_nonnegative(self.level)
        require_counts(self.matches, self.wins)
        if self.name is not None and (not isinstance(self.name, str) or len(self.name) > 160):
            raise ValidationError("Invalid ability label")


@dataclass(frozen=True, slots=True)
class SkillUpgrade:
    ability_id: int
    source_level: int
    time_seconds: int
    is_talent: bool | None
    name: str | None = None

    def __post_init__(self) -> None:
        if type(self.ability_id) is not int or not 0 <= self.ability_id <= 2147483647:
            raise ValidationError("Invalid upgrade ability")
        if (
            type(self.source_level) is not int
            or not 0 <= self.source_level <= 30
            or type(self.time_seconds) is not int
        ):
            raise ValidationError("Invalid upgrade level/time")
        if self.is_talent is not None and type(self.is_talent) is not bool:
            raise ValidationError("Invalid talent marker")
        if self.name is not None and (not isinstance(self.name, str) or len(self.name) > 160):
            raise ValidationError("Invalid upgrade label")


@dataclass(frozen=True, slots=True)
class GuideSample:
    hero: Hero
    match_id: MatchId
    metadata: DataMetadata
    player: MatchParticipant
    patch: GamePatch | None
    started_at: datetime | None
    duration_seconds: int | None
    did_radiant_win: bool | None
    upgrades: tuple[SkillUpgrade, ...] | None
    purchases: tuple[PurchaseEvent, ...] | None
    label_error: str | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.hero, Hero)
            or not isinstance(self.match_id, MatchId)
            or not isinstance(self.metadata, DataMetadata)
            or not isinstance(self.player, MatchParticipant)
            or self.player.hero_id != self.hero.hero_id
        ):
            raise ValidationError("Inconsistent guide sample identity")
        if self.started_at is not None:
            require_aware_time(self.started_at)
        require_nonnegative(self.duration_seconds)
        if self.did_radiant_win is not None and type(self.did_radiant_win) is not bool:
            raise ValidationError("Invalid guide outcome")
        if self.patch is not None and not isinstance(self.patch, GamePatch):
            raise ValidationError("Invalid sample patch")
        if self.label_error is not None and self.label_error not in {
            code.value for code in ProviderErrorCode
        }:
            raise ValidationError("Invalid ability label failure")
        for values, kind, maximum in (
            (self.upgrades, SkillUpgrade, 128),
            (self.purchases, PurchaseEvent, 1024),
        ):
            if values is not None and (
                not isinstance(values, tuple)
                or len(values) > maximum
                or any(not isinstance(v, kind) for v in values)
            ):
                raise ValidationError("Invalid sample events")


@dataclass(frozen=True, slots=True)
class HeroGuide:
    hero: Hero
    position: int
    metadata: DataMetadata
    week_index: int | None
    items: tuple[BuildItemBucket, ...] | None
    abilities: tuple[AbilityChoice, ...] | None
    talents: tuple[AbilityChoice, ...] | None
    samples: tuple[GuideSample, ...]
    notes: tuple[str, ...] = ()
    module_errors: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.hero, Hero) or not isinstance(self.metadata, DataMetadata):
            raise ValidationError("Invalid hero guide metadata")
        require_position(self.position)
        if self.position is None:
            raise ValidationError("A guide requires a position")
        require_nonnegative(self.week_index)
        for values, kind in (
            (self.items, BuildItemBucket),
            (self.abilities, AbilityChoice),
            (self.talents, AbilityChoice),
        ):
            if values is not None and (
                not isinstance(values, tuple)
                or len(values) > 4096
                or any(not isinstance(v, kind) for v in values)
            ):
                raise ValidationError("Invalid guide statistics")
        if (
            not isinstance(self.samples, tuple)
            or len(self.samples) > 3
            or any(
                not isinstance(v, GuideSample)
                or v.hero.hero_id != self.hero.hero_id
                or v.player.position != f"POSITION_{self.position}"
                for v in self.samples
            )
        ):
            raise ValidationError("Invalid guide sample selection")
        if (
            not isinstance(self.notes, tuple)
            or len(self.notes) > 16
            or any(not isinstance(v, str) or len(v) > 240 for v in self.notes)
            or not isinstance(self.module_errors, tuple)
            or len(self.module_errors) > 8
            or any(
                not isinstance(v, tuple)
                or len(v) != 2
                or v[0] not in {"statistics", "samples", "abilities", "talents"}
                or v[1]
                not in {
                    "scope_mismatch",
                    "not_found",
                    "private",
                    "rate_limited",
                    "timeout",
                    "unavailable",
                    "authentication",
                    "invalid_response",
                }
                for v in self.module_errors
            )
        ):
            raise ValidationError("Expected immutable guide status")
