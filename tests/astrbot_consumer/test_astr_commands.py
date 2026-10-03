"""AstrBot-neutral command parsing and error boundaries."""

import pytest
from astrbot_plugin_dota2forge.commands import (
    AstrAction,
    AstrCommandError,
    parse_command,
)
from dota2forge_core import AccountId, MatchId


@pytest.mark.parametrize(
    ("keyword", "text", "action", "account", "limit", "match"),
    [
        ("dota帮助", "", AstrAction.HELP, None, 10, None),
        ("dota菜单", "", AstrAction.MENU, None, 10, None),
        ("dota绑定", "123", AstrAction.BIND, AccountId(123), 10, None),
        ("dota绑定", "76561197960265851", AstrAction.BIND, AccountId(123), 10, None),
        ("dota改绑", "123", AstrAction.REBIND, AccountId(123), 10, None),
        ("dota玩家", "123", AstrAction.PLAYER, AccountId(123), 10, None),
        ("dota战绩", "100", AstrAction.RECENT, None, 100, None),
        ("dota战绩", "123 2", AstrAction.RECENT, AccountId(123), 2, None),
        ("dota比赛", "7000000001", AstrAction.MATCH, None, 10, MatchId(7000000001)),
    ],
)
def test_astr_command_grammar(keyword, text, action, account, limit, match):
    result = parse_command(keyword, text)
    assert result.action == action
    assert result.account == account and result.limit == limit and result.match_id == match


@pytest.mark.parametrize(
    ("keyword", "text"),
    [
        ("unknown", ""),
        ("dota帮助", "1"),
        ("dota绑定", "01"),
        ("dota玩家", "not-an-id"),
        ("dota战绩", "0"),
        ("dota战绩", "101"),
        ("dota战绩", "123 2 3"),
        ("dota比赛", "0"),
    ],
)
def test_astr_invalid_commands_do_not_guess(keyword, text):
    with pytest.raises(AstrCommandError):
        parse_command(keyword, text)


def test_astrbot_recent_selection_commands_are_strict():
    assert parse_command("dota比赛", "第1场").match_index == 1
    assert parse_command("dota战绩", "第2页").page == 2
    for text in ("第0场", "第101场", "第0页", "第21页", "第01场", "第1.0场"):
        with pytest.raises(AstrCommandError):
            parse_command("dota比赛" if "场" in text else "dota战绩", text)
