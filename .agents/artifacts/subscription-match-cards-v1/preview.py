"""Render synthetic subscription cards; no network, live identities or subscription DB."""

import json
import runpy
from dataclasses import replace
from pathlib import Path

from dota2forge_core import MatchAnalysis
from dota2forge_renderer import (
    PillowRenderer,
    subscription_event_cards,
    subscription_event_text_pages,
)
from PIL import Image


def main():
    output = Path(__file__).resolve().parent
    root = output.parents[2]
    fixture = runpy.run_path(str(root / "tests/renderer/test_subscription_cards.py"))[
        "synthetic_subscription_event"
    ]
    event = fixture(imp=False)
    report = replace(
        event.payload,
        analysis=MatchAnalysis(event.payload.match_id, event.payload.metadata, ()),
    )
    event = replace(event, payload=report)
    renderer = PillowRenderer()
    results = []
    try:
        for card in subscription_event_cards(event):
            artifact = renderer.render(card)
            filename = f"report-{card.page}.png"
            (output / filename).write_bytes(artifact.data)
            results.append(
                {
                    "file": filename,
                    "width": artifact.width,
                    "height": artifact.height,
                    "bytes": len(artifact.data),
                    "text_boxes": len(renderer.last_layout),
                    "layout_bounds_passed": True,
                }
            )
    finally:
        renderer.close()
    with Image.open(output / "report-1.png") as overview:
        overview.resize((780, round(overview.height * 780 / overview.width))).save(
            output / "overview-780.png"
        )
    pages = subscription_event_text_pages(event)
    fallback = "\n\n---\n\n".join(pages)
    (output / "fallback.txt").write_text(
        "\n".join(line.rstrip() for line in fallback.splitlines()) + "\n", encoding="utf-8"
    )
    (output / "qa.json").write_text(
        json.dumps(
            {
                "synthetic_only": True,
                "cards": results,
                "text_page_lengths": [len(page) for page in pages],
                "text_limit": 1400,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"cards": results, "text_pages": len(pages)}, indent=2))


if __name__ == "__main__":
    main()
