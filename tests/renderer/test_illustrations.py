"""Local ID mapping, missing art and manifest trust boundaries; no downloaded test art."""

import hashlib
import io
import json
from dataclasses import replace

import pytest
from dota2forge_core import PlayerProfile
from dota2forge_renderer import (
    MatchDetailCard,
    MenuCard,
    PillowRenderer,
    PlayerCard,
    RecentMatchesCard,
    RenderError,
)
from dota2forge_renderer.illustrations import MAX_CACHED_IMAGES, Illustrations
from PIL import Image
from test_renderer_cards import ACCOUNT, META, detail, recent


@pytest.fixture
def pack(tmp_path):
    manifest = {"version": 1, "heroes": {}, "items": {}, "decor": {}}
    for kind, identifier, color, size in (
        ("heroes", "2", "#f40099", (256, 144)),
        ("items", "1", "#20ff4a", (88, 64)),
        ("decor", "header", "#883030", (780, 174)),
    ):
        path = tmp_path / kind / f"{identifier}.png"
        path.parent.mkdir()
        with Image.new("RGBA", size, color) as image:
            image.save(path)
        manifest[kind][identifier] = {
            "name_loc": "合成插图",
            "status": "available",
            "file": f"{kind}/{identifier}.png",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "source": "fixture",
        }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path, manifest


def test_real_card_uses_local_id_images_and_keeps_unknowns(pack):
    path, _ = pack
    renderer = PillowRenderer(illustration_path=path)
    try:
        for card, point, color in (
            (RecentMatchesCard(recent()), (80, 300), (244, 0, 153)),
            (MatchDetailCard(detail()), (210, 640), (32, 255, 74)),
        ):
            artifact = renderer.render(card)
            with Image.open(io.BytesIO(artifact.data)) as image:
                assert image.getpixel(point) == color
        assert renderer.hero(2) == "合成插图"
        assert renderer.hero(999) == "英雄 ID 999" and renderer.hero(None) == "英雄未知"
        assert renderer._illustrations.image("items", 0) is None
        assert renderer._illustrations.image("items", None) is None
    finally:
        renderer.close()
    assert not renderer._illustrations._images


