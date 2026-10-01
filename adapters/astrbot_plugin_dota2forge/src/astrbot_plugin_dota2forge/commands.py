"""Small host-neutral command grammar; AstrBot event conversion stays outside Core."""

import re
from dataclasses import dataclass
from enum import StrEnum

from dota2forge_core import AccountId, MatchId, parse_account_id, parse_match_id


class AstrCommandError(Exception):
    def __init__(self) -> None:
        super().__init__("Invalid Dota2Forge AstrBot command")


class AstrAction(StrEnum):
    HELP = "dota帮助"
    MENU = "dota菜单"
    BIND = "dota绑定"
    REBIND = "dota改绑"
    BINDING = "dota账号"
    UNBIND = "dota解绑"
    PLAYER = "dota玩家"
    RECENT = "dota战绩"
    MATCH = "dota比赛"


@dataclass(frozen=True, slots=True)
class AstrCommand:
    action: AstrAction
    account: AccountId | None = None
    limit: int = 10
    match_id: MatchId | None = None


def parse_command(keyword: str, text: str) -> AstrCommand:
    try:
        action = AstrAction(keyword)
    except ValueError:
        raise AstrCommandError() from None
    tokens = text.split()
    if action in {AstrAction.HELP, AstrAction.MENU, AstrAction.BINDING, AstrAction.UNBIND}:
        if tokens:
            raise AstrCommandError()
        return AstrCommand(action)
    if action in {AstrAction.BIND, AstrAction.REBIND}:
        if len(tokens) != 1:
            raise AstrCommandError()
        try:
            return AstrCommand(action, account=parse_account_id(tokens[0]))
        except ValueError:
            raise AstrCommandError() from None
    if action == AstrAction.PLAYER:
        if len(tokens) > 1:
            raise AstrCommandError()
        try:
            return AstrCommand(action, account=parse_account_id(tokens[0]) if tokens else None)
        except ValueError:
            raise AstrCommandError() from None
    if action == AstrAction.MATCH:
        if len(tokens) != 1:
            raise AstrCommandError()
        try:
            return AstrCommand(action, match_id=parse_match_id(tokens[0]))
        except ValueError:
            raise AstrCommandError() from None
    if len(tokens) > 2:
        raise AstrCommandError()
    value = tokens[-1] if tokens else "10"
    if not re.fullmatch(r"[1-9][0-9]{0,2}", value) or not 1 <= int(value) <= 100:
        raise AstrCommandError()
    account = None
    if len(tokens) == 2:
        try:
            account = parse_account_id(tokens[0])
        except ValueError:
            raise AstrCommandError() from None
    return AstrCommand(action, account=account, limit=int(value))
