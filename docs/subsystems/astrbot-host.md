# AstrBot 宿主接入契约

当前源码新增[托管素材服务](assets.md)：空自定义路径按 auto/manual/off 准备，Token 等待与素材状态独立；管理命令校验可信权限。新候选尚未生产部署，历史手动素材和宿主证据不能替代自动下载联调。

源码核对基线是AstrBot v4.28.2（上游commit `3c7adafa1397e182d60b1016bf88759265113c8a`），本机桌面版同版本。声明`>=4.5.0`：v4.5.0（`07ba9c772c3518838921a01dd09290215833a80e`）已核对公开导入路径/命令类型；聊天验收仍为4.28.2。2026-10-07另有4.28.1/Linux/Python3.12.13的a7依赖安装、真实SDK导入及冷启动awaiting_config证据，Token未配置，不代表该环境业务或全部版本/平台已验收。

## 发现与配置

0.1.0a2本地候选的合法空Token进入awaiting_config，给出配置提示且不创建客户端/业务库；非法配置保持failed。填写后通过保存/重载的新实例恢复。商店生成入口另含早期项目库版本核对；本轮仅SDK桩与本地wheel隔离验收，不更新本机宿主兼容证据。见[发行步骤](../cookbook/plugin-release.md)。

[安装器](../../adapters/astrbot_plugin_dota2forge/src/astrbot_plugin_dota2forge/install.py)生成独立发现桥接的 main.py、metadata.yaml、_conf_schema.json、requirements.txt。Python src 库导入不依赖 AstrBot，不联网、不读取环境、不创建客户端或后台任务。ZIP 仅含桥接，未发布包须先以本地 wheel 安装；requirements.txt 让桌面版宿主选择 data/site-packages 的已安装依赖。宿主递归展开依赖并依次清除/导入顶层模块，库顶层公开导出按需加载，防止提前捕获旧Core/Renderer类型；Core/Renderer依赖仍由wheel元数据声明。

配置由AstrBot传入，Runtime验证namespace、stratz_token、timeout_seconds、reply_mode及subscriptions_enabled/轮询间隔/日报小时；未知键失败。Token repr隐藏；超时有限正数至多60秒，image/text。bindings.sqlite3和subscriptions.sqlite3固定放专用plugin_data目录，不复用GsCore数据库。订阅默认关闭，主动推送当前仅OneBot v11反向WebSocket，权限/尝试/调度边界见[订阅契约](subscriptions.md)。配置修改需重新加载。

## 身份、权限与命令

可信事件的 get_platform_name/get_platform_id/get_self_id/get_sender_id 先校验；namespace/platform 保留其 Core 标识语义，bot_id 为连接ID与机器人ID的确定性 SHA256 编码，避免同类型多连接串用。原始字段不进入日志。命令和 AI 参数不能指定目标平台用户。允许 @ 当前机器人触发，@ 他人和 @ 全体拒绝。

普通命令为帮助、菜单、绑定、改绑、账号、解绑、玩家、战绩、比赛；do段位是玩家别名、do最近是战绩别名。Core 严格校验 Dota账号ID/比赛ID，不接受未实现的英雄查询。命令遵循宿主唤醒前缀；GreedyStr 保留全部参数后交给解析器，禁止宿主整数转换绕过前导零/额外参数校验。管理员 do状态/do停用同时使用宿主权限过滤器和 event.is_admin() 检查，不注册 AI Tool。

## 发送与选择

TextReply 用 plain_result，ImageReply 用 Image.fromBytes + chain_result，经 event.send 主动发送并停止后续事件响应。渲染已知失败返回同次数据文本，Provider/存储失败仍为分类文本；程序错误、取消和发送失败传播，不自动重发。API返回不证明平台实际递送或图片可读。

每份最近列表容量128、写入后TTL600秒，读取不续期；键包含四维身份和群/私聊。私聊使用发送者，群聊使用可信 group_id；缺失或 OtherMessage 无选择状态但允许直接查询。完整发送后并重新核对绑定记录才提交；发送失败保留上一份列表，成功空结果替换旧列表，改绑/解绑/停用/新实例清空。每次查询1–100场，默认10；初始至多两页，其余用第N页，序号用已发送列表的ID查详情，不重新查近期来源。详情只对实际参赛绑定账号高亮。

## 生命周期与验证边界

initialize创建SQLite仓库、单个专用httpx客户端/StratzProvider和可选Renderer；不在构造和模块导入时创建。初始化任务保留所有权；重复initialize不重新构造。Runtime同时接纳至多16个请求，串行查询/发送；过载最多一个提示发送，其余丢弃。terminate拒绝新请求、取消在途/排队/过载发送，等待初始化和Renderer线程、关闭HTTP；重复关闭共享同一shield任务。无长期Scheduler。

离线桩测试与真实宿主分列：[任务](../../.agents/tasks/active/2026-10-02-astrbot-platform.md)记录禁网合成测试、构建、独立wheel和本机验证。本机发现、配置、冷启动、重载及terminate关闭恢复已通过；用户确认OneBot单会话菜单、绑定、玩家、20场战绩、第3页和第1场详情正常且图片可读。直接ID、聊天管理员权限、跨用户/会话/连接及其他平台未实机验证。安装步骤见[操作](../cookbook/astrbot.md)，原因见[决策](../../.agents/notes/implemented/2026-10-02-astrbot-platform.md)。
