# 英雄攻略来源与实施前验证

Category: data
Related task: [调研任务](../../tasks/done/2026-10-05-command-mmr-guide-survey.md)
Related code: [现有Provider边界](../../../packages/dota2forge-core/src/dota2forge_core/ports.py)
Related docs: [调研和拟定方案](../../../docs/cookbook/hero-guides.md)

## Problem
用户要求先找到稳定来源，再决定是否实施do[英雄名或简称]攻略。攻略需要明确位置/版本/更新时间、出装/加点及使用权限；成功访问网页或现有战绩Provider不能代替攻略API验证。

## Decision
仅提出优先验证STRATZ攻略/构筑schema与小样本的方案，尚未选定或实现GuideProvider。独立读取两个英雄/位置，确认字段、版本、样本口径与缺失/限流；通过后再由用户选择完整首版。Hero aliases/位置/过期状态在Core，HTTP在基础设施，双端共用；不按失败静默切源。

## Alternatives considered
- Dota2ProTracker：页面内容与需求匹配，但本机两个JSON请求403，未验证兼容和再发布许可；暂不生产接入。
- Spectral/Nerds公开.build：访问200、可版本固定；抽样7.41e、最近更新8月9日，CC BY-NC-SA 3.0且位置需筛选；可在接受许可/旧版提示后做原型。
- OpenDota itemPopularity：已获取四阶段物品计数，仅职业样本热门出装，无完整加点/教学；若接受范围缩小可做独立参考。
- 直接发源站链接：无需抓取攻略正文，但未满足在聊天完整展示攻略信息；作为较小方案单独选择。

## Consequences
本轮不出现攻略菜单或命令，不把方案描述为实现。STRATZ仍有字段/额度/许可待验证，不能承诺一定能提供完整构筑。若实施，另建任务/公共契约/note，并按来源显示缺失、版本/更新时间和缓存状态；中文名称/简称须审核，歧义不猜。商业分发前Spectral非商业条件必须满足，不能将第三方文本并入MIT授权。

## Verification
公开页面、官方接口文档与匿名HTTP结构证据见[获取摘要](../../artifacts/command-mmr-guide-v1/source-probes.json)。D2PT403；Spectral目录/许可/抽样200；OpenDota出装200。未使用真实Token或查询玩家，未长期观察、验证攻略GraphQL、解析全英雄或跑宿主聊天流程。

后续用户授权显式验证，STRATZ已取得两英雄/位置的购买事件、加点/天赋及7.41f样本，详见[新验证方案](2026-10-05-stratz-hero-guide-validation.md)。OpenDota已作为独立[出装功能](../implemented/2026-10-05-opendota-hero-items.md)落地；本调研保留原阶段证据，完整攻略仍未实现。
