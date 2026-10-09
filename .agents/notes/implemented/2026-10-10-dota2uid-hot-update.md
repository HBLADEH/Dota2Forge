# Dota2UID bundled 的受控热切换与取消排空

Category: architecture
Related task: [实施任务](../../tasks/done/2026-10-10-dota2uid-hot-update.md)
Related code: [管理入口](../../../adapters/Dota2UID/src/Dota2UID/bundled_host_entry.py.template)、[后端](../../../scripts/gscore_bundled_runtime.py)、[Runtime](../../../adapters/Dota2UID/src/Dota2UID/runtime.py)
Related docs: [契约](../../../docs/subsystems/gscore-bundled-runtime.md)、[操作](../../../docs/cookbook/gscore-bundled-install.md)、[Core](../../../docs/subsystems/core.md)

## Problem
用户授权执行[调研提案](../proposed/2026-10-09-dota2uid-hot-update.md)。原生重载不执行旧 shutdown，只清桥接而保留共享模块；旧 a6–a9 的 owner 及 Runtime 没有可靠排空协议。[旧决策](2026-10-08-dota2uid-bundled-bootstrap.md)的冷启动规则仍适用于这些发行及薄分发。

## Decision
本地 Dota2UID a10/Core a7 实现 protocol=1，未公开发布。生成器在 deployment.json 记录业务桥接摘要与存储/报告兼容标识；入口同步冻结清单、桥接源码和纯值配置，异步准备使用固定版本/SHA256。四包继续来自标准 wheel，HTTPX/Pillow/SDK 不参与替换。Core a7 将绑定/订阅 SQLite 线程包在拥有任务中：取消等待线程退出后再传播，已开始事务仍可能提交；Dota2UID 首启本地配置 I/O 使用同一边界。

进程外于插件命名空间的 registry 持有旧 owner 和异步串行锁。新 owner 在 start hook 准备候选；支持快速重载跳过未启动的中间 owner。旧业务完成关闭后再 detach 四项目包及子模块；其他路径/加载器继续原样使用。Runtime 关闭等待排队查询、发送取消清理、订阅、素材与绘图线程；超过30秒不清理项目模块，旧 close_task 仍由 owner 保有，管理入口要求冷启动。

后端检查唯一 owner 租约、全部模块来源、可见的其他模块/类型/函数消费者，以及 wheel 内绑定schema1/订阅schema3与兼容标识。仅支持由 Dota2UID 独占项目包的宿主；任意外部闭包/容器引用无法全面枚举，不能宣称全进程依赖隔离。未知消费者、旧协议或不同数据契约拒绝热切换。

新业务导入时先禁止 handler 接入，Runtime 就绪为ready/awaiting_config后才开启命令和唯一调度。旧列表选择失效，绑定/订阅持久状态恢复。current.json 仍是准备指针；active.json 在成功启用后另写版本与代际，状态区分期望/准备/活跃版本及切换阶段。聊天安装只准备，之后由用户原生重载启用；AutoReloadPlugins控制商店更新是否自动调度该过程。

准备/兼容预检失败保留旧业务，并恢复被宿主移除的SV/调度。候选初始化失败先完整关闭；若数据库schema与文件摘要不变，恢复旧模块和冻结桥接、重建旧Runtime。数据库改写、回退或候选关闭失败保留诊断、要求冷启动，不盲回写用户数据库。取消和不确定递送不自动重发。

## Alternatives considered
移除guard或部分importlib.reload不能排空旧引用。代际私有命名空间要改绝对import和资源读取；worker进程需IPC、取消、投递确认与监督，暂不实施。调用宿主重启影响全部插件，不满足常规更新只重载Dota2UID的目标。

## Consequences
旧a6–a9升级到a10需一次冷启动，之后兼容的bundled代际可重载；薄分发、第三方/Python/SDK升级、schema变化及未知所有权仍停机维护。Core取消会多等待已经开始的存储操作，是双端共同消费的取消语义变更，已同步依赖下限和文档。停止/卸载仍显式停用。后端/生成器属于scripts，提交后仍需维护者评审，未改治理门禁。

## Verification
已通过取消排空、存储线程重复取消、来源/共享拒绝、冻结输入、数据改写拒绝、失败恢复、超时与快速重载专项；五包构建、独立wheel及双端SDK-free分发smoke通过。真实fb80b874 SDK源码隔离副本验证活跃配置重载、不同版本/代码的合成Core a8 wheel原生升级、四包来源、新类型、唯一配置/hook/调度与三文件摘要保留、损坏更新恢复和关闭；证据见[验收目录](../../artifacts/dota2uid-hot-update-v1/README.md)。SDK解释器为既有Python3.13.2/元数据0.11.0/Pillow11.3，不能描述为生产0.11.1/Pillow12.3同构环境。最终统一检查记录于任务。Linux/Docker、真实商店Git/UI、QQ递送和生产部署未验收，未发布或改宿主。
