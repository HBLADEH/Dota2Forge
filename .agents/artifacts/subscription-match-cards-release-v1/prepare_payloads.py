"""Stage reviewed local package builds and byte-identical public shared packages."""

import hashlib
import json
import shutil
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WHEELS = HERE / "wheels"
PREVIOUS = ROOT / ".agents/artifacts/plugin-readme-release-20261012/Dota2UID-release-assets.json"
STABLE = ("dota2forge_core", "dota2forge_assets")
CURRENT = {
    "dota2forge_renderer": "0.1.0a7",
    "dota2uid": "0.1.0a14",
    "astrbot_plugin_dota2forge": "0.1.0a12",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_payload(path, data):
    if path.exists() and path.read_bytes() != data:
        raise ValueError("Existing payload differs: " + path.name)
    path.write_bytes(data)


def main():
    WHEELS.mkdir(parents=True, exist_ok=True)
    old = json.loads(PREVIOUS.read_bytes())
    rows = []
    for row in old["assets"]:
        name = row["filename"]
        if not name.startswith(STABLE):
            continue
        url = old["repository"] + "/releases/download/" + old["tag"] + "/" + name
        with urlopen(
            Request(url, headers={"User-Agent": "Dota2Forge-release-preparation"}), timeout=40
        ) as response:
            data = response.read(2 * 1024 * 1024 + 1)
        if len(data) != row["bytes"] or digest(data) != row["sha256"]:
            raise ValueError("Public stable package differs: " + name)
        write_payload(WHEELS / name, data)
        rows.append({**row, "source": url, "matches_previous_release": True})
    for package, version in CURRENT.items():
        for suffix in ("-py3-none-any.whl", ".tar.gz"):
            name = package + "-" + version + suffix
            data = (ROOT / "dist" / name).read_bytes()
            write_payload(WHEELS / name, data)
            rows.append(
                {
                    "filename": name,
                    "bytes": len(data),
                    "sha256": digest(data),
                    "source": "dist/" + name,
                }
            )
    for path in (ROOT / "dist").glob("*.whl"):
        if not path.name.startswith(("dota2", "astrbot_plugin_dota2forge")):
            shutil.copy2(path, WHEELS / path.name)
    report = {
        "passed": True,
        "unchanged_shared_versions": {"dota2forge-core": "0.1.0a7", "dota2forge-assets": "0.1.0a1"},
        "compared_release": old["repository"] + "/releases/tag/" + old["tag"],
        "new_versions": CURRENT,
        "local_dist_unchanged": True,
        "assets": rows,
    }
    (HERE / "payload-preparation.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    print("Staged ten project payloads; four unchanged shared payloads match public release bytes.")


if __name__ == "__main__":
    main()
