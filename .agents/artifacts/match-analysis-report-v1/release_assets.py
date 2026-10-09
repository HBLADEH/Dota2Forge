"""Explicit a9 release staging and anonymous verification; never a normal test."""

import argparse
import hashlib
import io
import json
import shutil
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile

REPOSITORY = "https://github.com/HBLADEH/Dota2UID"
TAG = "v0.1.0a9"
HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def tree(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def fetch(url, limit=32 * 1024 * 1024):
    request = Request(url, headers={"User-Agent": "Dota2Forge-a9-public-verification"})
    with urlopen(request, timeout=30) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Public response exceeded its bound")
    return data


def stage(args):
    candidate = args.candidate.resolve()
    expected = tree(candidate / "Dota2UID")
    runtime = json.loads(expected["runtime-wheels.json"])
    assert runtime["release_tag"] == TAG and runtime["repository"] == REPOSITORY
    target = args.assets.resolve()
    target.mkdir(parents=True, exist_ok=True)
    names = [
        "Dota2UID.zip",
        *sorted(entry["filename"] for entry in runtime["wheels"].values()),
        *sorted(
            entry["filename"].replace("-py3-none-any.whl", ".tar.gz")
            for entry in runtime["wheels"].values()
        ),
    ]
    rows = []
    for name in names:
        source = candidate / name if name == "Dota2UID.zip" else args.wheels / name
        data = source.read_bytes()
        destination = target / name
        if destination.exists() and destination.read_bytes() != data:
            raise ValueError("Existing release payload differs")
        shutil.copyfile(source, destination)
        rows.append({"filename": name, "bytes": len(data), "sha256": digest(data)})
    assert len(rows) == 9
    manifest = {
        "schema_version": 1,
        "repository": REPOSITORY,
        "tag": TAG,
        "source_commit": args.source_commit,
        "distribution_commit": args.distribution_commit,
        "runtime_manifest_sha256": digest(expected["runtime-wheels.json"]),
        "assets": rows,
    }
    sums = "".join(f"{row['sha256']}  {row['filename']}\n" for row in rows).encode("ascii")
    (target / "release-assets.json").write_bytes(json_bytes(manifest))
    (target / "SHA256SUMS").write_bytes(sums)
    (HERE / "release-assets.json").write_bytes(json_bytes(manifest))
    (HERE / "SHA256SUMS").write_bytes(sums)
    print("Staged 9 payloads and 2 checksum manifests.")


def verify(args):
    expected = tree(args.candidate.resolve() / "Dota2UID")
    archive = fetch("https://codeload.github.com/HBLADEH/Dota2UID/zip/" + args.distribution_commit)
    prefix = "Dota2UID-" + args.distribution_commit + "/"
    with ZipFile(io.BytesIO(archive)) as packed:
        public = {
            name.removeprefix(prefix): packed.read(name)
            for name in packed.namelist()
            if name.startswith(prefix) and not name.endswith("/")
        }
    assert public == expected
    api = json.loads(fetch("https://api.github.com/repos/HBLADEH/Dota2UID/releases/tags/" + TAG))
    assert api["tag_name"] == TAG and not api["draft"] and api["prerelease"]
    runtime = json.loads(expected["runtime-wheels.json"])
    manifest = json.loads((args.assets / "release-assets.json").read_bytes())
    rows = {row["filename"]: row for row in manifest["assets"]}
    for name in ("release-assets.json", "SHA256SUMS"):
        data = (args.assets / name).read_bytes()
        rows[name] = {"filename": name, "bytes": len(data), "sha256": digest(data)}
    listed = {entry["name"]: entry for entry in api["assets"]}
    assert set(listed) == set(rows)
    checked = []
    for name, row in rows.items():
        entry = listed[name]
        assert entry["size"] == row["bytes"]
        assert entry.get("digest") in (None, "sha256:" + row["sha256"])
        data = fetch(entry["browser_download_url"])
        assert len(data) == row["bytes"] and digest(data) == row["sha256"]
        assert data == (args.assets / name).read_bytes()
        if name == "Dota2UID.zip":
            with ZipFile(io.BytesIO(data)) as packed:
                assert {entry: packed.read(entry) for entry in packed.namelist()} == public
        elif name.endswith(".whl"):
            assert expected["runtime-wheels/" + name] == data
        checked.append({"filename": name, "bytes": len(data), "sha256": digest(data)})
        print("Anonymous asset verified: " + name, flush=True)
    assert manifest["source_commit"] == args.source_commit
    assert manifest["distribution_commit"] == args.distribution_commit
    assert runtime["wheels"]["dota2forge-core"]["filename"].startswith("dota2forge_core-0.1.0a6-")
    assert runtime["wheels"]["dota2uid"]["filename"].startswith("dota2uid-0.1.0a9-")
    report = {
        "passed": True,
        "anonymous": True,
        "repository": REPOSITORY,
        "tag": TAG,
        "source_commit": args.source_commit,
        "distribution_commit": args.distribution_commit,
        "repository_files_match_candidate": len(public),
        "zip_matches_repository": True,
        "runtime_manifest_sha256": digest(expected["runtime-wheels.json"]),
        "assets": checked,
        "production_host_modified": False,
        "chat_verified": False,
    }
    (HERE / "public-validation.json").write_bytes(json_bytes(report))
    print("Public repository, ZIP, 4 wheels and 11 assets match the reviewed candidate.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("stage", "verify"))
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--wheels", type=Path, default=Path("dist"))
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--distribution-commit", required=True)
    options = parser.parse_args()
    (stage if options.operation == "stage" else verify)(options)
