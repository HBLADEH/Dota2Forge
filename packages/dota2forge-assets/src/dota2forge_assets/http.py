"""Finite asynchronous requests, approved redirects and classified failures."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

import httpx

from .models import AssetError, AssetLimits, aware_time
from .sources import validate_url


class Fetcher:
    def __init__(
        self,
        client: httpx.AsyncClient,
        limits: AssetLimits,
        now: Callable[[], datetime],
        sleep: Callable[[float], Awaitable[None]],
    ) -> None:
        self.client, self.limits, self.now, self.sleep = client, limits, now, sleep
        self.client.auth = httpx.Auth()
        self.client.headers.clear()
        self.client.cookies.clear()
        self.slots = asyncio.Semaphore(limits.workers)

    async def fetch(self, url: str) -> bytes:
        validate_url(url)
        for attempt in range(self.limits.retries + 1):
            delay = (1.0, 3.0)[min(attempt, 1)]
            try:
                async with self.slots, asyncio.timeout(self.limits.request_seconds):
                    target = url
                    for redirect in range(4):
                        validate_url(target)
                        async with self.client.stream(
                            "GET",
                            target,
                            headers={"User-Agent": "Dota2Forge asset downloader/2"},
                            follow_redirects=False,
                        ) as response:
                            if response.is_redirect:
                                location = response.headers.get("location")
                                if not location or redirect == 3:
                                    raise AssetError("source")
                                target = urljoin(target, location)
                                continue
                            if response.status_code == 404:
                                raise AssetError("http_404")
                            if response.status_code == 429:
                                delay = self._retry_after(
                                    response.headers.get("retry-after"), delay
                                )
                                raise AssetError("http_429")
                            if 500 <= response.status_code <= 599:
                                raise AssetError("http_5xx")
                            if response.status_code != 200:
                                raise AssetError("http_error")
                            chunks = bytearray()
                            async for chunk in response.aiter_bytes():
                                if len(chunks) + len(chunk) > self.limits.response_bytes:
                                    raise AssetError("size")
                                chunks.extend(chunk)
                            return bytes(chunks)
            except (httpx.TimeoutException, TimeoutError):
                error = AssetError("timeout")
            except httpx.TransportError:
                error = AssetError("network")
            except AssetError as caught:
                error = caught
            if error.code not in {"timeout", "network", "http_429", "http_5xx"}:
                raise error
            if attempt == self.limits.retries:
                raise error
            await self.sleep(delay)
        raise AssetError("network")

    def _retry_after(self, raw: str | None, default: float) -> float:
        if raw is None:
            return default
        try:
            if raw.isdecimal():
                return max(default, float(raw))
            date = aware_time(parsedate_to_datetime(raw))
            return max(default, (date - aware_time(self.now())).total_seconds())
        except (ValueError, TypeError, OverflowError, AssetError):
            return default
