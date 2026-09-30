# STRATZ 首个联网 Provider

Status: done

## 目标
按 [选型决策](../../notes/implemented/2026-09-30-provider-selection.md) 实现 STRATZ 主源，接入现有玩家与最近比赛用例，供 Dota2UID 首个宿主闭环消费。

## 非目标
OpenDota 自动回退、Valve/GC、自建解析、完整历史补齐、缓存、自动重试、后台轮询、IMP/详情公共模型与消息发送。

## 验收
- [x] 在基础设施实现异步 PlayerProvider/MatchProvider，依赖与关闭责任由组合入口注入；导入不联网、不读取环境、不启动任务，HTTP 不进入领域/用例。
- [x] 固定最小 GraphQL 查询并以 variables 传参；Bearer Token、User-Agent: STRATZ_API、有限超时可验证，取消传播，客户端可关闭，凭据和完整身份不出现在日志/异常。
- [x] 将 seasonRank、昵称、最近比赛英雄/时间/时长/KDA/GPM/XPM/胜负映射到现有模型；按我方阵营与 didRadiantWin 判断胜负，不能把天辉胜利当成玩家胜利。未实测字段先核对 schema，不猜测。
- [x] 账号一致、同源、去重、按开始时间倒序且不超过 limit；验证默认 10 与契约边界 1–100。数据不足可少于 limit；远端 take 上限导致截断时需有界分页或明确限制，不能声称历史完整。
- [x] 允许段位下降；缺失值保留 None，0/False 有效，不输出精确 MMR 承诺。source=stratz，fetched_at 使用时钟；observed_at 无证据则为空，不挪用比赛解析时间冒充玩家段位观测时间。
- [x] 区分 HTTP、GraphQL errors、部分数据、空集合、null、无效 JSON/HTML、超时和取消；明确认证/隐私/不存在须有证据。受 errors 影响的必要字段失败，可选字段仅在缺失语义明确时保留，否则报错；isStratzPublic=false 不单独推断全账号不可查询。
- [x] 读取秒/分/时/日限流头，遇到耗尽或 429 不继续发送，向调用者保留可知等待秒数；不硬编码本次 Token 配额。无自动重试或跨源切换，认证失败与服务访问拦截不误报成玩家无战绩。
- [x] 普通测试禁网，用去标识合成响应覆盖成功、空结果、段位下降、错误与额度边界；既有归一化 fixture 不冒充原始 STRATZ 响应。运行统一离线检查，并同步依赖锁定和事实文档。
- [x] 用本机配置的有效 Token 与授权账号独立只读联调实现后的 Provider，记录查询和关闭结果；不得将此前临时探测视为本实现通过。新增契约时检查所有已实现消费者；Dota2UID 已消费当前契约，AstrBot 仍为骨架。

## 影响模块与决策
[Core](../../../packages/dota2forge-core/)、[公共契约](../../../docs/subsystems/core.md)、[Core 总任务](../done/2026-09-30-core-mvp.md)、[Dota2UID](../done/2026-09-30-dota2uid-first-loop.md)、[选型决策](../../notes/implemented/2026-09-30-provider-selection.md)、[实现决策](../../notes/implemented/2026-09-30-stratz-provider.md)。

## 验证证据
2026-09-30，Windows / Python 3.12.9，保留开工时已有修改。复用现有端口/模型，Dota2UID 已消费当前契约，未改领域和用例契约。
- 用户填写被忽略的本机 .env；将授权 Steam 主页链接中的 SteamID64 转换为配置账号值，未保存原始玩家响应或凭据到跟踪文件。
- 两次鉴权内省均 200、无 errors、客户端关闭；核实 steamAccount.seasonRank、GPM/XPM、Long/Int 参数和 DESC/skip。
- 实现后运行 scripts/check_stratz.py 默认 limit=10 及 --limit 100：概况成功，分别返回 10/100 场，所需字段无缺失，同账号/source=stratz、observed_at=None、client_closed=true。100 场通过有界分页完成。这是新实现的独立证据，不沿用 [此前评测](2026-09-30-stratz-evaluation.md)。
- 统一入口通过：治理、Ruff、mypy（24 个源文件）、487 项禁网测试；Core 与适配器综合覆盖率 98%，scripts 97%，Dota2UID 独立覆盖率 94.88%，独立 80% 门槛通过。
- 三个包 sdist/wheel 构建及独立临时环境无索引安装导入通过；uv.lock 使用与 CI 一致的 uv 0.11.6 更新，保留既有依赖版本和格式。
- 修正可选依赖表加入后治理测试夹具重复声明 TOML 表的问题，保留“禁止宿主依赖”的原断言；未修改 policy、工作流或治理脚本的既有补丁。

## 阻塞与下一步
STRATZ Provider 和 Dota2UID QQ 首个宿主闭环已完成。每次最多 10 页、每页至多 20，不承诺完整历史。尚未实测所有隐私/不存在错误，陌生 GraphQL 错误严格失败；多账号、长期稳定性和在线限流耗尽仍未验证。OpenDota、详情/IMP、缓存、重试和自动回退未实现。
