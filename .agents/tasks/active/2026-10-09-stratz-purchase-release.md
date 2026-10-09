# 赛前购买修复合并与 Dota2UID a8 发行

Status: in_progress

## 目标
按用户“直推送合并，然后真机更新测试”的授权，合并已验证修复并同步可供真机更新的 Dota2UID 随包分发。

## 非目标
操作用户生产宿主、发送聊天、发布 AstrBot 新版、更新商店索引或改动宿主 SDK。

## 验收
- 主仓修复及版本准备推送并合并 main，远端 CI 通过。
- Core a5/Dota2UID a8 随包候选完成离线安装及摘要检查，保留 Renderer a4/Assets a1 已公开字节。
- Dota2UID main 和 v0.1.0a8 公开资产一致，可从新分发冷启动取得修复。
- 交付明确更新/冷启动及 `do比赛 9035146588` 自测步骤，真实消息结果由用户确认。

## 影响模块与决策
[修复任务](../done/2026-10-09-stratz-match-detail-response.md)、[决策](../../notes/implemented/2026-10-09-pregame-purchase-time.md)、[发行步骤](../../../docs/cookbook/plugin-release.md)、[随包安装](../../../docs/cookbook/gscore-bundled-install.md)。业务在共享 Core，独立分发仅携带主仓生成结果。

## 验证证据
授权前本地修复已完成1955项统一禁网检查、五包构建、隔离wheel安装及指定比赛只读复测；正式a7/Core a4的旧约束已核对。用户于2026-10-09明确授权推送合并并自行真机更新。

Core a5/Dota2UID a8 包元数据、双端 Core 下限、uv.lock及生成参考已同步。新版统一入口退出0：1955项/330.91s，聚合93.04%，Ruff/mypy83及三组独立80%门槛通过；另114项版本与消费专项通过。[统一日志](../../artifacts/dota2uid-pregame-release-v1/offline-check.log)。

五包[构建](../../artifacts/dota2uid-pregame-release-v1/build.log)、[隔离安装](../../artifacts/dota2uid-pregame-release-v1/wheel-smoke.log)、[双端分发smoke](../../artifacts/dota2uid-pregame-release-v1/distribution-smoke.log)均退出0。a8-review-v1为本地候选；Renderer a4/Assets a1的wheel/sdist逐字节复用a7公开资产并校验SHA256。

## 阻塞与下一步
准备新版包元数据、锁文件和分发候选，验证后推送主仓并合并；随包公开发行后由用户冷启动自测。
