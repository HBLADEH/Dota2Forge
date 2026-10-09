"""Opt-in match response diagnosis; report structure without participant identities."""

import argparse
import asyncio
import json
import os
import traceback

import httpx
from dota2forge_core import (
    DataMetadata,
    MatchAnalysis,
    MatchDetail,
    ProviderError,
    ValidationError,
    parse_match_id,
)
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure._analysis_mapping import stratz_analysis
from dota2forge_core.infrastructure._stratz_detail import match_detail, participant
from dota2forge_core.infrastructure.stratz import (
    MATCH_ANALYSIS_QUERY,
    MATCH_DETAIL_QUERY,
    StratzProvider,
)


async def diagnose(match_number: str) -> None:
    match_id = parse_match_id(match_number)
    report: dict[str, object] = {}
    async with httpx.AsyncClient(trust_env=False) as client:
        provider = StratzProvider(
            client,
            token=os.environ["STRATZ_TOKEN"],
            clock=SystemClock(),
            timeout_seconds=float(os.environ.get("STRATZ_TIMEOUT_SECONDS", "10")),
        )
        payload, fetched_at = await provider._http.request(
            MATCH_DETAIL_QUERY, {"matchId": match_id.value}
        )
        if isinstance(payload, dict):
            errors = payload.get("errors")
            report["graphql_error_count"] = len(errors) if isinstance(errors, list) else None
            data = payload.get("data")
            row = data.get("match") if isinstance(data, dict) else None
            report["match_returned"] = isinstance(row, dict)
            if isinstance(row, dict):
                report["match_field_types"] = {
                    key: type(value).__name__ for key, value in row.items()
                }
                players = row.get("players")
                if isinstance(players, list):
                    report["player_count"] = len(players)
                    failures = []
                    for index, player in enumerate(players):
                        try:
                            participant(player)
                        except (ProviderError, ValidationError) as error:
                            frames = traceback.extract_tb(error.__traceback__)
                            failures.append(
                                {
                                    "index": index,
                                    "exception": type(error).__name__,
                                    "location": [
                                        {"function": frame.name, "line": frame.lineno}
                                        for frame in frames
                                    ],
                                    "field_types": {
                                        key: type(value).__name__ for key, value in player.items()
                                    }
                                    if isinstance(player, dict)
                                    else None,
                                    "negative_numeric_fields": [
                                        key
                                        for key, value in player.items()
                                        if type(value) is int and value < 0
                                    ]
                                    if isinstance(player, dict)
                                    else None,
                                }
                            )
                    report["participant_failures"] = failures
        try:
            result = match_detail(payload, match_id, DataMetadata(provider.source, fetched_at))
            report["detail_valid"] = True
            if isinstance(result, MatchDetail):
                report["parse_state"] = result.parse_state.value
                report["missing_fields"] = result.missing_fields
        except ProviderError as error:
            report["detail_valid"] = False
            report["error"] = error.code.value
        analysis_payload, analysis_time = await provider._http.request(
            MATCH_ANALYSIS_QUERY, {"matchId": match_id.value}
        )
        if isinstance(analysis_payload, dict):
            analysis_data = analysis_payload.get("data")
            analysis_match = analysis_data.get("match") if isinstance(analysis_data, dict) else None
            if isinstance(analysis_match, dict) and isinstance(analysis_match.get("players"), list):
                times = [
                    event.get("time")
                    for player in analysis_match["players"]
                    if isinstance(player, dict) and isinstance(player.get("stats"), dict)
                    for event in player["stats"].get("itemPurchases") or []
                    if isinstance(event, dict)
                ]
                integers = [value for value in times if type(value) is int]
                report["purchase_count"] = len(times)
                report["negative_purchase_times"] = sum(value < 0 for value in integers)
                report["minimum_purchase_time"] = min(integers) if integers else None
        try:
            analysis = stratz_analysis(
                analysis_payload, match_id, DataMetadata(provider.source, analysis_time)
            )
            report["analysis_valid"] = True
            if isinstance(analysis, MatchAnalysis):
                purchases = [
                    event
                    for player in analysis.participants or ()
                    for event in player.purchases or ()
                ]
                report["mapped_purchase_count"] = len(purchases)
                report["mapped_negative_purchase_times"] = sum(
                    event.time_seconds < 0 for event in purchases
                )
        except ProviderError as error:
            report["analysis_valid"] = False
            report["analysis_error"] = error.code.value
    report["client_closed"] = client.is_closed
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("match_id")
    args = parser.parse_args()
    try:
        asyncio.run(diagnose(args.match_id))
    except ProviderError as error:
        print(
            json.dumps(
                {"error": error.code.value, "retry_after_seconds": error.retry_after_seconds}
            )
        )
        raise SystemExit(1) from None
    except (KeyError, ValueError, ValidationError):
        print("Invalid local configuration or match ID")
        raise SystemExit(2) from None
