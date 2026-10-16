"""Check the explicit release candidate; no host configuration or network access."""

import hashlib
import json
import tarfile
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
STAGE = ROOT / "dist/review-skill-release-20261017"
SOURCE = "0e3ecc0d1eda948b548feae03c7c9fa62944d52d"
VERSIONS = {
    "dota2forge-core": "0.1.0a9",
    "dota2forge-renderer": "0.1.0a8",
    "dota2forge-assets": "0.1.0a1",
    "dota2uid": "0.1.0a16",
    "astrbot-plugin-dota2forge": "0.1.0a14",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    candidate = STAGE / "candidate"
    manifest = json.loads((candidate / "manifest.json").read_bytes())
    assert manifest["source_ref"] == SOURCE and manifest["versions"] == VERSIONS
    for name, expected in manifest["source_sha256"].items():
        assert digest((ROOT / name).read_bytes()) == expected
    for name, expected in manifest["files_sha256"].items():
        assert digest((candidate / name).read_bytes()) == expected
    packages = []
    for path in (STAGE / "wheels").iterdir():
        if not path.name.startswith(("dota2", "astrbot_plugin_dota2forge")):
            continue
        if path.suffix == ".whl":
            with ZipFile(path) as packed:
                entries = {name: packed.read(name) for name in packed.namelist()}
        elif path.name.endswith(".tar.gz"):
            with tarfile.open(path, "r:gz") as packed:
                entries = {}
                for entry in packed:
                    if entry.isfile():
                        stream = packed.extractfile(entry)
                        assert stream is not None
                        entries[entry.name] = stream.read()
        else:
            raise AssertionError("Unexpected project payload")
        assert not any(
            Path(name).name.startswith(".env")
            or Path(name).suffix in (".db", ".sqlite", ".sqlite3")
            for name in entries
        )
        if path.name.startswith("dota2forge_core-") and path.suffix == ".whl":
            prefix = "dota2forge_core/infrastructure/review_skills/dota2-review/"
            resources = {
                name.removeprefix(prefix): data
                for name, data in entries.items()
                if name.startswith(prefix)
            }
            expected_resources = {
                "SKILL.md",
                "THIRD_PARTY_LICENSE.txt",
                "references/overview.md",
                "references/economy.md",
                "references/items.md",
                "references/team.md",
            }
            assert set(resources) == expected_resources
            for name, data in resources.items():
                assert data == (ROOT / "packages/dota2forge-core/src" / prefix / name).read_bytes()
        packages.append(
            {
                "filename": path.name,
                "bytes": path.stat().st_size,
                "sha256": digest(path.read_bytes()),
            }
        )
    assert len(packages) == 10
    summaries = []
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
        release = json.loads(expected["release.json"])
        excluded = "astrbot-plugin-dota2forge" if plugin == "Dota2UID" else "dota2uid"
        assert release["versions"] == {k: v for k, v in VERSIONS.items() if k != excluded}
        for entry in runtime["wheels"].values():
            assert digest((STAGE / "wheels" / entry["filename"]).read_bytes()) == entry["sha256"]
        screenshots = [name for name in expected if name.startswith("screenshots/")]
        assert len(screenshots) == 7
        for name in screenshots:
            assert (
                expected[name]
                == (
                    ROOT / "dist/plugin-distributions/review-skill-20261016" / plugin / name
                ).read_bytes()
            )
        assert "英雄攻略和 AI Tool 尚未实现" not in expected["README.md"].decode("utf-8")
        assert "本轮不发布AstrBot" not in expected["README.md"].decode("utf-8")
        if plugin == "Dota2UID":
            assert "0.1.0a16" in expected["INSTALL.md"].decode("utf-8")
        else:
            assert "0.1.0-alpha.14" in expected["INSTALL.md"].decode("utf-8")
            assert expected["CHANGELOG.md"].decode("utf-8").splitlines()[2] == (
                "## 0.1.0-alpha.14 — 2026-10-17"
            )
            assert (candidate / (plugin + ".zip")).stat().st_size <= 16_000_000
        summaries.append(
            {
                "plugin": plugin,
                "files": len(expected),
                "zip_matches_folder": True,
                "reviewed_screenshots": len(screenshots),
            }
        )
    report = {
        "passed": True,
        "source_commit": SOURCE,
        "versions": VERSIONS,
        "packages": packages,
        "candidates": summaries,
        "skill_resources": 6,
        "private_config_databases_absent": True,
    }
    (Path(__file__).parent / "candidate-validation.json").write_text(
        json.dumps(report, indent=2) + "\n", "utf-8"
    )
    print("Candidate versions, hashes, Skill resources, screenshots and ZIP bytes verified")


if __name__ == "__main__":
    main()
