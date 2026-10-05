"""Hero resolution and observed item counts; no recommendations or I/O."""

import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from .errors import ValidationError
from .models import DataMetadata, require_nonnegative


def normalize_hero_name(value: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 64:
        raise ValidationError("Expected a bounded hero name")
    if any(unicodedata.category(char).startswith("C") for char in value):
        raise ValidationError("Invalid hero name characters")
    return "".join(char for char in value.strip().casefold() if char not in " _-")


@dataclass(frozen=True, slots=True)
class Hero:
    hero_id: int
    display_name: str
    english_name: str
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.hero_id) is not int or not 1 <= self.hero_id <= 32767:
            raise ValidationError("Expected a positive hero ID")
        if not isinstance(self.aliases, tuple):
            raise ValidationError("Expected immutable hero aliases")
        for name in (self.display_name, self.english_name, *self.aliases):
            if not normalize_hero_name(name):
                raise ValidationError("Empty hero name")


class HeroResolutionError(ValidationError):
    def __init__(self, candidates: tuple[Hero, ...] = ()) -> None:
        super().__init__("Ambiguous or unknown hero name")
        self.candidates = candidates


class HeroCatalog:
    def __init__(self, heroes: tuple[Hero, ...]) -> None:
        if not isinstance(heroes, tuple) or not heroes:
            raise ValidationError("Expected an immutable hero catalog")
        self._names: dict[str, tuple[Hero, ...]] = {}
        seen: set[int] = set()
        for hero in heroes:
            if not isinstance(hero, Hero) or hero.hero_id in seen:
                raise ValidationError("Duplicate or invalid catalog hero")
            seen.add(hero.hero_id)
            for name in (hero.display_name, hero.english_name, *hero.aliases):
                key = normalize_hero_name(name)
                candidates = self._names.get(key, ())
                if hero not in candidates:
                    self._names[key] = (*candidates, hero)

    def resolve(self, name: str) -> Hero:
        candidates = self._names.get(normalize_hero_name(name), ())
        if len(candidates) != 1:
            raise HeroResolutionError(candidates)
        return candidates[0]


class ItemStage(StrEnum):
    START = "start_game_items"
    EARLY = "early_game_items"
    MID = "mid_game_items"
    LATE = "late_game_items"


@dataclass(frozen=True, slots=True)
class ItemPurchaseCount:
    item_id: int
    count: int

    def __post_init__(self) -> None:
        if type(self.item_id) is not int or not 1 <= self.item_id <= 2147483647:
            raise ValidationError("Expected a positive item ID")
        if type(self.count) is not int:
            raise ValidationError("Expected an observed integer count")
        require_nonnegative(self.count)


@dataclass(frozen=True, slots=True)
class StageItemCounts:
    stage: ItemStage
    items: tuple[ItemPurchaseCount, ...] | None

    def __post_init__(self) -> None:
        if not isinstance(self.stage, ItemStage):
            raise ValidationError("Expected a known item stage")
        if self.items is None:
            return
        if not isinstance(self.items, tuple) or len(self.items) > 2048:
            raise ValidationError("Expected bounded immutable item counts")
        seen: set[int] = set()
        for item in self.items:
            if not isinstance(item, ItemPurchaseCount) or item.item_id in seen:
                raise ValidationError("Duplicate or invalid item count")
            seen.add(item.item_id)


@dataclass(frozen=True, slots=True)
class HeroItemStatistics:
    hero: Hero
    metadata: DataMetadata
    stages: tuple[StageItemCounts, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.hero, Hero) or not isinstance(self.metadata, DataMetadata):
            raise ValidationError("Expected validated hero and metadata")
        if not isinstance(self.stages, tuple) or len(self.stages) != 4:
            raise ValidationError("Expected all four item stages")
        if any(not isinstance(stage, StageItemCounts) for stage in self.stages):
            raise ValidationError("Expected normalized item stages")
        if tuple(stage.stage for stage in self.stages) != tuple(ItemStage):
            raise ValidationError("Duplicate or unordered item stages")

    @property
    def missing_fields(self) -> tuple[str, ...]:
        return tuple(stage.stage.value for stage in self.stages if stage.items is None)
