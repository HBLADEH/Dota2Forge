# Dota2Forge

**Dota2Forge —— 将 Dota 2 数据锻造成可复用的 Bot 能力。**

[GitHub 仓库](https://github.com/HBLADEH/Dota2Forge) · [CI 检查](https://github.com/HBLADEH/Dota2Forge/actions/workflows/ci.yml)

Forge 意为“锻造、打造”。项目将 Steam、STRATZ、OpenDota 的原始数据与接口能力统一封装、加工和组合，目标是提供可供不同 Bot 框架复用的战绩查询、玩家分析、英雄数据、图片战报、订阅检测和 AI 分析能力。

当前阶段：**M0 工程底座**。已提供 uv workspace、三个可构建的 Python 包骨架、工程规则、决策与任务记录、治理检查、离线测试和 CI 配置。当前没有可安装即用的 Bot 插件或 Dota 2 查询功能。

| 模块 | 名称 | 位置 |
| --- | --- | --- |
| 总项目 | Dota2Forge | 本仓库 |
| 共享核心 | Dota2Forge Core | [packages/dota2forge-core](packages/dota2forge-core/) |
| AstrBot 插件 | Dota2Forge / astrbot_plugin_dota2forge | [适配器骨架](adapters/astrbot_plugin_dota2forge/) |
| GsCore 插件 | Dota2UID | [适配器骨架](adapters/Dota2UID/) |
| 部署整合 | Dota2Forge Deploy | [阶段说明](deploy/README.md) |

Dota2UID 底层复用 Dota2Forge Core；两端不各自实现一套 Dota 2 业务。

## 开发

准备 Python 3.12+ 和 uv，在仓库根目录执行：

```sh
uv sync --locked --all-packages
uv run --locked python scripts/check_governance.py --all
uv build --all-packages
```

依赖安装和首次构建可能联网下载工具；测试禁用 socket，普通检查不调用真实 API。
详细操作见 [开发指南](docs/cookbook/development.md)。

## 文档

- [当前架构](docs/architecture.md)
- [治理检查契约与限制](docs/subsystems/governance.md)
- [包参考（自动生成）](docs/generated/packages.md)
- [项目规划](Dota2Forge_PROJECT_PLAN.md) 与 [AI 治理补充](Dota2Forge_AI_Governance_Addendum.md)：规划材料，不代表现状
- [M0 交付任务](.agents/tasks/done/2026-09-30-bootstrap.md)
- [后续 Core 最小闭环](.agents/tasks/active/2026-09-30-core-mvp.md)

后续顺序：Core 最小业务闭环 → Dota2UID（GsCore）→ AstrBot → 订阅与渲染扩展 → Deploy。完整 Phase 1 功能范围保留在规划中。

许可证：[MIT](LICENSE)。
