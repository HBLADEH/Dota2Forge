# 英雄攻略源调研（尚未实现）

2026-10-05首次公开调研未使用凭据，见[匿名摘要](../../.agents/artifacts/command-mmr-guide-v1/source-probes.json)。随后用户授权验证STRATZ，使用本机已有Token仅查公开英雄/schema/constants，不选账号/比赛ID、不落盘凭据。攻略命令仍未注册；一次成功不证明长期稳定。

| 来源 | 已核实能力 | 获取与局限 | 结论 |
| --- | --- | --- | --- |
| [Dota2ProTracker](https://dota2protracker.com/hero/Anti-Mage) | 页面有按位置的出装、技能、天赋及统计；当前页面标7.41f | /api/heroes/list与/api/hero/1/builds?position=pos%201本机均403；未核实公开接口兼容承诺或内容再发布许可 | 内容合适，但本轮不作为生产主源；可返回原页面链接 |
| [Spectral/Nerds仓库](https://github.com/leamare/nerds-builds) | .build含英雄/位置、出装/加点、说明及GameplayVersion/TimeUpdated | GitHub目录、样本和许可200；123个文件不等于123英雄/全覆盖；最近commit为2026-08-09，抽样敌法辅助版本7.41e。许可为[CC BY-NC-SA 3.0](https://github.com/leamare/nerds-builds/blob/master/LICENSE.md)，非商业/署名/相同方式共享 | 可做离线攻略原型，须按英雄位置筛选及标注过期；不保证随补丁及时更新 |
| [STRATZ](https://stratz.com/api) | 已验证heroStats.guide、itemFullPurchase、talent、abilityMinLevel；两英雄/对应位置返回技能、天赋、购买事件和7.41f样本 | 直接itemIds为null；须取matchPlayer.stats.itemPurchases。全体玩家加点嵌套查询超复杂度限制，应缩小/拆查询；无教学文字与长期稳定保证 | 技术可行，建议作为首版构筑统计/高手样例主源 |
| [OpenDota](https://docs.opendota.com/) | 两英雄itemPopularity均成功返回四阶段物品计数，后续补查出现不可用 | 不含技能顺序、教学文字或位置/当前补丁保证；热门不等于最优 | [独立热门出装功能已实现](hero-items.md)，不称完整攻略 |

STRATZ实测敌法师/POSITION_1、斧王/POSITION_3：聚合购买行数508/711，天赋9/9，加点185/195；这些是行数，不是比赛总数。每英雄详情取一局，分别17/19条加点、2/4条天赋、20/24条带时间购买事件，英雄/位置匹配。guide组matchCount为3374/5226，不能当所有聚合分母。两个样本gameVersionId=190，经constants.gameVersion映射为7.41f；创建时间、比赛时间和版本可得。初次摘要只记0/字段存在，最终[字段状态复核](../../.agents/artifacts/hero-builds-v1/guide-details.json)证明确有可用数据。

查询路径：heroStats.guide按heroId/positionId筛选，guides取少量目标matchPlayer的abilities与stats.itemPurchases；聚合查询独立按positionIds获取。嵌套match.players.abilities复杂度748062超过310000，减少take未改变计价；缩为目标matchPlayer后成功。完整schema、聚合、版本和拒绝证据见[验证记录](../../.agents/notes/proposed/2026-10-05-stratz-hero-guide-validation.md)。尚未确认默认week/段位窗口、分页覆盖、全部英雄/位置和长期限流策略。

首版攻略仍属方案：复用已实现的Core英雄解析，STRATZ提供分位置构筑统计及少量高手比赛样例。输出英雄、位置、补丁/更新时间、购买事件、加点/天赋、各自样本口径和来源；保留统计与单场区别，缺项/旧版明确提示，不编教学文字。主位置及可选位置需明确，不将辅助敌法误作核心攻略。

适配器仅识别 do…攻略 并转换可信身份/发送；Core增加独立GuideProvider与不可变结果，HTTP在基础设施；Renderer不联网。缓存按来源/英雄/位置/版本隔离，过期与获取失败区分、无静默换源。验证需覆盖别名歧义、位置、补丁过期、无攻略、403/限流、双端消费及图片/文本；实现和缓存策略须另建任务/note。

原选择原因见[调研记录](../../.agents/notes/proposed/2026-10-05-hero-guide-source.md)，后续STRATZ验证保持proposed，用户决定实施后另建攻略任务。
