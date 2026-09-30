"""Install the GsCore discovery bridge without importing or restarting GsCore."""

import argparse
import json
import os
from importlib.resources import files
from pathlib import Path


def install_bridge(host_root: Path, *, token: str = "") -> tuple[Path, Path]:
    root = host_root.resolve()
    if not (root / "gsuid_core" / "server.py").is_file():
        raise ValueError("Expected a GsCore checkout")
    plugins = root / "gsuid_core" / "plugins"
    destination = plugins / "Dota2UID"
    config_dir = root / "data" / "Dota2UID"
    if not destination.resolve().is_relative_to(root) or not config_dir.resolve().is_relative_to(
        root
    ):
        raise ValueError("Dota2UID installation path escapes the host checkout")
    entry = destination / "__init__.py"
    source = files("Dota2UID").joinpath("host_entry.py.template").read_text(encoding="utf-8")
    if entry.exists() and entry.read_text(encoding="utf-8") != source:
        raise ValueError("Existing bridge differs; stop the plugin before replacing it manually")
    destination.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    config = config_dir / "config.toml"
    if not config.exists():
        config.write_text(
            'namespace = "dota2uid-local"\nstratz_token = '
            + json.dumps(token)
            + '\ntimeout_seconds = 10\n\n[platforms]\nonebot = "qq"\nqq = "qq"\n'
            'telegram = "telegram"\n',
            encoding="utf-8",
        )
    if not entry.exists():
        entry.write_text(source, encoding="utf-8")
    return entry, config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-root", type=Path, required=True)
    parser.add_argument("--token-from-env", action="store_true")
    args = parser.parse_args()
    token = os.environ.get("STRATZ_TOKEN", "") if args.token_from_env else ""
    try:
        install_bridge(args.host_root, token=token)
    except (ValueError, OSError):
        print("Dota2UID installation failed; verify paths and existing bridge.")
        return 1
    print("Dota2UID bridge installed. Configure data/Dota2UID/config.toml, then load in GsCore.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
