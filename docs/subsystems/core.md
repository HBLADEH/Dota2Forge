# Core 账号绑定与查询契约

实现入口为 [公开用例](../../packages/dota2forge-core/src/dota2forge_core/use_cases.py)。领域值、端口与用例无 HTTP、SQL、环境读取或宿主 SDK 依赖；[SQLite 实现](../../packages/dota2forge-core/src/dota2forge_core/infrastructure/sqlite.py) 和 SystemClock 由组合入口显式注入。

## 身份与写入

AccountId 是 Dota account ID（本项目称 SteamID32 的十进制账号部分），取值 1 至 4294967294；0 与匿名玩家哨兵 4294967295 不允许绑定。SteamId64 仅接受 public universe、individual、desktop instance 的对应区间。两种模型分开校验，转换基数为 76561197960265728。

parse_account_id 接受整数或规范 ASCII 十进制字符串；拒绝 bool、浮点、符号、空白、前导零、溢出、Steam2/Steam3 文本、个人主页 URL 和 vanity name，不猜测输入含义。

PlatformIdentity 由 namespace、platform、bot_id、user_id 四部分组成。前两项为小写 ASCII 标识，后两项为 1–128 字符、无空白及控制字符的不透明值，保留大小写。namespace 由部署固定，须区分适配器和需要隔离的实例。同一用户号在不同平台、机器人、部署下互不影响；不同身份允许绑定同一 Dota 账号。

Dota2Service 提供 bind_account、get_binding、unbind_account、get_player、get_recent_matches。适配器必须从可信宿主事件构造调用者身份；禁止从命令参数或 AI 参数接受写入目标身份。Core 不验证平台登录，也不证明 Steam 账号所有权；绑定仅是查询偏好。

每个身份只有一个绑定。重复绑定同一账号返回原记录并保留 bound_at；改绑必须显式 replace=True。解绑返回是否删除，重复解绑返回 False。查询默认解析已有绑定，未绑定抛 BindingNotFoundError；显式 AccountId 查询不写绑定。最近比赛 limit 为 1–100，默认 10；查询无重试、缓存或自动数据源切换。

## 数据与失败

PlayerProvider、MatchProvider 返回不可变归一化模型。DataMetadata 包含 source、带时区 fetched_at、可缺省 observed_at 和 patch；未知时间/版本保留 None。每条比赛保存自己的元数据，RecentMatches 同时保存本次结果的元数据。

PlayerProfile 的未知昵称/段位与比赛的未知统计使用 None；missing_fields 列出数据字段缺口，0 和 False 保持原义。比赛列表要求同一玩家、同一来源、无重复 ID、按 started_at 从新到旧；条数不能超过请求值。非法模型被拒绝，Provider 实现负责将原始响应解析失败转换为 INVALID_RESPONSE。

有效空结果是带元数据的空 tuple。ProviderError.code 区分 NOT_FOUND、PRIVATE、RATE_LIMITED、TIMEOUT、UNAVAILABLE、AUTHENTICATION 和 INVALID_RESPONSE。限流可附非负整秒 retry_after_seconds；Core 不据此自动重试。来源不匹配、错玩家、过量或错误返回类型由用例拒绝。异常不转换为空列表，取消与意外程序错误继续传播。

错误文本不接收完整身份、令牌或原始响应。身份、账号、绑定和昵称的 repr 隐藏敏感字段；这不等于允许直接记录其序列化字典。项目无运行时日志系统。

## SQLite 与生命周期

使用专用文件，父目录由宿主准备；不支持 :memory:。先 await initialize()，再通过异步端口使用仓库。数据库以 application_id 和 user_version=1 标识，四个身份列为联合主键。未知版本、外部数据库、异常表结构及损坏行明确失败，不覆盖、不自动迁移、不伪装成未绑定。

SQL 使用参数绑定；BEGIN IMMEDIATE 将读取旧绑定、冲突检查与写入放在同一事务。阻塞 SQL 经 asyncio.to_thread 执行，每次操作连接均关闭；导入不打开数据库，不启动服务或常驻任务。锁等待默认 5 秒，可显式配置有限正数；存储故障统一 RepositoryError，原始 SQLite 异常不进入展示回溯。

取消等待不保证工作线程中的事务停止。发生取消后应重新读取状态再决定是否改绑；不承诺恰好一次写入。文件路径、备份、访问权限、部署调度与宿主卸载管理归组合入口。

