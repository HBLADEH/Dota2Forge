# STRATZ零标识技能与GsCore真实追问钩子修正

Category: bug-fix
Related task: [自测反馈](../../tasks/done/2026-10-15-stratz-followup-and-card-fixes.md)
Related code: [GS桥接](../../../adapters/Dota2UID/src/Dota2UID/host_ai.py.template)、[Provider](../../../packages/dota2forge-core/src/dota2forge_core/infrastructure/_stratz_heroes.py)、[Renderer](../../../packages/dota2forge-renderer/src/dota2forge_renderer/feature_layout.py)
Related docs: [复盘契约](../../../docs/subsystems/native-review.md)、[英雄契约](../../../docs/subsystems/hero-features.md)

## Problem
用户@后只基于短回复复盘，主宰攻略失败并发送空白长页。实际GsCore H14不填AgentHookContext.query，插件却依赖它判主题；原SDK隔离探针手动填query，漏掉真实差异。“这把有什么问题”也未识别。主宰220技能桶中14条ID0被正数校验拒绝，样例升级ID0导致3候选全部失败；共用异常路径连带丢失正常模块。

## Decision
GS在query缺省时读取同一可信event.raw_text，不改@、人格或发送权限。有效定位识别“这把”等相关追问，钉工具并提示先调用get_dota2_review_context取本主题详细事实，沿用比赛/英雄；首答给字段依据与建议，不仅复述结算数字。Astr仅同步共享提示，不发版。

Core AbilityChoice/SkillUpgrade允许来源ID0，保留真实序号/阶数/时刻；称未标识技能，不猜属性点/天赋，不查询常量0。负值/越界仍拒绝。攻略各模块独立校验英雄/位置/周/分母，module_errors新增talents，单项异常不删除正常模块；跨周不伪造日期。

Renderer默认最多2页、详细最多4页，仅发送有内容的模块，缺失状态汇总并提供显式样例指令。每个物品ID选场次最多的时间桶，避免重复条目，不累计不同桶分母或拼购买顺序。长说明按字体宽度换行；强势榜合并相同覆盖位置，保留缺日/固定窗口/延迟。极端越界按既有RenderError回退完整文字。

## Alternatives considered
绕过@或改全局人格违反用户配置；猜ID0属性点制造事实，删除0升级改变顺序；吞掉错误/切源破坏口径；固定4页继续产生空白长图。

## Consequences
公共结构保留，0和talents错误状态明确，双端消费者/序列化/Renderer/桥接一起检查。未发布候选版本沿用，新的运行清单摘要区分修复；用户更新分支后核实激活摘要与重载状态，不能只看a15。缓存/身份/存储/TTL不变，不改宿主配置或发送真实群消息。

## Verification
只读主宰复测764物品桶、220技能桶（14个0）、8天赋桶；3个实际1号位样例升级18/23/24、购买20/23/24，module_errors为空。仅保存公开形状/计数/布尔，无账号/比赛ID/玩家响应。新增禁网回归覆盖ID0/模块独立失败、缺页抑制、H14空query可信事件回退和泛化追问。卡片合成QA、实际SDK边界、最终统一检查/构建/推送见关联任务；SDK合成会话不等于真实模型/QQ递送，用户仍自测。

最终统一入口exit0：2106项禁网测试/401.26秒，覆盖91.01%，独立scripts/Core/Assets94%/90%/92%；Ruff/mypy通过。五包与固定SHA分发隔离消费通过，GS25文件/4wheel摘要一致。修复推送原主仓/GS测试分支，AstrBot不发版，无宿主配置或真实消息修改。
