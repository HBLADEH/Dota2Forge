"""Every bundled item label fits its reserved rectangle without hidden truncation."""

import pytest
from dota2forge_renderer import PillowRenderer
from dota2forge_renderer.engine import _Canvas
from dota2forge_renderer.hero_items import item_card_name, item_name, item_names


@pytest.mark.parametrize("width", [108, 124])
def test_complete_catalog_fits_two_lines_with_padding(width):
    renderer = PillowRenderer()
    try:
        renderer._load()
        for item_id in item_names():
            with _Canvas(renderer, 180) as canvas:
                renderer._item_label(canvas, item_id, 36, 30, width)
                assert 1 <= len(canvas.boxes) <= 2, item_id
                assert all(36 <= b[0] <= b[2] <= 36 + width for b in canvas.boxes)
                assert max(b[3] for b in canvas.boxes) <= 86, item_id
                assert "..." not in item_card_name(item_id)
    finally:
        renderer.close()


def test_reviewed_short_names_preserve_full_text_names():
    assert item_card_name(108) == "A杖"
    assert item_name(108) == "阿哈利姆神杖"
    assert item_card_name(151) == "臂章"
    assert item_card_name(150) == "臂章图纸"
    assert item_card_name(999999) == "装备 ID 999999"
