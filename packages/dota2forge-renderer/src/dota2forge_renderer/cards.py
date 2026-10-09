"""Immutable card inputs and bounded PNG outputs; no platform objects."""

from dataclasses import dataclass, field

from dota2forge_core import (
    AccountId,
    HeroItemStatistics,
    MatchDetail,
    MatchReport,
    PlayerProfile,
    RecentMatches,
)

WIDTH = 780
MAX_HEIGHT = 1800
REPORT_WIDTH = 1600
MAX_REPORT_HEIGHT = 3200
MAX_BYTES = 2 * 1024 * 1024
PER_PAGE = 5
DETAIL_PER_PAGE = 3


class RenderError(Exception):
    def __init__(self) -> None:
        super().__init__("Dota2Forge image rendering is unavailable")


@dataclass(frozen=True, slots=True)
class ImageArtifact:
    data: bytes = field(repr=False)
    width: int
    height: int
    mime: str = "image/png"

    def __post_init__(self) -> None:
        if (
            type(self.data) is not bytes
            or not self.data.startswith(b"\x89PNG\r\n\x1a\n")
            or len(self.data) > MAX_BYTES
            or self.mime != "image/png"
            or type(self.width) is not int
            or self.width not in (WIDTH, REPORT_WIDTH)
            or type(self.height) is not int
            or not 1 <= self.height <= (MAX_HEIGHT if self.width == WIDTH else MAX_REPORT_HEIGHT)
        ):
            raise RenderError()


@dataclass(frozen=True, slots=True)
class MenuCard:
    include_admin: bool = False
    adapter_label: str = "Dota2UID"


@dataclass(frozen=True, slots=True)
class PlayerCard:
    player: PlayerProfile


@dataclass(frozen=True, slots=True)
class HeroItemsCard:
    statistics: HeroItemStatistics


@dataclass(frozen=True, slots=True)
class RecentMatchesCard:
    recent: RecentMatches
    page: int = 1


@dataclass(frozen=True, slots=True)
class StatusCard:
    message: str
    adapter_label: str = "Dota2UID"


@dataclass(frozen=True, slots=True)
class MatchDetailCard:
    detail: MatchDetail
    page: int = 1
    perspective: AccountId | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class MatchReportCard:
    report: MatchReport
    page: int = 1


type Card = (
    MenuCard
    | PlayerCard
    | HeroItemsCard
    | RecentMatchesCard
    | StatusCard
    | MatchDetailCard
    | MatchReportCard
)
