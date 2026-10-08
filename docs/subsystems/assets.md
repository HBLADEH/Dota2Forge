# 托管素材服务

独立包 dota2forge-assets（导入 dota2forge_assets）提供素材基础设施，依赖 HTTPX/Pillow，不依赖 Core、Renderer 或平台 SDK。双端 Runtime 持有 AssetSession/AssetManager；构造不读文件、不联网。Renderer 仍只读 version=1 清单，查询不触发按需下载。[实施决策](../../.agents/notes/implemented/2026-10-07-managed-assets-service.md)记录边界和代价。

## 配置与命令

asset_download_mode=auto/manual/off，默认 auto；asset_proxy 为显式 HTTP(S) 代理，独立客户端 trust_env=False，不读取系统代理或玩家 Token。AstrBot 可继承宿主 http_proxy，插件字段优先。illustration_path 非空优先使用自定义目录；状态为 external/external_invalid，不下载或覆盖该目录。空路径使用插件持久化数据下 illustrations 托管根，两端目录独立。

图片模式 auto 在初始化结束后后台 ensure；合法空 Token 仍 awaiting_config、不创建业务客户端或数据库，但可准备素材。text/manual/off 无自动下载。已有完整且有效快照启动不联网；部分快照补齐失败文件；记录的 404 仅显式 update 重查。自动操作持久化 30 分钟冷却，手动操作 30 秒；一个 Runtime 同时只有一项任务，重复调用返回同一任务 ID，不排队。

do素材状态 返回状态和分类数量，不显示本机路径/代理；do下载素材 和 do更新素材 仅可信 Bot 管理员/主人可执行，不依赖 Token 就绪，不接受参数。宿主负责身份/权限，命令立即返回，不等待整包完成、不主动群发。ensure/update 返回任务 ID 或 None；status 返回不可变 AssetStatus；wait 等待当前任务，close 幂等并保留关闭任务所有权。

## 请求与失败

Valve herolist/itemlist 映射规范 ID 与 Steam CDN 路径；段位、星级、金币使用明确标记的 OpenDota 美术镜像。HTTPS 原址与每次重定向均检查允许列表，不接受聊天 URL。默认四并发；单请求绝对期限 30 秒、整项任务 10 分钟；网络/超时/5xx 最多重试两次，退避 1/3 秒；429 尊重 Retry-After 并服从总期限。403、身份、格式与 PNG 失败不重试。只有 404 成为 missing；其他失败单独保存，不能解释成官方缺图。

状态取 checking/downloading/ready/partial/failed/cancelled/busy，会话另有 disabled/external/external_invalid。按英雄/装备/段位/星级/界面/背景统计 available、missing_404、failed、reused；目录未知前 total=None，不伪造百分比。ready 允许实际 404，但须有可用图；有失败且有可用图为 partial。没有可用图为 failed。目录表失败也计入失败项目。

每文件记录来源、时间、SHA256、尺寸与权利；缓存复用前检查摘要和 PNG，支持文件级续作，不支持 HTTP Range。成功英雄/装备可单独发布，UI 失败不会丢弃它们；失败时保留旧图及原 fetched_at，没有旧图则不写虚假 missing。当前目录表未出现的旧 ID 保留。没有图像/条目变化时保留原 generation；最近成功时间更新于独立状态。

## 存储与生命周期

托管根包含 cache、staging、generations/<id>、current.json、status.json 和 OS 排他租约。第二实例报告 busy，不写目录、不挂载该托管快照；进程退出自动释放租约，不根据 PID 删除锁。缓存/快照单响应 4MiB、PNG 每边最多 2048/总像素最多 2048²、清单 1MiB、每类条目最多 2048、根预算 256MiB；越界、损坏、磁盘失败保留旧指针。

文件操作由受持有的线程任务完成；候选在同盘 staging 验证后改名为不可变 generation。候选 Renderer 验证后，在 AstrApplication._dispatch_lock 或 Dota2UID Runtime._send_lock 内原子更新 current.json 并切换实例；整组分页保持一个 Renderer。等待旧实例关闭后仅保留当前与上一代。提交前退出仍读旧快照，提交后退出仍读完整新快照。

关闭先进入 STOPPING，拒绝新操作并取消下载；等待请求、并发子任务、文件线程和 Renderer 后释放租约。关闭等待者取消不丢失所有权。GsCore 原生热卸载仍须先受控 stop。CLI 使用同一请求/来源/校验实现，保留 --output/--only-ui，选中资源全部请求成功后才发布；自定义目录 CLI 更新期间须停用渲染，文件替换不是目录级原子操作。

图片不进入 wheel/商店 ZIP，不自动生成背景，MIT 不重新许可 Valve 美术。新包需同步四组件宿主清单/固定 URL 与摘要；治理新增独立包边界及素材 80% 独立覆盖率，须维护者评审，不解除旧门槛。操作见[素材指南](../cookbook/illustrations.md)。
