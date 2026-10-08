"""Offline native configuration migration, secret metadata and persistence checks."""

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "adapters/Dota2UID/src/Dota2UID/host_config.py.template"
SDK = Path(__file__).with_name("_config_sdk.py")
LEGACY = (
    'namespace = "synthetic-deployment"\nstratz_token = "synthetic-token"\n'
    'timeout_seconds = 12\n[platforms]\nonebot = "qq"\n'
)


@pytest.fixture
def host_config(tmp_path, monkeypatch):
    helper_name = "synthetic_host_config_sdk"
    spec = importlib.util.spec_from_file_location(helper_name, SDK)
    helper = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, helper_name, helper)
    spec.loader.exec_module(helper)
    registry = helper.install_config_sdk(monkeypatch)
    plugin = tmp_path / "host/gsuid_core/plugins/Dota2UID"
    plugin.mkdir(parents=True)
    source = plugin / "_dota2forge_config.py"
    source.write_bytes(SOURCE.read_bytes())
    data = tmp_path / "host/data/Dota2UID"
    data.mkdir(parents=True)

    def load(name="synthetic_host_config"):
        spec = importlib.util.spec_from_file_location(name, source)
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        return module

    module = load()
    return SimpleNamespace(
        module=module,
        data=data,
        registry=registry,
        helper=helper,
        load=load,
        toml=data / "config.toml",
        native=data / "config.json",
    )


def test_first_start_registers_without_project_packages(host_config):
    host = host_config
    config = host.module.register_config(host.data)
    assert config.native is host.registry["Dota2UID"]
    assert config.native.plugin_name == "Dota2UID"
    assert config.snapshot() == host.module.DEFAULTS
    assert host.native.exists()
    assert not host.toml.exists()
    assert config.native.config["stratz_token"].secret is True
    assert config.native.config["asset_proxy"].secret is True
    assert config.native.config["platforms"].data.startswith("{")
    assert config.native.config["daily_report_hour"].desc.count("UTC+8") == 1
    assert all(
        "停用" in item.desc and "重载" in item.desc for item in config.native.config.values()
    )


def test_seed_legacy_optional_defaults_and_exact_bytes_preserved(host_config):
    host = host_config
    original = b"\xef\xbb\xbf" + LEGACY.replace("\n", "\r\n").encode()
    host.toml.write_bytes(original)
    config = host.module.register_config(host.data)
    values = config.snapshot()
    assert values["namespace"] == "synthetic-deployment"
    assert values["stratz_token"] == "synthetic-token"
    assert values["timeout_seconds"] == 12.0
    assert type(values["timeout_seconds"]) is float
    assert values["platforms"] == {"onebot": "qq"}
    assert values["subscriptions_enabled"] is False
    assert host.toml.read_bytes() == original


def test_existing_native_precedence_and_empty_token_never_falls_back(host_config):
    host = host_config
    host.toml.write_text(LEGACY, "utf-8")
    original = host.toml.read_bytes()
    config = host.module.register_config(host.data)
    assert config.native.set_config("stratz_token", "")
    host.toml.write_text("malformed synthetic-token = [", "utf-8")
    config = host.module.register_config(host.data)
    assert config.snapshot()["stratz_token"] == ""
    assert config.snapshot()["namespace"] == "synthetic-deployment"
    host.toml.write_bytes(original)
    assert config.native.set_config("reply_mode", "text")
    assert host.toml.read_bytes() == original


@pytest.mark.parametrize(
    "source",
    [
        "namespace = [",
        'namespace = "synthetic"\nstratz_token = "secret-canary"\n'
        'timeout_seconds = true\n[platforms]\nonebot = "qq"',
        LEGACY.replace('stratz_token = "synthetic-token"\n', ""),
        LEGACY.replace("timeout_seconds = 12", "timeout_seconds = nan"),
        LEGACY.replace('onebot = "qq"', "onebot = 6"),
        LEGACY.replace("[platforms]", 'unknown_field = "secret-canary"\n[platforms]'),
    ],
)
def test_malformed_legacy_is_preserved_and_never_registered(host_config, source):
    host = host_config
    host.toml.write_text(source, "utf-8")
    before = host.toml.read_bytes()
    with pytest.raises(host.module.ConfigBridgeError, match="^invalid_host_config$") as caught:
        host.module.register_config(host.data)
    assert "secret-canary" not in str(caught.value)
    assert host.toml.read_bytes() == before
    assert not host.native.exists()
    assert host.registry == {}


