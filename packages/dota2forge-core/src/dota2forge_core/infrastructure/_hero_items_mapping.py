"""Normalize OpenDota's stage dictionaries without inventing missing buckets."""

from ..domain.errors import ProviderErrorCode, ValidationError
from ..domain.hero_items import (
    Hero,
    HeroItemStatistics,
    ItemPurchaseCount,
    ItemStage,
    StageItemCounts,
)
from ..domain.models import DataMetadata
from ._opendota_http import failure


def item_statistics(payload: object, hero: Hero, metadata: DataMetadata) -> HeroItemStatistics:
    try:
        if not isinstance(payload, dict) or not payload or "error" in payload:
            raise ValidationError("Expected item statistics")
        stages = []
        for stage in ItemStage:
            value = payload.get(stage.value)
            if value is None:
                stages.append(StageItemCounts(stage, None))
                continue
            if not isinstance(value, dict) or len(value) > 2048:
                raise ValidationError("Expected bounded stage item dictionary")
            items = []
            for key, count in value.items():
                if (
                    not isinstance(key, str)
                    or not key.isascii()
                    or not key.isdecimal()
                    or len(key) > 10
                    or key.startswith("0")
                ):
                    raise ValidationError("Invalid item key")
                items.append(ItemPurchaseCount(int(key), count))
            stages.append(
                StageItemCounts(
                    stage, tuple(sorted(items, key=lambda item: (-item.count, item.item_id)))
                )
            )
        if all(stage.items is None for stage in stages):
            raise ValidationError("No recognized stage fields")
        return HeroItemStatistics(hero, metadata, tuple(stages))
    except ValidationError:
        raise failure(ProviderErrorCode.INVALID_RESPONSE) from None
