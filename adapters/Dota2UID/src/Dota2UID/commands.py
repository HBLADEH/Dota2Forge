"""A small command grammar and identity mapping from trusted host event fields."""

import re
from dataclasses import dataclass, field
from enum import StrEnum

from dota2forge_core import (
    AccountId,
    InvalidIdentityError,
    MatchId,
    PlatformIdentity,
    parse_account_id,
    parse_match_id,
)

from .config import Config


class CommandError(Exception):
    def __init__(self) -> None:
        super().__init__("Invalid Dota2UID command")


class Action(StrEnum):
    HELP = "dota帮助"
    MENU = "dota菜单"
    BIND = "dota绑定"
    REBIND = "dota改绑"
    BINDING = "dota账号"
    UNBIND = "dota解绑"
    PLAYER = "dota玩家"
    RECENT = "dota战绩"
    MATCH = "dota比赛"


@dataclass(frozen=True, repr=False)
class Caller:
    platform_key: str
    bot_self_id: str
    user_id: str
    connection_id: str | None
    mentioned: bool = False
    conversation_kind: str | None = None
    conversation_id: str | None = None
    is_admin: bool = False

    def identity(self, config: Config) -> PlatformIdentity:
        if not self.connection_id or self.platform_key not in config.platforms or self.mentioned:
            raise InvalidIdentityError()
        return PlatformIdentity(
            config.namespace, config.platforms[self.platform_key], self.bot_self_id, self.user_id
        )


@dataclass(frozen=True)
class Command:
    action: Action
    account: AccountId | None = field(default=None, repr=False)
    limit: int = 10
    match_id: MatchId | None = None
    match_index: int | None = None
    page: int | None = None


def parse_command(keyword: str, text: str) -> Command:
    try:
        action = Action(keyword)
    except ValueError:
        raise CommandError() from None
    tokens = text.split()
    if action in {Action.HELP, Action.MENU, Action.BINDING, Action.UNBIND}:
        if tokens:
            raise CommandError()
        return Command(action)
    if action in {Action.BIND, Action.REBIND}:
        if len(tokens) != 1:
            raise CommandError()
        return Command(action, parse_account_id(tokens[0]))
    if action == Action.PLAYER:
        if len(tokens) > 1:
            raise CommandError()
        return Command(action, parse_account_id(tokens[0]) if tokens else None)
    if action == Action.MATCH:
        if len(tokens) != 1:
            raise CommandError()
        selected = re.fullmatch(r"第([1-9][0-9]{0,2})场", tokens[0])
        if selected is not None:
            index = int(selected[1])
            if index > 100:
                raise CommandError()
            return Command(action, match_index=index)
        try:
            match_id = parse_match_id(tokens[0])
        except ValueError:
            raise CommandError() from None
        return Command(action, match_id=match_id)
    if len(tokens) == 1 and (selected := re.fullmatch(r"第([1-9][0-9]?)页", tokens[0])):
        page = int(selected[1])
        if page > 20:
            raise CommandError()
        return Command(action, page=page)
    if len(tokens) > 2:
        raise CommandError()
    # A single argument is a count; an explicit account uses "account count".
    if not tokens:
        return Command(action)
    count = tokens[-1]
    if not count.isascii() or not count.isdecimal() or len(count) > 3 or count.startswith("0"):
        raise CommandError()
    limit = int(count)
    if not 1 <= limit <= 100:
        raise CommandError()
    return Command(action, parse_account_id(tokens[0]) if len(tokens) == 2 else None, limit)
