"""Host-owned finite polling and delivery; construction starts no background tasks."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from dota2forge_core import (
    BEIJING,
    BindingNotFoundError,
    DeliveryOutcome,
    Dota2Service,
    PlatformIdentity,
    ProviderErrorCode,
    SQLiteSubscriptionRepository,
    SubscriptionCapacityError,
    SubscriptionEvent,
    SubscriptionKind,
    SubscriptionRepositoryError,
    SubscriptionScope,
    SubscriptionService,
    ValidationError,
)
from dota2forge_renderer.subscriptions import subscription_event_text

SUBSCRIPTION_COMMANDS = (
    "do订阅",
    "do订阅玩家",
    "do订阅比赛",
    "do订阅列表",
    "do取消订阅",
    "do重试推送",
)
KINDS = {
    "比赛": SubscriptionKind.NEW_MATCH,
    "段位": SubscriptionKind.RANK_CHANGE,
    "日报": SubscriptionKind.DAILY_REPORT,
}
LABELS = {kind: label for label, kind in KINDS.items()}
LABELS[SubscriptionKind.MATCH_REPORT] = "指定比赛"
SubscriptionSend = Callable[[SubscriptionEvent, str], Awaitable[DeliveryOutcome]]


class SubscriptionWorkerError(Exception):
    def __init__(self) -> None:
        super().__init__("Subscription worker paused after an unclassified failure")


class SubscriptionController:
    def __init__(
        self,
        namespace: str,
        bindings: Dota2Service,
        service: SubscriptionService,
        repository: SQLiteSubscriptionRepository,
        *,
        enabled: bool = False,
        interval_seconds: int = 300,
        daily_hour: int = 9,
        monotonic: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        logger: logging.Logger | None = None,
    ) -> None:
        self.namespace, self.bindings, self.service, self.repository = (
            namespace,
            bindings,
            service,
            repository,
        )
        self.enabled, self.interval, self.daily_hour = enabled, interval_seconds, daily_hour
        self._monotonic, self._now = monotonic, now
        self._logger = logger or logging.getLogger("Dota2Forge.subscriptions")
        self._lock = asyncio.Lock()
        self._active: asyncio.Task[object] | None = None
        self._closed = False
        self.paused = False
        self.last_error = "none"
        self._next_due = 0.0
        self._scope_cursor: SubscriptionScope | None = None
        self._cursors: dict[tuple[SubscriptionScope, SubscriptionKind], str | None] = {}
        self._delivery_cursors: dict[SubscriptionScope, int] = {}

    async def handle(
        self,
        identity: PlatformIdentity,
        destination: str,
        is_group: bool,
        is_admin: bool,
        keyword: str,
        text: str,
    ) -> str:
        if self._closed or not self.enabled:
            return "订阅功能未启用或已停用，请管理员检查 subscriptions_enabled 配置。"
        if (
            is_group
            and is_admin is not True
            and keyword in {"do订阅", "do订阅玩家", "do订阅比赛", "do重试推送"}
        ):
            return "群聊创建订阅或重试推送仅限 Bot 管理员；普通用户可在私聊订阅。"
        async with self._lock:
            if self._closed:
                return "订阅已停用。"
            tokens = text.split()
            try:
                if keyword == "do订阅":
                    if len(tokens) > 2 or (tokens and tokens[0] not in KINDS):
                        raise ValidationError("Invalid subscription grammar")
                    kind = KINDS[tokens[0]] if tokens else SubscriptionKind.NEW_MATCH
                    account = (
                        tokens[1]
                        if len(tokens) == 2
                        else (await self.bindings.get_binding(identity)).account_id.value
                    )
                    subscription = await self.service.subscribe(
                        identity, account, destination, kind=kind
                    )
                    return (
                        f"已保存{LABELS[kind]}订阅：{subscription.subscription_id}\n"
                        "首次比赛/段位轮询只建立基线，不补发历史；"
                        f"日报北京时间次日{self.daily_hour:02d}:00起观察。\n"
                        "账号为创建时快照；改绑/解绑会先取消该身份全部订阅。"
                    )
                if keyword == "do订阅玩家":
                    if len(tokens) != 1:
                        raise ValidationError("Expected one player ID")
                    subscription = await self.service.subscribe(
                        identity, tokens[0], destination, kind=SubscriptionKind.NEW_MATCH
                    )
                    return f"已保存玩家对局订阅：{subscription.subscription_id}"
                if keyword == "do订阅比赛":
                    if len(tokens) != 1:
                        raise ValidationError("Expected one match ID")
                    subscription = await self.service.subscribe_match(
                        identity, tokens[0], destination
                    )
                    return f"已保存指定比赛订阅：{subscription.subscription_id}"
                if keyword == "do订阅列表":
                    if len(tokens) > 1:
                        raise ValidationError("Invalid subscription cursor")
                    subscriptions = await self.service.list_subscriptions(
                        identity,
                        limit=10,
                        after_id=tokens[0] if tokens else None,
                        destination=destination,
                    )
                    lines = [
                        f"本会话订阅（polling_paused={self.paused} last_error={self.last_error}）"
                    ]
                    lines.extend(
                        f"{item.subscription_id} | {LABELS[item.key.kind]} | "
                        + (
                            f"账号 {item.key.account_id.value}"
                            if item.key.account_id
                            else f"比赛 {item.key.match_id.value if item.key.match_id else '未知'}"
                        )
                        for item in subscriptions
                    )
                    if len(subscriptions) == 10:
                        lines.append(f"下一页：do订阅列表 {subscriptions[-1].subscription_id}")
                    pending = await self.service.pending_events(identity, limit=100)
                    lines.extend(
                        f"未确认事件：{event.event_id}（重试可能重复；确认后用 do重试推送）"
                        for event in [
                            event for event in pending if event.key.destination == destination
                        ][:5]
                    )
                    return (
                        "\n".join(lines)
                        if subscriptions or pending
                        else "本会话没有订阅或未确认事件。"
                    )
                if len(tokens) != 1:
                    raise ValidationError("Expected one opaque subscription or event ID")
                if keyword == "do取消订阅":
                    removed = await self.service.unsubscribe(identity, tokens[0])
                    return (
                        "已取消你的订阅及其未确认事件。" if removed else "该订阅不存在或不属于你。"
                    )
                if keyword == "do重试推送":
                    released = await self.service.retry_event(identity, tokens[0])
                    return (
                        "已允许下一轮显式重试；若此前已送达，可能产生重复。"
                        if released
                        else "该事件未被占用、不存在或不属于你。"
                    )
                raise ValidationError("Unknown subscription command")
            except BindingNotFoundError:
                return "你尚未绑定账号；先 do绑定 <ID>，或 do订阅 比赛/段位/日报 <ID>。"
            except ValidationError:
                return (
                    "参数不正确：do订阅玩家 <玩家ID>；do订阅比赛 <比赛ID>；"
                    "do订阅 [比赛|段位|日报] [ID]；"
                    "do取消订阅 <订阅ID>；do重试推送 <事件ID>。"
                )
            except (SubscriptionRepositoryError, SubscriptionCapacityError):
                return "订阅存储不可用或容量已满；未确认事件不会自动丢弃，请管理员检查。"

    async def revoke(self, identity: PlatformIdentity) -> None:
        async with self._lock:
            await self.service.unsubscribe_all(identity)

    async def tick(self, send: SubscriptionSend) -> None:
        if (
            self._closed
            or not self.enabled
            or self.paused
            or self._lock.locked()
            or self._monotonic() < self._next_due
        ):
            return
        async with self._lock:
            self._active = asyncio.current_task()
            self._next_due = self._monotonic() + self.interval
            try:
                scopes = await self.repository.scopes(self.namespace, after=self._scope_cursor)
                if not scopes and self._scope_cursor is not None:
                    scopes = await self.repository.scopes(self.namespace)
                if not scopes:
                    return
                scope = scopes[0]
                self._scope_cursor = scope
                local_now = self._now().astimezone(BEIJING)
                for kind in SubscriptionKind:
                    cursor = self._cursors.get((scope, kind))
                    if kind == SubscriptionKind.NEW_MATCH:
                        results = await self.service.poll_new_matches(
                            scope, limit=5, after_id=cursor
                        )
                    elif kind == SubscriptionKind.RANK_CHANGE:
                        results = await self.service.poll_rank_changes(
                            scope, limit=5, after_id=cursor
                        )
                    elif (
                        kind == SubscriptionKind.DAILY_REPORT and local_now.hour >= self.daily_hour
                    ):
                        results = await self.service.poll_daily_reports(
                            scope, local_now.date() - timedelta(days=1), limit=5, after_id=cursor
                        )
                    elif kind == SubscriptionKind.MATCH_REPORT:
                        results = await self.service.poll_match_reports(
                            scope, limit=5, after_id=cursor
                        )
                    else:
                        continue
                    self._cursors[scope, kind] = (
                        results[-1].subscription.subscription_id if len(results) == 5 else None
                    )
                    for result in results:
                        if result.failure is not None:
                            self.last_error = result.failure.code.value
                            if result.failure.code == ProviderErrorCode.RATE_LIMITED:
                                if result.failure.retry_after_seconds is None:
                                    self.paused = True
                                else:
                                    self._next_due = max(
                                        self._next_due,
                                        self._monotonic() + result.failure.retry_after_seconds,
                                    )
                                return
                            if result.failure.code == ProviderErrorCode.AUTHENTICATION:
                                self.paused = True
                                return
                candidates = await self.repository.deliverable(
                    scope, limit=5, after_sequence=self._delivery_cursors.get(scope, 0)
                )
                for candidate in candidates:
                    sequence = await self.repository.event_sequence(scope, candidate.event_id)
                    if sequence is not None:
                        self._delivery_cursors[scope] = sequence
                    event = await self.service.claim_event(
                        candidate.key.identity, candidate.event_id
                    )
                    if event is None:
                        continue
                    outcome = await send(event, subscription_event_text(event))
                    if outcome == DeliveryOutcome.ACCEPTED:
                        await self.service.acknowledge(event.key.identity, event.event_id)
                    elif outcome == DeliveryOutcome.NOT_ATTEMPTED:
                        await self.service.retry_event(event.key.identity, event.event_id)
                    else:
                        self.last_error = "delivery_uncertain"
                if len(candidates) < 5:
                    self._delivery_cursors[scope] = 0
            except (SubscriptionRepositoryError, SubscriptionCapacityError) as error:
                self.last_error, self.paused = type(error).__name__, True
                self._logger.warning(
                    "subscription worker paused error_type=%s", type(error).__name__
                )
            except Exception as error:
                self.last_error, self.paused = type(error).__name__, True
                self._logger.warning(
                    "subscription worker paused error_type=%s", type(error).__name__
                )
                raise SubscriptionWorkerError() from None
            finally:
                self._active = None

    async def close(self) -> None:
        self._closed = True
        if self._active is not None and self._active is not asyncio.current_task():
            self._active.cancel()
            await asyncio.gather(self._active, return_exceptions=True)
