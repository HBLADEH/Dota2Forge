# Dota2Forge

**将 Dota 2 数据锻造成可复用的 Bot 能力。**

[GitHub 仓库](https://github.com/HBLADEH/Dota2Forge) · [CI 检查](https://github.com/HBLADEH/Dota2Forge/actions/workflows/ci.yml)

Dota2Forge 为 AstrBot 和 GsCore 提供共享的玩家查询、近期战绩、比赛分析、图片战报和订阅能力。业务复用 Dota2Forge Core，两端分别处理宿主命令、配置、身份、权限、消息与生命周期。当前处于 **M0 预发行**阶段。

| 模块 | 说明 | 文档 |
| --- | --- | --- |
| Dota2Forge Core | 账号校验、绑定、查询、分析与订阅用例 | [核心契约](docs/subsystems/core.md) |
| Dota2Forge Renderer | 共享文字与图片展示 | [渲染契约](docs/subsystems/renderer.md) |
| Dota2Forge Assets | 托管素材准备与更新 | [素材指南](docs/cookbook/illustrations.md) |
| astrbot_plugin_dota2forge | AstrBot 插件 | [插件 README](adapters/astrbot_plugin_dota2forge/README.md) |
| Dota2UID | GsCore 插件 | [插件 README](adapters/Dota2UID/README.md) |
| Dota2Forge Deploy | 后续部署整合 | [阶段说明](deploy/README.md) |

## 安装

使用对应的独立分发仓库，具体步骤与升级边界见插件说明：

- **AstrBot**：[alpha.10 预发行](https://github.com/HBLADEH/astrbot_plugin_dota2forge/releases/tag/v0.1.0a10) · [安装指南](docs/cookbook/astrbot-public-install.md)。需要 Python 3.12+、AstrBot >=4.5.0；停止宿主后用实际解释器安装固定版本运行组件，再冷启动。
- **GsCore**：[Dota2UID a12 随包预发行](https://github.com/HBLADEH/Dota2UID/releases/tag/v0.1.0a12) · [安装指南](docs/cookbook/gscore-bundled-install.md)。匹配项目运行库在插件专用目录准备；旧 a6–a9 首次升级需冷启动，兼容的新版随包更新支持受控重载。

AstrBot Cloud 的提交与审核情况见[发行记录](docs/cookbook/plugin-release.md)；[GsCore 索引 PR #40](https://github.com/Genshin-bots/GenshinUID-docs/pull/40)状态见[商店记录](docs/cookbook/gscore-store-publish.md)。本仓源码版本不代表商店已经同步。

## 能力与展示

命令统一使用 `do` 前缀，AstrBot 按唤醒设置添加 `/`。已实现账号绑定、玩家概况、段位预估 MMR、近期战绩分页、按 ID 或列表序号查看比赛、英雄热门出装、素材管理和默认关闭的订阅。玩家和比赛来自 STRATZ，热门出装来自 OpenDota。

比赛报告包含总览、两队详细统计与装备、团队优势曲线及 STRATZ IMP。预估 MMR 不等于精确天梯分，IMP 不等同官方 MVP，热门出装统计不代表最优出装。来源缺失明确保留，请求失败不伪装成无数据。

双端 README 使用“远古锻炉”主题和七张 GsCore 实机卡片，身份字段已脱敏，AstrBot 复用并注明来源。图片、尺寸与来源见[截图记录](docs/assets/screenshots/README.md)，配置页见[截图清单](docs/cookbook/plugin-showcase.md)。首次图片模式可在后台准备公共素材，角色、美术及字体遵循各自许可。

GsCore/QQ 与 AstrBot/OneBot 的基础图片查询、配置及生命周期已有独立验收；当前主题截图不代替另一端或所有客户端验收。[AstrBot 剩余场景](.agents/tasks/active/2026-10-02-astrbot-platform.md)和[真实订阅推送](.agents/tasks/active/2026-10-02-subscriptions.md)继续跟踪。英雄攻略、AI Tool 和部署整合尚未实现；本次 README 发行不操作生产宿主。

## 开发

准备 Python 3.12+、uv 和 Git，在仓库根目录执行：

```sh
uv sync --locked --all-packages
uv run --locked python scripts/check_governance.py --all
uv build --all-packages
```

普通测试禁网，不依赖真实 Token 或宿主环境；检查包含治理、Ruff、mypy、测试与覆盖率门槛。详细步骤见[开发指南](docs/cookbook/development.md)，五包元数据见[自动生成参考](docs/generated/packages.md)。

## 文档

- [当前架构](docs/architecture.md)与[治理契约](docs/subsystems/governance.md)
- [订阅契约](docs/subsystems/subscriptions.md)与[数据分析契约](docs/subsystems/analysis.md)
- [发行与验证指南](docs/cookbook/plugin-release.md)
- [项目规划](Dota2Forge_PROJECT_PLAN.md)与[治理补充](Dota2Forge_AI_Governance_Addendum.md)：规划材料，不代表现状

## 许可

代码使用 [MIT 许可证](LICENSE)。Dota 2 及相关角色、美术权利属于 Valve；第三方素材与字体见[素材说明](docs/cookbook/illustrations.md)。
