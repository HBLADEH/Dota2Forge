# /// script
# requires-python = ">=3.12"
# dependencies = ["fonttools==4.60.1"]
# ///
"""Mechanical local-font cmap and public hero-label resource generation."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "packages/dota2forge-renderer/src/dota2forge_renderer/assets/v1"


def main() -> None:
    with TTFont(ASSETS / "NotoSansCJKsc-Regular.otf") as font:
        glyphs = sorted(font.getBestCmap())
    (ASSETS / "glyphs.json").write_text(json.dumps(glyphs) + "\n", "utf-8")
    url = "https://www.dota2.com/datafeed/herolist?language=schinese"
    with urlopen(url, timeout=15) as response:
        payload = response.read()
    heroes = json.loads(payload)["result"]["data"]["heroes"]
    rows = [{key: hero[key] for key in ("id", "name", "name_loc")} for hero in heroes]
    result = {
        "version": 1,
        "source": url,
        "fetched_at": datetime.now(UTC).isoformat(),
        "response_sha256": hashlib.sha256(payload).hexdigest(),
        "heroes": sorted(rows, key=lambda hero: hero["id"]),
    }
    (ASSETS / "heroes.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    print(f"Prepared {len(glyphs)} font glyphs and {len(rows)} public hero labels")


if __name__ == "__main__":
    main()
