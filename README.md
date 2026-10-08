# Dota2Forge

**Dota2Forge —— 将 Dota 2 数据锻造成可复用的 Bot 能力。**

[GitHub 仓库](https://github.com/HBLADEH/Dota2Forge) · [CI 检查](https://github.com/HBLADEH/Dota2Forge/actions/workflows/ci.yml)

Forge 意为“锻造、打造”。项目将 Steam、STRATZ、OpenDota 的原始数据与接口能力统一封装、加工和组合，目标是提供可供不同 Bot 框架复用的战绩查询、玩家分析、英雄数据、图片战报、订阅检测和 AI 分析能力。

当前阶段：**M0 / 双端宿主接入**。Core 已实现严格账号校验、SQLite 绑定、查询用例和 STRATZ 联网 Provider。Dota2UID 已通过真实宿主热加载、受控重载、卸载清理与恢复冷启动，最终保持 ready；用户已确认 QQ 单会话帮助/绑定/玩家/战绩均正常回复，证据见 [接入任务](.agents/tasks/done/2026-09-30-dota2uid-first-loop.md)。AstrBot 4.28.2 已安装发现桥接并验证配置、冷启动、重载和关闭恢复；用户确认OneBot单会话菜单、绑定、玩家、战绩分页和序号详情图片正常且可读，权限等剩余场景见 [AstrBot 任务](.agents/tasks/active/2026-10-02-astrbot-platform.md)。普通测试禁网。

| 模块 | 名称 | 位置 |
| --- | --- | --- |
| 总项目 | Dota2Forge | 本仓库 |
| 共享核心 | Dota2Forge Core | [packages/dota2forge-core](packages/dota2forge-core/) |
| AstrBot 插件 | Dota2Forge / astrbot_plugin_dota2forge | [插件说明](adapters/astrbot_plugin_dota2forge/README.md) · [接入步骤](docs/cookbook/astrbot.md) |
| GsCore 插件 | Dota2UID | [插件说明](adapters/Dota2UID/README.md) · [安装步骤](docs/cookbook/dota2uid.md) |
| 部署整合 | Dota2Forge Deploy | [阶段说明](deploy/README.md) |

Dota2UID 底层复用 Dota2Forge Core；两端不各自实现一套 Dota 2 业务。

现已公开 **0.1.0a4 预览版**：[Dota2UID / GsCore](https://github.com/HBLADEH/Dota2UID/releases/tag/v0.1.0a4) · [Dota2Forge / AstrBot](https://github.com/HBLADEH/astrbot_plugin_dota2forge/releases/tag/v0.1.0a4)。本版加入装备简称、出装图片及更详细的比赛卡，四个包统一版本。首次安装及升级都需退出宿主、运行插件内安装器再冷启动：[GsCore](docs/cookbook/gscore-public-install.md) · [AstrBot](docs/cookbook/astrbot-public-install.md)。

新源码加入[后台素材准备](docs/cookbook/illustrations.md)：AstrBot a8、Dota2UID a6、Assets a1，Core/Renderer保持a4。首次图片模式自动补齐，支持状态/补缺/更新命令；Dota2UID a6 采用[随包运行库](docs/cookbook/gscore-bundled-install.md)与主人核心安装/状态入口，缺包仍可诊断。公开资产以 [Dota2UID Releases](https://github.com/HBLADEH/Dota2UID/releases) 为准；AstrBot a8 尚待发布。

[AstrBot商店申请](https://cloud.astrbot.app/plugin/HBLADEH/astrbot_plugin_dota2forge?tab=versions)已提交，页面显示等待安全检查；[GsCore PR #40](https://github.com/Genshin-bots/GenshinUID-docs/pull/40)仍待审核，均不代表已上架。本版离线/安装证据与真实聊天未验收边界见[发行记录](.agents/artifacts/a4-layout-release-v1/README.md)，生产版本和路由未更改。

双端插件说明参考 GenshinUID 的组织方式，包含独立生成的[Q 版主宰图标](docs/assets/branding/juggernaut-icon-v1.png)与功能展示位；按用户要求共用AstrBot主宰出装实机原图，GsCore说明注明原宿主。其余按[截图清单](docs/cookbook/plugin-showcase.md)补充，已采用图片与筛选范围见[来源记录](docs/assets/screenshots/README.md)。

现行源码命令统一使用 `do` 前缀：`do菜单`、`do绑定 <ID>`、`do查询 [ID]`、`do战绩`、`do比赛`及订阅/管理入口。`do查询`展示[段位预估MMR](docs/subsystems/ranks.md)，含区间/冠绝下界和非精确说明；旧`dota`入口不再注册。[英雄热门出装](docs/cookbook/hero-items.md)已实现，例如`do斧王出装`、`doAM出装`，无需绑定，来自OpenDota。[STRATZ攻略验证](docs/cookbook/hero-guides.md)已有可行数据方案，攻略命令尚未实现。2026-10-05本机双端均已升级匹配0.1.0a2运行库、桥接和新图标，恢复ready/image；[AstrBot](.agents/artifacts/astrbot-screenshot-update-v1/README.md)OneBot已连接，[GsCore](.agents/artifacts/gscore-current-deployment-v1/README.md)本轮尚无客户端连接，既有AstrBot GsCore桥接仍关闭。新指令/MMR真实聊天待验收，AstrBot主宰实机出装卡已补入说明。

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

图片卡片已支持共享深色主题和按ID映射的本地官方英雄/装备插图；资源须[显式下载并配置目录](docs/cookbook/illustrations.md)，不在回复时联网，不随MIT wheel分发。2026-10-05两端已配置独立素材并部署背景，用户确认所测图片正常，[记录](.agents/artifacts/dota-style-host-v2/README.md)；分页/五人详情/手机可读性仍待本轮逐项反馈。
