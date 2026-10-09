# 购买事件保留赛前负时间

Category: bug-fix
Related task: [响应修复](../../tasks/done/2026-10-09-stratz-match-detail-response.md)
Related code: [分析模型](../../../packages/dota2forge-core/src/dota2forge_core/domain/analysis.py)、[来源映射](../../../packages/dota2forge-core/src/dota2forge_core/infrastructure/_analysis_mapping.py)
Related docs: [分析契约](../../../docs/subsystems/analysis.md)

## Problem
正式版 `do比赛 9035146588` 基础详情有效，但随后的分析查询失败。只读诊断发现 235 条购买事件中 48 条发生于赛前，时间最低为 -89 秒。共享映射与 PurchaseEvent 错误地要求时间非负，将正常赛前出装拒绝为 INVALID_RESPONSE；两端比赛指令和订阅报告都会受影响。

## Decision
PurchaseEvent.time_seconds 保存来源比赛时钟的有符号整数，负数表示零秒前的赛前购买；保持原值、顺序、事件数量与来源，不归零或删除。STRATZ itemPurchases 与 OpenDota purchase_log 使用同一语义。只修改购买时间校验，bool、浮点、字符串和 null 仍拒绝；物品、charges、经济序列等约束继续生效。

核对已实现消费者：Dota2UID Runtime、AstrApplication 和共享报告文本消费事件计数；订阅 JSON 编解码已保存有符号整数，无需迁移 schema。基础详情模型、Provider 端口和错误传播不变。

用户随后授权推送合并并自行真机更新。Core 升为 a5，Dota2UID 随包发行升为 a8；两个适配器的 Core 下限同步 a5，防止新消费包安装到仍拒绝赛前时间的旧 Core。Renderer a4/Assets a1 保留既有公开字节，AstrBot a8 只准备源码而不在本次公开，见[发行任务](../../tasks/active/2026-10-09-stratz-purchase-release.md)。

## Alternatives considered
删除赛前事件或把负时间改为零会损失来源事实。仅忽略分析失败仍会丢失正常购买数据，并改变错误语义。给 STRATZ 单独接受负时间会与共用领域值及 OpenDota 比赛时钟不一致。

## Consequences
公共值允许合法赛前时间，旧非负事件仍兼容。既有持久记录无需迁移；旧运行库仍不能解析含负时间的新记录，升级应使用匹配运行包并遵循宿主关闭流程。不得根据负时间推断绝对日期或补造缺失事件。

## Verification
模型、两来源映射、双端比赛消费与订阅重开禁网回归通过。统一入口1955项测试、Ruff、mypy及scripts/Core/Assets独立覆盖率门槛通过；五包构建与隔离wheel安装通过。指定比赛只读复测保留235条购买事件（48条负时间），基础详情及分析均有效，客户端关闭；证据见任务。未公开发布、未更新正式宿主或发送聊天。