def test_missing_art_is_placeholder_but_changed_art_fails(pack):
    path, manifest = pack
    art = Illustrations(path)
    art.load()
    (path / "heroes/2.png").unlink()
    assert art.image("heroes", 2) is None
    manifest["items"]["3"] = {"name_loc": "缺图", "source": "fixture", "status": "missing"}
    (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    art.close()
    art.load()
    assert art.image("items", 3) is None and art.name("items", 3) == "缺图"
    (path / "items/1.png").write_bytes(b"changed")
    with pytest.raises(RenderError):
        art.image("items", 1)
    art.close()


@pytest.mark.parametrize(
    "change",
    [
        {"version": 2},
        {"version": True},
        {"heroes": []},
        {
            "heroes": {
                "2": {
                    "name_loc": "合成",
                    "source": "fixture",
                    "status": "available",
                    "file": "../2.png",
                    "sha256": "0" * 64,
                }
            }
        },
        {"heroes": {"2": {"name_loc": "合成", "source": "fixture", "status": []}}},
    ],
)
def test_invalid_manifest_is_render_error(pack, change):
    path, manifest = pack
    (path / "manifest.json").write_text(json.dumps(manifest | change), encoding="utf-8")
    renderer = PillowRenderer(illustration_path=path)
    try:
        with pytest.raises(RenderError):
            renderer.render(MenuCard())
    finally:
        renderer.close()


def test_cached_decoded_images_are_bounded_and_closed(pack):
    path, manifest = pack
    for identifier in range(3, MAX_CACHED_IMAGES + 4):
        filename = f"heroes/{identifier}.png"
        (path / filename).write_bytes((path / "heroes/2.png").read_bytes())
        manifest["heroes"][str(identifier)] = manifest["heroes"]["2"] | {"file": filename}
    (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    art = Illustrations(path)
    art.load()
    first = art.image("heroes", 2)
    assert art.image("heroes", 2) is first
    for identifier in range(3, MAX_CACHED_IMAGES + 4):
        art.image("heroes", identifier)
    assert len(art._images) == MAX_CACHED_IMAGES
    with pytest.raises(ValueError, match="closed"):
        first.getpixel((0, 0))
    art.close()


def test_long_equipment_id_falls_back_instead_of_hiding_raw_id():
    match = detail()
    participant = replace(match.players[0], item_ids=(999999999999999999, 0, None, 0, 0, 0))
    renderer = PillowRenderer()
    try:
        with pytest.raises(RenderError):
            renderer.render(MatchDetailCard(replace(match, players=(participant,))))
    finally:
        renderer.close()


@pytest.fixture
def rank_pack(pack):
    path, manifest = pack
    for kind, keys in (("ranks", range(9)), ("rank_stars", range(1, 6)), ("ui", ("gold",))):
        (path / kind).mkdir()
        manifest[kind] = {}
        for key in keys:
            filename = f"{kind}/{key}.png"
            color = (20 + int(key) * 20, 40, 60, 255) if kind == "ranks" else (0, 0, 0, 0)
            with Image.new("RGBA", (256, 256), color) as image:
                if kind == "rank_stars":
                    image.paste((240, int(key) * 30, 180, 255), (112, 16, 144, 48))
                elif kind == "ui":
                    image.paste((255, 220, 0, 255), (0, 0, 256, 256))
                image.save(path / filename)
            manifest[kind][str(key)] = {
                "name_loc": "合成图标",
                "status": "available",
                "file": filename,
                "sha256": hashlib.sha256((path / filename).read_bytes()).hexdigest(),
                "source": "fixture",
            }
    (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return path, manifest


@pytest.mark.parametrize(
    "rank",
    [
        0,
        80,
        *[tier * 10 + stars for tier in range(1, 8) for stars in range(1, 6)],
        None,
        1,
        16,
        50,
        81,
        999,
    ],
)
def test_rank_badge_uses_correct_medal_and_transparent_stars_without_guessing(rank_pack, rank):
    path, _ = rank_pack
    renderer = PillowRenderer(illustration_path=path)
    try:
        artifact = renderer.render(PlayerCard(PlayerProfile(ACCOUNT, META, "合成玩家", rank)))
        tier, stars = divmod(rank, 10) if rank is not None else (-1, -1)
        known = rank in (0, 80) or (1 <= tier <= 7 and 1 <= stars <= 5)
        with Image.open(io.BytesIO(artifact.data)) as image:
            medal = (20 + tier * 20, 40, 60) if known else (16, 23, 26)
            assert image.getpixel((640, 440)) == medal
            if known and 1 <= tier <= 7:
                assert image.getpixel((640, 372)) == (240, stars * 30, 180)
            else:
                assert image.getpixel((640, 372)) == medal
        assert artifact.height == 960 and len(artifact.data) <= 2 * 1024 * 1024
    finally:
        renderer.close()


def test_rank_missing_stars_or_medal_keeps_data_card_but_corrupt_art_fails(rank_pack):
    path, _ = rank_pack
    card = PlayerCard(PlayerProfile(ACCOUNT, META, "合成玩家", 51))
    (path / "rank_stars/1.png").unlink()
    renderer = PillowRenderer(illustration_path=path)
    try:
        artifact = renderer.render(card)
        with Image.open(io.BytesIO(artifact.data)) as image:
            assert image.getpixel((640, 372)) == (120, 40, 60)
    finally:
        renderer.close()
    original = (path / "ranks/5.png").read_bytes()
    (path / "ranks/5.png").unlink()
    renderer = PillowRenderer(illustration_path=path)
    try:
        artifact = renderer.render(card)
        with Image.open(io.BytesIO(artifact.data)) as image:
            assert image.getpixel((640, 372)) == (16, 23, 26)
    finally:
        renderer.close()
    (path / "ranks/5.png").write_bytes(original + b"tampered")
    renderer = PillowRenderer(illustration_path=path)
    try:
        with pytest.raises(RenderError):
            renderer.render(card)
    finally:
        renderer.close()


def test_gold_icon_is_present_in_recent_and_detail_data_cards(rank_pack):
    path, _ = rank_pack
    renderer = PillowRenderer(illustration_path=path)
    try:
        for card, point in (
            (RecentMatchesCard(recent()), (428, 390)),
            (MatchDetailCard(detail()), (58, 518)),
        ):
            artifact = renderer.render(card)
            with Image.open(io.BytesIO(artifact.data)) as image:
                assert image.getpixel(point) == (255, 220, 0)
    finally:
        renderer.close()


@pytest.mark.parametrize(
    "kind,key", [("ranks", "9"), ("ranks", "05"), ("rank_stars", "6"), ("ui", "../gold")]
)
def test_new_icon_sections_reject_unknown_or_escaped_keys(rank_pack, kind, key):
    path, manifest = rank_pack
    manifest[kind][key] = next(iter(manifest[kind].values()))
    (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    renderer = PillowRenderer(illustration_path=path)
    try:
        with pytest.raises(RenderError):
            renderer.render(MenuCard())
    finally:
        renderer.close()
