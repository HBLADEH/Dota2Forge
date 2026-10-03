# Provider 缓存、刷新与有限重试

Category: performance
Related task: [缓存任务](../../tasks/done/2026-10-02-cache-retry.md)
Related code: [缓存与重试实现](../../../packages/dota2forge-core/src/dota2forge_core/infrastructure/)
Related docs: [缓存契约](../../../docs/subsystems/cache-retry.md)

## Problem
STRATZ 与 OpenDota Provider 已实现一次请求一次来源的契约，但重复查询会重复消耗来源额度；此前没有可组合的刷新和有限重试边界。直接在 Core 用例中加缓存会混入来源时效和宿主配置，自动重试所有错误会隐藏隐私、认证或解析失败。

## Decision
- 在 ports 增加异步 `CachePort`；基础设施提供进程内 `MemoryCache` 和显式初始化/关闭的 `SQLiteCache`。MemoryCache 用单调时钟，SQLite 默认墙上时钟，两个实现都限制容量、TTL 和键长度；SQLite 使用调用方 codec，不使用不可信 pickle。
- `CachedProvider` 按来源、操作、账号/比赛 ID、近期条数隔离成功的不可变归一化值。普通读取不续期；`refresh_*` 绕过缓存并在成功后替换；账号/比赛失效显式删除。缓存类型、来源或目标不符返回 INVALID_RESPONSE，缓存数据库/codec失败返回 CacheError，不静默绕过或伪装为空。
- `RetryPolicy` 限制总尝试数、退避和上限。`RetryingProvider` 只重试 TIMEOUT/UNAVAILABLE；限流、认证、隐私、不存在、解析错误、取消和程序错误原样传播。sleep、client和生命周期由组合入口提供，默认 Runtime 不启用。
- 推荐组合为 `CachedProvider(RetryingProvider(provider, policy), cache)`；这样只对缓存未命中执行有限重试，成功后才缓存。缓存不是来源回退、完整历史保证或写入幂等工具。

## Alternatives considered
- 在 Dota2Service 内隐式缓存：会让所有消费者共享无法配置的时效，拒绝。
- 以 pickle 持久化归一化对象：本地缓存文件不应成为代码执行入口，拒绝；SQLite 要求显式 codec。
- 重试所有 ProviderError 或自动等待 429：会隐藏隐私/认证/解析语义并可能继续消耗限额，拒绝。
- 刷新失败立即删除旧值：会让一次暂时故障清空可用观察，选择保留旧值但把刷新错误返回调用方。

## Consequences
Core SDK 获得可选 Memory/SQLite TTL 缓存和显式刷新、有限重试；默认 AstrBot/GsCore 行为、来源主次和客户端所有权不变。SQLite codec、TTL、容量及重载清理必须由组合入口管理；当前未将装饰器接入运行中的宿主，未验证跨进程/长期运行性能或线上来源额度。

## Verification
新增9项缓存/重试测试，覆盖 MemoryCache、SQLiteCache、过期/容量/失效、来源和参数隔离、刷新失败、类型损坏、瞬时错误退避和非瞬时错误传播；与旧测试合计923项禁网测试通过，聚合覆盖率94.72%，治理工具独立97%，Core独立96%；Ruff、mypy47源文件、四包构建/隔离wheel及治理门禁结果记录于任务。
