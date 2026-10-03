# 缓存、刷新与有限重试

Status: done

## 目标
按规划 Step 11 为 Core Provider 增加可组合的有界缓存、显式刷新和有限重试策略，保持 AstrBot/GsCore 默认行为和 STRATZ 主源不变。

## 非目标
不更改运行中的宿主配置，不发送消息，不实现来源自动切换、跨源拼接、后台刷新、订阅、AI、IMP 或 Deploy。OpenDota 仍只作为显式 SDK 使用。

## 验收
- [x] 提供无 I/O 构造的 CachePort、MemoryCache 和显式初始化的 SQLiteCache。
- [x] Provider 缓存按来源/账号/参数隔离，只缓存成功值；过期、容量、显式刷新、失效和取消边界可观察。
- [x] 有限重试仅覆盖 TIMEOUT/UNAVAILABLE，次数/退避可配置；不重试限流、认证、隐私、解析错误、取消或程序错误。
- [x] 缓存/重试组合保持来源、时间、缺失和错误语义，不拥有或关闭调用方 HTTP 客户端。
- [x] 检查现有 Core、OpenDota、STRATZ、Renderer 和双端消费者兼容；更新契约、操作、决策与规划。
- [x] 统一离线门禁、四包构建和隔离 wheel 通过。

## 影响模块与决策
[Core](../../../packages/dota2forge-core/)、[OpenDota](../../../docs/subsystems/opendota.md)、[缓存契约](../../../docs/subsystems/cache-retry.md)、[决策](../../notes/implemented/2026-10-02-cache-retry.md)。

## 验证证据
Step 10 基线为914项禁网测试；本任务新增9项测试，最终923项禁网测试通过，聚合覆盖率94.72%，治理工具独立97%，Core独立96%；Ruff format/lint、mypy47源文件通过。

四包构建和隔离 wheel smoke 通过；新增Core wheel可导入CachePort、MemoryCache、SQLiteCache、RetryPolicy、RetryingProvider和CachedProvider。未更新运行中的AstrBot或GsCore宿主。

## 阻塞与下一步
Step 11已完成并归档。缓存尚未接入运行中的AstrBot Runtime；后续如需生产启用，应由组合入口显式配置 TTL、容量和策略并单独联调。下一项按规划为Step12 IMP/经济、购买序列，但需先核对来源字段和口径。
