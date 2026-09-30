# 历史单局详情查询与图片卡

Status: planned

## 目标
获取历史对局中某一局的详细信息，支持通过比赛 ID 直接查询，也能从已返回战绩列表选择一局；在 Dota2UID 展示详情卡，未来 AstrBot 共用。

## 非目标
完整历史采集、无限翻页、自动申请解析/刷新、跨源拼接和精确 MMR。IMP/经济/购买事件属于后续增量，首版详情不等待全部分析字段。

## 验收
- [ ] 实施前核对 STRATZ match 查询/schema，固定 variables；按 ID 获取指定比赛，不要求它出现在当前 recent 列表，不受最近 100 场列表范围限制，不保证所有历史比赛都有详情。
- [ ] 新增严格比赛 ID、MatchDetail 和独立详情 Provider/用例；保持现有 PlayerProvider/MatchProvider 消费兼容，逐一检查 Dota2UID、合成 Provider 和服务注入；AstrBot 骨架不计作已实现消费者。
- [ ] 基础详情包含 ID、时间、时长、模式/版本、天辉/夜魇、胜方及参赛玩家英雄/KDA/GPM/XPM/装备等可证字段；昵称/身份/缺失玩家不凭空推断。绑定账号确实参赛才高亮我方。
- [ ] 保留 source/fetched_at/observed_at/缺失字段；部分解析、未解析、无数据、未知隐私与有证据的拒绝/不存在区分，错误不绘成正常比赛，无证据不得声称详情完整。
- [ ] 规划 dota比赛 <比赛ID> 为无会话依赖入口；战绩卡同时显示 ID。规划 dota比赛 第N场 从调用者最后一次有效列表选择，先验证账号、机器人、会话、有效期与改绑/重载失效规则，禁止重新拉列表导致序号错指比赛。
- [ ] 先完成详情契约、Provider、禁网测试和只读联调，再实现 MatchDetailCard；可对两队拆页，手机可读且附来源/抓取时间，生成失败用同次数据的文本回退。
- [ ] 后续独立核对 IMP、经济曲线和购买事件口径及可用性；IMP 标明 STRATZ 指标，缺失/未解析用未知表示，不让这些字段阻塞基础详情。
- [ ] 复用有限超时、取消、限流与客户端生命周期，无自动重试/跨源切换；账号查询偏好不等于所有权证明，禁止暴露完整平台身份和匿名玩家身份。
- [ ] 离线覆盖合法/非法 ID、列表范围外的旧比赛、部分/null/错误详情、匿名参赛者、非参赛绑定账号、列表失效与并发选择；用授权账号的历史比赛另做只读和 QQ 验收。

## 影响模块与决策
[Core 端口](../../../packages/dota2forge-core/src/dota2forge_core/ports.py)、[公共契约](../../../docs/subsystems/core.md)、[STRATZ](../../../packages/dota2forge-core/src/dota2forge_core/infrastructure/stratz.py)、[Dota2UID 命令](../../../adapters/Dota2UID/src/Dota2UID/commands.py)、[基础图片任务](2026-10-01-image-interaction.md)、[决策](../../notes/proposed/2026-10-01-image-history-interaction.md)。

## 验证证据
2026-10-01 用户明确要求历史单局详情。目前只有玩家和最近比赛 Provider；尚无详情公共模型、按 ID 用例、列表序号会话或详情卡。此前 STRATZ 详情临时评测不等于本任务实现通过。

## 阻塞与下一步
按基础图片交互 → 最小详情契约/Provider → ID 查询/详情卡 → 列表选择 → IMP/时间序列增量推进。字段必须先核对；列表选择需明确有界临时状态与失效规则，不能静默增加战绩缓存/重试。
