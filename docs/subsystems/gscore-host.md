# GsCore 本机接入基线

2026-09-30 核实 Windows 原生实例，安装 Dota2UID 并完成真实热加载、受控重载、卸载/重启清理和恢复后冷启动。最终插件 ready，用户已确认 QQ 单会话收发成功，未推广为多账号或全平台保证；证据见 [接入任务](../../.agents/tasks/done/2026-09-30-dota2uid-first-loop.md)。

## 环境证据

- 控制台 `http://localhost:8765/app/` 返回 HTTP 200、HTML，标题为“网页控制台”。仅证明入口可达，未验证管理员登录或聊天平台连接。
- 宿主工作目录为 `D:\bot\gsuid_core`，运行进程使用 CPython 3.13.2。宿主虚拟环境的发行包元数据与 pyproject.toml 均为 gsuid-core 0.11.0。
- 宿主源码 HEAD 为 `87c06f11ae10c12b3bb8e76b3c6f420c831282a8`；本次核实的模型、加载器、生命周期和 UID 源文件无工作区修改。此记录不宣称该提交是远端最新版本。
- `/openapi.json` 未开放；源码 app_life.py 将 OpenAPI 置于 GSUID_ENABLE_OPENAPI 开关后，默认关闭。无需为插件接入开启它。

下述宿主源码路径相对于该 checkout，不是本仓库源码。初次基线核查未导入宿主应用入口、访问真实绑定表、重启或发消息；本轮安装仅复用用户已配置的 STRATZ 凭据，不修改宿主核心。2026-10-01 又安装了 Core、Renderer、Dota2UID 和 Pillow cp313 wheel，更新 reply_mode=image 与发现桥接并冷启动；宿主独立导入 Renderer/OFL 资源并生成780px菜单图通过。WebConsole管理员会话已过期、接口401，因此未宣称新命令注册或消息发送通过。

## 插件加载边界

`gsuid_core/server.py` 的 GsServer.load_plugins 扫描 gsuid_core/plugins 与 buildin_plugins。load_plugin 识别目录根部的 __init__.py、__full__.py，或 __nest__.py/同名嵌套目录；发现阶段检查插件 pyproject，随后集中处理依赖再导入模块。

本仓库 [Dota2UID](../../adapters/Dota2UID/) 保留 src 库包布局，显式安装器将分发模板放入 plugins/Dota2UID/__init__.py，SV 在该桥接中构造以满足调用栈归属。仅安装 wheel 不注册命令，宿主须再加载发现入口。详见 [安装步骤](../cookbook/dota2uid.md)。

## 身份与 UID

`gsuid_core/models.py` 的 Event 包含 bot_id、bot_self_id、user_id、real_bot_id、WS_BOT_ID、user_pm 和 at。handler.msg_process 将 MessageReceive.bot_id 的冒号后缀移除后作为 Event.bot_id，并在 real_bot_id 保留原值；WS_BOT_ID 由已连接宿主对象赋值。bot_self_id 才是机器人账号维度，bot_id 不是可直接替代它的字段。

`gsuid_core/utils/database/base_models.py` 的 BaseModel.select_data 按 user_id 与 bot_id 查询。Bind.get_uid_list_by_game 通过游戏列获取下划线分隔的多个 UID，get_uid_by_game 返回首个 UID，insert_uid 有追加/去重语义。

这与 [Core 绑定契约](core.md) 的四维隔离、每身份单账号及显式改绑不同。Dota2UID 将受控平台映射、bot_self_id、user_id 与部署 namespace 转成 Core 身份，要求 WS_BOT_ID 且拒绝代办 @。使用专用 Core SQLite，不同步或双写宿主 Bind 表，不能把两种存储描述为等价。

## 生命周期

已核查宿主自带 gscore-plugin-development 开发指南的生命周期章节，并对照源码：

- app_life.lifespan 等待 core_start_before_execute 后才继续启动；core_start_execute 由 create_task 在后台执行。因此普通 on_core_start 不是命令可用前已完成的保证。
- server.core_start_before_execute 捕获并记录异常，宿主可能继续启动；仅注册初始化钩子不构成业务就绪保证。
- on_core_shutdown 在进程退出阶段执行；这是进程生命周期接口，不能据此推断所有插件热更新资源都已正确释放。
- utils/plugins_update/reload_plugin.py 的 _run_plugin_start_hooks 只为目标插件后台重跑 on_core_start，不跑 on_core_start_before。首次热安装与重载必须单独验收。

原生 reload 会删除旧 shutdown 钩子但不执行，uninstall_plugin 只删目录和帮助缓存。Dota2UID 注册 start_before/start/shutdown，首命令进行幂等就绪检查；显式 stop 关闭客户端后再重载/卸载。实机观察卸载后路由/命令仍存在但已 stopped，重启后状态路由 404、无命令；恢复入口并再次重启后 ready、8 个命令各注册一次。匿名 GET 状态和 POST 停用均 401，配置/SQLite 指纹不变。直接原生删目录的资源释放仍不受保证，不能省略受控停用。

## 本仓库兼容检查

在独立于宿主的 CPython 3.13.2 环境运行本仓库统一离线入口：251 项测试通过，Core 语句与分支综合覆盖率 100%，Ruff、mypy、治理与独立覆盖率门槛通过；未安装宿主 SDK。首次检查发现测试夹具的 SQLite 连接未显式关闭，修正后以 ResourceWarning 为错误复核，无告警。Python 3.12.9 的 27 项仓库测试也通过。这些结果证明离线 Core 的解释器兼容性，不代表 GsCore 命令已接通。
