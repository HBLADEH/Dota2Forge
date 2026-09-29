# Dota2Forge 初始工程底座

Category: architecture
Related task: [M0 初始化](../../tasks/done/2026-09-30-bootstrap.md)
Related code: [workspace](../../../pyproject.toml)
Related docs: [当前架构](../../../docs/architecture.md)

## Problem
初始目录仅有两份规划，无代码、依赖锁定、Git 或工程检查。用户确定品牌为 Dota2Forge，明确共享 Core 和双宿主边界，并选择 MIT 许可证。

## Decision
使用 Python 3.12+、uv workspace 和三个独立 src 包。Core 先保持无运行依赖，适配器只声明 Core 依赖；M0 不实现业务与宿主入口。使用 Ruff、mypy、pytest 与严格配置驱动的治理检查。通过解析包 TOML 生成参考文档。

补充方案将 M0 放在业务前，并优先服务现有 GsCore 场景，因此完成工程底座后先做 Core，再 Dota2UID，再 AstrBot。原规划的完整业务范围保留为后续里程碑。

## Alternatives considered
- 初期拆成多个仓库：跨包验证与初始开发协调成本较高，采用规划建议的 monorepo。
- 立即实现全套 Provider 和插件：尚无真实宿主与数据源验证环境，先完成补充方案要求的 M0。
- 手写包参考：与真实依赖易漂移，改为确定性读取 TOML。

## Consequences
骨架可安装、构建且无需平台 SDK。治理脚本可验证机械规则，但不能证明业务或插件可用。依赖下载需要网络，测试本身不访问外部服务。真实 API、插件生命周期和托管保护仍需后续验证。工具和规则变更需维护者评审。

## Verification
实际检查与产物验证结果记录在关联的 M0 任务中。
