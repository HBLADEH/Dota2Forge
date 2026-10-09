# 经济序列与购买事件契约

[MatchAnalysis](../../packages/dota2forge-core/src/dota2forge_core/domain/analysis.py) 是独立于基础 MatchDetail 的来源观察。`MatchAnalysisService` 只校验比赛 ID、来源和结果类型；它不修改基础详情构造，也不要求先查询近期列表。

## 来源语义

STRATZ 保存玩家 `networthPerMinute` / `itemPurchases`；玩家净资产序列仍为0秒起点、60秒间隔的 `NETWORTH_LEVEL`，不作为收入求和。另保存比赛级 `radiantNetworthLeads` / `radiantExperienceLeads`，分别为天辉相对夜魇的净资产/经验优势；首样本描述为 -60～0 秒，按 -60 秒起点、60 秒间隔保留有符号值，正数天辉领先，负数夜魇领先。不能拼接不同语义。OpenDota `gold_t` / `xp_t` / `purchase_log` 仍为 `COLLECTED_GOLD` / `EXPERIENCE_TOTAL` / 购买事件，来源、值、起点及间隔均保留。

购买事件保留来源比赛时钟（包括赛前负数）、来源提供的物品 ID 或 key、可选 charges；空列表表示来源明确返回没有事件，null 表示该字段缺失或未提供。匿名/未知账号只保留槽位和公开统计，不带昵称或身份推断。玩家最多十人，重复槽位、错误 ID、非法时间类型和超量序列失败为 `INVALID_RESPONSE`；时间须为整数且禁止 bool，赛前事件不删除或归零，见[决策](../../.agents/notes/implemented/2026-10-09-pregame-purchase-time.md)。

## IMP 边界

STRATZ `imp` 为未版本化模型输出。按用户选择原样保存于 MatchParticipant.imp，只允许 STRATZ 来源的有符号 Short；缺失仍为 None，0 有效。MatchReport 在本局可用分数中列最高正分/最低负分各至多三人，不把全正分局的最低分叫表现差，也不推断缺失分数。并列展示 K/D/A、参战率、经济、伤害/治疗，这些是统计依据而非 IMP 公式；不换算 MMR、胜率或官方 MVP，不作跨比赛/来源比较。averageImp/award 未实现。[决策](../../.agents/notes/implemented/2026-10-09-match-analysis-report.md)接续旧研究边界。

## 错误与生命周期

分析 Provider 使用与基础详情相同的注入 HTTP 客户端、有限超时、限流和取消语义；不自动解析、不申请刷新、不重试或换源。显式 null 比赛返回 `MatchAnalysisUnavailable`，players=null 保留为未知，空 tuple 表示明确空列表。Provider 不拥有或关闭调用方客户端。

分析结果接入双端比赛宽幅报告和订阅MatchReport文本。IMP可用时列来源表现排序；不可用时订阅保留旧胜方K/D/A非官方候选。团队合计/参战率仅在实际五名同阵营玩家的必要字段完整时计算；零击杀或参战数大于团队击杀为未知。订阅JSON保留新字段，旧记录缺键仍可读，schema不变。缓存、刷新和有限重试只能由组合入口显式装饰Provider，不改变来源语义。

验证见[Step 12任务](../../.agents/tasks/done/2026-10-02-analysis-enrichment.md)和[研究决策](../../.agents/notes/implemented/2026-10-02-analysis-enrichment.md)。
