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

## 实现范围

[合成 fixture](../../tests/core/fixtures/public-player.json) 仅验证归一化端口及业务流程，标记 source=fixture，不是 STRATZ 原始响应样本。[StratzProvider](../../packages/dota2forge-core/src/dota2forge_core/infrastructure/stratz.py) 已实现两个查询端口，HTTP 依赖为 stratz extra；Token、Clock、有限超时和专用客户端由组合入口注入并关闭。[Dota2UID](../cookbook/dota2uid.md) 已消费现有用例，AstrBot 尚无业务消费者；本轮不改 Core 公共契约。

STRATZ 映射 steamAccount.seasonRank/昵称及最近比赛基本统计；胜负由玩家阵营和 didRadiantWin 共同决定。每页至多 20、每次至多 10 页，短页继续按实际行数推进，空页或无进展停止，不保证历史完整。去重冲突、错账号、必要字段缺失或不合法模型失败；集合和每场分别保留实际抓取时间，observed_at/patch 未知时为空。

HTTP 401 与已核实的缺 Bearer JSON 提示为认证失败；429/限额耗尽保留可知等待，超时明确返回，其余非 200 为 UNAVAILABLE。JSON/schema/null 及 GraphQL errors（含部分数据和可选字段错误）为 INVALID_RESPONSE；正常可选 null 可保留 None。空 matches 有效，null player/matches 不伪装为空，也不猜测 PRIVATE/NOT_FOUND；isStratzPublic=false 不是整个账号不可查的证据。无重试、缓存或自动回退，同 Token/循环须复用一个实例读取额度。

实现后已用本机配置账号独立只读查询概况和 100 场，验证同账号、source=stratz 与客户端关闭；Dota2UID 宿主生命周期也已单独实测。QQ 单会话收发已获用户确认；按比赛 ID 的 MatchDetail、图片 Renderer、IMP、精确 MMR 与经济序列仍未实现，后续边界见 [图片任务](../../.agents/tasks/active/2026-10-01-image-interaction.md) 和 [详情任务](../../.agents/tasks/active/2026-10-01-historical-match-detail.md)。限制与操作见 [STRATZ 接入](../cookbook/stratz.md)，Provider 证据见 [任务](../../.agents/tasks/done/2026-09-30-stratz-provider.md)。

操作见 [离线闭环](../cookbook/core-offline.md)，原因见 [Core 决策](../../.agents/notes/implemented/2026-09-30-core-offline-contracts.md)。
