# 经济序列与购买事件

Category: data
Related task: [分析任务](../../tasks/done/2026-10-02-analysis-enrichment.md)
Related code: [分析模型与Provider](../../../packages/dota2forge-core/src/dota2forge_core/domain/analysis.py)
Related docs: [分析契约](../../../docs/subsystems/analysis.md)

## Problem
Step 12要求扩展IMP、经济和购买数据。现有研究已核对 STRATZ 的 `networthPerMinute`、`itemPurchases`，以及 OpenDota 的 `gold_t`、`xp_t`、`purchase_log`；这些字段名称相似但统计口径不同。研究同时把 STRATZ `imp`、`averageImp`、`award` 归为未版本化专有模型输出，不足以建立可解释公共指标。

## Decision
- 新增独立 `MatchAnalysisProvider`、`MatchAnalysisService` 和不可变分析值，保持基础 MatchDetail、旧 Provider 端口和双端消费者不变。显式 null、players=null、空列表和缺失序列分别保留。
- STRATZ只请求并保存 `stats.networthPerMinute` 与 `stats.itemPurchases`；净资产序列的来源语义标为 `NETWORTH_LEVEL`，0秒起点、60秒间隔。OpenDota保存 `gold_t`/`xp_t`/`purchase_log`，标为 `COLLECTED_GOLD`/`EXPERIENCE_TOTAL`，不跨源拼接。
- IMP、averageImp、award、impPerMinute等专有模型输出不进入模型、不补0、不映射为评分/MMR/胜率。若将来有版本和口径证据，另立契约。
- 严格校验来源、比赛ID、账号/槽位、序列值、购买时间、ID/key/charges和最多十名玩家；匿名账号不带昵称。分析 Provider 复用注入客户端、超时、限流、取消和所有权，不自动解析/刷新/换源。

## Alternatives considered
- 把经济序列直接加到MatchParticipant并复用旧missing_fields：会把来源特有指标伪装成基础详情字段，破坏旧消费者兼容，拒绝。
- 用 OpenDota gold_t 替代 STRATZ networthPerMinute：金钱与净资产不是同一指标，拒绝。
- 将 IMP 当作统一评分或失败时置零：专有模型未版本化、缺失不等于0，拒绝。
- 为分析自动请求解析/刷新或跨源补齐：会增加网络副作用并隐藏来源缺失，拒绝。

## Consequences
SDK可以读取来源明确的经济与购买观察，基础详情和机器人行为不变；分析尚未接入图片/聊天命令，IMP仍未实现。不同来源的序列只能按各自语义展示，不能据长度或数值推断时间对齐；真实账号和长期字段覆盖仍待授权联调。

## Verification
核对已有 STRATZ 评测、历史详情 schema 和公开 OpenDota MatchResponse；新增10项禁网分析测试覆盖两来源映射、null/空/匿名、类型/范围错误、独立查询和无 IMP 请求。最终933项禁网测试（聚合93.47%）、治理工具独立97%、Core独立93%、Ruff/mypy49源文件、四包构建、git diff --check和隔离wheel通过；未在线查询、未部署到宿主。
