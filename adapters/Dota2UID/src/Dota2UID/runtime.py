"""Own the repository, STRATZ instance and HTTP client for one host lifecycle."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import httpx
from dota2forge_core import (
    BindingConflictError,
    BindingNotFoundError,
    Dota2Service,
    InvalidIdentityError,
    MatchAnalysisService,
    MatchAnalysisUnavailable,
    MatchDetail,
    MatchDetailService,
    MatchId,
    MatchReport,
    PlatformIdentity,
    PlayerBinding,
    ProviderError,
    RecentMatches,
    RepositoryError,
    SQLiteSubscriptionRepository,
    SubscriptionEvent,
    SubscriptionRepositoryError,
    SubscriptionService,
    ValidationError,
)
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure.sqlite import SQLiteBindingRepository
from dota2forge_core.infrastructure.stratz import StratzProvider
from dota2forge_renderer import (
    AsyncRenderer,
    Card,
    MatchDetailCard,
    MenuCard,
    PlayerCard,
    RecentMatchesCard,
    RenderError,
    StatusCard,
)
from dota2forge_renderer.subscriptions import match_report_lines

from .commands import Action, Caller, Command, CommandError, parse_command
from .config import Config, ConfigurationError, load_config
from .presentation import HELP, match_detail_text, player_text, provider_error_text, recent_text
from .replies import ImageReply, Reply, TextReply
from .selection import RecentSelectionStore, ResultKey, SelectionError, result_key
from .subscription_routes import delivery_route, destination
from .subscriptions import SUBSCRIPTION_COMMANDS, SubscriptionController, SubscriptionSend

UNAVAILABLE = "Dota2UID 尚未就绪或已停用，请管理员检查配置并按文档重新加载。"
LOGGER = logging.getLogger("Dota2UID")
COMMAND_NAMES = frozenset(action.value for action in Action) | frozenset(SUBSCRIPTION_COMMANDS)


@dataclass(frozen=True, repr=False)
class _RecentCandidate:
    key: ResultKey
    recent: RecentMatches
    binding: PlayerBinding | None


@dataclass(frozen=True, repr=False)
class _CommandResult:
    messages: list[str]
    candidate: _RecentCandidate | None = None
    cards: tuple[Card, ...] = ()


class State(StrEnum):
    NEW = "new"
    STARTING = "starting"
    READY = "ready"
    FAILED = "failed"
    STOPPING = "stopping"
    STOPPED = "stopped"


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(trust_env=False)


class Runtime:
    def __init__(
        self,
        config_path: Path,
        *,
        client_factory: Callable[[], httpx.AsyncClient] = make_client,
        selection_clock: Callable[[], float] = time.monotonic,
        renderer_factory: Callable[[], AsyncRenderer] = AsyncRenderer,
    ) -> None:
        self._config_path = config_path
        self._client_factory = client_factory
        self._config: Config | None = None
        self._client: httpx.AsyncClient | None = None
        self._service: Dota2Service | None = None
        self._details: MatchDetailService | None = None
        self._analysis: MatchAnalysisService | None = None
        self._lock = asyncio.Lock()
        self._state = State.NEW
        self._active: asyncio.Task[object] | None = None
        self._close_task: asyncio.Task[None] | None = None
        self._send_lock = asyncio.Lock()
        self._sending: asyncio.Task[object] | None = None
        self._overload_sending: asyncio.Task[object] | None = None
        self._dispatch_count = 0
        self._pending_delivery: _RecentCandidate | None = None
        self._selections = RecentSelectionStore(clock=selection_clock)
        self._renderer_factory = renderer_factory
        self._renderer: AsyncRenderer | None = None
        self._subscriptions: SubscriptionController | None = None

    @property
    def subscriptions_enabled(self) -> bool:
        return self._subscriptions is not None and self._subscriptions.enabled

    def subscription_route(self, event: SubscriptionEvent) -> Caller:
        if self._config is None:
            raise InvalidIdentityError()
        return delivery_route(event, self._config)

    async def poll_subscriptions(self, send: SubscriptionSend) -> None:
        if self._state == State.READY and self._subscriptions is not None:
            await self._subscriptions.tick(send)

    @property
    def state(self) -> State:
        return self._state

    @property
    def client_closed(self) -> bool:
        return self._client is None or self._client.is_closed

    async def start(self) -> None:
        async with self._lock:
            if self._state != State.NEW:
                return
            self._state = State.STARTING
            LOGGER.info("lifecycle state=starting")
            client: httpx.AsyncClient | None = None
            ready = False
            try:
                config = await asyncio.to_thread(load_config, self._config_path)
                await asyncio.to_thread(config.database.parent.mkdir, parents=True, exist_ok=True)
                repository = SQLiteBindingRepository(config.database)
                await repository.initialize()
                if self.state == State.STOPPING:
                    return
                client = self._client_factory()
                clock = SystemClock()
                provider = StratzProvider(
                    client, token=config.token, clock=clock, timeout_seconds=config.timeout_seconds
                )
                self._config = config
                self._client = client
                self._service = Dota2Service(repository, provider, provider, clock)
                self._details = MatchDetailService(provider)
                self._analysis = MatchAnalysisService(provider)
                subscription_repository = SQLiteSubscriptionRepository(
                    config.database.with_name("subscriptions.sqlite3")
                )
                await subscription_repository.initialize()
                if self._state == State.STOPPING:
                    return
                self._subscriptions = SubscriptionController(
                    config.namespace,
                    self._service,
                    SubscriptionService(
                        subscription_repository, provider, provider, clock, provider, provider
                    ),
                    subscription_repository,
                    enabled=config.subscriptions_enabled,
                    interval_seconds=config.subscription_interval_seconds,
                    daily_hour=config.daily_report_hour,
                )
                self._renderer = self._renderer_factory() if config.reply_mode == "image" else None
                self._state = State.READY
                ready = True
                LOGGER.info("lifecycle state=ready reply_mode=%s", config.reply_mode)
            except (
                ConfigurationError,
                RepositoryError,
                SubscriptionRepositoryError,
                OSError,
                ValidationError,
            ) as error:
                # Expected boundary failures are fixed text, never host-logged tracebacks.
                self._state = State.FAILED
                LOGGER.warning("lifecycle state=failed error_type=%s", type(error).__name__)
            finally:
                if not ready:
                    if client is not None:
                        await client.aclose()
                    if self._state == State.STARTING:
                        self._state = State.FAILED

    async def close(self) -> None:
        if self._close_task is None:
            self._state = State.STOPPING
            LOGGER.info("lifecycle state=stopping")
            if self._active is not None:
                self._active.cancel()
            if self._sending is not None and self._sending is not self._active:
                self._sending.cancel()
            if self._overload_sending is not None:
                self._overload_sending.cancel()
            self._close_task = asyncio.create_task(self._finish_close())
        # Retain ownership even if a host timeout cancels the waiter.
        await asyncio.shield(self._close_task)

    async def _finish_close(self) -> None:
        async with self._lock:
            try:
                try:
                    if self._subscriptions is not None:
                        await self._subscriptions.close()
                    if self._client is not None:
                        await self._client.aclose()
                finally:
                    if self._renderer is not None:
                        await self._renderer.close()
            finally:
                self._service = None
                self._details = None
                self._analysis = None
                self._config = None
                self._selections.clear()
                self._pending_delivery = None
                self._renderer = None
                self._subscriptions = None
                self._state = State.STOPPED
                LOGGER.info("lifecycle state=stopped client_closed=true")

    async def handle(self, caller: Caller, keyword: str, text: str) -> list[str]:
        """Return text only; callers must use dispatch to confirm chat delivery."""
        return (await self._handle(caller, keyword, text, capture=False)).messages

    async def dispatch(
        self,
        caller: Caller,
        keyword: str,
        text: str,
        send: Callable[[Reply], Awaitable[object]],
    ) -> None:
        """Serialize sends; commit selection only when the complete reply was sent."""
        operation = keyword if keyword in COMMAND_NAMES else "invalid"
        LOGGER.info("dispatch state=started operation=%s", operation)
        if self._state in {State.STOPPING, State.STOPPED}:
            LOGGER.info("dispatch state=ignored operation=%s reason=stopped", operation)
            return
        if self._dispatch_count >= 16:
            if self._overload_sending is not None:
                return
            self._overload_sending = asyncio.current_task()
            try:
                await send(TextReply("Dota2UID 当前排队请求较多，请稍后手动再试。"))
                LOGGER.info("delivery state=completed operation=%s replies=1 images=0", operation)
            finally:
                self._overload_sending = None
            return
        self._dispatch_count += 1
        task = asyncio.current_task()
        try:
            async with self._send_lock:
                if self._state in {State.STOPPING, State.STOPPED}:
                    return
                self._sending = task
                reply = await self._handle(caller, keyword, text, capture=True)
                self._pending_delivery = reply.candidate
                messages: list[Reply] = [TextReply(message) for message in reply.messages]
                if reply.cards and self._renderer is not None:
                    try:
                        rendered: list[Reply] = [
                            ImageReply(await self._renderer.render(card)) for card in reply.cards
                        ]
                    except RenderError:
                        LOGGER.warning(
                            "render state=fallback operation=%s cards=%d",
                            operation,
                            len(reply.cards),
                        )
                    else:
                        messages = rendered + messages[len(reply.cards) :]
                image_messages = [
                    message for message in messages if isinstance(message, ImageReply)
                ]
                image_bytes = sum(len(message.artifact.data) for message in image_messages)
                image_sizes = (
                    ",".join(
                        f"{message.artifact.width}x{message.artifact.height}"
                        for message in image_messages
                    )
                    or "none"
                )
                LOGGER.info(
                    "delivery state=prepared operation=%s replies=%d images=%d "
                    "image_bytes=%d image_sizes=%s",
                    operation,
                    len(messages),
                    len(image_messages),
                    image_bytes,
                    image_sizes,
                )
                try:
                    for message in messages:
                        if self._state in {State.STOPPING, State.STOPPED}:
                            LOGGER.info(
                                "delivery state=ignored operation=%s reason=stopped", operation
                            )
                            return
                        await send(message)
                except asyncio.CancelledError:
                    LOGGER.info("delivery state=cancelled operation=%s", operation)
                    raise
                except Exception as error:
                    LOGGER.warning(
                        "delivery state=failed operation=%s error_type=%s",
                        operation,
                        type(error).__name__,
                    )
                    raise
                LOGGER.info(
                    "delivery state=completed operation=%s replies=%d", operation, len(messages)
                )
                candidate = reply.candidate
                if candidate is not None:
                    async with self._lock:
                        if (
                            self._state == State.READY
                            and self._pending_delivery is candidate
                            and candidate.binding == await self._binding(candidate.key.identity)
                        ):
                            self._selections.remember(
                                candidate.key, candidate.recent, candidate.binding
                            )
                            LOGGER.info("selection state=committed operation=%s", operation)
        finally:
            if self._sending is task:
                self._sending = None
                self._pending_delivery = None
            self._dispatch_count -= 1

    async def _binding(self, identity: PlatformIdentity) -> PlayerBinding | None:
        assert self._service is not None
        try:
            return await self._service.get_binding(identity)
        except BindingNotFoundError:
            return None

    async def _handle(
        self,
        caller: Caller,
        keyword: str,
        text: str,
        *,
        capture: bool,
    ) -> _CommandResult:
        command: Command | None = None
        try:
            if keyword not in SUBSCRIPTION_COMMANDS:
                command = parse_command(keyword, text)
            await self.start()
            async with self._lock:
                if self._state != State.READY or self._config is None or self._service is None:
                    return _CommandResult([UNAVAILABLE])
                identity = caller.identity(self._config)
                self._active = asyncio.current_task()
                try:
                    if keyword in SUBSCRIPTION_COMMANDS:
                        assert self._subscriptions is not None
                        message = await self._subscriptions.handle(
                            identity,
                            destination(caller, self._config),
                            caller.conversation_kind == "group",
                            caller.is_admin,
                            keyword,
                            text,
                        )
                        return _CommandResult([message])
                    assert command is not None
                    if command.action == Action.MATCH:
                        assert self._details is not None
                        binding = await self._binding(identity)
                        if command.match_index is not None:
                            recent = self._selections.get(result_key(caller, self._config), binding)
                            if command.match_index > len(recent.matches):
                                return _CommandResult(
                                    [f"该列表只有 {len(recent.matches)} 场，请使用有效序号。"]
                                )
                            match_id = recent.matches[command.match_index - 1].match_id
                        else:
                            assert command.match_id is not None
                            match_id = command.match_id.value
                        result = await self._details.get_match_detail(match_id)
                        perspective = None if binding is None else binding.account_id
                        analysis = (
                            await self._analysis.get_match_analysis(match_id)
                            if self._analysis is not None and isinstance(result, MatchDetail)
                            else MatchAnalysisUnavailable(MatchId(match_id), result.metadata)
                        )
                        report = MatchReport(
                            MatchId(match_id), result.metadata, perspective, None, result, analysis
                        )
                        cards: tuple[Card, ...] = ()
                        fallback = match_detail_text(result, perspective)
                        detail_page_count = len(fallback)
                        if isinstance(result, MatchDetail):
                            fallback.append("\n".join(match_report_lines(report)))
                        if isinstance(result, MatchDetail):
                            cards = tuple(
                                MatchDetailCard(result, page + 1, perspective)
                                for page in range(detail_page_count)
                            )
                        return _CommandResult(fallback, cards=cards)
                    if command.action == Action.RECENT:
                        binding = await self._binding(identity)
                        if command.page is not None:
                            recent = self._selections.get(result_key(caller, self._config), binding)
                            pages = recent_text(recent)
                            if command.page > len(pages):
                                return _CommandResult(
                                    [f"该列表只有 {len(pages)} 页，请使用有效页码。"]
                                )
                            return _CommandResult(
                                [pages[command.page - 1]],
                                cards=(RecentMatchesCard(recent, command.page),),
                            )
                        recent = await self._service.get_recent_matches(
                            identity, command.limit, account_id=command.account
                        )
                        pages = recent_text(recent)
                        candidate: _RecentCandidate | None = None
                        if capture:
                            try:
                                key = result_key(caller, self._config)
                            except SelectionError:
                                key = None
                            if key is not None:
                                candidate = _RecentCandidate(key, recent, binding)
                        if len(pages) > 2:
                            pages = pages[:2] + [
                                f"本次返回 {len(recent.matches)} 场、共 "
                                f"{(len(recent.matches) + 4) // 5} 页。"
                                "请用 dota战绩 第N页 查看其余结果。"
                                if candidate is not None
                                else "本次仅显示前 10 场；无法确认会话，不能保存后续页。"
                            ]
                        count = min(2, max(1, (len(recent.matches) + 4) // 5))
                        cards = tuple(RecentMatchesCard(recent, page + 1) for page in range(count))
                        return _CommandResult(pages, candidate, cards)
                    if command.action in {Action.HELP, Action.MENU}:
                        admin = caller.is_admin is True
                        text_help = HELP + ("\ndota停用：关闭插件（管理员）。" if admin else "")
                        return _CommandResult([text_help], cards=(MenuCard(admin),))
                    if command.action == Action.PLAYER:
                        player = await self._service.get_player(
                            identity, account_id=command.account
                        )
                        return _CommandResult([player_text(player)], cards=(PlayerCard(player),))
                    if command.action in {Action.REBIND, Action.UNBIND}:
                        assert self._subscriptions is not None
                        await self._subscriptions.revoke(identity)
                    messages = await execute(self._service, identity, command)
                    if command.action in {Action.REBIND, Action.UNBIND}:
                        self._selections.invalidate(identity)
                        if (
                            self._pending_delivery is not None
                            and self._pending_delivery.key.identity == identity
                        ):
                            self._pending_delivery = None
                    return _CommandResult(messages, cards=(StatusCard(messages[0]),))
                finally:
                    self._active = None
        except CommandError:
            return _CommandResult(["命令参数不正确。\n" + HELP])
        except InvalidIdentityError:
            return _CommandResult(
                ["无法确认调用者的平台与机器人身份，或包含 @ 他人；本次操作未执行。"]
            )
        except ValidationError:
            return _CommandResult(
                ["账号格式不正确，请使用规范的 Dota 账号 ID 或 SteamID64 十进制数字。"]
            )
        except BindingConflictError:
            return _CommandResult(["你已绑定其他账号；如需替换，请使用 dota改绑 <ID>。"])
        except BindingNotFoundError:
            return _CommandResult(["你尚未绑定账号，请使用 dota绑定 <ID>，或显式查询账号。"])
        except (RepositoryError, SubscriptionRepositoryError):
            return _CommandResult(["账号绑定存储不可用，本次操作失败；请管理员检查。"])
        except SelectionError as error:
            return _CommandResult([str(error)])
        except ProviderError as error:
            return _CommandResult(
                [
                    provider_error_text(
                        error,
                        subject="比赛"
                        if command is not None and command.action == Action.MATCH
                        else "玩家",
                    )
                ]
            )


async def execute(service: Dota2Service, identity: PlatformIdentity, command: Command) -> list[str]:
    if command.action in {Action.HELP, Action.MENU}:
        return [HELP]
    if command.action in {Action.BIND, Action.REBIND}:
        assert command.account is not None
        await service.bind_account(
            identity, command.account.value, replace=command.action == Action.REBIND
        )
        return ["账号绑定已保存。绑定仅用于查询，不证明 Steam 账号所有权。"]
    if command.action == Action.BINDING:
        await service.get_binding(identity)
        return ["你已绑定 Dota 账号。可用 dota玩家 / dota战绩 查询，或 dota改绑 <ID> 替换。"]
    if command.action == Action.UNBIND:
        removed = await service.unbind_account(identity)
        return ["已解除你的账号绑定。" if removed else "你目前没有绑定账号。"]
    if command.action == Action.PLAYER:
        return [player_text(await service.get_player(identity, account_id=command.account))]
    if command.action == Action.RECENT:
        return recent_text(
            await service.get_recent_matches(identity, command.limit, account_id=command.account)
        )
    raise CommandError()
