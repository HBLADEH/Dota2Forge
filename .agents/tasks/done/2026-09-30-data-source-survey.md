# Dota2 免费开源数据获取调研

Status: done

## 目标
回答个人段位、精确 MMR、基础战绩与录像解析的主流获取方法，区分开源软件与免费托管服务，并提供可核验来源。
用户随后澄清：开源不是门槛，真实要求为免费好用；此前基于完整开源的优先级不再适用。STRATZ 纳入同级候选，见 [补充评测](2026-09-30-stratz-evaluation.md)。

## 非目标
不实现 Provider，不改变已定数据源策略，不登录 Steam，不查询真实私人账号，不发布或发送消息。

## 验收
- [x] 比较 OpenDota、Valve Web API、GC、开源录像解析与 GSI，并说明 STRATZ 等服务的开源限制。
- [x] 标明隐私、历史完整性、时效、额度与维护风险；不将估算分数当精确 MMR。
- [x] 在对话交付详细建议与来源，记录实际核验和未验证事项。

## 影响模块与决策
仅调研记录；参考 [Core 契约](../../../docs/subsystems/core.md)，不修改公共契约或 Provider 策略，无需新实施决策。

## 验证证据
已检查工作区，保留所有已有修改；读取根规则、任务模板、相关任务与 Core 契约/决策。
通过公开 HTTP 读取 OpenDota 在线 schema、项目 README 与许可证，以及 GitHub 仓库元信息；未使用凭据。
2026-09-30：[在线 schema](https://api.opendota.com/api) 为 31.1.0，computed_mmr/computed_mmr_turbo 明确为估算，ratings 为段位变化历史。[metadata](https://api.opendota.com/api/metadata) 返回 freeCallLimit=3000、freeRateLimit=60；结合前端 Api.tsx 与 core/config.ts 确认为每日免费额度与每分钟限额。实际服务策略可变。
核实 odota/core、odota/parser、dotabuff/manta 为 MIT，skadistats/clarity 为 BSD-3-Clause；Arcana/node-dota2 已归档，ValvePython/dota2 最近 push 为 2023-03-02。读取 Valve Web API 条款和 SteamDatabase GC 协议字段。
STRATZ API/文档页在本环境返回 HTTP 403，未验证当前 token 配额、GraphQL schema 或实时响应。未将其认定为完整开源后端。
统一离线检查 `uv run --locked python scripts/check_governance.py --all` 通过：治理、Ruff 格式/lint、mypy、251 项测试；Core 覆盖率 100%，治理工具 98%（报告取整）。网络核验在普通测试之外单独执行。

## 阻塞与下一步
调研完成；只新增本记录，未改业务代码或数据源策略。未做真实玩家、Steam GC、录像解析执行或宿主联调。若决定实施，以新任务核对授权、在线响应及契约，不将本文建议当成已实现能力。
