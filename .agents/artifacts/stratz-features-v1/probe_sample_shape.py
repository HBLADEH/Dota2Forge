"""Diagnose mapping with booleans/type counts only; never write player payloads."""

import asyncio
import json
import os
import re
from collections import Counter
from pathlib import Path

import httpx
from dota2forge_core import DataMetadata, DataSource, MatchId, ProviderError
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure._stratz_detail import match_detail
from dota2forge_core.infrastructure._stratz_heroes import SAMPLE_QUERY, upgrades
from dota2forge_core.infrastructure._stratz_http import StratzHTTP


async def main() -> None:
    report = {}
    async with httpx.AsyncClient(trust_env=False) as client:
        transport = StratzHTTP(client, os.environ["STRATZ_TOKEN"], SystemClock(), 20)
        payload, _ = await transport.request(
            """
          {
          heroStats{
          guide(heroId:2, positionId:POSITION_3, take:1){
          heroId guides(take:1){
          heroId matchId steamAccountId}
          }
          }
          }
          """,
            {},
        )
        groups = payload["data"]["heroStats"]["guide"] or []
        for group in groups:
            for selected in group["guides"] or []:
                mid, account = selected["matchId"], selected["steamAccountId"]
                payload, fetched = await transport.request(
                    SAMPLE_QUERY, {"matchId": mid, "accountId": account}
                )
                report["graphql_errors"] = bool(payload.get("errors"))
                report["invalid_fields"] = [
                    field
                    for error in payload.get("errors") or []
                    for field in re.findall(
                        r'Cannot query field "([A-Za-z_][A-Za-z0-9_]*)"', error.get("message", "")
                    )
                ]
                messages = " ".join(
                    error.get("message", "").lower() for error in payload.get("errors") or []
                )
                report["error_categories"] = {
                    key: key in messages
                    for key in (
                        "complex",
                        "argument",
                        "required",
                        "permission",
                        "rate",
                        "invalid",
                        "unknown",
                        "schema",
                    )
                }
                match = (payload.get("data") or {}).get("match") or {}
                players = match.get("players") or []
                report["selected_count"] = len(players)
                report["players"] = []
                for player in players:
                    event_rows = player.get("abilities") or []
                    shape = {
                        "hero_matches": player.get("heroId") == 2,
                        "account_matches": player.get("steamAccountId") == account,
                        "steam_nested_matches": (player.get("steamAccount") or {}).get("id")
                        == account,
                        "position": player.get("position"),
                        "ability_count": len(event_rows),
                        "ability_types": {
                            field: dict(
                                Counter(type(row.get(field)).__name__ for row in event_rows)
                            )
                            for field in ("abilityId", "level", "time", "isTalent")
                        },
                    }
                    try:
                        upgrades(player.get("abilities"))
                        shape["upgrades_valid"] = True
                    except ProviderError:
                        shape["upgrades_valid"] = False
                    report["players"].append(shape)
                try:
                    match_detail(payload, MatchId(mid), DataMetadata(DataSource.STRATZ, fetched))
                    report["detail_valid"] = True
                except ProviderError:
                    report["detail_valid"] = False
                break
    Path(__file__).with_name("sample-shape.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
