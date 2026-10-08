# Dota2UID 随包运行库与无核心依赖的管理入口

Category: architecture
Related task: [聊天安装设计](../../tasks/done/2026-10-08-dota2uid-bootstrap-design.md)
Related code: [发行生成器](../../../scripts/build_plugin_distributions.py)、[入口模板](../../../adapters/Dota2UID/src/Dota2UID/host_entry.py.template)、[版本检查](../../../scripts/plugin_bootstrap.py)
Related docs: [现行分发契约](../../../docs/subsystems/plugin-distribution.md)、[公开安装](../../../docs/cookbook/gscore-public-install.md)

用户已授权实施，本页保留设计阶段记录；实际方案与验收边界见[实施决策](../implemented/2026-10-08-dota2uid-bundled-bootstrap.md)。

## Problem
用户使用正确分发 URL，但热加载未安装项目运行库，do帮助无响应。当前入口先执行版本guard，随后才注册SV；缺包会使安装/诊断指令同样不可用。用户希望一条指令拉取或部署核心，并要求尽量不改GsCore。

现行CLI写宿主site-packages，要求宿主退出；[已验证故障](../implemented/2026-10-02-gscore-wheel-recovery.md)包括Pillow DLL占用与旧Core导入缓存。直接把CLI包在聊天handler里不能解决这些问题。本提案保留[既有冷启动决策](../implemented/2026-10-06-gscore-public-release.md)，不改变当前公开a4安装契约。

## Decision
推荐Dota2UID分发仓库携带匹配的本项目wheel，并提供只依赖标准库与已有GsCore SDK的管理入口；默认URL安装取得运行库，聊天安装指令作为恢复入口。仅修改本项目生成器、桥接和安装模块，使用宿主原有发现、权限、事件、消息与生命周期接口。

### 分发与加载
1. 从主仓构建的标准wheel生成分发，业务仍维护于共享包；不建立第二套业务源码。公开a4是Core/Renderer/Dota2UID三个组件；候选a5新增Assets，必须使用其对应四组件组合，不能把未发布Assets当作现有a4资产。
2. bundled模式根pyproject不再向GsCore声明本项目包及其gscore_auto_update_dep，避免import前仍向PyPI安装。HTTPX/Pillow的第三方约束单独保留并明确受宿主开关控制；组件版本/hash留在独立清单。
3. 根入口先注册管理SV；所有Core/Renderer/Assets/业务适配器导入延后。启动hook在后台线程校验随包wheel，准备data/Dota2UID/runtime/<清单摘要>/不可变目录；不在import中联网或安装，不在宿主环境执行pip。
4. wheel只接受固定项目白名单、匹配Name/Version/Python要求、py3-none-any与SHA256；限制ZIP路径、符号链接、解压体积和文件碰撞，保留资源、dist-info及许可证。禁止携带SDK、Pillow二进制、Valve图像、实际配置和数据库。
5. 新目录完整校验及子进程离线导入/Renderer资源验证后才原子发布。宿主HTTPX/Pillow及相关依赖必须兼容；第三方库不兼容时保持管理入口可用，返回维护步骤，不自动升级宿主库。
6. 项目包通过受控私有路径加载，核对包元数据与已加载模块来源；这是同进程寻址，不是完整依赖隔离。检测到旧版本、未知来源或不同代际的项目模块时拒绝业务加载，不清空sys.modules强行切换。业务导入失败保留管理入口和明确失败状态，清理本次部分业务注册，不把bootstrap一起卸载。
7. bootstrap统一拥有start/start_before/shutdown与业务注册，避免在执行hook列表时追加动态hook；重复启动不重复注册。首次干净进程可加载完整随包运行库；运行中的安装/修复只准备新目录，激活需冷启动。原生热重载仍要求显式停用。

### 命令与状态
- `do安装核心`：管理SV为pm=0，handler再次校验type(user_pm)为int且等于0，无URL、版本或pip参数。优先使用随包wheel；缺失/损坏时才从清单固定Release URL取回并校验。同清单完整目录直接复用；完成后返回已准备、需要冷启动，不声称业务ready。
- `do核心状态`：管理指令，区分未准备、准备中、失败、待重启、第三方不兼容、运行库可用；业务awaiting_config单独显示。回复不含Token、完整身份或宿主路径。
- 缺核心时普通`do帮助`/`do菜单`仍可返回纯文字安装提示；运行库可用后沿用现有帮助与配置语义，不依赖Token才能安装。
- 单宿主文件锁及单任务处理并发；重复命令只返回现有进度。超时、取消、权限、摘要、磁盘与第三方冲突分别报告；失败只清理本次暂存，不移动旧指针或删绑定数据。关闭等待准备任务退出。

### 发行代价
当前本地候选四项目wheel合计13,841,202 bytes，主要来自Renderer自带OFL字体。比现行薄仓库大；最终Git/ZIP体积和许可需重新测量，不据此保证商店限制通过。字体无需拆包，游戏素材仍由独立Assets机制准备。需新版本发行，不能仅更新README让现有a4获得该能力。

## Alternatives considered
- 仅bootstrap聊天入口+写宿主环境的pip：仓库小，但DLL占用、共享依赖更新与旧模块缓存问题仍在，不作为默认。
- 轻量bootstrap+首次按命令下载到私有目录：不改GsCore、体积小，可作为以后薄分发模式；首次多一次网络依赖，不能消除用户额外操作。
- bundled运行库+恢复命令：URL安装同时取得匹配组件，保留故障诊断与恢复，推荐。
- 提交GsCore热依赖修复或发PyPI：前者需上游接受，后者不解决已加载共享库的升级；不作为本轮前提。
- 私有venv+业务worker：能够进一步隔离第三方库，但引入跨进程协议和生命周期，不适合本次M0安装改进。

## Consequences
项目依赖取得和数据查询分离，管理入口在核心缺失时可用；无需改变GsCore。运行中修复后仍需重启，HTTPX/Pillow不兼容仍需维护安装，不承诺任何宿主下一条指令就可查询。现有CLI保留用于旧版与第三方维护；AstrBot分发先保持原状，公共生成器/guard改动须检查其已实现消费者。

## Verification
本轮仅设计与只读复核：确认guard顺序、GsCore根入口发现方式、已加载模块缓存、四wheel标签/大小及资源读取方式，并完成独立子代理设计复核。Python官方[模块缓存说明](https://docs.python.org/3/reference/import.html#the-module-cache)支持不能靠更换路径热切换已有对象的边界；未实现管理指令、解压器或私有加载器。

实施验收需覆盖缺所有项目包、第三方不兼容、非法权限、错误摘要/路径、进程中断、并发及重复执行、旧模块来源、双消费者生成漂移、字体许可与资源、更新冷启动/回退和数据保留。统一离线检查后，在干净Windows与Linux/Docker实际GsCore验证URL安装、主人指令、关闭重启、Token等待、聊天回复与升级卸载；桩测试不替代这些证据。
