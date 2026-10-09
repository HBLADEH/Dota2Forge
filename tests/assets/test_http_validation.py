import asyncio
import io
import json
from datetime import timedelta

import httpx
import pytest
from dota2forge_assets import AssetError, AssetLimits
from dota2forge_assets.http import Fetcher
from dota2forge_assets.models import aware_time
from dota2forge_assets.sources import CDN, FEEDS, catalog, validate_url
from dota2forge_assets.validation import png_size, read_json, safe_path, validate_manifest
from PIL import Image


@pytest.mark.parametrize(
    "url",
    [
        "http://www.dota2.com/datafeed/herolist?language=schinese",
        "https://user:secret@www.dota2.com/datafeed/herolist?language=schinese",
        "https://www.dota2.com/datafeed/herolist?language=en",
        "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/../secret.png",
        "https://cdn.cloudflare.steamstatic.com:123/heroes/axe.png",
        "https://raw.githubusercontent.com/unknown/images/a.png",
        "https://example.invalid/axe.png",
        "https://[broken",
    ],
)
def test_unapproved_source_is_rejected_without_requests(url):
    with pytest.raises(AssetError, match="source"):
        validate_url(url)


@pytest.mark.parametrize(
    "code,attempts,error",
    [(404, 1, "http_404"), (403, 1, "http_error"), (500, 3, "http_5xx"), (429, 3, "http_429")],
)
def test_retry_classification_is_bounded(code, attempts, error, backend, run_async):
    async def run():
        calls, sleeps = [], []

        async def sleep(delay):
            sleeps.append(delay)

        def request(req):
            calls.append(req)
            return httpx.Response(code, headers={"Retry-After": "5"})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(request),
            headers={"Authorization": "secret"},
            auth=("private", "secret"),
        ) as client:
            fetcher = Fetcher(client, AssetLimits(), lambda: backend.now, sleep)
            with pytest.raises(AssetError, match=error):
                await fetcher.fetch(FEEDS["heroes"][0])
        assert len(calls) == attempts
        assert all("authorization" not in req.headers for req in calls)
        assert sleeps == ([5, 5] if code == 429 else [1, 3] if code == 500 else [])

    run_async(run())


def test_redirect_allowlist_and_absolute_stream_deadline(backend, run_async):
    async def run():
        calls = []

        def redirect(req):
            calls.append(str(req.url))
            return httpx.Response(302, headers={"Location": "https://example.invalid/private"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(redirect)) as client:
            fetcher = Fetcher(client, AssetLimits(retries=0), lambda: backend.now, asyncio.sleep)
            with pytest.raises(AssetError, match="source"):
                await fetcher.fetch(f"{CDN}/heroes/axe.png")
        assert len(calls) == 1

        class Slow(httpx.AsyncByteStream):
            closed = False

            async def __aiter__(self):
                yield b"x"
                await asyncio.sleep(1)
                yield b"y"

            async def aclose(self):
                self.closed = True

        stream = Slow()
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, stream=stream))
        ) as client:
            fetcher = Fetcher(
                client,
                AssetLimits(retries=0, request_seconds=0.02),
                lambda: backend.now,
                asyncio.sleep,
            )
            with pytest.raises(AssetError, match="timeout"):
                await fetcher.fetch(f"{CDN}/heroes/axe.png")
        assert stream.closed

    run_async(run())


def test_success_redirect_size_limits_and_retry_after_date(backend, run_async):
    async def run():
        count = 0

        def request(req):
            nonlocal count
            count += 1
            if count == 1:
                return httpx.Response(
                    307, headers={"Location": "/apps/dota2/images/dota_react/heroes/axe.png"}
                )
            return httpx.Response(200, content=b"12345")

        async with httpx.AsyncClient(transport=httpx.MockTransport(request)) as client:
            fetcher = Fetcher(
                client, AssetLimits(retries=0, response_bytes=4), lambda: backend.now, asyncio.sleep
            )
            with pytest.raises(AssetError, match="size"):
                await fetcher.fetch(f"{CDN}/heroes/axe.png")
            assert count == 2
            from email.utils import format_datetime

            assert fetcher._retry_after(format_datetime(backend.now + timedelta(seconds=8)), 1) == 8
            assert fetcher._retry_after("invalid", 3) == 3
            assert fetcher._retry_after(None, 3) == 3

    run_async(run())


@pytest.mark.parametrize(
    "row",
    [
        {},
        {"id": True, "name": "item_blink", "name_loc": "fake"},
        {"id": 1, "name": "item_../escape", "name_loc": "fake"},
        {"id": 0, "name": "item_blink", "name_loc": "fake"},
    ],
)
def test_catalog_and_manifest_identity_boundaries(row, tmp_path):
    with pytest.raises(AssetError, match="catalog"):
        catalog(json.dumps({"result": {"data": {"items": [row]}}}).encode(), "items", "item_")
    (tmp_path / "manifest.json").write_text(json.dumps({"version": 1, "heroes": {"../x": row}}))
    with pytest.raises(AssetError, match="manifest"):
        validate_manifest(tmp_path, AssetLimits())


def test_local_path_png_and_json_boundaries(tmp_path, backend):
    with pytest.raises(AssetError, match="path"):
        safe_path(tmp_path, "../escape")
    with pytest.raises(AssetError, match="png"):
        png_size(b"broken", AssetLimits())
    with pytest.raises(AssetError, match="size"):
        png_size(backend.png(), AssetLimits(response_bytes=1))
    stream = io.BytesIO()
    with Image.new("RGB", (2049, 1)) as image:
        image.save(stream, "PNG")
    with pytest.raises(AssetError, match="png"):
        png_size(stream.getvalue(), AssetLimits())
    for raw in (b"[]", b"broken", b"\xff"):
        (tmp_path / "bad.json").write_bytes(raw)
        with pytest.raises(AssetError, match="manifest"):
            read_json(tmp_path / "bad.json", 100)
    with pytest.raises(AssetError, match="manifest"):
        read_json(tmp_path / "bad.json", 0)
    with pytest.raises(AssetError, match="clock"):
        aware_time(backend.now.replace(tzinfo=None))


@pytest.mark.parametrize(
    "options",
    [
        {"workers": 5},
        {"workers": True},
        {"retries": 3},
        {"job_seconds": 0},
        {"request_seconds": float("nan")},
        {"root_bytes": -1},
    ],
)
def test_invalid_budgets_rejected(options):
    with pytest.raises(AssetError, match="configuration"):
        AssetLimits(**options)
