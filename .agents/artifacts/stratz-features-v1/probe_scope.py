"""Final read-only public-statistics probe; no player identities or secrets saved."""

import asyncio
import json
import os
from pathlib import Path

import httpx
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure._stratz_http import StratzHTTP


async def main() -> None:
    async with httpx.AsyncClient(trust_env=False) as client:
        transport = StratzHTTP(client, os.environ["STRATZ_TOKEN"], SystemClock(), 30)
        payload, fetched = await transport.request(
            """
          {
          lang:__type(name:"LanguageEnum"){
          enumValues{
          name}
          }
          heroStats{
          days:winDay(heroIds:[2], take:14, positionIds:[POSITION_3],
          gameModeIds:[ALL_PICK_RANKED]){
          day heroId matchCount winCount}
          p1:itemFullPurchase(heroId:2, positionIds:[POSITION_1], matchLimit:1000){
          itemId time instance position matchCount winCount week}
          p3:itemFullPurchase(heroId:2, positionIds:[POSITION_3], matchLimit:1000){
          itemId time instance position matchCount winCount week}
          }
          }
          """,
            {},
        )
        if payload.get("errors"):
            report = {"graphql_errors": True}
        else:
            stats = payload["data"]["heroStats"]
            report = {
                "fetched_at": fetched.isoformat(),
                "languages": payload["data"]["lang"],
                "daily_count": len(stats["days"]),
                "daily_timestamps": sorted({r["day"] for r in stats["days"]}),
                "p1_rows": len(stats["p1"]),
                "p3_rows": len(stats["p3"]),
                "same_results": stats["p1"] == stats["p3"],
                "p3_positions": sorted({r["position"] for r in stats["p3"]}),
                "p3_week_indices": sorted({r["week"] for r in stats["p3"]}),
            }
    report["client_closed"] = client.is_closed
    Path(__file__).with_name("scope.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
