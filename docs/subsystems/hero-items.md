# 英雄热门出装契约

Core新增HeroItemProvider、HeroItemService和不可变HeroItemStatistics；服务先解析英雄，再检查Provider结果的类型、英雄和来源。无需玩家账号、绑定或近期比赛；取消和程序错误传播。双端使用同一服务，平台事件/正则/发送留在适配器。

HeroCatalog按官方中文/英文名、内部名及审核简称精确匹配；忽略大小写、空格、下划线和连字符，输入最多64字符且拒绝控制字符。未知名称返回未识别；“猴子”“ES”“SK”等歧义返回候选，不模糊猜测。127英雄名称来自[Valve列表](https://www.dota2.com/datafeed/herolist?language=schinese)，英文表于2026-10-05核对；资源只在显式启动时本地加载，不依赖Renderer或联网刷新。

OpenDotaProvider匿名GET `/heroes/{hero_id}/itemPopularity`，共用既有HTTP生命周期、超时、限流和错误分类。请求剥离客户端Authorization/Cookie/代理认证及默认查询参数；不转发STRATZ Token、不跟随重定向、不重试/缓存/换源。上游失败保留ProviderError，不能解释为无出装。

结果按出门/前期/中期/后期四阶段排列，各自包含不可变物品ID/非负整数计数。bool、浮点、负数、非规范ID、重复物品、每阶段超过2048项或全部阶段缺失均拒绝为INVALID_RESPONSE。缺失/null阶段为None，空对象为有效空tuple，0为实际计数；missing_fields只列未知阶段。总样本数、位置、补丁、统计窗口与观测时间未由此接口提供，均不推断；fetched_at仅代表抓取时间。

两端注册do[英雄名或简称]出装与do出装 英雄名，每阶段按次数降序/同次数按ID列前5项。中文物品名来自本地Valve事实表，未知物品保留ID；不把职业比赛购买次数称为出场率、胜率、最优出装或购买顺序。共享HeroItemsCard为780×1674 PNG，英雄头像与四阶段各五件装备图按本地ID对应，名称可两行，长名采用审核简称，文本回复保留全名；缺图占位且保留名称/未知ID。RenderError回退同次成功结果文字，不重新请求Provider。

STRATZ英雄攻略仅完成[来源验证](../cookbook/hero-guides.md)，未新增GuideProvider或攻略命令。此出装功能已接入两个库运行时及桥接模板，普通禁网测试消费同一契约；本轮未部署宿主或验证真实聊天。使用与联调证据见[步骤](../cookbook/hero-items.md)，原因见[决策](../../.agents/notes/implemented/2026-10-05-opendota-hero-items.md)。
