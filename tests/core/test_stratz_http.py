"""Synthetic transport cases; pytest-socket remains enabled for every request."""

import asyncio
import json
import traceback
from datetime import timedelta

import httpx
import pytest
from dota2forge_core import ProviderError, ProviderErrorCode, ValidationError
from dota2forge_core.infrastructure._stratz_http import ENDPOINT, StratzHTTP

TOKEN = "synthetic-token-not-a-credential"


def test_http_contract_and_caller_closes_client(clock, run_async):
    requests = []

    def reply(request):
        requests.append(request)
        assert request.url == ENDPOINT
        assert request.method == "POST"
        assert request.headers["authorization"] == f"Bearer {TOKEN}"
        assert request.headers["user-agent"] == "STRATZ_API"
        assert request.headers["content-type"] == "application/json"
        assert request.extensions["timeout"] == dict.fromkeys(
            ["connect", "read", "write", "pool"], 2.5
        )
        assert json.loads(request.content) == {"query": "query Test", "variables": {"id": 123}}
        return httpx.Response(200, json={"data": {}})

    async def check():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(reply), auth=("unwanted", "client-default")
        ) as client:
            provider = StratzHTTP(client, TOKEN, clock, 2.5)
            assert TOKEN not in repr(provider)
            assert await provider.request("query Test", {"id": 123}) == ({"data": {}}, clock.now())
        assert client.is_closed
        with pytest.raises(ProviderError) as error:
            await provider.request("query Test", {})
        assert error.value.code == ProviderErrorCode.UNAVAILABLE
        assert len(requests) == 1

    run_async(check())


@pytest.mark.parametrize("token", [None, 1, "", "token space", "token\r\n", "令牌", "a\x7f"])
def test_invalid_tokens_are_rejected_without_echo(clock, token):
    with pytest.raises(ValidationError, match="ASCII bearer token"):
        StratzHTTP(None, token, clock, 10)


@pytest.mark.parametrize("timeout", [None, "10", True, 0, -1, float("inf"), float("nan")])
def test_invalid_timeouts_are_rejected(clock, timeout):
    with pytest.raises(ValidationError, match="finite positive"):
        StratzHTTP(None, TOKEN, clock, timeout)


@pytest.mark.parametrize(
    ("status", "code"),
    [(401, ProviderErrorCode.AUTHENTICATION)]
    + [(status, ProviderErrorCode.UNAVAILABLE) for status in [204, 301, 400, 403, 404, 500, 503]],
)
def test_http_errors_and_redirects_never_become_player_absence(clock, run_async, status, code):
    requests = []

    def reply(request):
        requests.append(request)
        return httpx.Response(status, text=TOKEN, headers={"Location": "https://example.invalid/"})

    async def check():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(reply), follow_redirects=True
        ) as c:
            with pytest.raises(ProviderError) as error:
                await StratzHTTP(c, TOKEN, clock, 1).request("q", {})
            assert error.value.code == code
            assert TOKEN not in str(error.value)
        assert c.is_closed and len(requests) == 1

    run_async(check())


@pytest.mark.parametrize("content", [b"<html>blocked</html>", b"{", b"", b"\xff"])
def test_invalid_json_is_not_an_empty_result(clock, run_async, content):
    async def check():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, content=content))
        ) as c:
            with pytest.raises(ProviderError) as error:
                await StratzHTTP(c, TOKEN, clock, 1).request("q", {})
            assert error.value.code == ProviderErrorCode.INVALID_RESPONSE

    run_async(check())


@pytest.mark.parametrize("exception", [httpx.ReadTimeout, httpx.ConnectError, httpx.ReadError])
def test_transport_failures_are_sanitized_without_retry(clock, run_async, exception):
    calls = []

    def reply(request):
        calls.append(request)
        raise exception(TOKEN, request=request)

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as c:
            with pytest.raises(ProviderError) as error:
                await StratzHTTP(c, TOKEN, clock, 1).request("q", {})
            expected = (
                ProviderErrorCode.TIMEOUT
                if exception is httpx.ReadTimeout
                else ProviderErrorCode.UNAVAILABLE
            )
            assert error.value.code == expected
            assert TOKEN not in "".join(traceback.format_exception(error.value))
        assert c.is_closed and len(calls) == 1

    run_async(check())


def test_overall_request_timeout_interrupts_a_stalled_transport(clock, run_async):
    async def reply(_):
        await asyncio.Event().wait()

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as c:
            with pytest.raises(ProviderError) as error:
                await asyncio.wait_for(StratzHTTP(c, TOKEN, clock, 0.01).request("q", {}), 2)
            assert error.value.code == ProviderErrorCode.TIMEOUT
        assert c.is_closed

    run_async(check())


def test_cancellation_propagates_and_unlocks_the_transport(clock, run_async):
    async def check():
        started = asyncio.Event()
        calls = 0

        async def reply(_):
            nonlocal calls
            calls += 1
            if calls == 1:
                started.set()
                await asyncio.Event().wait()
            return httpx.Response(200, json={"data": {}})

        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as c:
            transport = StratzHTTP(c, TOKEN, clock, 10)
            task = asyncio.create_task(transport.request("q", {}))
            await started.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            await transport.request("q", {})
        assert c.is_closed and calls == 2

    run_async(check())


