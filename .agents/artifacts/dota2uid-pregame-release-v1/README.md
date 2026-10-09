# Dota2UID a8 赛前购买时间修复发行

本次依据用户2026-10-09“直推送合并，然后真机更新测试”的授权，准备 Core a5/Dota2UID a8 随包发行。用户负责生产插件更新、冷启动和 QQ 指令测试，本任务不操作生产宿主。

前置[修复证据](../stratz-match-detail-response-v1/README.md)确认指定比赛235条购买事件中48条为赛前负时间，旧代码拒绝正常数据。修复完整保留时间，双端消费及订阅重开禁网回归通过。

正式分发仅携带新 Core a5、Dota2UID a8 与旧公开 Renderer a4、Assets a1。主仓 PR #9 合并为 `33e97e2f27feb46ddb01cd55e09ee9298e7cfef4`，分发仓 PR #1 合并为 `c11c8d40ad5cb3e57a119f9edea9ff58371722f0`；[v0.1.0a8 Release](https://github.com/HBLADEH/Dota2UID/releases/tag/v0.1.0a8) 的 11 个资产已匿名下载校验，仓库 ZIP 和公开文件与候选一致。证据见[公开摘要](public-validation.json)、[资产清单](release-assets.json)与[发行任务](../../tasks/active/2026-10-09-stratz-purchase-release.md)。不替换旧 Release。
