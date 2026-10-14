"""Fixed verified hero selections sharing the provider's transport and quota owner."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from ..domain.analysis import PurchaseEvent
from ..domain.errors import DataSource, ProviderError, ProviderErrorCode, ValidationError
from ..domain.hero_features import (
    AbilityChoice,
    BuildItemBucket,
    GamePatch,
    GuideSample,
    HeroGuide,
    HeroMetaSnapshot,
    HeroWinBucket,
    MetaRequest,
    RankBracket,
    SkillUpgrade,
)
from ..domain.hero_items import Hero
from ..domain.match_detail import MatchDetail, MatchId
from ..domain.models import DataMetadata
from ._feature_cache import ObservationCache
from ._stratz_detail import match_detail
from ._stratz_http import StratzHTTP, failure
from ._stratz_mapping import field, integer, object_value, optional_bool

PATCHES_QUERY = "{constants{gameVersions{id name asOfDateTime}}}"
SAMPLE_FIELDS = """
id startDateTime durationSeconds didRadiantWin gameMode gameVersionId isStats parsedDateTime
players(steamAccountId:$accountId) {
  playerSlot steamAccountId steamAccount {id name} isRadiant heroId kills deaths assists
  goldPerMinute experiencePerMinute level numLastHits numDenies networth
  heroDamage towerDamage heroHealing imp position lane
  item0Id item1Id item2Id item3Id item4Id item5Id backpack0Id backpack1Id backpack2Id neutral0Id
  abilities {abilityId level time isTalent}
  stats {itemPurchases {time itemId}}
}
"""
SAMPLE_QUERY = "query($matchId:Long!,$accountId:Long!){match(id:$matchId){" + SAMPLE_FIELDS + "}}"


def data(payload: object) -> dict[str, object]:
    envelope = object_value(payload)
    if envelope.get("errors") not in (None, []):
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    return object_value(field(envelope, "data"))


def rows(value: object, maximum: int = 4096) -> list[object]:
    if not isinstance(value, list) or len(value) > maximum:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    return value


def instant(value: object) -> datetime:
    try:
        return datetime.fromtimestamp(integer(value), UTC)
    except (ValueError, OverflowError, OSError):
        raise failure(ProviderErrorCode.INVALID_RESPONSE) from None


def patch(raw: object) -> GamePatch:
    row = object_value(raw)
    name = field(row, "name")
    if not isinstance(name, str):
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    return GamePatch(
        integer(field(row, "id"), minimum=1), name, instant(field(row, "asOfDateTime"))
    )


def upgrades(value: object) -> tuple[SkillUpgrade, ...] | None:
    if value is None:
        return None
    result = []
    for raw in rows(value, 128):
        row = object_value(raw)
        label: str | None = None
        if row.get("ability") is not None:
            ability = object_value(row["ability"])
            if ability.get("id") != row.get("abilityId"):
                raise failure(ProviderErrorCode.INVALID_RESPONSE)
            raw_label = ability.get("name")
            if raw_label is not None and not isinstance(raw_label, str):
                raise failure(ProviderErrorCode.INVALID_RESPONSE)
            label = raw_label
        result.append(
            SkillUpgrade(
                integer(field(row, "abilityId")),
                integer(field(row, "level")),
                integer(field(row, "time"), minimum=-2147483648),
                optional_bool(field(row, "isTalent")),
                label,
            )
        )
    return tuple(result)


class StratzHeroes:
    def __init__(self, http: StratzHTTP) -> None:
        self._http = http
        self._patches = ObservationCache[tuple[GamePatch, ...]](ttl=1800, capacity=1)
        self._meta = ObservationCache[HeroMetaSnapshot](ttl=1800)
        self._guides = ObservationCache[HeroGuide](ttl=21600)
        self._samples = ObservationCache[GuideSample](ttl=3600)
        self._labels = ObservationCache[tuple[tuple[int, str | None], ...]](ttl=21600)

    async def close(self) -> None:
        for cache in (self._patches, self._meta, self._guides, self._samples, self._labels):
            await cache.close()

    async def labels(self, events: tuple[SkillUpgrade, ...], version: int) -> dict[int, str | None]:
        ids = tuple(sorted({v.ability_id for v in events if 0 < v.ability_id <= 32767}))
        return await self.label_ids(ids, version)

    async def label_ids(self, ids: tuple[int, ...], version: int) -> dict[int, str | None]:
        ids = tuple(sorted({identifier for identifier in ids if 0 < identifier <= 32767}))
        if not ids:
            return {}

        async def load() -> tuple[tuple[int, str | None], ...]:
            selections = " ".join(
                f"a{i}:ability(id:{ability},gameVersionId:$version,language:S_CHINESE)"
                "{id name language{displayName}}"
                for i, ability in enumerate(ids)
            )
            payload, _ = await self._http.request(
                "query($version:Short!){constants{" + selections + "}}", {"version": version}
            )
            constants = object_value(field(data(payload), "constants"))
            result = []
            for i, ability in enumerate(ids):
                raw = field(constants, f"a{i}")
                label: str | None = None
                if raw is not None:
                    row = object_value(raw)
                    if field(row, "id") != ability:
                        raise failure(ProviderErrorCode.INVALID_RESPONSE)
                    language = field(row, "language")
                    if language is not None:
                        raw_label = field(object_value(language), "displayName")
                        if raw_label is not None and (
                            not isinstance(raw_label, str) or len(raw_label) > 160
                        ):
                            raise failure(ProviderErrorCode.INVALID_RESPONSE)
                        label = raw_label
                    # Verified constant key, not a guess from an unidentified event ID.
                    if not label and row.get("name") == "special_bonus_attributes":
                        label = "属性加点"
                result.append((ability, label))
            return tuple(result)

        return dict(await self._labels.get(f"{version}:{ids}", load))

    async def patches(self) -> tuple[GamePatch, ...]:
        async def load() -> tuple[GamePatch, ...]:
            payload, _ = await self._http.request(PATCHES_QUERY, {})
            return tuple(
                patch(row)
                for row in rows(
                    field(object_value(field(data(payload), "constants")), "gameVersions")
                )
            )

        return await self._patches.get("versions", load)

    async def meta(self, request: MetaRequest) -> HeroMetaSnapshot:
        return await self._meta.get(str(request), lambda: self._meta_load(request))

    async def _meta_load(self, request: MetaRequest) -> HeroMetaSnapshot:
        versions = await self.patches()
        positions = (request.position,) if request.position is not None else (1, 2, 3, 4, 5)
        bracket = "" if request.rank == RankBracket.ALL else f",bracketIds:[{request.rank.value}]"
        selections = "\n".join(
            f"p{p}:winDay(take:14,positionIds:[POSITION_{p}],gameModeIds:[ALL_PICK_RANKED]{bracket})"
            "{day heroId matchCount winCount}"
            for p in positions
        )
        payload, fetched = await self._http.request("{heroStats{" + selections + "}}", {})
        available = tuple(v for v in versions if v.effective_at <= fetched)
        if not available:
            raise failure(ProviderErrorCode.INVALID_RESPONSE)
        current = max(available, key=lambda v: (v.effective_at, v.version_id))
        end = fetched.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        first_patch_day = current.effective_at.astimezone(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        if first_patch_day < current.effective_at:
            first_patch_day += timedelta(days=1)
        start = min(end, max(end - timedelta(days=request.days), first_patch_day))
        stats = object_value(field(data(payload), "heroStats"))
        buckets: list[HeroWinBucket] = []
        observed_days: dict[int, set[datetime]] = {}
        for position in positions:
            observed_days[position] = set()
            for raw in rows(field(stats, f"p{position}"), 4096):
                row = object_value(raw)
                day = instant(field(row, "day"))
                if day.hour or day.minute or day.second:
                    raise failure(ProviderErrorCode.INVALID_RESPONSE)
                if start <= day < end:
                    observed_days[position].add(day)
                    buckets.append(
                        HeroWinBucket(
                            day,
                            integer(field(row, "heroId"), minimum=1),
                            position,
                            integer(field(row, "matchCount")),
                            integer(field(row, "winCount")),
                        )
                    )
        notes = ["统计范围：天梯全选，当前版本的完整 UTC 日。"]
        expected_days = int((end - start).total_seconds() // 86400)
        coverage: dict[int, list[int]] = {}
        for position, dates in observed_days.items():
            if len(dates) < expected_days:
                coverage.setdefault(len(dates), []).append(position)
        for days, covered_positions in coverage.items():
            label = "、".join(str(position) for position in covered_positions)
            notes.append(f"{label}号位：有效 {days}/{expected_days} 日，缺日不补零。")
        if coverage:
            notes.append("请求窗口固定，不因来源延迟向前移动。")
        if (
            current.effective_at > first_patch_day - timedelta(days=1)
            and current.effective_at != first_patch_day
        ):
            notes.append("版本切换所在的不完整日桶已排除。")
        latest = max((r.day + timedelta(days=1) for r in buckets), default=None)
        if latest is not None and latest < end:
            notes.append(f"来源数据滞后：最后可用日截至 {latest:%Y-%m-%d} UTC。")
        return HeroMetaSnapshot(
            request,
            DataMetadata(DataSource.STRATZ, fetched, latest, current.name),
            current,
            start,
            end,
            tuple(buckets),
            tuple(notes),
        )

    async def guide(self, hero: Hero, position: int) -> HeroGuide:
        return await self._guides.get(
            f"{hero.hero_id}:{position}", lambda: self._guide_load(hero, position)
        )

    async def _guide_load(self, hero: Hero, position: int) -> HeroGuide:
        errors: list[tuple[str, str]] = []
        items = None
        abilities = None
        talents = None
        week = None
        notes = ["统计分母为对应装备/技能桶的观察场次；不作为整套方案胜率。"]
        query = (
            "query($hero:Short!){heroStats{"
            + (
                f"items:itemFullPurchase(heroId:$hero,positionIds:[POSITION_{position}])"
                "{heroId week position itemId time instance matchCount winCount}"
                f"skills:abilityMinLevel(heroId:$hero,positionIds:[POSITION_{position}])"
                "{heroId week position abilityId level matchCount winCount}"
                f"talents:talent(heroId:$hero,positionIds:[POSITION_{position}])"
                "{heroId week position abilityId matchCount winCount}"
            )
            + "}}"
        )
        try:
            payload, fetched = await self._http.request(query, {"hero": hero.hero_id})
            stats = object_value(field(data(payload), "heroStats"))
            weeks_seen: set[int] = set()
            for name, module in (
                ("items", "statistics"),
                ("skills", "abilities"),
                ("talents", "talents"),
            ):
                try:
                    bucket_rows = tuple(object_value(r) for r in rows(field(stats, name)))
                    if any(field(r, "heroId") != hero.hero_id for r in bucket_rows):
                        raise failure(ProviderErrorCode.INVALID_RESPONSE)
                    if any(field(r, "position") != f"POSITION_{position}" for r in bucket_rows):
                        errors.append((module, "scope_mismatch"))
                        continue
                    weeks = {integer(field(r, "week")) for r in bucket_rows}
                    if len(weeks) > 1:
                        raise failure(ProviderErrorCode.INVALID_RESPONSE)
                    if name == "items":
                        items = tuple(
                            BuildItemBucket(
                                integer(field(r, "itemId"), minimum=1),
                                integer(field(r, "time")),
                                integer(field(r, "instance")),
                                integer(field(r, "matchCount")),
                                integer(field(r, "winCount")),
                            )
                            for r in bucket_rows
                        )
                    elif name == "skills":
                        abilities = tuple(
                            AbilityChoice(
                                integer(field(r, "abilityId")),
                                integer(field(r, "level")),
                                integer(field(r, "matchCount")),
                                integer(field(r, "winCount")),
                            )
                            for r in bucket_rows
                        )
                    else:
                        talents = tuple(
                            AbilityChoice(
                                integer(field(r, "abilityId")),
                                None,
                                integer(field(r, "matchCount")),
                                integer(field(r, "winCount")),
                            )
                            for r in bucket_rows
                        )
                    weeks_seen.update(weeks)
                except ProviderError as error:
                    errors.append((module, error.code.value))
                except ValidationError:
                    errors.append((module, "invalid_response"))
            week = next(iter(weeks_seen)) if len(weeks_seen) == 1 else None
            if len(weeks_seen) > 1:
                notes.append("各模块来源周索引不同，统计窗口尚未核实。")
        except ProviderError as error:
            if error.code in {ProviderErrorCode.AUTHENTICATION, ProviderErrorCode.RATE_LIMITED}:
                raise
            errors.append(("statistics", error.code.value))
            fetched = None
        samples: list[GuideSample] = []
        try:
            query = (
                "query($hero:Short!){heroStats{"
                f"guide(heroId:$hero,positionId:POSITION_{position},take:1)"
                "{heroId guides(take:3){heroId matchId steamAccountId}}}}"
            )
            payload, fetched_samples = await self._http.request(query, {"hero": hero.hero_id})
            if fetched is None:
                fetched = fetched_samples
            groups_raw = rows(field(object_value(field(data(payload), "heroStats")), "guide"), 16)
            seen: set[int] = set()
            for raw in groups_raw:
                group = object_value(raw)
                if field(group, "heroId") != hero.hero_id:
                    raise failure(ProviderErrorCode.INVALID_RESPONSE)
                for candidate in rows(field(group, "guides"), 3):
                    row = object_value(candidate)
                    if field(row, "heroId") != hero.hero_id:
                        raise failure(ProviderErrorCode.INVALID_RESPONSE)
                    match_id = MatchId(integer(field(row, "matchId"), minimum=1))
                    if match_id.value in seen or len(samples) >= 3:
                        continue
                    seen.add(match_id.value)
                    account = integer(field(row, "steamAccountId"), minimum=1)
                    sample = await self._selected_sample(match_id, hero, account)
                    if sample.player.position != f"POSITION_{position}":
                        raise failure(ProviderErrorCode.INVALID_RESPONSE)
                    samples.append(sample)
        except ProviderError as error:
            if error.code in {ProviderErrorCode.AUTHENTICATION, ProviderErrorCode.RATE_LIMITED}:
                raise
            errors.append(("samples", error.code.value))
        if fetched is None:
            raise failure(ProviderErrorCode.UNAVAILABLE)
        if talents:
            try:
                versions = tuple(v for v in await self.patches() if v.effective_at <= fetched)
                if not versions:
                    raise failure(ProviderErrorCode.INVALID_RESPONSE)
                label_patch = max(versions, key=lambda v: (v.effective_at, v.version_id))
                selected = sorted(talents, key=lambda v: (-v.matches, v.ability_id))[:16]
                names = await self.label_ids(
                    tuple(v.ability_id for v in selected), label_patch.version_id
                )
                talents = tuple(replace(v, name=names.get(v.ability_id)) for v in talents)
                notes.append(
                    f"天赋中文名称使用 {label_patch.name} 常量，仅解释技能标识；统计窗口未核实。"
                )
                if any(not v.name for v in sorted(talents, key=lambda v: -v.matches)[:16]):
                    notes.append("部分天赋中文名称未返回，保留技能 ID，不推测效果。")
            except ProviderError as error:
                notes.append(f"天赋中文名称获取失败（{error.code.value}），保留技能 ID。")
        return HeroGuide(
            hero,
            position,
            DataMetadata(DataSource.STRATZ, fetched),
            week,
            items,
            abilities,
            talents,
            tuple(samples),
            tuple(notes),
            tuple(errors),
        )

    async def sample(self, match_id: MatchId, hero: Hero, detail: MatchDetail) -> GuideSample:
        players = tuple(p for p in detail.players or () if p.hero_id == hero.hero_id)
        if len(players) != 1:
            raise failure(ProviderErrorCode.NOT_FOUND)
        player = players[0]
        if player.account_id is None:
            versions = await self.patches()
            version = next((v for v in versions if v.version_id == detail.game_version_id), None)
            return GuideSample(
                hero,
                match_id,
                replace(detail.metadata, patch=None if version is None else version.name),
                player,
                version,
                detail.started_at,
                detail.duration_seconds,
                detail.did_radiant_win,
                None,
                None,
            )
        account_id = player.account_id.value
        return await self._samples.get(
            f"{match_id.value}:{hero.hero_id}",
            lambda: self._selected_sample(match_id, hero, account_id),
        )

    async def _selected_sample(self, match_id: MatchId, hero: Hero, account: int) -> GuideSample:
        payload, fetched = await self._http.request(
            SAMPLE_QUERY, {"matchId": match_id.value, "accountId": account}
        )
        metadata = DataMetadata(DataSource.STRATZ, fetched)
        detail = match_detail(payload, match_id, metadata)
        if (
            not isinstance(detail, MatchDetail)
            or detail.players is None
            or len(detail.players) != 1
        ):
            raise failure(ProviderErrorCode.NOT_FOUND)
        player = detail.players[0]
        if (
            player.hero_id != hero.hero_id
            or player.account_id is None
            or player.account_id.value != account
        ):
            raise failure(ProviderErrorCode.INVALID_RESPONSE)
        raw = object_value(
            rows(field(object_value(field(data(payload), "match")), "players"), 1)[0]
        )
        purchase_events = None
        if raw.get("stats") is not None:
            purchase_raw = field(object_value(raw["stats"]), "itemPurchases")
            if purchase_raw is not None:
                purchase_events = tuple(
                    PurchaseEvent(
                        integer(field(object_value(r), "time"), minimum=-2147483648),
                        integer(field(object_value(r), "itemId"), minimum=1),
                    )
                    for r in rows(purchase_raw, 1024)
                )
        versions = await self.patches()
        version = next((v for v in versions if v.version_id == detail.game_version_id), None)
        events = upgrades(field(raw, "abilities"))
        label_error = None
        if events and version is not None:
            try:
                names = await self.labels(events, version.version_id)
                events = tuple(
                    replace(event, name=names.get(event.ability_id) or event.name)
                    for event in events
                )
            except ProviderError as error:
                label_error = error.code.value
        return GuideSample(
            hero,
            match_id,
            replace(metadata, patch=None if version is None else version.name),
            player,
            version,
            detail.started_at,
            detail.duration_seconds,
            detail.did_radiant_win,
            events,
            purchase_events,
            label_error,
        )
