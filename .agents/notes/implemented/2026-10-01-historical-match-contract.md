# 历史单局详情的独立 Core 契约

Category: data
Related task: [历史详情](../../tasks/active/2026-10-01-historical-match-detail.md)
Related code: [详情模型](../../../packages/dota2forge-core/src/dota2forge_core/domain/match_detail.py)
Related docs: [Core 契约](../../../docs/subsystems/core.md)

## Problem
已实现的玩家/近期 Provider 不能按 ID 查询列表外的旧比赛。原计划要求最小十人/两队详情、严格 ID、匿名保护与可区分缺失语义；`null match` 和 `isStats` 均不足以证明比赛不存在、私密或数据完整。样图仍待明确确认，因此先实现与版式无关的详情基础。

## Decision
- 新增 MatchId：规范 ASCII 十进制、1 至 signed Long 最大值 9223372036854775807；拒绝 bool、浮点、空白、符号、前导零、URL 和序号。MatchDetailService 仅依赖独立 MatchDetailProvider，不读取绑定、不拉 recent，也不受现有 100 场/10 页范围限制。
- 保持 Dota2Service 构造、PlayerProvider、MatchProvider 及现有公开模型兼容；Dota2UID 原有组合入口和合成消费者继续消费旧契约。详情消费者通过独立服务显式注入，不用可选构造参数改变旧服务行为。
- MatchDetail 保留可缺省时间、模式枚举、上游 gameVersionId、胜方、isStats 和解析时间；十人以内的不可变参赛者保存槽位、明确阵营、英雄、KDA/GPM/XPM 和六个装备槽。None/0/False 区分；装备 0 为上游零值，None 为未知。人数、槽位和字段缺口不推断成完整详情。
- 匿名账号哨兵 0/4294967295 转为无账号且 is_anonymous=True；null 账号的匿名状态未知。两者都禁止携带昵称，不暴露潜在身份。已知账号才保留经一致性核对的昵称；字段 repr 隐藏账号/昵称。participant(AccountId) 仅查实际参赛者，不能据绑定偏好编造我方阵营。
- HTTP 200、无 GraphQL errors 的显式 null match 返回 MatchDetailUnavailable，保留 source/fetched_at，原因/隐私未知；这不是正常比赛、NOT_FOUND 或 PRIVATE。列表 null、空或少于十人分别保存，非法字段/schema/重复槽位/账号、GraphQL errors 仍为 INVALID_RESPONSE。
- STRATZ 使用固定 `$matchId: Long!` variables 查询；2026-10-01 内省与只读请求核对所有选中字段。gameVersionId 不转换为未经核对的补丁名称；parsedDateTime 不冒充观测时间；isStats 不代表解析/详情完整。共用现有 HTTP 限额、有限超时、取消和客户端所有权，无自动重试、解析作业或换源。

## Alternatives considered
- 在旧 MatchProvider 中强制加入新方法：会使现有合成 Provider/消费者失配，选择独立端口与服务。
- null match 抛 NOT_FOUND：缺少原因证据，选择单独无数据结果。
- 将未收录/未解析字段补零或补十名玩家：掩盖缺口，保留可缺省字段与实际列表。
- isStats=true 即声明完整：既有评测已显示指标不等价，保留上游标记和逐字段缺口。

## Consequences
公共导出新增详情值和用例，Core 仍无必选依赖。Dota2UID 已显式注入独立服务，`dota比赛 <比赛ID>` 返回同次结果的分阵营文本，未绑定可查；只高亮实际参赛绑定账号，错误/取消保真。战绩文本显示直接查询命令。会话序号/取页按 [独立选择决策](2026-10-01-delivered-list-selection.md) 实现；详情卡、字体资源和 IMP/经济数据仍未实现，真实 QQ 验收按两个任务推进。正常无数据与 Provider 错误分别展示。客户端/日志配置由组合入口管理。

## Verification
150 项新增 Core 禁网合成用例通过，详情模型与映射语句/分支 100%；首次子集因仓库总覆盖率不足仍失败，未调整门槛。最终统一705项通过，Core约99%、scripts约97%，Dota2UID独立约96%；三包构建/无索引隔离wheel安装导入通过。只读旧比赛查到十人数据并关闭客户端，未记录原始身份/响应。wheel smoke 增加详情公共导出断言，未改离线安装/SDK 隔离断言；脚本改动需维护者评审。内省/只读脚本手动调用，不进入普通pytest；新命令未部署/QQ验证。
