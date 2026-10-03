# 历史单局详情查询与图片卡

Status: in_progress

## 目标
获取历史对局中某一局的详细信息，支持通过比赛 ID 直接查询，也能从已返回战绩列表选择一局；在 Dota2UID 展示详情卡，未来 AstrBot 共用。

## 非目标
完整历史采集、无限翻页、自动申请解析/刷新、跨源拼接和精确 MMR。IMP/经济/购买事件属于后续增量，首版详情不等待全部分析字段。

## 验收
- [x] 实施前核对 STRATZ match 查询/schema，固定 variables；按 ID 获取指定比赛，不要求它出现在当前 recent 列表，不受最近 100 场列表范围限制，不保证所有历史比赛都有详情。
- [x] 新增严格比赛 ID、MatchDetail 和独立详情 Provider/用例；保持现有 PlayerProvider/MatchProvider 消费兼容，逐一检查 Dota2UID、合成 Provider 和服务注入；AstrBot 骨架不计作已实现消费者。
- [x] 基础详情包含 ID、时间、时长、模式/版本、天辉/夜魇、胜方及参赛玩家英雄/KDA/GPM/XPM/装备等可证字段；昵称/身份/缺失玩家不凭空推断。绑定账号确实参赛才高亮我方。
- [x] 保留 source/fetched_at/observed_at/缺失字段；MatchParseState 区分部分解析、未解析、无数据和未知状态，有证据的拒绝/不存在沿用 ProviderError，错误不绘成正常比赛，无证据不声称详情完整。
- [x] Dota2UID 已接直接 ID 的文本详情，用同一 Provider 实例；未绑定可查，不重新拉 recent，帮助与战绩给出查询方式。
- [x] dota比赛 第N场 与 dota战绩 第N页 使用最后完整发送列表；账号/机器人/会话隔离、容量128/TTL10分钟、改绑/重载/发送失败及并发已离线验证，不重新取 recent。
- [x] 战绩图片卡显示比赛 ID 与查询方式。
- [x] 详情契约、Provider、禁网测试、只读联调和 MatchDetailCard 已实现；两队拆页，手机可读并附来源/抓取时间，RenderError 用同次数据文本回退。
- [x] 独立核对并实现经济曲线/购买事件端口：STRATZ `networthPerMinute`/`itemPurchases` 与 OpenDota `gold_t`/`xp_t`/`purchase_log` 按来源语义保存，不阻塞基础详情；IMP/averageImp/award 已核对为未版本化专有输出，保持未实现并记录于[分析契约](../../../docs/subsystems/analysis.md)。
- [x] 复用有限超时、取消、限流与客户端生命周期，无自动重试/跨源切换；账号查询偏好不等于所有权证明，禁止暴露完整平台身份和匿名玩家身份。
- [x] 离线覆盖合法/非法 ID、列表范围外的旧比赛、部分/null/错误详情、匿名参赛者、非参赛绑定账号、列表失效与并发选择；授权账号旧比赛只读验证通过。
- [x] 新命令/图片四包已安装当前 CPython 3.13.2 GsCore，发现桥接替换并冷启动；无管理员会话时不宣称命令注册通过。
- [x] 真实 QQ 单会话详情/图片/序号/取页通过；冷却结束后的直接 ID 详情已由用户确认，10-02冷启动与两轮管理员stop/reload后用户再次确认详情正常、图片可读。

## 影响模块与决策
[Core 端口](../../../packages/dota2forge-core/src/dota2forge_core/ports.py)、[公共契约](../../../docs/subsystems/core.md)、[STRATZ](../../../packages/dota2forge-core/src/dota2forge_core/infrastructure/stratz.py)、[Dota2UID 命令](../../../adapters/Dota2UID/src/Dota2UID/commands.py)、[基础图片任务](2026-10-01-image-interaction.md)、[决策](../../notes/proposed/2026-10-01-image-history-interaction.md)。

## 验证证据
2026-10-01 在保留样图修改的工作区继续推进，先完成与版式无关的详情契约/Provider，再接 Dota2UID 直接 ID 文本命令。原 Dota2Service 构造和两端口不变，旧合成/适配器消费者回归通过；AstrBot 仍为骨架。[实现原因](../../notes/implemented/2026-10-01-historical-match-contract.md)、[只读证据](../../artifacts/historical-match-detail-v1/README.md)。

STRATZ 内省/固定查询通过；授权账号偏移 100 的第 101 条旧比赛直接查到十人数据，账号实际参赛、匿名名称抑制、client_closed=true。has_stats=false 但 parsed_at 存在；两个装备槽未知，不推断完整。未记录真实身份/原始响应。

新增 150 项 Core、26 项适配器详情和42项选择测试；覆盖旧比赛、null/schema/错误、匿名、非参赛账号、无绑定、共用限流、发送失败、100场取页/选择、会话过期/隔离、并发和停用取消。[列表状态决策](../../notes/implemented/2026-10-01-delivered-list-selection.md)。新增 MatchParseState 文本/图片标签；状态只摘要同次上游证据，不宣称字段完整。

最终统一入口通过：813 项禁网测试、Ruff、mypy 36 源文件；综合96.27%，Core约99%、scripts约97%，Dota2UID约95%、Renderer约98%，两个独立80%门槛通过。四包 build 及无索引、无SDK、隔离 wheel 安装/导入通过，包含详情公共导出与 Renderer 资源断言；CPython3.13.2 宿主已安装四包 wheel 并冷启动，Dota2UID/Renderer独立导入与资源生成通过；新命令未实机消息/QQ验证。

## 阻塞与下一步
基础详情契约/Provider/直接ID、列表序号/取页和详情卡已完成代码、离线与QQ单会话验收。10-02宿主恢复/冷启动和两轮stop/reload后，用户复测详情正常、图片可读，[证据](../../artifacts/gscore-image-lifecycle-v1/README.md)。IMP/经济/购买序列口径仍待独立增量；不静默增加来源缓存/重试。
