"""Fixed public sources and explicit identity mapping; no guessed art or credentials."""

import hashlib
import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from .models import AssetError

CDN = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react"
MIRROR = "https://raw.githubusercontent.com/odota/web/master/public/assets/images/dota2"
RIGHTS = (
    "Dota 2 artwork © Valve Corporation. All rights reserved; no redistribution license claimed."
)
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
RANK_NAMES = ("未定级", "先锋", "卫士", "中军", "统帅", "传奇", "万古流芳", "超凡入圣", "冠绝一世")
STATIC_ART = {
    "ranks": {
        str(n): (f"{MIRROR}/rank_icons/rank_icon_{n}.png", name)
        for n, name in enumerate(RANK_NAMES)
    },
    "rank_stars": {
        str(n): (f"{MIRROR}/rank_icons/rank_star_{n}.png", f"{n} 星") for n in range(1, 6)
    },
    "ui": {"gold": (f"{MIRROR}/gold.png", "金币")},
}


def validate_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
        valid = (
            parsed.scheme == "https"
            and parsed.port in (None, 443)
            and parsed.username is None
            and parsed.password is None
            and not parsed.fragment
        )
    except ValueError:
        raise AssetError("source") from None
    if not valid:
        raise AssetError("source")
    if parsed.hostname == "www.dota2.com":
        valid = url in {feed[0] for feed in FEEDS.values()}
    elif parsed.hostname in {
        "cdn.cloudflare.steamstatic.com",
        "cdn.steamstatic.com",
        "shared.fastly.steamstatic.com",
    }:
        valid = (
            bool(
                re.fullmatch(
                    r"/apps/dota2/images/dota_react/(heroes|items)/[a-z0-9_]+\.png", parsed.path
                )
            )
            and not parsed.query
        )
    elif parsed.hostname == "raw.githubusercontent.com":
        valid = url in {v[0] for group in STATIC_ART.values() for v in group.values()}
    else:
        valid = False
    if not valid:
        raise AssetError("source")


def catalog(data: bytes, key: str, prefix: str) -> list[dict[str, Any]]:
    try:
        raw = json.loads(data)
        rows = raw["result"]["data"][key]
    except (ValueError, KeyError, TypeError):
        raise AssetError("catalog") from None
    if not isinstance(rows, list) or not 1 <= len(rows) <= 2048:
        raise AssetError("catalog")
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
            raise AssetError("catalog")
        seen.add(row["id"])
    return rows


def entry(kind: str, key: str, url: str, name: str, now: datetime) -> dict[str, Any]:
    row: dict[str, Any] = {
        "name_loc": name,
        "source": url,
        "fetched_at": now.isoformat(),
        "rights": RIGHTS,
    }
    if kind in STATIC_ART:
        row |= {"source_kind": "valve_game_art_mirror", "mirror": "OpenDota"}
    return row


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
