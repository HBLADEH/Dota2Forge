"""Offline hero resolution, item observations, provider and use-case boundaries."""

import asyncio
from dataclasses import replace

import httpx
import pytest
from dota2forge_core import (
    DataSource,
    Hero,
    HeroCatalog,
    HeroItemService,
    HeroItemStatistics,
    HeroResolutionError,
    ItemPurchaseCount,
    ItemStage,
    ProviderError,
    ProviderErrorCode,
    StageItemCounts,
    ValidationError,
)
from dota2forge_core.domain.hero_items import normalize_hero_name
from dota2forge_core.infrastructure.hero_catalog import load_hero_catalog
from dota2forge_core.infrastructure.opendota import OpenDotaProvider


def payload():
    return {
        "start_game_items": {"44": 2, "1": 2, "999999": 0},
        "early_game_items": {},
        "mid_game_items": None,
        "late_game_items": {"1": 4},
    }


@pytest.mark.parametrize(
    "name,hero_id",
    [
        ("斧王", 2),
        ("AXE", 2),
        ("敌法", 1),
        ("Anti Mage", 1),
        ("anti-mage", 1),
        ("AM", 1),
        ("影魔", 11),
        ("SF", 11),
        ("幻影刺客", 44),
        ("pa", 44),
        ("火猫", 106),
        ("蓝猫", 17),
        ("小狗", 54),
        ("老鹿", 52),
        ("水人", 10),
        ("虚无之灵", 126),
    ],
)
def test_exact_hero_name_and_reviewed_aliases(name, hero_id):
    assert load_hero_catalog().resolve(name).hero_id == hero_id


@pytest.mark.parametrize(
    "name,ids",
    [
        ("猴子", {12, 114}),
        ("ES", {7, 106, 107}),
        ("ss", {17, 27}),
        ("sk", {16, 42}),
        ("not-a-hero", set()),
    ],
)
def test_ambiguous_and_unknown_names_do_not_guess(name, ids):
    with pytest.raises(HeroResolutionError) as error:
        load_hero_catalog().resolve(name)
    assert {hero.hero_id for hero in error.value.candidates} == ids
    assert name not in str(error.value)


@pytest.mark.parametrize("name", [None, 2, "", " " * 65, "x" * 65, "axe\nother", "axe\x1b"])
def test_invalid_hero_name_is_bounded_and_has_no_controls(name):
    with pytest.raises(ValidationError):
        normalize_hero_name(name)


def test_catalog_rejects_duplicates_and_invalid_shape():
    hero = Hero(2, "斧王", "Axe")
    for heroes in ((), [hero], (hero, hero), (None,)):
        with pytest.raises(ValidationError):
            HeroCatalog(heroes)
    assert HeroCatalog((hero,)).resolve("axe") is hero


@pytest.mark.parametrize(
    "args",
    [
        (0, "斧王", "Axe"),
        (True, "斧王", "Axe"),
        (2, "", "Axe"),
        (2, "斧王", ""),
        (2, "斧王", "Axe", []),
        (2, "斧王", "Axe", (None,)),
    ],
)
def test_hero_model_rejects_invalid_values(args):
    with pytest.raises(ValidationError):
        Hero(*args)


@pytest.mark.parametrize(
    "item_id,count",
    [(0, 1), (-1, 1), (True, 1), (1, None), (1, True), (1, -1), (1, 1.5), (1, "2"), (2**31, 1)],
)
def test_item_count_rejects_coercion_and_invalid_values(item_id, count):
    with pytest.raises(ValidationError):
        ItemPurchaseCount(item_id, count)


def test_stage_and_result_models_preserve_empty_missing_and_zero(metadata):
    item = ItemPurchaseCount(1, 0)
    for stage, items in (
        ("start_game_items", ()),
        (ItemStage.START, [item]),
        (ItemStage.START, (item, item)),
        (ItemStage.START, (None,)),
        (ItemStage.START, (item,) * 2049),
    ):
        with pytest.raises(ValidationError):
            StageItemCounts(stage, items)
    hero = Hero(2, "斧王", "Axe")
    stages = tuple(
        StageItemCounts(stage, None if stage == ItemStage.MID else ()) for stage in ItemStage
    )
    result = HeroItemStatistics(hero, metadata, stages)
    assert result.missing_fields == ("mid_game_items",)
    for args in (
        (None, metadata, stages),
        (hero, None, stages),
        (hero, metadata, list(stages)),
        (hero, metadata, ()),
        (hero, metadata, (None,) * 4),
        (hero, metadata, stages[::-1]),
    ):
        with pytest.raises(ValidationError):
            HeroItemStatistics(*args)


