# 订阅、每日观察与持久化投递

[SubscriptionService](../../packages/dota2forge-core/src/dota2forge_core/subscriptions.py) 提供有限单次检测；[SQLite仓储](../../packages/dota2forge-core/src/dota2forge_core/infrastructure/subscriptions.py) 保存检查点、outbox和发送尝试。Core没有Scheduler、后台循环或消息I/O。两端Runtime已接入，默认关闭；真实推送验收见[任务](../../.agents/tasks/active/2026-10-02-subscriptions.md)。

## 所有权与账号快照

SubscriptionKey包含可信PlatformIdentity、opaque destination、可选AccountId、可选MatchId、DataSource与SubscriptionKind（new_match/rank_change/daily_report/match_report）。玩家订阅需要AccountId，指定比赛订阅只需要MatchId。路由为1–512字符、无空白/控制字符的适配器标识，不是用户填写的群号或URL；平台鉴权归适配器。身份、部署、机器人、所有者、账号、比赛、目标、来源、种类互相隔离。相同完整键幂等返回原记录；重新订阅生成新32位小写十六进制ID。

subscribe保存显式账号快照，不证明Steam所有权；默认账号由适配器读取绑定。两端改绑/解绑先取消该身份所有订阅、事件与尝试，再写绑定，取消失败不改变绑定。两文件不是跨库原子事务：后续绑定写入失败时，旧订阅可能已经撤销，不自动复活。

list_subscriptions/unsubscribe/pending_events/claim_event/retry_event/acknowledge按完整所有者隔离；列表可筛本会话。SubscriptionScope仅供可信组合入口，不可作为用户命令参数。订阅列表按ID分页，limit1–100、默认20，after_id为上一页末项。删除游标不影响续页；新增低ID下轮从头扫描。unsubscribe_all原子级联删除该身份全部订阅。

## 有限检测

poll_new_matches/poll_rank_changes/poll_daily_reports/poll_match_reports每次只处理一页对应kind订阅，默认20。新比赛默认20场、上限100；日报默认100。玩家新比赛先按recent发现，再读取详情与分析快照；指定比赛轮询详情，只有明确有时长和胜方才生成一次报告。批内同账号共享归一化观察，独立保存检查点。注入原始或明确刷新的Provider，不把TTL缓存当新数据；来源不符为INVALID_RESPONSE，不换源或重建基线。

- 首次有效非空比赛观察静默基线；后续仅接受更晚开始时间或最高时刻未观察ID，不用ID数值推断时间。事件按时间由旧到新保存。
- 未知胜负为UNKNOWN，保留旧frontier，不把缺字段当结束证据；空列表为EMPTY且不清基线。上一frontier不在窗口时coverage_gap=True，不编造缺失比赛。
- 已知段位首次静默基线；升降及0均可观察。None为UNKNOWN，不当作0；没有精确MMR。
- 抓取时间早于创建/已提交观察、倒退列表或CAS失败为STALE，不覆盖状态。正常EMPTY/UNKNOWN/UNCHANGED更新抓取时间和revision。
- ProviderError为FAILED，保留code/source/retry_after。429或鉴权失败立即结束当前批，不继续调用其他账号。存储、容量、取消和程序错误传播；已提交outbox不受后续失败影响。
- MatchReport同时保存比赛详情和经济/购买分析；分析源缺失时保留明确不可用状态。当前Provider没有官方MVP字段，消息只展示基于胜方K/D/A的“表现候选（非官方MVP）”，不冒充官方评分。

## 北京时间日报

固定UTC+8，不依赖操作系统时区。report_bounds按比赛开始时间归属半开区间[当天00:00,次日00:00)；不按结束时间。只允许已结束的北京时间日，默认09:00起观察前一天，小时可配置0–23。创建订阅之前的日期静默记录；重启只观察当前前一天，不批量补发漏过的历史日期。

DailyReport最多100场，保存原始行元数据、胜/负/未知数。coverage为empty_observation（来源为空，不等于当天没打）、bounded_observation（有限返回）、window_truncated（达到查询上限但未跨过日边界）、window_spanned（观察到日边界之前）。跨界也不证明来源完整：私密、延迟和遗漏仍可能存在。报告日期随事件同事务推进，重复日期不生成第二事件；失败不推进。

## schema v3与发送尝试

专用application_id的独立subscriptions.sqlite3，不复用绑定/缓存库。schema v3增加可空match_id与完成报告游标；已知v1/v2仅从经过列、唯一键、外键、行/事件校验的事务迁移，损坏、异库或未知版本固定SubscriptionRepositoryError。每次操作在线程内开闭连接。检查点/revision/outbox以BEGIN IMMEDIATE与完整前态CAS同事务提交；失败回滚。默认每bot scope1000订阅、每订阅1000未确认事件，满时明确失败，不淘汰。

pending按sequence读1–100条，不删；deliverable跳过已有发送尝试并支持sequence续页，避免离线目标阻塞后续事件。发送前claim_event原子占用；跨进程同一事件只能成功占用一次。attempt无自动过期。收到明确平台接受回执才acknowledge级联删除；失败、取消、超时或无回执保留占用，重启不盲发。retry_event由所有者显式解除，可能重复；确定没有尝试（未连接/未授权）可安全解除。进程可能在占用后、真正发送前崩溃，仍需人工重试。

这不是exactly-once或视觉送达保证。库含个人查询偏好和路由，部署负责权限、备份与删除；repr和日志不展示完整身份、路由、凭据或载荷。

## 两端组合

六个订阅入口：dota订阅玩家 <玩家ID>、dota订阅比赛 <比赛ID>、dota订阅 [比赛|段位|日报] [ID]、dota订阅列表 [游标]、dota取消订阅 <订阅ID>、dota重试推送 <事件ID>。dota比赛 <比赛ID>同时查询详情和分析数据。目标只从可信当前事件构造，投递时复核所有者、bot/连接与私聊目标。群创建/投递/重试要求当前Bot管理员；不等于任意群管理员。

GsCore用gsuid_core.aps.scheduler显式注册唯一interval job；AstrBot initialize拥有唯一asyncio timer，主动推送目前仅支持OneBot v11反向WebSocket，用明确self_id发送，避免Context.send_message无法选择同连接bot。连接表按本机SDK版本核对；其他AstrBot平台创建/重试明确拒绝。

计时器每60秒唤醒，按配置间隔门控（默认300、最小60），每轮一个分页轮转scope、每kind最多5订阅及5事件，非重入；日报只在配置小时之后。429尊重retry_after；无冷却信息或鉴权失败暂停至重新加载；存储/程序错误安全暂停。停用先移除/取消timer并等待在途轮询，再关闭HTTP/Renderer；导入和构造不启动任务。两端独立库不做跨平台去重，不同时订阅同一目标来假定唯一投递。操作见[接入指南](../cookbook/subscriptions.md)。
