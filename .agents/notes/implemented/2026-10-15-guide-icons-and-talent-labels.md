# 攻略本地图标、版本化天赋中文与复盘质量约束

Category: bug-fix
Related task: [实施任务](../../tasks/done/2026-10-15-guide-icons-and-talent-labels.md)
Related code: [常量解析](../../../packages/dota2forge-core/src/dota2forge_core/infrastructure/_stratz_heroes.py)、[卡片](../../../packages/dota2forge-renderer/src/dota2forge_renderer/feature_layout.py)、[复盘](../../../packages/dota2forge-core/src/dota2forge_core/review.py)
Related docs: [攻略](../../../docs/subsystems/hero-features.md)、[复盘](../../../docs/subsystems/native-review.md)

## Problem
用户自测攻略购买无图标，聚合天赋忽略已定义name字段且Provider未填中文；单场ID730无中文，长天赋被四列布局截短。公开常量查询证实其内部键special_bonus_attributes，其他主宰天赋有中文displayName。截图确认GsCore多轮/补图可用，但问出装只发图、数值前后不一致，并从曲线臆断团战与责任。

## Decision
Renderer复用本地资源映射，在统计、样例购买和复盘购买图绘制装备图标；缺图保留文字，不引入HTTP。升级改三列，两行完整中文；超长回退完整文字，不截断效果。

样例常量严格使用本场版本；聚合周窗口未核实，选择抓取时最新已生效版本为最多16项天赋ID解释中文，notes明确名称版本，不修改统计patch。工具talents增加可空name，两端既有消费者共同消费共享结果。按来源内部键将无中文special_bonus_attributes译为属性加点，不给未核实数值、不推测ID0。未返回名称/常量错误分别声明，保留有效统计。

复盘共享提示和工具局限明确净资产非GPM、优势曲线非团战胜负/个人责任；建议按问题给文字与适用条件，补图不代替回答，数字核对本轮事实。本轮不是接入事件数据或模型评测；宿主人格/模型仍影响遵守程度。

## Alternatives considered
硬编码天赋ID/数值会跨版本误导；将本周统计默认为当前版本未经证实。联网渲染违反边界；仅终局图标不解决购买时序。增加指令模板替代普通对话违背用户多轮诉求；提示不能宣称彻底解决归因错误。

## Consequences
每次冷攻略新增有界常量请求，仍共用配额与6小时标签缓存，失败保留数据。JSON字段仅增量，双端源码/分发验证；AstrBot不发布。沿用测试候选版本，用清单摘要区分代码。真实模型质量与未接入事件继续明确。

## Verification
公开常量探针只保存公共技能定义，无比赛/账号/聊天；合成禁网测试和6张卡片视觉QA。最终全仓检查、构建与授权测试分支推送结果见关联任务和[证据](../../artifacts/guide-labels-20261015/README.md)。

统一入口2113项禁网测试通过、覆盖91.04%，独立scripts/Core/Assets94%/90%/92%；五包隔离安装、双端本地候选smoke与GS提交25文件/4wheel摘要验证通过。主仓388587a/GS85490d1推送原测试分支，无AstrBot发行。
