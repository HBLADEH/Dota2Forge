"""Explicit download before offline wheel smoke; never called by ordinary tests."""

import subprocess
import sys
from importlib.metadata import requires, version
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]


def runtime_requirements() -> list[str]:
    """Pin the installed locked runtime closure, including active platform markers."""
    pending = ["pillow", "httpx"]
    pinned: dict[str, str] = {}
    while pending:
        name = pending.pop().lower().replace("_", "-")
        if name in pinned:
            continue
        pinned[name] = version(name)
        for value in requires(name) or ():
            requirement = Requirement(value)
            if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
                pending.append(requirement.name)
    return [f"{name}=={value}" for name, value in sorted(pinned.items())]


def main() -> int:
    destination = ROOT / "dist"
    destination.mkdir(exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--only-binary=:all:",
            "--no-deps",
            "--dest",
            str(destination),
            *runtime_requirements(),
        ],
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
