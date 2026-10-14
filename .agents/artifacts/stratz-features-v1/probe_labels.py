"""Inspect public ability label semantics only."""

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
        payload, _ = await transport.request(
            '{__type(name:"AbilityLanguageType"){fields{name}}}', {}
        )
        fields = [f["name"] for f in payload["data"]["__type"]["fields"]]
        selected = "displayName" if "displayName" in fields else None
        report = {"language_fields": fields}
        if selected:
            payload, fetched = await transport.request(
                "{constants{ability(id:5007,gameVersionId:190,language:S_CHINESE)"
                "{id name language{displayName}}}}",
                {},
            )
            report["label_example"] = payload
            report["fetched_at"] = fetched.isoformat()
    Path(__file__).with_name("labels.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
