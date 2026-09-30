# STRATZ 与免费数据源候选评测

Status: done

## 目标
按用户澄清，以免费、好用、稳定为标准评测 STRATZ、OpenDota 和 Valve；服务端开源不作为门槛。完成公开资料、鉴权、线上额度及一个授权账号最近 20 场的实际对比。

## 非目标
不实施 Provider 或调整运行策略，不创建账号或购买额度，不发布或发送消息；单账号样本不代表全站质量。

## 验收
- [x] 核对 STRATZ 授权、当前 Token 额度与查询能力。
- [x] 同账号比较段位、最近比赛基础字段及详细数据覆盖。
- [x] 修正先前调研的选型前提，交付建议并列明未验证项。

## 影响模块与决策
仅调研；参考 [先前调研](2026-09-30-data-source-survey.md) 与 [Core 契约](../../../docs/subsystems/core.md)。不改变公共契约或实施决策。

## 验证证据
2026-09-30 检查工作区并保留已有修改，读取相关规则和任务。用户授权使用所给 Token 和 Steam 主页进行只读查询；账号值仅在会话内转换，仓库未存凭据、完整身份或原始玩家响应。

官方知识库 [免费及署名要求](https://github.com/STRATZ-Esports/knowledge-base/issues/31)、[Token 分类](https://github.com/STRATZ-Esports/knowledge-base/issues/37)、[额度](https://github.com/STRATZ-Esports/knowledge-base/issues/15) 更新于 2021 年，不能当当前配额保证。[数据能力](https://github.com/STRATZ-Esports/knowledge-base/issues/7) 更新于 2024-12-24，明确实际 MMR 不属于可提供的公开数据。

STRATZ 初始普通 User-Agent 请求（含带鉴权最小查询）返回 403 HTML Cloudflare 挑战页。根据社区客户端线索改用 User-Agent: STRATZ_API，同一 Bearer Token、端点和最小查询返回 200 JSON。此后玩家查询及类型内省、详细数据查询均成功，无 GraphQL errors。不能将早期 403 判为 Token 失效或玩家隐私。

实际响应头：该 Token 限额 8/秒、150/分钟、1500/小时、15000/天，仅代表所测 Token。OpenDota metadata 返回免费 3000/天、60/分钟。

最近 20 场 ID 完全重合，英雄、开始时间、时长、阵营、胜方、K/D/A 无差异。STRATZ 返回段位编码 51，OpenDota 返回 52；用户随后确认当前为传奇 1 星、之前达到传奇 2 星，故本样本 STRATZ 与当前状态一致，OpenDota 保留旧段位。该核对来自用户确认，不是游戏客户端自动验证，不推广为所有账号的时效保证。OpenDota computed_mmr 明确为估算。

STRATZ 20 场中 15 场有净资产序列和购买事件，13 场有 IMP；isStats 为 true 的有 19 场，故不能把该标记等同于详细字段完整。OpenDota 20 次对应详情请求均 200，其中 2 场有解析版本、经济序列、补刀序列和购买记录。最新一场 STRATZ 有上述详细数据，OpenDota 缺少，双方基础结果一致。未发起解析/刷新作业。

历史统计口径不同：OpenDota 默认胜负合计 2771，significant=0 后 3235；STRATZ matchCount=3201。不能据此简单判断谁历史完整。

单次观察：OpenDota 资料/近期/胜负/最新详情约 0.69–0.84 秒；STRATZ 组合资料与 20 场约 1.16 秒、20 场详细字段约 1.25 秒。请求内容不同，未计算 p95 或宣称性能优劣。

统一离线检查 `uv run --locked python scripts/check_governance.py --all` 通过：治理、Ruff、mypy、251 项测试；Core 100%、治理工具 98%（报告取整）。在线核验在普通测试之外执行。已建议轮换聊天中提供的 Token。

## 阻塞与下一步
本轮评测完成，用户已接受 STRATZ 主源、OpenDota 补充与交叉核验、Valve 按需补充的选型；计划落实见 [待实施决策](../../notes/implemented/2026-09-30-provider-selection.md)。联网 Provider 和自动回退尚未实现。
尚未验证多账号覆盖、长期稳定性、新比赛收录延迟、限流边界、所有隐私场景及宿主联调；未做负载测试。生产接入时需单独形成任务/决策，固定 GraphQL 查询、识别部分错误，保留数据来源、缺失值和时间语义。
