# 比赛宽幅详情与 STRATZ IMP

Status: in_progress

## 目标
按用户参考截图重做比赛报告：空装备槽置空，宽幅详尽展示有分析价值的数据，使用用户选择的 STRATZ IMP 列出表现突出与偏弱者及统计依据。

## 非目标
复刻 STRATZ 页面、推断不存在的地图/回放数据、把 IMP 变为官方评分或自造分数，以及未经本任务授权的生产部署。

## 验收
- 0/null装备槽图片均无占位文字，模型仍区分无装备与未提供，页脚说明空白语义；正ID缺图保留名称/ID。
- 全十人总览、分队详细指标与装备、已有经济序列、评分与依据均进入双端图片和文本回退。
- 新字段经 schema 与指定比赛只读核查，保留来源、缺失与解析状态；匿名玩家不恢复身份。
- 合成禁网回归、统一离线检查及宽图视觉检查通过，不以手机固定比例删减信息。

## 影响模块与决策
[Core](../../../docs/subsystems/core.md)、[分析契约](../../../docs/subsystems/analysis.md)、[Renderer](../../../docs/subsystems/renderer.md)、两个适配器和订阅JSON。对先前 IMP 未实现边界另立决策，来源口径仍明确。

## 验证证据
开工 main=103733b，保留用户两个未跟踪商店任务；复用已附独立工作区，分支 codex/match-analysis-report。用户明确选择 STRATZ IMP 加统计依据。截图只作布局参考，含其他玩家身份，不保存到仓库或作为测试fixture。

新字段内省和指定比赛只读核对通过：十个IMP与截图一致，两条优势各41样本。系统DNS/证书异常时显式诊断连接公共DNS核对的IP，Host/SNI/TLS仍为原api.stratz.com；生产Provider未改。[脱敏证据](../../artifacts/match-analysis-report-v1/README.md)。三图1600×2990/2870/2870，每张不超过2MiB，已视觉检查；参赛身份全部移除后才保存。

统一禁网检查1985项通过/288.12s，聚合92.61%；scripts/Core/Assets各自超过80%，Ruff和mypy85源文件通过。[检查日志](../../artifacts/match-analysis-report-v1/offline-check.log)。专项覆盖STRATZ字段/排名/序列、旧订阅记录兼容、缺失统计、双端图片与文本、宽图和长回复分段。五包构建、双端发行smoke及五wheel离线安装导入通过。版本元数据专项110项及更新后的发行测试通过。

## 阻塞与下一步
主仓PR #10已合并提交 `7e650a2fb9a2db9c242c260a7d72ac11424c1989`，Python3.12/3.13 CI成功。Dota2UID PR #2/#3已合并提交 `129e8e67fb8582f14d28e12d71ace769bbe196de` / `cfce3fa66b22ec843e64f9b60d5196bf360d75f2`。[v0.1.0a9 Release](https://github.com/HBLADEH/Dota2UID/releases/tag/v0.1.0a9)已发布：11项资产匿名下载和SHA256、仓库ZIP及18个文件与候选匹配，Assets a1沿用原公开字节。[匿名校验摘要](../../artifacts/match-analysis-report-v1/public-validation.json)、[manifest](../../artifacts/match-analysis-report-v1/release-assets.json)、[SHA256SUMS](../../artifacts/match-analysis-report-v1/SHA256SUMS)。

用户接下来停用旧实例、更新Dota2UID并完整冷启动，用 `do核心状态` 确认Core a6/Renderer a5/Dota2UID a9，再执行 `do比赛 9035146588`。真实QQ图片压缩/顺序/数量和宿主配置保留待用户反馈；未反馈前不宣称真机通过。本次没有操作生产宿主，也未发布AstrBot a9。
