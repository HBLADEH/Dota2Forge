"""Probe a user-selected match without persisting IDs, names or source response data."""

import argparse
import asyncio
import json
import os
from pathlib import Path

import httpx
from dota2forge_core import ProviderError, ReviewService, evidence_data
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure.hero_catalog import load_hero_catalog
from dota2forge_core.infrastructure.stratz import StratzProvider


async def check(match_id, hero):
    async with httpx.AsyncClient(trust_env=False) as client:
        provider = StratzProvider(client, token=os.environ["STRATZ_TOKEN"], clock=SystemClock())
        try:
            evidence = await ReviewService(provider, provider, load_hero_catalog()).get_context(
                match_id, hero
            )
            facts = evidence_data(evidence)
            report = {
                "target_selected": evidence.target_slot is not None,
                "players_in_perspective": len(facts["players"]),
                "analysis_error": evidence.analysis_error,
                "economic_series": len(facts["economic_series"]),
                "purchase_records": None if facts["purchases"] is None else len(facts["purchases"]),
                "team_series": len(facts["team_series"]),
                "identity_in_serialized_data": any(
                    key in json.dumps(facts)
                    for key in ("account_id", "steamAccountId", "display_name")
                ),
            }
        except ProviderError as error:
            report = {"error": error.code.value}
        await provider.close()
    Path(__file__).with_name("review-shape.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("match_id")
    parser.add_argument("hero")
    args = parser.parse_args()
    asyncio.run(check(args.match_id, args.hero))
