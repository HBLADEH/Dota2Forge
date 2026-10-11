"""Explicit two-plugin release staging and anonymous verification, outside normal tests."""

import argparse
import hashlib
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def tree(root):
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts
    }


def fetch(url):
    with urlopen(
        Request(url, headers={"User-Agent": "Dota2Forge-release-verification"}), timeout=30
    ) as response:
        data = response.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024:
        raise ValueError("Public response exceeded bound")
    return data


def stage(args):
    expected = tree(args.candidate / args.plugin)
    runtime = json.loads(expected["runtime-wheels.json"])
    repository = "https://github.com/HBLADEH/" + args.plugin
    assert runtime["repository"] == repository
    args.assets.mkdir(parents=True, exist_ok=True)
    names = [args.plugin + ".zip"]
    names.extend(sorted(entry["filename"] for entry in runtime["wheels"].values()))
    names.extend(sorted(name.replace("-py3-none-any.whl", ".tar.gz") for name in names[1:]))
    rows = []
    for name in names:
        source = args.candidate / name if name.endswith(".zip") else args.wheels / name
        data = source.read_bytes()
        destination = args.assets / name
        if destination.exists() and destination.read_bytes() != data:
            raise ValueError("Existing payload differs")
        destination.write_bytes(data)
        rows.append({"filename": name, "bytes": len(data), "sha256": digest(data)})
    manifest = {
        "schema_version": 1,
        "repository": repository,
        "tag": runtime["release_tag"],
        "source_commit": args.source_commit,
        "distribution_commit": args.distribution_commit,
        "runtime_manifest_sha256": digest(expected["runtime-wheels.json"]),
        "assets": rows,
    }
    (args.assets / "release-assets.json").write_text(json.dumps(manifest, indent=2) + "\n", "utf-8")
    (args.assets / "SHA256SUMS").write_text(
        "".join(f"{row['sha256']}  {row['filename']}\n" for row in rows), "utf-8"
    )
    print(f"Staged {len(rows)} payloads and 2 manifests for {args.plugin}")


def verify(args):
    expected = tree(args.candidate / args.plugin)
    manifest = json.loads((args.assets / "release-assets.json").read_bytes())
    archive = fetch(
        f"https://codeload.github.com/HBLADEH/{args.plugin}/zip/{args.distribution_commit}"
    )
    prefix = args.plugin + "-" + args.distribution_commit + "/"
    with ZipFile(io.BytesIO(archive)) as packed:
        public = {
            name.removeprefix(prefix): packed.read(name)
            for name in packed.namelist()
            if name.startswith(prefix) and not name.endswith("/")
        }
    assert public == expected
    api = json.loads(
        fetch(f"https://api.github.com/repos/HBLADEH/{args.plugin}/releases/tags/{manifest['tag']}")
    )
    assert api["tag_name"] == manifest["tag"] and not api["draft"] and api["prerelease"]
    rows = {row["filename"]: row for row in manifest["assets"]}
    for name in ("release-assets.json", "SHA256SUMS"):
        data = (args.assets / name).read_bytes()
        rows[name] = {"filename": name, "bytes": len(data), "sha256": digest(data)}
    entries = {entry["name"]: entry for entry in api["assets"]}
    assert set(entries) == set(rows)
    for name, row in rows.items():
        entry = entries[name]
        assert entry["size"] == row["bytes"]
        assert entry.get("digest") in (None, "sha256:" + row["sha256"])
        data = fetch(entry["browser_download_url"])
        assert data == (args.assets / name).read_bytes() and digest(data) == row["sha256"]
        if name.endswith(".zip"):
            with ZipFile(io.BytesIO(data)) as packed:
                assert {name: packed.read(name) for name in packed.namelist()} == public
        print("Anonymous asset verified: " + name, flush=True)
    assert manifest["source_commit"] == args.source_commit
    assert manifest["distribution_commit"] == args.distribution_commit
    if args.plugin.startswith("astrbot"):
        assert b"0.1.0-alpha.10" in public["CHANGELOG.md"]
    report = {
        "passed": True,
        "anonymous": True,
        "repository": manifest["repository"],
        "tag": manifest["tag"],
        "source_commit": args.source_commit,
        "distribution_commit": args.distribution_commit,
        "repository_files_match_candidate": len(public),
        "zip_matches_repository": True,
        "assets": list(rows.values()),
        "production_host_modified": False,
        "chat_verified": False,
    }
    (Path(__file__).parent / (args.plugin + "-public-validation.json")).write_text(
        json.dumps(report, indent=2) + "\n", "utf-8"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("stage", "verify"))
    parser.add_argument(
        "--plugin", choices=("Dota2UID", "astrbot_plugin_dota2forge"), required=True
    )
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--wheels", type=Path, default=Path("dist"))
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--distribution-commit", required=True)
    options = parser.parse_args()
    (stage if options.operation == "stage" else verify)(options)