def valid_native(host):
    host.module.register_config(host.data)
    return json.loads(host.native.read_text("utf-8"))


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.pop("namespace"),
        lambda value: value.update(unknown={}),
        lambda value: value["stratz_token"].update(type="GsIntConfig"),
        lambda value: value["stratz_token"].update(data=77),
        lambda value: value["stratz_token"].update(secret="true"),
        lambda value: value["platforms"].update(data="not JSON secret-canary"),
        lambda value: value["platforms"].update(data='{"onebot":5}'),
        lambda value: value["platforms"].update(data='{"onebot":"qq","onebot":"qq"}'),
        lambda value: value["reply_mode"].update(options=[True]),
        lambda value: value["daily_report_hour"].update(max_value="23"),
        lambda value: value["subscriptions_enabled"].update(data=1),
        lambda value: value["timeout_seconds"].update(data=True),
        lambda value: value["timeout_seconds"].update(data=float("nan")),
        lambda value: value["timeout_seconds"].update(data=float("inf")),
        lambda value: value["timeout_seconds"].update(data=float("-inf")),
        lambda value: value["timeout_seconds"].update(max_value=10**400),
        lambda value: value["namespace"].update(title=[]),
        lambda value: value["namespace"].update(unknown="secret-canary"),
        lambda value: value["namespace"].update(data="\ud800"),
    ],
)
def test_damaged_native_never_repaired_and_previous_registration_untouched(host_config, change):
    host = host_config
    values = valid_native(host)
    existing = host.registry["Dota2UID"]
    before_state = dict(existing.__dict__)
    change(values)
    host.native.write_text(json.dumps(values), "utf-8")
    damaged = host.native.read_bytes()
    with pytest.raises(host.module.ConfigBridgeError, match="^invalid_host_config$"):
        host.module.register_config(host.data)
    assert host.native.read_bytes() == damaged
    assert host.registry["Dota2UID"] is existing
    assert existing.__dict__ == before_state


@pytest.mark.parametrize(
    "source",
    ["[", "null", "[]", '{"namespace":{},"namespace":{}}', '{"timeout_seconds":{"data":NaN}}'],
)
def test_invalid_native_json_not_overwritten(host_config, source):
    host = host_config
    host.native.write_text(source, "utf-8")
    before = host.native.read_bytes()
    with pytest.raises(host.module.ConfigBridgeError):
        host.module.register_config(host.data)
    assert host.native.read_bytes() == before
    assert host.registry == {}


@pytest.mark.parametrize("metadata", [False, True])
def test_json_numeric_overflow_inside_complete_envelope_is_never_sdk_repaired(
    host_config,
    metadata,
):
    host = host_config
    values = valid_native(host)
    native = host.registry["Dota2UID"]
    before_state = dict(native.__dict__)
    field = "max_value" if metadata else "data"
    values["timeout_seconds"][field] = 12345.0
    raw = json.dumps(values).replace("12345.0", "1e999").encode()
    host.native.write_bytes(raw)
    with pytest.raises(host.module.ConfigBridgeError, match="^invalid_host_config$"):
        host.module.register_config(host.data)
    assert host.native.read_bytes() == raw
    assert host.registry["Dota2UID"] is native
    assert native.__dict__ == before_state


@pytest.mark.parametrize(
    "key,value",
    [
        ("namespace", "Invalid namespace"),
        ("stratz_token", "secret-canary\n"),
        ("stratz_token", "密钥-canary"),
        ("timeout_seconds", True),
        ("timeout_seconds", 0),
        ("timeout_seconds", 61),
        ("timeout_seconds", float("nan")),
        ("reply_mode", "json"),
        ("subscriptions_enabled", 1),
        ("subscription_interval_seconds", 59),
        ("subscription_interval_seconds", 86401),
        ("daily_report_hour", -1),
        ("daily_report_hour", 24),
        ("illustration_path", "invalid\npath"),
        ("asset_download_mode", "always"),
        ("asset_proxy", "socks5://host:123"),
        ("asset_proxy", "https://host"),
        ("asset_proxy", "http://host:99999"),
        ("asset_proxy", "https://host:123/path"),
        ("asset_proxy", "https://host:123?secret-canary"),
        ("platforms", {}),
        ("platforms", "[]"),
        ("platforms", "{}"),
        ("platforms", '{"onebot":"QQ"}'),
        ("platforms", '{"":"qq"}'),
        ("platforms", '{"onebot":6}'),
        ("unknown", "secret-canary"),
    ],
)
def test_native_api_rejects_invalid_writes_without_values_in_output(
    host_config, key, value, caplog
):
    host = host_config
    bridge = host.module.register_config(host.data)
    before = host.native.read_bytes()
    snapshot = bridge.snapshot()
    assert bridge.native.set_config(key, value) is False
    assert bridge.snapshot() == snapshot
    assert host.native.read_bytes() == before
    assert "secret-canary" not in caplog.text


