# 订阅接入与离线验收

[契约](../subsystems/subscriptions.md)、[首轮outbox决策](../../.agents/notes/implemented/2026-10-02-subscription-outbox.md)、[投递决策](../../.agents/notes/implemented/2026-10-02-subscription-delivery.md)。两端库实现/桥接已接入；实际安装和真实消息进度见[任务](../../.agents/tasks/active/2026-10-02-subscriptions.md)。

## 配置与生命周期

默认subscriptions_enabled=false。确认唯一负责推送的宿主/目标后再启用；两端不跨库去重。GsCore配置为data/Dota2UID/config.toml顶层，不能写在[platforms]表内；AstrBot在插件配置中设置同名字段：

~~~toml
subscriptions_enabled = true
subscription_interval_seconds = 300
daily_report_hour = 9
~~~

轮询间隔60–86400秒；日报小时0–23，固定北京时间。每轮有限分页，不表示每名玩家都恰好300秒查询一次；人数增多时检测延迟增加。429尊重服务端冷却，无冷却或鉴权失败暂停至stop/reload。订阅列表显示polling_paused/last_error；不要通过重建Provider或反复重载绕过配额。

共享wheel升级必须关闭整个宿主后安装并冷启动。仅修改发现桥接：GsCore先do停用或管理员stop API，确认stopped/client_closed=true后受控reload；AstrBot terminate等待timer取消和Runtime关闭后再重载。不得依赖GsCore原生卸载清理旧timer。数据库保留在插件数据目录；v1/v2只在严格校验后事务升级v3，先备份。不编辑真实凭据、聊天记录或订阅库入库。

## 用户命令

- 私聊或由Bot管理员在群内执行do订阅玩家 <玩家ID>；它在发现新对局后查询详情与分析并播报。do订阅比赛 <比赛ID>订阅指定比赛，完成后只播报一次；do比赛 <比赛ID>直接查询同样的详情/分析。
- 传统偏好通知可用do订阅 比赛、do订阅 段位或do订阅 日报；无类型默认比赛。
- 显式账号用do订阅 比赛 <ID>，账号只是查询偏好；不接受用户自填投递群号。
- 群聊创建/重试仅限Bot管理员；投递时重新检查当前授权。私聊只投给订阅所有者。AstrBot目前仅OneBot v11反向WebSocket支持主动推送。
- do订阅列表列出本会话/本人记录、未确认事件和暂停状态；10项满页时按给定游标续页。
- do取消订阅 <订阅ID>取消本人记录及待发事件。改绑/解绑先取消该身份全部会话订阅，再修改绑定；失败不自动恢复旧订阅。
- 无回执、发送失败/取消保留尝试，不自动重发。核实是否已经送达后，do重试推送 <事件ID>解除占用；可能重复。

第一次比赛/段位只建基线，不补旧战绩；玩家对局播报需详情确认完成。指定比赛订阅等待明确时长和胜方；分析源未提供时保留说明。当前没有官方MVP字段，消息中的表现候选不是官方评分。日报默认北京时间次日09:00起，统计前一天开始的有限观察，最多100场，未知胜负独立计数。空来源不等于当天没打，跨边界也不保证完整；停机不补全部历史日期。

## 禁网检查与实机验收

~~~sh
uv run --locked python scripts/check_governance.py --all
uv build --all-packages
uv run --locked python scripts/smoke_wheels.py
~~~

合成测试覆盖日报日期/半开边界/未知/不足、v1迁移回滚、持久claim并发/重开/人工retry、路由和权限、改绑串行化、限流暂停、发送取消、timer唯一注册/关闭。普通测试不安装宿主SDK，不查真实账号或发送消息。

实机由用户发起订阅：确认菜单、玩家/指定比赛命令；私聊/群管理员与非管理员隔离；初次无历史通知；之后完成对局报告、已知段位变化/日报送达；失败无盲发、显式retry及stop/reload无旧timer。核对详情、分析缺失和非官方MVP候选文案。保存最小状态证据，不保存真实消息/完整身份；SDK桩、平台API接受与客户端视觉可读性分别记录，不互相替代。
