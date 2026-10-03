# 缓存与有限重试的组合入口

缓存和重试属于 Core 外的基础设施组合，不读取环境变量，也不改变原始 Provider。先构造并拥有一个来源 Provider，再按需要装饰；HTTP 客户端仍由最外层组合入口关闭。

```python
from dota2forge_core import CachedProvider, MemoryCache, RetryPolicy, RetryingProvider

cache = MemoryCache(capacity=256)
retrying = RetryingProvider(
    provider,
    RetryPolicy(max_attempts=3, initial_delay_seconds=0.25),
)
cached = CachedProvider(retrying, cache, ttl_seconds=300)

profile = await cached.get_player(account_id)  # TTL 内命中
fresh = await cached.refresh_player(account_id)  # 明确绕过缓存
recent = await cached.get_recent_matches(account_id, 20)  # 条数进入缓存键
await cached.invalidate_account(account_id)
```

实际服务应在组合入口使用 `async with httpx.AsyncClient(...)`，并在宿主停用时先关闭 Provider 相关资源，再关闭 `SQLiteCache`。装饰器不关闭下层 client；同一个 cache 可共享，但键已包含来源，SQLite 文件建议按部署隔离。

SQLite 需要稳定的 codec，不能用不可信 pickle：

```python
from dota2forge_core import SQLiteCache

cache = SQLiteCache(path, codec, capacity=2048)
await cache.initialize()
try:
    await cache.set("example", encoded_value, 300)
    value = await cache.get("example")
finally:
    await cache.close()
```

只缓存成功的不可变归一化结果。认证、隐私、解析错误和限流不会重试；429 返回的等待由调用方决定。刷新请求失败时不会删除旧条目，但刷新调用本身仍返回错误。不要把缓存命中当作新的抓取时间，不要用旧缓存掩盖明确的来源拒绝。

验证命令：

```sh
uv run --locked python scripts/check_governance.py --all
```

当前 AstrBot/GsCore Runtime 未启用该装饰器；启用需要单独配置和联调。Step 11 已通过 923 项禁网测试、四包构建和隔离 wheel 验证。
