"""Explicit download tool tests replace HTTP with synthetic public catalogs and PNGs."""

import asyncio
import io
import json
from urllib.error import HTTPError

import httpx
import pytest
import pytest_socket
from dota2forge_assets import AssetError, AssetLimits
from dota2forge_assets import cli as assets
from dota2forge_assets.sources import MIRROR, catalog
from dota2forge_assets.validation import png_size
from PIL import Image


@pytest.fixture(autouse=True)
def cli_loop(monkeypatch):
    pytest_socket.enable_socket()
    try:
        loop = asyncio.new_event_loop()
    finally:
        pytest_socket.disable_socket()
    monkeypatch.setattr(assets.asyncio, "run", loop.run_until_complete)
    monkeypatch.setattr(assets, "AssetLimits", lambda: AssetLimits(retries=0))
    try:
        yield loop.run_until_complete
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())
        loop.close()


def install_fetch(monkeypatch, fetch):
    def request(req):
        try:
            return httpx.Response(200, content=fetch(str(req.url)))
        except HTTPError as error:
            return httpx.Response(error.code)
        except OSError:
            raise httpx.ConnectError("synthetic interruption") from None

    monkeypatch.setattr(
        assets,
        "make_client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(request), trust_env=False),
    )


def png():
    with io.BytesIO() as stream, Image.new("RGB", (256, 144), "red") as image:
        image.save(stream, "PNG")
        return stream.getvalue()


def test_download_pack_sources_hashes_missing_and_cli(tmp_path, monkeypatch, capsys, cli_loop):
    def fetch(url):
        if "herolist" in url:
            return json.dumps(
                {
                    "result": {
                        "data": {
                            "heroes": [{"id": 2, "name": "npc_dota_hero_axe", "name_loc": "斧王"}]
                        }
                    }
                }
            ).encode()
        if "itemlist" in url:
            return json.dumps(
                {
                    "result": {
                        "data": {
                            "itemabilities": [
                                {"id": 1, "name": "item_blink", "name_loc": "闪烁匕首"}
                            ]
                        }
                    }
                }
            ).encode()
        if "items" in url:
            raise HTTPError(url, 404, "missing", {}, None)
        return png()

    install_fetch(monkeypatch, fetch)
    assert assets.main(["--output", str(tmp_path)]) == 0
    manifest = json.loads((tmp_path / "manifest.json").read_text("utf-8"))
    assert manifest["heroes"]["2"]["status"] == "available"
    assert manifest["heroes"]["2"]["source"].endswith("heroes/axe.png")
    assert manifest["items"]["1"]["status"] == "missing"
    assert manifest["items"]["1"]["file"] is None
    assert "Valve" in (tmp_path / "RIGHTS.txt").read_text("utf-8")
    assert "1 available" in capsys.readouterr().out
    manifest["decor"] = {"header": {"source": "fixture"}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert cli_loop(assets.download_pack(tmp_path))["decor"] == manifest["decor"]


def test_failed_network_does_not_publish_new_manifest(tmp_path, monkeypatch, capsys):
    original = b'{"version": 1, "decor": {}}'
    (tmp_path / "manifest.json").write_bytes(original)

    def fetch(url):
        raise HTTPError(url, 403, "rejected", {}, None)

    install_fetch(monkeypatch, fetch)
    assert assets.main(["--output", str(tmp_path)]) == 1
    assert (tmp_path / "manifest.json").read_bytes() == original
    assert "AssetError" in capsys.readouterr().out


def test_later_download_failure_preserves_previous_image(tmp_path, monkeypatch):
    (tmp_path / "heroes").mkdir()
    previous = tmp_path / "heroes/2.png"
    previous.write_bytes(b"previous local art")

    def fetch(url):
        if "herolist" in url:
            return json.dumps(
                {
                    "result": {
                        "data": {
                            "heroes": [{"id": 2, "name": "npc_dota_hero_axe", "name_loc": "斧王"}]
                        }
                    }
                }
            ).encode()
        if "itemlist" in url:
            raise OSError("synthetic interruption")
        return png()

    install_fetch(monkeypatch, fetch)
    assert assets.main(["--output", str(tmp_path)]) == 1
    assert previous.read_bytes() == b"previous local art"
    assert not (tmp_path / "manifest.json").exists()


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [{}],
        [{"id": 1, "name": "item_../blink", "name_loc": "bad"}],
        [{"id": True, "name": "item_blink", "name_loc": "bad"}],
    ],
)
def test_invalid_catalog_never_guesses_identity(rows):
    data = json.dumps({"result": {"data": {"items": rows}}}).encode()
    with pytest.raises(AssetError):
        catalog(data, "items", "item_")


def test_bad_png_and_large_response_are_rejected(monkeypatch):
    with pytest.raises(AssetError), io.BytesIO() as stream, Image.new("RGB", (1, 1)) as image:
        image.save(stream, "JPEG")
        png_size(stream.getvalue(), AssetLimits())
    # Exercise the shared streaming limit through the public CLI.
    install_fetch(monkeypatch, lambda url: b"x" * (4 * 1024 * 1024 + 1))
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as root:
        assert assets.main(["--output", str(Path(root))]) == 1
        assert not Path(root, "manifest.json").exists()


def test_only_ui_download_records_mirror_and_preserves_existing_assets(tmp_path, monkeypatch):
    original = {
        "version": 1,
        "heroes": {"2": {"source": "kept"}},
        "items": {"1": {"status": "missing"}},
        "catalogs": {"heroes": {"response_sha256": "kept"}},
        "decor": {"header": {"sha256": "kept"}},
        "custom": {"kept": True},
    }
    (tmp_path / "manifest.json").write_text(json.dumps(original), encoding="utf-8")

    def fetch(url):
        assert url.startswith(MIRROR)
        if url.endswith("rank_star_5.png"):
            raise HTTPError(url, 404, "missing", {}, None)
        return png()

    install_fetch(monkeypatch, fetch)
    assert assets.main(["--output", str(tmp_path), "--only-ui"]) == 0
    manifest = json.loads((tmp_path / "manifest.json").read_text("utf-8"))
    for key in ("heroes", "items", "catalogs", "decor", "custom"):
        assert manifest[key] == original[key]
    assert set(manifest["ranks"]) == set(map(str, range(9)))
    assert manifest["ranks"]["5"]["source"].endswith("rank_icon_5.png")
    assert manifest["ranks"]["5"]["source_kind"] == "valve_game_art_mirror"
    assert manifest["rank_stars"]["5"]["status"] == "missing"
    assert manifest["ui"]["gold"]["mirror"] == "OpenDota"


def test_late_ui_failure_does_not_replace_existing_manifest_or_png(tmp_path, monkeypatch):
    original = b'{"version":1,"decor":{"header":{"source":"keep"}}}'
    (tmp_path / "manifest.json").write_bytes(original)
    (tmp_path / "ranks").mkdir()
    previous = tmp_path / "ranks/5.png"
    previous.write_bytes(b"previous medal")

    def fetch(url):
        if url.endswith("gold.png"):
            raise OSError("synthetic interruption")
        return png()

    install_fetch(monkeypatch, fetch)
    assert assets.main(["--output", str(tmp_path), "--only-ui"]) == 1
    assert (tmp_path / "manifest.json").read_bytes() == original
    assert previous.read_bytes() == b"previous medal"
