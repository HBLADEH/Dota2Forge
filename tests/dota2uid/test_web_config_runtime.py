"""Host configuration snapshots share TOML validation and explicit restart semantics."""

import asyncio
import json
import tomllib
from types import MappingProxyType

import httpx
import pytest
from Dota2UID.config import (
    ConfigurationError,
    ConfigurationPending,
    load_config,
    load_config_values,
)
from Dota2UID.runtime import AWAITING_CONFIG, UNAVAILABLE, Runtime, State


def values(**changes):
    return {
        "namespace": "synthetic-deployment",
        "stratz_token": "synthetic-web-token",
        "timeout_seconds": 2,
        "platforms": {"onebot": "qq", "telegram": "telegram"},
        "reply_mode": "text",
        "asset_download_mode": "off",
        **changes,
    }


def profile(request):
    account = json.loads(request.content)["variables"]["accountId"]
    return httpx.Response(
        200,
        json={
            "data": {
                "player": {
                    "steamAccountId": account,
                    "steamAccount": {"id": account, "name": "Synthetic Player", "seasonRank": 51},
                    "matches": [],
                }
            }
        },
    )


def test_mapping_and_toml_share_validation_and_fixed_local_paths(config_path, monkeypatch):
    config_path.write_text(
        'illustration_path="artwork/custom"\nasset_download_mode="manual"\n'
        + config_path.read_text("utf-8"),
        "utf-8",
    )
    original = config_path.read_bytes()
    raw = tomllib.loads(original.decode("utf-8"))
    expected = load_config(config_path)

    def forbidden(*args, **kwargs):
        pytest.fail("A host snapshot must not read or write TOML")

    monkeypatch.setattr(type(config_path), "read_text", forbidden)
    monkeypatch.setattr(type(config_path), "write_text", forbidden)
    config = load_config_values(config_path, MappingProxyType(raw))
    assert config == expected
    assert config.database == config_path.parent / "bindings.sqlite3"
    assert config.illustration_path == config_path.parent / "artwork/custom"
    assert config.assets.external == config.illustration_path
    assert config_path.read_bytes() == original
    raw["platforms"]["onebot"] = "changed"
    raw["stratz_token"] = "changed-token"
    assert config.platforms["onebot"] == "qq" and config.token == "synthetic-token"
    assert "synthetic-token" not in repr(config)


@pytest.mark.parametrize("missing", ["namespace", "stratz_token", "timeout_seconds", "platforms"])
def test_mapping_requires_the_same_explicit_identity_and_provider_fields(tmp_path, missing):
    raw = values()
    del raw[missing]
    with pytest.raises(ConfigurationError, match="configuration is missing or invalid"):
        load_config_values(tmp_path / "config.toml", raw)


@pytest.mark.parametrize(
    "changes",
    [
        {"namespace": 1},
        {"namespace": "UPPER"},
        {"stratz_token": 1},
        {"stratz_token": "synthetic-secret\n"},
        {"stratz_token": "令牌"},
        {"timeout_seconds": True},
        {"timeout_seconds": "10"},
        {"timeout_seconds": 0},
        {"timeout_seconds": 61},
        {"timeout_seconds": float("nan")},
        {"timeout_seconds": float("inf")},
        {"platforms": []},
        {"platforms": {}},
        {"platforms": {"onebot": 1}},
        {"platforms": {"onebot": "UPPER"}},
        {"platforms": {"": "qq"}},
        {"reply_mode": "html"},
        {"reply_mode": None},
        {"subscriptions_enabled": 1},
        {"subscription_interval_seconds": True},
        {"subscription_interval_seconds": 60.0},
        {"subscription_interval_seconds": 59},
        {"subscription_interval_seconds": 86401},
        {"daily_report_hour": True},
        {"daily_report_hour": 9.0},
        {"daily_report_hour": -1},
        {"daily_report_hour": 24},
        {"illustration_path": []},
        {"illustration_path": "synthetic-secret\n"},
        {"illustration_path": "x" * 2049},
        {"asset_download_mode": "unknown"},
        {"asset_proxy": "https://synthetic-secret@example.invalid"},
        {"asset_proxy": "http://example.invalid:80/?synthetic-secret"},
        {"database": "/outside.sqlite3"},
        {"unknown": "synthetic-secret"},
    ],
)
def test_mapping_rejects_invalid_values_without_exposing_them(tmp_path, changes):
    with pytest.raises(ConfigurationError) as failure:
        load_config_values(tmp_path / "config.toml", values(**changes))
    assert str(failure.value) == "Dota2UID configuration is missing or invalid"
    assert "synthetic-secret" not in repr(failure.value)
    assert failure.value.__cause__ is None
    assert not list(tmp_path.iterdir())


