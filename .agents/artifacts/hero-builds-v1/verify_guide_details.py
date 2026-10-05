"""Explicit small hero-only probe; never persist accounts, match IDs or credentials."""

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from dota2forge_core import ProviderError
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure._stratz_http import StratzHTTP
from dota2forge_core.infrastructure.hero_catalog import load_hero_catalog
from dota2forge_core.infrastructure.opendota import OpenDotaProvider


def state(value):
    if value is None:
        return "null"
    if isinstance(value, list):
        return "empty" if not value else "populated"
    return "populated"


async def main():
    report = {"checked_on": "2026-10-05", "stratz": [], "opendota": []}
    async with httpx.AsyncClient(trust_env=False) as client:
        transport = StratzHTTP(client, os.environ["STRATZ_TOKEN"], SystemClock(), 20)
        for hero_id, position in ((1, "POSITION_1"), (2, "POSITION_3")):
            query = (
                "{heroStats{guide(heroId:"
                + str(hero_id)
                + ",positionId:"
                + position
                + ",take:1){heroId matchCount guides(take:1){heroId createdDateTime itemIds "
                "matchPlayer{heroId position abilities{abilityId level time isTalent} "
                "stats{itemPurchases{time itemId}}} "
                "match{gameVersionId startDateTime players{heroId position "
                "item0Id item1Id item2Id item3Id item4Id item5Id}}}}}}"
            )
            row = {"hero_id": hero_id, "requested_position": position}
            try:
                payload, fetched = await transport.request(query, {})
                row["fetched_at"] = fetched.isoformat()
                if payload.get("errors"):
                    row["error"] = "graphql_error"
                    row["error_messages"] = [
                        str(error.get("message", ""))[:300] for error in payload["errors"]
                    ]
                else:
                    groups = payload["data"]["heroStats"]["guide"]
                    row["groups"] = []
                    for group in groups or []:
                        guides = []
                        for guide in group.get("guides") or []:
                            match = guide.get("match") or {}
                            selected = [
                                p for p in match.get("players") or [] if p.get("heroId") == hero_id
                            ]
                            guides.append(
                                {
                                    "item_ids_state": state(guide.get("itemIds")),
                                    "match_player_state": state(guide.get("matchPlayer")),
                                    "match_player_hero_matches": (
                                        guide.get("matchPlayer") or {}
                                    ).get("heroId")
                                    == hero_id,
                                    "match_player_position": (guide.get("matchPlayer") or {}).get(
                                        "position"
                                    ),
                                    "ability_state": state(
                                        (guide.get("matchPlayer") or {}).get("abilities")
                                    ),
                                    "ability_count": len(
                                        (guide.get("matchPlayer") or {}).get("abilities") or []
                                    ),
                                    "talent_count": sum(
                                        bool(a.get("isTalent"))
                                        for a in (guide.get("matchPlayer") or {}).get("abilities")
                                        or []
                                    ),
                                    "purchase_state": state(
                                        ((guide.get("matchPlayer") or {}).get("stats") or {}).get(
                                            "itemPurchases"
                                        )
                                    ),
                                    "purchase_count": len(
                                        ((guide.get("matchPlayer") or {}).get("stats") or {}).get(
                                            "itemPurchases"
                                        )
                                        or []
                                    ),
                                    "purchase_times_present": all(
                                        type(p.get("time")) is int
                                        for p in (
                                            (guide.get("matchPlayer") or {}).get("stats") or {}
                                        ).get("itemPurchases")
                                        or []
                                    ),
                                    "game_version_id": match.get("gameVersionId"),
                                    "created_date_time": guide.get("createdDateTime"),
                                    "match_version_present": match.get("gameVersionId") is not None,
                                    "observed_time_present": match.get("startDateTime") is not None,
                                    "selected_players": [
                                        {
                                            "position": p.get("position"),
                                            "ability_state": "not_requested",
                                            "end_item_count": sum(
                                                bool(p.get(f"item{i}Id")) for i in range(6)
                                            ),
                                        }
                                        for p in selected
                                    ],
                                }
                            )
                        row["groups"].append(
                            {"match_count": group.get("matchCount"), "guides": guides}
                        )
            except ProviderError as error:
                row["error"] = error.code.value
            report["stratz"].append(row)
        provider = OpenDotaProvider(client, clock=SystemClock())
        catalog = load_hero_catalog()
        for name in () if "--stratz-only" in sys.argv else ("AM", "斧王"):
            hero = catalog.resolve(name)
            try:
                result = await provider.get_hero_item_statistics(hero)
            except ProviderError as error:
                report["opendota"].append({"hero_id": hero.hero_id, "error": error.code.value})
                continue
            report["opendota"].append(
                {
                    "hero_id": result.hero.hero_id,
                    "fetched_at": result.metadata.fetched_at.isoformat(),
                    "observed_at": result.metadata.observed_at,
                    "stages": {
                        stage.stage.value: len(stage.items) if stage.items is not None else None
                        for stage in result.stages
                    },
                    "missing_fields": result.missing_fields,
                }
            )
    report["client_closed"] = client.is_closed
    Path(".agents/artifacts/hero-builds-v1/guide-details.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
