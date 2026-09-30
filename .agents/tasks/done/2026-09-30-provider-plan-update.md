# 数据源选型计划同步

Status: done

## 目标
落实用户确认的 STRATZ 主源、OpenDota 补充与交叉核验、Valve 按需补充的计划，记录当前段位确认并同步后续验收。

## 非目标
不实现联网 Provider、缓存、自动回退或宿主命令；不更改治理门禁，不使用真实凭据或发送消息。

## 验收
- [x] 总规划明确数据源职责、接入顺序、段位与估算分数语义。
- [x] 新增待实施决策与 STRATZ 接入任务，同步 Core、Dota2UID 和事实文档。
- [x] 记录用户确认本次 STRATZ 段位为当前值，不推广为全站时效保证。
- [x] 统一离线检查通过，保留工作区已有修改。

## 影响模块与决策
[项目规划](../../../Dota2Forge_PROJECT_PLAN.md)、[Core 契约](../../../docs/subsystems/core.md)、[评测](2026-09-30-stratz-evaluation.md)、[待实施决策](../../notes/implemented/2026-09-30-provider-selection.md)、[接入任务](../done/2026-09-30-stratz-provider.md)。决策实现后再迁移状态。

## 验证证据
已检查工作区，读取根/文档/决策规则、有效契约及相关任务；现有业务与治理修改全部保留。
2026-09-30：`uv run --locked python scripts/check_governance.py --all` 通过，包含治理/文档链接与预算、Ruff 格式和 lint、mypy（15 个源文件）、pytest（251 passed）；Core 覆盖率 100%，治理工具 98%（报告取整）。`git diff --check` 通过。仅改规划、事实说明、任务和待实施决策；未提交或推送。

## 阻塞与下一步
计划同步完成；下一步执行 STRATZ 接入任务。本轮未修改业务代码或实施联网能力，多账号/长期稳定性与项目 Provider、宿主联调仍待后续任务验证。