@pytest.mark.parametrize(
    ("window", "delay"), [("Second", 1), ("Minute", 60), ("Hour", 3600), ("Day", 86400)]
)
def test_quota_exhaustion_blocks_later_requests_until_reset(clock, run_async, window, delay):
    calls = []

    def reply(request):
        calls.append(request)
        return httpx.Response(200, json={}, headers={f"X-RateLimit-Remaining-{window}": "0"})

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as c:
            transport = StratzHTTP(c, TOKEN, clock, 1)
            await transport.request("q", {})
            with pytest.raises(ProviderError) as error:
                await transport.request("q", {})
            assert error.value.code == ProviderErrorCode.RATE_LIMITED
            assert error.value.retry_after_seconds == delay
            assert len(calls) == 1
            clock.instant += timedelta(seconds=delay)
            await transport.request("q", {})
            assert len(calls) == 2

    run_async(check())


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({"Retry-After": "12"}, 12),
        ({"Retry-After": "0"}, 0),
        ({"Retry-After": "999999999999"}, 999999999999),
        ({"Retry-After": "Wed, 30 Sep 2026 00:00:12 GMT"}, 12),
        ({"Retry-After": "Tue, 29 Sep 2026 00:00:12 GMT"}, 0),
        ({"Retry-After": "Wed, 30 Sep 2026 00:00:12"}, None),
        ({"Retry-After": "bad"}, None),
        ({"Retry-After": "-1"}, None),
        ({"Retry-After": "9" * 500}, None),
        ({}, None),
        ({"Retry-After": "12", "X-RateLimit-Remaining-Hour": "0"}, 3600),
        ({"X-RateLimit-Remaining-Day": "0", "Date": "Wed, 30 Sep 2026 23:59:55 GMT"}, 5),
        ({"X-RateLimit-Remaining-Second": "0", "Date": "malformed"}, 1),
        ({"X-RateLimit-Remaining-Minute": "invalid"}, None),
        ({"X-RateLimit-Remaining-Minute": "9" * 500}, None),
    ],
)
def test_429_respects_tightest_window_and_known_wait(clock, run_async, headers, expected):
    calls = []

    def reply(request):
        calls.append(request)
        return httpx.Response(429, headers=headers, text=TOKEN)

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as c:
            transport = StratzHTTP(c, TOKEN, clock, 1)
            for _ in range(2):
                with pytest.raises(ProviderError) as error:
                    await transport.request("q", {})
                assert error.value.code == ProviderErrorCode.RATE_LIMITED
                assert error.value.retry_after_seconds == expected
            assert len(calls) == (2 if expected == 0 else 1)

    run_async(check())


def test_queued_requests_see_exhausted_quota(clock, run_async):
    async def check():
        started, release = asyncio.Event(), asyncio.Event()
        calls = 0

        async def reply(_):
            nonlocal calls
            calls += 1
            started.set()
            await release.wait()
            return httpx.Response(200, json={}, headers={"X-RateLimit-Remaining-Minute": "0"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as c:
            transport = StratzHTTP(c, TOKEN, clock, 1)
            first = asyncio.create_task(transport.request("q", {}))
            await started.wait()
            second = asyncio.create_task(transport.request("q", {}))
            release.set()
            await first
            with pytest.raises(ProviderError) as error:
                await second
            assert error.value.code == ProviderErrorCode.RATE_LIMITED
            assert calls == 1

    run_async(check())


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            {
                "message": "A bearer token is required for a request. View more at https://stratz.com/api"
            },
            ProviderErrorCode.AUTHENTICATION,
        ),
        ({"message": "Access forbidden"}, ProviderErrorCode.UNAVAILABLE),
        (None, ProviderErrorCode.UNAVAILABLE),
    ],
)
def test_only_verified_403_message_means_authentication(clock, run_async, body, expected):
    async def check():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(403, json=body))
        ) as client:
            with pytest.raises(ProviderError) as error:
                await StratzHTTP(client, TOKEN, clock, 1).request("q", {})
            assert error.value.code == expected

    run_async(check())


@pytest.mark.parametrize(
    ("headers", "retry"),
    [
        ({"RateLimit-Remaining": "0", "RateLimit-Reset": "13"}, 13),
        ({"RateLimit-Remaining": "0"}, None),
        ({"RateLimit-Remaining": "0", "Retry-After": "5"}, 5),
    ],
)
def test_generic_rate_headers_also_stop_later_requests(clock, run_async, headers, retry):
    async def check():
        calls = []

        def respond(request):
            calls.append(request)
            return httpx.Response(429, headers=headers)

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            transport = StratzHTTP(client, TOKEN, clock, 1)
            for _ in range(2):
                with pytest.raises(ProviderError) as error:
                    await transport.request("q", {})
                assert error.value.code == ProviderErrorCode.RATE_LIMITED
                assert error.value.retry_after_seconds == retry
            assert len(calls) == 1

    run_async(check())
