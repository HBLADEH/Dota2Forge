"""Versioned, bounded local art; downloading belongs to an explicit external tool."""

import hashlib
import io
import json
import re
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .cards import RenderError

MAX_ASSET_BYTES = 8 * 1024 * 1024
MAX_ASSET_PIXELS = 2048 * 2048
MAX_CACHED_IMAGES = 48
KEY_PATTERNS = {
    "heroes": r"[1-9][0-9]{0,9}",
    "items": r"[1-9][0-9]{0,9}",
    "decor": r"header",
    "ranks": r"[0-8]",
    "rank_stars": r"[1-5]",
    "ui": r"gold",
}


@dataclass(frozen=True, slots=True)
class _Entry:
    file: str | None
    sha256: str | None
    name: str


class Illustrations:
    def __init__(self, path: Path | None) -> None:
        self.path = path
        self._loaded = False
        self._entries: dict[tuple[str, str], _Entry] = {}
        self._images: OrderedDict[tuple[str, str], Image.Image] = OrderedDict()

    def load(self) -> None:
        if self._loaded:
            return
        entries: dict[tuple[str, str], _Entry] = {}
        if self.path is not None:
            manifest = self.path / "manifest.json"
            if manifest.stat().st_size > 1024 * 1024:
                raise RenderError()
            raw = json.loads(manifest.read_bytes())
            if (
                not isinstance(raw, dict)
                or type(raw.get("version")) is not int
                or raw["version"] != 1
            ):
                raise RenderError()
            for kind, pattern in KEY_PATTERNS.items():
                rows = raw.get(kind, {})
                if not isinstance(rows, dict) or len(rows) > 2048:
                    raise RenderError()
                for key, row in rows.items():
                    if (
                        not isinstance(key, str)
                        or re.fullmatch(pattern, key) is None
                        or not isinstance(row, dict)
                        or not isinstance(row.get("name_loc"), str)
                        or not isinstance(row.get("source"), str)
                        or row.get("status") not in ("available", "missing")
                    ):
                        raise RenderError()
                    filename, digest = row.get("file"), row.get("sha256")
                    if row["status"] == "available":
                        if (
                            filename != f"{kind}/{key}.png"
                            or not isinstance(digest, str)
                            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                        ):
                            raise RenderError()
                    elif filename is not None or digest is not None:
                        raise RenderError()
                    entries[kind, key] = _Entry(filename, digest, row["name_loc"])
        self._entries = entries
        self._loaded = True

    def name(self, kind: str, identifier: int | None) -> str | None:
        entry = self._entries.get((kind, str(identifier)))
        return entry.name or None if entry is not None else None

    def image(self, kind: str, identifier: int | str | None) -> Image.Image | None:
        key = (kind, str(identifier))
        if key in self._images:
            self._images.move_to_end(key)
            return self._images[key]
        entry = self._entries.get(key)
        if entry is None or entry.file is None or self.path is None:
            return None
        root = self.path.resolve()
        path = (root / entry.file).resolve()
        if not path.is_relative_to(root):
            raise RenderError()
        try:
            if path.stat().st_size > MAX_ASSET_BYTES:
                raise RenderError()
            data = path.read_bytes()
        except FileNotFoundError:
            return None
        if hashlib.sha256(data).hexdigest() != entry.sha256:
            raise RenderError()
        with io.BytesIO(data) as stream, Image.open(stream) as original:
            if (
                original.format != "PNG"
                or original.width < 1
                or original.height < 1
                or original.width * original.height > MAX_ASSET_PIXELS
            ):
                raise RenderError()
            original.load()
            decoded = original.convert("RGBA")
            decoded.thumbnail((1024, 1024) if kind == "decor" else (256, 256))
        self._images[key] = decoded
        if len(self._images) > MAX_CACHED_IMAGES:
            self._images.popitem(last=False)[1].close()
        return decoded

    def close(self) -> None:
        for image in self._images.values():
            image.close()
        self._images.clear()
        self._entries.clear()
        self._loaded = False
