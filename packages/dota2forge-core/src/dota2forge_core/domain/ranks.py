"""Versioned community medal estimates, independent of observed or exact MMR."""

from dataclasses import dataclass

from .errors import ValidationError
from .models import require_nonnegative


@dataclass(frozen=True, slots=True)
class RankMmrEstimate:
    """Inclusive approximate bounds; None means there is no known upper bound."""

    lower_bound: int
    upper_bound: int | None

    def __post_init__(self) -> None:
        if type(self.lower_bound) is not int:
            raise ValidationError("Expected an estimate lower bound")
        require_nonnegative(self.lower_bound)
        require_nonnegative(self.upper_bound)
        if self.upper_bound is not None and self.upper_bound < self.lower_bound:
            raise ValidationError("Reversed MMR estimate bounds")


def estimate_rank_mmr(rank_tier: int | None) -> RankMmrEstimate | None:
    """Apply community-medal-v1, never infer a score from unknown/unrated ranks.

    Medal tiers 1–6 span 770 points with 154 per star; Divine spans 1000
    with 200 per star; Immortal has only an approximate 5620 lower bound.
    These are community thresholds, not Valve guarantees or Provider data.
    References and limitations: docs/subsystems/core.md.
    """
    require_nonnegative(rank_tier)
    if rank_tier is None or rank_tier == 0:
        return None
    if rank_tier == 80:
        return RankMmrEstimate(5620, None)
    tier, stars = divmod(rank_tier, 10)
    if not (1 <= tier <= 7 and 1 <= stars <= 5):
        return None
    step = 200 if tier == 7 else 154
    lower = (tier - 1) * 770 + (stars - 1) * step
    return RankMmrEstimate(lower, lower + step - 1)
