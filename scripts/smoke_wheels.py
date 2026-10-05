"""Install each built distribution in a separate temporary environment, without an index."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    for distribution, module in [
        ("dota2forge-core", "dota2forge_core"),
        ("dota2forge-renderer", "dota2forge_renderer"),
        ("astrbot-plugin-dota2forge", "astrbot_plugin_dota2forge"),
        ("dota2uid", "Dota2UID"),
    ]:
        with tempfile.TemporaryDirectory(prefix="dota2forge-wheel-") as directory:
            environment = Path(directory) / "venv"
            subprocess.run(["uv", "venv", "--python", sys.executable, str(environment)], check=True)
            python = environment / (
                "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
            )
            subprocess.run(
                [
                    "uv",
                    "pip",
                    "install",
                    "--no-cache",
                    "--python",
                    str(python),
                    "--no-index",
                    "--find-links",
                    str(ROOT / "dist"),
                    "--prerelease=allow",
                    distribution,
                ],
                check=True,
            )
            smoke = (
                f"import {module}; from dota2forge_core import Dota2Service, MatchDetailService, "
                "MatchDetail, MatchDetailUnavailable, MatchId, MatchParseState; "
                "assert MatchId(1).value == 1; "
                "assert MatchParseState.NO_DATA.value == 'no_data'; "
                "from dota2forge_core.infrastructure.hero_catalog import load_hero_catalog; "
                "assert load_hero_catalog().resolve('AM').hero_id == 1; "
                "import importlib.util; "
                "assert importlib.util.find_spec('astrbot') is None; "
                "assert importlib.util.find_spec('gsuid_core') is None"
            )
            if module == "Dota2UID":
                smoke += (
                    "; from Dota2UID.commands import parse_command; "
                    "from importlib.resources import files; "
                    "assert parse_command('do帮助', '').limit == 10; "
                    "assert files('Dota2UID').joinpath('host_entry.py.template').is_file()"
                )
            if module == "dota2forge_renderer":
                smoke += (
                    "; from dota2forge_renderer import PillowRenderer, MenuCard; "
                    "from importlib.resources import files; "
                    "assert files('dota2forge_renderer').joinpath('assets/v1/OFL.txt').is_file(); "
                    "from dota2forge_renderer.hero_items import item_name; "
                    "assert item_name(1) == '闪烁匕首'; "
                    "renderer = PillowRenderer(); image = renderer.render(MenuCard()); "
                    "assert image.data.startswith(b'\\x89PNG') and image.width == 780; "
                    "renderer.close()"
                )
            if module == "astrbot_plugin_dota2forge":
                smoke += (
                    "; from astrbot_plugin_dota2forge import AstrApplication, AstrTextReply; "
                    "assert AstrApplication and AstrTextReply"
                )
            subprocess.run(
                [
                    str(python),
                    "-I",
                    "-c",
                    smoke,
                ],
                cwd=directory,
                check=True,
            )
            print(f"Wheel install/import passed: {distribution}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
