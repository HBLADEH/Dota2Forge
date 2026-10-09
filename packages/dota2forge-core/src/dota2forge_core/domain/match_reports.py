"""Completed match reports combining detail and source-specific analysis."""

from dataclasses import dataclass

from .analysis import MatchAnalysis, MatchAnalysisResult, MatchAnalysisUnavailable
from .errors import ValidationError
from .identity import AccountId
from .match_detail import (
    MatchDetail,
    MatchDetailResult,
    MatchDetailUnavailable,
    MatchId,
    MatchParticipant,
)
from .models import DataMetadata, MatchSummary


@dataclass(frozen=True, slots=True)
class MatchReport:
    match_id: MatchId
    metadata: DataMetadata
    tracked_account_id: AccountId | None
    summary: MatchSummary | None
    detail: MatchDetailResult
    analysis: MatchAnalysisResult

    def __post_init__(self) -> None:
        if not isinstance(self.match_id, MatchId) or not isinstance(self.metadata, DataMetadata):
            raise ValidationError("Expected a validated match report identity")
        if self.tracked_account_id is not None and not isinstance(
            self.tracked_account_id, AccountId
        ):
            raise ValidationError("Expected a validated tracked account")
        if self.summary is not None and (
            not isinstance(self.summary, MatchSummary)
            or self.summary.match_id != self.match_id.value
            or self.summary.metadata.source != self.metadata.source
        ):
            raise ValidationError("Inconsistent match report summary")
        if not isinstance(self.detail, (MatchDetail, MatchDetailUnavailable)):
            raise ValidationError("Expected a validated match detail")
        if not isinstance(self.analysis, (MatchAnalysis, MatchAnalysisUnavailable)):
            raise ValidationError("Expected a validated match analysis")
        if (
            self.detail.match_id != self.match_id
            or self.detail.metadata.source != self.metadata.source
        ):
            raise ValidationError("Inconsistent match report detail")
        if (
            self.analysis.match_id != self.match_id
            or self.analysis.metadata.source != self.metadata.source
        ):
            raise ValidationError("Inconsistent match report analysis")

    @property
    def completed(self) -> bool:
        return isinstance(self.detail, MatchDetail) and (
            self.detail.duration_seconds is not None and self.detail.did_radiant_win is not None
        )

    def team_total(self, radiant: bool, metric: str) -> int | None:
        if type(radiant) is not bool:
            raise ValidationError("Expected a known team side")
        if metric not in {"kills", "net_worth", "hero_damage", "tower_damage", "hero_healing"}:
            raise ValidationError("Unsupported team total metric")
        if not isinstance(self.detail, MatchDetail):
            return None
        team = tuple(player for player in self.detail.players or () if player.is_radiant is radiant)
        values = tuple(getattr(player, metric) for player in team)
        return None if len(team) != 5 or any(value is None for value in values) else sum(values)

    def participation(self, player: MatchParticipant) -> float | None:
        if not isinstance(self.detail, MatchDetail) or player not in (self.detail.players or ()):
            return None
        if player.is_radiant is None or player.kills is None or player.assists is None:
            return None
        total = self.team_total(player.is_radiant, "kills")
        if not total or player.kills + player.assists > total:
            return None
        return (player.kills + player.assists) / total

    @property
    def imp_ranking(self) -> tuple[MatchParticipant, ...]:
        if not isinstance(self.detail, MatchDetail):
            return ()
        return tuple(
            sorted(
                (player for player in self.detail.players or () if player.imp is not None),
                key=lambda player: (
                    -(player.imp or 0),
                    player.player_slot if player.player_slot is not None else 256,
                ),
            )
        )

    @property
    def strong_performers(self) -> tuple[MatchParticipant, ...]:
        return tuple(
            player for player in self.imp_ranking if player.imp is not None and player.imp > 0
        )[:3]

    @property
    def weak_performers(self) -> tuple[MatchParticipant, ...]:
        return tuple(
            player
            for player in reversed(self.imp_ranking)
            if player.imp is not None and player.imp < 0
        )[:3]

    @property
    def performance_candidate(self) -> tuple[AccountId | None, int | None] | None:
        if not isinstance(self.detail, MatchDetail) or self.detail.did_radiant_win is None:
            return None
        players = tuple(
            player
            for player in self.detail.players or ()
            if player.account_id is not None
            and player.is_radiant is not None
            and player.is_radiant == self.detail.did_radiant_win
        )
        if not players or any(player.kills is None or player.deaths is None for player in players):
            return None
        candidate = max(
            players,
            key=lambda player: (
                (player.kills or 0) + (player.assists or 0),
                -(player.deaths or 0),
                player.gold_per_minute or -1,
                -(player.player_slot or 255),
            ),
        )
        return candidate.account_id, candidate.player_slot
