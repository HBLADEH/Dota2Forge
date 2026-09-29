# Dota2Forge 当前架构

仓库采用 Python 3.12+ 与 uv workspace。三个独立版本包均使用 src 布局和 Hatchling 构建，包元数据是名称、版本和依赖的事实源。

```text
astrbot_plugin_dota2forge ──┐
                          ├──依赖──> dota2forge_core
Dota2UID ──────────────────┘
```

当前三个包仅包含可安全导入的骨架。Core 无运行依赖；适配器仅依赖 Core，尚未安装宿主 SDK、注册命令、启动后台任务或实现业务用例。两端互不依赖。平台事件不能传入核心，领域与用例经由端口使用基础设施。

治理配置与检查器覆盖实际 workspace 包配置、Python 静态及常量动态导入、依赖声明、文档长度、链接、决策记录和包参考漂移。检查器使用配置指定的显式包路径，导入名由各包 Hatchling 配置解析。

测试禁用网络；独立构建和干净环境导入用于验证产物边界。包的可构建性不代表插件能被宿主加载。

- [包参考](generated/packages.md)
- [治理契约](subsystems/governance.md)
- [开发操作](cookbook/development.md)
- [初始工程决策](../.agents/notes/implemented/2026-09-30-workspace-foundation.md)
- [业务阶段任务](../.agents/tasks/active/2026-09-30-core-mvp.md)
