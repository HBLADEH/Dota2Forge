"""The opt-in online command is itself tested with sockets disabled."""

import json

import httpx
import pytest
from dota2forge_core import AccountId, DataSource, ProviderError, ProviderErrorCode

from scripts import check_stratz


def test_check_queries_and_closes_without_printing_identity(monkeypatch, capsys, run_async):
    def response(request):
        query = json.loads(request.content)["query"]
        fields = (
            {"steamAccount": {"id": 123, "name": "Synthetic Secret Name", "seasonRank": 51}}
            if "Dota2ForgePlayer" in query
            else {"matches": []}
        )
        return httpx.Response(200, json={"data": {"player": {"steamAccountId": 123, **fields}}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(response))
    monkeypatch.setattr(check_stratz.httpx, "AsyncClient", lambda **kwargs: client)
    run_async(check_stratz.check("synthetic-token", AccountId(123), 1, 10))
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result["client_closed"] is True and client.is_closed
    assert result["same_account"] is True and result["matches"] == 0
    assert all(secret not in output for secret in ("synthetic-token", "123", "Secret Name"))


def test_check_closes_on_provider_failure(monkeypatch, run_async):
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(503)))
    monkeypatch.setattr(check_stratz.httpx, "AsyncClient", lambda **kwargs: client)
    with pytest.raises(ProviderError):
        run_async(check_stratz.check("synthetic-token", AccountId(123), 1, 10))
    assert client.is_closed


@pytest.fixture
def local_configuration(monkeypatch, run_async):
    monkeypatch.setenv("STRATZ_TOKEN", "synthetic-token")
    monkeypatch.setenv("STRATZ_ACCOUNT_ID", "123")
    monkeypatch.setenv("STRATZ_TIMEOUT_SECONDS", "2")
    monkeypatch.setattr("sys.argv", ["check_stratz.py", "--limit", "100"])
    monkeypatch.setattr(check_stratz.asyncio, "run", run_async)


def test_main_passes_configuration_and_accepts_steam64(local_configuration, monkeypatch):
    monkeypatch.setenv("STRATZ_ACCOUNT_ID", str(AccountId(123).to_steam_id64().value))
    calls = []

    async def check(*args):
        calls.append(args)

    monkeypatch.setattr(check_stratz, "check", check)
    assert check_stratz.main() == 0
    assert calls == [("synthetic-token", AccountId(123), 2.0, 100)]


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("STRATZ_TOKEN", None),
        ("STRATZ_ACCOUNT_ID", None),
        ("STRATZ_ACCOUNT_ID", "private-invalid-account"),
        ("STRATZ_TIMEOUT_SECONDS", "private-invalid-timeout"),
    ],
)
def test_main_redacts_invalid_configuration(local_configuration, monkeypatch, capsys, name, value):
    if value is None:
        monkeypatch.delenv(name)
    else:
        monkeypatch.setenv(name, value)
    assert check_stratz.main() == 2
    assert "private-invalid" not in capsys.readouterr().out


def test_main_reports_only_classified_failure(local_configuration, monkeypatch, capsys):
    async def check(*args):
        raise ProviderError(
            ProviderErrorCode.RATE_LIMITED, DataSource.STRATZ, retry_after_seconds=12
        )

    monkeypatch.setattr(check_stratz, "check", check)
    assert check_stratz.main() == 1
    assert json.loads(capsys.readouterr().out) == {
        "source": "stratz",
        "error": "rate_limited",
        "retry_after_seconds": 12,
    }
