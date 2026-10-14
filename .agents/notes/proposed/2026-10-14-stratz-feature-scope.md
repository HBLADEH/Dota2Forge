# STRATZ 强势榜、数据攻略与证据驱动复盘的实施边界

Category: feature
Related task: [需求规划](../../tasks/done/2026-10-14-stratz-feature-planning.md)
Related code: [共享端口](../../../packages/dota2forge-core/src/dota2forge_core/ports.py)
Related docs: [详细需求方案](../../../Dota2Forge_STRATZ_FEATURE_PLAN.md)

本文保留规划时点。首版实施后的事实、口径变化和权限/缓存取舍见[新实施决策](../implemented/2026-10-14-stratz-hero-and-native-review.md)，真实模型/平台联调仍单独待验收。

## Problem
用户要求基于 STRATZ 规划当前版本强势英雄、丰富英雄攻略，以及在 GsCore/AstrBot AI 对话中的比赛复盘。已有比赛/购买/经济/IMP 与卡片可以复用，但完整攻略和 AI 工具未实现。历史攻略小样本与 schema 不足以证明当前补丁、段位窗口、所有分母及详细事件覆盖。用户提供的单场攻略页本次返回客户端/请求错误，不能宣称逐项验证该页面。

## Decision
本 note 为 proposed：先验证数据口径，再依次实现榜单、攻略和双端 AI 复盘。Core 提供同一组不可变统计、样例、证据与报告校验；HTTP/缓存留基础设施，宿主 AI/身份/消息/生命周期留适配器，Renderer 延续远古锻炉主题且不联网。

强势榜保留补丁与实际窗口、段位/位置/模式和分母；默认 1,000 场门槛、95% Wilson 胜率下界排序，规则明确且低样本不凑榜。上游无法核实排位/补丁时降低表述，不冒充排位当前版数据。攻略分统计构筑与单场样例，聚合加点不拼成未经验证的合法路线，guide 组场数不共享为所有模块分母。

复盘先构造 A/B 事实证据包，再使用宿主 AI 判断；C 事件按需新增。图片事实来自 Core，AI 判断标为推断并引用证据；结构校验不能证明语义正确。自然对话数据工具不嵌套调用 LLM，`do复盘` 通过适配器实现的 ReviewNarrator 端口只调用一次。无 AI/模型失败只输出同快照事实和原因。

首版有界进程内缓存、会话句柄隔离，无 SQLite 迁移；补丁指针变更失效，旧数据不冒充新鲜，不静默换源/重试。工具限受控参数，只回复当前会话；重载注销并排空，不能捕获旧代际业务对象。暂不将复盘自动加入订阅。申请解析是外部写操作，放 P2 独立定义权限、额度和幂等，不复制参考项目自动 POST 行为。

## Alternatives considered
- 直接复刻 STRATZ 页面：本次正文不可用，网页与 GraphQL 覆盖也未证实；优先已验证数据路径及新口径核查。
- 单按原始胜率排行：小样本可能占榜，默认采用可解释的下界；原始胜率仍允许显式选择且保留门槛。
- 将单场出装称完整推荐：缺乏通用性与合法聚合加点保证，分开统计和样例。
- 把整个 OpenDota 复盘 Skill 接入运行时：其自动解析、副作用、固化版本与脚本执行不符合本项目首版边界；仅借鉴事实/判断和行动建议的结构。
- 双端各写完整复盘/出图：会复制口径和缺失规则，改为共享 Core/Renderer，适配各自工具与模型。

## Consequences
发布前需要重新核实上游字段/筛选/分母、宿主 AI SDK 与模型能力；命石/技能素材另扩展 Assets。缓存、权限、公共契约与热切换实施另立 note。规划不代表 API 的长期稳定或已注册命令，不修改 policy/治理门禁，也不提供真实英雄排行榜。

## Verification
[历史攻略证据](../../artifacts/hero-builds-v1/README.md)、[当前分析契约](../../../docs/subsystems/analysis.md)、[本轮来源与草案说明](../../artifacts/stratz-feature-plan-v1/README.md)。本轮阅读本机 GsCore `register.py` 并对照手册：源码将插件特权分类重定向 common，与手册旧表述不同；本方案采用 common，不改宿主。两端 Dota AI 工具、当前榜单和详细事件未联调。

用户随后补充多轮对话偏好和攻略截图，[新提案](2026-10-14-conversational-review-and-guide-sample.md)替代默认报告/单一追问快照设计；本文保留首轮取舍，其他来源和架构边界继续有效。
