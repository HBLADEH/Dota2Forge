"""Hero use cases depend on observation ports, without HTTP or platform state."""

from .domain.errors import ProviderError, ProviderErrorCode, ValidationError
from .domain.hero_features import (
    GuideSample,
    HeroGuide,
    HeroMetaEntry,
    HeroMetaRanking,
    HeroMetaSnapshot,
    MetaRequest,
    MetaSort,
    require_position,
)
from .domain.hero_items import HeroCatalog
from .domain.match_detail import parse_match_id
from .ports import HeroGuideProvider, HeroMetaProvider


def rank_heroes(snapshot: HeroMetaSnapshot) -> HeroMetaRanking:
    totals: dict[tuple[int, int], tuple[int, int]] = {}
    for bucket in snapshot.buckets:
        key = bucket.hero_id, bucket.position
        matches, wins = totals.get(key, (0, 0))
        totals[key] = matches + bucket.matches, wins + bucket.wins
    entries = tuple(
        HeroMetaEntry(hero, position, matches, wins)
        for (hero, position), (matches, wins) in totals.items()
        if matches >= snapshot.request.minimum_matches
    )

    def metric(row: HeroMetaEntry) -> float:
        return (
            row.reliability if snapshot.request.sort == MetaSort.RELIABLE else row.win_rate or 0.0
        )

    ordered = tuple(
        sorted(
            entries,
            key=lambda row: (
                -metric(row),
                -row.matches,
                -(row.win_rate or 0.0),
                row.hero_id,
                row.position,
            ),
        )
    )
    if snapshot.request.position is None:
        ordered = tuple(
            row
            for position in range(1, 6)
            for row in tuple(e for e in ordered if e.position == position)[:2]
        )
    else:
        ordered = ordered[:10]
    return HeroMetaRanking(
        snapshot,
        ordered,
        sum(matches < snapshot.request.minimum_matches for matches, _wins in totals.values()),
    )


class HeroFeatureService:
    def __init__(
        self, meta: HeroMetaProvider, guides: HeroGuideProvider, catalog: HeroCatalog
    ) -> None:
        self._meta, self._guides, self._catalog = meta, guides, catalog

    async def get_meta(self, request: MetaRequest) -> HeroMetaRanking:
        if not isinstance(request, MetaRequest):
            raise ValidationError("Expected a meta request")
        result = await self._meta.get_hero_meta(request)
        if (
            not isinstance(result, HeroMetaSnapshot)
            or result.request != request
            or result.metadata.source != self._meta.source
        ):
            raise ProviderError(ProviderErrorCode.INVALID_RESPONSE, self._meta.source)
        return rank_heroes(result)

    async def get_guide(self, name: str, position: int) -> HeroGuide:
        hero = self._catalog.resolve(name)
        require_position(position)
        if position is None:
            raise ValidationError("Expected an explicit guide position")
        result = await self._guides.get_hero_guide(hero, position)
        if (
            not isinstance(result, HeroGuide)
            or result.hero != hero
            or result.position != position
            or result.metadata.source != self._guides.source
        ):
            raise ProviderError(ProviderErrorCode.INVALID_RESPONSE, self._guides.source)
        return result

    async def get_sample(self, match: int | str, name: str) -> GuideSample:
        hero, match_id = self._catalog.resolve(name), parse_match_id(match)
        result = await self._guides.get_guide_sample(match_id, hero)
        if (
            not isinstance(result, GuideSample)
            or result.hero != hero
            or result.match_id != match_id
            or result.metadata.source != self._guides.source
        ):
            raise ProviderError(ProviderErrorCode.INVALID_RESPONSE, self._guides.source)
        return result
