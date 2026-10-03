# 经济序列与购买事件

Status: done

## 目标
按规划 Step 12 增加独立的比赛分析端口，保留 STRATZ/OpenDota 已核对的经济序列和购买事件及各自时间语义，不阻塞基础 MatchDetail。

## 非目标
不把 IMP、averageImp、award 或其他未版本化专有模型输出做成可解释业务指标；不实现 AI、订阅、自动解析、刷新作业、跨源拼接、后台任务或机器人新命令，不查询真实账号。

## 验收
- [x] 新增独立 MatchAnalysis 值、端口和服务，不改变基础 MatchDetail 构造或旧消费者。
- [x] STRATZ 保存 networthPerMinute、itemPurchases；OpenDota 保存 gold_t、xp_t、purchase_log，来源和缺失状态可区分。
- [x] 严格校验时间、序列、账号/槽位、匿名和购买字段；不把金钱、净资产、经验序列互相替换。
- [x] 禁网测试覆盖正常、缺失、空、错类型、重复玩家、匿名和 HTTP 错误；客户端所有权与取消语义保持。
- [x] 更新来源/详情契约、研究决策、历史任务和规划；统一门禁、四包构建和隔离 wheel 通过。

## 影响模块与决策
[Core](../../../packages/dota2forge-core/)、[来源契约](../../../docs/subsystems/opendota.md)、[详情任务](../active/2026-10-01-historical-match-detail.md)、[决策](../../notes/implemented/2026-10-02-analysis-enrichment.md)。

## 验证证据
Step 11 基线为923项禁网测试；本任务新增10项测试，最终933项禁网测试通过，聚合覆盖率93.47%，治理工具独立97%，Core独立93%；Ruff format/lint、mypy49源文件通过。

四包构建、git diff --check 和隔离 wheel smoke 通过；Core wheel包含MatchAnalysis公共导出。未更新运行中的AstrBot或GsCore宿主。

## 阻塞与下一步
Step 12已完成并归档。IMP已根据现有研究标为专有、未版本化且不可解释，保持未实现。分析结果未接入运行中的AstrBot/GsCore或图片命令；后续Step13为订阅系统，需另立任务和生命周期决策。
