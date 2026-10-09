# Dota2Forge 当前架构

仓库采用 Python 3.12+ 与 uv workspace。五个独立版本包均使用 src 布局和 Hatchling 构建，包元数据是名称、版本和依赖的事实源。

当前源码版本为Core a7、Renderer a5、Assets a1、AstrBot a9、Dota2UID a10。公开Dota2UID a9已有宽幅比赛报告；a10受控热切换仍是本地候选，见[实施任务](../.agents/tasks/done/2026-10-10-dota2uid-hot-update.md)。AstrBot现行公开a7的依赖修复及手动素材部署见[修复任务](../.agents/tasks/done/2026-10-07-astrbot-store-dependency-fix.md)。[发行生成器](../scripts/build_plugin_distributions.py)从同一源码生成双端根桥接、四组件锁定依赖及校验清单；Dota2UID可选bundled模式携带标准wheel，不另行维护业务副本。入口检查Python/组件版本；合法空Token等待业务配置，仍可按设置准备公共素材。

GsCore bundled管理入口仅依赖标准库/已有SDK，核心缺失仍能响应主人安装、状态与文字帮助；项目wheel在独立数据目录准备不可变代际，通过完整校验及离线资源检查才发布。公开a6–a9更新仍冷启动；本地a10以owner协议、独占租约、来源与数据兼容检查及完整任务排空实施整组热切换，准备/运行指针分开，失败保留或重建旧业务。Core SQLite取消等待已开始线程退出；宿主HTTPX/Pillow不被自动替换。薄分发及AstrBot路径继续保留，见[随包契约](subsystems/gscore-bundled-runtime.md)。

```text
AstrBot / Dota2UID ──> Core（业务与端口）
                  ├─> Renderer ──> Core
                  └─> Assets（公共素材 HTTP 与文件，无其他项目包依赖）
```

Assets 是独立素材基础设施，两个适配器持有生命周期、代理和权限，不进入 Core 业务，也不让 Renderer 联网。默认首次图片模式后台准备；自定义路径优先、完整快照无网络、按文件补缺与独立部分失败。OS 租约和不可变 generation/current.json 保证单写与完整恢复；两端整组绘图/发送锁内换 Renderer，关闭等待请求和线程。见[素材契约](subsystems/assets.md)。

Core 已包含严格身份/比赛 ID 值、绑定/查询用例、独立 MatchDetailService、异步 Provider/Repository 端口、文件型 SQLite 仓库，以及STRATZ/OpenDota玩家/最近比赛/按ID详情Provider。基础安装无必选运行依赖，联网实现分别使用stratz/opendota extra中的httpx。领域与用例不读取环境、执行 SQL 或访问 HTTP；SQLite、缓存、时钟与专用 HTTP 客户端由组合入口显式构造、注入和关闭。

STRATZ 主源已实现并独立只读联调概况、100 场分页及按比赛 ID 的最小详情；后者不受 recent 范围限制，不保证历史覆盖。详情字段缺口、匿名身份和正常 null 详情分别保留；错误不降级为空结果，额度耗尽停止发送，无自动重试或回退。Dota2UID已有直接ID、已发送列表序号/取页和图片/文本模式；共享Renderer和详情卡已实现。GsCore冷启动/受控stop/reload与QQ单会话图片可读性已验证，[证据](../.agents/artifacts/gscore-image-lifecycle-v1/README.md)。见[图片任务](../.agents/tasks/active/2026-10-01-image-interaction.md)、[详情任务](../.agents/tasks/active/2026-10-01-historical-match-detail.md)、[Renderer契约](subsystems/renderer.md)。OpenDota独立补充与CrossCheckService、Core的显式缓存/刷新/有限重试装饰器已实现并禁网验证，两份观察及差异分别保留，不换源/拼接；明确PRIVATE不继续补充请求，[来源契约](subsystems/opendota.md)与[缓存契约](subsystems/cache-retry.md)。新装饰器未部署到Bot或查询真实账号；Valve仍按需规划。

