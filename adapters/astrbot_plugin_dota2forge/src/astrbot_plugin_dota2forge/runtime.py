"""Own one host lifecycle; imports and construction perform no I/O."""

import asyncio
import logging
from collections.abc import Callable, Mapping
from enum import StrEnum
from pathlib import Path

import httpx
from dota2forge_core import (
    Dota2Service,
    HeroItemService,
    InvalidIdentityError,
    MatchAnalysisService,
    MatchDetailService,
    RepositoryError,
    SQLiteSubscriptionRepository,
    SubscriptionEvent,
    SubscriptionRepositoryError,
    SubscriptionService,
    ValidationError,
)
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure.hero_catalog import load_hero_catalog
from dota2forge_core.infrastructure.opendota import OpenDotaProvider
from dota2forge_core.infrastructure.sqlite import SQLiteBindingRepository
from dota2forge_core.infrastructure.stratz import StratzProvider
from dota2forge_renderer import AsyncRenderer, PillowRenderer

from .application import AstrApplication, AstrSend, AstrTextReply
from .commands import AstrCommandError, parse_command
from .config import Config, ConfigurationError, ConfigurationPending, load_config
from .identity import Caller
from .subscription_routes import delivery_route, destination
from .subscriptions import SUBSCRIPTION_COMMANDS, SubscriptionController, SubscriptionSend

LOGGER = logging.getLogger("Dota2Forge.AstrBot")
UNAVAILABLE = "Dota2Forge 尚未就绪，请管理员检查插件配置并重新加载。"
AWAITING_CONFIG = (
    "Dota2Forge 等待配置：请管理员在 AstrBot 插件配置填写 STRATZ Token，"
    "确认部署 namespace 后重载插件；请勿在聊天中发送 Token。"
)


class State(StrEnum):
    NEW = "new"
    STARTING = "starting"
    READY = "ready"
    AWAITING_CONFIG = "awaiting_config"
    FAILED = "failed"
    STOPPING = "stopping"
    STOPPED = "stopped"


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(trust_env=False)


