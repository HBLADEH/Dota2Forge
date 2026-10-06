# 英雄出装与STRATZ攻略验证证据

2026-10-05。攻略只做可行性验证，出装已实现双端源码；未发布/重启宿主或发送聊天消息。图中所有次数为合成fixture，来源明确为FIXTURE，不能视作实际比赛数据。

## STRATZ（显式真实API）

- stratz-schema.json：root及12个类型的公开schema，无Token/账号数据。
- stratz-validation.json：两个固定英雄/位置的聚合行数；初次详情摘要仅记0与存在性，最终字段状态以guide-details.json为准。
- guide-details.json：最终两个样本的字段状态、行数及公开版本ID；直接itemIds=null，matchPlayer加点/天赋及stats.itemPurchases可用，英雄/位置匹配。不保存账号、比赛ID或原始响应。
- game-version.json：constants将190映射到7.41f。
- guide-details-complexity.json：全体玩家加点嵌套查询被复杂度限制拒绝，748062>310000。缩为目标matchPlayer字段后成功。

复核使用仓库已有HTTP边界，Token仅通过uv显式注入；普通离线检查不读取.env：

```sh
uv run --env-file .env --locked python .agents/artifacts/hero-builds-v1/verify_stratz.py
uv run --env-file .env --locked python .agents/artifacts/hero-builds-v1/verify_guide_details.py --stratz-only
```

## OpenDota（显式匿名API）

opendota-validation.json记录两个英雄归一化成功的四阶段项数、抓取时间、未知观测时间和客户端关闭；后续详情补查同时访问OpenDota时返回UNAVAILABLE，未重试或转成功。初次成功不保证长期可用。verify_guide_details.py省略--stratz-only时也探测OpenDota，错误独立记录。

## 离线、构建及合成图

offline-check.log、build.log、wheel-smoke.log记录统一检查、四包构建和无索引隔离安装导入。render-qa.json及items-full/items-partial/menu/menu-admin PNG由render_qa.py生成，含390px手机预览；所有文字边界在画布内，1530/1450/1580px均低于1600px。已人工查看出装与管理员菜单，无裁切；未知ID、0、来源时间和提示可读。

首次完整检查1332通过/1失败：旧日志隐私测试用短账号123，合法image_bytes=71233误命中。改为有效合成长账号987654321，并保留原完整身份/账号不出现的断言；未删断言、接受快照或改门槛。后续真实统一检查结果见日志和[任务](../../tasks/done/2026-10-05-hero-builds-stratz-validation.md)。
