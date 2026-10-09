"""Opt-in live report preview with all participant identities removed before saving."""

import argparse
import asyncio
import ipaddress
import json
import os
from dataclasses import replace
from pathlib import Path

import httpx
from dota2forge_core import MatchAnalysis, MatchDetail, MatchId, MatchReport
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure._subscription_codec import (
    analysis_dict,
    decode_analysis,
    decode_detail,
    detail_dict,
)
from dota2forge_core.infrastructure.stratz import StratzProvider
from dota2forge_renderer import MatchReportCard, PillowRenderer
from dota2forge_renderer.reporting import match_report_text

HERE = Path(__file__).resolve().parent


class DiagnosticTransport(httpx.AsyncHTTPTransport):
    def __init__(self, connect_ip=None):
        super().__init__()
        self.connect_ip = connect_ip

    async def handle_async_request(self, request):
        try:
            if self.connect_ip is not None:
                assert request.url.host == "api.stratz.com"
                request.extensions["sni_hostname"] = "api.stratz.com"
                request.url = request.url.copy_with(host=self.connect_ip)
            response = await super().handle_async_request(request)
            print(json.dumps({"http_status": response.status_code}))
            return response
        except httpx.RequestError as error:
            print(json.dumps({"transport_error": type(error).__name__}))
            raise


async def main(connect_ip=None, cached=False):
    target = MatchId(9035146588)
    if cached:
        stored = json.loads(HERE.joinpath("sanitized-observation.json").read_text("utf-8"))
        detail = decode_detail(stored["detail"])
        analysis = decode_analysis(stored["analysis"])
        client_closed = True
    else:
        async with httpx.AsyncClient(
            transport=DiagnosticTransport(connect_ip), trust_env=False
        ) as client:
            provider = StratzProvider(client, token=os.environ["STRATZ_TOKEN"], clock=SystemClock())
            detail = await provider.get_match_detail(target)
            analysis = await provider.get_match_analysis(target)
        client_closed = client.is_closed
    assert isinstance(detail, MatchDetail) and isinstance(analysis, MatchAnalysis)
    detail = replace(
        detail,
        players=tuple(
            replace(player, account_id=None, display_name=None, is_anonymous=True)
            for player in detail.players or ()
        ),
    )
    analysis = replace(
        analysis,
        participants=tuple(
            replace(player, account_id=None) for player in analysis.participants or ()
        ),
    )
    if not cached:
        HERE.joinpath("sanitized-observation.json").write_text(
            json.dumps(
                {"detail": detail_dict(detail), "analysis": analysis_dict(analysis)}, indent=2
            )
            + "\n",
            encoding="utf-8",
        )
    report = MatchReport(target, detail.metadata, None, None, detail, analysis)
    renderer = PillowRenderer(
        illustration_path=Path("D:/workstation/Dota2Forge/.dota2forge-assets")
    )
    sizes = []
    try:
        pages = match_report_text(report)
        for page in range(1, len(pages) + 1):
            artifact = renderer.render(MatchReportCard(report, page))
            HERE.joinpath(f"report-{page}.png").write_bytes(artifact.data)
            sizes.append(
                {
                    "page": page,
                    "width": artifact.width,
                    "height": artifact.height,
                    "bytes": len(artifact.data),
                }
            )
        HERE.joinpath("preview.txt").write_text("\n\n".join(pages), encoding="utf-8")
    finally:
        renderer.close()
    evidence = {
        "checked_on": "2026-10-09",
        "match_id": target.value,
        "client_closed": client_closed,
        "imp_available": len(report.imp_ranking),
        "imp_values": [player.imp for player in detail.players or ()],
        "team_series": [
            {
                "semantic": series.semantic.value,
                "points": len(series.values),
                "start_seconds": series.start_seconds,
            }
            for series in analysis.team_metrics
        ],
        "identity_removed": True,
        "pages": sizes,
    }
    HERE.joinpath("live-preview.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connect-ip", type=lambda value: str(ipaddress.ip_address(value)))
    parser.add_argument("--cached", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.connect_ip, args.cached))
