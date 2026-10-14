# STRATZ 强势英雄、英雄攻略与 AI 复盘需求规划

Status: done

## 目标
阅读当前架构、已实现消费者及有效决策，核对 STRATZ 与用户指定的参考项目，形成三项功能的指令、卡片、数据边界、分期与可执行验收方案。

## 非目标
本轮不实现业务、不注册命令/AI 工具、不发布或部署、不发送平台消息；不把历史探测结果当成当前版本统计。

## 验收
- 区分已有能力、历史核实和待验证字段。
- 两端共享业务与 Renderer；卡片延续远古锻炉主题。
- 规划明确样本/版本/位置口径、缺失与失败、AI 证据与推断。
- 列出实现任务和首版范围，按开发指南运行统一离线检查。

## 影响模块与决策
- [完整需求规划](../../../Dota2Forge_STRATZ_FEATURE_PLAN.md)
- [规划取舍](../../notes/proposed/2026-10-14-stratz-feature-scope.md)
- [架构](../../../docs/architecture.md)
- [英雄攻略源调研](../../../docs/cookbook/hero-guides.md)
- [分析契约](../../../docs/subsystems/analysis.md)
- [Renderer 契约](../../../docs/subsystems/renderer.md)

## 验证证据
开工工作区已有两份未跟踪的 GsCore 商店 PR 历史任务，保留原状。核查当前契约/源码、有效主题决策、历史攻略/分析证据、公开参考项目/许可与AstrBot工具文档；本机GsCoreSDK与接入手册的特权分类差异以源码为准。本轮未用Token，用户指定攻略页标题可读、正文先后出现客户端/请求错误，不宣称完整页面核验。

交付主规划、proposed note和四项planned任务，仅在两份cookbook加入规划导航。使用实际共享Canvas/theme制作三张780×1680卡片、390px预览与总览，所有内容合成、无Valve位图/账号/昵称；[尺寸/文字QA](../../artifacts/stratz-feature-plan-v1/qa.json)与人工阅读通过，每张约0.2MiB。[说明与复现](../../artifacts/stratz-feature-plan-v1/README.md)。预览脚本首轮lint发现未使用导入/嵌套with等，修正及格式化后专项Ruff通过。

`uv run --locked python scripts/check_governance.py --all` exit0：Python3.12.9，2054项禁网测试通过/444.15s，聚合覆盖93.06%；scripts/Core/Assets独立报告94%/93%/92%，均满足80%门槛。Ruff格式/lint、mypy87源码文件与治理通过。[完整日志](../../artifacts/stratz-feature-plan-v1/offline-check.log)。本轮无运行源码/包配置变更，不需要构建发行物；[归档后治理复核](../../artifacts/stratz-feature-plan-v1/governance-final.log)、预览脚本Ruff格式/lint及git diff --check均通过。

## 阻塞与下一步
规划已完成。依次接续[字段口径核查](../done/2026-10-14-stratz-data-readiness.md)、[强势榜](../done/2026-10-14-hero-meta.md)、[攻略](../done/2026-10-14-stratz-hero-guides.md)与[AI复盘](../done/2026-10-14-ai-match-review.md)。当前统计覆盖、命石/技能素材、详细事件、双端AI/模型/真实卡片递送仍待实施与联调；没有注册命令/工具、部署发布、修改真实配置或发送消息。
