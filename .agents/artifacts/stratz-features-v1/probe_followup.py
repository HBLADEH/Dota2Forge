"""Small source verification; persist only public constants and anonymous shapes."""

import asyncio
import json
import os
from pathlib import Path

import httpx
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure._stratz_http import StratzHTTP


async def main() -> None:
    report = {}
    async with httpx.AsyncClient(trust_env=False) as client:
        transport = StratzHTTP(client, os.environ["STRATZ_TOKEN"], SystemClock(), 30)
        payload, _ = await transport.request(
            """
          {
          constants{
          gameVersions{
          id name asOfDateTime}
          }
          a:__type(name:"MatchType"){
          fields{
          name args{
          name type{
          kind name ofType{
          kind name}
          }
          }
          }
          }
          b:__type(name:"ConstantQuery"){
          fields{
          name args{
          name type{
          kind name ofType{
          kind name}
          }
          }
          }
          }
          heroStats{
          guide(heroId:2, positionId:POSITION_3, take:1){
          heroId matchCount guides(take:3){
          heroId matchId steamAccountId matchPlayer{
          heroId}
          }
          }
          }
          }
          """,
            {},
        )
        if payload.get("errors"):
            print(json.dumps({"errors": [e.get("message") for e in payload["errors"]]}))
            return
        data = payload["data"]
        report["versions"] = sorted(
            data["constants"]["gameVersions"], key=lambda r: r["asOfDateTime"], reverse=True
        )[:4]
        report["match_players_args"] = [f for f in data["a"]["fields"] if f["name"] == "players"]
        report["constants_args"] = [
            f for f in data["b"]["fields"] if f["name"] in ("ability", "abilities", "item")
        ]
        report["samples"] = []
        for group in data["heroStats"]["guide"] or []:
            for guide in group["guides"] or []:
                match_id = guide.get("matchId")
                account = guide.get("steamAccountId")
                observation = {
                    "hero_matches": guide.get("heroId") == 2,
                    "match_present": type(match_id) is int and match_id > 0,
                    "account_present": type(account) is int and account > 0,
                    "nested_player_present": guide.get("matchPlayer") is not None,
                }
                if not observation["match_present"] or not observation["account_present"]:
                    report["samples"].append(observation)
                    continue
                selected, _ = await transport.request(
                    """
          query($m:Long!, $a:Long!){
          match(id:$m){
          gameVersionId
          players(steamAccountId:$a){
          heroId position playerSlot
          abilities{
          abilityId level time isTalent}
          stats{
          itemPurchases{
          time itemId}
          }
          }
          }
          }
          """,
                    {"m": match_id, "a": account},
                )
                if selected.get("errors"):
                    observation["error"] = "graphql"
                else:
                    players = (selected["data"].get("match") or {}).get("players")
                    observation["selected_count"] = None if players is None else len(players)
                    observation["players"] = [
                        {
                            "hero_matches": p.get("heroId") == 2,
                            "position": p.get("position"),
                            "abilities": p.get("abilities"),
                            "purchase_count": None
                            if (p.get("stats") or {}).get("itemPurchases") is None
                            else len(p["stats"]["itemPurchases"]),
                        }
                        for p in players or []
                    ]
                report["samples"].append(observation)
                break
    report["client_closed"] = client.is_closed
    Path(__file__).with_name("followup.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
