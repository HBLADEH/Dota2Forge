# 订阅投递、权限与每日观察战报

Category: architecture
Related task: [Step13](../../tasks/active/2026-10-02-subscriptions.md)
Related code: [Core订阅](../../../packages/dota2forge-core/src/dota2forge_core/subscriptions.py)、[Dota2UID](../../../adapters/Dota2UID/)、[AstrBot](../../../adapters/astrbot_plugin_dota2forge/)
Related docs: [订阅契约](../../../docs/subsystems/subscriptions.md)

## Problem
首轮outbox仅保存待确认事件，没有跨重启的发送尝试标记，也没有每日战报、宿主调度或路由。仅依赖进程锁会在重载后自动重发不确定消息；有限recent不能证明全天完整战绩。用户已授权停机更新后重启。

## Decision
在专用订阅库schema v2增加事件尝试表，发送前原子占用，无自动过期；发送失败/取消/不确定则保留，显式重试才解除，确认成功级联删除。v1仅在应用标识、结构、唯一键、外键与行/事件验证后事务迁移，不触碰绑定库。

日报按固定UTC+8北京时间的开始时间归属日，默认09:00发送前一天观察；最多100场，明确窗口截断/跨越和未知胜负，不称完整全天。只发送创建订阅当日起的报告，不启动历史补发。

适配器保存来自可信事件的编码路由并验证身份/机器人/连接/会话；群创建/投递要求当前Bot管理员，私聊只能送给订阅所有者。查询偏好不证明账号所有权；改绑/解绑前取消该身份旧订阅，失败则不写新绑定。调度由宿主启动后显式注册，停用先移除/取消并等待，再关闭客户端；默认关闭，通过配置显式启用。失败不盲目重试，429尊重冷却且不重建Provider。

AstrBot主动推送限定OneBot v11反向WebSocket，用明确self_id调用API并核对连接；Context.send_message只选平台实例，不能证明同连接选中了原bot，因此未用于推送。其他AstrBot平台创建/重试明确拒绝。有限delivery sequence续页避免未连接/撤权目标阻塞后续事件；scope也按游标轮转，不静默截断100个机器人。

## Alternatives considered

GsCore插件指南推荐gs_subscribe统一管理；本机Subscribe.send不返回平台回执且可能按bot_id跨WS回退。它与本项目的Core唯一持久所有者、连接隔离和不确定发送确认不兼容。本增量不双写宿主订阅表、不修改宿主框架，使用已验证Core事件路由与target_send(wait_recall=True)；这是显式兼容取舍，未宣称接入宿主通用订阅管理页。
发送后才标记不能处理成功后崩溃；短lease自动恢复会重发不确定消息。因此选无自动过期的尝试记录加人工重试。每日只汇总20场或声称空结果就是没打都可能误导，选择最多100场的观察口径与明确不完整提示。

## Consequences
被占用但未发送的事件也可能需用户解除；不能保证exactly-once或视觉送达。群管理员撤权时不再投递。两端独立部署仍可能用户分别订阅同账号，需要用户明确只启用一个平台目标；不跨库去重。改绑先撤销再写绑定不是跨库原子事务，绑定写入失败不复活订阅。日报漏过历史日期不批量补发。真实消息验证不得用离线桩代替。

## Verification
统一检查1121项禁网测试、四包构建/隔离导入通过。实际SDK验证注册/取消timer与资源关闭；停机备份安装后两端冷启动ready，默认推送关闭。[证据](../../artifacts/subscriptions-host-v1/README.md)与[任务](../../tasks/active/2026-10-02-subscriptions.md)分别记录未验收的真实消息/权限/stop-reload；不以SDK桩替代聊天验收。