## 历史单局详情

[详情值](../../packages/dota2forge-core/src/dota2forge_core/domain/match_detail.py) 和 MatchDetailService 独立于原 Dota2Service/玩家/近期端口。MatchId 接受 1–9223372036854775807 的整数或规范 ASCII 十进制字符串；拒绝 bool、浮点、符号、空白、前导零和 URL。服务通过 MatchDetailProvider 按 ID 直接查询，无绑定或 recent 依赖，不受近期 100 场边界限制；核对返回 ID、类型和来源。

MatchDetail 保留可缺省开始/解析时间、时长、模式枚举、game_version_id、胜方、has_stats 和实际参赛者。人数最多十人，重复已知槽位/账号失败；players=None、空 tuple 与不足十人可区分。解析时间不等于 observed_at，版本 ID 不等于补丁名称，has_stats 不证明字段完整。`parse_state` 只摘要上游证据：`UNPARSED`、`UPSTREAM_PARSED`、`PARTIAL`、`UNKNOWN`；显式 null 结果为 `NO_DATA`，原因/隐私仍未知。

MatchParticipant 保留阵营/槽位、英雄/KDA/GPM/XPM 和六个装备槽；0/False 有效，None 为缺失。账号哨兵 0/4294967295 是匿名，null 账号的匿名状态未知；均禁止携带昵称。已知账号与嵌套 steamAccount ID 必须一致；仅实际参赛账号可取得 participant 视角，绑定不证明参赛。账号/昵称 repr 隐藏，missing_fields 记录未知字段和装备槽。

无 GraphQL errors 的显式 null match 返回 MatchDetailUnavailable，保留 ID/source/fetched_at，原因及隐私未知，不能解释成明确不存在/拒绝或正常比赛。缺字段、非法类型、重复玩家和 GraphQL errors 仍为 INVALID_RESPONSE；明确的 NOT_FOUND/PRIVATE 保持 ProviderError 契约，当前 STRATZ 没有该细化证据。共用同一 Provider 的限流、超时、取消和客户端所有权，不重试/换源。

## 实现范围

[合成 fixture](../../tests/core/fixtures/public-player.json) 仅验证归一化端口及业务流程，标记 source=fixture，不是 STRATZ 原始响应样本。[StratzProvider](../../packages/dota2forge-core/src/dota2forge_core/infrastructure/stratz.py) 已实现三个独立查询端口，HTTP 依赖为 stratz extra；Dota2UID 和 AstrApplication 都只通过注入端口消费 Core，AstrBot 平台生命周期/真实消息尚未验证；新增详情契约没有更改旧构造与端口。

STRATZ 映射 steamAccount.seasonRank/昵称及最近比赛基本统计；胜负由玩家阵营和 didRadiantWin 共同决定。每页至多 20、每次至多 10 页，短页继续按实际行数推进，空页或无进展停止，不保证历史完整。去重冲突、错账号、必要字段缺失或不合法模型失败；集合和每场分别保留实际抓取时间，observed_at/patch 未知时为空。

HTTP 401 与已核实的缺 Bearer JSON 提示为认证失败；429/限额耗尽保留可知等待，超时明确返回，其余非 200 为 UNAVAILABLE。JSON/schema/null 及 GraphQL errors（含部分数据和可选字段错误）为 INVALID_RESPONSE；正常可选 null 可保留 None。空 matches 有效，null player/matches 不伪装为空，也不猜测 PRIVATE/NOT_FOUND；isStratzPublic=false 不是整个账号不可查的证据。无重试、缓存或自动回退，同 Token/循环须复用一个实例读取额度。

已独立只读联调概况、100场及偏移100旧比赛详情：source=stratz、10名参赛者、绑定账号确实参赛和client关闭均核对。has_stats=False但parsed_at存在，不能据单一标记推断完整；装备缺失保持None。Dota2UID详情/序号/取页及共享Renderer图片代码离线验证，尚未部署/QQ图片验收；临时列表仍在适配器。IMP/精确MMR/经济序列仍未实现。详情见[决策](../../.agents/notes/implemented/2026-10-01-historical-match-contract.md)，图片见[Renderer契约](../subsystems/renderer.md)。

操作见 [离线闭环](../cookbook/core-offline.md)，原因见 [Core 决策](../../.agents/notes/implemented/2026-09-30-core-offline-contracts.md)。
