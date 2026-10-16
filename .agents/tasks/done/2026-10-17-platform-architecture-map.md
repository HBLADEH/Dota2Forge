# GsCore / AstrBot 当前架构图

Status: done

## 目标

根据当前文档、有效决策和源码绘制新人可读的 Dota2Forge 架构图，说明两端适配、查询返回、订阅与原生复盘交互，并在聊天中展示。

用户补充要求手绘、简单易懂，因此用手绘简图作为默认展示，详细结构/时序保留为接续参考。

## 非目标

不改变架构、公共契约、业务实现、部署或发布状态；不访问真实聊天和凭据。

## 验收

- 总览区分宿主、独立适配器、共享 Core、Renderer、Assets 和外部服务。
- 说明可信身份转换、依赖注入、结果发送及生命周期归属。
- 标注源码实现与真实联调的边界；保留可维护的 Mermaid 图和入口链接。
- 按开发指南运行统一离线检查并记录真实结果。

## 影响模块与决策

- [架构](../../../docs/architecture.md)、[GsCore](../../../docs/subsystems/gscore-host.md)、[AstrBot](../../../docs/subsystems/astrbot-host.md)。
- [共享核心决策](../../notes/implemented/2026-09-30-workspace-foundation.md)、[双端消费](../../notes/implemented/2026-10-01-astrbot-shared-consumer.md)、[原生复盘](../../notes/implemented/2026-10-16-review-skill.md)。
- 仅整理现有架构事实，不新增架构决策；保留开工时已有的未跟踪产物与任务。

## 验证证据

- 已交付[手绘速览与三张 Mermaid 图](../../../docs/subsystems/platform-adapters.md)，README 和架构入口已链接；纠正 README 中开发候选攻略/AI Tool 仍未实现的旧说明。
- 核对两端发现模板、Runtime 组合、可信身份、Core 端口、原生会话和已实施决策；区分独立插件与 AstrBot→GsCore 宿主转发。
- 内置 image_gen 生成手绘图并定向补上 Renderer 两端共用；图片/汉字/连线已核对，生成提示词及 Mermaid 11.12.0 解析/渲染证据见[验证记录](../../artifacts/platform-architecture-20261017/README.md)。
- `uv run --locked python scripts/check_governance.py --all` 退出0：治理、Ruff、mypy、pytest（收集2150项）、三个独立覆盖率门槛通过。图文最终调整另以原 `check_repository(ROOT)` 复核，`git diff --check` 通过。
- 未运行宿主或模型、未发送消息；AstrBot完整多轮/隔离/过期/重载及新订阅卡真实递送仍未完整验收。死亡/团战/视野/录像事件仍未接入，部署整合未实现。

## 阻塞与下一步

本次绘图已完成，无阻塞；后续架构变化同步维护简图和详细时序，实机验证沿用各自 active 任务。保留其他任务既有与并发修改。
