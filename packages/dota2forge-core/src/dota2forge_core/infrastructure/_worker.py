"""Keep ownership of an already-started storage transaction until it exits."""

import asyncio
from collections.abc import Callable


async def run_storage[T](operation: Callable[[], T]) -> T:
    worker = asyncio.create_task(asyncio.to_thread(operation))
    try:
        return await asyncio.shield(worker)
    except asyncio.CancelledError:
        while not worker.done():
            try:
                await asyncio.shield(worker)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        # Retrieve an eventual transaction failure; cancellation still describes
        # the caller's outcome, and an already-running write may have committed.
        if not worker.cancelled():
            worker.exception()
        raise
