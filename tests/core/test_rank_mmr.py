"""Community estimates remain distinct from the Provider's observed rank."""

from dataclasses import FrozenInstanceError

import pytest
from dota2forge_core import RankMmrEstimate, ValidationError, estimate_rank_mmr


@pytest.mark.parametrize(
    "rank,lower,upper",
    [
        (11, 0, 153),
        (15, 616, 769),
        (21, 770, 923),
        (31, 1540, 1693),
        (41, 2310, 2463),
        (45, 2926, 3079),
        (51, 3080, 3233),
        (61, 3850, 4003),
        (65, 4466, 4619),
        (71, 4620, 4819),
        (72, 4820, 5019),
        (75, 5420, 5619),
        (80, 5620, None),
    ],
)
def test_rank_estimate_uses_approximate_medal_intervals(rank, lower, upper):
    assert estimate_rank_mmr(rank) == RankMmrEstimate(lower, upper)


@pytest.mark.parametrize("rank", [None, 0, 1, 10, 16, 20, 76, 81, 99, 999])
def test_unknown_unrated_or_unrecognized_ranks_have_no_estimate(rank):
    assert estimate_rank_mmr(rank) is None


@pytest.mark.parametrize("rank", [-1, True, False, 51.0, "51"])
def test_invalid_rank_input_is_not_coerced(rank):
    with pytest.raises(ValidationError):
        estimate_rank_mmr(rank)


@pytest.mark.parametrize("lower,upper", [(None, 1), (-1, 1), (True, 1), (1, False), (2, 1)])
def test_estimate_rejects_invalid_or_reversed_bounds(lower, upper):
    with pytest.raises(ValidationError):
        RankMmrEstimate(lower, upper)


def test_estimate_is_immutable_and_rank_decreases_reduce_estimate():
    higher = estimate_rank_mmr(52)
    lower = estimate_rank_mmr(51)
    assert higher.lower_bound > lower.upper_bound
    with pytest.raises(FrozenInstanceError):
        lower.lower_bound = 9999
