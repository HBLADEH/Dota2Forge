# Dota2UID 玩家订阅命令入口修复

Status: done

## 目标
修复有效的 `do订阅玩家 <玩家ID>` 在 GsCore 被拒绝为参数错误的问题，并检查共享前缀的比赛订阅、订阅列表入口；沿用本会话插件发行授权准备Dota2UID a12修复版。

## 非目标
改变订阅权限、数据模型或 Provider 策略；操作真实宿主、查询真实玩家和发送聊天消息。

## 验收
- 原始命令经宿主匹配后进入正确的订阅分支，玩家 ID 保持完整。
- 薄入口与随包入口均覆盖，错误参数和群聊权限校验保持。
- 回归测试使用合成身份，统一离线检查通过。
- a12分发main／tag／Release固定源码、包版本与摘要，公开下载可验证；不覆盖a11。

## 影响模块与决策
[适配器](../../../adapters/Dota2UID/)、[订阅契约](../../../docs/subsystems/subscriptions.md)、[宿主契约](../../../docs/subsystems/gscore-host.md)、[修复决策](../../notes/implemented/2026-10-11-subscription-command-prefix.md)、[证据](../../artifacts/subscription-command-prefix-v1/README.md)。

## 验证证据
现有控制器测试直接传入正确keyword通过，但桥接桩按完整关键字查表，未覆盖前缀匹配。新增回归修复前3项复现同一报错，修复后3项通过；本机实际Event／Trigger／trie源码禁网隔离执行，旧入口与倒序入口仍先命中短命令，修复后9种路由通过。源码摘要不变，没有操作生产配置或外部聊天。

## 阻塞与下一步
统一禁网检查exit0，2013项通过；五包构建与逐包隔离安装／导入通过。Core、Renderer、Assets wheel摘要与已公开a11附件相同。首轮Ruff指出隔离脚本循环变量覆盖迭代输入，修正命名后重新完整检查通过，未解除门禁。

源码[PR #15](https://github.com/HBLADEH/Dota2Forge/pull/15)已合并；head `2e4e56a4b2e8242938474f65d3084f7ba201c736` 的push／PR四项Python3.12／3.13 CI通过。固定该源码生成候选，SDK-free分发smoke通过。

[Dota2UID a12](https://github.com/HBLADEH/Dota2UID/releases/tag/v0.1.0a12)已公开，分发main／tag为`d66c12e80cedc7d3e9f131ce77f61866c2bd24f1`；仓库18文件与候选一致，ZIP与仓库一致，11个附件完整匿名下载／SHA256通过。匿名GitHub API曾限流，改用gh读取公开发布元数据，保持所有内容断言；区别见证据。

本任务完成。生产宿主更新、QQ原命令重试及真实订阅推送仍待用户环境复测；未更改配置／数据库或发送聊天，AstrBot版本保持a10。
