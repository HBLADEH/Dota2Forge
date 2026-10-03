"""Compare installed wheel members and bridge resources without importing hosts."""

import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
GS_ROOT = Path("D:/bot/gsuid_core")
ASTR_ROOT = Path("C:/Users/BLADE/.astrbot")


def wheel_matches(distribution, module, site_packages):
    wheel = ROOT / "dist" / f"{distribution}-0.1.0a1-py3-none-any.whl"
    with ZipFile(wheel) as archive:
        members = [
            name
            for name in archive.namelist()
            if name.startswith(module + "/") and not name.endswith("/")
        ]
        return bool(members) and all(
            (site_packages / name).read_bytes() == archive.read(name) for name in members
        )


def main():
    results = {}
    for host, site_packages, adapter_distribution, adapter_module in [
        ("gscore", GS_ROOT / ".venv/Lib/site-packages", "dota2uid", "Dota2UID"),
        (
            "astrbot",
            ASTR_ROOT / "data/site-packages",
            "astrbot_plugin_dota2forge",
            "astrbot_plugin_dota2forge",
        ),
    ]:
        results[host] = {
            distribution: wheel_matches(distribution, module, site_packages)
            for distribution, module in [
                ("dota2forge_core", "dota2forge_core"),
                ("dota2forge_renderer", "dota2forge_renderer"),
                (adapter_distribution, adapter_module),
            ]
        }
    results["gscore_bridge"] = (
        GS_ROOT / "gsuid_core/plugins/Dota2UID/__init__.py"
    ).read_bytes() == (ROOT / "adapters/Dota2UID/src/Dota2UID/host_entry.py.template").read_bytes()
    resources = ROOT / "adapters/astrbot_plugin_dota2forge/src/astrbot_plugin_dota2forge/host"
    results["astrbot_bridge"] = all(
        (ASTR_ROOT / "data/plugins/astrbot_plugin_dota2forge" / name).read_bytes()
        == (resources / ("main.py.template" if name == "main.py" else name)).read_bytes()
        for name in ["main.py", "_conf_schema.json", "metadata.yaml", "requirements.txt"]
    )
    print(json.dumps(results))
    assert all(results["gscore"].values()) and all(results["astrbot"].values())
    assert results["gscore_bridge"] and results["astrbot_bridge"]


if __name__ == "__main__":
    main()
