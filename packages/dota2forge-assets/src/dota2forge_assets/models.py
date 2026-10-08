"""Immutable, credential-free public state and finite resource budgets."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType

KINDS = ("heroes", "items", "ranks", "rank_stars", "ui", "decor")


class AssetError(Exception):
    def __init__(self, code: str = "invalid") -> None:
        self.code = code
        super().__init__(f"Dota2Forge asset operation failed ({code})")


@dataclass(frozen=True, slots=True)
class AssetLimits:
    workers: int = 4
    response_bytes: int = 4 * 1024 * 1024
    manifest_bytes: int = 1024 * 1024
    pixels: int = 2048 * 2048
    root_bytes: int = 256 * 1024 * 1024
    request_seconds: float = 30
    job_seconds: float = 600
    retries: int = 2
    auto_cooldown: float = 1800
    manual_cooldown: float = 30

    def __post_init__(self) -> None:
        import math

        for name in ("workers", "response_bytes", "manifest_bytes", "pixels", "root_bytes"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise AssetError("configuration")
        if type(self.retries) is not int or not 0 <= self.retries <= 2 or self.workers > 4:
            raise AssetError("configuration")
        for name in ("request_seconds", "job_seconds", "auto_cooldown", "manual_cooldown"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise AssetError("configuration")


@dataclass(frozen=True, slots=True)
class AssetCounts:
    available: int = 0
    missing_404: int = 0
    failed: int = 0
    reused: int = 0


@dataclass(frozen=True, slots=True)
class AssetStatus:
    state: str = "checking"
    generation: str | None = None
    counts: Mapping[str, AssetCounts] = field(default_factory=dict)
    completed: int = 0
    total: int | None = None
    downloaded_bytes: int = 0
    last_attempt: datetime | None = None
    last_success: datetime | None = None
    error: str | None = None
    retry_after_seconds: int = 0
    task_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "counts", MappingProxyType(dict(self.counts)))


def utc_now() -> datetime:
    return datetime.now(UTC)


def aware_time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AssetError("clock")
    return value.astimezone(UTC)
