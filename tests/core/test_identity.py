from dataclasses import FrozenInstanceError, replace

import pytest
from dota2forge_core import (
    AccountId,
    InvalidIdentityError,
    InvalidSteamIdError,
    PlatformIdentity,
    SteamId64,
    parse_account_id,
)
from dota2forge_core.domain.identity import MAX_ACCOUNT_ID, STEAM_ID64_BASE


@pytest.mark.parametrize("value", [1, 123, MAX_ACCOUNT_ID])
def test_ids_round_trip_and_parse_both_decimal_forms(value):
    account = AccountId(value)
    steam = account.to_steam_id64()
    assert steam.value == STEAM_ID64_BASE + value
    assert steam.to_account_id() == account
    for raw in (value, str(value), steam.value, str(steam.value)):
        assert parse_account_id(raw) == account


@pytest.mark.parametrize(
    "raw",
    [
        0,
        -1,
        True,
        False,
        1.0,
        None,
        [],
        {},
        "",
        "0",
        "01",
        "+1",
        "-1",
        "1.0",
        "1e3",
        " 123",
        "123 ",
        "123\n",
        "１２３",
        "١٢٣",
        "9" * 5000,
        "STEAM_0:1:61",
        "[U:1:123]",
        "https://steamcommunity.com/id/synthetic",
        "synthetic-name",
        4294967295,
        4294967296,
        STEAM_ID64_BASE,
        STEAM_ID64_BASE - 1,
        STEAM_ID64_BASE + (1 << 32) - 1,
        STEAM_ID64_BASE + (1 << 32),
        (1 << 64) - 1,
    ],
    ids=lambda value: str(value)[:60],
)
def test_invalid_id_inputs_are_rejected_without_echoing(raw):
    with pytest.raises(InvalidSteamIdError) as caught:
        parse_account_id(raw)
    assert str(caught.value) == str(InvalidSteamIdError())


@pytest.mark.parametrize("value", [True, 1.0, "123", 0, -1, 4294967295])
def test_account_constructor_rejects_coercion_and_anonymous_values(value):
    with pytest.raises(InvalidSteamIdError):
        AccountId(value)


@pytest.mark.parametrize("value", [True, "76561197960265851", 1.0, 123, 2**64])
def test_steam64_constructor_is_distinct_from_account_id(value):
    with pytest.raises(InvalidSteamIdError):
        SteamId64(value)


@pytest.mark.parametrize("field", ["namespace", "platform", "bot_id", "user_id"])
@pytest.mark.parametrize("invalid", [None, 123, "", " ", "a b", "a\nb", "a\x00b", "a" * 129])
def test_identity_rejects_invalid_components(identity, field, invalid):
    with pytest.raises(InvalidIdentityError):
        replace(identity, **{field: invalid})


def test_identity_is_case_sensitive_immutable_and_unambiguous(identity):
    assert replace(identity, user_id="Alice") != replace(identity, user_id="alice")
    assert replace(identity, bot_id="a:b", user_id="c") != replace(
        identity, bot_id="a", user_id="b:c"
    )
    assert PlatformIdentity("adapter-one", "test-chat", "bot-1", "用户-1").user_id == "用户-1"
    with pytest.raises(FrozenInstanceError):
        identity.user_id = "other"
    with pytest.raises(InvalidIdentityError):
        replace(identity, namespace="UPPERCASE")
    assert identity.user_id not in repr(identity)
    assert identity.bot_id not in repr(identity)
    assert str(AccountId(123).to_steam_id64().value) not in repr(AccountId(123).to_steam_id64())
