# 双平台商店分发核查

首次核查：2026-10-05；2026-10-06已实现a3分发与公共运行包CLI。GsCore公开仓库/Releases及固定隔离SDK安装、升级/卸载通过，索引PR #40待审核；PyPI未发布，直接热安装缺包执行限制仍在。真实聊天、商店界面和维护者合并分列验收，见[执行记录](../cookbook/gscore-store-publish.md)。其余历史核查证据保留。

## 当前项目

[架构](../architecture.md)保留四个 src 包，Core/Renderer 不依赖宿主 SDK，两端互不依赖。已有本机 GsCore/QQ 和 AstrBot/OneBot 基础图片及生命周期证据；最新 do 命令、MMR、出装代码与历史宿主验收不能混为同一个版本。订阅真实推送及部分权限场景仍在[任务](../../.agents/tasks/active/2026-10-02-subscriptions.md)中。

| 检查项 | AstrBot | GsCore / Dota2UID |
| --- | --- | --- |
| 开发仓库根发现入口 | 无 main.py、metadata.yaml | 无 __init__.py 或宿主识别的同名嵌套入口 |
| 现有桥接 | 安装器生成四文件 ZIP | 安装器写 plugins/Dota2UID/__init__.py |
| 取得运行库 | 候选requirements锁定三个未发布PyPI运行包 | 公开CLI安装固定Releases wheel，保留Pillow宿主约束并pip check；原生清单保留版本比较 |
| 首次配置 | 合法空Token为awaiting_config，保存配置后重载 | 首启独占创建空配置；合法空Token为awaiting_config，填写后停用/重载 |
| 实际商店安装及升级 | 未验收 | 隔离SDK公开安装/升级/卸载通过，真实商店界面与QQ待验收 |

根 pyproject 是 package=false、dependencies=[] 的 uv 开发 workspace；宿主不会自动执行 uv workspace 或本项目安装器。[AstrBot 安装器](../../adapters/astrbot_plugin_dota2forge/src/astrbot_plugin_dota2forge/install.py)只打包 main.py、metadata.yaml、_conf_schema.json、requirements.txt，依赖 astrbot-plugin-dota2forge==0.1.0a2；元数据 repo 仍指向本开发仓库。[Dota2UID 安装器](../../adapters/Dota2UID/src/Dota2UID/install.py)另写数据目录配置，普通 Git 克隆不会执行安装器。新生成的候选入口另含根发现文件、版本guard和宿主依赖清单，Runtime启动独立处理首次配置。

首次调研时四包为0.1.0a1，现已升为0.1.0a2候选。2026-10-05请求PyPI四项目JSON接口均404；2026-10-06复核GsCore所需三个项目仍404，不推断名称一定可注册，也不排除其他私有索引。

## GsCore 收录与安装

