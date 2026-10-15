"""Source evidence for native chat tools, without conversation or platform identity."""

from dataclasses import dataclass
from enum import StrEnum

from .analysis import MatchAnalysis
from .errors import DataSource, ValidationError
from .match_detail import MatchDetail


class ReviewTopic(StrEnum):
    OVERVIEW = "overview"
    ECONOMY = "economy"
    ITEMS = "items"
    LANING = "laning"
    TEAM = "team"


class ReviewChartKind(StrEnum):
    ECONOMY = "economy"
    TEAM_ADVANTAGE = "team_advantage"
    ITEMS = "items"


@dataclass(frozen=True, slots=True)
class ReviewEvidence:
    detail: MatchDetail
    analysis: MatchAnalysis | None
    target_slot: int | None = None
    analysis_error: str | None = None
    source_attempts: tuple[tuple[DataSource, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.detail, MatchDetail):
            raise ValidationError("Expected match evidence")
        if self.analysis is not None and (
            not isinstance(self.analysis, MatchAnalysis)
            or self.analysis.match_id != self.detail.match_id
            or self.analysis.metadata.source != self.detail.metadata.source
        ):
            raise ValidationError("Incompatible match evidence")
        if self.target_slot is not None and (
            type(self.target_slot) is not int
            or not any(p.player_slot == self.target_slot for p in self.detail.players or ())
        ):
            raise ValidationError("Unknown review perspective")
        if self.analysis_error is not None and self.analysis_error not in {
            "not_found",
            "private",
            "rate_limited",
            "timeout",
            "unavailable",
            "authentication",
            "invalid_response",
        }:
            raise ValidationError("Invalid evidence failure")
        if (
            not isinstance(self.source_attempts, tuple)
            or len(self.source_attempts) > 2
            or any(
                not isinstance(v, tuple)
                or len(v) != 2
                or not isinstance(v[0], DataSource)
                or v[0] not in (DataSource.STRATZ, DataSource.OPENDOTA)
                or v[1]
                not in {
                    "not_found",
                    "timeout",
                    "unavailable",
                    "rate_limited",
                    "basic_only",
                    "private",
                    "authentication",
                    "invalid_response",
                }
                for v in self.source_attempts
            )
        ):
            raise ValidationError("Invalid review source attempts")


@dataclass(frozen=True, slots=True)
class ReviewChartRequest:
    kind: ReviewChartKind
    start_seconds: int = 0
    end_seconds: int = 3600

    def __post_init__(self) -> None:
        if (
            not isinstance(self.kind, ReviewChartKind)
            or type(self.start_seconds) is not int
            or type(self.end_seconds) is not int
            or not -600 <= self.start_seconds < self.end_seconds <= 21600
        ):
            raise ValidationError("Expected a bounded chart kind/time range")
