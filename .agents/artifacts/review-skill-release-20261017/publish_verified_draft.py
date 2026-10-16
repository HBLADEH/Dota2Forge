"""Publish only the explicitly authorized, byte-verified release draft."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[2] / "dist/review-skill-release-20261017"
CONFIG = {
    "Dota2UID": (415213025, "v0.1.0a16", "8cfcfce5630f14135b0362d337e7dfd417b4a024"),
    "astrbot_plugin_dota2forge": (
        415215043,
        "v0.1.0a14",
        "c885bbfa6fac4f3a4863a08d868413722b55ae8e",
    ),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin", choices=CONFIG, required=True)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    release_id, tag, commit = CONFIG[args.plugin]
    repo = "HBLADEH/" + args.plugin

    def api(path):
        return json.loads(
            subprocess.check_output(
                ["gh", "api", f"repos/{repo}/{path}"], text=True, encoding="utf-8"
            )
        )

    folder = STAGE / "assets" / args.plugin
    expected = {
        p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in folder.iterdir()
        if p.is_file()
    }
    assert len(expected) == 11
    manifest = json.loads((folder / "release-assets.json").read_bytes())
    assert manifest["tag"] == tag and manifest["distribution_commit"] == commit
    assert manifest["source_commit"] == "0e3ecc0d1eda948b548feae03c7c9fa62944d52d"
    release = api(f"releases/{release_id}")
    assert release["tag_name"] == tag and release["prerelease"]
    assert release["draft"], "Only the task-owned draft may be published by this helper"
    actual = {a["name"]: a for a in release["assets"]}
    assert set(actual) == set(expected), f"Incomplete draft: {len(actual)}/11 assets"
    for name, data in expected.items():
        assert actual[name]["state"] == "uploaded"
        assert actual[name]["size"] == data["bytes"]
        assert actual[name]["digest"] == "sha256:" + data["sha256"]
    assert api(f"git/ref/tags/{tag}")["object"]["sha"] == commit
    assert api("branches/main")["commit"]["sha"] == commit
    report = {
        "passed": True,
        "plugin": args.plugin,
        "tag": tag,
        "distribution_commit": commit,
        "draft_id": release_id,
        "draft_assets_verified": expected,
        "published": False,
    }
    output = HERE / (args.plugin + "-draft-validation.json")
    output.write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    if args.publish:
        subprocess.run(
            [
                "gh",
                "release",
                "edit",
                tag,
                "-R",
                repo,
                "--draft=false",
                "--prerelease",
                "--target",
                commit,
            ],
            check=True,
        )
        public = api(f"releases/{release_id}")
        assert not public["draft"] and public["prerelease"] and public["tag_name"] == tag
        assert public["target_commitish"] == commit
        report["published"] = True
        report["url"] = public["html_url"]
        report["published_at"] = public["published_at"]
        output.write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "draft_assets_verified"}))


if __name__ == "__main__":
    main()
