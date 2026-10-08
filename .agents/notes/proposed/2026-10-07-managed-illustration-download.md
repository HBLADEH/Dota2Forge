# 首次自动准备与受控更新本地素材

Category: architecture
Related task: [设计任务](../../tasks/done/2026-10-07-managed-illustration-download-design.md)
Related code: [现有下载器](../../../scripts/download_dota_assets.py)
Related docs: [当前素材流程](../../../docs/cookbook/illustrations.md)

## Problem
现有工具支持显式下载及--only-ui，但不进入安装wheel，没有插件后台任务/管理命令。商店新装缺图会出现问号。10-07实际容器下载完成英雄/装备后，OpenDota图标镜像超时导致整包没有发布。直接把同步脚本放进启动或渲染会阻塞宿主、反复下载，并留下覆盖期间文件/清单不同步的问题。

以下为待实现设计；不将此提案描述为现有能力。

## Decision

### 用户行为与兼容
两端拟新增asset_download_mode=auto/manual/off，默认auto；asset_proxy默认空，illustration_path保留。非空自定义路径优先，状态为external或external_invalid，自动和管理命令都不覆盖该目录。空路径使用插件持久化数据下的托管illustrations目录，无须手填生成路径；原配置不自动重写。

auto在图片模式首次Runtime初始化时后台ensure；已有完整有效快照时不联网，partial只补未完成文件。text模式不自动启动。manual仅按管理员请求下载；off禁止素材联网。非密钥配置有效但Token为空时仍可准备图片，业务维持awaiting_config，不创建STRATZ请求。导入/构造无I/O，查询/渲染不按需拉图，首命令只可复用幂等初始化；首装未完成时先使用占位卡。

拟定三个入口（唤醒前缀沿用宿主）：

| 入口 | 权限与行为 |
| --- | --- |
| do素材状态 | 返回素材状态、可用/404/网络失败数量、进度、最近尝试及更新时间；普通用户不显示本机路径/代理 |
| do下载素材 | 当前Bot管理员/主人；ensure首次下载或补齐，完整快照立即复用 |
| do更新素材 | 当前Bot管理员/主人；重新取得目录表并刷新素材，原快照继续出图 |

管理鉴权在宿主适配器执行，拒绝普通用户，不依赖Token就绪。命令立即返回已开始/已有任务，不等待整包完成；启动和完成只更新状态与日志，不主动群发。auto失败尝试持久化30分钟冷却，单次初始化至多一个任务；手动操作30秒冷却，不排队重复任务。没有周期性全包更新；已记录404仅在显式更新时再查。

### 共享边界与接口
拟新增独立共享包dota2forge-assets，导入名dota2forge_assets，两个适配器直接依赖。它承载下载/文件基础设施，依赖httpx与Pillow，不依赖Core、Renderer或平台SDK；Renderer继续只读version=1清单，Core业务无素材职责。避免把HTTP塞进现有Renderer或在两个适配器复制下载器。

AssetManager由Runtime持有，注入HTTP transport、时钟、托管根和进度接收器；异步ensure()/update()返回任务ID，status()返回不可变AssetStatus，异步close()等待关闭。AssetStatus含state、generation、按类别的available/missing_404/failed/reused、文件进度/总数/字节数、last_attempt/last_success及脱敏错误；目录表未知前不捏造百分比。state取disabled/external/external_invalid/busy/checking/downloading/ready/partial/failed/cancelled；ready允许404但须有可用游戏图，partial仍有失败，全无可用图为failed。素材状态与业务ready独立。

CLI复用共享服务，保留--output/--only-ui旧调用；显式自定义目录CLI仍只在成功后更新选中资源，在线管理的部分成功不静默改变旧脚本验收语义。AstrBot用AstrApplication的_dispatch_lock切换Renderer；Dota2UID用Runtime的_send_lock切换，发送已生成bytes不重绘。一组分页固定同一Renderer/快照。

### 来源、增量与失败
沿用Valve datafeed及Steam CDN获取英雄/装备，OpenDota镜像获取段位/星级/金币；不需要玩家凭据。生成背景不自动生成或从未核实URL下载，自定义已有背景保持原来源。独立客户端trust_env=False，不复用Provider的认证头/Token；代理由组合入口显式传入，AstrBot可继承已配置宿主代理，asset_proxy优先。日志不打印带凭据的URL。

