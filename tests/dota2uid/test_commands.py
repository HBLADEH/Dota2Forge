from dataclasses import replace

import pytest
from dota2forge_core import AccountId, InvalidIdentityError, InvalidSteamIdError
from Dota2UID.commands import Action, CommandError, parse_command
from Dota2UID.config import ConfigurationError, load_config


@pytest.mark.parametrize(
    ("keyword", "text", "account", "limit"),
    [
        ("do帮助", "", None, 10),
        ("do账号", "", None, 10),
        ("do解绑", "", None, 10),
        ("do绑定", "123", AccountId(123), 10),
        ("do改绑", "123", AccountId(123), 10),
        ("do绑定", str(AccountId(123).to_steam_id64().value), AccountId(123), 10),
        ("do查询", "", None, 10),
        ("do查询", "123", AccountId(123), 10),
        ("do战绩", "", None, 10),
        ("do战绩", "1", None, 1),
        ("do战绩", "100", None, 100),
        ("do战绩", "123 10", AccountId(123), 10),
    ],
)
def test_exact_command_grammar(keyword, text, account, limit):
    result = parse_command(keyword, text)
    assert result.action == Action(keyword) and result.account == account and result.limit == limit


@pytest.mark.parametrize("keyword", ["dota帮助", "dota玩家", "dota战绩", "do玩家"])
def test_replaced_command_names_are_no_longer_accepted(keyword):
    with pytest.raises(CommandError):
        parse_command(keyword, "")


@pytest.mark.parametrize(
    ("keyword", "text"),
    [
        ("绑定", "123"),
        ("do帮助", "123"),
        ("do账号", "123"),
        ("do解绑", "123"),
        ("do绑定", ""),
        ("do绑定", "123 456"),
        ("do查询", "123 456"),
        ("do战绩", "123 10 20"),
        ("do战绩", "0"),
        ("do战绩", "-1"),
        ("do战绩", "101"),
        ("do战绩", "01"),
        ("do战绩", "１０"),
        ("do战绩", "1.0"),
    ],
)
def test_invalid_command_does_not_guess_input(keyword, text):
    with pytest.raises(CommandError):
        parse_command(keyword, text)


@pytest.mark.parametrize(
    "text", ["0", "0123", "+123", "https://steamcommunity.com/profiles/123", "@x"]
)
def test_bind_uses_core_strict_id_parser(text):
    with pytest.raises(InvalidSteamIdError):
        parse_command("do绑定", text)


@pytest.mark.parametrize(
    "changes",
    [
        {"platform_key": "unknown"},
        {"bot_self_id": ""},
        {"user_id": ""},
        {"connection_id": None},
        {"connection_id": ""},
        {"mentioned": True},
    ],
)
def test_identity_requires_trusted_complete_host_fields(config_path, caller, changes):
    with pytest.raises(InvalidIdentityError):
        replace(caller, **changes).identity(load_config(config_path))


def test_identity_separates_deployment_platform_bot_user(config_path, caller):
    config = load_config(config_path)
    identity = caller.identity(config)
    assert (
        len(
            {
                identity,
                replace(caller, platform_key="telegram").identity(config),
                replace(caller, bot_self_id="other-bot").identity(config),
                replace(caller, user_id="other-user").identity(config),
                caller.identity(replace(config, namespace="other-deployment")),
            }
        )
        == 5
    )
    assert "synthetic-user" not in repr(caller)
    assert "synthetic-token" not in repr(config)
    assert replace(caller, connection_id="reconnected").identity(config) == identity


@pytest.mark.parametrize(
    "contents",
    [
        "",
        "[broken",
        'stratz_token="synthetic-token"',
        'namespace="UPPER"\nstratz_token="synthetic-token"\ntimeout_seconds=2\n[platforms]\nonebot="qq"',
        'namespace="demo"\nstratz_token=""\ntimeout_seconds=2\n[platforms]\nonebot="qq"',
        'namespace="demo"\nstratz_token=1\ntimeout_seconds=2\n[platforms]\nonebot="qq"',
        'namespace="demo"\nstratz_token="synthetic-token"\ntimeout_seconds=true\n[platforms]\nonebot="qq"',
        'namespace="demo"\nstratz_token="synthetic-token"\ntimeout_seconds=inf\n[platforms]\nonebot="qq"',
        'namespace="demo"\nstratz_token="synthetic-token"\ntimeout_seconds=61\n[platforms]\nonebot="qq"',
        'namespace="demo"\nstratz_token="synthetic-token"\ntimeout_seconds=2\n[platforms]\nonebot=1',
        'namespace="demo"\nstratz_token="synthetic-token"\ntimeout_seconds=2\n[platforms]',
    ],
)
def test_invalid_config_fails_with_fixed_message(config_path, contents):
    config_path.write_text(contents, encoding="utf-8")
    with pytest.raises(ConfigurationError) as error:
        load_config(config_path)
    assert "synthetic-token" not in str(error.value)


def test_missing_config_is_not_silently_defaulted(tmp_path):
    with pytest.raises(ConfigurationError):
        load_config(tmp_path / "missing.toml")
