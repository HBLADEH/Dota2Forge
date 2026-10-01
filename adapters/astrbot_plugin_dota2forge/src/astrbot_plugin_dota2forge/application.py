"""AstrBot-neutral application composition over Core and the shared Renderer.

The module is safe to import without AstrBot installed. A future AstrBot hook
should convert its trusted event into PlatformIdentity and send these replies.
"""

from dataclasses import dataclass
from typing import Protocol

from dota2forge_core import (
    BindingNotFoundError,
    Dota2Service,
    MatchDetail,
    MatchDetailResult,
    MatchDetailService,
    MatchDetailUnavailable,
    MatchParseState,
    PlatformIdentity,
    PlayerProfile,
    ProviderError,
    RecentMatches,
)
from dota2forge_renderer import (
    AsyncRenderer,
    Card,
    ImageArtifact,
    MatchDetailCard,
    MenuCard,
    PlayerCard,
    RecentMatchesCard,
    RenderError,
    StatusCard,
)
from dota2forge_renderer.engine import detail_groups
from dota2forge_renderer.formatting import (
    duration_text,
    rank_text,
    safe_name,
    timestamp,
    value_text,
)

from .commands import AstrAction, AstrCommandError, parse_command


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
                f"比赛 ID {match.match_id} | dota比赛 {match.match_id}"
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
            f"抓取时间：{timestamp(detail.metadata.fetched_at)}"
        ]
    winner = (
        "未知" if detail.did_radiant_win is None else "天辉" if detail.did_radiant_win else "夜魇"
    )
    header = (
        f"Dota2Forge 比赛 {detail.match_id.value}\n"
        f"开始：{timestamp(detail.started_at)} | 时长：{duration_text(detail.duration_seconds)}\n"
        f"模式：{detail.game_mode or '未知'} | 胜方：{winner}\n"
        f"来源：{source_label(detail.metadata.source.value)}\n"
        f"详情状态：{detail_state_text(detail)}\n"
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
        for offset in range(0, len(players), 5):
            lines = [header, label]
            for player in players[offset : offset + 5]:
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
            pages.append("\n".join(lines))
    return pages or [header + "\n本次返回 0 名参赛者。"]


class AstrApplication:
    def __init__(
        self,
        service: Dota2Service,
        details: MatchDetailService,
        renderer: AsyncRenderer | None = None,
        *,
        image_mode: bool = True,
    ) -> None:
        self._service = service
        self._details = details
        self._renderer = renderer
        self._image_mode = image_mode

    async def handle(self, identity: PlatformIdentity, keyword: str, text: str) -> list[AstrReply]:
        """Query once, then render; RenderError returns all same-data text replies."""
        try:
            command = parse_command(keyword, text)
            cards: tuple[Card, ...] = ()
            if command.action in {AstrAction.HELP, AstrAction.MENU}:
                texts = [
                    "Dota2Forge / AstrBot\n"
                    "dota绑定 <ID>\ndota玩家 [ID]\n"
                    "dota战绩 [条数]\ndota比赛 <ID>"
                ]
                cards = (MenuCard(),)
            elif command.action in {AstrAction.BIND, AstrAction.REBIND}:
                assert command.account is not None
                await self._service.bind_account(
                    identity,
                    command.account.value,
                    replace=command.action == AstrAction.REBIND,
                )
                texts = ["账号绑定已保存。绑定仅用于查询，不证明账号所有权。"]
                cards = (StatusCard(texts[0]),)
            elif command.action == AstrAction.BINDING:
                await self._service.get_binding(identity)
                texts = ["你已绑定 Dota 账号。"]
                cards = (StatusCard(texts[0]),)
            elif command.action == AstrAction.UNBIND:
                removed = await self._service.unbind_account(identity)
                texts = ["已解除你的账号绑定。" if removed else "你目前没有绑定账号。"]
                cards = (StatusCard(texts[0]),)
            elif command.action == AstrAction.PLAYER:
                player = await self._service.get_player(identity, account_id=command.account)
                texts = [player_text(player)]
                cards = (PlayerCard(player),)
            elif command.action == AstrAction.RECENT:
                recent = await self._service.get_recent_matches(
                    identity, command.limit, account_id=command.account
                )
                texts = recent_text(recent)
                cards = tuple(
                    RecentMatchesCard(recent, index + 1) for index in range(min(2, len(texts)))
                )
            else:
                assert command.match_id is not None
                result = await self._details.get_match_detail(command.match_id.value)
                texts = detail_text(result)
                if isinstance(result, MatchDetail):
                    groups = detail_groups(MatchDetailCard(result))
                    cards = tuple(
                        MatchDetailCard(result, index + 1) for index in range(len(groups))
                    )
            if not cards or not self._image_mode or self._renderer is None:
                return [AstrTextReply(value) for value in texts]
            try:
                images: list[AstrReply] = [
                    AstrImageReply(await self._renderer.render(card)) for card in cards[:2]
                ]
                if len(texts) > len(images):
                    images.append(
                        AstrTextReply(
                            f"本次返回 {len(texts)} 页；AstrBot 会话翻页尚未接入，"
                            "请使用比赛 ID 直接查询。"
                        )
                    )
                return images
            except RenderError:
                return [AstrTextReply(value) for value in texts]
        except (AstrCommandError, BindingNotFoundError):
            return [AstrTextReply("命令参数不正确或尚未绑定账号。")]
        except ProviderError as error:
            return [AstrTextReply(f"{error.source.value.upper()} 查询失败：{error.code.value}。")]

    async def close(self) -> None:
        if self._renderer is not None:
            await self._renderer.close()
