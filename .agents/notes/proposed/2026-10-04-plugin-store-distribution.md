# 双平台插件商店分发建议

Category: architecture
Related task: [拆分评估](../../tasks/done/2026-10-04-plugin-store-assessment.md)
Related code: [当前 workspace](../../../pyproject.toml)
Related docs: [当前架构](../../../docs/architecture.md)

## Problem

截至 2026-10-04，四个独立包和双端消费者已实现，共享 Core/Renderer 不依赖宿主 SDK，两个适配器互不依赖。GsCore/QQ、AstrBot/OneBot 的基础查询、图片和受控生命周期有本机证据；订阅最新代码已安装，但真实推送、权限和部分聊天边界仍待验收。版本均为 0.1.0a1，不能按规划 Step 数推算产品完成百分比。

当前安装不是商店闭环：AstrBot ZIP 仅包含发现桥接，其 requirements 引用尚未发布的适配器包；GsCore 安装器分别写桥接和配置，普通克隆不会执行安装器。两端仍需手动准备三个 wheel。主仓库根目录既没有 AstrBot 的 metadata.yaml/main.py，也没有 GsCore 插件发现入口，根 pyproject 是无业务运行依赖的开发 workspace，直接登记主仓库不能解决安装。

现有隔离 wheel 测试证明包可安装，不证明商店首次安装成功。共享包升级有模块缓存和 Pillow DLL 占用的已知故障；GsCore 原生重载/卸载不能替代显式关闭。

## Decision

建议先拆分发布入口，继续在 Dota2Forge 单仓开发与联合验证。此记录为待实施方案，尚未创建仓库、发布包或获得商店收录。

建议增加两个由主仓库发布版本确定性生成的分发仓库：

- astrbot_plugin_dota2forge：根目录放 main.py、metadata.yaml、_conf_schema.json、requirements.txt、README 和 LICENSE，元数据 repo 指向这个分发仓库。
- Dota2UID：根目录放 __init__.py、用于宿主依赖检查的 pyproject.toml、README、LICENSE 和配置说明；需要补首次配置准备及缺 Token 的明确待配置状态。此 pyproject 不应直接复制带 workspace 源引用的开发配置。

以当前桥接方案为基础，优先评估将 Core、Renderer 和两个适配器共四个 wheel 发布到 PyPI，让商店宿主自动解析依赖。分发仓库只生成与该次发布匹配的桥接和依赖清单，用户不需要 uv、源码 checkout 或手动 pip。共享库无需另建源码仓库。每次发布使用新版本，固定实际验证过的版本组合，禁止重新发布相同 0.1.0a1 来代表不同源码。

两个分发仓库只接受主仓库生成结果；维护源码、契约和联合测试仍在这里。发布顺序为联合检查、构建与干净安装、共享包及适配器包可取得、同步分发入口、实机安装验收、提交商店收录。流水线与治理配置实施时仍须维护者评审。

首个商店版本可限定为 STRATZ 绑定、玩家、近期和单局图片查询；未完成实机验收的订阅默认关闭或明确标为实验功能。AI/IMP、Valve 和 Deploy 不必成为这个有限版本的前置条件，不能宣传为已有能力。

## Alternatives considered

- 将开发拆成 Core、Renderer、两端和 Deploy 多仓：现阶段公共契约与 schema v3 刚变化，协调依赖、测试和升级成本更高，缺少独立维护需求，暂不推荐。以后各端发布节奏或维护团队独立时再评估。
- 仅登记现有主仓库或复制 adapters 子目录：根发现布局和未发布依赖问题仍然存在，不构成一键安装。
- 发布产物内携带共享源码：若包索引不可用，可由同一版本源码自动生成，保留许可、资源及校验；需处理模块路径和重载冲突。不能人工维护两份业务源码。
- 使用 Git URL 拉取整个 workspace 作为运行依赖：增加构建、网络和相对 workspace 引用问题，固定 wheel 更符合当前包边界。

## Consequences

开发仍能在一个 PR 验证双方消费者，但新增两个发布入口、包发布和版本兼容矩阵。采用全 wheel 方案后，商店更新桥接不等于已更新运行中的库；必须验证宿主依赖更新开关、版本检查、关闭资源和冷启动路径。GsCore 基线在关闭自动依赖更新时不会检查已安装版本是否满足新约束，不能仅依赖精确版本声明保证升级。

一键安装定义为已有兼容宿主内点击安装，自动取得插件与依赖；STRATZ Token、机器人连接及管理员设置仍需用户配置，不承诺零配置。Python >=3.12、Pillow/HTTPX 的兼容和下载可达性必须作为真实安装矩阵检查。原始配置、绑定与订阅库保留在各端专用数据目录；schema 升级后的回退须用兼容版本或备份恢复验证，不能只回退代码。

发布前必须取得以下证据：干净宿主安装无需本地 wheel；无 Token 时可配置且有明确状态；配置后完整基础命令可用；升级/重载/卸载不重复注册、不泄漏资源且保留数据；独立商店收录成功。覆盖 Windows/Linux 的拟支持部署方式，AstrBot 当前仅按 >=4.28.2,<4.29 验证，不直接扩大兼容声明。

## Verification

本次静态核对两个安装器、四包元数据、契约、任务和公开宿主源码。AstrBot 按项目固定 commit 的 [插件管理器](https://github.com/AstrBotDevs/AstrBot/blob/3c7adafa1397e182d60b1016bf88759265113c8a/astrbot/core/star/star_manager.py)及 updater 验证根元数据与 requirements 路径；[官方集合页](https://github.com/AstrBotDevs/AstrBot_Plugins_Collection)已标记弃用并指向 [cloud](https://cloud.astrbot.app/)，文档仍有旧市场表单说明，申请时以实际入口为准。

GsCore 按项目固定 commit 的 [安装流程](https://github.com/Genshin-bots/gsuid_core/blob/87c06f11ae10c12b3bb8e76b3c6f420c831282a8/gsuid_core/utils/plugins_update/_plugins.py)及 server.py 核对克隆、根发现和依赖检查；[公开索引](https://docs.sayu-bot.com/plugin_list.json)包含仓库和分支字段，本次未见 Dota2UID。收录申请方式和维护者审核要求未核实，不臆测自动上架。

本次检查结果记录于关联任务。没有进行真实商店安装、发布、收录申请、宿主操作或聊天发送；已有本机证据不能替代这些验收。
