# Dota2Forge 当前架构

仓库采用 Python 3.12+ 与 uv workspace。四个独立版本包均使用 src 布局和 Hatchling 构建，包元数据是名称、版本和依赖的事实源。

```text
astrbot_plugin_dota2forge ──┐
                          ├──依赖──> dota2forge_core
Dota2UID ────────┐
                 ├──依赖──> dota2forge_renderer ──> dota2forge_core
                 └────────> dota2forge_core
```

Core 已包含严格身份/比赛 ID 值、绑定/查询用例、独立 MatchDetailService、异步 Provider/Repository 端口、文件型 SQLite 仓库和 STRATZ 玩家/最近比赛/按 ID 详情 Provider。基础安装无必选运行依赖，联网实现使用 stratz extra 中的 httpx。领域与用例不读取环境、执行 SQL 或访问 HTTP；SQLite、时钟与专用 HTTP 客户端由组合入口显式构造、注入和关闭。

STRATZ 主源已实现并独立只读联调概况、100 场分页及按比赛 ID 的最小详情；后者不受 recent 范围限制，不保证历史覆盖。详情字段缺口、匿名身份和正常 null 详情分别保留；错误不降级为空结果，额度耗尽停止发送，无自动重试或回退。Dota2UID 已有直接ID、已发送列表序号/取页和图片/文本模式，图片代码/离线回退已验证，当前GsCore/QQ图片联调未验证；共享Renderer和MatchDetailCard已实现。见[图片任务](../.agents/tasks/active/2026-10-01-image-interaction.md)、[详情任务](../.agents/tasks/active/2026-10-01-historical-match-detail.md)、[Renderer契约](subsystems/renderer.md)。OpenDota、Valve按需补充仍待实现。

Dota2UID 已有首个绑定/查询消费者：安全导入的 src 库包加显式安装到 plugins/Dota2UID 的宿主发现桥接。组合入口安装 stratz extra，管理专用 HTTP 客户端与 Core SQLite 仓库；可信 Event 转为四维身份后才调用 Core。插件注册普通命令及需管理员鉴权的状态/停用接口，不注册 AI 工具、不做推送。AstrBot 适配器已有无宿主 SDK 的 AstrApplication，消费同一 Core/Renderer；AstrBot 平台事件、配置、生命周期和真实消息发送仍未验证，两端互不依赖，平台事件不传入核心。

已发送的最后战绩以128份/10分钟有界进程内状态保存，按部署/平台/机器人/用户/连接/群或私聊隔离；改绑/解绑/停用/重载失效。完整发送后才提交，失败不重发；页码不再查Provider，序号使用已保存ID。此状态属于适配器交互，不是来源数据缓存；见 [选择决策](../.agents/notes/implemented/2026-10-01-delivered-list-selection.md)。

GsCore 本机版本的原生热重载/卸载不保证执行旧关闭钩子；Dota2UID 使用显式停用后再操作宿主的受控流程，不能把删除目录等同资源释放。实际安装和验证状态见 [宿主任务](../.agents/tasks/done/2026-09-30-dota2uid-first-loop.md)，操作见 [接入步骤](cookbook/dota2uid.md)。平台身份、权限、消息、配置和生命周期归适配器，账号规则保留在 Core。

治理配置与检查器覆盖实际 workspace 包配置、Python 静态及常量动态导入、依赖声明、文档长度、链接、决策记录和包参考漂移。检查器使用配置指定的显式包路径，导入名由各包 Hatchling 配置解析。

测试禁用网络；Core 与治理工具分别执行 80% 覆盖率门槛。独立构建和干净环境导入用于验证产物边界，包的可构建性不代表插件能被宿主加载。SQLite 每次操作关闭连接，异步用例不启动常驻任务；具体错误、幂等和取消语义见 Core 契约。

- [包参考](generated/packages.md)
- [治理契约](subsystems/governance.md)
- [Core 契约](subsystems/core.md)
- [GsCore 本机接入基线](subsystems/gscore-host.md)
- [Core 离线回放](cookbook/core-offline.md)
- [开发操作](cookbook/development.md)
- [初始工程决策](../.agents/notes/implemented/2026-09-30-workspace-foundation.md)
- [业务阶段任务](../.agents/tasks/done/2026-09-30-core-mvp.md)
