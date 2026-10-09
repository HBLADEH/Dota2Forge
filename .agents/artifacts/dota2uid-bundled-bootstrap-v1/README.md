# Dota2UID a6 随包候选实施证据

本目录记录本地构建、禁网测试与隔离 GsCore SDK 验证；不含真实 Token、聊天记录或平台身份。候选未公开发布或部署。[任务](../../tasks/done/2026-10-08-dota2uid-bundled-bootstrap.md)、[决策](../../notes/implemented/2026-10-08-dota2uid-bundled-bootstrap.md)。

## 本地安装
五项目 wheel 由 `uv build --offline --all-packages` 构建，`smoke_wheels.py` 逐个在新 venv 中安装导入并验证 Renderer 字体/OFL资源。双端 `smoke_plugin_distributions.py` 使用清单对应本地 wheel，两个新环境均无 SDK。GsCore 只向环境安装 HTTPX/Pillow 及传递依赖，准备前四项目包均不存在；随后使用私有运行库完成配置等待、绑定、关闭和数据恢复。

## 实际 SDK 范围
固定 SDK checkout `87c06f11ae10c12b3bb8e76b3c6f420c831282a8` 的源码复制到临时目录，排除其部署 data 和 plugins。使用既有 SDK CPython 3.13.2 解释器，其全局历史项目包未修改；父进程激活后核对四项目模块均来自本次私有代际。因此这是实际 SDK 组件验证，不等同完全干净 SDK 宿主或生产验证。

调用真实 `load_plugin` / `cached_import`、SV、Event、Trigger、权限检查、Bot、生命周期、原生 reload、FastAPI 与原生卸载；平台输出仅为内存 WebSocket frame 收集。禁用外部 socket，没有真实用户、QQ连接、STRATZ 请求或消息发送。SDK 原源码摘要在验证前后核对。

五阶段 JSON：[首次启动](windows-sdk-initial.json)、[新进程重启](windows-sdk-cold.json)、[停用后卸载](windows-sdk-uninstall.json)、[代际变化](windows-sdk-upgrade.json)、[新代际冷启动](windows-sdk-upgraded-cold.json)。管理权限/参数拒绝、Token 等待、停用配置重载、活跃重载保留 owner、幂等恢复、匿名 API 拒绝、关闭客户端、卸载和重启数据保留均通过。代际变化使用相同固定 wheel，仅改变清单字节，验证新的目录不能在旧模块进程中热启用；不是真实发行升级或旧 schema 回退验收。

实际 SDK 复核还发现并修复了正常导入生成 pyc 破坏不可变目录、certifi 日历版本补零被误判的问题；对应真实进程回归纳入禁网测试。私有加载器禁止缓存，宿主其他模块仍正常写缓存。

## 未验证项
真实商店 URL 下载、GitHub Release 恢复下载与真实 QQ/客户端递送未验证。下载边界由离线注入测试覆盖，尚无本候选公开 Release。Linux/Docker 验证未执行：本机 Docker daemon 不可用。共享 DLL 更新不在聊天恢复路径；第三方冲突只诊断并要求停机维护。

统一入口1740 passed / 245.13s，Ruff格式与lint通过（346文件），mypy通过（83文件）；总覆盖92.95%，scripts94%、Core93%、Assets92%，未修改本轮治理门禁。随后发行文案修正另跑生成器/public回归81项与Ruff/mypy，通过后重新生成最终候选。完整尺寸、版本与ZIP摘要见[机器记录](validation.json)；不以桩测试替代真实平台联调。
