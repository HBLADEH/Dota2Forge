# 经济序列与购买事件契约

[MatchAnalysis](../../packages/dota2forge-core/src/dota2forge_core/domain/analysis.py) 是独立于基础 MatchDetail 的来源观察。`MatchAnalysisService` 只校验比赛 ID、来源和结果类型；它不修改基础详情构造，也不要求先查询近期列表。

## 来源语义

STRATZ 当前固定查询保存 `stats.networthPerMinute` 和 `stats.itemPurchases { time itemId }`。前者是来源标记为 per-minute 的净资产序列，按 60 秒间隔、0 秒起点保存为 `NETWORTH_LEVEL`；不能把它当作收入或简单求和。OpenDota 保存详情玩家的 `gold_t`、`xp_t` 和 `purchase_log`，分别标为 `COLLECTED_GOLD`、`EXPERIENCE_TOTAL` 和购买事件；它们不与 STRATZ 净资产序列拼接或互换。序列值、起点、间隔和来源始终保留。

购买事件保留来源比赛时钟（包括赛前负数）、来源提供的物品 ID 或 key、可选 charges；空列表表示来源明确返回没有事件，null 表示该字段缺失或未提供。匿名/未知账号只保留槽位和公开统计，不带昵称或身份推断。玩家最多十人，重复槽位、错误 ID、非法时间类型和超量序列失败为 `INVALID_RESPONSE`；时间须为整数且禁止 bool，赛前事件不删除或归零，见[决策](../../.agents/notes/implemented/2026-10-09-pregame-purchase-time.md)。

## IMP 边界

STRATZ 的 `imp`、`averageImp`、`award` 等字段属于未版本化专有模型输出；现有研究记录没有足够定义支持跨时间或跨来源解释。Core 不导出 IMP，也不把它转换为评分、胜率、MMR 或建议。缺失的 IMP 不返回 0；后续若获得可核对的版本和口径，需另立契约与决策。

## 错误与生命周期

分析 Provider 使用与基础详情相同的注入 HTTP 客户端、有限超时、限流和取消语义；不自动解析、不申请刷新、不重试或换源。显式 null 比赛返回 `MatchAnalysisUnavailable`，players=null 保留为未知，空 tuple 表示明确空列表。Provider 不拥有或关闭调用方客户端。

分析结果已接入比赛详情查询和订阅MatchReport文本；详情/经济/购买数据仍保留来源与缺失状态。消息中的表现候选按胜方K/D/A等已观测字段计算，只是非官方MVP候选。缓存、刷新和有限重试只能由组合入口显式装饰分析 Provider，并不改变序列语义。

验证见[Step 12任务](../../.agents/tasks/done/2026-10-02-analysis-enrichment.md)和[研究决策](../../.agents/notes/implemented/2026-10-02-analysis-enrichment.md)。
