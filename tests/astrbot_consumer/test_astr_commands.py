"""AstrBot-neutral command parsing and error boundaries."""

import pytest
from astrbot_plugin_dota2forge.commands import (
    AstrAction,
    AstrCommandError,
    parse_command,
)
from dota2forge_core import AccountId, MatchId


@pytest.mark.parametrize("keyword", ["dota帮助", "dota玩家", "dota战绩", "do玩家"])
def test_replaced_command_names_are_no_longer_accepted(keyword):
    with pytest.raises(AstrCommandError):
        parse_command(keyword, "")


@pytest.mark.parametrize(
    ("keyword", "text", "action", "account", "limit", "match"),
    [
        ("do帮助", "", AstrAction.HELP, None, 10, None),
        ("do菜单", "", AstrAction.MENU, None, 10, None),
        ("do绑定", "123", AstrAction.BIND, AccountId(123), 10, None),
        ("do绑定", "76561197960265851", AstrAction.BIND, AccountId(123), 10, None),
        ("do改绑", "123", AstrAction.REBIND, AccountId(123), 10, None),
        ("do查询", "123", AstrAction.PLAYER, AccountId(123), 10, None),
        ("do战绩", "100", AstrAction.RECENT, None, 100, None),
        ("do战绩", "123 2", AstrAction.RECENT, AccountId(123), 2, None),
        ("do比赛", "7000000001", AstrAction.MATCH, None, 10, MatchId(7000000001)),
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
        ("do帮助", "1"),
        ("do绑定", "01"),
        ("do查询", "not-an-id"),
        ("do战绩", "0"),
        ("do战绩", "101"),
        ("do战绩", "123 2 3"),
        ("do比赛", "0"),
    ],
)
def test_astr_invalid_commands_do_not_guess(keyword, text):
    with pytest.raises(AstrCommandError):
        parse_command(keyword, text)


def test_astrbot_recent_selection_commands_are_strict():
    assert parse_command("do比赛", "第1场").match_index == 1
    assert parse_command("do战绩", "第2页").page == 2
    for text in ("第0场", "第101场", "第0页", "第21页", "第01场", "第1.0场"):
        with pytest.raises(AstrCommandError):
            parse_command("do比赛" if "场" in text else "do战绩", text)
