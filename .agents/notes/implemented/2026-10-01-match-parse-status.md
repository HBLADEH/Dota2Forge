# 历史详情解析状态证据

Category: data
Related task: [历史单局详情](../../tasks/active/2026-10-01-historical-match-detail.md)
Related code: [详情模型](../../../packages/dota2forge-core/src/dota2forge_core/domain/match_detail.py)
Related docs: [Core 契约](../../../docs/subsystems/core.md)

## Problem
详情契约保留了 STRATZ 的 `isStats` 和 `parsedDateTime`，但文本与图片只展示原始字段。用户无法区分上游明确未解析、上游标记已解析、只返回部分字段和完全没有解析证据的观察；`null match` 也需要保持无数据与隐私原因未知。

## Decision
新增 `MatchParseState`，只表达可由同次响应证明的状态：`UNPARSED` 对应 `isStats=False`，`UPSTREAM_PARSED` 对应 `isStats=True`，没有标记但已有字段或参赛者时为 `PARTIAL`，完全没有解析标记和详情字段时为 `UNKNOWN`，显式 `null match` 为 `NO_DATA`。`UPSTREAM_PARSED` 不等于字段完整，`NO_DATA` 不等于不存在或私密。

文本详情和 `MatchDetailCard` 同时展示状态、原始 `isStats` 与解析时间；仍保留逐字段缺失、source、fetched_at 和 observed_at，不补字段、不触发第二次 Provider 查询。

## Alternatives considered
- 仅显示 `isStats`：无法表达无标记的部分响应，也容易被读成完整性承诺。
- 用 `parsedDateTime` 单独判定完整：实测 `isStats=False` 仍可能带解析时间。
- 将 null 归为 NOT_FOUND 或 PRIVATE：当前响应没有对应证据。

## Consequences
Core 新增一个只读派生属性和公共枚举，适配器与共享 Renderer 需维护有限标签映射。状态仍是上游证据摘要，不覆盖 IMP、经济曲线、购买事件或字段完整性评估。

## Verification
新增 Core、STRATZ 映射、Dota2UID 文本断言；完整离线测试、Ruff、mypy 和治理检查在本轮修改后复跑。真实 QQ 详情/分页/压缩仍待宿主窗口可操作时验收。
