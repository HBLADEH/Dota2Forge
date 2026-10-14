"""Explicit public hero-only readiness probe. No accounts/match IDs/names persisted."""

import asyncio
import json
import os
from pathlib import Path

import httpx
from dota2forge_core import ProviderError
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure._stratz_http import StratzHTTP

QUERIES = {
    "constants_and_meta": """
          {
          constants{
          gameVersions{
          id name asOfDateTime}
          }
          heroStats{
          days:winDay(heroIds:[1, 2], take:2, skip:0, positionIds:[POSITION_3],
          gameModeIds:[ALL_PICK_RANKED]){
          day heroId winCount matchCount}
          grouped:winDay(heroIds:[1, 2], take:2, skip:0, positionIds:[POSITION_3],
          gameModeIds:[ALL_PICK_RANKED], groupBy:HERO_ID){
          day heroId winCount matchCount}
          versions:winGameVersion(heroIds:[1, 2], take:2, positionIds:[POSITION_3],
          gameModeIds:[ALL_PICK_RANKED]){
          gameVersionId heroId durationMinute winCount matchCount}
          p1:winDay(heroIds:[2], take:2, positionIds:[POSITION_1],
          gameModeIds:[ALL_PICK_RANKED]){
          day heroId winCount matchCount}
          p3:winDay(heroIds:[2], take:2, positionIds:[POSITION_3],
          gameModeIds:[ALL_PICK_RANKED]){
          day heroId winCount matchCount}
          legend:winDay(heroIds:[2], take:2, positionIds:[POSITION_3],
          bracketIds:[LEGEND], gameModeIds:[ALL_PICK_RANKED]){
          day heroId winCount matchCount}
          }
          }
          """,
    "guide_shape": """
          {
          heroStats{
          itemFullPurchase(heroId:2, positionIds:[POSITION_3]){
          heroId week position itemId instance time matchCount winCount}
          abilityMinLevel(heroId:2, positionIds:[POSITION_3]){
          heroId week position abilityId level matchCount winCount}
          talent(heroId:2, positionIds:[POSITION_3]){
          heroId week position abilityId matchCount winCount}
          guide(heroId:2, positionId:POSITION_3, take:1){
          heroId matchCount guides(take:1){
          heroId matchId steamAccountId createdDateTime
          match{
          gameVersionId startDateTime durationSeconds didRadiantWin}
          matchPlayer{
          heroId position playerSlot isRadiant kills deaths assists imp
          item0Id item1Id item2Id item3Id item4Id item5Id backpack0Id backpack1Id
          backpack2Id neutral0Id
          abilities{
          abilityId level time isTalent}
          stats{
          itemPurchases{
          time itemId}
          }
          }
          }
          }
          }
          }
          """,
    "constants_schema": """
          {
          __type(name:"ConstantQuery"){
          name fields{
          name args{
          name defaultValue}
          type{
          kind name ofType{
          kind name}
          }
          }
          }
          }
          """,
}


async def main() -> None:
    report = {"checked_on": "2026-10-14", "observations": {}}
    async with httpx.AsyncClient(trust_env=False) as client:
        transport = StratzHTTP(client, os.environ["STRATZ_TOKEN"], SystemClock(), 30)
        for label, query in QUERIES.items():
            try:
                payload, fetched = await transport.request(query, {})
            except ProviderError as error:
                report["observations"][label] = {"error": error.code.value}
                if error.code.value == "rate_limited":
                    break
                continue
            if payload.get("errors"):
                report["observations"][label] = {
                    "error": "graphql_error",
                    "messages": [e.get("message") for e in payload["errors"]],
                }
                continue
            data = payload["data"]
            if label == "guide_shape":
                stats = data["heroStats"]
                summary = {
                    name: {"count": len(rows or []), "sample": (rows or [])[:5]}
                    for name, rows in stats.items()
                    if name != "guide"
                }
                summary["guides"] = []
                for group in stats.get("guide") or []:
                    for guide in group.get("guides") or []:
                        player = guide.get("matchPlayer") or {}
                        abilities = player.get("abilities")
                        purchases = (player.get("stats") or {}).get("itemPurchases")
                        summary["guides"].append(
                            {
                                "group_count": group.get("matchCount"),
                                "hero_matches": player.get("heroId") == 2,
                                "position": player.get("position"),
                                "patch_id": (guide.get("match") or {}).get("gameVersionId"),
                                "abilities": abilities,
                                "purchase_count": None if purchases is None else len(purchases),
                                "purchase_time_range": None
                                if not purchases
                                else [
                                    min(p["time"] for p in purchases),
                                    max(p["time"] for p in purchases),
                                ],
                                "source_equipment_fields": sum(
                                    player.get(f"item{i}Id") is not None for i in range(6)
                                ),
                            }
                        )
                data = summary
            elif label == "constants_and_meta":
                data["constants"]["gameVersions"] = data["constants"]["gameVersions"][-8:]
            report["observations"][label] = {"fetched_at": fetched.isoformat(), "data": data}
    report["client_closed"] = client.is_closed
    Path(__file__).with_name("readiness.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
