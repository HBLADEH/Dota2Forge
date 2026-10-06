# 共享英雄解析与OpenDota热门出装

Category: feature
Related task: [任务](../../tasks/done/2026-10-05-hero-builds-stratz-validation.md)
Related code: [用例](../../../packages/dota2forge-core/src/dota2forge_core/hero_items.py)、[Provider](../../../packages/dota2forge-core/src/dota2forge_core/infrastructure/opendota.py)、[卡片](../../../packages/dota2forge-renderer/src/dota2forge_renderer/engine.py)
Related docs: [契约](../../../docs/subsystems/hero-items.md)、[使用](../../../docs/cookbook/hero-items.md)

## Problem
用户要求验证STRATZ攻略，并将OpenDota出装统计独立提供为do[英雄名或简写]出装。原查询只接受账号/比赛ID；需要两个适配器消费同一英雄解析、来源和缺失契约，不查询玩家或将统计误称攻略。

## Decision
Core增加独立HeroItemProvider/HeroItemService及不可变四阶段结果；业务解析留在Core，官方127英雄中英名和审核简称本地加载，歧义返回候选。OpenDota匿名itemPopularity使用既有HTTP边界，一次请求、无缓存/重试/换源；来源、抓取时间、缺失、空和0严格保留。新增公共契约逐一接入Dota2UID和AstrApplication/Runtime，并维护宿主桥接及菜单。

每阶段展示次数前5项；Renderer本地544物品名称仅作事实标识，未知ID保留，文字/图片共享语义。图片1530px及现有菜单均在1600px上限内，RenderError只回退同次结果，不增加请求。STRATZ只读验证另记[后续方案](../proposed/2026-10-05-stratz-hero-guide-validation.md)，攻略命令未实现。

## Alternatives considered
- 双端各维护别名/请求：会产生业务漂移，改用共享核心。
- 模糊猜英雄或保留单一“猴子”：不采用，可能查询错误英雄。
- 将购买次数除以猜测样本数或推断当前补丁/位置：接口不提供这些证据，明确未知。
- 失败回退STRATZ或缓存旧结果：本次未选择，保持来源/失败清晰；未来须独立策略和note。

## Consequences
新增两个包内JSON事实资源，无图像再分发；请求共享客户端但OpenDota剥离认证/默认参数，不泄漏STRATZ Token。运行期仍要求原有宿主配置，出装不要求玩家绑定。API默认口径与可用性有外部变化风险，别名表需人工维护。没有数据库/权限变更，也没有宿主发布、重启或消息发送。

## Verification
实际英雄1/2请求通过归一化并返回四阶段；后续UNAVAILABLE如实记录。禁网覆盖别名/歧义、数据0/空/缺失/非法、认证隔离、一次请求、限流/失败、双端渲染/文字回退、桥接捕获和关闭。完整统一检查与构建结果补在关联任务，不将源码测试当成宿主联调。

统一检查1333项通过，Ruff/mypy、聚合92.99%及scripts/Core独立门槛通过；四包构建/无索引隔离安装与新JSON资源消费成功。4张合成图和390px预览文字边界合格，出装/管理员菜单人工查看无裁切。隐私测试短ID与合法图片字节数偶然重合，改合成长ID保留断言；未放宽门槛。运行宿主和真实聊天未升级/验证。
