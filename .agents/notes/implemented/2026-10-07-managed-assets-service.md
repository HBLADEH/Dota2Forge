# 共享素材下载与不可变快照

Category: architecture
Related task: [实施任务](../../tasks/active/2026-10-07-managed-illustration-download.md)
Related code: [素材服务](../../../packages/dota2forge-assets/src/dota2forge_assets/manager.py)
Related docs: [素材契约](../../../docs/subsystems/assets.md)

## Problem

AstrBot 商店不含 Valve 游戏图片。旧显式脚本不随运行包安装，UI 镜像超时使已下载英雄/装备没有清单。用户要求实施[自动准备提案](../proposed/2026-10-07-managed-illustration-download.md)，需同时解决首次体验、失败续作、生命周期与分发缺包。

## Decision

新增独立 dota2forge-assets，而不把 HTTP 放入 Core 或 Renderer。双端消费 AssetSession/AssetManager；导入/构造无 I/O，启动后按 auto/manual/off 与 image/text 决定后台 ensure。自定义路径优先且不覆盖；合法空 Token 仅等待业务配置，仍可准备公共素材。管理命令使用宿主可信管理员判断和正常身份校验，不接受 URL，不主动发送完成消息。

缓存经摘要/PNG 检查后复用，记录真实 404 与其他失败；每类文件独立失败，成功部分可发布。更新失败保留旧条目原时间，保留历史 ID，不为缺失数据猜图。请求允许列表、四并发、请求/任务绝对期限、有限重试、持久化冷却和空间预算见契约；独立客户端不携带玩家认证，代理显式注入。

OS 锁防止双实例共享一个托管根。staging 验证后改名为不可变 generation，current.json 原子提交；在两端整组绘图/发送锁内切换 Renderer，关闭旧实例后回收当前及上一代之外快照。STOPPING 后禁止提交，关闭等待者被取消仍由持有任务等待请求、子任务和文件线程。CLI 复用共享实现，保留显式工具选中资源全部请求成功才替换的语义。

根 workspace、锁文件、依赖与分发清单加入第五包；每个宿主使用 Core/Renderer/Assets/自身适配器四组件，Assets/Renderer 不带 stratz extra。AstrBot 升至未发布 a8，Dota2UID 未发布 a5，Assets a1，Core/Renderer a4；不覆盖已公开 a7 同版本 wheel。开发桥接要求先装匹配本地 wheel；公开候选继续生成固定 Release URL/SHA256，不能回退到未发布 PyPI 名称。

policy/schema/checker 新增 independent_paths，强制 Assets 不引用其他项目包，并新增独立 80% 覆盖率；保持 Core/治理工具原门槛。此工程配置变更须维护者评审，本地实现不代表评审或发布获准。

## Alternatives considered

同步调用原脚本会阻塞启动，失败仍连带整包。渲染时拉图会增加查询延迟、破坏展示边界。双端各写下载器会重复权限之外的逻辑。原地更新图片与清单会让一组分页混用不同版本；仅手动下载不能解决新装体验。

## Consequences

首次完成前仍用占位，有效完整快照无需再联网，真实 404 继续占位。新增共享运行包扩大安装/升级契约；缓存与两代快照占用受限持久化空间。自动下载不代表所有美术可得，也不自动生成背景或获得再分发许可。GsCore 原生卸载不保证关闭，受控 stop 仍必须执行。

## Verification

新增禁网专项覆盖部分成功、续作、旧图时间、严格来源/格式/大小、管理员权限、空 Token、模式/自定义目录、整组切换、缓存损坏及关闭。真实子进程验证租约争用和退出释放，以及指针提交前后进程退出恢复。最终统一门禁1608测试通过、总覆盖93.03%；五包构建/独立 wheel 及双端SDK-free隔离分发通过。

授权服务器隔离目录真实下载557张可用PNG，129装备404无其他失败；完整快照重开不联网，合成战绩卡与截图对应英雄解码通过。Linux内两端SDK-free Runtime验证重复启动、快照复用及关闭，临时目录已清理。命令、候选摘要和联调边界见[实施证据](../../artifacts/managed-illustration-download-v1/README.md)。新自动功能尚未生产部署、商店发布或真实聊天联调，不能引用旧手动素材部署作为自动功能验收；治理配置仍需维护者评审。
