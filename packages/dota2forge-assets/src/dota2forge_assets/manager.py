"""One owned preparation job; successful files survive unrelated source failures."""

import asyncio
import copy
import logging
import math
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any

import httpx

from .http import Fetcher
from .models import KINDS, AssetCounts, AssetError, AssetLimits, AssetStatus, aware_time, utc_now
from .sources import CDN, FEEDS, RIGHTS, STATIC_ART, catalog, digest, entry
from .store import Store
from .validation import png_size

Activate = Callable[[Path, Callable[[], Awaitable[None]]], Awaitable[None]]
ClientFactory = Callable[[], httpx.AsyncClient]
LOGGER = logging.getLogger("Dota2Forge.assets")


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(trust_env=False)


class AssetManager:
    def __init__(
        self,
        root: Path,
        *,
        limits: AssetLimits | None = None,
        client_factory: ClientFactory = make_client,
        clock: Callable[[], datetime] = utc_now,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        activate: Activate | None = None,
    ) -> None:
        self.limits = limits or AssetLimits()
        self.store = Store(root, self.limits)
        self.client_factory, self.clock, self.sleep, self.activate = (
            client_factory,
            clock,
            sleep,
            activate,
        )
        self._opened = False
        self._closed = False
        self._path: Path | None = None
        self._manifest: dict[str, Any] = {}
        self._complete = False
        self._status = AssetStatus()
        self._failures: dict[tuple[str, str], str] = {}
        self._reused: dict[str, int] = {}
        self._candidate: dict[str, Any] = {}
        self._plan: set[tuple[str, str]] = set()
        self._finished: set[tuple[str, str]] = set()
        self._retry_until: datetime | None = None
        self._operation_lock = asyncio.Lock()
        self._job: asyncio.Task[None] | None = None
        self._close_task: asyncio.Task[None] | None = None

    @property
    def path(self) -> Path | None:
        return self._path

    def status(self) -> AssetStatus:
        counts = {}
        manifest = self._candidate if self._status.state == "downloading" else self._manifest
        for kind in KINDS:
            rows = manifest.get(kind, {})
            counts[kind] = AssetCounts(
                sum(r["status"] == "available" for r in rows.values()),
                sum(r["status"] == "missing" for r in rows.values()),
                sum(k == kind for k, _ in self._failures),
                self._reused.get(kind, 0),
            )
        remaining = (
            max(0, math.ceil((self._retry_until - aware_time(self.clock())).total_seconds()))
            if self._retry_until is not None
            else 0
        )
        return replace(self._status, counts=counts, retry_after_seconds=remaining)

    async def open(self) -> None:
        async with self._operation_lock:
            await self._open()

    async def _open(self) -> None:
        if self._opened or self._closed:
            return
        try:
            await self.store.io.run(self.store.open)
            self._opened = True
            current = await self.store.io.run(self.store.current)
            if current is not None:
                self._path, self._manifest, pointer = current
                self._complete = (
                    pointer["complete"]
                    and all(self._manifest.get(kind) for kind in FEEDS)
                    and all(
                        set(group) <= set(self._manifest.get(kind, {}))
                        for kind, group in STATIC_ART.items()
                    )
                )
            saved = await self.store.io.run(self.store.state)
            attempt, success = (
                self._time(saved.get("last_attempt")),
                self._time(saved.get("last_success")),
            )
            failures = saved.get("failures", [])
            if not isinstance(failures, list) or len(failures) > 12288:
                raise AssetError("manifest")
            for failure in failures:
                if (
                    not isinstance(failure, dict)
                    or failure.get("kind") not in KINDS
                    or not isinstance(failure.get("key"), str)
                    or not isinstance(failure.get("code"), str)
                ):
                    raise AssetError("manifest")
                self._failures[failure["kind"], failure["key"]] = failure["code"]
            self._status = AssetStatus(
                "ready"
                if self._complete
                else "partial"
                if self._path
                else "failed"
                if attempt
                else "checking",
                self._path.name if self._path else None,
                last_attempt=attempt,
                last_success=success,
                error="incomplete" if attempt and not self._complete else None,
            )
        except (OSError, AssetError) as error:
            self._status = replace(
                self._status,
                state="busy"
                if isinstance(error, AssetError) and error.code == "busy"
                else "failed",
                error=error.code if isinstance(error, AssetError) else "storage",
            )

    @staticmethod
    def _time(value: Any) -> datetime | None:
        if value is None:
            return None
        try:
            return aware_time(datetime.fromisoformat(value))
        except (ValueError, TypeError, AssetError):
            raise AssetError("manifest") from None

    async def ensure(self, *, automatic: bool = False) -> str | None:
        return await self._schedule(False, automatic)

    async def update(self) -> str | None:
        return await self._schedule(True, False)

    async def _schedule(self, refresh: bool, automatic: bool) -> str | None:
        async with self._operation_lock:
            if self._closed:
                return None
            await self._open()
            if self._closed or self.store.lease.stream is None:
                return None
            if self._job is not None and not self._job.done():
                return self._status.task_id
            if self._complete and not refresh:
                return None
            now = aware_time(self.clock())
            cooldown = self.limits.auto_cooldown if automatic else self.limits.manual_cooldown
            if self._status.last_attempt is not None:
                until = self._status.last_attempt + timedelta(seconds=cooldown)
                if until > now:
                    self._retry_until = min(until, now + timedelta(seconds=cooldown))
                    return None
            self._retry_until = None
            task_id = uuid.uuid4().hex
            self._status = replace(
                self._status,
                state="downloading",
                task_id=task_id,
                last_attempt=now,
                completed=0,
                total=None,
                downloaded_bytes=0,
                error=None,
            )
            await self._persist()
            if self._closed:
                self._status = replace(self._status, state="cancelled")
                return None
            self._job = asyncio.create_task(self._prepare(task_id, refresh))
            self._job.add_done_callback(self._observe)
            return task_id

    @staticmethod
    def _observe(task: asyncio.Task[None]) -> None:
        if not task.cancelled():
            task.exception()

    async def wait(self) -> None:
        if self._job is not None:
            await asyncio.shield(self._job)

    async def _persist(self) -> None:
        if self.store.lease.stream is None:
            return
        status = self._status
        raw = {
            "state": status.state,
            "last_attempt": status.last_attempt.isoformat() if status.last_attempt else None,
            "last_success": status.last_success.isoformat() if status.last_success else None,
            "failures": [
                {"kind": k, "key": key, "code": code}
                for (k, key), code in sorted(self._failures.items())
            ],
        }
        try:
            await self.store.io.run(
                lambda: self.store.write_json(self.store.root / "status.json", raw, status=True)
            )
        except (OSError, AssetError):
            self._status = replace(self._status, error="storage")

    async def _prepare(self, name: str, refresh: bool) -> None:
        previous_failures = set(self._failures)
        self._failures, self._reused, self._plan, self._finished = {}, {}, set(), set()
        self._candidate = copy.deepcopy(self._manifest) or {"version": 1, "rights": RIGHTS}
        self._candidate.setdefault("catalogs", {})
        stage = self.store.root / "staging" / name
        try:
            async with asyncio.timeout(self.limits.job_seconds):
                await self.store.io.run(lambda: stage.mkdir(parents=True))
                if self._path is not None:
                    for kind in KINDS:
                        for row in self._manifest.get(kind, {}).values():
                            source = (
                                self._path / row["file"] if row["status"] == "available" else None
                            )
                            await self.store.io.run(
                                partial(self.store.copy_entry, stage, row, source)
                            )
                client = self.client_factory()
                try:
                    fetcher = Fetcher(client, self.limits, self.clock, self.sleep)
                    jobs: list[tuple[str, str, str, str, str | None]] = []
                    for kind, (url, key, prefix) in FEEDS.items():
                        try:
                            data = (
                                None
                                if refresh
                                else await self.store.io.run(partial(self.store.catalog, kind))
                            )
                            if data is not None:
                                try:
                                    catalog(data, key, prefix)
                                except AssetError:
                                    data = None
                            if data is None:
                                data = await fetcher.fetch(url)
                            rows = catalog(data, key, prefix)
                            await self.store.io.run(partial(self.store.save_catalog, kind, data))
                            self._candidate["catalogs"][kind] = {
                                "source": url,
                                "response_sha256": digest(data),
                            }
                            jobs.extend(
                                (
                                    kind,
                                    str(r["id"]),
                                    f"{CDN}/{kind}/{r['name'].removeprefix(prefix)}.png",
                                    r["name_loc"],
                                    r["name"],
                                )
                                for r in rows
                            )
                        except AssetError as error:
                            self._failures[kind, "catalog"] = error.code
                    jobs.extend(
                        (kind, key, url, title, None)
                        for kind, group in STATIC_ART.items()
                        for key, (url, title) in group.items()
                    )
                    self._plan = {(kind, key) for kind, key, *_ in jobs}
                    self._status = replace(
                        self._status, total=None if self._failures else len(jobs)
                    )
                    slots = asyncio.Semaphore(self.limits.workers)

                    async def download(job: tuple[str, str, str, str, str | None]) -> None:
                        async with slots:
                            await self._download(stage, fetcher, job, refresh, previous_failures)

                    children = [asyncio.create_task(download(job)) for job in jobs]
                    try:
                        await asyncio.gather(*children)
                    finally:
                        for child in children:
                            if not child.done():
                                child.cancel()
                        await asyncio.gather(*children, return_exceptions=True)
                finally:
                    await client.aclose()
            await self.store.io.wait()
            await self._publish(name)
        except TimeoutError:
            await self.store.io.wait()
            for pair in self._plan - self._finished:
                self._failures[pair] = "timeout"
            if not self._plan:
                self._failures["heroes", "catalog"] = "timeout"
            self._status = replace(self._status, error="timeout")
            try:
                await self._publish(name)
            except (AssetError, OSError):
                self._status = replace(
                    self._status,
                    state="cancelled" if self._closed else "failed",
                    error=None if self._closed else "timeout",
                )
        except asyncio.CancelledError:
            self._status = replace(self._status, state="cancelled", error=None)
            raise
        except (AssetError, OSError) as error:
            code = error.code if isinstance(error, AssetError) else "storage"
            self._status = replace(
                self._status, state="cancelled" if code == "closed" else "failed", error=code
            )
        except Exception as error:
            self._status = replace(self._status, state="failed", error="unexpected")
            LOGGER.error("Asset preparation failed error_type=%s", type(error).__name__)
            raise
        finally:
            await self.store.io.wait()
            try:
                await self.store.io.run(lambda: self.store.discard_stage(name))
            except (OSError, AssetError):
                self._status = replace(self._status, error="storage")
            await self._persist()
            LOGGER.info(
                "Asset preparation state=%s failed=%d", self._status.state, len(self._failures)
            )

    async def _download(
        self,
        stage: Path,
        fetcher: Fetcher,
        job: tuple[str, str, str, str, str | None],
        refresh: bool,
        previous_failures: set[tuple[str, str]],
    ) -> None:
        kind, key, url, title, internal = job
        finished = False
        self._candidate.setdefault(kind, {})
        old = self._manifest.get(kind, {}).get(key)
        try:
            cached = None
            if not refresh and (kind, key) not in previous_failures:
                if old is not None and old.get("source") == url:
                    cached = (
                        old,
                        self._path / old["file"]
                        if old["status"] == "available" and self._path
                        else None,
                    )
                else:
                    cached = await self.store.io.run(lambda: self.store.cache(kind, key, url))
            if cached is not None:
                row, source = cached
                await self.store.io.run(lambda: self.store.copy_entry(stage, row, source))
                self._reused[kind] = self._reused.get(kind, 0) + 1
            else:
                row = entry(kind, key, url, title, aware_time(self.clock()))
                if internal is not None:
                    row["name"] = internal
                try:
                    data = await fetcher.fetch(url)
                except AssetError as error:
                    if error.code != "http_404":
                        raise
                    data = None
                    row |= {"status": "missing", "reason": "http_404", "file": None, "sha256": None}
                else:
                    assert data is not None
                    width, height = await self.store.io.run(partial(png_size, data, self.limits))
                    row |= {
                        "status": "available",
                        "file": f"{kind}/{key}.png",
                        "sha256": digest(data),
                        "width": width,
                        "height": height,
                    }
                    self._status = replace(
                        self._status, downloaded_bytes=self._status.downloaded_bytes + len(data)
                    )
                await self.store.io.run(lambda: self.store.save_cache(kind, key, url, row, data))
                cached = await self.store.io.run(lambda: self.store.cache(kind, key, url))
                if cached is None:
                    raise AssetError("digest")
                await self.store.io.run(lambda: self.store.copy_entry(stage, row, cached[1]))
            self._candidate[kind][key] = row
            finished = True
        except AssetError as error:
            self._failures[kind, key] = error.code
            finished = True
        finally:
            if finished:
                self._finished.add((kind, key))
                self._status = replace(self._status, completed=self._status.completed + 1)

    @staticmethod
    def _content(manifest: dict[str, Any]) -> dict[str, Any]:
        return {
            kind: {
                key: {k: v for k, v in row.items() if k != "fetched_at"}
                for key, row in manifest.get(kind, {}).items()
            }
            for kind in KINDS
        }

    async def _publish(self, name: str) -> None:
        if self._closed:
            raise AssetError("closed")
        complete = not self._failures
        usable = any(
            row["status"] == "available"
            for kind in KINDS
            if kind != "decor"
            for row in self._candidate.get(kind, {}).values()
        )
        if not usable:
            self._status = replace(self._status, state="failed", error="no_usable_assets")
            return
        if self._path is not None and self._content(self._candidate) == self._content(
            self._manifest
        ):
            await self.store.io.run(partial(self.store.commit, self._path, complete))
        else:
            self._candidate["fetched_at"] = aware_time(self.clock()).isoformat()
            generation = await self.store.io.run(lambda: self.store.finalize(name, self._candidate))

            async def commit() -> None:
                if self._closed:
                    raise AssetError("closed")
                await self.store.io.run(lambda: self.store.commit(generation, complete))

            previous = self._path.name if self._path else None
            if self.activate is not None:
                await self.activate(generation, commit)
            else:
                await commit()
            self._path, self._manifest = generation, self._candidate
            keep = {name}
            if previous is not None:
                keep.add(previous)
            await self.store.io.run(partial(self.store.collect, keep))
        self._complete = complete
        self._status = replace(
            self._status,
            state="ready" if complete else "partial",
            generation=self._path.name if self._path else None,
            last_success=aware_time(self.clock()) if complete else self._status.last_success,
            error="incomplete" if not complete else None,
        )

    async def close(self) -> None:
        if self._close_task is None:
            self._closed = True
            self.store.stopping.set()
            if self._job is not None:
                if not self._job.done():
                    self._status = replace(self._status, state="cancelled", error=None)
                self._job.cancel()
            self._close_task = asyncio.create_task(self._finish_close())
        await asyncio.shield(self._close_task)

    async def _finish_close(self) -> None:
        if self._job is not None:
            await asyncio.gather(self._job, return_exceptions=True)
        await self.store.io.wait()
        async with self._operation_lock:
            self.store.lease.close()
