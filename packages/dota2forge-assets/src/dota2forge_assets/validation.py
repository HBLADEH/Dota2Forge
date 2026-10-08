"""Verify local manifests and bounded PNGs independently of drawing and platforms."""

import hashlib
import io
import json
import re
from pathlib import Path
from typing import Any

from PIL import Image

from .models import KINDS, AssetError, AssetLimits

PATTERNS = {
    "heroes": r"[1-9][0-9]{0,9}",
    "items": r"[1-9][0-9]{0,9}",
    "ranks": r"[0-8]",
    "rank_stars": r"[1-5]",
    "ui": "gold",
    "decor": "header",
}


def safe_path(root: Path, relative: str) -> Path:
    path = root / relative
    if root.is_symlink() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise AssetError("path")
    for parent in path.parents:
        if parent == root:
            break
        if parent.is_symlink():
            raise AssetError("path")
    return path


def png_size(data: bytes, limits: AssetLimits) -> tuple[int, int]:
    if len(data) > limits.response_bytes:
        raise AssetError("size")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if (
                image.format != "PNG"
                or not 1 <= image.width * image.height <= limits.pixels
                or max(image.size) > 2048
            ):
                raise AssetError("png")
            image.verify()
            return image.size
    except (OSError, ValueError, Image.DecompressionBombError):
        raise AssetError("png") from None


def read_json(path: Path, limit: int) -> dict[str, Any]:
    if path.is_symlink() or path.stat().st_size > limit:
        raise AssetError("manifest")
    try:
        raw = json.loads(path.read_bytes())
    except (ValueError, UnicodeError):
        raise AssetError("manifest") from None
    if not isinstance(raw, dict):
        raise AssetError("manifest")
    return raw


def validate_entry(root: Path, kind: str, key: str, row: Any, limits: AssetLimits) -> None:
    if (
        re.fullmatch(PATTERNS[kind], key) is None
        or not isinstance(row, dict)
        or not isinstance(row.get("name_loc"), str)
        or not isinstance(row.get("source"), str)
        or row.get("status") not in ("available", "missing")
    ):
        raise AssetError("manifest")
    if row["status"] == "missing":
        if row.get("file") is not None or row.get("sha256") is not None:
            raise AssetError("manifest")
        return
    digest = row.get("sha256")
    if (
        row.get("file") != f"{kind}/{key}.png"
        or not isinstance(digest, str)
        or re.fullmatch(r"[0-9a-f]{64}", digest) is None
    ):
        raise AssetError("manifest")
    path = safe_path(root, row["file"])
    if path.stat().st_size > limits.response_bytes:
        raise AssetError("size")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise AssetError("digest")
    png_size(data, limits)


def validate_manifest(root: Path, limits: AssetLimits) -> dict[str, Any]:
    raw = read_json(safe_path(root, "manifest.json"), limits.manifest_bytes)
    if type(raw.get("version")) is not int or raw["version"] != 1:
        raise AssetError("manifest")
    for kind in KINDS:
        rows = raw.get(kind, {})
        if not isinstance(rows, dict) or len(rows) > 2048:
            raise AssetError("manifest")
        for key, row in rows.items():
            if not isinstance(key, str):
                raise AssetError("manifest")
            validate_entry(root, kind, key, row, limits)
    return raw
