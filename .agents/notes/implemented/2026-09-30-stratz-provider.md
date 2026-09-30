# STRATZ 首个 HTTP Provider

Category: data
Related task: [接入任务](../../tasks/done/2026-09-30-stratz-provider.md)
Related code: [实现](../../../packages/dota2forge-core/src/dota2forge_core/infrastructure/stratz.py)
Related docs: [接入步骤](../../../docs/cookbook/stratz.md)

## Problem
现有用例仅由合成归一化 fixture 消费；需要按 [选型方向](../implemented/2026-09-30-provider-selection.md) 实现可关闭、有界且不伪造缺失或错误语义的首个联网来源。两个适配器仍无业务消费者，公共模型和端口无需变化。

## Decision
- httpx 是 Core 的 stratz 可选依赖，开发组安装同一版本范围；基础 Core 与适配器骨架安装不引入 HTTP 依赖。联网组合入口显式安装 extra，注入专用 AsyncClient、Token、Clock 和有限超时，拥有并关闭客户端；Provider 不读环境、不创建任务，导入不联网。
- 查询固定并只通过 variables 传账号和分页参数。2026-09-30 使用本机配置凭据内省核对 Long/Int/Byte/Short 标量、steamAccount.seasonRank、玩家 GPM/XPM、take/skip、DESC 和玩家过滤参数。不查询无用的详情/IMP，也不拿比赛解析时间表示玩家观测时间。
- 同一 Token 在同一宿主循环复用一个实例，HTTP 串行使排队请求看到上一响应的限额。读取秒/分/时/日剩余额度及通用 RateLimit-Reset、Retry-After，使用服务端 Date 计算对齐窗口的等待；等待由调用者决定。429 没有可知重置时间则本实例停止发送，不能以自动重建实例绕过。跨进程协调未实现。
- 每页至多 20 场，每次调用至多 10 页；短页按实际条数推进 skip，不当作完整历史证据。空页、无新 ID 或达到 limit 停止；同 ID 冲突失败。结果为同源/同账号且按时间倒序，可能少于 limit，不保证完整历史或分页快照隔离。
- HTTP 401 及已核实的“缺少 Bearer Token”精确 JSON 提示为 AUTHENTICATION；429 为 RATE_LIMITED，超时为 TIMEOUT，其余非 200 为 UNAVAILABLE。HTML 403/404 不推断玩家私密/不存在。JSON/schema/null/错账号及 GraphQL errors 为 INVALID_RESPONSE；目前没有已核实的玩家隐私/不存在错误码，不做字符串猜测。即使可选字段报错也失败，正常显式 null 才保留 None；isStratzPublic 不用作拒绝查询条件。
- 不做缓存、重试、跨源切换。取消及意外编程错误传播；预计传输/解析失败使用固定异常文本并隐藏底层展示回溯。日志不记录请求、原始响应、昵称或完整身份。

## Alternatives considered
- Core 必选 HTTP 依赖：会把尚不需要联网的骨架与离线用例也绑定 HTTP，选 extra 保留轻量安装和原有无索引 wheel 检查。
- 自动接受部分 GraphQL 数据：无法证明缺口由正常缺失而非权限或服务故障导致，先严格失败。
- 单次 take=100 或无限翻页：前者可能被上游截断，后者容易耗尽额度；选有界分页并明确不完整保证。

## Consequences
调用方负责 Token、客户端关闭和唯一实例复用，展示应附 STRATZ 来源链接。仅支持玩家概况和最近比赛；精确 MMR、详情、补充源与宿主命令仍不在此交付中。隐私/不存在细化映射需新增真实错误证据与测试后再扩展，不能将陌生错误降级为空结果。

## Verification
schema 内省 200、无 GraphQL errors、客户端关闭已核对。实现后独立只读查询概况及默认 10/100 场成功，所需字段无缺失、同账号且客户端关闭。统一检查 407 passed、Core 99.87%；三个包构建和独立无索引 wheel 安装导入通过。依赖新增导致旧治理测试夹具重复 TOML 表，已修正构造方式并保留原禁止平台依赖断言；未改变门禁。完整证据及尚未实测项见接入任务。