Dota2UID 已有首个绑定/查询消费者：安全导入的 src 库包加显式安装到 plugins/Dota2UID 的宿主发现桥接。组合入口安装 stratz extra，管理专用 HTTP 客户端与 Core SQLite 仓库；可信 Event 转为四维身份后才调用 Core。插件注册普通命令及需管理员鉴权的状态/停用接口，不注册 AI 工具、不做推送。AstrBot 适配器已有无宿主 SDK 的 AstrApplication，并提供按 AstrBot 4.28.2 验证的发现桥接模板、配置 Schema、可信身份转换、图片消息转换和可重复关闭的 Runtime；消费同一 Core/Renderer。AstrBot本机发现、配置加载、冷启动、重载与关闭恢复已验证，用户确认OneBot单会话菜单/绑定/玩家/战绩分页/序号详情图片正常且可读；剩余实机边界见[AstrBot证据](../.agents/artifacts/astrbot-host-v1/README.md)。库顶层按需导出，避免宿主递归重载依赖时捕获旧Core/Renderer类型。两端互不依赖，平台事件不传入核心。

已发送的最后战绩以128份/10分钟有界进程内状态保存，按部署/平台/机器人/用户/连接/群或私聊隔离；改绑/解绑/停用/重载失效。完整发送后才提交，失败不重发；页码不再查Provider，序号使用已保存ID。此状态属于适配器交互，不是来源数据缓存；见 [选择决策](../.agents/notes/implemented/2026-10-01-delivered-list-selection.md)。

GsCore原生热重载/卸载不保证执行旧关闭钩子；公开版先停用，a10由跨重载owner主动等待旧关闭，旧版首次升级仍冷启动。卸载仍显式停用，不能把删除目录等同资源释放。a10实际SDK隔离验收与Linux/Docker/QQ未验证边界见[证据](../.agents/artifacts/dota2uid-hot-update-v1/README.md)；历史接入见[宿主任务](../.agents/tasks/done/2026-09-30-dota2uid-first-loop.md)。平台身份、权限、消息、配置和生命周期归适配器，账号规则保留在Core。

Core订阅提供玩家新比赛、指定比赛完成报告、段位变化及北京时间每日有限观察战报；独立SQLite检查点/outbox/schema v3发送尝试，原子占用后投递，成功确认，不确定或取消不盲发。Core没有Scheduler或消息I/O；双端Runtime/桥接显式拥有计时器，默认关闭，群订阅要求当前Bot管理员。改绑/解绑先取消该身份旧订阅。AstrBot主动推送仅支持OneBot v11反向WebSocket；两端不跨库去重。详情/经济/购买分析和非官方MVP候选保留来源边界。日期、有限窗口、权限、重试和stop/reload边界见[订阅契约](subsystems/subscriptions.md)，实机进度见[Step13任务](../.agents/tasks/active/2026-10-02-subscriptions.md)。

治理配置与检查器覆盖实际 workspace 包配置、Python 静态及常量动态导入、依赖声明、文档长度、链接、决策记录和包参考漂移。检查器使用配置指定的显式包路径，导入名由各包 Hatchling 配置解析。

测试禁用网络；Core、治理工具与 Assets 分别执行 80% 覆盖率门槛。独立构建和干净环境导入用于验证产物边界，包的可构建性不代表插件能被宿主加载。SQLite 每次操作关闭连接，异步用例不启动常驻任务；具体错误、幂等和取消语义见 Core 契约。

- [包参考](generated/packages.md)
- [治理契约](subsystems/governance.md)
- [Core 契约](subsystems/core.md)
- [GsCore 本机接入基线](subsystems/gscore-host.md)
- [Core 离线回放](cookbook/core-offline.md)
- [开发操作](cookbook/development.md)
- [初始工程决策](../.agents/notes/implemented/2026-09-30-workspace-foundation.md)
- [业务阶段任务](../.agents/tasks/done/2026-09-30-core-mvp.md)