运行索引为[plugin_list.json](https://docs.sayu-bot.com/plugin_list.json)，源码在 Genshin-bots/GenshinUID-docs 的 vp 分支、docs/public/plugin_list.json。现场 HTTP 200，42 条插件，包含 MingChaoBQ，尚无 Dota2UID；与固定提交 0b04c49 的 JSON 解析结果相同。

[MingChaoBQ PR #39](https://github.com/Genshin-bots/GenshinUID-docs/pull/39/files)于 2026-09-27 合并到 vp，仅改该文件，+13/-1：plugins 新增条目，并将 ID 加到 fun_plugins。这证明当前有向文档仓库提交 PR 的收录路径；合并仍由维护者决定，不推断审核时长或完整审核规则。

条目实例包含 link、avatar、cover、branch、type、content、info、installMsg、alias。Dota2UID 属于游戏查询，现有 tool_plugins 包含 GenshinUID、CS2UID 等同类，是合理候选分类，需维护者认可；不能照抄表情包的 fun_plugins。

本次 git ls-remote 核实 GsCore master 为 87c06f1，与[本机基线](gscore-host.md)相同。[安装实现](https://github.com/Genshin-bots/gsuid_core/blob/87c06f11ae10c12b3bb8e76b3c6f420c831282a8/gsuid_core/utils/plugins_update/_plugins.py)从索引取 link/branch，浅克隆到插件目录，调用 reload_plugin；没有任意仓库子目录选择或本项目安装器执行步骤。目录名取 link 的最后一段，索引 key 不负责重命名目录；将 Dota2UID key 指向 Dota2Forge 主仓仍会克隆到 Dota2Forge。branch 为 main 时不传 -b，使用远端默认分支；分发仓库默认分支也应一致。

加载器识别根 __init__.py、__full__.py、__nest__.py/同名目录，读取根 pyproject 的 project.dependencies 或 Poetry 依赖。不会读取 adapters/Dota2UID/pyproject.toml，也不会自动安装开发 workspace。商店安装后立即加载，因此只在进程启动阶段准备配置不足以覆盖首次热安装。

[依赖检查实现](https://github.com/Genshin-bots/gsuid_core/blob/87c06f11ae10c12b3bb8e76b3c6f420c831282a8/gsuid_core/server.py)受 AutoInstallDep/AutoUpdateDep 控制。仅自动安装开启时，已有包不检查新版本约束；project.gscore_auto_update_dep 可为指定依赖开启版本检查，但两个总开关均关闭时仍跳过。该字段属于 GsCore 扩展，不应直接塞进待发布的标准 wheel 元数据；需单独生成宿主分发清单。发现桥接更新不保证运行中的共享库已更新；显式停用、必要时停机安装/冷启动仍见[接入指南](../cookbook/dota2uid.md)。

2026-10-06执行固定上游函数的隔离复核：冷启动先flush_pending_installs再导入，商店reload_plugin没有执行依赖队列；新装缺三个项目库时当前guard拒绝。需处理或验证明确的冷启动流程，不能把依赖清单等同热安装成功。本机a1→a2历史升级已验证；后续a3公开CLI新装、a2→a3修复升级和SDK原生卸载已隔离通过，真实商店界面与QQ待验收，见执行记录；详见[复核证据](../../.agents/artifacts/gscore-store-readiness-v1/README.md)。

## AstrBot 收录与安装（2026-10-05）

[官方发布指南](https://docs.astrbot.app/dev/star/plugin-publish.html)现已明确：先将插件推送到 GitHub，再通过[AstrBot Cloud 发布页](https://cloud.astrbot.app/publish)提交，需要 Cloud 账号。指南要求 ZIP 不超过 16MB，超限需要维护者处理。本次未登录或提交表单，不能宣称已确认账号权限、审核结果或表单全部字段。

[开发指南](https://docs.astrbot.app/dev/star/plugin-new.html)要求插件元数据及第三方依赖清单；现有模板具备这些内容，但位于 src 下且 main.py 是模板。当前[市场规范](https://docs.astrbot.app/dev/plugin-market/2026-06-27.html)允许 GitHub 仓库 URL 或分支 URL，禁止子目录 URL；可用 HTTPS download_url 指定 ZIP，包内 author/name/version 必须匹配市场记录。直接登记 adapters 子目录链接不可行；download_url 是规范/源码支持，不等于 Cloud 表单已确认开放该字段。

本次远端 master 为 42972e9。[更新器](https://github.com/AstrBotDevs/AstrBot/blob/42972e932a64f01d96e2e0708579b0f79dd6f792/astrbot/core/star/updater.py)读取仓库根元数据、取得仓库或下载 ZIP；管理器从插件根目录发现 main.py 并读取 requirements.txt，不递归寻找 adapters。现有插件兼容声明仍为 >=4.28.2,<4.29；检查较新源码不扩大已验证的[宿主兼容范围](astrbot-host.md)。

现有 dist 中 Renderer wheel 为 13,725,493 bytes，字体源为 16,437,364 bytes；这些仅为已有文件大小，不是本次重建或最终商店 ZIP 验收。桥接很小不代表完整运行产物很小；若选择携带源码/资源，须实际压缩测量。Pillow/HTTPX 可用依赖清单取得，不应直接塞入跨平台 ZIP。

[本地插图契约](renderer.md)将官方英雄/装备/段位图与生成背景放在外部素材目录，不随 MIT wheel 分发；商店安装应能在未配置素材时用占位出图。商店包不能未经评估就包含本机下载资源和调研输出。

## 验证边界

首次核查仅只读调研；后续授权执行已创建GsCore分发仓库、Releases运行包及索引PR #40并完成隔离SDK验收。未发布PyPI、提交AstrBot Cloud申请、操作生产宿主或发送真实消息。推荐方案与实施顺序见[补充决策](../../.agents/notes/proposed/2026-10-05-plugin-store-readiness.md)；统一离线检查及未验证项见[核查任务](../../.agents/tasks/done/2026-10-05-plugin-store-verification.md)。

## 0.1.0a4双端更新

生成器新增--astrbot-wheels，AstrBot可附固定版本/SHA256清单、共用显式安装器及INSTALL.md；只允许该插件仓库和三个匹配运行包，拒绝两端adapter互换。两个宿主都先停机安装组件再冷启动，依赖保留有版本约束，导入不联网。AstrBot首次公开渠道为GitHub Releases，Cloud已提交a4，等待安全检查，尚未获准上架；[安装指南](../cookbook/astrbot-public-install.md)、[发行任务](../../.agents/tasks/done/2026-10-06-a4-layout-release.md)。

AstrBot分发README为兼容Cloud渲染，图片使用本仓raw.githubusercontent.com/main完整地址，INSTALL.md/LICENSE使用GitHub完整地址；图片仍随ZIP提供。GsCore继续相对路径。Cloud不会将相对资源自动解析到GitHub，修复见[任务](../../.agents/tasks/active/2026-10-06-cloud-readme-images.md)。
