# 赛前购买时间诊断

2026-10-09 用户报告正式版 `do比赛 9035146588` 返回 STRATZ 数据不完整/无法解析。a7 分发清单使用 Core a4，基础详情之后还会查询经济/购买分析。

本机只读请求观察到：基础详情有效，十名参赛者；分析包含 235 条购买事件，其中 48 条时间小于零，最早 -89 秒。旧代码在购买时间映射处返回 INVALID_RESPONSE；网络客户端正常关闭。原始响应只用于内存校验，没有保存账号、昵称或响应正文。

[诊断入口](diagnose.py) 只输出字段类型、计数、时间范围及固定错误分类，不输出凭据、身份、昵称、原始 GraphQL 错误或响应。它不是普通测试的一部分；只有显式执行才读取 uv 注入的环境并联网：

```powershell
uv run --env-file D:/workstation/Dota2Forge/.env --locked python .agents/artifacts/stratz-match-detail-response-v1/diagnose.py 9035146588
```

修复后的只读复测基础详情与分析均有效，235 条事件（包括 48 条赛前负时间）完整保留，客户端已关闭，见[脱敏摘要](live-check.json)。统一入口1955项禁网测试通过，聚合覆盖率93.04%；Ruff、mypy及三个独立覆盖率门槛均通过，[日志](offline-check.log)。五包[构建](build.log)与[离线安装导入](wheel-smoke.log)通过。

修复、合成回归和复测结果见[任务](../../tasks/done/2026-10-09-stratz-match-detail-response.md)及[决策](../../notes/implemented/2026-10-09-pregame-purchase-time.md)。正式版部署与真实 QQ 回复仍未复测；本地产物沿用现有版本，仅用于验证。