class Runtime:
    def __init__(
        self,
        raw_config: Mapping[str, object],
        data_dir: Path,
        *,
        client_factory: Callable[[], httpx.AsyncClient] = make_client,
        renderer_factory: Callable[[], AsyncRenderer] | None = None,
    ) -> None:
        self._raw_config = dict(raw_config)
        self._data_dir = data_dir
        self._client_factory = client_factory
        self._renderer_factory = renderer_factory
        self._state = State.NEW
        self._config: Config | None = None
        self._client: httpx.AsyncClient | None = None
        self._application: AstrApplication | None = None
        self._start_task: asyncio.Task[None] | None = None
        self._close_task: asyncio.Task[None] | None = None
        self._operations: set[asyncio.Task[None]] = set()
        self._overload: asyncio.Task[object] | None = None
        self._subscriptions: SubscriptionController | None = None
        self._subscription_commands_lock = asyncio.Lock()

    @property
    def subscriptions_enabled(self) -> bool:
        return self._subscriptions is not None and self._subscriptions.enabled

    def subscription_route(self, event: SubscriptionEvent) -> Caller:
        if self._config is None:
            raise InvalidIdentityError()
        return delivery_route(event, self._config.namespace)

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
        if self._state == State.NEW:
            self._state = State.STARTING
            self._start_task = asyncio.create_task(self._initialize())
        if self._start_task is not None:
            await asyncio.shield(self._start_task)

    async def _initialize(self) -> None:
        client = None
        renderer = None
        ready = False
        try:
            config = load_config(self._raw_config, self._data_dir)
            await asyncio.to_thread(config.database.parent.mkdir, parents=True, exist_ok=True)
            repository = SQLiteBindingRepository(config.database)
            await repository.initialize()
            if self._state != State.STARTING:
                return
            client = self._client_factory()
            clock = SystemClock()
            provider = StratzProvider(
                client, token=config.token, clock=clock, timeout_seconds=config.timeout_seconds
            )
            if config.reply_mode == "image":
                renderer = (
                    self._renderer_factory()
                    if self._renderer_factory is not None
                    else AsyncRenderer(PillowRenderer(illustration_path=config.illustration_path))
                )
            bindings = Dota2Service(repository, provider, provider, clock)
            application = AstrApplication(
                bindings,
                MatchDetailService(provider),
                renderer,
                analysis=MatchAnalysisService(provider),
                items=HeroItemService(
                    OpenDotaProvider(client, clock=clock, timeout_seconds=config.timeout_seconds),
                    load_hero_catalog(),
                ),
                image_mode=config.reply_mode == "image",
            )
            subscription_repository = SQLiteSubscriptionRepository(
                config.database.with_name("subscriptions.sqlite3")
            )
            await subscription_repository.initialize()
            if self._state != State.STARTING:
                return
            self._subscriptions = SubscriptionController(
                config.namespace,
                bindings,
                SubscriptionService(
                    subscription_repository, provider, provider, clock, provider, provider
                ),
                subscription_repository,
                enabled=config.subscriptions_enabled,
                interval_seconds=config.subscription_interval_seconds,
                daily_hour=config.daily_report_hour,
            )
            self._config, self._client, self._application = config, client, application
            self._state = State.READY
            ready = True
            LOGGER.info("lifecycle state=ready reply_mode=%s", config.reply_mode)
        except ConfigurationPending:
            if self._state == State.STARTING:
                self._state = State.AWAITING_CONFIG
                LOGGER.info("lifecycle state=awaiting_config")
        except (
            ConfigurationError,
            RepositoryError,
            SubscriptionRepositoryError,
            OSError,
            ValidationError,
        ) as error:
            LOGGER.warning("lifecycle state=failed error_type=%s", type(error).__name__)
        finally:
            self._raw_config.clear()
            if not ready:
                try:
                    if renderer is not None:
                        await renderer.close()
                finally:
                    if client is not None:
                        await client.aclose()
                if self._state == State.STARTING:
                    self._state = State.FAILED

    async def dispatch(self, caller: Caller, keyword: str, text: str, send: AstrSend) -> None:
        if self._state in {State.STOPPING, State.STOPPED}:
            return
        if len(self._operations) >= 16:
            if self._overload is None:
                self._overload = asyncio.create_task(
                    send(AstrTextReply("Dota2Forge 当前排队请求较多，请稍后手动再试。"))
                )
                try:
                    await self._overload
                finally:
                    self._overload = None
            return
        task = asyncio.create_task(self._dispatch(caller, keyword, text, send))
        self._operations.add(task)
        try:
            await task
        finally:
            self._operations.discard(task)

    async def _dispatch(self, caller: Caller, keyword: str, text: str, send: AstrSend) -> None:
        await self.start()
        try:
            identity = caller.identity(self._config.namespace if self._config else "astrbot-local")
        except InvalidIdentityError:
            await send(AstrTextReply("无法确认调用者身份或包含 @ 他人；本次操作未执行。"))
            return
        if self._state != State.READY or self._application is None:
            await send(
                AstrTextReply(
                    AWAITING_CONFIG if self._state == State.AWAITING_CONFIG else UNAVAILABLE
                )
            )
            return
        assert self._subscriptions is not None and self._config is not None
        if keyword in SUBSCRIPTION_COMMANDS or keyword in {"do改绑", "do解绑"}:
            async with self._subscription_commands_lock:
                try:
                    if keyword in SUBSCRIPTION_COMMANDS:
                        if keyword in {"do订阅", "do重试推送"} and caller.platform != "aiocqhttp":
                            await send(
                                AstrTextReply("当前主动订阅仅支持 OneBot v11 反向 WebSocket。")
                            )
                            return
                        message = await self._subscriptions.handle(
                            identity,
                            destination(caller, self._config.namespace),
                            caller.conversation_kind == "GroupMessage",
                            caller.is_admin,
                            keyword,
                            text,
                        )
                        await send(AstrTextReply(message))
                        return
                    try:
                        parse_command(keyword, text)
                    except AstrCommandError:
                        pass
                    else:
                        await self._subscriptions.revoke(identity)
                    await self._application.dispatch(
                        identity, keyword, text, send, caller.session()
                    )
                except InvalidIdentityError:
                    await send(AstrTextReply("无法确认本会话投递目标；本次操作未执行。"))
                except SubscriptionRepositoryError:
                    await send(AstrTextReply("订阅存储不可用，未修改绑定；请管理员检查。"))
        else:
            await self._application.dispatch(identity, keyword, text, send, caller.session())

    async def close(self) -> None:
        if self._close_task is None:
            self._state = State.STOPPING
            for task in self._operations:
                task.cancel()
            if self._overload is not None:
                self._overload.cancel()
            self._close_task = asyncio.create_task(self._finish_close())
        await asyncio.shield(self._close_task)

    async def _finish_close(self) -> None:
        try:
            if self._operations:
                await asyncio.gather(*tuple(self._operations), return_exceptions=True)
            if self._overload is not None:
                await asyncio.gather(self._overload, return_exceptions=True)
            if self._start_task is not None:
                await self._start_task
        finally:
            try:
                if self._application is not None:
                    if self._subscriptions is not None:
                        await self._subscriptions.close()
                    await self._application.close()
            finally:
                try:
                    if self._client is not None:
                        await self._client.aclose()
                finally:
                    self._application = None
                    self._subscriptions = None
                    self._config = None
                    self._raw_config.clear()
                    self._state = State.STOPPED
                    LOGGER.info("lifecycle state=stopped client_closed=%s", self.client_closed)
