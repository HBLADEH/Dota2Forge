"""Verify committed GsCore candidate bytes and runtime wheel hashes."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CANDIDATE = ROOT / "dist/plugin-distributions/guide-labels-20261015/Dota2UID"
REPOSITORY = ROOT / "dist/stratz-push/Dota2UID"


def blob(path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(REPOSITORY), "show", "HEAD:" + path])


def main() -> None:
    files = tuple(path for path in CANDIDATE.rglob("*") if path.is_file())
    for path in files:
        assert path.resolve().is_relative_to(CANDIDATE.resolve())
        assert path.read_bytes() == blob(path.relative_to(CANDIDATE).as_posix())
    manifest = json.loads(blob("runtime-wheels.json"))
    for wheel in manifest["wheels"].values():
        data = blob("runtime-wheels/" + wheel["filename"])
        assert hashlib.sha256(data).hexdigest() == wheel["sha256"]
    print(
        json.dumps(
            {
                "committed_files_verified": len(files),
                "committed_wheels_verified": len(manifest["wheels"]),
            }
        )
    )


if __name__ == "__main__":
    main()
