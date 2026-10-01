import asyncio
import threading

import pytest
from dota2forge_renderer import AsyncRenderer, ImageArtifact, MenuCard, RenderError


class SlowEngine:
    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.active = 0
        self.max_active = 0
        self.closed = False
        self.fail = None

    def render(self, card):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        self.entered.set()
        try:
            assert self.release.wait(5)
            if self.fail is not None:
                raise self.fail
            return ImageArtifact(b"\x89PNG\r\n\x1a\n", 780, 1)
        finally:
            self.active -= 1

    def close(self):
        assert self.active == 0
        self.closed = True


async def wait_entered(engine):
    for _ in range(500):
        if engine.entered.is_set():
            return
        await asyncio.sleep(0.001)
    pytest.fail("Render thread never started")


def test_cancelled_render_retains_one_thread_and_close_survives_waiter_cancel(run_async):
    async def check():
        engine = SlowEngine()
        renderer = AsyncRenderer(engine)
        task = asyncio.create_task(renderer.render(MenuCard()))
        try:
            await wait_entered(engine)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            next_task = asyncio.create_task(renderer.render(MenuCard()))
            await asyncio.sleep(0)
            assert engine.max_active == 1
            closing = asyncio.create_task(renderer.close())
            await asyncio.sleep(0)
            closing.cancel()
            with pytest.raises(asyncio.CancelledError):
                await closing
            assert not engine.closed
            engine.release.set()
            with pytest.raises(RenderError):
                await next_task
            await renderer.close()
            assert engine.closed and engine.max_active == 1 and renderer._worker is None
            with pytest.raises(RenderError):
                await renderer.render(MenuCard())
        finally:
            engine.release.set()
            await renderer.close()

    run_async(check())


def test_cancelled_worker_error_is_drained_and_waiting_capacity_is_bounded(run_async):
    async def check():
        engine = SlowEngine()
        renderer = AsyncRenderer(engine)
        first = asyncio.create_task(renderer.render(MenuCard()))
        pending = []
        try:
            await wait_entered(engine)
            pending = [asyncio.create_task(renderer.render(MenuCard())) for _ in range(3)]
            await asyncio.sleep(0)
            with pytest.raises(RenderError):
                await renderer.render(MenuCard())
            for task in [first, *pending]:
                task.cancel()
            await asyncio.gather(first, *pending, return_exceptions=True)
            engine.fail = RenderError()
            engine.release.set()
            await renderer.close()
            assert engine.closed and renderer._waiting == 0
        finally:
            engine.release.set()
            await renderer.close()

    run_async(check())
