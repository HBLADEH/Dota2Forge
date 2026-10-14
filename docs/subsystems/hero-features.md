# 版本强势与STRATZ攻略

M0开发候选已实现；Core/Renderer最低0.1.0a8，Dota2UID候选a15、AstrBot候选a13。当前公开发行链接仍指向此前版本；本轮未发布或部署。

## 共享契约
`HeroMetaProvider.get_hero_meta(MetaRequest)`返回不可变`HeroMetaSnapshot`，包含来源/抓取/观测时间、真实补丁、请求筛选、UTC窗口、逐日英雄/位置胜场和场次、缺日说明。`HeroFeatureService`校验身份和来源，以累计胜场/累计场次归并，禁止均值拼接和重复桶。默认近7日、天梯全选、全球全部段位；位置1–5各前2，指定位置前10、每页5。可选14日与RankBracket、原始胜率排序；不能证明的选用率不展示。

可靠度使用Wilson双侧95%下界，z=1.96；最低1000场，小样本留在观察计数，不进入正式榜。窗口为当前生效版本和完整UTC日的交集；版本切换不完整日排除。没有场次不补零，不为上游延迟平移请求窗口，显示最后可用日和缺日；当前成功探针也存在延迟，不保证任何时刻完整。

`HeroGuideProvider`提供`HeroGuide`与独立`GuideSample`。聚合itemFullPurchase、abilityMinLevel、talent各桶保留自己的matchCount/winCount、原始周索引；周索引不伪装为epoch/日期，也不把guide组matchCount当整套推荐分母。来源位置标记不一致时，items/abilities/talents为None，`module_errors`明确scope_mismatch；已知空元组与未返回None可区分。

guide目标matchPlayer当前为null，故临时读取候选比赛/账号ID后，以独立match.players筛选并校验实际hero/position/account；不把传入的位置当已经生效的口径。嵌套ability解析遭拒，中文名由constants.ability按本场gameVersionId/S_CHINESE独立查询，失败以label_error保留。样例含单场补丁、时间、阵营/KDA/IMP、升级和购买事件及来源装备槽；序列不构造“最佳加点”。匿名/账号缺失时允许终局快照，升级与购买为None，不猜身份。

## 展示与边界
`HeroMetaCard`、`HeroGuideCard`、`GuideSampleCard`使用共享Forge主题和同源文字回退。攻略默认2页、详细4页；样例2页，升级最多24条的四列网格、购买最多32条，标明显示/总条数。升级序号不是英雄等级，源level是从0起的技能阶数。赛前负购买时间、重复与组件保留；最终6装备/3背包/中立槽为来源快照，不回放任意时刻库存。缺图使用名字/ID/空槽占位，技能名不会猜测，未接入技能官方栅格素材。

普通攻略统计与OpenDota职业`do出装`独立，不互补来源、不伪称同版本。单場样例不代表最优选择或因果。技能天赋、命石、详细中立获取、任意等级/库存回放仍按核查范围声明，不因schema存在即承诺支持。

## Provider与生命周期
共用原StratzProvider/HTTP/配额锁，固定受限GraphQL，无自动重试/切源/录像解析POST。缓存为有界进程内观察：版本/榜单30分钟、攻略/中文名6小时、样例1小时；最多128项，版本表1项，同key合并、至多16个在途key、最后等待者取消即排空。关闭释放缓存与在途任务，client仍由适配器所有。无SQL迁移。来源响应与错误不写身份日志，AI输出删除账号/昵称。见[原生复盘](native-review.md)、[实施决策](../../.agents/notes/implemented/2026-10-14-stratz-hero-and-native-review.md)。
