"""Synthetic observations and real local resources; Pillow tests remain offline."""

import hashlib
import importlib
import io
from datetime import UTC, datetime, timedelta
from importlib.resources import files
from pathlib import Path

import pytest
from dota2forge_core import (
    AccountId,
    DataMetadata,
    DataSource,
    MatchDetail,
    MatchId,
    MatchParticipant,
    MatchSummary,
    PlayerProfile,
    RecentMatches,
)
from dota2forge_renderer import (
    ImageArtifact,
    MatchDetailCard,
    MenuCard,
    PillowRenderer,
    PlayerCard,
    RecentMatchesCard,
    RenderError,
    StatusCard,
)
from dota2forge_renderer.engine import FONT_SHA256, _Canvas
from PIL import Image

META = DataMetadata(DataSource.FIXTURE, datetime(2026, 10, 1, tzinfo=UTC))
ACCOUNT = AccountId(123)


def recent(count=10):
    rows = tuple(
        MatchSummary(
            7000000100 - index,
            ACCOUNT,
            META.fetched_at - timedelta(hours=index),
            META,
            hero_id=(2 if index % 3 == 0 else 999 if index % 3 == 1 else None),
            duration_seconds=0 if index % 2 else None,
            kills=0,
            gold_per_minute=0,
            is_win=False if index % 2 else None,
        )
        for index in range(count)
    )
    return RecentMatches(ACCOUNT, rows, META)


def detail():
    players = tuple(
        MatchParticipant(
            player_slot=index,
            account_id=ACCOUNT if index == 0 else None,
            display_name="合成玩家" if index == 0 else None,
            is_anonymous=False if index == 0 else True if index % 2 else None,
            is_radiant=index < 5,
            hero_id=2,
            kills=0,
            item_ids=(0, 1, None, 0, 0, 0),
        )
        for index in range(10)
    )
    return MatchDetail(MatchId(1), META, players=players, has_stats=False, duration_seconds=0)


@pytest.mark.parametrize(
    "card",
    [
        MenuCard(),
        MenuCard(True),
        PlayerCard(PlayerProfile(ACCOUNT, META)),
        PlayerCard(PlayerProfile(ACCOUNT, META, "超长中文昵称" * 20 + "\U0001f680", 0)),
        RecentMatchesCard(recent()),
        RecentMatchesCard(recent(0)),
        RecentMatchesCard(recent(), 2),
        StatusCard("已保存绑定。"),
        MatchDetailCard(detail(), perspective=ACCOUNT),
        MatchDetailCard(detail(), 2),
        MatchDetailCard(MatchDetail(MatchId(1), META)),
    ],
)
def test_real_cards_encode_nonblank_bounded_png_and_text_bounds(card):
    renderer = PillowRenderer()
    artifact = renderer.render(card)
    assert artifact.mime == "image/png" and artifact.width == 780 and artifact.height <= 1600
    assert len(artifact.data) <= 2 * 1024 * 1024 and "合成玩家" not in repr(artifact)
    with Image.open(io.BytesIO(artifact.data)) as image:
        image.load()
        assert image.size == (artifact.width, artifact.height) and image.mode == "RGB"
        assert any(low < high for low, high in image.getextrema())
    assert renderer.last_layout
    renderer.close()
    assert renderer._font_data is None and not renderer._fonts


def test_full_hundred_match_pages_are_bounded_and_never_blank():
    renderer = PillowRenderer()
    data = recent(100)
    for page in range(1, 21):
        artifact = renderer.render(RecentMatchesCard(data, page))
        assert artifact.height <= 1600 and len(artifact.data) <= 2 * 1024 * 1024
    renderer.close()


@pytest.mark.parametrize(
    "card",
    [
        RecentMatchesCard(recent(), 0),
        RecentMatchesCard(recent(), 3),
        RecentMatchesCard(recent(), True),
        RecentMatchesCard(recent(101)),
        MatchDetailCard(detail(), 0),
        MatchDetailCard(detail(), 3),
    ],
)
def test_invalid_page_or_excess_data_raises_render_error(card):
    renderer = PillowRenderer()
    try:
        with pytest.raises(RenderError):
            renderer.render(card)
    finally:
        renderer.close()


def test_resource_hash_chinese_names_glyph_fallback_and_closed_renderer():
    root = files("dota2forge_renderer").joinpath("assets/v1")
    assert (
        hashlib.sha256(root.joinpath("NotoSansCJKsc-Regular.otf").read_bytes()).hexdigest()
        == FONT_SHA256
    )
    assert "OPEN FONT LICENSE" in root.joinpath("OFL.txt").read_text("utf-8")
    renderer = PillowRenderer()
    renderer.render(MenuCard())
    assert renderer.hero(2) == "斧王" and renderer.hero(999) == "英雄 ID 999"
    assert renderer.hero(None) == "英雄未知"
    assert "U+1F680" in renderer.display("\U0001f680")
    assert renderer.display("合成玩家") == "合成玩家"
    renderer.close()
    with pytest.raises(RenderError):
        renderer.render(MenuCard())


def test_missing_or_corrupt_resources_are_render_errors(tmp_path):
    renderer = PillowRenderer(tmp_path)
    with pytest.raises(RenderError):
        renderer.render(MenuCard())
    (tmp_path / "NotoSansCJKsc-Regular.otf").write_bytes(b"invalid")
    with pytest.raises(RenderError):
        renderer.render(MenuCard())
    renderer.close()


def test_text_and_canvas_bounds_errors_release_images():
    renderer = PillowRenderer()
    renderer.render(MenuCard())
    with pytest.raises(RenderError):
        _Canvas(renderer, 1601)
    with _Canvas(renderer, 200) as canvas:
        with pytest.raises(RenderError):
            canvas.text(760, 20, "溢出")
        canvas.text(36, 20, "重复")
        with pytest.raises(RenderError):
            canvas.text(36, 20, "重叠")
    renderer.close()


def test_png_encoding_failure_and_programming_errors_are_distinct(monkeypatch):
    renderer = PillowRenderer()
    renderer.render(MenuCard())

    def failed(*args, **kwargs):
        raise OSError("synthetic encode failure")

    monkeypatch.setattr(Image.Image, "save", failed)
    with pytest.raises(RenderError):
        renderer.render(MenuCard())
    with pytest.raises(TypeError):
        renderer.render(object())
    renderer.close()


@pytest.mark.parametrize(
    "changes",
    [
        {"data": b"bad"},
        {"data": b"\x89PNG\r\n\x1a\n" + b"x" * (2 * 1024 * 1024)},
        {"width": True},
        {"width": 781},
        {"height": 1601},
        {"height": 0},
        {"mime": "image/jpeg"},
    ],
)
def test_artifact_rejects_invalid_limits(changes):
    with pytest.raises(RenderError):
        ImageArtifact(**({"data": b"\x89PNG\r\n\x1a\n", "width": 780, "height": 1} | changes))


def test_renderer_import_and_construction_do_not_load_resources(monkeypatch):
    import dota2forge_renderer

    def forbidden(*args, **kwargs):
        pytest.fail("Import/constructor must not read local resources")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    importlib.reload(dota2forge_renderer)
    renderer = dota2forge_renderer.PillowRenderer()
    renderer.close()
