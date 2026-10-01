# 历史详情只读验证 v1

两个脚本是显式联调入口，不由普通测试执行。凭据/授权账号由 uv 从本机被忽略的 `.env` 注入；脚本不输出 Token、完整账号、昵称、比赛 ID 或原始玩家/比赛响应，不写真实响应到仓库。

```sh
uv run --env-file .env --locked python .agents/artifacts/historical-match-detail-v1/inspect_schema.py
uv run --env-file .env --locked python .agents/artifacts/historical-match-detail-v1/check_detail.py --offset 100
```

`inspect_schema.py` 仅返回公开字段/schema 形状；`check_detail.py` 为验证旧比赛，先在授权账号的列表偏移处找一个 ID，再通过实际 MatchDetailService/StratzProvider 直接查详情。诊断内部复用同实例的 HTTP 限流状态；生产详情用例没有列表查询。成功和失败均由 async with 关闭客户端，无重试/解析/写入作业。

2026-10-01 实际证据：内省确认 `match(id: Long!)`、MatchType 与 MatchPlayerType 所选字段，固定详情查询无 GraphQL errors。偏移 100（第 101 条，不在 recent 100 条范围内）的旧比赛直接查询成功：source=stratz、10 名参赛者、授权账号实际参赛、匿名名称抑制、client_closed=true。MatchDetail 必选缺口为空，参赛者有两个未知装备槽；has_stats=false、parsed_at 存在，observed_at/patch 名称未知。

这只证明一个授权账号/旧比赛样本，不保证历史覆盖、隐私/不存在错误码、多账号或长期稳定性。Dota2UID 直接 ID、已发送列表序号/取页文本命令已离线验证；详情卡未实现，未部署或 QQ 实测。离线用例使用完全合成响应，见 [测试](../../../tests/core/test_stratz_detail.py)；公共契约原因见 [决策](../../notes/implemented/2026-10-01-historical-match-contract.md)。
