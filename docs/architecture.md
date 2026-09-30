# Dota2Forge 当前架构

仓库采用 Python 3.12+ 与 uv workspace。三个独立版本包均使用 src 布局和 Hatchling 构建，包元数据是名称、版本和依赖的事实源。

```text
astrbot_plugin_dota2forge ──┐
                          ├──依赖──> dota2forge_core
Dota2UID ──────────────────┘
```

Core 已包含严格身份值、绑定/查询用例、异步 Provider/Repository 端口、文件型 SQLite 仓库和 STRATZ 玩家/最近比赛 Provider。基础安装无必选运行依赖，联网实现使用 stratz extra 中的 httpx。领域与用例不读取环境、执行 SQL 或访问 HTTP；SQLite、时钟与专用 HTTP 客户端由组合入口显式构造、注入和关闭。

STRATZ 主源已实现并独立只读联调概况及 100 场分页结果；受限于现有端口，只提供基础资料与近期战绩，不保证完整历史。错误不降级为空结果，额度耗尽停止发送，无自动重试或回退。按比赛 ID 的历史详情、共享图片 Renderer 和 MatchDetailCard 已列入后续任务，见 [接入任务](../.agents/tasks/done/2026-09-30-stratz-provider.md)、[图片任务](../.agents/tasks/active/2026-10-01-image-interaction.md)、[详情任务](../.agents/tasks/active/2026-10-01-historical-match-detail.md) 与 [实现决策](../.agents/notes/implemented/2026-09-30-stratz-provider.md)。OpenDota、Valve 按需补充仍待实现；Dota2UID 真实宿主生命周期已验证，QQ 单会话收发由用户实测确认。

Dota2UID 已有首个绑定/查询消费者：安全导入的 src 库包加显式安装到 plugins/Dota2UID 的宿主发现桥接。组合入口安装 stratz extra，管理专用 HTTP 客户端与 Core SQLite 仓库；可信 Event 转为四维身份后才调用 Core。插件注册普通命令及需管理员鉴权的状态/停用接口，不注册 AI 工具、不做推送。AstrBot 仍是骨架，两端互不依赖，平台事件不传入核心。

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
