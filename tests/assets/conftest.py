"""Synthetic Valve catalogs and public artwork; all requests stay in MockTransport."""

import asyncio
import io
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import pytest_socket
from dota2forge_assets import AssetLimits, AssetManager
from dota2forge_assets.sources import FEEDS
from PIL import Image


class Backend:
    def __init__(self):
        self.now = datetime(2026, 1, 1, tzinfo=UTC)
        self.calls = []
        self.clients = []
        self.fail = {}
        self.active = self.maximum = 0
        self.color = "red"
        self.hero = "axe"
        self.delay = 0

    def advance(self, seconds=31):
        self.now += timedelta(seconds=seconds)

    def png(self):
        stream = io.BytesIO()
        with Image.new("RGB", (32, 18), self.color) as image:
            image.save(stream, "PNG")
        return stream.getvalue()

    async def request(self, request):
        self.calls.append(request)
        assert "authorization" not in request.headers
        assert "cookie" not in request.headers
        self.active += 1
        self.maximum = max(self.active, self.maximum)
        try:
            await asyncio.sleep(self.delay)
            for prefix, value in self.fail.items():
                if str(request.url).startswith(prefix):
                    if isinstance(value, Exception):
                        raise value
                    return httpx.Response(value, request=request)
            for kind, (url, key, prefix) in FEEDS.items():
                if str(request.url) == url:
                    return httpx.Response(
                        200,
                        json={
                            "result": {
                                "data": {
                                    key: [
                                        {
                                            "id": 2 if kind == "heroes" else 1,
                                            "name": prefix
                                            + (self.hero if kind == "heroes" else "blink"),
                                            "name_loc": "合成公开素材",
                                        }
                                    ]
                                }
                            }
                        },
                    )
            return httpx.Response(200, content=self.png())
        finally:
            self.active -= 1

    def client(self):
        client = httpx.AsyncClient(transport=httpx.MockTransport(self.request), trust_env=False)
        self.clients.append(client)
        return client

    def manager(self, root, activate=None, **limits):
        return AssetManager(
            root,
            client_factory=self.client,
            clock=lambda: self.now,
            activate=activate,
            limits=AssetLimits(retries=0, **limits),
        )


@pytest.fixture
def backend():
    return Backend()


@pytest.fixture
def run_async():
    # Only create asyncio's wakeup sockets; application sockets remain blocked.
    pytest_socket.enable_socket()
    try:
        loop = asyncio.new_event_loop()
    finally:
        pytest_socket.disable_socket()
    try:
        yield loop.run_until_complete
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())
        loop.close()
