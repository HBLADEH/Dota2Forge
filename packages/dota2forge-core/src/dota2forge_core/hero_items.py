"""Independent item-statistics use case, without binding or source fallback."""

from .domain.errors import ProviderError, ProviderErrorCode, ValidationError
from .domain.hero_items import HeroCatalog, HeroItemStatistics
from .ports import HeroItemProvider


class HeroItemService:
    def __init__(self, provider: HeroItemProvider, catalog: HeroCatalog) -> None:
        if not isinstance(catalog, HeroCatalog):
            raise ValidationError("Expected a hero catalog")
        self._provider = provider
        self._catalog = catalog

    async def get_items(self, hero_name: str) -> HeroItemStatistics:
        hero = self._catalog.resolve(hero_name)
        result = await self._provider.get_hero_item_statistics(hero)
        if (
            not isinstance(result, HeroItemStatistics)
            or result.hero != hero
            or result.metadata.source != self._provider.source
        ):
            raise ProviderError(ProviderErrorCode.INVALID_RESPONSE, self._provider.source)
        return result
