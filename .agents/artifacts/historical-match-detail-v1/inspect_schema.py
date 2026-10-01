"""Explicit read-only schema inspection; output schema, never player data or credentials."""

import asyncio
import json
import os

import httpx
from dota2forge_core import ProviderError
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure._stratz_http import StratzHTTP

QUERY = """
query Dota2ForgeMatchSchema {
  __schema {
    queryType {
      name
      fields {
        name description
        type { kind name ofType { kind name ofType { kind name } } }
        args { name type { kind name ofType { kind name } } }
      }
    }
  }
  match: __type(name: "MatchType") {
    name fields { name description type { kind name ofType { kind name } } }
  }
  participant: __type(name: "MatchPlayerType") {
    name fields { name description type { kind name ofType { kind name } } }
  }
}
"""


async def main() -> None:
    async with httpx.AsyncClient(trust_env=False) as client:
        provider = StratzHTTP(client, os.environ["STRATZ_TOKEN"], SystemClock(), 15)
        payload, _ = await provider.request(QUERY, {})
        if not isinstance(payload, dict) or payload.get("errors"):
            raise ValueError("Schema inspection failed")
        schema = payload["data"]
        schema["__schema"]["queryType"]["fields"] = [
            field for field in schema["__schema"]["queryType"]["fields"] if field["name"] == "match"
        ]
        for name, wanted in {
            "match": {
                "id",
                "startDateTime",
                "durationSeconds",
                "didRadiantWin",
                "gameMode",
                "gameVersion",
                "gameVersionId",
                "isStats",
                "parsedDateTime",
                "players",
            },
            "participant": {
                "playerSlot",
                "steamAccountId",
                "steamAccount",
                "heroId",
                "isRadiant",
                "kills",
                "deaths",
                "assists",
                "goldPerMinute",
                "experiencePerMinute",
                "item0Id",
                "item1Id",
                "item2Id",
                "item3Id",
                "item4Id",
                "item5Id",
            },
        }.items():
            if schema[name] is not None:
                schema[name]["fields"] = [
                    field for field in schema[name]["fields"] if field["name"] in wanted
                ]
    print(
        json.dumps(
            {"schema": schema, "client_closed": client.is_closed}, ensure_ascii=False, indent=2
        )
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ProviderError as error:
        print(
            json.dumps(
                {"error": error.code.value, "retry_after_seconds": error.retry_after_seconds}
            )
        )
        raise SystemExit(1) from None
    except (KeyError, ValueError):
        print("Schema or local configuration unavailable")
        raise SystemExit(2) from None
