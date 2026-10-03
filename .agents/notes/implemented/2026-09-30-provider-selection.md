# STRATZ 主源与独立补充数据源

Category: data
Related task: [STRATZ 接入](../../tasks/done/2026-09-30-stratz-provider.md)
Related code: [Provider 端口](../../../packages/dota2forge-core/src/dota2forge_core/ports.py)
Related docs: [Core 契约](../../../docs/subsystems/core.md)

## Problem
用户的选型标准为免费、好用、稳定，不要求服务端开源。此前仅有离线 Provider 契约；2026-09-30 的 [真实评测](../../tasks/done/2026-09-30-stratz-evaluation.md) 已验证 STRATZ 鉴权、部分 schema、额度与一个授权账号的 20 场比赛。

双方基础战绩一致，STRATZ 15/20 场有详细经济及购买记录，OpenDota 为 2/20；用户确认 STRATZ 返回当前段位，而 OpenDota 保留先前较高段位。该证据支持本次选型，不证明所有账号上 STRATZ 永远更新、更完整。

## Decision
STRATZ 基础接入已实施并验收；迁入 implemented 仅确认已落地的主源选择和首轮边界。OpenDota、Valve、详情/IMP 仍是后续方向，不表示已实现。承接 [离线契约](2026-09-30-core-offline-contracts.md)，保留其身份、缺失值和错误语义；具体实现见 [HTTP 决策](2026-09-30-stratz-provider.md)。

后续实施进展：历史详情已按[详情决策](2026-10-01-historical-match-contract.md)实现；OpenDota独立SDK与显式交叉核验见[补充源决策](2026-10-02-opendota-cross-check.md)，不改变STRATZ默认主源或本选型的禁止自动拼接/隐私回退原则。

- STRATZ 为默认主源：先实现现有 PlayerProvider/MatchProvider 的玩家段位与最近比赛；单场详情、IMP、经济/购买序列随后扩展契约，不混入当前模型冒充已支持。
- OpenDota 为后续独立补充与交叉核验来源；首轮不实现自动 fallback。来源冲突分别标注，不能取最高段位或用旧值覆盖主源；不能跨源拼接一个无字段来源的结果。明确隐私拒绝时不换源绕过限制。
- Valve Web API 仅在账号解析或官方基础数据确有缺口时引入；Steam GC、自建全量采集、录像解析服务及 GSI 不作为首个闭环依赖。
- HTTP、Token、超时及限流放基础设施/组合入口，领域与用例只依赖端口；优先完成 STRATZ → Dota2UID → AstrBot，后续补充源不阻塞首个宿主闭环。
- 使用 Bearer Token 与本次验证通过的 User-Agent: STRATZ_API。额度读取响应头并遵守秒/分/时/日最紧窗口；本次 Token 的 8/150/1500/15000 仅作证据，不硬编码为所有账号保证。免费默认配置不要求 OpenDota 付费 Key。
- HTTP 200 仍检查 GraphQL errors、null 与部分数据；不把 HTML 403 直接解释为玩家私密或凭据失效。未知隐私与明确拒绝分开；必要字段受错误影响时明确失败，可选缺失仅在已有模型可表达时保留 None，否则先修订契约。
- 段位可升可降，排行榜名次与精确 MMR 分离；估算分数必须标注估算。IMP 为 STRATZ 指标，不能当作官方分数。保留 source/fetched_at，数据观测时间未知时不以抓取时间冒充；不同经济序列或历史统计不默认为同口径。
- 首轮不加入缓存、自动重试、轮询或自动解析任务；限流等待信息与超时明确返回。后续缓存、重试和回退需单独验收，避免用无声降级掩盖旧段位或数据缺失。展示层提供 STRATZ 来源链接。

## Alternatives considered
- OpenDota 单主源：无需 Token、基础战绩一致，但本次详细数据较少且段位滞后，保留为独立补充。
- STRATZ 与 OpenDota 自动拼接/切换：口径、时效和隐私不等价，先保持明确来源。
- Valve/GC/录像全自建：控制力更高，但维护会话、协议、采集与存储不利于当前最小闭环。

## Consequences
需要维护 Token 与 GraphQL 查询，处理多个限流窗口和部分错误；不保证精确 MMR、完整历史或实时段位。凭据由本机配置注入，不把聊天中的 Token 写入项目；已建议轮换曾在聊天中提供的 Token。单账号生产读取和独立客户端关闭已验证，长期稳定性、多账号及宿主生命周期仍待验证。

## Verification
接入任务已使用去标识合成响应验证字段、错误及限流，407 项禁网测试及统一检查通过；随后用本机配置账号独立只读验证实现后的概况和默认 10/100 场查询、客户端关闭。当前无已实现适配器消费者，新增契约时须再次检查消费者。未实测的隐私/不存在错误保持失败，不猜测；详情和补充源另立验收。
