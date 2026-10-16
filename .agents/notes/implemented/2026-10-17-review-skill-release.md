# 双端复盘 Skill 公开分发

Category: operations
Related task: [发行](../../tasks/done/2026-10-17-review-skill-release.md)
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
源码PR #23／四项CI和本地统一2150项禁网检查通过，覆盖91.11%；五包与双端隔离消费通过。GS a16／Astr alpha.14已公开，main／tag及每端11附件与候选一致，旧版保留。匿名API限流时仅元数据使用已登录API，仓库及附件仍匿名下载，不放宽字节／摘要断言。

Cloud原市场单次更新提交后，只读解析确认当前版本alpha.14；新版本行与审核结论尚未可见，状态记未知，不重复提交或冒充上架。完整检查、截图、失败原件和公开下载证据见[发行记录](../../artifacts/review-skill-release-20261017/README.md)。其他正在编辑的架构／README工作保留，不混入本轮交付。
