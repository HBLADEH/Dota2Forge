# Dota2Forge

**Dota2Forge —— 将 Dota 2 数据锻造成可复用的 Bot 能力。**

[GitHub 仓库](https://github.com/HBLADEH/Dota2Forge) · [CI 检查](https://github.com/HBLADEH/Dota2Forge/actions/workflows/ci.yml)

Forge 意为“锻造、打造”。项目将 Steam、STRATZ、OpenDota 的原始数据与接口能力统一封装、加工和组合，目标是提供可供不同 Bot 框架复用的战绩查询、玩家分析、英雄数据、图片战报、订阅检测和 AI 分析能力。

当前阶段：**M0 / 双端宿主接入**。Core 已实现严格账号校验、SQLite 绑定、查询用例和 STRATZ 联网 Provider。Dota2UID 已通过真实宿主热加载、受控重载、卸载清理与恢复冷启动，最终保持 ready；用户已确认 QQ 单会话帮助/绑定/玩家/战绩均正常回复，证据见 [接入任务](.agents/tasks/done/2026-09-30-dota2uid-first-loop.md)。AstrBot 4.28.2 已安装发现桥接并验证配置、冷启动、重载和关闭恢复；用户确认OneBot单会话菜单、绑定、玩家、战绩分页和序号详情图片正常且可读，权限等剩余场景见 [AstrBot 任务](.agents/tasks/active/2026-10-02-astrbot-platform.md)。普通测试禁网。

| 模块 | 名称 | 位置 |
| --- | --- | --- |
| 总项目 | Dota2Forge | 本仓库 |
| 共享核心 | Dota2Forge Core | [packages/dota2forge-core](packages/dota2forge-core/) |
| AstrBot 插件 | Dota2Forge / astrbot_plugin_dota2forge | [适配器与接入步骤](docs/cookbook/astrbot.md) |
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

STRATZ 主源已实现概况、当前段位、最近比赛和独立按 ID 的最小历史详情；Dota2UID 的直接ID、列表选择/取页和图片/文本模式已实现。QQ单会话已确认菜单、玩家、账号、分页、序号及直接ID详情；2026-10-02冷启动与两轮停用/重载后用户复测回复正常、图片可读，[证据](.agents/artifacts/gscore-image-lifecycle-v1/README.md)。共享Renderer包含菜单、玩家、状态、近期和详情卡；AstrApplication与AstrBot桥接消费同一Core/Renderer，宿主生命周期和OneBot主流程图片已验证，[证据](.agents/artifacts/astrbot-host-v1/README.md)。配置及只读验证见[STRATZ接入](docs/cookbook/stratz.md)，安装见[Dota2UID接入](docs/cookbook/dota2uid.md)与[AstrBot接入](docs/cookbook/astrbot.md)，图片契约见[Renderer契约](docs/subsystems/renderer.md)。OpenDota独立Provider、显式交叉核验和经济/购买分析SDK已实现并禁网验证，[步骤](docs/cookbook/opendota.md)；分析尚未在线查询或部署到Bot，默认主源仍为STRATZ，IMP仍未实现。Valve按需补充仍在规划中。

[STRATZ基础接入已完成](.agents/tasks/done/2026-09-30-stratz-provider.md)。共享Renderer、双端基础/详情卡片与文本回退已禁网验证；GsCore/QQ和AstrBot/OneBot首轮主流程图片及生命周期已验证，其他实机边界单独跟踪。OpenDota补充SDK、显式TTL缓存/有限重试、经济/购买分析端口已实现；IMP仍未实现。Step13已接入玩家/指定比赛完成报告、详情分析、双端受控调度和schema v3持久投递尝试，两端按部署分别启用，不盲目重发；见[订阅契约](docs/subsystems/subscriptions.md)，真实推送等[任务](.agents/tasks/active/2026-10-02-subscriptions.md)保持active。后续AI与Deploy，完整范围保留在规划中。

许可证：[MIT](LICENSE)。
