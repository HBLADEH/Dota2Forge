"""AstrBot-neutral application composition over Core and the shared Renderer.

The module is safe to import without AstrBot installed. The host bridge converts
trusted events into identities and sends these replies.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from dota2forge_core import (
    BindingConflictError,
    BindingNotFoundError,
    Dota2Service,
    HeroItemService,
    HeroResolutionError,
    MatchAnalysisService,
    MatchAnalysisUnavailable,
    MatchDetail,
    MatchDetailResult,
    MatchDetailService,
    MatchDetailUnavailable,
    MatchId,
    MatchParseState,
    MatchReport,
    PlatformIdentity,
    PlayerBinding,
    PlayerProfile,
    ProviderError,
    RecentMatches,
    RepositoryError,
)
from dota2forge_renderer import (
    AsyncRenderer,
    Card,
    HeroItemsCard,
    ImageArtifact,
    MatchDetailCard,
    MenuCard,
    PlayerCard,
    RecentMatchesCard,
    RenderError,
    StatusCard,
)
from dota2forge_renderer.cards import DETAIL_PER_PAGE
from dota2forge_renderer.engine import detail_groups
from dota2forge_renderer.formatting import (
    duration_text,
    mmr_estimate_text,
    rank_text,
    safe_name,
    timestamp,
    value_text,
)
from dota2forge_renderer.hero_items import hero_items_text, hero_resolution_text
from dota2forge_renderer.match_details import participant_items_text, participant_stats_text
from dota2forge_renderer.subscriptions import match_report_lines

from .commands import AstrAction, AstrCommandError, parse_command
from .selection import Key, SelectionError, SelectionStore, Session

HELP = (
    "Dota2Forge / AstrBot\n"
    "do菜单 / do帮助\ndo绑定 <ID> / do改绑 <ID>\n"
    "do账号 / do解绑\ndo查询 [ID]\n"
    "do[英雄名或简称]出装：OpenDota职业比赛热门出装统计\n"
    "do战绩 [条数] / do战绩 <ID> <条数>\n"
    "do战绩 第N页\ndo比赛 <ID> / do比赛 第N场\n"
    "do订阅 [比赛|段位|日报] [ID] / do订阅列表 [游标]\n"
    "do订阅玩家 <玩家ID> / do订阅比赛 <比赛ID>：完成后播报详情分析\n"
    "do取消订阅 <订阅ID> / do重试推送 <事件ID>\n"
    "订阅默认关闭；群订阅仅限 Bot 管理员。失败推送不自动重发。\n"
    "ID 为规范十进制 Dota 账号 ID 或 SteamID64。绑定只是查询偏好。"
)


@dataclass(frozen=True, slots=True)
class AstrTextReply:
    text: str


@dataclass(frozen=True, slots=True)
class AstrImageReply:
    artifact: ImageArtifact


type AstrReply = AstrTextReply | AstrImageReply


class AstrSend(Protocol):
    async def __call__(self, reply: AstrReply) -> object: ...


def source_label(source: str) -> str:
    return source.upper()


def player_text(player: PlayerProfile) -> str:
    return (
        f"Dota2Forge 玩家\n昵称：{safe_name(player.display_name)}\n"
        f"段位：{rank_text(player.rank_tier)}\n"
        f"预估 MMR：{mmr_estimate_text(player.rank_tier)}\n"
        "按段位区间估算，非精确分数；段位可能滞后。\n"
        f"抓取时间：{timestamp(player.metadata.fetched_at)}\n"
        f"数据观测时间：{timestamp(player.metadata.observed_at)}\n"
        f"来源：{source_label(player.metadata.source.value)}"
    )


def recent_text(recent: RecentMatches) -> list[str]:
    if not recent.matches:
        return [
            f"{source_label(recent.metadata.source.value)} 本次返回 0 场比赛"
            "（不代表完整历史无战绩）。\n"
            f"抓取时间：{timestamp(recent.metadata.fetched_at)}\n"
            f"来源：{source_label(recent.metadata.source.value)}"
        ]
    pages: list[str] = []
    for offset in range(0, len(recent.matches), 5):
        lines = [f"Dota2Forge 近期战绩 {offset + 1}–{min(offset + 5, len(recent.matches))}"]
        for index, match in enumerate(recent.matches[offset : offset + 5], offset + 1):
            outcome = "未知" if match.is_win is None else "胜" if match.is_win else "负"
            lines.append(
                f"第 {index} 场 | {timestamp(match.started_at)} | {outcome} | "
                f"英雄ID {value_text(match.hero_id)}\n"
                f"K/D/A {value_text(match.kills)}/{value_text(match.deaths)}/"
                f"{value_text(match.assists)}"
                f" | 时长 {duration_text(match.duration_seconds)}\n"
                f"比赛 ID {match.match_id} | do比赛 {match.match_id}"
            )
        lines.append(
            f"来源：{source_label(recent.metadata.source.value)}；"
            f"抓取时间 {timestamp(recent.metadata.fetched_at)}\n"
            f"本次返回 {len(recent.matches)} 场，不保证历史完整。"
        )
        pages.append("\n".join(lines))
    return pages


def detail_state_text(result: MatchDetailResult) -> str:
    return {
        MatchParseState.NO_DATA: "未返回（原因和隐私状态未知）",
        MatchParseState.UNKNOWN: "未知（没有解析标记）",
        MatchParseState.UNPARSED: "未解析（上游 isStats=False）",
        MatchParseState.PARTIAL: "部分解析（字段可能缺失）",
        MatchParseState.UPSTREAM_PARSED: "上游已标记解析（不代表字段完整）",
    }[result.parse_state]


def detail_text(detail: MatchDetailResult) -> list[str]:
    if isinstance(detail, MatchDetailUnavailable):
        return [
            f"Dota2Forge 比赛 {detail.match_id.value}\n"
            "本次没有返回详情；原因和隐私状态未知，不能判定为不存在或私密。\n"
            f"详情状态：{detail_state_text(detail)}\n"
            f"来源：{source_label(detail.metadata.source.value)}\n"
            f"抓取时间：{timestamp(detail.metadata.fetched_at)}"
        ]
    winner = (
        "未知" if detail.did_radiant_win is None else "天辉" if detail.did_radiant_win else "夜魇"
    )
    marker = (
        f"version {value_text(detail.parse_version)}"
        if detail.metadata.source.value == "opendota"
        else f"isStats {value_text(detail.has_stats)}"
    )
    header = (
        f"Dota2Forge 比赛 {detail.match_id.value}\n"
        f"开始：{timestamp(detail.started_at)} | 时长：{duration_text(detail.duration_seconds)}\n"
        f"模式：{detail.game_mode or '未知'} | 胜方：{winner}\n"
        f"来源：{source_label(detail.metadata.source.value)}\n"
        f"详情状态：{detail_state_text(detail)}\n"
        f"解析标记：{marker}\n"
        f"解析时间：{timestamp(detail.parsed_at)} | "
        f"抓取时间：{timestamp(detail.metadata.fetched_at)}\n"
        "状态不代表详情字段完整。"
    )
    if detail.players is None:
        return [header + "\n参赛者数据未知。"]
    pages: list[str] = []
    for side, label in ((True, "天辉"), (False, "夜魇"), (None, "阵营未知")):
        players = tuple(player for player in detail.players if player.is_radiant is side)
        if not players:
            continue
        for offset in range(0, len(players), DETAIL_PER_PAGE):
            lines = [header, label]
            for player in players[offset : offset + DETAIL_PER_PAGE]:
                name = (
                    "匿名参赛者"
                    if player.is_anonymous is True
                    else "身份未知"
                    if player.account_id is None
                    else safe_name(player.display_name)
                )
                lines.append(
                    f"{name} | 英雄 ID {value_text(player.hero_id)}\n"
                    f"K/D/A {value_text(player.kills)}/{value_text(player.deaths)}/"
                    f"{value_text(player.assists)}"
                )
                lines.append(
                    f"GPM {value_text(player.gold_per_minute)} / "
                    f"XPM {value_text(player.experience_per_minute)}"
                )
                lines.extend((participant_stats_text(player), participant_items_text(player)))
            pages.append("\n".join(lines))
    return pages or [header + "\n本次返回 0 名参赛者。"]


class AstrApplication:
    def __init__(
        self,
        service: Dota2Service,
        details: MatchDetailService,
        renderer: AsyncRenderer | None = None,
        *,
        analysis: MatchAnalysisService | None = None,
        items: HeroItemService | None = None,
        image_mode: bool = True,
        selection_clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._service = service
        self._details = details
        self._analysis = analysis
        self._items = items
        self._renderer = renderer
        self._image_mode = image_mode
        self._selections = SelectionStore(selection_clock)
        self._dispatch_lock = asyncio.Lock()

    async def _binding(self, identity: PlatformIdentity) -> PlayerBinding | None:
        try:
            return await self._service.get_binding(identity)
        except BindingNotFoundError:
            return None

    async def handle(self, identity: PlatformIdentity, keyword: str, text: str) -> list[AstrReply]:
        """Prepare replies without committing a delivered list."""
        replies, _ = await self._prepare(identity, keyword, text, None, False)
        return replies

    async def dispatch(
        self,
        identity: PlatformIdentity,
        keyword: str,
        text: str,
        send: AstrSend,
        session: Session | None = None,
    ) -> None:
        async with self._dispatch_lock:
            key = (identity, session) if session is not None else None
            replies, candidate = await self._prepare(identity, keyword, text, key, True)
            for reply in replies:
                await send(reply)
            if candidate is not None and key is not None:
                recent, binding = candidate
                if binding == await self._binding(identity):
                    self._selections.remember(key, recent, binding)

    async def _prepare(
        self,
        identity: PlatformIdentity,
        keyword: str,
        text: str,
        key: Key | None,
        capture: bool,
    ) -> tuple[list[AstrReply], tuple[RecentMatches, PlayerBinding | None] | None]:
        """Query once, then render; RenderError returns all same-data text replies."""
        candidate = None
        try:
            command = parse_command(keyword, text)
            cards: tuple[Card, ...] = ()
            if command.action in {AstrAction.HELP, AstrAction.MENU}:
                texts = [HELP]
                cards = (MenuCard(adapter_label="Dota2Forge / AstrBot"),)
            elif command.action in {AstrAction.BIND, AstrAction.REBIND}:
                assert command.account is not None
                await self._service.bind_account(
                    identity,
                    command.account.value,
                    replace=command.action == AstrAction.REBIND,
                )
                texts = ["账号绑定已保存。绑定仅用于查询，不证明账号所有权。"]
                self._selections.invalidate(identity)
                cards = (StatusCard(texts[0], "Dota2Forge / AstrBot"),)
            elif command.action == AstrAction.BINDING:
                binding = await self._service.get_binding(identity)
                texts = [f"你已绑定 Dota 账号 {binding.account_id.value}。"]
                cards = (StatusCard(texts[0], "Dota2Forge / AstrBot"),)
            elif command.action == AstrAction.UNBIND:
                removed = await self._service.unbind_account(identity)
                texts = ["已解除你的账号绑定。" if removed else "你目前没有绑定账号。"]
                self._selections.invalidate(identity)
                cards = (StatusCard(texts[0], "Dota2Forge / AstrBot"),)
            elif command.action == AstrAction.PLAYER:
                player = await self._service.get_player(identity, account_id=command.account)
                texts = [player_text(player)]
                cards = (PlayerCard(player),)
            elif command.action == AstrAction.ITEMS:
                if self._items is None:
                    return [AstrTextReply("英雄出装服务尚未配置。")], None
                assert command.hero_name is not None
                result_items = await self._items.get_items(command.hero_name)
                texts = [hero_items_text(result_items)]
                cards = (HeroItemsCard(result_items),)
            elif command.action == AstrAction.RECENT:
                recent_binding: PlayerBinding | None = await self._binding(identity)
                if command.page is not None:
                    recent = self._selections.get(key, recent_binding)
                    pages = recent_text(recent)
                    if command.page > len(pages):
                        return [AstrTextReply(f"该列表只有 {len(pages)} 页。")], None
                    texts = [pages[command.page - 1]]
                    cards = (RecentMatchesCard(recent, command.page),)
                else:
                    recent = await self._service.get_recent_matches(
                        identity, command.limit, account_id=command.account
                    )
                    pages = recent_text(recent)
                    texts = pages[:2]
                    cards = tuple(
                        RecentMatchesCard(recent, index + 1) for index in range(len(texts))
                    )
                    if capture and key is not None:
                        candidate = (recent, recent_binding)
                    if len(pages) > 2:
                        texts.append(
                            f"本次返回 {len(recent.matches)} 场、共 {len(pages)} 页。"
                            "请用 do战绩 第N页 查看其余结果。"
                            if candidate is not None
                            else "本次仅显示前 10 场；无法确认会话，不能保存后续页。"
                        )
            else:
                detail_binding: PlayerBinding | None = await self._binding(identity)
                if command.match_index is not None:
                    recent = self._selections.get(key, detail_binding)
                    if command.match_index > len(recent.matches):
                        return [AstrTextReply(f"该列表只有 {len(recent.matches)} 场。")], None
                    match_id = recent.matches[command.match_index - 1].match_id
                else:
                    assert command.match_id is not None
                    match_id = command.match_id.value
                result = await self._details.get_match_detail(match_id)
                analysis = (
                    await self._analysis.get_match_analysis(match_id)
                    if self._analysis is not None and isinstance(result, MatchDetail)
                    else MatchAnalysisUnavailable(MatchId(match_id), result.metadata)
                )
                report = MatchReport(
                    MatchId(match_id),
                    result.metadata,
                    detail_binding.account_id if detail_binding is not None else None,
                    None,
                    result,
                    analysis,
                )
                texts = detail_text(result)
                if isinstance(result, MatchDetail):
                    texts[-1] += "\n" + "\n".join(match_report_lines(report))
                if isinstance(result, MatchDetail):
                    groups = detail_groups(MatchDetailCard(result))
                    cards = tuple(
                        MatchDetailCard(
                            result,
                            index + 1,
                            None if detail_binding is None else detail_binding.account_id,
                        )
                        for index in range(len(groups))
                    )
            if not cards or not self._image_mode or self._renderer is None:
                return [AstrTextReply(value) for value in texts], candidate
            try:
                images: list[AstrReply] = [
                    AstrImageReply(await self._renderer.render(card)) for card in cards
                ]
                if len(texts) > len(images):
                    images.extend(AstrTextReply(value) for value in texts[len(images) :])
                return images, candidate
            except RenderError:
                return [AstrTextReply(value) for value in texts], candidate
        except AstrCommandError:
            return [AstrTextReply("命令参数不正确。\n" + HELP)], None
        except HeroResolutionError as error:
            return [AstrTextReply(hero_resolution_text(error))], None
        except BindingNotFoundError:
            return [AstrTextReply("你尚未绑定账号，请使用 do绑定 <ID>。")], None
        except BindingConflictError:
            return [AstrTextReply("你已绑定其他账号；如需替换，请使用 do改绑 <ID>。")], None
        except SelectionError:
            return [AstrTextReply("没有有效的已发送列表，请在本会话重新查询 do战绩。")], None
        except RepositoryError:
            return [AstrTextReply("绑定存储不可用，请管理员检查本地数据目录。")], None
        except ProviderError as error:
            wait = (
                f" 请在 {error.retry_after_seconds} 秒后手动再试。"
                if error.retry_after_seconds is not None
                else ""
            )
            return [
                AstrTextReply(f"{error.source.value.upper()} 查询失败：{error.code.value}。{wait}")
            ], None

    async def close(self) -> None:
        self._selections.clear()
        if self._renderer is not None:
            await self._renderer.close()
