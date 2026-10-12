"""Check candidate bytes, versions, reviewed images and private file boundaries."""

import argparse
import hashlib
import json
import tarfile
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXPECTED = {
    "dota2forge-core": "0.1.0a7",
    "dota2forge-renderer": "0.1.0a7",
    "dota2forge-assets": "0.1.0a1",
    "dota2uid": "0.1.0a14",
    "astrbot-plugin-dota2forge": "0.1.0a12",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--forbidden-sample", action="append", default=[])
    args = parser.parse_args()
    candidate = HERE / "candidate"
    manifest = json.loads((candidate / "manifest.json").read_bytes())
    assert manifest["versions"] == EXPECTED
    assert manifest["source_ref"] == args.source_commit
    for name, expected in manifest["files_sha256"].items():
        assert digest((candidate / name).read_bytes()) == expected
    for name, expected in manifest["source_sha256"].items():
        assert digest((ROOT / name).read_bytes()) == expected
    previous = ROOT / "dist/plugin-distributions/readme-release-20261012-v1"
    summaries = []
    forbidden = [value.encode("utf-8") for value in args.forbidden_sample]
    project_payloads = []
    for path in (HERE / "wheels").iterdir():
        if not path.name.startswith(("dota2", "astrbot_plugin_dota2forge")):
            continue
        if path.name.endswith(".whl"):
            with ZipFile(path) as packed:
                entries = {name: packed.read(name) for name in packed.namelist()}
        elif path.name.endswith(".tar.gz"):
            with tarfile.open(path, "r:gz") as packed:
                entries = {
                    entry.name: packed.extractfile(entry).read()
                    for entry in packed
                    if entry.isfile()
                }
        else:
            continue
        assert not any(
            Path(name).name.startswith(".env")
            or Path(name).suffix in (".db", ".sqlite", ".sqlite3")
            for name in entries
        )
        assert not any(sample in data for sample in forbidden for data in entries.values())
        project_payloads.append(path.name)
    for plugin in ("Dota2UID", "astrbot_plugin_dota2forge"):
        folder = candidate / plugin
        expected = {
            p.relative_to(folder).as_posix(): p.read_bytes()
            for p in folder.rglob("*")
            if p.is_file()
        }
        with ZipFile(candidate / (plugin + ".zip")) as packed:
            assert {name: packed.read(name) for name in packed.namelist()} == expected
        runtime = json.loads(expected["runtime-wheels.json"])
        released = json.loads(expected["release.json"])
        assert released["versions"] == {
            name: version
            for name, version in EXPECTED.items()
            if name != ("astrbot-plugin-dota2forge" if plugin == "Dota2UID" else "dota2uid")
        }
        for entry in runtime["wheels"].values():
            data = (HERE / "wheels" / entry["filename"]).read_bytes()
            assert digest(data) == entry["sha256"]
        assert not any(
            Path(name).name.startswith(".env")
            or Path(name).suffix in (".db", ".sqlite", ".sqlite3")
            for name in expected
        )
        assert not any(sample in data for sample in forbidden for data in expected.values())
        reviewed = []
        for name, data in expected.items():
            if name.startswith("screenshots/"):
                assert data == (previous / plugin / name).read_bytes()
                reviewed.append({"filename": name, "sha256": digest(data)})
        assert len(reviewed) == 7
        if plugin.startswith("astrbot"):
            assert (
                expected["CHANGELOG.md"]
                .decode("utf-8")
                .splitlines()[2]
                .startswith("## 0.1.0-alpha.12 — ")
            )
            assert (candidate / (plugin + ".zip")).stat().st_size <= 16_000_000
        summaries.append(
            {
                "plugin": plugin,
                "repository_files": len(expected),
                "zip_bytes": (candidate / (plugin + ".zip")).stat().st_size,
                "zip_matches_folder": True,
                "reviewed_screenshots": reviewed,
            }
        )
    report = {
        "passed": True,
        "source_commit": args.source_commit,
        "private_files_absent": True,
        "forbidden_source_samples_absent": True,
        "forbidden_source_samples_checked": len(forbidden),
        "versions": EXPECTED,
        "project_payloads_scanned": sorted(project_payloads),
        "candidates": summaries,
    }
    (HERE / "candidate-validation.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    print("Candidate byte, version, reviewed screenshot and privacy validation passed.")


if __name__ == "__main__":
    main()
