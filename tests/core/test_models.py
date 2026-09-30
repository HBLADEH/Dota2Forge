from dataclasses import replace
from datetime import datetime, timedelta

import pytest
from dota2forge_core import (
    AccountId,
    DataSource,
    MatchSummary,
    PlayerBinding,
    PlayerProfile,
    ProviderError,
    ProviderErrorCode,
    RecentMatches,
    ValidationError,
)


def test_unknown_stats_are_distinct_from_zero_and_loss(provider):
    player = provider.profile
    match = provider.recent.matches[0]
    assert player.missing_fields == ("rank_tier",)
    assert match.missing_fields == ("gold_per_minute", "experience_per_minute")
    assert match.kills == 0
    assert match.is_win is False
    assert match.metadata.source == DataSource.FIXTURE
    assert match.metadata.observed_at is None
    assert match.metadata.patch is None
    assert PlayerProfile(AccountId(123), player.metadata).missing_fields == (
        "display_name",
        "rank_tier",
    )


@pytest.mark.parametrize(
    "field",
    [
        "kills",
        "deaths",
        "assists",
        "duration_seconds",
        "gold_per_minute",
        "experience_per_minute",
        "hero_id",
    ],
)
@pytest.mark.parametrize("invalid", [-1, True, 1.5, "1"])
def test_stats_reject_invalid_types(provider, field, invalid):
    with pytest.raises(ValidationError):
        replace(provider.recent.matches[0], **{field: invalid})


@pytest.mark.parametrize(
    "changes",
    [
        {"match_id": 0},
        {"match_id": True},
        {"account_id": 123},
        {"metadata": None},
        {"hero_id": 0},
        {"is_win": 1},
        {"started_at": datetime(2026, 1, 1)},
    ],
)
def test_match_invariants(provider, changes):
    with pytest.raises(ValidationError):
        replace(provider.recent.matches[0], **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"account_id": 123},
        {"metadata": None},
        {"display_name": 0},
        {"rank_tier": False},
        {"rank_tier": -1},
    ],
)
def test_player_invariants(provider, changes):
    with pytest.raises(ValidationError):
        replace(provider.profile, **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"source": "stratz"},
        {"fetched_at": datetime(2026, 1, 1)},
        {"observed_at": datetime(2026, 1, 1)},
        {"patch": ""},
        {"patch": " "},
        {"patch": 1},
        {"patch": "x" * 65},
    ],
)
def test_metadata_rejects_invalid_observations(metadata, changes):
    with pytest.raises(ValidationError):
        replace(metadata, **changes)


def test_metadata_preserves_observed_time_and_known_patch(metadata):
    observation = metadata.fetched_at - timedelta(hours=1)
    result = replace(metadata, observed_at=observation, patch="synthetic-patch")
    assert result.observed_at == observation
    assert result.patch == "synthetic-patch"


def test_recent_matches_reject_duplicates_mixed_players_sources_and_bad_order(provider):
    recent = provider.recent
    first, second = recent.matches
    invalid = [
        (first, first),
        (second, first),
        ("bad",),
        (replace(first, account_id=AccountId(456)),),
        (replace(first, metadata=replace(first.metadata, source=DataSource.STEAM)),),
    ]
    for matches in invalid:
        with pytest.raises(ValidationError):
            replace(recent, matches=matches)
    for changes in [{"matches": []}, {"account_id": 123}, {"metadata": None}]:
        with pytest.raises(ValidationError):
            replace(recent, **changes)
    assert replace(recent, matches=()).matches == ()


def test_binding_requires_validated_values_and_aware_time(identity, metadata):
    binding = PlayerBinding(identity, AccountId(123), metadata.fetched_at)
    for changes in [{"identity": None}, {"account_id": 123}, {"bound_at": datetime(2026, 1, 1)}]:
        with pytest.raises(ValidationError):
            replace(binding, **changes)
    assert identity.user_id not in repr(binding)


def test_provider_error_carries_safe_classification_and_retry_hint():
    failure = ProviderError(
        ProviderErrorCode.RATE_LIMITED, DataSource.STRATZ, retry_after_seconds=15
    )
    assert failure.retry_after_seconds == 15
    assert str(failure) == "Provider stratz: rate_limited"
    for invalid in [True, -1, 1.5, "1"]:
        with pytest.raises(ValidationError):
            ProviderError(
                ProviderErrorCode.RATE_LIMITED, DataSource.STRATZ, retry_after_seconds=invalid
            )
    with pytest.raises(ValidationError):
        ProviderError(ProviderErrorCode.TIMEOUT, DataSource.STRATZ, retry_after_seconds=5)
    with pytest.raises(ValidationError):
        ProviderError("timeout", DataSource.STRATZ)
    with pytest.raises(ValidationError):
        ProviderError(ProviderErrorCode.TIMEOUT, "secret-token")


def test_minimal_match_marks_all_optional_fields_missing(metadata):
    match = MatchSummary(1, AccountId(123), metadata.fetched_at, metadata)
    assert len(match.missing_fields) == 8
    assert RecentMatches(AccountId(123), (match,), metadata).matches[0] == match
