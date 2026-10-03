# Provider 缓存、刷新与有限重试

Core 的基础 `Dota2Service`、`MatchDetailService` 和原始 Provider 保持一次调用一次来源请求的语义。缓存和重试是组合入口显式加入的基础设施装饰器，默认 AstrBot/GsCore 不启用，因此不会改变当前已验证的消息行为。

## 缓存

`CachePort` 是异步键值端口；[MemoryCache](../../packages/dota2forge-core/src/dota2forge_core/infrastructure/cache.py) 使用进程内有界字典、单调时钟和 TTL，[SQLiteCache](../../packages/dota2forge-core/src/dota2forge_core/infrastructure/cache.py) 使用调用方提供的 codec、专用 SQLite 文件和显式 `initialize()`/`close()`。SQLite 的 TTL 默认使用墙上时钟，便于跨进程读取；MemoryCache 默认使用单调时钟。构造均不打开文件、不启动任务。

`CachedProvider` 为每个成功的玩家、近期列表和比赛详情生成包含 `DataSource`、账号/比赛 ID 与近期条数的键。不同来源、账号和条数互相隔离；缓存值必须仍是正确的归一化类型、来源和目标 ID，否则删除并返回 `INVALID_RESPONSE`。ProviderError、取消、程序错误和缓存写入失败不会被转为空结果；刷新失败时旧的有效条目仍可由普通读取使用。

普通 `get_*` 在 TTL 内返回同一份不可变归一化结果，不续期；过期后重新查询。`refresh_player`、`refresh_recent_matches` 和 `refresh_match_detail` 明确绕过缓存，成功后替换条目。`invalidate_account` 清除该账号的资料及1–100条数的近期条目，`invalidate_match` 清除详情；没有后台刷新、来源回退或持久化绑定状态。SQLite codec 不可信或数据库版本/应用标识不匹配时返回固定 `CacheError`，不静默绕过。

## 有限重试

`RetryPolicy` 默认最多三次总尝试，退避为0.25、0.5、1秒且上限2秒；最大五次，参数必须显式通过校验。`RetryingProvider` 只重试 `TIMEOUT` 和 `UNAVAILABLE`，并由注入的异步 sleep 执行等待。`RATE_LIMITED` 的等待应交给调用方，`AUTHENTICATION`、`PRIVATE`、`NOT_FOUND`、`INVALID_RESPONSE`、取消和未分类程序错误立即传播。最后一次仍失败时保留原 `ProviderError` 和来源。

重试与缓存可组合：通常将 `RetryingProvider` 放在 `CachedProvider` 内侧，使缓存未命中时最多执行有限重试，成功结果才写入缓存；也可以只使用其中一个装饰器。两个装饰器都不拥有或关闭下层 HTTP 客户端，生命周期仍由组合入口管理。重试不等于幂等保证；GET 查询当前是只读的，写入/订阅操作不得复用此策略。

## 验证边界

禁网测试覆盖 TTL、容量、SQLite 持久化/失效、错误 codec、来源与参数隔离、刷新失败保留旧值、错误类型校验、退避和取消。当前运行中的 AstrBot 未接入装饰器；生产启用前应由 Runtime 显式决定 TTL、容量、缓存文件、codec 和策略，并单独验证清理/重载。
