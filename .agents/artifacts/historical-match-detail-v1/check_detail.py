"""Opt-in read-only check for the authorized local account; no raw data is printed."""

import argparse
import asyncio
import json
import os

import httpx
from dota2forge_core import (
    MatchDetail,
    MatchDetailService,
    ProviderError,
    ProviderErrorCode,
    ValidationError,
    parse_account_id,
)
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure._stratz_http import failure
from dota2forge_core.infrastructure._stratz_mapping import field, integer, object_value, player_data
from dota2forge_core.infrastructure.stratz import StratzProvider

DISCOVER = """
query Dota2ForgeHistoryCheck($accountId: Long!, $skip: Int!) {
  player(steamAccountId: $accountId) {
    steamAccountId
    matches(request: {take: 1, skip: $skip, orderBy: DESC}) { id }
  }
}
"""


async def check(offset: int) -> None:
    account = parse_account_id(os.environ["STRATZ_ACCOUNT_ID"])
    async with httpx.AsyncClient(trust_env=False) as client:
        provider = StratzProvider(
            client,
            token=os.environ["STRATZ_TOKEN"],
            clock=SystemClock(),
            timeout_seconds=float(os.environ.get("STRATZ_TIMEOUT_SECONDS", "10")),
        )
        # Manual diagnostic only: discovery reuses the same private HTTP quota state.
        payload, _ = await provider._http.request(
            DISCOVER, {"accountId": account.value, "skip": offset}
        )
        rows = field(player_data(payload, account), "matches")
        if not isinstance(rows, list) or len(rows) != 1:
            raise failure(ProviderErrorCode.INVALID_RESPONSE)
        match_id = integer(field(object_value(rows[0]), "id"), minimum=1)
        result = await MatchDetailService(provider).get_match_detail(match_id)
        report: dict[str, object] = {
            "source": result.metadata.source.value,
            "discovery_offset": offset,
            "direct_id_lookup": True,
            "detail_available": isinstance(result, MatchDetail),
            "observed_at_unknown": result.metadata.observed_at is None,
            "patch_name_unknown": result.metadata.patch is None,
        }
        if isinstance(result, MatchDetail):
            report.update(
                {
                    "players": None if result.players is None else len(result.players),
                    "account_participates": result.participant(account) is not None,
                    "missing_fields": result.missing_fields,
                    "participant_missing_fields": sorted(
                        {name for player in result.players or () for name in player.missing_fields}
                    ),
                    "has_stats": result.has_stats,
                    "has_parsed_time": result.parsed_at is not None,
                    "anonymous_names_suppressed": all(
                        player.display_name is None
                        for player in result.players or ()
                        if player.account_id is None
                    ),
                }
            )
    report["client_closed"] = client.is_closed
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offset", type=int, default=100, choices=range(1001))
    args = parser.parse_args()
    try:
        asyncio.run(check(args.offset))
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
        raise SystemExit(1) from None
    except (KeyError, ValueError, ValidationError):
        print("Invalid local configuration or unavailable diagnostic result")
        raise SystemExit(2) from None
