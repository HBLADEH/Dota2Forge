"""Bounded implementation acceptance probe; save only public scope/count/status."""

import asyncio
import json
import os
from pathlib import Path

import httpx
from dota2forge_core import HeroFeatureService, MetaRequest, ProviderError, RankBracket
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure.hero_catalog import load_hero_catalog
from dota2forge_core.infrastructure.stratz import StratzProvider


async def main() -> None:
    report = {}
    async with httpx.AsyncClient(trust_env=False) as client:
        provider = StratzProvider(client, token=os.environ["STRATZ_TOKEN"], clock=SystemClock())
        service = HeroFeatureService(provider, provider, load_hero_catalog())
        try:
            meta = await service.get_meta(MetaRequest(position=3, rank=RankBracket.LEGEND))
            report["meta"] = {
                "patch": meta.snapshot.patch.name,
                "bucket_count": len(meta.snapshot.buckets),
                "entry_count": len(meta.entries),
                "notes": meta.snapshot.notes,
            }
        except ProviderError as error:
            report["meta"] = {"error": error.code.value}
        try:
            guide = await service.get_guide("斧王", 3)
            report["guide"] = {
                "module_errors": guide.module_errors,
                "sample_count": len(guide.samples),
                "samples": [
                    {
                        "position_valid": s.player.position == "POSITION_3",
                        "upgrades": len(s.upgrades or ()),
                        "purchases": len(s.purchases or ()),
                        "label_error": s.label_error,
                    }
                    for s in guide.samples
                ],
            }
        except ProviderError as error:
            report["guide"] = {"error": error.code.value}
        await provider.close()
    report["client_closed"] = client.is_closed
    Path(__file__).with_name("implemented.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
