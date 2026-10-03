"""Daily observations, not a claim of complete match history."""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from enum import StrEnum

from .errors import ValidationError
from .identity import AccountId
from .match_detail import MatchId
from .models import DataMetadata, MatchSummary

BEIJING = timezone(timedelta(hours=8), "UTC+08:00")


def report_bounds(report_date: date) -> tuple[datetime, datetime]:
    if type(report_date) is not date or not 1 < report_date.year < 9999:
        raise ValidationError("Expected a supported daily observation date")
    start = datetime.combine(report_date, time.min, BEIJING)
    return start, start + timedelta(days=1)


class DailyCoverage(StrEnum):
    EMPTY = "empty_observation"
    BOUNDED = "bounded_observation"
    WINDOW_SPANNED = "window_spanned"
    TRUNCATED = "window_truncated"


@dataclass(frozen=True, slots=True)
class DailyReport:
    account_id: AccountId = field(repr=False)
    report_date: date
    metadata: DataMetadata
    matches: tuple[MatchSummary, ...]
    coverage: DailyCoverage

    def __post_init__(self) -> None:
        start, end = report_bounds(self.report_date)
        if not isinstance(self.account_id, AccountId) or not isinstance(
            self.metadata, DataMetadata
        ):
            raise ValidationError("Expected daily observation identity and metadata")
        if not isinstance(self.coverage, DailyCoverage) or not isinstance(self.matches, tuple):
            raise ValidationError("Expected immutable daily observations and coverage")
        if len(self.matches) > 100:
            raise ValidationError("Daily observations exceed the recent-match bound")
        seen: set[int] = set()
        for match in self.matches:
            if (
                not isinstance(match, MatchSummary)
                or match.account_id != self.account_id
                or match.metadata.source != self.metadata.source
                or not start <= match.started_at < end
                or match.match_id in seen
            ):
                raise ValidationError("Inconsistent daily match observations")
            MatchId(match.match_id)
            seen.add(match.match_id)

    @property
    def wins(self) -> int:
        return sum(match.is_win is True for match in self.matches)

    @property
    def losses(self) -> int:
        return sum(match.is_win is False for match in self.matches)

    @property
    def unknown_outcomes(self) -> int:
        return sum(match.is_win is None for match in self.matches)
