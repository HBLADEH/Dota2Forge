"""Explicit read-only schema probe; no credentials or match identities are printed."""

import asyncio
import json
import os
from pathlib import Path

import httpx
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure._stratz_http import StratzHTTP

TYPES = (
    "MatchType",
    "MatchPlayerType",
    "MatchPlayerStatsType",
    "SteamAccountType",
    "MatchLaneType",
    "MatchPlayerPositionType",
)


async def main():
    selections = "\n".join(
        f't{i}: __type(name: "{name}") {{ name fields {{ name description '
        "type { kind name ofType { kind name ofType { kind name } } } } "
        "enumValues { name description } }"
        for i, name in enumerate(TYPES)
    )
    async with httpx.AsyncClient(trust_env=False) as client:
        provider = StratzHTTP(client, os.environ["STRATZ_TOKEN"], SystemClock(), 20)
        payload, _ = await provider.request("query Dota2ForgeReportSchema {" + selections + "}", {})
        assert isinstance(payload, dict) and not payload.get("errors")
        types = {name: payload["data"][f"t{i}"] for i, name in enumerate(TYPES)}
    result = {"checked_on": "2026-10-09", "types": types, "client_closed": client.is_closed}
    Path(__file__).with_name("schema.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for name, value in types.items():
        print(name, None if value is None else [field["name"] for field in value["fields"] or []])
        if value and value.get("enumValues"):
            print([row["name"] for row in value["enumValues"]])


if __name__ == "__main__":
    asyncio.run(main())
