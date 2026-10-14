"""Bounded process-local observations and cancellation-safe request coalescing."""

import asyncio
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import monotonic

from ..domain.errors import DataSource, ProviderError, ProviderErrorCode


@dataclass
class _Flight[T]:
    task: asyncio.Task[T]
    waiters: int = 0


class ObservationCache[T]:
    def __init__(
        self, *, ttl: float, capacity: int = 128, clock: Callable[[], float] = monotonic
    ) -> None:
        self._ttl, self._capacity, self._clock = ttl, capacity, clock
        self._values: OrderedDict[str, tuple[float, T]] = OrderedDict()
        self._flights: dict[str, _Flight[T]] = {}
        self._closed = False

    async def get(self, key: str, load: Callable[[], Awaitable[T]]) -> T:
        if self._closed:
            raise ProviderError(ProviderErrorCode.UNAVAILABLE, DataSource.STRATZ)
        cached = self._values.get(key)
        if cached is not None and cached[0] > self._clock():
            self._values.move_to_end(key)
            return cached[1]
        self._values.pop(key, None)
        flight = self._flights.get(key)
        if flight is None:
            if len(self._flights) >= 16:
                raise ProviderError(ProviderErrorCode.UNAVAILABLE, DataSource.STRATZ)
            flight = _Flight(asyncio.create_task(self._load(key, load)))
            self._flights[key] = flight
        flight.waiters += 1
        try:
            return await asyncio.shield(flight.task)
        finally:
            flight.waiters -= 1
            if flight.waiters == 0:
                if not flight.task.done():
                    flight.task.cancel()
                await asyncio.gather(flight.task, return_exceptions=True)
                if self._flights.get(key) is flight:
                    del self._flights[key]

    async def _load(self, key: str, load: Callable[[], Awaitable[T]]) -> T:
        value = await load()
        if not self._closed:
            self._values[key] = self._clock() + self._ttl, value
            self._values.move_to_end(key)
            while len(self._values) > self._capacity:
                self._values.popitem(last=False)
        return value

    async def close(self) -> None:
        self._closed = True
        self._values.clear()
        tasks = tuple(f.task for f in self._flights.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._flights.clear()
