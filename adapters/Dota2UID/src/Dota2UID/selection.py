"""Bounded, volatile state for selecting the last successfully delivered result."""

import math
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

from dota2forge_core import PlatformIdentity, PlayerBinding, RecentMatches

from .commands import Caller
from .config import Config


class SelectionError(Exception):
    def __init__(self, *, invalid_session: bool = False) -> None:
        super().__init__(
            "无法确认会话，不能使用战绩序号或页码。"
            if invalid_session
            else "该会话战绩列表不存在、已过期或绑定已变化，请重新查询 do战绩。"
        )


@dataclass(frozen=True, repr=False)
class ResultKey:
    identity: PlatformIdentity
    connection_id: str
    conversation_kind: str
    conversation_id: str


def result_key(caller: Caller, config: Config) -> ResultKey:
    identity = caller.identity(config)
    conversation = (
        caller.user_id if caller.conversation_kind == "direct" else caller.conversation_id
    )
    if caller.conversation_kind not in {"direct", "group"} or any(
        not isinstance(value, str)
        or not 1 <= len(value) <= 128
        or not value.isprintable()
        or any(char.isspace() for char in value)
        for value in (caller.connection_id, conversation)
    ):
        raise SelectionError(invalid_session=True)
    assert caller.connection_id is not None and conversation is not None
    return ResultKey(identity, caller.connection_id, caller.conversation_kind, conversation)


@dataclass(frozen=True, repr=False)
class DeliveredRecent:
    recent: RecentMatches
    binding: PlayerBinding | None
    expires_at: float


class RecentSelectionStore:
    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        capacity: int = 128,
        ttl_seconds: float = 600,
    ) -> None:
        if (
            type(capacity) is not int
            or not 1 <= capacity <= 128
            or isinstance(ttl_seconds, bool)
            or not 0 < ttl_seconds <= 600
            or not math.isfinite(ttl_seconds)
        ):
            raise ValueError("Expected bounded selection capacity and TTL")
        self._clock = clock
        self._capacity = capacity
        self._ttl = ttl_seconds
        self._results: OrderedDict[ResultKey, DeliveredRecent] = OrderedDict()

    def _expire(self) -> None:
        now = self._clock()
        for key, result in tuple(self._results.items()):
            if result.expires_at <= now:
                del self._results[key]

    def remember(
        self, key: ResultKey, recent: RecentMatches, binding: PlayerBinding | None
    ) -> None:
        self._expire()
        self._results[key] = DeliveredRecent(recent, binding, self._clock() + self._ttl)
        self._results.move_to_end(key)
        while len(self._results) > self._capacity:
            self._results.popitem(last=False)

    def get(self, key: ResultKey, binding: PlayerBinding | None) -> RecentMatches:
        self._expire()
        result = self._results.get(key)
        if result is None:
            raise SelectionError()
        if result.binding != binding:
            del self._results[key]
            raise SelectionError()
        return result.recent

    def invalidate(self, identity: PlatformIdentity) -> None:
        for key in tuple(self._results):
            if key.identity == identity:
                del self._results[key]

    def clear(self) -> None:
        self._results.clear()
