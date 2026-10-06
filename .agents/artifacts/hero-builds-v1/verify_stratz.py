"""Explicit public hero schema probe; credentials are only injected by uv --env-file."""

import asyncio
import json
import os
from pathlib import Path

import httpx
from dota2forge_core import ProviderError
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure._stratz_http import StratzHTTP

TYPE = "kind name ofType { kind name ofType { kind name } }"


async def main() -> None:
    report = {"checked_on": "2026-10-05", "requests": []}
    async with httpx.AsyncClient(trust_env=False) as client:
        transport = StratzHTTP(client, os.environ["STRATZ_TOKEN"], SystemClock(), 20)

        async def fetch(label, query):
            try:
                payload, fetched = await transport.request(query, {})
            except ProviderError as error:
                report["requests"].append(
                    {
                        "label": label,
                        "error": error.code.value,
                        "retry_after": error.retry_after_seconds,
                    }
                )
                return None
            if not isinstance(payload, dict) or payload.get("errors"):
                report["requests"].append({"label": label, "error": "graphql_or_schema_error"})
                return None
            report["requests"].append({"label": label, "fetched_at": fetched.isoformat()})
            return payload.get("data")

        fields = "fields { name type { " + TYPE + " } args { name type { " + TYPE + " } } }"
        root = await fetch("root", "{ __schema { queryType { name " + fields + " } } }")
        if root:
            query_type = root["__schema"]["queryType"]
            selected = [
                row
                for row in query_type["fields"]
                if any(word in row["name"].lower() for word in ("hero", "guide", "constant"))
            ]
            report["root_fields"] = selected
            queue = []

            def name_of(value):
                while value.get("ofType"):
                    value = value["ofType"]
                return value.get("name")

            queue.extend(name_of(row["type"]) for row in selected)
            seen = set()
            while queue and len(seen) < 12:
                name = queue.pop(0)
                if (
                    not name
                    or name in seen
                    or name in ("Int", "String", "Boolean", "Float", "Long")
                ):
                    continue
                seen.add(name)
                data = await fetch(name, '{ __type(name:"' + name + '") { name ' + fields + " } }")
                if not data or not data.get("__type"):
                    break
                report.setdefault("types", {})[name] = data["__type"]
                for row in data["__type"].get("fields") or []:
                    if any(
                        word in row["name"].lower()
                        for word in ("guide", "build", "item", "ability", "talent", "hero")
                    ):
                        queue.append(name_of(row["type"]))
    report["client_closed"] = client.is_closed
    Path(".agents/artifacts/hero-builds-v1/stratz-schema.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    print(
        json.dumps(
            {
                "requests": report["requests"],
                "root_fields": [row["name"] for row in report.get("root_fields", [])],
                "types": list(report.get("types", {})),
                "client_closed": report["client_closed"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
