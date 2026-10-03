# 订阅检测与持久化事件边界

Category: architecture
Related task: [Step13](../../tasks/active/2026-10-02-subscriptions.md)
Related code: [检测](../../../packages/dota2forge-core/src/dota2forge_core/subscriptions.py)、[仓储](../../../packages/dota2forge-core/src/dota2forge_core/infrastructure/subscriptions.py)
Related docs: [订阅契约](../../../docs/subsystems/subscriptions.md)

## Problem
Step13 要求订阅，但当前 Core 无订阅状态；Bot 查询/消息资源已有独立生命周期。仅在检测成功后推进游标会让发送失败丢事件，只靠进程内去重则重载会重发历史。

## Decision
采用独立订阅 SQLite 文件和 Repository，显式单次 Core 轮询原始 Provider；首次有效非空比赛/已知段位静默基线，检查点与待发送事件同事务保存。使用版本比较避免旧轮询覆盖新状态；取消订阅删除事件，新订阅采用新 ID。发送归适配器，成功后显式确认；本轮不启动任何调度器或外部消息。

订阅是明确账号快照，不随绑定自动变化；完整键包含四维身份、路由、账号、来源和种类。bot scope 列表仅供可信调度入口，用户读写按完整所有者隔离。单次页与历史窗口各至多100；同批同账号复用观察，来源改变明确失败。只有已知胜负的候选进入新比赛检测，未知候选不越过 frontier；空结果不抹去旧基线，段位 None 不当0，升降均保留。

匹配最高开始时间加同刻IDs而非数值最大ID；缺少旧 frontier明确标记 coverage_gap，不编造漏掉的比赛。默认每bot最多1000订阅、每订阅1000待确认事件；容量满失败、回滚、不淘汰。JSON解码、schema/唯一键/外键失败固定分类，不泄露底层错误。取消后线程事务可能已提交，outbox保留供重读。

## Alternatives considered
直接在 Core 调度/发送违背现有边界；复用绑定数据库需迁移并影响运行中的查询；先推进游标再发送有丢失风险。因此拟选独立存储和持久化 outbox。

## Consequences
首次非空基线不会补发旧比赛；有限 recent 不保证完整覆盖。outbox 不保证平台 exactly-once，发送与确认之间崩溃仍可能重复；实际启用前适配器必须明确单一调度/消费所有者、权限、发送失败与卸载规则。每日战报及平台接入未实现。

## Verification
新增124项合成测试，最终统一入口1057项禁网测试通过，聚合94.19%、Core独立94%，订阅领域值/SQLite仓储100%；四包build与隔离wheel通过，命令证据见关联任务。保留比赛载荷各自的抓取/观测时间，不强制与近期列表时间相等。两个已有适配器组合入口未修改；宿主权限、调度与推送、每日战报和真实周期观察尚未实现/验证。
