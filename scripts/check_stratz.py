"""Explicit, read-only STRATZ integration check; never invoked by ordinary tests."""

import argparse
import asyncio
import json
import os

import httpx
from dota2forge_core import AccountId, ProviderError, ValidationError, parse_account_id
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure.stratz import StratzProvider


async def check(token: str, account_id: AccountId, timeout: float, limit: int) -> None:
    async with httpx.AsyncClient(trust_env=False) as client:
        provider = StratzProvider(client, token=token, clock=SystemClock(), timeout_seconds=timeout)
        player = await provider.get_player(account_id)
        recent = await provider.get_recent_matches(account_id, limit)
    print(
        json.dumps(
            {
                "source": player.metadata.source.value,
                "profile_missing_fields": player.missing_fields,
                "matches": len(recent.matches),
                "requested_limit": limit,
                "match_missing_fields": sorted(
                    {f for m in recent.matches for f in m.missing_fields}
                ),
                "same_account": player.account_id == recent.account_id == account_id,
                "observed_at_unknown": player.metadata.observed_at is None,
                "client_closed": client.is_closed,
            }
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    try:
        token = os.environ["STRATZ_TOKEN"]
        account_id = parse_account_id(os.environ["STRATZ_ACCOUNT_ID"])
        timeout = float(os.environ.get("STRATZ_TIMEOUT_SECONDS", "10"))
        asyncio.run(check(token, account_id, timeout, args.limit))
    except (KeyError, ValueError, ValidationError):
        print("Invalid or missing STRATZ configuration; check local token, account and timeout.")
        return 2
    except ProviderError as error:
        print(
            json.dumps(
                {
                    "source": error.source.value,
                    "error": error.code.value,
                    "retry_after_seconds": error.retry_after_seconds,
                }
            )
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
