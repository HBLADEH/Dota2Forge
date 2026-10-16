# 数据驱动复盘 Skill

开发候选：Core0.1.0a9、Dota2UID0.1.0a16、AstrBot0.1.0a14；Renderer仍为a8。未发AstrBot或生产Release，真实模型遵守程度仍需评估。

## 内容与入口
共享资源位于Core.infrastructure.review_skills/dota2-review，版本1.0.0。SKILL.md保留取证、主题路由、事实/解释/行动/条件、图文互补与自检；references按overview、economy（含laning）、items、team渐进加载。资料参考[dota2-newbie-assistant固定版本](https://github.com/timzhangherenow/dota2-newbie-assistant/tree/be6cf7f038c0f548a535d50b723181c0b806a01e)，包内保留作者归属与MIT许可。

综合复盘考虑对线/资源、装备、职责和团队目标，按影响与证据选择重点；单点追问只展开对应主题。辅助不按核心补刀或净资产评分，不能用KDA/IMP分锅；替代路线需说明解决的问题、触发条件和代价。数据缺少的方面明确缺口，不凑结论。没有固定补丁/分钟出装表、自动解析脚本或录像操作推断。

两端get_dota2_review_context的JSON新增analysis_guide（名称、Skill版本、正文、当前专题资源与内容），每次读取受限枚举，不接受模型路径。指南不进入evidence_id计算，事实摘要仍由事实生成。宿主没有Skills API时同样可读指南；不是仅把文件放进开发.agents/skills。

GsCore通过ai_skill注册Core安装目录的只读资源；使用当前SDK的list/load/read资源机制，取数仍经可信事件/会话/人格权限。SDK目前无公开注销接口，适配器仅在确认登记列表和重建函数可用时注册；释放时按tuple对象身份删除本代登记并重建，避免旧代关闭误删新代或用户覆盖。缺接口时使用工具内指南，不修改宿主或全局人格。Skill不提供可执行脚本，AstrBot复用指南但不注册GsCore SDK。

## STRATZ优先与OpenDota兜底
普通战绩和CrossCheckService规则不变；仅ReviewService由组合入口显式注入一个OpenDota备用服务。STRATZ有目标时间线/购买时不查询OpenDota；双方概览可用团队或任一参赛者时间线。空时间线和空购买不等于完整过程。

主源not_found/timeout/unavailable/rate_limited，或只有基础结算且没有以上过程数据时，最多读取一次备用完整证据；不重试、不POST、不跨源补字段。PRIVATE、AUTHENTICATION、INVALID_RESPONSE不触发切换，保留来源错误。若备用有过程数据则整份选用备用；两份均基础或备用失败，保留主源事实。主源完全失败且备用可用时允许基础复盘；两源都失败返回主源错误，取消和程序错误传播。

ReviewEvidence末尾增source_attempts，最多两条固定来源/原因，旧构造兼容；工具返回实际source、source_attempts和各自时间/语义。OpenDota的collected_gold不作为STRATZ净资产，不借用主源补丁或IMP。两源分别有5分钟有界缓存，由各适配器关闭。

## 事实辅助与验证边界
JSON新增匿名lineup、availability和checkpoints。阵容只含slot/hero/阵营/位置，无账号昵称；采购区分missing/empty/available。采样点仅在5/10/15/20/25/30/40/50/60分钟恰有原采样且不越时长时提供，不取邻点、不插值；每项保留semantic和target/radiant视角，避免把天辉优势误认成目标方优势。

两端从既有Renderer中文表注入英雄/装备名称供display_names查ID；未知保留ID/key。名称不修改原始事实和evidence_id，也不证明本场补丁机制，Core不依赖Renderer或自行读取其资源。

死亡、团战、目标、视野和分钟补刀仍为not_integrated。OpenDota原API可能有这些字段，不代表本版已经归一化或可用于判断。Skill解析/工具回归不证明模型分析正确；真实模型评测与原生会话实机验收分开记录。

原因见[决策](../../.agents/notes/implemented/2026-10-16-review-skill.md)，操作见[多轮复盘](../cookbook/native-review.md)。
