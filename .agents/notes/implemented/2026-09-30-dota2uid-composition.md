# Dota2UID 宿主组合与受控生命周期

Category: architecture
Related task: [Dota2UID 接入](../../tasks/done/2026-09-30-dota2uid-first-loop.md)
Related code: [运行时](../../../adapters/Dota2UID/src/Dota2UID/runtime.py)
Related docs: [操作契约](../../../docs/cookbook/dota2uid.md)

## Problem
Core 已有绑定用例和 STRATZ Provider，需要首个真实适配器消费者。GsCore 从 plugins 路径中的调用栈推断 SV 归属，而项目使用可安全导入的 src 包；仅安装 wheel 无法注册服务。源码还显示原生重载删除关闭钩子而不执行，卸载只删除目录，不能假定客户端会随模块自动关闭。

## Decision
- 保留 src/Dota2UID 库包的无副作用导入。安装 dota2uid[stratz] 激活 Core 的 stratz extra；包内随附发现桥接模板，由显式安装命令放入 plugins/Dota2UID/__init__.py。SV 在该文件构造，符合宿主调用栈。模板是有宿主依赖的分发资源，由离线桩测试执行并核对触发器/鉴权，不将桩验证写成真实宿主通过。
- Config 从宿主 data/Dota2UID/config.toml 显式异步读取，Token 不进入 repr/日志。部署固定 namespace，platforms 将已核实的 Event.bot_id 映射为平台标识；未知平台失败。bot_self_id 为机器人账号，user_id 为调用者，要求存在 WS_BOT_ID，不用连接号代替机器人号，不接受 @ 他人代办或命令参数中的身份。
- SQLite 使用 data/Dota2UID/bindings.sqlite3，保持 Core 四维隔离、单账号、幂等及显式改绑。不接宿主多 UID Bind 表，不双写。绑定是查询偏好而非所有权证明。仅适配命令与展示，不复制账号/数据源业务。
- 命令是 dota帮助/绑定/改绑/账号/解绑/玩家/战绩，后两项可显式查询账号，条数 1–100 默认 10。未知统计展示“未知”，段位允许下降；每 5 场分段纯文本回复，附 STRATZ 链接及实际抓取时间，不保证历史完整。无 AI 自动注册、推送、轮询或回退。
- Runtime 以锁串行初始化/操作，首命令也检查初始化，覆盖首次热安装不跑 start_before 的情况。start_before 和 start 钩子均幂等；失败保持 failed，不自动重试。每个运行期复用一个 Provider 和专用 HTTP 客户端，保留限流状态。
- 停用先拒绝新操作、取消在途查询，再关闭 HTTP；关闭任务保留并 shield，调用方取消等待不丢失资源所有权。Core SQLite 线程取消不保证事务停止，延续原契约。宿主退出钩子与受控停用共用 close。
- 增加管理员头鉴权的 GET /api/dota2uid/status 和 POST /api/dota2uid/stop，返回状态及关闭标志，不泄露配置/身份。另有 pm=0 的 dota停用。受控重载须先停用成功再调用宿主 reload；卸载先停用、删除发现目录，重启宿主清除其残余触发器。不改宿主核心、不猴子补丁其卸载器，也不承诺直接删除目录可释放客户端。

## Alternatives considered
- 在 site-packages 直接创建 SV：与宿主的路径归属假设冲突。
- 迁用 GsCore Bind：多 UID 与 Core 的身份/写入语义不同，需另立迁移契约。
- 仅 on_core_start_before 初始化：首次热安装和重载漏跑；采用幂等钩子加命令就绪门禁。
- 自动补丁宿主 reload/uninstall 或扫描目录的常驻轮询：侵入宿主或增加无关任务；选显式停用和真实说明限制。
- 将 Token 放入通用 Web 配置：本阶段选择专用本机文件，减少对配置 UI 与宿主模型的依赖。

## Consequences
安装库与发现桥接是两步；宿主更新库后需受控重载或重启，不靠同版本 wheel 自动刷新。平台映射需部署核实，不能猜测未知标识。管理员操作和真实聊天消息联调分开授权；外部 API 故障展示固定错误分类。原生任意热卸载、跨进程限额、详情/IMP、补充源与真实平台收发不在当前离线证据内。

## Verification
487 项禁网测试及统一检查通过，适配器 80 项测试、独立覆盖率 94.88%。2026-09-30 在真实运行中的 GsCore 完成首次热加载、先停用再重载、先停用再卸载/重启清理，以及恢复后的冷启动；最终 ready、8 个命令，无重复，匿名 GET 状态/POST 停用均 401，配置和绑定库指纹不变。原生卸载确实留下 stopped 路由/命令，重启后消失，证实受控流程必要。Agent 未代发外部聊天；用户随后在 QQ 单会话实测并确认帮助、绑定、玩家和战绩均正常回复。治理脚本仅纠正“全部骨架”输出；wheel 检查加 --no-cache 与模块/资源断言，保留原门槛和隔离断言；脚本改动仍需维护者评审。
