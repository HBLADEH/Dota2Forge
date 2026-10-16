"""Explicit public constants probe; no account or match query."""

import asyncio
import json
import os
from pathlib import Path

import httpx
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure._stratz_http import StratzHTTP


async def main():
    async with httpx.AsyncClient(trust_env=False) as client:
        transport = StratzHTTP(client, os.environ["STRATZ_TOKEN"], SystemClock(), 30)
        schema, _ = await transport.request(
            '{__type(name:"AbilityType"){fields{name type{kind name ofType{kind name}}}}}', {}
        )
        query = (
            "{constants{"
            + " ".join(
                f"a{i}:ability(id:{identifier},gameVersionId:190,language:S_CHINESE)"
                "{id name language{displayName description attributes}}"
                for i, identifier in enumerate((730, 7021, 7394, 915, 1192, 1013, 628, 6105))
            )
            + "}}"
        )
        payload, fetched = await transport.request(query, {})
    report = {"schema": schema, "constants": payload, "fetched_at": fetched.isoformat()}
    Path(__file__).with_name("constants.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