def test_provider_is_anonymous_and_preserves_stage_semantics(clock, run_async):
    hero = load_hero_catalog().resolve("Axe")
    calls = []

    def handler(request):
        calls.append(request)
        assert str(request.url) == "https://api.opendota.com/api/heroes/2/itemPopularity"
        assert not any(
            header in request.headers
            for header in ("Authorization", "Cookie", "Proxy-Authorization")
        )
        return httpx.Response(200, json=payload())

    async def check():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            headers={"Authorization": "Bearer synthetic-secret", "Cookie": "x=synthetic"},
            params={"api_key": "synthetic"},
        ) as client:
            provider = OpenDotaProvider(client, clock=clock)
            result = await HeroItemService(provider, load_hero_catalog()).get_items("axe")
            assert result.hero == hero and result.metadata.source == DataSource.OPENDOTA
            assert result.metadata.patch is None and result.metadata.observed_at is None
            assert [item.item_id for item in result.stages[0].items] == [1, 44, 999999]
            assert result.stages[0].items[-1].count == 0
            assert result.stages[1].items == () and result.stages[2].items is None
            assert len(calls) == 1 and not client.is_closed
            with pytest.raises(ValidationError):
                await provider.get_hero_item_statistics(2)
        assert client.is_closed

    run_async(check())


@pytest.mark.parametrize(
    "bad",
    [
        None,
        [],
        {},
        {"error": "synthetic"},
        {"unrelated": {}},
        {"start_game_items": []},
        {"start_game_items": {"01": 1}},
        {"start_game_items": {"0": 1}},
        {"start_game_items": {"١": 1}},
        {"start_game_items": {"x": 1}},
        {"start_game_items": {"99999999999": 1}},
        {"start_game_items": {"1": True}},
        {"start_game_items": {"1": -1}},
        {"start_game_items": {"1": "1"}},
        {"start_game_items": {str(i): 1 for i in range(1, 2050)}},
    ],
)
def test_malformed_upstream_never_becomes_empty_stats(bad, clock, run_async):
    async def check():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=bad))
        ) as client:
            with pytest.raises(ProviderError) as error:
                await OpenDotaProvider(client, clock=clock).get_hero_item_statistics(
                    Hero(2, "斧王", "Axe")
                )
            assert error.value.code == ProviderErrorCode.INVALID_RESPONSE

    run_async(check())


@pytest.mark.parametrize(
    "status,code",
    [
        (403, ProviderErrorCode.UNAVAILABLE),
        (404, ProviderErrorCode.UNAVAILABLE),
        (401, ProviderErrorCode.AUTHENTICATION),
        (429, ProviderErrorCode.RATE_LIMITED),
    ],
)
def test_item_endpoint_failure_classification_and_no_retry(status, code, clock, run_async):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers={"Retry-After": "12"})

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(ProviderError) as error:
                await OpenDotaProvider(client, clock=clock).get_hero_item_statistics(
                    Hero(2, "斧王", "Axe")
                )
            assert error.value.code == code and len(calls) == 1

    run_async(check())


def test_service_checks_returned_source_hero_type_and_propagates_cancel(metadata, run_async):
    hero = Hero(2, "斧王", "Axe")
    result = HeroItemStatistics(
        hero, metadata, tuple(StageItemCounts(stage, ()) for stage in ItemStage)
    )

    class Provider:
        source = DataSource.FIXTURE
        value = result
        calls = 0

        async def get_hero_item_statistics(self, hero):
            self.calls += 1
            if isinstance(self.value, BaseException):
                raise self.value
            return self.value

    async def check():
        provider = Provider()
        service = HeroItemService(provider, HeroCatalog((hero,)))
        with pytest.raises(HeroResolutionError):
            await service.get_items("no-such-hero")
        assert provider.calls == 0
        for value in (
            None,
            replace(result, hero=Hero(1, "敌法师", "Anti-Mage")),
            replace(result, metadata=replace(metadata, source=DataSource.STRATZ)),
        ):
            provider.value = value
            with pytest.raises(ProviderError) as error:
                await service.get_items("axe")
            assert error.value.code == ProviderErrorCode.INVALID_RESPONSE
        for error in (asyncio.CancelledError(), RuntimeError("synthetic failure")):
            provider.value = error
            with pytest.raises(type(error)):
                await service.get_items("axe")
        with pytest.raises(ValidationError):
            HeroItemService(provider, None)

    run_async(check())
