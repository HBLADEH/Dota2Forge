"""Explicit local configuration; importing the adapter performs no I/O."""

import json
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


class ConfigurationPending(ConfigurationError):
    """The otherwise valid configuration still needs a local STRATZ Token."""


def ensure_config(path: Path, *, token: str = "") -> None:
    """Explicit startup preparation; exclusive creation preserves existing configuration."""
    if path.is_dir():
        raise IsADirectoryError("Dota2UID configuration path must be a file")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(
                'namespace = "dota2uid-local"\nstratz_token = '
                + json.dumps(token)
                + '\ntimeout_seconds = 10\nreply_mode = "image"\nillustration_path = ""\n'
                "subscriptions_enabled = false\nsubscription_interval_seconds = 300\n"
                'daily_report_hour = 9\n\n[platforms]\nonebot = "qq"\nqq = "qq"\n'
                'telegram = "telegram"\n'
            )
    except FileExistsError:
        if not path.is_file():
            raise


def identifier(value: str) -> bool:
    return re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", value) is not None


@dataclass(frozen=True)
class Config:
    namespace: str
    token: str = field(repr=False)
    database: Path = field(repr=False)
    platforms: Mapping[str, str] = field(repr=False)
    timeout_seconds: float = 10
    reply_mode: str = "image"
    subscriptions_enabled: bool = False
    subscription_interval_seconds: int = 300
    daily_report_hour: int = 9
    illustration_path: Path | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if (
            not identifier(self.namespace)
            or not self.token.isascii()
            or any(not 33 <= ord(char) <= 126 for char in self.token)
            or not self.database.is_absolute()
            or not self.platforms
            or any(not key or not identifier(value) for key, value in self.platforms.items())
            or isinstance(self.timeout_seconds, bool)
            or not 0 < self.timeout_seconds <= 60
            or not math.isfinite(self.timeout_seconds)
            or self.reply_mode not in {"image", "text"}
            or type(self.subscriptions_enabled) is not bool
            or type(self.subscription_interval_seconds) is not int
            or not 60 <= self.subscription_interval_seconds <= 86400
            or type(self.daily_report_hour) is not int
            or not 0 <= self.daily_report_hour <= 23
            or (self.illustration_path is not None and not self.illustration_path.is_absolute())
        ):
            raise ConfigurationError()
        if not self.token:
            raise ConfigurationPending()
        object.__setattr__(self, "platforms", MappingProxyType(dict(self.platforms)))


def load_config(path: Path) -> Config:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8-sig"))
        if not {"namespace", "stratz_token", "timeout_seconds", "platforms"} <= set(raw) or (
            set(raw)
            - {
                "namespace",
                "stratz_token",
                "timeout_seconds",
                "platforms",
                "reply_mode",
                "subscriptions_enabled",
                "subscription_interval_seconds",
                "daily_report_hour",
                "illustration_path",
            }
        ):
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
        reply_mode = raw.get("reply_mode", "image")
        illustration = raw.get("illustration_path", "")
        if (
            not isinstance(reply_mode, str)
            or not isinstance(illustration, str)
            or len(illustration) > 2048
            or any(ord(char) < 32 for char in illustration)
        ):
            raise ConfigurationError()
        return Config(
            namespace,
            token,
            path.resolve().parent / "bindings.sqlite3",
            platforms,
            timeout,
            reply_mode,
            raw.get("subscriptions_enabled", False),
            raw.get("subscription_interval_seconds", 300),
            raw.get("daily_report_hour", 9),
            (path.resolve().parent / illustration).resolve() if illustration else None,
        )
    except (OSError, ValueError):
        raise ConfigurationError() from None
