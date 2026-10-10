# Dota2UID 商店更新后的受控代际切换可行性

Category: architecture
Related task: [调研任务](../../tasks/done/2026-10-09-dota2uid-hot-update-research.md)
Related code: [管理入口](../../../adapters/Dota2UID/src/Dota2UID/bundled_host_entry.py.template)、[运行库后端](../../../scripts/gscore_bundled_runtime.py)、[Runtime](../../../adapters/Dota2UID/src/Dota2UID/runtime.py)
Related docs: [当前契约](../../../docs/subsystems/gscore-bundled-runtime.md)、[安装指南](../../../docs/cookbook/gscore-bundled-install.md)

本提案已授权实施；具体范围、旧版首次升级和真实验收边界见[实施决策](../implemented/2026-10-10-dota2uid-hot-update.md)。下文保留调研时结论。

## Problem
用户反馈商店更新到最新版本后，仅重载插件不能使用新改动。本次只调研，不改变[现行冷启动决策](../implemented/2026-10-08-dota2uid-bundled-bootstrap.md)。当前公开 a9 随包 Core a6/Renderer a5/Assets a1；历史架构页版号不能替代包元数据与当次发行任务。

GsCore 的商店更新调用 update_plugins，执行 Git 更新；AutoReloadPlugins 开启且有更新时调用 reload_plugin。原生重载同步删除插件 SV、模块、定时注册、路由和生命周期 hook，但不执行旧 shutdown；只后台运行新 on_core_start，不等待业务就绪。宿主“更新/重载成功”不等于项目运行库已经切换。

模块匹配规则覆盖 Dota2UID 及 plugins.Dota2UID，却不覆盖 dota2forge_core、dota2forge_renderer、dota2forge_assets。随包清单任一 wheel 或 Release 标识变化会改变整体摘要，四组件重新位于另一代际，即使某组件字节不变。改变 sys.path 不会替换 sys.modules，也不会替换 handler、任务和对象里保存的旧类型。

管理入口故意将 owner 保存在宿主重载范围外：活跃重载复用旧 owner 并置 restart_required；显式停用完成后可新建 owner，但 activate 仍拒绝来源不在新代际的项目模块。两重保护分别防止资源泄漏与新旧运行库混用，不是下载失败。

## Decision
**可行，但需实施有边界的插件热切换；不能通过移除 module_conflict 保护获得安全热更新。** 推荐先为 bundled 的独占项目运行库实现受控切换，Core 保持平台无关，不修改 GsCore SDK。薄分发、共享第三方维护仍保留冷启动流程。本页为 proposed，未承诺所有升级无需重启。

目标体验：商店更新后点一次原生重载，管理入口通过新 start hook 完成异步切换；AutoReloadPlugins 开启时可由更新自动触发，关闭时仍需手动重载。切换期间短暂停止 Dota2UID 业务，其他插件继续运行。后台重载返回值只能表示已调度，插件状态才报告 ready/awaiting_config/failed。

拟实施步骤：
1. 新入口保留旧 owner 的关闭句柄，以进程级锁串行化重载/安装/停用；读取固定候选清单，准备并验证新代际，冻结同版本业务桥接与配置快照，避免后续 Git 更新混入文件。
2. 管理入口继续可诊断，业务入口先关闭接入；移除旧调度并等待启动、查询、全部排队/发送协程、订阅 tick、素材线程和绘图线程退出。当前 Runtime.close 有取消和资源关闭，但没有完整 dispatch 任务集合/排空证明，必须补齐，不以 client_closed 单项判断。
3. 仅允许由该 owner 管理、全部来自已验证旧代际的四项目模块切换。显式登记消费者和独占租约，发现其他 owner、未知来源或共享消费者则要求重启；扫描文件路径不能证明没有任意外部引用。
4. 保存旧模块/路径快照，仅清理上述四包及其子模块、旧私有路径/加载器缓存，重新导入整组新包。HTTPX、Pillow、SDK 和其他插件不参与清理；不可原地 reload 部分业务模块。
5. 通过新的 Runtime 创建全部类型/服务和业务注册，验证配置与本地资源后再开启命令和唯一调度。旧会话战绩列表失效，持久绑定/订阅继续按原契约恢复。记录期望、已准备、活跃的版本和摘要，不能只读磁盘元数据。
6. 候选准备失败保留旧业务；关闭/切换失败保留诊断与明确状态。旧 Runtime 已 stopped 不能复用；自动回退需冻结旧业务桥接、重建旧 Runtime，且数据库写入/schema兼容已有证明，否则保持 unavailable 并要求冷启动。准备指针与活跃代际分开提交，不能用 current.json 的准备成功代表激活成功。

