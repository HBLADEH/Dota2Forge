"""Small host-neutral command grammar; AstrBot event conversion stays outside Core."""

import re
from dataclasses import dataclass
from enum import StrEnum

from dota2forge_core import AccountId, MatchId, parse_account_id, parse_match_id
from dota2forge_core.domain.hero_items import normalize_hero_name


class AstrCommandError(Exception):
    def __init__(self) -> None:
        super().__init__("Invalid Dota2Forge AstrBot command")


class AstrAction(StrEnum):
    HELP = "do帮助"
    MENU = "do菜单"
    BIND = "do绑定"
    REBIND = "do改绑"
    BINDING = "do账号"
    UNBIND = "do解绑"
    PLAYER = "do查询"
    RECENT = "do战绩"
    MATCH = "do比赛"
    ITEMS = "do出装"


@dataclass(frozen=True, slots=True)
class AstrCommand:
    action: AstrAction
    account: AccountId | None = None
    limit: int = 10
    match_id: MatchId | None = None
    match_index: int | None = None
    page: int | None = None
    hero_name: str | None = None


def parse_command(keyword: str, text: str) -> AstrCommand:
    if keyword.startswith("do") and keyword.endswith("出装") and keyword != "do出装":
        if text.strip():
            raise AstrCommandError()
        text, keyword = keyword[2:-2], "do出装"
    try:
        action = AstrAction(keyword)
    except ValueError:
        raise AstrCommandError() from None
    tokens = text.split()
    if action == AstrAction.ITEMS:
        try:
            normalize_hero_name(text)
        except ValueError:
            raise AstrCommandError() from None
        return AstrCommand(action, hero_name=text.strip())
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
        selected = re.fullmatch(r"第([1-9][0-9]{0,2})场", tokens[0])
        if selected is not None:
            if int(selected[1]) > 100:
                raise AstrCommandError()
            return AstrCommand(action, match_index=int(selected[1]))
        try:
            return AstrCommand(action, match_id=parse_match_id(tokens[0]))
        except ValueError:
            raise AstrCommandError() from None
    if len(tokens) == 1 and (selected := re.fullmatch(r"第([1-9][0-9]?)页", tokens[0])):
        if int(selected[1]) > 20:
            raise AstrCommandError()
        return AstrCommand(action, page=int(selected[1]))
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
