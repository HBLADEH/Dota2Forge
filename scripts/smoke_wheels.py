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
                f"import {module}; from dota2forge_core import Dota2Service; "
                "import importlib.util; "
                "assert importlib.util.find_spec('astrbot') is None; "
                "assert importlib.util.find_spec('gsuid_core') is None"
            )
            if module == "Dota2UID":
                smoke += (
                    "; from Dota2UID.commands import parse_command; "
                    "from importlib.resources import files; "
                    "assert parse_command('dota帮助', '').limit == 10; "
                    "assert files('Dota2UID').joinpath('host_entry.py.template').is_file()"
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
