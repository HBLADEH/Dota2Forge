# 图片交互与历史单局详情计划更新

Status: in_progress

## 目标
将用户提出的图片菜单/查询回复及历史单局详情放入合适的实施顺序，形成可接续的任务和待实施决策。

## 非目标
本轮不实施 Renderer、详情 Provider 或命令，不改变已实现契约和宿主配置。

## 验收
- [ ] 同步项目规划的渲染架构、功能范围、Dota2UID/AstrBot 职责与执行顺序。
- [ ] 图片交互先消费已实现数据；历史详情明确比赛 ID 查询、列表选择、缺失状态与来源。
- [ ] 新增 planned 任务和 proposed 决策，区分方案与现状；事实文档仅链接后续计划。
- [ ] 运行统一离线检查，保留既有代码、配置与未提交工作。

## 影响模块与决策
[项目规划](../../../Dota2Forge_PROJECT_PLAN.md)、[Renderer 任务](2026-10-01-image-interaction.md)、[历史详情任务](2026-10-01-historical-match-detail.md)、[待实施决策](../../notes/proposed/2026-10-01-image-history-interaction.md)。

## 验证证据
已读取根/文档/决策规则、现有模型/端口与执行顺序；当前分支 codex/m0-stratz-dota2uid，开工时工作区干净。此前审阅 StarRailUID 的命令帮助和 Pillow 卡片路径，本轮只承接使用方式，不引入其代码或美术资产。

## 阻塞与下一步
先完成计划编辑和验证；视觉风格、每页条数与细节字段在实现前确认，不影响记录用户已要求的功能。
