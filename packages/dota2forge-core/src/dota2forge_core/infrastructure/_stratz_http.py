"""Bounded STRATZ HTTP requests; client ownership remains with the caller."""

import asyncio
import math
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from ..domain.errors import DataSource, ProviderError, ProviderErrorCode, ValidationError
from ..domain.models import require_aware_time
from ..ports import Clock

ENDPOINT = "https://api.stratz.com/graphql"
_WINDOWS = {"Second": 1, "Minute": 60, "Hour": 3600, "Day": 86400}


def failure(code: ProviderErrorCode, retry: int | None = None) -> ProviderError:
    return ProviderError(code, DataSource.STRATZ, retry_after_seconds=retry)


def _integer(value: str | None) -> int | None:
    if value is None or not value.isascii() or not value.isdecimal():
        return None
    # Bound header parsing; a malformed upstream must not trigger integer limits.
    return int(value) if len(value) <= 12 else None


def _retry_after(value: str | None, now: datetime) -> int | None:
    seconds = _integer(value)
    if seconds is not None or value is None:
        return seconds
    try:
        date = parsedate_to_datetime(value)
        if date.tzinfo is not None:
            return max(0, math.ceil((date - now).total_seconds()))
    except (ValueError, TypeError, OverflowError):
        pass
    return None


class StratzHTTP:
    def __init__(
        self, client: httpx.AsyncClient, token: str, clock: Clock, timeout_seconds: float
    ) -> None:
        if (
            not isinstance(token, str)
            or not token
            or not token.isascii()
            or any(ord(char) < 33 or ord(char) > 126 for char in token)
        ):
            raise ValidationError("Expected a nonempty ASCII bearer token without whitespace")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValidationError("Expected a finite positive request timeout")
        self._client = client
        self._token = token
        self._clock = clock
        self._timeout = float(timeout_seconds)
        self._lock = asyncio.Lock()
        self._blocked_until: float | None = None
        self._unknown_reset = False

    async def request(self, query: str, variables: dict[str, int]) -> tuple[object, datetime]:
        # One instance per token in a host: queued calls observe preceding quota headers.
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
                    response = await self._client.post(
                        ENDPOINT,
                        json={"query": query, "variables": variables},
                        headers={
                            "Authorization": f"Bearer {self._token}",
                            "User-Agent": "STRATZ_API",
                            "Accept": "application/json",
                            "Content-Type": "application/json",
                        },
                        auth=httpx.Auth(),
                        timeout=httpx.Timeout(self._timeout),
                        follow_redirects=False,
                    )
            except (httpx.TimeoutException, TimeoutError):
                raise failure(ProviderErrorCode.TIMEOUT) from None
            except httpx.RequestError:
                raise failure(ProviderErrorCode.UNAVAILABLE) from None
            fetched_at = self._clock.now()
            require_aware_time(fetched_at)
            retry = self._observe_limits(response, fetched_at)
            if response.status_code == 429:
                if self._blocked_until is None or self._blocked_until <= fetched_at.timestamp():
                    self._unknown_reset = retry is None
                raise failure(ProviderErrorCode.RATE_LIMITED, retry)
            if response.status_code == 401:
                raise failure(ProviderErrorCode.AUTHENTICATION)
            if response.status_code == 403:
                try:
                    body = response.json()
                except (ValueError, UnicodeError):
                    body = None
                # Exact gateway response verified independently; no message substring guesses.
                if isinstance(body, dict) and body.get("message") == (
                    "A bearer token is required for a request. View more at https://stratz.com/api"
                ):
                    raise failure(ProviderErrorCode.AUTHENTICATION)
            if response.status_code != 200:
                # A gateway's HTML 403/404 is not evidence about a player's privacy/existence.
                raise failure(ProviderErrorCode.UNAVAILABLE)
            try:
                payload: object = response.json()
            except (ValueError, UnicodeError):
                raise failure(ProviderErrorCode.INVALID_RESPONSE) from None
            return payload, fetched_at

    def _observe_limits(self, response: httpx.Response, now: datetime) -> int | None:
        waits: list[int] = []
        server_now = now
        try:
            server_date = parsedate_to_datetime(response.headers.get("Date", ""))
            if server_date.tzinfo is not None:
                server_now = server_date.astimezone(UTC)
        except (ValueError, TypeError, OverflowError):
            pass
        for name, duration in _WINDOWS.items():
            remaining = _integer(response.headers.get(f"X-RateLimit-Remaining-{name}"))
            if remaining == 0:
                # STRATZ documents aligned second/minute/hour/day windows; Date avoids skew.
                waits.append(math.ceil(duration - server_now.timestamp() % duration))
        retry = _retry_after(response.headers.get("Retry-After"), server_now)
        if _integer(response.headers.get("RateLimit-Remaining")) == 0:
            reset = _integer(response.headers.get("RateLimit-Reset"))
            if reset is not None:
                waits.append(reset)
            elif not waits and retry is None:
                self._unknown_reset = True
        if retry is not None and (response.status_code == 429 or waits):
            waits.append(retry)
        if waits:
            delay = max(waits)
            until = now.timestamp() + delay
            if self._blocked_until is None or until > self._blocked_until:
                self._blocked_until = until
        if self._blocked_until is not None and self._blocked_until > now.timestamp():
            return math.ceil(self._blocked_until - now.timestamp())
        return retry
