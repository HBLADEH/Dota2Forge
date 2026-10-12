# 订阅比赛卡合成验收

使用合成账号 2000–2009、比赛 7001 和合成事件 ID；未保存用户提供的账号、比赛、事件或聊天记录。运行 `uv run --locked python .agents/artifacts/subscription-match-cards-v1/preview.py` 复现，无网络、平台 SDK、订阅库或真实凭据。

本轮预览故意不给 IMP、优势曲线或额外分析序列，验证已有订阅快照只有基础统计时依然能生成卡片，并保留非官方表现候选、明确未知字段和来源为空的计数。生产资源缺图使用问号，不推断英雄或装备。

- [比赛总览](report-1.png)：十人对比、结果和时长、订阅玩家、表现候选与来源边界。
- [天辉详情](report-2.png)、[夜魇详情](report-3.png)：五人完整指标、六装备／三背包／中立槽，订阅玩家高亮。
- [780px 总览预览](overview-780.png)、[完整文本回退](fallback.txt)、[尺寸与文本边界](qa.json)。

PillowRenderer 的文字边框检查同时验证无越界／重叠；PNG 均不超过 3200px 高和 2MiB，文本各段不超过 1400 字符。人工布局检查及离线检查结果由本轮任务记录。尚未验证 QQ 压缩、真实订阅图片递送或真实宿主生命周期。

最终[统一离线检查](offline-check.log)2054项禁网测试通过，聚合93.08%，治理工具/Core/Assets独立覆盖率94%/93%/92%，Ruff、mypy87源文件及治理预算/链接通过。[五包构建](build.log)和[隔离安装/导入](wheel-smoke.log)通过；开发版本Renderer a7、UID a14、Astr a12，不发布或覆盖旧公开产物。首轮源码检查另留[升级版本前日志](offline-before-version.log)。

源文件与合成产物扫描未发现用户提供的主账号/比赛/事件样本；已有未跟踪任务文件保留。完成记录见[任务](../../tasks/done/2026-10-12-subscription-match-cards.md)，设计原因见[决策](../../notes/implemented/2026-10-12-subscription-match-cards.md)。
