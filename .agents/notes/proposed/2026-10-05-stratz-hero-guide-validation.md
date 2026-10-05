# STRATZ分位置英雄攻略可行性

Category: feature
Related task: [验证任务](../../tasks/done/2026-10-05-hero-builds-stratz-validation.md)
Related code: [已有HTTP边界](../../../packages/dota2forge-core/src/dota2forge_core/infrastructure/_stratz_http.py)
Related docs: [来源与方案](../../../docs/cookbook/hero-guides.md)

## Problem
此前[来源调研](2026-10-05-hero-guide-source.md)未使用Token验证攻略接口。用户现已授权显式验证，需证明英雄/位置出装、加点、天赋、版本和样本可得，并识别字段缺口及查询限制；不得因玩家Provider成功就宣称攻略可用。

## Decision
2026-10-05使用本机既有Token，仅查询英雄1/POSITION_1与英雄2/POSITION_3及公开schema/constants；不选账号或比赛ID，不落盘凭据/原始账号响应。聚合itemFullPurchase、talent、abilityMinLevel均成功。直接guide.itemIds为null，但缩小详情查询后，guide.matchPlayer返回正确英雄/位置、17/19条加点、2/4条天赋和20/24条带time的购买事件；guide组matchCount为3374/5226，不能直接当成每个聚合桶的分母。样本gameVersionId=190，经constants映射为7.41f。

建议首版独立GuideProvider：按英雄/位置提供构筑统计及少量高手比赛样例，使用matchPlayer.stats.itemPurchases还原购买事件、abilities展示加点/天赋；保留聚合与单场口径区别、样本时间/版本及来源。缺项/旧版/限流明确显示；内容称数据攻略或构筑参考，不编教学文字，不直接使用null itemIds。用户要求先验证，本轮不注册do…攻略；本note保持proposed。

## Alternatives considered
- 直接取guide.itemIds：两个样本null，不能作为稳定出装入口。
- 一次嵌套所有match.players.abilities：复杂度748062超过310000，减少take仍未降低该查询计价；改为目标matchPlayer及必要字段的小查询。
- OpenDota做完整攻略：只有四阶段购买统计，已作为独立出装功能，不能补出技能/天赋。
- Spectral/D2PT：保留原调研的许可/更新与403限制；本轮STRATZ已具备可实施数据路径，无需换源。

## Consequences
小样本成功证明技术可行，不证明长期稳定、所有英雄/位置或所有字段完整。默认week/段位窗口、分页覆盖、未来补丁/限流口径仍需在实现时确定。不能将组matchCount、购买事件行数、聚合计数混作总样本或胜率；技能升级时间不是教学推荐。若未来加缓存，应按来源/英雄/位置/版本隔离，TTL/过期/重试单独决策。

## Verification
[schema](../../artifacts/hero-builds-v1/stratz-schema.json)、[聚合摘要](../../artifacts/hero-builds-v1/stratz-validation.json)、[详情复核](../../artifacts/hero-builds-v1/guide-details.json)、[版本映射](../../artifacts/hero-builds-v1/game-version.json)、[复杂度拒绝](../../artifacts/hero-builds-v1/guide-details-complexity.json)。初次摘要仅记0/字段存在，不能区分null与空；后续按状态复核为准。客户端关闭已验证；未验证长期可用性、上线、真实聊天或完整攻略输出。