HTTPS源及重定向目标使用明确允许列表，不接受聊天传入URL或随机镜像。默认4并发，单请求绝对期限30秒，整任务10分钟；连接超时/临时5xx最多重试2次，退避1/3秒，429尊重Retry-After且服从总期限。403/身份格式/摘要或PNG失败不重试；仅404记missing，网络错误保留failed，取消不算missing。

逐文件复用经SHA256/PNG检查的缓存，支持文件级续作，不在首版实现HTTP Range。英雄、装备和UI失败隔离：成功文件可进入新的partial快照，UI超时不丢弃英雄/装备。失败且旧文件有效时保留旧条目及原fetched_at；没有旧文件则不写成manifest missing，失败详情放manager状态。有效404按真实缺图发布；旧历史ID仍保留已验证条目，不把当前表未包含等同404。无新可用变化时保持旧generation。

保留原URL、响应/文件摘要、时间、尺寸、版权和镜像标记。单响应4MiB、PNG2048²、清单1MiB，沿用规范ID/路径/条目数限制；托管根总预算256MiB，超额/磁盘不足终止候选发布并保留旧快照。目录表或PNG不合法不会成为可用资源。

### 存储、发布与关闭
托管根包含cache、staging、generations/<id>、current.json和独立任务状态；version=1 manifest只含available/missing，业务Renderer不读管理状态。自定义目录不纳入回收。

Runtime持有托管根的跨进程排他租约，一个根只供一个宿主实例；重复进程不写入、不接入该托管Renderer，报告busy。租约由OS锁实现并在进程退出释放，不能按PID猜测删除锁。两端各用自己的数据目录。

下载到同一文件系统的staging，验证全部拟发布条目后变为不可变generation。候选Renderer验证后，在整组绘图锁内原子替换current.json并切换实例；不原地覆盖正在读取的PNG/manifest。磁盘指针先更新、进程若随后崩溃，下次启动仍能读完整快照。新任务不得在旧切换完成前发布；等待旧批次/绘图线程、close旧Renderer后回收，仅保留当前和上一代。发布失败或校验失败不替换旧指针。

stop/reload先拒绝新任务，取消下载并等待请求/文件操作及任何已开始线程，再关闭Renderer/HTTP并释放租约。STOPPING后不得调用应用切换；关闭幂等且保留任务所有权，不能只取消awaiter。GsCore继续要求受控stop后重载，不宣称原生卸载会释放这些资源。

### 发行与实施
增加第五个共享包，需要维护者评审治理policy/验证配置；本提案不修改门禁。两端依赖、版本guard、生成参考、runtime-wheels/release.json、公开requirements、安装器及离线映射须同步支持新增wheel。assets与renderer不带stratz extra，Core/适配器保留正确extra；新组件仍用固定Release URL/SHA256，不能回退到未发布PyPI名称。

先实现独立服务/CLI和禁网测试，再接两端配置/管理权限/生命周期/快照切换，最后做四个运行组件的隔离安装/升级与两端真实首装。发布另记授权；素材仍不进入MIT wheel/商店ZIP。

## Alternatives considered
启动时直接执行整包脚本：阻塞、不可续作且图标失败仍连带全部资源。回复时联网补图：增加查询延迟并破坏Renderer边界。把下载器放入Core或两个适配器各写一份：职责混入业务或形成重复实现。只加手动命令：不能解决商店新装仍需要人工操作的问题。

## Consequences
新装图片模式允许独立后台下载，管理员可关闭；首次完成前仍会短暂占位。迁移不修改现有自定义素材/Token/绑定。新增包和Renderer替换入口扩大公共契约及发行验收面；清单兼容、部分失败、取消和锁必须先经离线验证。来源可变化，自动下载不代表所有历史素材可得，也不重新许可Valve美术。

## Verification
本轮只核对源码/现行契约和形成提案，尚无功能实现、性能或真实宿主自动下载证据。实施验收见[计划任务](../../tasks/active/2026-10-07-managed-illustration-download.md)，本轮治理/离线结果记录于设计任务。
