"""Explicit schema-only probe; uv injects the ignored .env, no identities requested."""

import asyncio
import json
import os
from pathlib import Path

import httpx
from dota2forge_core import ProviderError
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure._stratz_http import StratzHTTP

TYPES = (
    "HeroStatsQuery",
    "ConstantsQuery",
    "HeroWinDayType",
    "HeroWinHourType",
    "HeroWinGameVersionType",
    "FilterHeroWinRequestGroupBy",
    "RankBracket",
    "RankBracketBasicEnum",
    "MatchPlayerPositionType",
    "GameModeEnumType",
    "GameVersionType",
    "HeroGuideListType",
    "HeroGuideType",
    "HeroItemPurchaseType",
    "HeroAbilityMinType",
    "HeroAbilityTalentType",
    "PlayerAbilityType",
    "MatchPlayerStatsType",
    "ItemType",
    "AbilityType",
)
TYPE = "kind name ofType { kind name ofType { kind name ofType { kind name } } }"


async def main() -> None:
    output = {"checked_on": "2026-10-14", "types": {}}
    fields = (
        "name kind description enumValues { name description } "
        "fields { name description type { " + TYPE + " } "
        "args { name description defaultValue type { " + TYPE + " } } }"
    )
    query = (
        "{"
        + " ".join(
            f't{index}:__type(name:"{name}")' + "{" + fields + "}"
            for index, name in enumerate(TYPES)
        )
        + "}"
    )
    async with httpx.AsyncClient(trust_env=False) as client:
        transport = StratzHTTP(client, os.environ["STRATZ_TOKEN"], SystemClock(), 30)
        try:
            payload, fetched = await transport.request(query, {})
        except ProviderError as error:
            print(json.dumps({"error": error.code.value, "retry_after": error.retry_after_seconds}))
            return
        if not isinstance(payload, dict) or payload.get("errors"):
            print(
                json.dumps(
                    {
                        "error": "graphql_error",
                        "messages": [e.get("message") for e in payload.get("errors", [])],
                    }
                )
            )
            return
        output["fetched_at"] = fetched.isoformat()
        output["types"] = {name: payload["data"].get(f"t{i}") for i, name in enumerate(TYPES)}
    output["client_closed"] = client.is_closed
    Path(__file__).with_name("schema.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "types": {
                    name: {
                        "fields": [f["name"] for f in (value or {}).get("fields") or []],
                        "enum": [f["name"] for f in (value or {}).get("enumValues") or []],
                    }
                    for name, value in output["types"].items()
                },
                "client_closed": client.is_closed,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
