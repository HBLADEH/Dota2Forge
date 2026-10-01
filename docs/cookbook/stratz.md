# 配置与验证 STRATZ

[StratzProvider](../../packages/dota2forge-core/src/dota2forge_core/infrastructure/stratz.py) 同时实现 PlayerProvider/MatchProvider/MatchDetailProvider。只读查询，无缓存、自动重试或回退；限流立即返回 ProviderError，调用者决定何时再次查询。

## 本机配置
在仓库根复制 .env.example 为 .env，填写 STRATZ_TOKEN、STRATZ_ACCOUNT_ID 和 STRATZ_TIMEOUT_SECONDS（默认 10 秒）。账号可以是规范 Dota account ID 或 SteamID64；Token 从 [STRATZ API](https://stratz.com/api) 获取。只在本机编辑器填密钥，.env 已被 Git 忽略，不把它写进聊天、源码、截图或日志。Core 不自动加载 .env 或环境变量。

开发环境通过锁文件安装 httpx；独立部署联网组合入口安装 dota2forge-core[stratz]。普通 Core 和适配器骨架仍可不装 extra。先运行 [统一离线检查](development.md)，再显式执行：

~~~sh
uv run --env-file .env --locked python scripts/check_stratz.py
uv run --env-file .env --locked python scripts/check_stratz.py --limit 100
~~~

[联调命令](../../scripts/check_stratz.py) 是独立组合入口，由 uv 注入本机环境；它创建客户端、查询配置账号的概况与近期比赛并关闭客户端，仅输出来源、条数、缺失字段、身份一致和关闭状态，不输出完整账号、昵称、Token 或原始响应。失败输出固定错误分类及可知限流等待。限流后不要立即重跑命令来绕过等待。

## 宿主注入
配置读取和 HTTP 生命周期在宿主的组合入口处理：

~~~python
import httpx
from dota2forge_core import MatchDetailService
from dota2forge_core.infrastructure import SystemClock
from dota2forge_core.infrastructure.stratz import StratzProvider

async with httpx.AsyncClient(trust_env=False) as client:
    provider = StratzProvider(client, token=local_token, clock=SystemClock())
    # 将 provider 同时传给 Dota2Service 的 players 和 matches。
    player = await provider.get_player(account_id)
    recent = await provider.get_recent_matches(account_id, limit=10)
    # match_id 为调用方选择的规范比赛 ID，与 recent/绑定无依赖。
    detail = await MatchDetailService(provider).get_match_detail(match_id)
~~~

同一宿主循环中同 Token 复用一个 Provider 及专用客户端；宿主卸载时关闭客户端。不要在每条消息中创建实例以规避限额。Provider 固定 HTTPS 端点、Bearer、STRATZ_API User-Agent，不跟随重定向；单次 HTTP 包含连接/读写/连接池超时及总超时。客户端钩子、外部重试传输和请求正文日志不由 Provider 控制，组合入口不应启用。

## 结果边界
limit 为 1–100，默认 10。每页最多 20，最多 10 页；按实际行数翻页，重复无进展时停止。返回去重后最近的至多 limit 场，允许少于请求值，不承诺历史完整或并发分页快照。每场保留所属页的 fetched_at，集合保留最后一页抓取时间；observed_at 和 patch 无证据时为空。

缺失统计保留 None，0/False 有效。胜负结合玩家 isRadiant 与 didRadiantWin；seasonRank 可下降，不代表精确 MMR。展示结果附 [STRATZ 来源](https://stratz.com)，玩家链接应由展示层基于已验证账号生成。

详情使用固定 Long ID 查询，包含可缺省时间/模式/版本 ID、胜方、isStats/解析时间、参赛者及六个装备槽。`MatchParseState` 将 `isStats=False` 摘要为未解析、`isStats=True` 摘要为上游已标记解析，无标记但有字段为部分解析，完全无标记为未知；这些状态不宣称字段完整。显式 null match 返回 MatchDetailUnavailable（状态为无数据），原因/隐私未知；其余详情 schema 或 GraphQL errors 失败。匿名/未知账号不保存昵称。详情用例不受 recent 的 100 场边界限制，不保证上游历史覆盖，契约见 [Core](../subsystems/core.md)。

HTTP 拦截、认证、429、超时和响应错误明确失败。无 errors 的显式可选 null 可缺失；GraphQL errors（含可选字段）目前一律失败。空 matches 是有效空集合，null player/matches 是 INVALID_RESPONSE。未核实的隐私/不存在错误不映射为 PRIVATE/NOT_FOUND，也不因 isStratzPublic=false 拒绝整个账号。

耗尽任一秒/分/时/日窗口后，本实例在可知重置前不发送；429 无可知重置时间则持续拒绝，需运维核实额度后重新初始化。无自动 sleep、重试、跨进程限额协调或换源。

测试使用 [原始形状合成响应](../../tests/core/test_stratz.py) 和 MockTransport，普通测试始终禁网。实际验证证据与未验收项见 [接入任务](../../.agents/tasks/done/2026-09-30-stratz-provider.md)，策略原因见 [决策](../../.agents/notes/implemented/2026-09-30-stratz-provider.md)。
