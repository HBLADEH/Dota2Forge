"""Validate the explicit host configuration without reading environment variables."""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from dota2forge_core import PlatformIdentity, ValidationError


class ConfigurationError(Exception):
    def __init__(self) -> None:
        super().__init__("Dota2Forge AstrBot configuration is missing or invalid")


class ConfigurationPending(ConfigurationError):
    """The otherwise valid host configuration still needs a local STRATZ Token."""


@dataclass(frozen=True, repr=False)
class Config:
    namespace: str
    token: str = field(repr=False)
    database: Path = field(repr=False)
    timeout_seconds: float = 10
    reply_mode: str = "image"
    subscriptions_enabled: bool = False
    subscription_interval_seconds: int = 300
    daily_report_hour: int = 9
    illustration_path: Path | None = field(default=None, repr=False)


def load_config(raw: Mapping[str, object], data_dir: Path) -> Config:
    namespace = raw.get("namespace", "astrbot-local")
    token = raw.get("stratz_token", "")
    timeout = raw.get("timeout_seconds", 10)
    mode = raw.get("reply_mode", "image")
    enabled = raw.get("subscriptions_enabled", False)
    interval = raw.get("subscription_interval_seconds", 300)
    daily_hour = raw.get("daily_report_hour", 9)
    illustration = raw.get("illustration_path", "")
    if (
        set(raw)
        - {
            "namespace",
            "stratz_token",
            "timeout_seconds",
            "reply_mode",
            "subscriptions_enabled",
            "subscription_interval_seconds",
            "daily_report_hour",
            "illustration_path",
        }
        or not isinstance(namespace, str)
        or not isinstance(token, str)
        or not token.isascii()
        or any(not 33 <= ord(char) <= 126 for char in token)
        or type(timeout) not in {int, float}
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or not 0 < timeout <= 60
        or mode not in ("image", "text")
        or type(enabled) is not bool
        or not isinstance(interval, int)
        or isinstance(interval, bool)
        or not 60 <= interval <= 86400
        or not isinstance(daily_hour, int)
        or isinstance(daily_hour, bool)
        or not 0 <= daily_hour <= 23
        or not isinstance(illustration, str)
        or len(illustration) > 2048
        or any(ord(char) < 32 for char in illustration)
    ):
        raise ConfigurationError()
    try:
        PlatformIdentity(namespace, "astrbot", "validation", "validation")
    except ValidationError:
        raise ConfigurationError() from None
    if not token:
        raise ConfigurationPending()
    return Config(
        namespace,
        token,
        data_dir.resolve() / "bindings.sqlite3",
        float(timeout),
        str(mode),
        enabled,
        interval,
        daily_hour,
        (data_dir.resolve() / illustration).resolve() if illustration else None,
    )
