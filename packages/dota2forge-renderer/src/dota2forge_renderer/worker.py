"""One owned rendering thread per instance; cancelled waiters do not abandon it."""

import asyncio

from .cards import Card, ImageArtifact, RenderError
from .engine import PillowRenderer


class AsyncRenderer:
    def __init__(self, engine: PillowRenderer | None = None) -> None:
        self._engine = engine if engine is not None else PillowRenderer()
        self._lock = asyncio.Lock()
        self._worker: asyncio.Task[ImageArtifact] | None = None
        self._closed = False
        self._close_task: asyncio.Task[None] | None = None
        self._waiting = 0

    async def _drain(self) -> None:
        worker = self._worker
        if worker is not None:
            try:
                await asyncio.shield(worker)
            except RenderError:
                pass
            finally:
                if worker.done():
                    self._worker = None

    async def render(self, card: Card) -> ImageArtifact:
        if self._closed or self._waiting >= 4:
            raise RenderError()
        self._waiting += 1
        try:
            async with self._lock:
                await self._drain()
                if self._closed:
                    raise RenderError()
                self._worker = asyncio.create_task(asyncio.to_thread(self._engine.render, card))
                worker = self._worker
                try:
                    return await asyncio.shield(worker)
                finally:
                    if worker.done():
                        self._worker = None
        finally:
            self._waiting -= 1

    async def close(self) -> None:
        if self._close_task is None:
            self._closed = True
            self._close_task = asyncio.create_task(self._finish_close())
        await asyncio.shield(self._close_task)

    async def _finish_close(self) -> None:
        async with self._lock:
            try:
                await self._drain()
            finally:
                self._engine.close()
