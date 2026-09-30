"""Explicit account and platform identities; no implicit integer coercion."""

import re
from dataclasses import dataclass, field

from .errors import InvalidIdentityError, InvalidSteamIdError

STEAM_ID64_BASE = 76561197960265728
# Zero and the Dota anonymous-player sentinel (uint32 max) are not bindable.
MAX_ACCOUNT_ID = (1 << 32) - 2


@dataclass(frozen=True, slots=True)
class AccountId:
    value: int = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.value) is not int or not 1 <= self.value <= MAX_ACCOUNT_ID:
            raise InvalidSteamIdError()

    def to_steam_id64(self) -> "SteamId64":
        return SteamId64(STEAM_ID64_BASE + self.value)


@dataclass(frozen=True, slots=True)
class SteamId64:
    value: int = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.value) is not int
            or not STEAM_ID64_BASE < self.value <= STEAM_ID64_BASE + MAX_ACCOUNT_ID
        ):
            raise InvalidSteamIdError()

    def to_account_id(self) -> AccountId:
        return AccountId(self.value - STEAM_ID64_BASE)


def parse_account_id(value: int | str) -> AccountId:
    """Accept canonical decimal account IDs or public individual SteamID64s.

    Steam2/Steam3 text, vanity names, URLs, spaces, signs and leading zeroes
    require an explicit adapter parser and are intentionally not guessed here.
    """
    if isinstance(value, str):
        if not re.fullmatch(r"[1-9][0-9]{0,16}", value):
            raise InvalidSteamIdError()
        number = int(value)
    elif type(value) is int:
        number = value
    else:
        raise InvalidSteamIdError()
    if number <= MAX_ACCOUNT_ID:
        return AccountId(number)
    return SteamId64(number).to_account_id()


@dataclass(frozen=True, slots=True)
class PlatformIdentity:
    """Created from the authenticated host context, never from command arguments.

    Namespace identifies the adapter/deployment. Bot and user IDs remain opaque,
    case-sensitive strings; separate SQL columns prevent delimiter collisions.
    """

    namespace: str
    platform: str
    bot_id: str = field(repr=False)
    user_id: str = field(repr=False)

    def __post_init__(self) -> None:
        for token in (self.namespace, self.platform):
            if not isinstance(token, str) or not re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", token):
                raise InvalidIdentityError()
        for opaque_id in (self.bot_id, self.user_id):
            if (
                not isinstance(opaque_id, str)
                or not 1 <= len(opaque_id) <= 128
                or not opaque_id.isprintable()
                or any(character.isspace() for character in opaque_id)
            ):
                raise InvalidIdentityError()