def test_valid_empty_mapping_token_retains_the_validated_pending_configuration(tmp_path):
    with pytest.raises(ConfigurationPending) as pending:
        load_config_values(tmp_path / "config.toml", values(stratz_token=""))
    assert pending.value.config is not None
    assert pending.value.config.namespace == "synthetic-deployment"
    assert pending.value.config.token == ""
    assert pending.value.config.assets.mode == "off"
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("existing", [False, True])
def test_custom_loader_does_not_create_or_modify_toml(tmp_path, monkeypatch, run_async, existing):
    import Dota2UID.runtime as runtime_module

    path = tmp_path / "data/config.toml"
    if existing:
        path.parent.mkdir()
        path.write_bytes(b"preserved invalid legacy TOML")
    original = path.read_bytes() if existing else None
    calls = []
    clients = []

    def forbidden(*args, **kwargs):
        pytest.fail("Custom configuration must not ensure or load TOML")

    monkeypatch.setattr(runtime_module, "ensure_config", forbidden)
    monkeypatch.setattr(runtime_module, "load_config", forbidden)

    def loader(received_path):
        calls.append(received_path)
        return load_config_values(received_path, values())

    def client():
        instance = httpx.AsyncClient(transport=httpx.MockTransport(profile), trust_env=False)
        clients.append(instance)
        return instance

    async def check():
        runtime = Runtime(path, config_loader=loader, client_factory=client)
        assert not calls and not clients
        await asyncio.gather(runtime.start(), runtime.start())
        assert runtime.state is State.READY and calls == [path] and len(clients) == 1
        assert (path.read_bytes() if path.exists() else None) == original
        await runtime.close()
        assert clients[0].is_closed

    run_async(check())


def test_saved_web_values_apply_only_to_a_new_runtime_after_stop(
    config_path, caller, run_async, caplog
):
    original = config_path.read_bytes()
    saved = values()
    calls, clients, requests = [], [], []

    def loader(path):
        calls.append(path)
        return load_config_values(path, saved)

    def client():
        def transport(request):
            requests.append((request.headers["Authorization"], request.extensions["timeout"]))
            return profile(request)

        instance = httpx.AsyncClient(transport=httpx.MockTransport(transport), trust_env=False)
        clients.append(instance)
        return instance

    async def check():
        first = Runtime(config_path, config_loader=loader, client_factory=client)
        await first.start()
        assert first.state is State.READY
        assert "players/123" in (await first.handle(caller, "do查询", "123"))[0]
        saved.update(stratz_token="synthetic-saved-token", timeout_seconds=8)
        await first.start()
        assert "players/124" in (await first.handle(caller, "do查询", "124"))[0]
        assert calls == [config_path]
        assert [header for header, _ in requests] == ["Bearer synthetic-web-token"] * 2
        assert all(timeout["read"] == 2 for _, timeout in requests)
        await first.close()
        assert clients[0].is_closed and first.state is State.STOPPED
        assert await first.handle(caller, "do查询", "125") == [UNAVAILABLE]
        restored = Runtime(config_path, config_loader=loader, client_factory=client)
        await restored.start()
        assert restored.state is State.READY
        assert "players/125" in (await restored.handle(caller, "do查询", "125"))[0]
        assert calls == [config_path, config_path]
        assert requests[-1][0] == "Bearer synthetic-saved-token"
        assert requests[-1][1]["read"] == 8
        await restored.close()
        assert all(instance.is_closed for instance in clients)

    run_async(check())
    assert config_path.read_bytes() == original
    assert "synthetic-web-token" not in caplog.text and "synthetic-saved-token" not in caplog.text


