"""Explicit local configuration; importing the adapter performs no I/O."""

import math
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType


class ConfigurationError(Exception):
    def __init__(self) -> None:
        super().__init__("Dota2UID configuration is missing or invalid")


def identifier(value: str) -> bool:
    return re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", value) is not None


@dataclass(frozen=True)
class Config:
    namespace: str
    token: str = field(repr=False)
    database: Path = field(repr=False)
    platforms: Mapping[str, str] = field(repr=False)
    timeout_seconds: float = 10

    def __post_init__(self) -> None:
        if (
            not identifier(self.namespace)
            or not self.token
            or not self.token.isascii()
            or any(not 33 <= ord(char) <= 126 for char in self.token)
            or not self.database.is_absolute()
            or not self.platforms
            or any(not key or not identifier(value) for key, value in self.platforms.items())
            or isinstance(self.timeout_seconds, bool)
            or not 0 < self.timeout_seconds <= 60
            or not math.isfinite(self.timeout_seconds)
        ):
            raise ConfigurationError()
        object.__setattr__(self, "platforms", MappingProxyType(dict(self.platforms)))


def load_config(path: Path) -> Config:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8-sig"))
        if set(raw) != {"namespace", "stratz_token", "timeout_seconds", "platforms"}:
            raise ConfigurationError()
        namespace, token, timeout, platforms = (
            raw["namespace"],
            raw["stratz_token"],
            raw["timeout_seconds"],
            raw["platforms"],
        )
        if (
            not isinstance(namespace, str)
            or not isinstance(token, str)
            or not isinstance(timeout, (int, float))
            or isinstance(timeout, bool)
            or not isinstance(platforms, dict)
            or any(not isinstance(k, str) or not isinstance(v, str) for k, v in platforms.items())
        ):
            raise ConfigurationError()
        return Config(
            namespace, token, path.resolve().parent / "bindings.sqlite3", platforms, timeout
        )
    except (OSError, ValueError):
        raise ConfigurationError() from None
