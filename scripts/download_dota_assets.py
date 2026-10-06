"""Explicit Valve art download, independent of Provider queries and offline checks."""

import argparse
import hashlib
import io
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from PIL import Image

CDN = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react"
# Valve game art mirrored by OpenDota; these are not Valve-hosted URLs.
MIRROR = "https://raw.githubusercontent.com/odota/web/master/public/assets/images/dota2"
RANK_NAMES = ("未定级", "先锋", "卫士", "中军", "统帅", "传奇", "万古流芳", "超凡入圣", "冠绝一世")
STATIC_ART = {
    "ranks": {
        str(tier): (f"{MIRROR}/rank_icons/rank_icon_{tier}.png", name)
        for tier, name in enumerate(RANK_NAMES)
    },
    "rank_stars": {
        str(stars): (f"{MIRROR}/rank_icons/rank_star_{stars}.png", f"{stars} 星")
        for stars in range(1, 6)
    },
    "ui": {"gold": (f"{MIRROR}/gold.png", "金币")},
}
FEEDS = {
    "heroes": (
        "https://www.dota2.com/datafeed/herolist?language=schinese",
        "heroes",
        "npc_dota_hero_",
    ),
    "items": (
        "https://www.dota2.com/datafeed/itemlist?language=schinese",
        "itemabilities",
        "item_",
    ),
}
MAX_DOWNLOAD = 4 * 1024 * 1024
RIGHTS = (
    "Dota 2 artwork © Valve Corporation. All rights reserved; no redistribution license claimed."
)


def fetch(url: str) -> bytes:
    with urlopen(
        Request(url, headers={"User-Agent": "Dota2Forge asset downloader/1"}), timeout=20
    ) as response:
        data = response.read(MAX_DOWNLOAD + 1)
    if not isinstance(data, bytes) or len(data) > MAX_DOWNLOAD:
        raise ValueError("Asset response exceeds limit")
    return data


def png_size(data: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(data)) as image:
        if image.format != "PNG" or not 1 <= image.width * image.height <= 2048 * 2048:
            raise ValueError("Expected bounded PNG art")
        image.verify()
        return image.size


def catalog(data: bytes, key: str, prefix: str) -> list[dict[str, Any]]:
    raw = json.loads(data)
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("result"), dict)
        or not isinstance(raw["result"].get("data"), dict)
    ):
        raise ValueError("Invalid Valve art catalog")
    rows = raw["result"]["data"].get(key)
    if not isinstance(rows, list) or not 1 <= len(rows) <= 2048:
        raise ValueError("Invalid Valve art catalog")
    seen: set[int] = set()
    for row in rows:
        if (
            not isinstance(row, dict)
            or type(row.get("id")) is not int
            or not 1 <= row["id"] <= 9999999999
            or row["id"] in seen
            or not isinstance(row.get("name"), str)
            or re.fullmatch(re.escape(prefix) + r"[a-z0-9_]+", row["name"]) is None
            or not isinstance(row.get("name_loc"), str)
        ):
            raise ValueError("Invalid Valve art identity")
        seen.add(row["id"])
    return rows


def download_entry(root: Path, kind: str, row: dict[str, Any], prefix: str) -> dict[str, Any]:
    identifier = str(row["id"])
    url = f"{CDN}/{kind}/{row['name'].removeprefix(prefix)}.png"
    return download_art(root, kind, identifier, url, row["name_loc"]) | {"name": row["name"]}


def download_art(root: Path, kind: str, identifier: str, url: str, name: str) -> dict[str, Any]:
    entry = {
        "name_loc": name,
        "source": url,
        "fetched_at": datetime.now(UTC).isoformat(),
        "rights": RIGHTS,
    }
    if kind in STATIC_ART:
        entry |= {"source_kind": "valve_game_art_mirror", "mirror": "OpenDota"}
    try:
        data = fetch(url)
    except HTTPError as error:
        if error.code != 404:
            raise
        return entry | {"status": "missing", "reason": "http_404", "file": None, "sha256": None}
    width, height = png_size(data)
    filename = f"{kind}/{identifier}.png"
    destination = root / filename
    temporary = destination.with_suffix(".part")
    temporary.write_bytes(data)
    temporary.replace(destination)
    return entry | {
        "status": "available",
        "file": filename,
        "sha256": hashlib.sha256(data).hexdigest(),
        "width": width,
        "height": height,
    }


def download_pack(root: Path, *, only_ui: bool = False) -> dict[str, Any]:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    previous = root / "manifest.json"
    existing = json.loads(previous.read_bytes()) if previous.exists() else {}
    if not isinstance(existing, dict) or (
        existing and (type(existing.get("version")) is not int or existing["version"] != 1)
    ):
        raise ValueError("Invalid existing art manifest")
    manifest: dict[str, Any] = existing | {
        "version": 1,
        "fetched_at": datetime.now(UTC).isoformat(),
        "rights": RIGHTS,
    }
    manifest.setdefault("catalogs", {})
    manifest.setdefault("decor", {})
    selected = []
    with TemporaryDirectory(prefix=".download-", dir=root) as directory:
        stage = Path(directory)
        for kind, (url, key, prefix) in ({} if only_ui else FEEDS).items():
            data = fetch(url)
            rows = catalog(data, key, prefix)
            manifest["catalogs"][kind] = {
                "source": url,
                "response_sha256": hashlib.sha256(data).hexdigest(),
            }
            (stage / kind).mkdir()
            with ThreadPoolExecutor(max_workers=6) as pool:
                entries = list(pool.map(partial(download_entry, stage, kind, prefix=prefix), rows))
            manifest[kind] = {
                str(row["id"]): entry for row, entry in zip(rows, entries, strict=True)
            }
            selected.append(kind)
        for kind, resources in STATIC_ART.items():
            (stage / kind).mkdir()
            with ThreadPoolExecutor(max_workers=6) as pool:
                entries = list(
                    pool.map(
                        lambda key, kind=kind, resources=resources: download_art(
                            stage, kind, key, *resources[key]
                        ),
                        resources,
                    )
                )
            manifest[kind] = dict(zip(resources, entries, strict=True))
            selected.append(kind)
        for kind in selected:
            (root / kind).mkdir(exist_ok=True)
            for entry in manifest[kind].values():
                if entry["file"] is not None:
                    (stage / entry["file"]).replace(root / entry["file"])
    temporary = root / "manifest.json.part"
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(previous)
    (root / "RIGHTS.txt").write_text(RIGHTS + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True, help="Local art directory, outside wheels"
    )
    parser.add_argument(
        "--only-ui",
        action="store_true",
        help="Update rank, stars and gold; preserve heroes/items/decor",
    )
    args = parser.parse_args(argv)
    try:
        manifest = download_pack(args.output, only_ui=args.only_ui)
    except (OSError, ValueError, KeyError) as error:
        print(
            f"Art download failed ({type(error).__name__}); pack update is not confirmed complete."
        )
        return 1
    for kind in (*(() if args.only_ui else FEEDS), *STATIC_ART):
        rows = manifest[kind].values()
        available = sum(row["status"] == "available" for row in rows)
        print(f"{kind}: {available} available, {len(manifest[kind]) - available} missing")
    print(f"Local art: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
