"""Explicit live diagnostics: public bucket shapes and anonymous counts, no player payloads."""

import asyncio
import json
import os
from collections import Counter
from pathlib import Path

import httpx
from dota2forge_core import (
    AbilityChoice,
    BuildItemBucket,
    HeroFeatureService,
    MatchId,
    ProviderError,
)
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure._stratz_heroes import integer
from dota2forge_core.infrastructure.hero_catalog import load_hero_catalog
from dota2forge_core.infrastructure.stratz import StratzProvider


async def main():
    report = {}
    async with httpx.AsyncClient(trust_env=False) as client:
        provider = StratzProvider(client, token=os.environ["STRATZ_TOKEN"], clock=SystemClock())
        query = """{heroStats{
          items:itemFullPurchase(heroId:8,positionIds:[POSITION_1]){
            heroId week position itemId time instance matchCount winCount}
          skills:abilityMinLevel(heroId:8,positionIds:[POSITION_1]){
            heroId week position abilityId level matchCount winCount}
          talents:talent(heroId:8,positionIds:[POSITION_1]){
            heroId week position abilityId matchCount winCount}
          guide(heroId:8,positionId:POSITION_1,take:1){
            heroId guides(take:3){heroId matchId steamAccountId}}
        }}"""
        payload, _ = await provider._http.request(query, {})
        stats = payload["data"]["heroStats"]
        for key in ("items", "skills", "talents"):
            rows = stats[key] or []
            failures = Counter()
            for row in rows:
                try:
                    if key == "items":
                        BuildItemBucket(
                            row["itemId"],
                            row["time"],
                            row["instance"],
                            row["matchCount"],
                            row["winCount"],
                        )
                    else:
                        AbilityChoice(
                            row["abilityId"],
                            row["level"] if key == "skills" else None,
                            row["matchCount"],
                            row["winCount"],
                        )
                except ValueError as error:
                    failures[str(error)] += 1
                for field in ("abilityId", "level") if key == "skills" else ():
                    if row[field] is None:
                        failures[field + "_null"] += 1
                    if row[field] == 0:
                        failures[field + "_zero"] += 1
            report[key] = {
                "rows": len(rows),
                "positions": dict(Counter(r["position"] for r in rows)),
                "weeks": sorted({r["week"] for r in rows}),
                "failures": dict(failures),
            }
        report["samples"] = []
        for group in stats["guide"] or []:
            for row in group["guides"] or []:
                try:
                    sample = await provider._heroes._selected_sample(
                        MatchId(integer(row["matchId"], minimum=1)),
                        load_hero_catalog().resolve("主宰"),
                        integer(row["steamAccountId"], minimum=1),
                    )
                    report["samples"].append(
                        {
                            "valid_position": sample.player.position == "POSITION_1",
                            "upgrades": len(sample.upgrades or ()),
                            "purchases": len(sample.purchases or ()),
                        }
                    )
                except ProviderError as error:
                    report["samples"].append({"error": error.code.value})
        service = HeroFeatureService(provider, provider, load_hero_catalog())
        guide = await service.get_guide("主宰", 1)
        report["implementation"] = {"errors": guide.module_errors, "samples": len(guide.samples)}
        await provider.close()
    Path(__file__).with_name("guide-shapes.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
