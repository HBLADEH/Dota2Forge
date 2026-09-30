from dataclasses import replace
from datetime import UTC, datetime

import pytest
from dota2forge_core import (
    AccountId,
    DataMetadata,
    DataSource,
    MatchSummary,
    PlayerProfile,
    ProviderError,
    ProviderErrorCode,
    RecentMatches,
)
from Dota2UID.presentation import (
    player_text,
    provider_error_text,
    rank_text,
    recent_text,
    safe_name,
)


@pytest.mark.parametrize(
    ("rank", "expected"),
    [
        (None, "未知"),
        (0, "未定级"),
        (51, "传奇 1 星"),
        (52, "传奇 2 星"),
        (80, "冠绝一世"),
        (99, "未知段位编码"),
    ],
)
def test_rank_display_does_not_promise_mmr(rank, expected):
    assert expected in rank_text(rank)
    assert "MMR" not in rank_text(rank)


def test_nickname_does_not_inject_chat_markup():
    name = safe_name("[CQ:at,qq=all]\n<b>Hi</b>\x1b\u202e" + "x" * 100)
    assert len(name) <= 48
    assert all(char not in name for char in "[]<>\n\x1b\u202e")
    assert safe_name(None) == "未知" and safe_name("") == "（空昵称）"


def test_match_chunks_keep_source_unknowns_and_false():
    meta = DataMetadata(DataSource.STRATZ, datetime(2026, 9, 30, tzinfo=UTC))
    match = MatchSummary(1, AccountId(123), meta.fetched_at, meta, kills=0, is_win=False)
    recent = RecentMatches(
        AccountId(123), tuple(replace(match, match_id=i) for i in range(1, 101)), meta
    )
    replies = recent_text(recent)
    assert len(replies) == 20 and all(len(text) < 1600 for text in replies)
    assert "负" in replies[0] and "0/未知/未知" in replies[0]
    assert all(
        "STRATZ" in text and "不保证历史完整" in text and "抓取时间" in text for text in replies
    )
    observed = replace(meta, observed_at=meta.fetched_at)
    assert "数据观测时间：2026" in player_text(PlayerProfile(AccountId(123), observed))


@pytest.mark.parametrize("code", list(ProviderErrorCode))
def test_errors_are_explained_without_turning_into_empty_history(code):
    error = ProviderError(code, DataSource.STRATZ)
    assert provider_error_text(error)
    assert "0 场" not in provider_error_text(error)
