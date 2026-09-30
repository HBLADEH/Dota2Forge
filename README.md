# Dota2Forge

**Dota2Forge —— 将 Dota 2 数据锻造成可复用的 Bot 能力。**

[GitHub 仓库](https://github.com/HBLADEH/Dota2Forge) · [CI 检查](https://github.com/HBLADEH/Dota2Forge/actions/workflows/ci.yml)

Forge 意为“锻造、打造”。项目将 Steam、STRATZ、OpenDota 的原始数据与接口能力统一封装、加工和组合，目标是提供可供不同 Bot 框架复用的战绩查询、玩家分析、英雄数据、图片战报、订阅检测和 AI 分析能力。

当前阶段：**M0 / 首个宿主接入**。Core 已实现严格账号校验、SQLite 绑定、查询用例和 STRATZ 联网 Provider。Dota2UID 已通过真实宿主热加载、受控重载、卸载清理与恢复冷启动，最终保持 ready；用户已确认 QQ 单会话帮助/绑定/玩家/战绩均正常回复，证据见 [接入任务](.agents/tasks/done/2026-09-30-dota2uid-first-loop.md)。普通测试禁网，AstrBot 仍为包骨架。

| 模块 | 名称 | 位置 |
| --- | --- | --- |
| 总项目 | Dota2Forge | 本仓库 |
| 共享核心 | Dota2Forge Core | [packages/dota2forge-core](packages/dota2forge-core/) |
| AstrBot 插件 | Dota2Forge / astrbot_plugin_dota2forge | [适配器骨架](adapters/astrbot_plugin_dota2forge/) |
| GsCore 插件 | Dota2UID | [适配器与安装步骤](docs/cookbook/dota2uid.md) |
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
- [Core 业务契约](docs/subsystems/core.md) 与 [离线闭环验证](docs/cookbook/core-offline.md)
- [治理检查契约与限制](docs/subsystems/governance.md)
- [包参考（自动生成）](docs/generated/packages.md)
- [项目规划](Dota2Forge_PROJECT_PLAN.md) 与 [AI 治理补充](Dota2Forge_AI_Governance_Addendum.md)：规划材料，不代表现状
- [M0 交付任务](.agents/tasks/done/2026-09-30-bootstrap.md)
- [Core 最小闭环进展与联调待办](.agents/tasks/done/2026-09-30-core-mvp.md)

STRATZ 主源已实现概况、当前段位和最近比赛，支持有界分页、错误分类、限流等待和客户端生命周期注入；Dota2UID 已完成 QQ 单会话绑定和查询。配置及只读验证见 [STRATZ 接入](docs/cookbook/stratz.md)，宿主安装见 [Dota2UID 接入](docs/cookbook/dota2uid.md)。OpenDota 独立补充与交叉核验、Valve 按需补充仍在规划中，无自动回退，见 [选型决策](.agents/notes/implemented/2026-09-30-provider-selection.md)。

[STRATZ 基础接入已完成](.agents/tasks/done/2026-09-30-stratz-provider.md)。后续顺序：Dota2UID（GsCore）→ AstrBot → 详情/IMP 与补充数据源 → 订阅与渲染扩展 → Deploy。完整 Phase 1 功能范围保留在规划中。

许可证：[MIT](LICENSE)。
