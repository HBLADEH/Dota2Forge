"""Stage an AstrBot discovery bridge or ZIP without importing/restarting the host."""

import argparse
from importlib.resources import files
from pathlib import Path
from zipfile import ZipFile


def bridge_files() -> dict[str, bytes]:
    resources = files("astrbot_plugin_dota2forge").joinpath("host")
    return {
        "main.py": resources.joinpath("main.py.template").read_bytes(),
        "_conf_schema.json": resources.joinpath("_conf_schema.json").read_bytes(),
        "metadata.yaml": resources.joinpath("metadata.yaml").read_bytes(),
        "requirements.txt": resources.joinpath("requirements.txt").read_bytes(),
    }


def install_bridge(host_root: Path, *, data_root: Path | None = None) -> Path:
    root = host_root.resolve()
    if not (root / "astrbot" / "core" / "star" / "star_manager.py").is_file():
        raise ValueError("Expected an AstrBot checkout")
    storage = root if data_root is None else data_root.resolve()
    destination = storage / "data" / "plugins" / "astrbot_plugin_dota2forge"
    if not destination.resolve().is_relative_to(storage):
        raise ValueError("Plugin directory escapes the host checkout")
    resources = bridge_files()
    for name, content in resources.items():
        target = destination / name
        if not target.resolve().is_relative_to(storage):
            raise ValueError("Plugin file escapes the host checkout")
        if target.exists() and target.read_bytes() != content:
            raise ValueError(
                "Existing bridge differs; disable the plugin before manual replacement"
            )
    destination.mkdir(parents=True, exist_ok=True)
    for name, content in resources.items():
        target = destination / name
        if not target.exists():
            target.write_bytes(content)
    return destination


def build_archive(output: Path) -> Path:
    with ZipFile(output, "x") as archive:
        for name, content in bridge_files().items():
            archive.writestr(name, content)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--host-root", type=Path)
    group.add_argument("--output", type=Path)
    parser.add_argument("--data-root", type=Path, help="Desktop AstrBot runtime root")
    args = parser.parse_args()
    try:
        if args.host_root is not None:
            install_bridge(args.host_root, data_root=args.data_root)
        else:
            build_archive(args.output)
    except (OSError, ValueError):
        print("Dota2Forge bridge preparation failed; check layout and existing files.")
        return 1
    print(
        "Dota2Forge bridge prepared. Install matching wheels and configure in AstrBot before load."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
