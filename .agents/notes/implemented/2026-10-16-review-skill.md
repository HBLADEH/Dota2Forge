# 渐进式复盘指南与显式整份来源回退

Category: feature
Related task: [实施](../../tasks/done/2026-10-16-review-skill.md)
Related code: [复盘](../../../packages/dota2forge-core/src/dota2forge_core/review.py)、[指南](../../../packages/dota2forge-core/src/dota2forge_core/infrastructure/review_guidance.py)、[GS桥接](../../../adapters/Dota2UID/src/Dota2UID/host_ai.py.template)
Related docs: [契约](../../../docs/subsystems/review-skill.md)

## Problem
用户要求参考dota2-newbie-assistant，优先STRATZ、不能使用时OpenDota，并改善多方面建议。前轮仅短提示，截图有只发图、时间数字错位和无事件归因。参考be6cf7f的完整度先行、阶段/职责、装备解决问题与下局行动适用；其自动POST解析、固定7.41f和终端脚本不符合现有只读机器人链路。

## Decision
Core随wheel提供dota2-review Skill1.0.0和四个专题，保留MIT归属；指南由基础设施读资源，领域/用例不读文件。双端工具按topic提供同一指南，相关追问提示主题，不依赖模型主动发现文件。GS另外用ai_skill注册原生资源；框架无公开注销，适配器显式检测私有兼容入口，释放仅匹配本代tuple身份并重建。旧SDK缺能力仍有工具内指南，不改框架/用户自定义Skill。

ReviewService可显式配置STRATZ→OpenDota一次整份回退。主源可用不查备用；仅not_found/timeout/unavailable/rate_limited或无过程基础结果触发。认证/隐私/格式失败不隐瞒或绕过。备用更有过程证据则整份采用，备用无改善/失败保留主源；两源完全失败仍报告主源错误。独立5分钟缓存由适配器所有，不改变普通查询/交叉核验。

新增source_attempts、匿名阵容、数据可用状态及精确原采样节点，减少源语义和时间/阵营错读；不拼数据、不插值、不增加事件已接入声明。指南明确事实—有条件解释—动作—条件/代价，综合多维、追问聚焦、辅助按职责，不以分锅或固定最优路线取代分析。

既有Renderer名称表由两端注入Core指南组合器形成display_names；不改变原事实或摘要，不凭ID猜英雄装备，也不把本地名称当本场补丁机制。比赛来源字段仍只作数据，插件内置指南通过独立analysis_guide提供。

## Alternatives considered
只加全局人格提示会污染普通聊天，模型不主动读Skill时文件不生效；只注册GS会让AstrBot丢能力。把OpenDota缺项拼到STRATZ或自动POST解析，会改变证据语义和外部副作用。硬编码版本与经济基准易过期。后台另建LLM会破坏原生多轮与预算。

## Consequences
Core升a9，两适配器最低Corea9并分别候选a16/a14，Renderer仍a8；锁与生成参考同步，AstrBot不发版。工具多一小份按题指南，有token成本；Skill不能补充未接入事件或保证模型遵守。新字段兼容原构造和Renderer，两端消费同一结果，无SQL迁移或平台消息。

## Verification
初步102项禁网回归与Skill前置验证通过。实际GsCore/Pydantic Skill发现、注册、卸载及原生五轮工具链使用合成依赖验证，不调用真实模型/消息。完整检查/构建/分支交付见[证据](../../artifacts/review-skill-20261016/README.md)。

统一检查2150项禁网通过、覆盖91.11%，随后提示末句一处措辞澄清经105项选测通过；最终wheel离线隔离安装和6份Skill文件实际SDK解析通过。未以字符串/格式检查冒充模型效果验证。

固定源码cc591cc及GS分发ab751ab推送既有测试分支，双端分发本地消费通过，25文件/4wheel提交字节与摘要一致。AstrBot无发行、宿主无修改、无真实模型/消息调用。
