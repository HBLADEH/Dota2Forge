# 验证 Core 离线闭环

环境准备与统一检查见 [开发指南](development.md)，行为定义见 [Core 契约](../subsystems/core.md)。无需 Token、真实 Dota 账号、GsCore 或 AstrBot；不会访问真实 API。

安装 workspace 后，在仓库根目录运行：

~~~sh
uv sync --locked --all-packages
uv run --locked pytest tests/core --cov-reset --cov=dota2forge_core --cov-branch --cov-fail-under=80
~~~

单独回放用户流程（局部运行不用于报告整体覆盖率）：

~~~sh
uv run --locked pytest tests/core/test_workflow.py -v --no-cov
~~~

流程使用 [合成数据](../../tests/core/fixtures/public-player.json) 和 pytest 临时 SQLite 文件，覆盖未绑定 → SteamID64 绑定 → 重建仓库 → 玩家/最近比赛查询 → 显式改绑 → 解绑。其他测试覆盖身份隔离、并发冲突、持久化、未知/损坏数据库、锁等待、有效空列表和错误分类。

pytest 默认禁止 socket 和 DNS。异步测试仅在创建事件循环内部唤醒连接时暂时启用 socket，在运行任何业务协程前恢复禁网；测试另行断言协程与工作线程内的 socket 仍被阻止。

适配器实现时，以固定 namespace 和可信宿主身份创建 PlatformIdentity，构造并初始化 SQLiteBindingRepository，注入 PlayerProvider、MatchProvider、SystemClock 后使用 Dota2Service。fixture Provider 仅在测试中，不能当生产默认值。平台鉴权和消息展示不在 Core 内实现。

## 后续真实联调准备

- [API 评测](../../.agents/tasks/done/2026-09-30-stratz-evaluation.md) 已核实 Bearer Token、User-Agent: STRATZ_API、部分 GraphQL schema 与单账号数据；按 [接入任务](../../.agents/tasks/done/2026-09-30-stratz-provider.md) 补齐字段、错误与隐私验证，不得将归一化 fixture 当作远端响应样本。
- 已实现的 STRATZ Provider 使用显式注入的 Token 和可关闭 HTTP 客户端，独立 [联调入口](stratz.md) 使用本机配置的授权账号；先通过禁网检查再运行。凭据不写源码/fixture/日志，Core 不自行读取配置。
- Windows 原生 GsCore 的版本及源码接口已核实，见 [宿主基线](../subsystems/gscore-host.md)；编写 Dota2UID 时仍须实现并验证加载入口、身份转换与资源生命周期。
- 真实查询、宿主命令与资源释放需另列验证证据；离线通过不等于这些项目已通过。
