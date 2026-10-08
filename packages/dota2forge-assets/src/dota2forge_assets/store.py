"""Owned local I/O, process leases, verified cache and immutable generations."""

import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, BinaryIO

from .models import AssetError, AssetLimits
from .sources import digest
from .validation import read_json, safe_path, validate_entry, validate_manifest


class OwnedIO:
    def __init__(self) -> None:
        self.tasks: set[asyncio.Task[Any]] = set()

    async def run[T](self, operation: Callable[[], T]) -> T:
        task = asyncio.create_task(asyncio.to_thread(operation))
        self.tasks.add(task)
        try:
            return await asyncio.shield(task)
        finally:
            if task.done():
                self.tasks.discard(task)

    async def wait(self) -> None:
        while self.tasks:
            tasks = tuple(self.tasks)
            await asyncio.gather(*tasks, return_exceptions=True)
            self.tasks.difference_update(tasks)


class Lease:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.stream: BinaryIO | None = None

    def acquire(self) -> None:
        if self.stream is not None:
            return
        stream = self.path.open("a+b")
        try:
            if sys.platform == "win32":
                import msvcrt

                if stream.seek(0, 2) == 0:
                    stream.write(b"\0")
                    stream.flush()
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            stream.close()
            raise AssetError("busy") from None
        self.stream = stream

    def close(self) -> None:
        if self.stream is not None:
            self.stream.close()
            self.stream = None


class Store:
    def __init__(self, root: Path, limits: AssetLimits) -> None:
        self.root = Path(os.path.abspath(root))
        self.limits = limits
        self.io = OwnedIO()
        self.lease = Lease(self.root / ".lease")
        self.stopping = threading.Event()
        self._writes = threading.RLock()
        self._used_bytes: int | None = None

    def open(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        safe_path(self.root, ".lease")
        self.lease.acquire()
        for name in ("cache", "staging", "generations"):
            safe_path(self.root, name).mkdir(exist_ok=True)
        for stage in safe_path(self.root, "staging").iterdir():
            if re.fullmatch(r"[0-9a-f]{32}", stage.name) and not stage.is_symlink():
                shutil.rmtree(stage)
        self._used_bytes = self._scan_bytes(self.root)

    @staticmethod
    def _scan_bytes(root: Path) -> int:
        used = 0
        for path in root.rglob("*"):
            if path.is_symlink():
                raise AssetError("path")
            if path.is_file():
                used += path.stat().st_size
        return used

    def _check_budget(self, additional: int) -> None:
        if self._used_bytes is None:
            self._used_bytes = self._scan_bytes(self.root)
        if self._used_bytes + additional > self.limits.root_bytes:
            raise AssetError("budget")

    def write(self, path: Path, data: bytes, *, status: bool = False) -> None:
        with self._writes:
            if self.stopping.is_set() and not status:
                raise AssetError("closed")
            safe_path(self.root, path.relative_to(self.root).as_posix())
            self._check_budget(len(data))
            previous_size = path.stat().st_size if path.exists() else 0
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix=".asset-", dir=path.parent)
            temporary = Path(name)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                if self.stopping.is_set() and not status:
                    raise AssetError("closed")
                temporary.replace(path)
                assert self._used_bytes is not None
                self._used_bytes += len(data) - previous_size
            finally:
                temporary.unlink(missing_ok=True)

    def write_json(self, path: Path, raw: dict[str, Any], *, status: bool = False) -> None:
        data = (json.dumps(raw, ensure_ascii=False, indent=2) + "\n").encode()
        if len(data) > self.limits.manifest_bytes:
            raise AssetError("manifest")
        self.write(path, data, status=status)

    def current(self) -> tuple[Path, dict[str, Any], dict[str, Any]] | None:
        pointer = safe_path(self.root, "current.json")
        if not pointer.exists():
            return None
        raw = read_json(pointer, self.limits.manifest_bytes)
        name = raw.get("generation")
        if (
            type(raw.get("schema_version")) is not int
            or raw["schema_version"] != 1
            or not isinstance(name, str)
            or re.fullmatch(r"[0-9a-f]{32}", name) is None
            or type(raw.get("complete")) is not bool
        ):
            raise AssetError("manifest")
        root = safe_path(self.root, f"generations/{name}")
        manifest = validate_manifest(root, self.limits)
        if digest((root / "manifest.json").read_bytes()) != raw.get("manifest_sha256"):
            raise AssetError("digest")
        return root, manifest, raw

    def state(self) -> dict[str, Any]:
        path = safe_path(self.root, "status.json")
        return read_json(path, self.limits.manifest_bytes) if path.exists() else {}

    def catalog(self, kind: str) -> bytes | None:
        path = safe_path(self.root, f"cache/catalogs/{kind}.json")
        if not path.exists():
            return None
        if path.stat().st_size > self.limits.response_bytes:
            raise AssetError("size")
        return path.read_bytes()

    def save_catalog(self, kind: str, data: bytes) -> None:
        self.write(safe_path(self.root, f"cache/catalogs/{kind}.json"), data)

    def cache(self, kind: str, key: str, url: str) -> tuple[dict[str, Any], Path | None] | None:
        root = safe_path(self.root, f"cache/{digest(url.encode())}")
        metadata = root / "entry.json"
        if not metadata.exists():
            return None
        try:
            row = read_json(metadata, self.limits.manifest_bytes)
            if row.get("source") != url:
                return None
            validate_entry(root, kind, key, row, self.limits)
            return row, root / row["file"] if row["status"] == "available" else None
        except (OSError, AssetError):
            return None

    def save_cache(
        self, kind: str, key: str, url: str, row: dict[str, Any], data: bytes | None
    ) -> None:
        root = safe_path(self.root, f"cache/{digest(url.encode())}")
        if data is not None:
            self.write(root / f"{kind}/{key}.png", data)
        self.write_json(root / "entry.json", row)

    def copy_entry(self, stage: Path, row: dict[str, Any], source: Path | None) -> None:
        if source is not None:
            self.write(safe_path(stage, row["file"]), source.read_bytes())

    def finalize(self, name: str, manifest: dict[str, Any]) -> Path:
        stage = safe_path(self.root, f"staging/{name}")
        self.write_json(stage / "manifest.json", manifest)
        validate_manifest(stage, self.limits)
        with self._writes:
            self._used_bytes = self._scan_bytes(self.root)
            self._check_budget(0)
        generation = safe_path(self.root, f"generations/{name}")
        if self.stopping.is_set():
            raise AssetError("closed")
        stage.replace(generation)
        return generation

    def commit(self, generation: Path, complete: bool) -> None:
        if generation.parent != safe_path(self.root, "generations"):
            raise AssetError("path")
        self.write_json(
            self.root / "current.json",
            {
                "schema_version": 1,
                "generation": generation.name,
                "complete": complete,
                "manifest_sha256": digest((generation / "manifest.json").read_bytes()),
            },
        )

    def collect(self, keep: set[str]) -> None:
        for path in safe_path(self.root, "generations").iterdir():
            if re.fullmatch(r"[0-9a-f]{32}", path.name) and path.name not in keep:
                if path.is_symlink():
                    raise AssetError("path")
                self._remove_tree(path)

    def _remove_tree(self, path: Path) -> None:
        with self._writes:
            size = self._scan_bytes(path)
            shutil.rmtree(path)
            if self._used_bytes is not None:
                self._used_bytes -= size

    def discard_stage(self, name: str) -> None:
        if re.fullmatch(r"[0-9a-f]{32}", name) is None:
            raise AssetError("path")
        path = safe_path(self.root, f"staging/{name}")
        if path.exists():
            self._remove_tree(path)
