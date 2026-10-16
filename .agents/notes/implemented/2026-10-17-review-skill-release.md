# 双端复盘 Skill 公开分发

Category: operations
Related task: [发行](../../tasks/active/2026-10-17-review-skill-release.md)
Related code: [双端适配器](../../../adapters/)、[分发生成器](../../../scripts/build_plugin_distributions.py)
Related docs: [发行指南](../../../docs/cookbook/plugin-release.md)、[复盘用法](../../../docs/cookbook/native-review.md)

## Problem
用户已确认两端均可使用共享复盘指南，明确要求分别整理并发版，随后自行测试。此前 AstrBot 暂不发布的限制已被本次授权替代；源码与 GsCore 测试分支尚未形成这轮公开发行。

## Decision
沿用现有未公开版本 Dota2UID a16／AstrBot alpha.14，锁定 Core a9、Renderer a8、Assets a1。整理各自 README、AstrBot CHANGELOG、安装步骤与 Skill 使用方式，通过源码 PR 和 CI 固定提交后生成两端分发。Assets a1 复用既有公开 wheel/sdist 原字节；新版本固定摘要，不覆盖旧发行。

每端先准备完整 draft 附件并校验，再发布预发行；公开后匿名下载仓库、ZIP 与全部附件核对。GsCore 注册原生 Skill 并随工具附带指南，AstrBot 通过工具消费同一指南；不将两端接入方式写成完全相同。Cloud 发布状态另行实查并记录，不能把 GitHub Release 当商店审核通过。

## Alternatives considered
只推测试分支无法提供公开依赖和固定安装版本；只更新入口会混用旧 Core／Renderer。覆盖旧版附件会破坏已安装清单摘要，因此保留既有标签和发行。直接部署或发送测试聊天不属于本次用户后续自测安排。

## Consequences
这次公开包含强势英雄、攻略图标／中文天赋和共享 Skill；真实模型效果与 AstrBot 平台多轮仍待用户测试。建议两端备份后冷启动，AstrBot 需用实际宿主 Python 更新四组件。来源及事件缺口仍明确保留，不改变 Provider／存储／权限契约，也不修改宿主配置或运行实例。

## Verification
开工确认 GitHub 默认分支、既有 PR／标签／Release，目标 a16／alpha.14 尚未公开，前轮推送 CI 均成功。完整本轮检查、候选和公开下载证据见[发行记录](../../artifacts/review-skill-release-20261017/README.md)，未完成项按真实结果接续。
