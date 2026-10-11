"""Default theme must work without local game art and preserve both consumers."""

import io

from astrbot_plugin_dota2forge.application import HELP as ASTR_HELP
from dota2forge_renderer import MenuCard, PillowRenderer, StatusCard
from dota2forge_renderer.engine import _Canvas
from Dota2UID.presentation import HELP as GS_HELP
from PIL import Image


def test_default_header_is_deterministic_without_bitmap_resources(monkeypatch):
    renderer = PillowRenderer()
    real = renderer._read

    def read_without_bitmaps(name):
        assert not name.endswith((".png", ".jpg", ".webp"))
        return real(name)

    monkeypatch.setattr(renderer, "_read", read_without_bitmaps)
    artifact = renderer.render(MenuCard())
    with (
        Image.open(io.BytesIO(artifact.data)) as image,
        image.crop((560, 0, 780, 20)) as decoration,
    ):
        # The default theme has actual drawn decoration without illustration_path.
        assert any(low < high for low, high in decoration.getextrema())
    assert renderer.render(MenuCard()).data == artifact.data
    renderer.close()


def test_menu_keeps_complete_commands_and_gates_admin_text(monkeypatch):
    captured = []
    original = _Canvas.text

    def capture(canvas, x, y, value, **kwargs):
        captured.append(value)
        return original(canvas, x, y, value, **kwargs)

    monkeypatch.setattr(_Canvas, "text", capture)
    renderer = PillowRenderer()
    try:
        renderer.render(MenuCard())
        assert not any("do停用" in text for text in captured)
        for marker in (
            "do战绩 <ID> <条数>",
            "do订阅 [比赛|段位|日报]",
            "do重试推送",
            "do素材状态",
        ):
            assert any(marker in text for text in captured)
        renderer.render(MenuCard(True))
        assert any(text == "管理员：do停用" for text in captured)
    finally:
        renderer.close()
    for help_text in (ASTR_HELP, GS_HELP):
        for marker in ("查段位", "do比赛 第N场", "do素材状态", "不自动重发", "do取消订阅"):
            assert marker in help_text


def test_status_wrap_keeps_mmr_readable(monkeypatch):
    captured = []
    original = _Canvas.text

    def capture(canvas, x, y, value, **kwargs):
        captured.append(value)
        return original(canvas, x, y, value, **kwargs)

    monkeypatch.setattr(_Canvas, "text", capture)
    renderer = PillowRenderer()
    try:
        renderer.render(StatusCard("已绑定查询账号。现在输入 do查询，查看段位与预估 MMR。"))
        assert "MMR。" in captured
        assert "R。" not in captured
    finally:
        renderer.close()