## Alternatives considered
| 方案 | 可行性与代价 |
| --- | --- |
| 独占四包的受控同进程切换 | 最贴合现有实现；需生命周期排空、所有权、整组导入、失败恢复与真实 SDK 验收，推荐先做 |
| 私有代际命名空间 | 可同时保存两版，但各包绝对 import 与 importlib.resources 的固定包名须改造；简单别名仍指向全局缓存，改造面更大 |
| 独立 worker 进程 | 新进程天然隔离模块/原生依赖，只重启插件 worker；需配置、身份、结果/图片、取消、订阅投递确认的 IPC 协议及监督，适合后续更强隔离需求 |
| 一键调用宿主重启 | 可减少手工步骤，但影响全部插件并需验证 Docker/自定义启动方式；未达到只重载插件即可生效的目标 |
| 去掉 guard 或逐个 importlib.reload | 旧对象和任务仍存在、类型身份混用，不能作为安全方案 |

## Consequences
HTTPX/Pillow/Python/SDK升级、第三方不兼容、数据库不支持热迁移、外部共享模块、关闭超时、未知 owner 协议都需要明确冷启动。发送取消可能已递送，保留 UNCERTAIN，不自动重发。进程内切换不是零中断或完整依赖隔离；不能可靠约束消费者时应选 worker。

旧 a6-a9 未提供新交接协议，从旧版首次升级可能需一次冷启动；若要兼容直接升级，必须单独验收旧 owner 到新 owner 的交接，不能宣称新入口落盘就具备热切换。四包仍由 canonical wheel 生成，不能复制业务维护第二份实现。后端属于 scripts，正式实现需按规则维护者评审。

## Verification
只读核查本机 GsCore 87c06f1，并通过 GitHub API核对部署记录的 0.11.1/fb80b874：reload_plugin.py 与 _plugins.py 逐字节相同；server.py 整文件不同，已另读 fb 的发现/依赖检查逻辑，不宣称当前生产进程同构验收。

CPython3.12.9隔离子进程使用本地公开 a6/a7 四 wheel，临时数据目录，创建事件循环后阻断 socket/DNS，准备子进程也使用现有禁网 probe。复现 module_conflict；将新路径前置仍取得旧模块；完整移除59个项目模块后59个新模块均来自新代际，字体/菜单 PNG 两次各174035 bytes。保留的旧 AccountId 对象不属于新 AccountId 类型，证明模块移除不等于旧引用消失。未实例化活跃业务 Runtime，不读真实 Token/库、不导入 SDK、不发消息；该实验只证明导入机制，不是安全热更新验收。

另一禁网临时实验使用当前 Runtime、合成配置/SQLite与延迟取消清理的发送回调：close 返回 stopped/client_closed=true 时发送任务未完成，dispatch_count=1；释放回调后变0。证明热切换必须新增完整排空屏障，不将当前资源关闭标志等同所有旧栈退出；未连接宿主或聊天。

追加本地公开 a7→a9 wheel 实验同样复现冲突；移除旧59模块后新60模块均来自Core a6/Renderer a5/Assets a1/Dota2UID a9代际，字体/菜单PNG通过，未实例化活跃业务。2026-10-10最终统一离线检查1985项通过（498.27s），Ruff/mypy及三独立覆盖率门槛通过；开发环境旧元数据的首轮失败与同步过程保留在任务。

实施验收须覆盖真实两版运行库的原生更新/重载、活跃查询/发送/绘图/下载/订阅时切换、重复并发重载、关闭超时、部分注册/导入失败、数据保留与schema拒绝、旧版交接、共享包拒绝、回退与版本状态；两端发行回归及 Windows/Linux/Docker SDK 验证后，再单独验收真实聊天。