def test_empty_web_token_never_falls_back_to_legacy_token(config_path, caller, run_async, caplog):
    original = config_path.read_bytes()
    saved = values(stratz_token="")
    calls, clients = [], []

    def loader(path):
        calls.append(path)
        return load_config_values(path, saved)

    def client():
        instance = httpx.AsyncClient(transport=httpx.MockTransport(profile), trust_env=False)
        clients.append(instance)
        return instance

    async def check():
        waiting = Runtime(config_path, config_loader=loader, client_factory=client)
        assert await waiting.handle(caller, "do菜单", "") == [AWAITING_CONFIG]
        assert waiting.state is State.AWAITING_CONFIG and waiting.client_closed
        assert not clients and not (config_path.parent / "bindings.sqlite3").exists()
        assert not (config_path.parent / "subscriptions.sqlite3").exists()
        saved["stratz_token"] = "synthetic-saved-token"
        assert await waiting.handle(caller, "do菜单", "") == [AWAITING_CONFIG]
        assert calls == [config_path] and not clients
        await waiting.close()
        configured = Runtime(config_path, config_loader=loader, client_factory=client)
        await configured.start()
        assert configured.state is State.READY and len(clients) == 1
        await configured.close()
        database = (config_path.parent / "bindings.sqlite3").read_bytes()
        saved["stratz_token"] = ""
        cleared = Runtime(config_path, config_loader=loader, client_factory=client)
        assert await cleared.handle(caller, "do菜单", "") == [AWAITING_CONFIG]
        assert cleared.state is State.AWAITING_CONFIG and cleared.client_closed
        assert len(clients) == 1 and clients[0].is_closed
        assert (config_path.parent / "bindings.sqlite3").read_bytes() == database
        await cleared.close()
        assert calls == [config_path] * 3

    run_async(check())
    assert config_path.read_bytes() == original
    assert "synthetic-token" not in caplog.text and "synthetic-saved-token" not in caplog.text


@pytest.mark.parametrize("failure", [OSError, ValueError, TypeError, RuntimeError])
def test_loader_errors_fail_with_fixed_log_and_no_business_resources(
    tmp_path, caller, run_async, caplog, failure
):
    path = tmp_path / "data/config.toml"
    calls = []

    def loader(received_path):
        calls.append(received_path)
        raise failure("synthetic-secret")

    async def check():
        runtime = Runtime(
            path,
            config_loader=loader,
            client_factory=lambda: pytest.fail("No client for a failed loader"),
        )
        assert await runtime.handle(caller, "do菜单", "") == [UNAVAILABLE]
        await runtime.start()
        assert runtime.state is State.FAILED and runtime.client_closed and calls == [path]
        assert not path.parent.exists()
        await runtime.close()

    run_async(check())
    assert "error_type=ConfigurationError" in caplog.text and "synthetic-secret" not in caplog.text


def test_loader_cannot_return_unvalidated_values(tmp_path, caller, run_async):
    path = tmp_path / "config.toml"

    async def check():
        runtime = Runtime(
            path,
            config_loader=lambda _: values(),
            client_factory=lambda: pytest.fail("No client for unvalidated values"),
        )
        assert await runtime.handle(caller, "do菜单", "") == [UNAVAILABLE]
        assert runtime.state is State.FAILED and not list(tmp_path.iterdir())
        await runtime.close()

    run_async(check())
