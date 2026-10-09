# 正式版比赛查询 STRATZ 响应修复

Status: done

## 目标
修复用户执行 `do比赛 9035146588` 因赛前购买事件时间为负数而返回 INVALID_RESPONSE 的问题。

## 非目标
自动换源、吞掉上游错误、补造统计或身份，以及公开发布和宿主重启。

## 验收
- 保留合法赛前购买时间的符号与原值，非法类型仍明确失败。
- 覆盖 STRATZ/OpenDota 映射、Dota2UID/AstrBot 比赛消费及订阅 JSON 重开。
- 运行统一离线检查并只读复测指定比赛，记录正式版未部署/聊天未复测。

## 影响模块与决策
[分析模型](../../../packages/dota2forge-core/src/dota2forge_core/domain/analysis.py)、[映射](../../../packages/dota2forge-core/src/dota2forge_core/infrastructure/_analysis_mapping.py)、[契约](../../../docs/subsystems/analysis.md)、[决策](../../notes/implemented/2026-10-09-pregame-purchase-time.md)。

## 验证证据
原目录 main=54417cc，保留已有两个商店任务记录、素材与临时目录。拉取 origin/main=4db06b9，在独立工作区分支 codex/stratz-pregame-purchases 排查。

只读查询指定比赛：基础详情校验成功、十名参赛者；235 条购买事件中 48 条时间为负，最小 -89 秒；分析返回 INVALID_RESPONSE，客户端已关闭。没有保存原始响应、账号或昵称。正式版 a7 随包 Core a4 与最新源码的购买时间约束相同。

修复后对同一比赛只读复测：基础详情与分析均有效，235 条事件和 48 条负时间完整保留，客户端已关闭；[脱敏摘要](../../artifacts/stratz-match-detail-response-v1/live-check.json)与[诊断入口](../../artifacts/stratz-match-detail-response-v1/README.md)可复核。

`uv run --locked python scripts/check_governance.py --all` 最终退出 0：治理/格式/lint/mypy 83 源文件通过；1955 项禁网测试通过，聚合覆盖率 93.04%，scripts/Core/Assets 分别约 94%/93%/92%，三个 80% 门槛通过。首轮因新测试导入排序失败，已修正后完整重跑，没有改变门禁。[日志](../../artifacts/stratz-match-detail-response-v1/offline-check.log)。

`uv build --all-packages` 与 `uv run --locked python scripts/smoke_wheels.py` 均退出 0，五包构建和独立无索引安装/导入成功；[构建](../../artifacts/stratz-match-detail-response-v1/build.log)、[wheel smoke](../../artifacts/stratz-match-detail-response-v1/wheel-smoke.log)。构建仍使用现有版本，仅作为本地验证，不代表新版发行。`git diff --check` 通过。

## 阻塞与下一步
本地修复、双端消费、订阅重开、统一离线与指定比赛只读复测已完成。正式版发布、随包运行库更新、宿主冷启动和真实 QQ 回复仍待后续发行/联调；本次未推送、发布、重启宿主或发送聊天。
