# STRATZ 首版代码推送与 GsCore 测试分支

Status: done

## 目标
按用户2026-10-15“先推送代码，我自己测试一下，AstrBot先不发版”授权，提交并推送主仓首版实现分支，提供匹配的Dota2UID随包测试分支供用户自行测试。

## 非目标
不推送AstrBot分发仓库，不创建任何Release/标签，不提交Cloud/商店，不合并主分支，不部署本机或发送测试消息；不提交凭据/原始聊天/玩家响应，保留两份开工前已有商店历史任务。

## 验收
- 主仓推送codex/stratz-features，包含Core/Renderer、双端源码、测试、文档与脱敏证据；AstrBot仅保留共享源码中的候选改动。
- Dota2UID测试分支携带匹配的Core/Renderer a8、UID a15、Assets a1四份本地wheel，manifest/文档链接固定主仓实现SHA，未发布资产不作为已公开可下载版本。
- 保持2101项统一禁网验证、五包构建/隔离安装与分发消费的真实结果；提交前再核对工作树/链接/格式，固定SHA的分发重新验证摘要与隔离消费。
- 推送后核实远端分支SHA，交付测试分支与安装方式、未联调边界；不自动发送PR/Issue评论。

## 影响模块与决策
[首版实施](2026-10-14-stratz-feature-implementation.md)、[打包契约](../../../docs/cookbook/plugin-release.md)、[原生复盘](../../../docs/subsystems/native-review.md)、[部署暂停](../active/2026-10-15-gscore-nonebot-napcat-live-test.md)。本轮仅交付已有实现，不改变公共契约/存储/权限策略。

## 验证证据
此前统一入口exit0：2101项禁网测试、聚合覆盖91.03%，Ruff/mypy与scripts/Core/Assets门槛通过；五包与双端隔离消费通过。远端main新增合并提交0d277b0但与本地f5e26c9树相同，已快进基线，保留全部功能改动。

主仓实现372b0bb4f0b48ce0167178f10ea0e6542e62d25e与Dota2UID d1f1a2bea9fc55146a83b8532a52b2749901503a均推送codex/stratz-features。固定实现SHA重新生成候选、双端隔离消费exit0；25个GsCore提交文件与候选逐字节一致，4个wheel摘要匹配。主仓暂存150文件凭据检查无命中，保留两份原有未跟踪商店任务；先前失败日志仅清理行尾空白，未掩盖失败。[推送与安装说明](../../artifacts/stratz-code-push-20261015/README.md)。

## 阻塞与下一步
代码与GsCore测试分支推送完成，用户自行部署/测试。两个main不变，未创建Release/标签，未推送AstrBot分发仓库/Cloud/商店，未部署或发送真实消息。真实会话接续见[私聊任务](../active/2026-10-15-gscore-nonebot-napcat-live-test.md)。
