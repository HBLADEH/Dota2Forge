"""Fixed public OpenDota GETs; no credentials, retries or client ownership."""

import asyncio
import math
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

import httpx

from ..domain.errors import DataSource, ProviderError, ProviderErrorCode, ValidationError
from ..domain.models import require_aware_time
from ..ports import Clock

ENDPOINT = "https://api.opendota.com/api"


def failure(code: ProviderErrorCode, retry: int | None = None) -> ProviderError:
    return ProviderError(code, DataSource.OPENDOTA, retry_after_seconds=retry)


def header_integer(value: str | None) -> int | None:
    if value is None or not re.fullmatch(r"-?[0-9]{1,12}", value):
        return None
    return int(value)


def retry_after(value: str | None, now: datetime) -> int | None:
    number = header_integer(value)
    if number is not None:
        return number if number >= 0 else None
    if value is not None:
        try:
            date = parsedate_to_datetime(value)
            if date.tzinfo is not None:
                return max(0, math.ceil((date - now).total_seconds()))
        except (ValueError, TypeError, OverflowError):
            pass
    return None


class OpenDotaHTTP:
    def __init__(self, client: httpx.AsyncClient, clock: Clock, timeout_seconds: float) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= 60
        ):
            raise ValidationError("Expected a finite request timeout between 0 and 60 seconds")
        self._client = client
        self._clock = clock
        self._timeout = float(timeout_seconds)
        self._lock = asyncio.Lock()
        self._blocked_until: float | None = None
        self._unknown_reset = False

    async def request(
        self, path: str, params: list[tuple[str, str]] | None = None
    ) -> tuple[object, datetime]:
        async with self._lock:
            now = self._clock.now()
            require_aware_time(now)
            if self._unknown_reset:
                raise failure(ProviderErrorCode.RATE_LIMITED)
            if self._blocked_until is not None and self._blocked_until > now.timestamp():
                raise failure(
                    ProviderErrorCode.RATE_LIMITED,
                    math.ceil(self._blocked_until - now.timestamp()),
                )
            if self._client.is_closed:
                raise failure(ProviderErrorCode.UNAVAILABLE)
            try:
                async with asyncio.timeout(self._timeout):
                    request = self._client.build_request(
                        "GET",
                        ENDPOINT + path,
                        params=httpx.QueryParams(tuple(params or ())),
                        headers={"Accept": "application/json", "User-Agent": "Dota2Forge/0.1"},
                        timeout=httpx.Timeout(self._timeout),
                    )
                    # Do not inherit credentials/query defaults from another source's client.
                    request.url = httpx.URL(
                        ENDPOINT + path, params=httpx.QueryParams(tuple(params or ()))
                    )
                    for header in ("Authorization", "Cookie", "Proxy-Authorization"):
                        request.headers.pop(header, None)
                    response = await self._client.send(
                        request, auth=httpx.Auth(), follow_redirects=False
                    )
            except (httpx.TimeoutException, TimeoutError):
                raise failure(ProviderErrorCode.TIMEOUT) from None
            except httpx.RequestError:
                raise failure(ProviderErrorCode.UNAVAILABLE) from None
            fetched_at = self._clock.now()
            require_aware_time(fetched_at)
            wait = self._observe_limits(response, fetched_at)
            if response.status_code == 429:
                if wait is None:
                    self._unknown_reset = True
                raise failure(ProviderErrorCode.RATE_LIMITED, wait)
            if response.status_code == 401:
                raise failure(ProviderErrorCode.AUTHENTICATION)
            if response.status_code != 200:
                # A proxy 403/404 is not evidence of player privacy or match absence.
                raise failure(ProviderErrorCode.UNAVAILABLE)
            try:
                payload: object = response.json()
            except (ValueError, UnicodeError):
                raise failure(ProviderErrorCode.INVALID_RESPONSE) from None
            return payload, fetched_at

    def _observe_limits(self, response: httpx.Response, now: datetime) -> int | None:
        server_now = now
        try:
            date = parsedate_to_datetime(response.headers.get("Date", ""))
            if date.tzinfo is not None:
                server_now = date
        except (ValueError, TypeError, OverflowError):
            pass
        waits = []
        for name, window in (("Minute", 60), ("Day", 86400)):
            remaining = header_integer(response.headers.get(f"X-Rate-Limit-Remaining-{name}"))
            if remaining is not None and remaining <= 0:
                waits.append(math.ceil(window - server_now.timestamp() % window))
        wait = retry_after(response.headers.get("Retry-After"), server_now)
        if wait is not None and (waits or response.status_code == 429):
            waits.append(wait)
        if waits:
            self._blocked_until = max(self._blocked_until or 0, now.timestamp() + max(waits))
            return math.ceil(self._blocked_until - now.timestamp())
        return None
