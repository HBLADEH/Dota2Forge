"""Own the repository, STRATZ instance and HTTP client for one host lifecycle."""

import asyncio
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path

import httpx
from dota2forge_core import (
    BindingConflictError,
    BindingNotFoundError,
    Dota2Service,
    InvalidIdentityError,
    PlatformIdentity,
    ProviderError,
    RepositoryError,
    ValidationError,
)
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure.sqlite import SQLiteBindingRepository
from dota2forge_core.infrastructure.stratz import StratzProvider

from .commands import Action, Caller, Command, CommandError, parse_command
from .config import Config, ConfigurationError, load_config
from .presentation import HELP, player_text, provider_error_text, recent_text

UNAVAILABLE = "Dota2UID 尚未就绪或已停用，请管理员检查配置并按文档重新加载。"


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
        self, config_path: Path, *, client_factory: Callable[[], httpx.AsyncClient] = make_client
    ) -> None:
        self._config_path = config_path
        self._client_factory = client_factory
        self._config: Config | None = None
        self._client: httpx.AsyncClient | None = None
        self._service: Dota2Service | None = None
        self._lock = asyncio.Lock()
        self._state = State.NEW
        self._active: asyncio.Task[object] | None = None
        self._close_task: asyncio.Task[None] | None = None

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
            client: httpx.AsyncClient | None = None
            ready = False
            try:
                config = await asyncio.to_thread(load_config, self._config_path)
                await asyncio.to_thread(config.database.parent.mkdir, parents=True, exist_ok=True)
                repository = SQLiteBindingRepository(config.database)
                await repository.initialize()
                if self._state == State.STOPPING:
                    return
                client = self._client_factory()
                clock = SystemClock()
                provider = StratzProvider(
                    client, token=config.token, clock=clock, timeout_seconds=config.timeout_seconds
                )
                self._config = config
                self._client = client
                self._service = Dota2Service(repository, provider, provider, clock)
                self._state = State.READY
                ready = True
            except (ConfigurationError, RepositoryError, OSError, ValidationError):
                # Expected boundary failures are fixed text, never host-logged tracebacks.
                self._state = State.FAILED
            finally:
                if not ready:
                    if client is not None:
                        await client.aclose()
                    if self._state == State.STARTING:
                        self._state = State.FAILED

    async def close(self) -> None:
        if self._close_task is None:
            self._state = State.STOPPING
            if self._active is not None:
                self._active.cancel()
            self._close_task = asyncio.create_task(self._finish_close())
        # Retain ownership even if a host timeout cancels the waiter.
        await asyncio.shield(self._close_task)

    async def _finish_close(self) -> None:
        async with self._lock:
            try:
                if self._client is not None:
                    await self._client.aclose()
            finally:
                self._service = None
                self._config = None
                self._state = State.STOPPED

    async def handle(self, caller: Caller, keyword: str, text: str) -> list[str]:
        try:
            command = parse_command(keyword, text)
            await self.start()
            async with self._lock:
                if self._state != State.READY or self._config is None or self._service is None:
                    return [UNAVAILABLE]
                identity = caller.identity(self._config)
                self._active = asyncio.current_task()
                try:
                    return await execute(self._service, identity, command)
                finally:
                    self._active = None
        except CommandError:
            return ["命令参数不正确。\n" + HELP]
        except InvalidIdentityError:
            return ["无法确认调用者的平台与机器人身份，或包含 @ 他人；本次操作未执行。"]
        except ValidationError:
            return ["账号格式不正确，请使用规范的 Dota 账号 ID 或 SteamID64 十进制数字。"]
        except BindingConflictError:
            return ["你已绑定其他账号；如需替换，请使用 dota改绑 <ID>。"]
        except BindingNotFoundError:
            return ["你尚未绑定账号，请使用 dota绑定 <ID>，或显式查询账号。"]
        except RepositoryError:
            return ["账号绑定存储不可用，本次操作失败；请管理员检查。"]
        except ProviderError as error:
            return [provider_error_text(error)]


async def execute(service: Dota2Service, identity: PlatformIdentity, command: Command) -> list[str]:
    if command.action == Action.HELP:
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
    return recent_text(
        await service.get_recent_matches(identity, command.limit, account_id=command.account)
    )
