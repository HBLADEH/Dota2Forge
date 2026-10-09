"""Explicit legacy pack download; selected resources publish only after all requests succeed."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import httpx

from .http import Fetcher
from .manager import make_client
from .models import AssetError, AssetLimits
from .sources import CDN, FEEDS, RIGHTS, STATIC_ART, catalog, digest, entry
from .validation import png_size, read_json, safe_path


async def download_pack(
    root: Path, *, only_ui: bool = False, client: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    existing = (
        read_json(safe_path(root, "manifest.json"), AssetLimits().manifest_bytes)
        if (root / "manifest.json").exists()
        else {}
    )
    if not isinstance(existing, dict) or (
        existing and (type(existing.get("version")) is not int or existing["version"] != 1)
    ):
        raise AssetError("manifest")
    manifest = existing | {
        "version": 1,
        "rights": RIGHTS,
        "fetched_at": datetime.now(UTC).isoformat(),
    }
    manifest.setdefault("catalogs", {})
    manifest.setdefault("decor", {})
    owned = client is None
    client = client or make_client()
    limits = AssetLimits()
    fetcher = Fetcher(client, limits, lambda: datetime.now(UTC), asyncio.sleep)
    jobs: list[tuple[str, str, str, str, str | None]] = []
    selected = list(STATIC_ART)
    try:
        async with asyncio.timeout(limits.job_seconds):
            for kind, (url, key, prefix) in ({} if only_ui else FEEDS).items():
                data = await fetcher.fetch(url)
                rows = catalog(data, key, prefix)
                manifest["catalogs"][kind] = {"source": url, "response_sha256": digest(data)}
                jobs.extend(
                    (
                        kind,
                        str(r["id"]),
                        f"{CDN}/{kind}/{r['name'].removeprefix(prefix)}.png",
                        r["name_loc"],
                        r["name"],
                    )
                    for r in rows
                )
                selected.append(kind)
            jobs.extend(
                (kind, key, url, title, None)
                for kind, group in STATIC_ART.items()
                for key, (url, title) in group.items()
            )
            for kind in selected:
                manifest[kind] = {}
            with TemporaryDirectory(prefix=".download-", dir=root) as directory:
                stage = Path(directory)
                slots = asyncio.Semaphore(limits.workers)

                async def download(job: tuple[str, str, str, str, str | None]) -> None:
                    async with slots:
                        kind, key, url, title, internal = job
                        row = entry(kind, key, url, title, datetime.now(UTC))
                        if internal:
                            row["name"] = internal
                        try:
                            data = await fetcher.fetch(url)
                        except AssetError as error:
                            if error.code != "http_404":
                                raise
                            row |= {
                                "status": "missing",
                                "reason": "http_404",
                                "file": None,
                                "sha256": None,
                            }
                        else:
                            width, height = png_size(data, limits)
                            filename = f"{kind}/{key}.png"
                            (stage / kind).mkdir(exist_ok=True)
                            (stage / filename).write_bytes(data)
                            row |= {
                                "status": "available",
                                "file": filename,
                                "sha256": digest(data),
                                "width": width,
                                "height": height,
                            }
                        manifest[kind][key] = row

                tasks = [asyncio.create_task(download(job)) for job in jobs]
                try:
                    await asyncio.gather(*tasks)
                finally:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                encoded = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
                if len(encoded) > limits.manifest_bytes:
                    raise AssetError("manifest")
                # Validate every destination before replacing any existing image.
                for kind in selected:
                    safe_path(root, kind)
                    for row in manifest[kind].values():
                        if row["file"] is not None:
                            safe_path(root, row["file"])
                for name in ("manifest.json", "manifest.json.part", "RIGHTS.txt"):
                    safe_path(root, name)
                for kind in selected:
                    safe_path(root, kind).mkdir(exist_ok=True)
                    for row in manifest[kind].values():
                        if row["file"] is not None:
                            (stage / row["file"]).replace(safe_path(root, row["file"]))
            temporary = safe_path(root, "manifest.json.part")
            temporary.write_text(encoded.decode(), encoding="utf-8")
            temporary.replace(safe_path(root, "manifest.json"))
            safe_path(root, "RIGHTS.txt").write_text(RIGHTS + "\n", encoding="utf-8")
            return manifest
    finally:
        if owned:
            await client.aclose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--only-ui", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest = asyncio.run(download_pack(args.output, only_ui=args.only_ui))
    except (OSError, ValueError, AssetError, TimeoutError) as error:
        print(
            f"Art download failed ({type(error).__name__}); pack update is not confirmed complete."
        )
        return 1
    for kind in (*(() if args.only_ui else FEEDS), *STATIC_ART):
        available = sum(row["status"] == "available" for row in manifest[kind].values())
        print(f"{kind}: {available} available, {len(manifest[kind]) - available} missing")
    print(f"Local art: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
