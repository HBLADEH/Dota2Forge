# Dota2UID 随包运行库与聊天恢复入口

Category: architecture
Related task: [实施任务](../../tasks/done/2026-10-08-dota2uid-bundled-bootstrap.md)
Related code: [后端](../../../scripts/gscore_bundled_runtime.py)、[管理桥接](../../../adapters/Dota2UID/src/Dota2UID/bundled_host_entry.py.template)、[生成器](../../../scripts/build_plugin_distributions.py)
Related docs: [契约](../../../docs/subsystems/gscore-bundled-runtime.md)、[操作指南](../../../docs/cookbook/gscore-bundled-install.md)

## Problem
URL 热安装未取得项目依赖，旧 guard 在 SV 注册前失败，导致帮助和修复命令都不可用。用户要求提供恢复指令且尽量不修改 GsCore；[已批准设计](../proposed/2026-10-08-dota2uid-bundled-bootstrap.md)选择随包标准 wheel 和独立管理入口。

## Decision
Dota2UID a6 为未发布源码候选，生成器显式 `--gscore-bundled` 携带四个匹配项目 wheel，保留薄模式/AstrBot。宿主根清单只声明共享 HTTPX/Pillow；deployment.json 固定运行清单摘要，业务只从 canonical wheel 加载。

标准库后端校验认证字节、元数据/标签/依赖、RECORD 与许可、路径/碰撞/解压限额，拒绝 SDK、原生库、游戏图、配置与数据库。默认启动不联网；主人 `do安装核心` 缺失/损坏时才使用清单固定 Release URL，拒绝额外参数并复核权限。准备使用线程、OS 文件锁和插件拥有的任务，关闭或取消等待实际任务与子进程退出。

运行库位于 data/Dota2UID/runtime 的不可变代际；先验证文件、宿主第三方和离线子进程导入/字体渲染，再原子发布指针。失败只清理本次暂存，保留旧目录和用户数据。项目包加载使用私有路径，拒绝来源不符的既有模块，运行中的恢复只准备目录，冷启动才激活。

管理入口先注册 SV；bootstrap 统一拥有 start_before/start/shutdown，业务延迟导入，失败/取消回滚本次业务注册并关闭资源。活跃热重载保留旧 owner 并要求重启；完成显式停用后，仅同代际的配置重载可重新启用。管理与业务配置状态分开，不把准备成功写成 ready。

实际 SDK 导入会生成 pyc，使原完整性检查认为目录被改变并新建代际，造成停用重载模块来源冲突。私有 FileFinder/SourceFileLoader 只编译源码、忽略 pyc 并禁写缓存；不修改全局 bytecode 开关，宿主其他模块照常缓存。已加载第三方版本按规范化数字段比较，允许 certifi 的日历版本补零，不误判兼容环境。

## Alternatives considered
聊天 handler 包装全局 pip 仍有 Pillow DLL、宿主共享依赖和已加载模块问题。仅命令下载增加首次网络依赖。私有 venv worker 引入跨进程协议，超出 M0。随包方案代价是较大仓库，但可直接取得匹配组件；保留旧 CLI 用于旧发行与第三方维护。

## Consequences
无需修改 GsCore 源码或全局项目包，不提供热切换与自动宿主重启。HTTPX/Pillow 不兼容仍需停机维护；私有目录与宿主同进程，不能描述为完整依赖隔离。字体及 OFL 随 wheel 保留，游戏素材仍由独立 Assets 机制准备；尚未发布的候选不能下载不存在的 Release 资产。

## Verification
针对性后端、桥接和生成器离线测试已通过，覆盖认证字节、ZIP 异常、并发/跨进程锁、中断、取消回收、权限、部分注册回滚、旧模块来源与第三方冲突。五包构建、五个独立 wheel 安装以及 SDK-free 双端分发 smoke 已通过；GsCore 干净环境仅安装第三方库，四项目组件均从私有目录加载。

统一离线入口1740 passed，Ruff/mypy及三独立覆盖率门槛通过；Windows实际SDK源码隔离副本验证管理指令、原生重载、冷启动、关闭与卸载，配置/绑定保留。证据区分既有SDK解释器和SDK-free干净安装，代际变化是同wheel清单模拟。[实施记录](../../tasks/done/2026-10-08-dota2uid-bundled-bootstrap.md)与[证据目录](../../artifacts/dota2uid-bundled-bootstrap-v1/README.md)列出尺寸和边界。真实QQ/平台递送、URL商店流程、Release恢复下载与Linux/Docker联调尚未验证；本次未发布或部署。