def test_valid_native_writes_persist_and_snapshot_is_detached(host_config):
    host = host_config
    bridge = host.module.register_config(host.data)
    values = {
        "namespace": "another-partition",
        "stratz_token": "synthetic-token",
        "timeout_seconds": 5,
        "reply_mode": "text",
        "illustration_path": "custom/images",
        "asset_download_mode": "manual",
        "asset_proxy": "http://user:secret-canary@host:123",
        "subscriptions_enabled": True,
        "subscription_interval_seconds": 600,
        "daily_report_hour": 22,
        "platforms": '{"onebot":"qq","synthetic":"test"}',
    }
    for key, value in values.items():
        assert bridge.native.set_config(key, value) is True
    persisted = json.loads(host.native.read_text("utf-8"))
    assert persisted["stratz_token"]["secret"] is True
    assert persisted["asset_proxy"]["secret"] is True
    assert persisted["timeout_seconds"]["data"] == 5.0
    snapshot = bridge.snapshot()
    assert snapshot["platforms"] == {"onebot": "qq", "synthetic": "test"}
    snapshot["platforms"]["onebot"] = "modified"
    assert bridge.snapshot()["platforms"]["onebot"] == "qq"
    assert host.module.register_config(host.data).snapshot()["stratz_token"] == "synthetic-token"


def test_reload_reuses_base_singleton_and_binds_fresh_validator(host_config):
    host = host_config
    first = host.module.register_config(host.data)
    module = host.load("synthetic_reloaded_host_config")
    second = module.register_config(host.data)
    assert second.native is first.native
    assert second is not first
    assert second.native.set_config.__self__ is second
    assert second.native.set_config("timeout_seconds", 2) is True
    assert first.snapshot()["timeout_seconds"] == 2.0


def test_structurally_valid_semantic_error_remains_visible_for_correction(host_config):
    host = host_config
    values = valid_native(host)
    values["daily_report_hour"]["data"] = 99
    host.native.write_text(json.dumps(values), "utf-8")
    bridge = host.module.register_config(host.data)
    assert bridge.snapshot()["daily_report_hour"] == 99
    assert bridge.native.set_config("daily_report_hour", 9) is True
    assert bridge.snapshot()["daily_report_hour"] == 9


@pytest.mark.parametrize("existing", [False, True])
def test_registration_io_failure_rolls_back_only_own_registry(host_config, monkeypatch, existing):
    host = host_config
    previous = host.module.register_config(host.data) if existing else None
    host.registry["OtherPlugin"] = other = object()
    previous_state = dict(previous.native.__dict__) if previous else None

    def fail(instance):
        raise OSError("synthetic-write-failure")

    native_class = sys.modules["gsuid_core.utils.plugins_config.gs_config"].StringConfig
    monkeypatch.setattr(native_class, "write_config", fail)
    with pytest.raises(host.module.ConfigBridgeError):
        host.module.register_config(host.data)
    assert host.registry["OtherPlugin"] is other
    if previous:
        assert host.registry["Dota2UID"] is previous.native
        assert previous.native.__dict__ == previous_state
    else:
        assert "Dota2UID" not in host.registry


def test_snapshot_reports_fixed_error_for_in_memory_wrong_type(host_config):
    host = host_config
    bridge = host.module.register_config(host.data)
    bridge.native.config["stratz_token"].data = {"secret-canary": "value"}
    with pytest.raises(host.module.ConfigBridgeError, match="^invalid_host_config$"):
        bridge.snapshot()


def test_write_io_failure_restores_previous_memory_value(host_config, monkeypatch):
    host = host_config
    bridge = host.module.register_config(host.data)
    before = deepcopy(bridge.snapshot())
    raw = host.native.read_bytes()

    def fail():
        raise OSError("synthetic-write-failure")

    monkeypatch.setattr(bridge.native, "write_config", fail)
    assert bridge.native.set_config("stratz_token", "synthetic-token") is False
    assert bridge.snapshot() == before
    assert host.native.read_bytes() == raw
