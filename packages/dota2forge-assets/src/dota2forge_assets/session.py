"""Platform-free options and lifecycle facade; hosts supply trusted admin decisions."""

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from .manager import Activate, AssetManager
from .models import KINDS, AssetCounts, AssetError, AssetLimits, AssetStatus
from .store import OwnedIO
from .validation import validate_manifest

ASSET_COMMANDS = ("do素材状态", "do下载素材", "do更新素材")


@dataclass(frozen=True, slots=True)
class AssetOptions:
    mode: str = "auto"
    reply_mode: str = "image"
    external: Path | None = field(default=None, repr=False)
    proxy: str = field(default="", repr=False)


def load_asset_options(raw: Mapping[str, object], base: Path) -> AssetOptions:
    mode = raw.get("asset_download_mode", "auto")
    reply = raw.get("reply_mode", "image")
    path = raw.get("illustration_path", "")
    proxy = raw.get("asset_proxy", "")
    if (
        not isinstance(mode, str)
        or mode not in {"auto", "manual", "off"}
        or not isinstance(reply, str)
        or reply not in {"image", "text"}
        or not isinstance(path, str)
        or len(path) > 2048
        or any(ord(c) < 32 for c in path)
        or not isinstance(proxy, str)
        or len(proxy) > 2048
        or any(ord(c) < 33 for c in proxy)
    ):
        raise AssetError("configuration")
    if proxy:
        try:
            value = urlsplit(proxy)
            if value.scheme not in {"http", "https"} or not value.hostname or value.port is None:
                raise AssetError("configuration")
            if value.query or value.fragment or value.path not in ("", "/"):
                raise AssetError("configuration")
        except ValueError:
            raise AssetError("configuration") from None
    return AssetOptions(mode, reply, (base.resolve() / path).resolve() if path else None, proxy)


ManagerFactory = Callable[[Path, Activate | None], AssetManager]


class AssetSession:
    def __init__(
        self,
        options: AssetOptions,
        root: Path,
        activate: Activate | None = None,
        *,
        manager_factory: ManagerFactory | None = None,
    ) -> None:
        self.options = options
        self.manager = (
            manager_factory(root, activate)
            if manager_factory is not None
            else AssetManager(
                root,
                activate=activate,
                client_factory=lambda: httpx.AsyncClient(
                    proxy=options.proxy or None, trust_env=False
                ),
            )
        )
        self._external_io = OwnedIO()
        self._external_status = AssetStatus("external")
        self._started = False
        self._closed = False
        self._close_task: asyncio.Task[None] | None = None

    @property
    def path(self) -> Path | None:
        return self.options.external or self.manager.path

    async def start(self) -> None:
        if self._started or self._closed:
            return
        self._started = True
        if self.options.external is not None:
            path = self.options.external
            try:
                manifest = await self._external_io.run(
                    lambda: validate_manifest(path, AssetLimits())
                )
                counts = {
                    kind: AssetCounts(
                        sum(r["status"] == "available" for r in manifest.get(kind, {}).values()),
                        sum(r["status"] == "missing" for r in manifest.get(kind, {}).values()),
                    )
                    for kind in KINDS
                }
                self._external_status = AssetStatus("external", counts=counts)
            except (OSError, AssetError):
                self._external_status = AssetStatus("external_invalid", error="invalid_local_pack")
        else:
            await self.manager.open()

    async def auto_prepare(self) -> None:
        if (
            not self._closed
            and self.options.external is None
            and self.options.mode == "auto"
            and self.options.reply_mode == "image"
        ):
            await self.manager.ensure(automatic=True)

    def status(self) -> AssetStatus:
        if self.options.external is not None:
            return self._external_status
        status = self.manager.status()
        return replace(status, state="disabled") if self.options.mode == "off" else status

    async def handle(self, keyword: str, text: str, *, is_admin: bool) -> str:
        if text.strip():
            return "素材命令不接受参数；使用 do素材状态、do下载素材 或 do更新素材。"
        if keyword != "do素材状态":
            if not is_admin:
                return "仅当前 Bot 管理员或主人可下载、更新素材。"
            if self._closed:
                return "素材服务已关闭，请管理员重载插件。"
            if self.options.external is not None:
                return (
                    "当前使用自定义素材目录，未修改它；"
                    "清空 illustration_path 后重载可使用托管下载。"
                )
            if self.options.mode == "off":
                return "素材下载已关闭；请管理员将 asset_download_mode 改为 auto 或 manual 后重载。"
            if keyword == "do更新素材":
                await self.manager.update()
            elif keyword == "do下载素材":
                await self.manager.ensure()
            else:
                raise AssetError("command")
        return status_text(self.status())

    async def close(self) -> None:
        if self._close_task is None:
            self._closed = True
            self._close_task = asyncio.create_task(self._finish_close())
        await asyncio.shield(self._close_task)

    async def _finish_close(self) -> None:
        await self.manager.close()
        await self._external_io.wait()


def status_text(status: AssetStatus) -> str:
    labels = {
        "checking": "待准备",
        "downloading": "后台下载中",
        "ready": "就绪",
        "partial": "部分就绪",
        "failed": "准备失败",
        "cancelled": "已取消",
        "busy": "托管目录被另一实例占用",
        "external": "使用自定义目录",
        "external_invalid": "自定义目录无效",
        "disabled": "下载已关闭",
    }
    lines = [f"Dota2Forge 素材：{labels.get(status.state, status.state)}。"]
    names = {
        "heroes": "英雄",
        "items": "装备",
        "ranks": "段位",
        "rank_stars": "星级",
        "ui": "界面",
        "decor": "背景",
    }
    for kind, count in status.counts.items():
        lines.append(
            f"{names[kind]}：可用 {count.available}，404缺图 {count.missing_404}，"
            f"失败项目 {count.failed}，复用 {count.reused}。"
        )
    if status.state == "downloading":
        total = str(status.total) if status.total is not None else "目录尚未完整取得"
        lines.append(f"已处理 {status.completed} / {total}；接收 {status.downloaded_bytes} 字节。")
    if status.error:
        lines.append(f"错误类别：{status.error}；网络失败不等于官方缺图，原有效素材继续保留。")
    if status.retry_after_seconds:
        lines.append(f"本次操作冷却剩余 {status.retry_after_seconds} 秒。")
    if status.last_attempt:
        lines.append(f"最近尝试：{status.last_attempt.isoformat()}")
    if status.last_success:
        lines.append(f"最近完整更新：{status.last_success.isoformat()}")
    return "\n".join(lines)
