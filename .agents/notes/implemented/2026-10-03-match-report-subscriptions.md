# 完成对局报告订阅

Category: feature
Related task: [Step13](../../tasks/active/2026-10-02-subscriptions.md)
Related code: [Core订阅](../../../packages/dota2forge-core/src/dota2forge_core/subscriptions.py)、[报告值](../../../packages/dota2forge-core/src/dota2forge_core/domain/match_reports.py)、[双端控制器](../../../adapters/)
Related docs: [订阅契约](../../../docs/subsystems/subscriptions.md)、[分析契约](../../../docs/subsystems/analysis.md)

## Problem

原订阅只保存recent中的MatchSummary，不能在群里汇总完成对局的详情、参赛者统计、经济序列和购买事件；也没有指定比赛的持久订阅目标。已有分析Provider只支持显式查询。

## Decision

增加MatchReport不可变值，保存MatchDetail、MatchAnalysis或明确Unavailable状态、玩家订阅快照和来源元数据。玩家新比赛由recent发现后查询详情/分析；指定比赛订阅以MatchId为唯一目标，详情没有明确时长和胜方时保持等待，完成后原子推进游标并生成一次事件。schema v3增加match_id和match_reported，v1/v2严格迁移到v3。

新增dota订阅玩家 <玩家ID>和dota订阅比赛 <比赛ID>；原dota比赛查询同时附加报告信息。两个适配器继续各自持有命令、调度和SQLite库。群创建和推送权限沿用Bot管理员规则。

当前STRATZ/OpenDota分析契约没有官方MVP或IMP字段。按胜方K/D/A、死亡、GPM和槽位产生确定性的表现候选，只标注为非官方MVP；缺少字段时显示未知，不编造官方评分。经济序列和购买事件只显示计数及来源状态，原始语义仍在持久事件里。

## Alternatives considered

只发送MatchSummary无法满足详情和分析要求；每轮只查指定比赛详情会在未结束时重复播报；用短期内存集合去重会在重启后失效。因此选择MatchReport快照、持久完成游标和outbox确认。把表现候选命名成官方MVP会误导，故保留来源边界。

## Consequences

一场玩家对局可能触发一次详情和一次分析Provider请求；详情或分析失败时不确认新的玩家frontier，下一轮可重试，仍受429和认证暂停规则约束。指定比赛订阅按完整比赛目标隔离；同一群可订阅多个比赛。两端仍不跨部署去重。官方MVP需要Provider未来提供可验证字段后另立契约。

## Verification

新增离线测试覆盖未完成等待、指定比赛完成一次、玩家recent转MatchReport、详情/分析持久化重开、命令和桥接注册。统一治理、完整禁网测试和实际宿主重启在任务中记录；真实群播报仍需用户发起测试。
